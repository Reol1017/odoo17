# -*- coding: utf-8 -*-

import base64
import json
import os
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class OcrDebugWizard(models.TransientModel):
    _name = 'ocr.debug.wizard'
    _description = 'OCR调试向导'
    
    invoice_file = fields.Binary(string='发票文件', required=True)
    file_name = fields.Char(string='文件名')
    company_id = fields.Many2one('res.company', string='公司', default=lambda self: self.env.company)
    
    # 调试结果字段
    raw_ocr_result = fields.Text(string='原始OCR结果', readonly=True)
    processed_result = fields.Text(string='处理后结果', readonly=True)
    mapped_fields = fields.Text(string='映射字段', readonly=True)
    error_message = fields.Text(string='错误信息', readonly=True)
    success = fields.Boolean(string='识别成功', readonly=True, default=False)
    
    def action_test_ocr(self):
        """测试OCR识别"""
        self.ensure_one()
        
        if not self.invoice_file:
            raise UserError(_('请上传发票文件'))
        
        try:
            # 获取OCR配置
            ocr_config = self.env['baidu.ocr.config'].search([
                ('company_id', '=', self.env.company.id),
                ('active', '=', True)
            ], limit=1)
            
            if not ocr_config:
                self.error_message = "未找到百度OCR配置"
                return self._return_form()
            
            # 获取文件数据
            file_data = base64.b64decode(self.invoice_file)
            
            # 检查文件类型
            file_extension = ''
            if self.file_name:
                file_extension = os.path.splitext(self.file_name)[1].lower()
                
            # 检查文件内容的前几个字节来确定文件类型
            is_pdf = False
            if file_extension == '.pdf' or (len(file_data) > 4 and file_data[0:4] == b'%PDF'):
                is_pdf = True
            
            # 根据文件类型调用不同的OCR识别方法
            if is_pdf:
                raw_result = ocr_config.recognize_invoice_pdf(file_data)
            else:
                raw_result = ocr_config.recognize_invoice(file_data)
                
            self.raw_ocr_result = json.dumps(raw_result, ensure_ascii=False, indent=2)
            
            # 测试费用数据准备
            expense_vals = self.env['hr.expense']._prepare_expense_vals_from_ocr(raw_result)
            self.mapped_fields = json.dumps(expense_vals, ensure_ascii=False, indent=2, default=str)
            
            # 显示处理后的关键信息
            processed_info = {
                '供应商': expense_vals.get('vendor_name'),
                '发票号码': expense_vals.get('invoice_number'),
                '发票代码': expense_vals.get('invoice_code'),
                '发票日期': str(expense_vals.get('invoice_date')),
                '费用名称': expense_vals.get('name'),
                '单价': expense_vals.get('unit_amount'),
                '数量': expense_vals.get('quantity'),
                '金额': expense_vals.get('amount'),
                '税率': expense_vals.get('tax_rate'),
                '税额': expense_vals.get('tax_amount'),
                '含税金额': expense_vals.get('amount_with_tax'),
                '是否固定资产': expense_vals.get('is_fixed_asset'),
            }
            
            self.processed_result = json.dumps(processed_info, ensure_ascii=False, indent=2)
            self.success = True
            self.error_message = "识别成功！"
            
        except Exception as e:
            self.error_message = f"OCR识别失败: {str(e)}"
            self.success = False
            
        return self._return_form()
    
    def action_create_expense(self):
        """创建费用记录"""
        self.ensure_one()
        
        if not self.success:
            raise UserError(_('请先成功测试OCR识别'))
        
        try:
            # 创建附件
            attachment_vals = {
                'name': self.file_name or ('发票_OCR_DEBUG.pdf' if '.pdf' in (self.file_name or '').lower() else '发票_OCR_DEBUG.jpg'),
                'datas': self.invoice_file,
                'res_model': 'hr.expense',
                'type': 'binary',
            }
            attachment = self.env['ir.attachment'].create(attachment_vals)
            
            # 创建OCR费用
            expense_id = self.env['hr.expense'].create_from_ocr(attachment.id)
            
            # 打开创建的费用
            return {
                'name': _('OCR识别的费用'),
                'view_mode': 'form',
                'res_model': 'hr.expense',
                'res_id': expense_id,
                'type': 'ir.actions.act_window',
                'context': {'form_view_initial_mode': 'edit'},
            }
            
        except Exception as e:
            raise UserError(_('创建费用失败: %s') % str(e))
    
    def _return_form(self):
        """返回当前表单"""
        return {
            'name': _('OCR调试向导'),
            'view_mode': 'form',
            'res_model': 'ocr.debug.wizard',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }