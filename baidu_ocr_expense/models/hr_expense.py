# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class HrExpense(models.Model):
    _inherit = 'hr.expense'
    
    ocr_recognized = fields.Boolean('OCR已识别', default=False)
    invoice_code = fields.Char('发票代码', readonly=True)
    invoice_number = fields.Char('发票号码', readonly=True)
    vendor_name = fields.Char('销售方名称', readonly=True)
    
    # 新增字段
    invoice_date = fields.Date('开票日期', readonly=True)
    note_drawer = fields.Char('开票人', readonly=True)
    total_amount = fields.Float('金额合计', digits=(16, 2), readonly=True)
    total_tax = fields.Float('税额合计', digits=(16, 2), readonly=True)
    amount_in_figures = fields.Float('含税价格', digits=(16, 2), readonly=True)
    amount_in_words = fields.Char('价税合计(大写)', readonly=True)
    tax_rate = fields.Char('税率', readonly=True)
    remarks = fields.Text('备注', readonly=True)
    
    # 购买方信息
    purchaser_name = fields.Char('购买方名称', readonly=True)
    purchaser_register_num = fields.Char('购买方税号', readonly=True)
    
    # 销售方信息
    seller_register_num = fields.Char('销售方税号', readonly=True)
    
    def action_ocr_recognize(self):
        """打开OCR识别向导"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ocr.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_expense_id': self.id} if self.id else {},
        }
    
    @api.model
    def create_from_ocr_data(self, ocr_data, attachment=None):
        """从OCR数据创建费用记录"""
        # 这个方法可以被其他模块调用，用于从OCR数据创建费用记录
        # 确保ocr_recognized字段被设置为True
        ocr_data['ocr_recognized'] = True
        
        _logger.info("创建OCR费用记录: %s", ocr_data)
        
        vals = {
            'name': ocr_data.get('name', '未命名费用'),
            'date': ocr_data.get('date', fields.Date.today()),
            'total_amount': ocr_data.get('total_amount', 0.0),
            'product_id': ocr_data.get('product_id'),
            'description': ocr_data.get('description', ''),
            'ocr_recognized': True,  # 强制设置为True
            'invoice_code': ocr_data.get('invoice_code', ''),
            'invoice_number': ocr_data.get('invoice_number', ''),
            'vendor_name': ocr_data.get('vendor_name', ''),
            
            # 新增字段值
            'invoice_date': ocr_data.get('invoice_date'),
            'note_drawer': ocr_data.get('note_drawer', ''),
            'total_tax': ocr_data.get('total_tax', 0.0),
            'amount_in_figures': ocr_data.get('amount_in_figures', 0.0),
            'amount_in_words': ocr_data.get('amount_in_words', ''),
            'tax_rate': ocr_data.get('tax_rate', ''),
            'remarks': ocr_data.get('remarks', ''),
            'purchaser_name': ocr_data.get('purchaser_name', ''),
            'purchaser_register_num': ocr_data.get('purchaser_register_num', ''),
            'seller_register_num': ocr_data.get('seller_register_num', ''),
        }
        
        # 创建费用记录
        expense = self.create(vals)
        
        # 记录日志
        _logger.info("OCR费用记录已创建: %s, ocr_recognized=%s", expense.id, expense.ocr_recognized)
        
        # 如果有附件，附加到费用记录
        if attachment:
            self.env['ir.attachment'].create({
                'name': attachment.get('name', '附件'),
                'type': 'binary',
                'datas': attachment.get('datas'),
                'res_model': 'hr.expense',
                'res_id': expense.id,
            })
        
        return expense

class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'
    
    def action_ocr_recognize(self):
        """打开OCR识别向导"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ocr.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_expense_sheet_id': self.id} if self.id else {},
        } 