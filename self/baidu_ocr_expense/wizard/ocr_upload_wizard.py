# ========== 清理后的 OCR 向导 ==========
# wizard/ocr_upload_wizard.py

# -*- coding: utf-8 -*-

import base64
import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class OcrUploadWizard(models.TransientModel):
    _name = 'ocr.upload.wizard'
    _description = 'OCR上传向导'
    
    invoice_file = fields.Binary('票据文件', required=True)
    filename = fields.Char('文件名')
    expense_id = fields.Many2one('hr.expense', string='关联费用')
    expense_sheet_id = fields.Many2one('hr.expense.sheet', string='费用报销单')
    
    @api.model
    def default_get(self, fields_list):
        """获取默认值"""
        res = super(OcrUploadWizard, self).default_get(fields_list)
        
        # 处理费用相关上下文
        if self.env.context.get('default_expense_id'):
            res['expense_id'] = self.env.context.get('default_expense_id')
        elif self.env.context.get('default_expense_sheet_id'):
            res['expense_sheet_id'] = self.env.context.get('default_expense_sheet_id')
        # 兼容旧的上下文参数
        elif self.env.context.get('default_sheet_id'):
            res['expense_sheet_id'] = self.env.context.get('default_sheet_id')
            
        return res
    
    def action_upload_and_recognize(self):
        """上传并识别票据"""
        self.ensure_one()
        
        if not self.invoice_file:
            raise UserError(_('请先上传票据文件'))
        
        # 获取OCR配置
        config = self.env['baidu.ocr.config'].get_default_config()
        if not config:
            raise UserError(_('未找到有效的百度OCR配置'))
        
        try:
            # 获取文件内容
            file_content = base64.b64decode(self.invoice_file)
            
            # 调用百度OCR API
            ocr_result = config.recognize_invoice(file_content)
            
            # 检查OCR结果
            if not ocr_result or 'words_result' not in ocr_result:
                raise UserError(_('OCR识别失败'))
            
            # 提取票据类型
            first_result = ocr_result['words_result'][0]
            ticket_type = first_result.get('type', 'unknown')
            
            _logger.info("OCR识别结果: 票据类型=%s", ticket_type)
            
            # 根据票据类型创建相应的记录
            return self._create_invoice_record(ticket_type, ocr_result)
                
        except Exception as e:
            _logger.exception("OCR识别过程中发生错误: %s", str(e))
            raise UserError(_('OCR识别失败: %s') % str(e))
    
    def _create_invoice_record(self, ticket_type, ocr_result):
        """根据票据类型创建相应的记录"""
        if ticket_type == 'vat_invoice':
            # 创建增值税发票记录
            record = self.env['vat.invoice'].create_from_ocr_data(ocr_result)
            
            # 如果有关联的费用报销单，将新费用添加到报销单中
            if self.expense_sheet_id:
                record.sheet_id = self.expense_sheet_id.id
                
            return {
                'type': 'ir.actions.act_window',
                'name': _('增值税发票 - OCR识别结果'),
                'res_model': 'vat.invoice',
                'res_id': record.id,
                'view_mode': 'form',
                'target': 'current',
            }
        elif ticket_type == 'train_ticket':
            # 未来实现: 创建火车票记录
            # record = self.env['train.ticket'].create_from_ocr_data(ocr_result)
            # return {...}
            raise UserError(_('火车票识别功能即将推出'))
        else:
            # 其他类型，创建通用费用记录
            return self._create_generic_expense(ocr_result, ticket_type)
    
    def _create_generic_expense(self, ocr_result, ticket_type):
        """创建通用费用记录"""
        # 基本信息提取
        words_result = ocr_result['words_result'][0]['result']
        amount_str = self._get_field_value(words_result, 'AmountInFiguers') or '0'
        
        try:
            amount = float(amount_str.replace(',', ''))
        except:
            amount = 0.0
        
        # 获取员工
        employee_id = self.env.user.employee_id.id
        if not employee_id:
            raise UserError(_('当前用户没有关联的员工记录'))
        
        # 创建或查找产品
        product = self._find_or_create_product(f'{ticket_type}费用')
        
        expense_vals = {
            'name': f'{ticket_type}费用',
            'employee_id': employee_id,
            'product_id': product.id,
            'unit_amount': amount,
            'quantity': 1.0,
            'date': fields.Date.today(),
            'description': f'OCR识别的{ticket_type}',
        }
        
        # 创建费用记录
        expense = self.env['hr.expense'].create(expense_vals)
        
        # 如果有关联的费用报销单，将新费用添加到报销单中
        if self.expense_sheet_id:
            expense.sheet_id = self.expense_sheet_id.id
            
        return {
            'type': 'ir.actions.act_window',
            'name': _('费用记录 - OCR识别结果'),
            'res_model': 'hr.expense',
            'res_id': expense.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _find_or_create_product(self, name):
        """查找或创建产品"""
        product = self.env['product.product'].search([
            ('name', '=', name),
            ('can_be_expensed', '=', True)
        ], limit=1)
        
        if not product:
            product = self.env['product.product'].create({
                'name': name,
                'detailed_type': 'service',
                'can_be_expensed': True,
                'sale_ok': False,
                'purchase_ok': True,
            })
        
        return product
    
    def _get_field_value(self, words_result, field_name):
        """获取字段值"""
        field_data = words_result.get(field_name, [])
        if field_data and isinstance(field_data, list) and len(field_data) > 0:
            return field_data[0].get('word', '')
        return ''