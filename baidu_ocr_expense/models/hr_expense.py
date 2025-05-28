# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class HrExpense(models.Model):
    _inherit = 'hr.expense'
    
    # OCR识别标志
    ocr_recognized = fields.Boolean('OCR已识别', default=False)
    
    # 发票基本信息
    invoice_code = fields.Char('发票代码', readonly=True)
    invoice_number = fields.Char('发票号码', readonly=True)
    invoice_date = fields.Date('开票日期', readonly=True)
    drawer = fields.Char('开票人', readonly=True)
    
    # 金额信息
    tax_amount = fields.Float('税额', digits=(16, 2), readonly=True)
    amount_without_tax = fields.Float('不含税金额', digits=(16, 2), readonly=True)
    tax_rate = fields.Char('税率', readonly=True)
    amount_in_words = fields.Char('价税合计(大写)', readonly=True)
    
    # 销售方和购买方信息
    vendor_name = fields.Char('销售方名称', readonly=True)
    vendor_tax_id = fields.Char('销售方税号', readonly=True)
    purchaser_name = fields.Char('购买方名称', readonly=True)
    purchaser_tax_id = fields.Char('购买方税号', readonly=True)
    
    # 票据类型
    ticket_type = fields.Char('票据类型', readonly=True)
    
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
        vals = {
            'name': ocr_data.get('name', '未命名费用'),
            'date': ocr_data.get('date', fields.Date.today()),
            'total_amount': ocr_data.get('amount', 0.0),
            'product_id': ocr_data.get('product_id'),
            'description': ocr_data.get('description', ''),
            'ocr_recognized': True,
            'invoice_code': ocr_data.get('invoice_code', ''),
            'invoice_number': ocr_data.get('invoice_number', ''),
            'invoice_date': ocr_data.get('invoice_date'),
            'drawer': ocr_data.get('drawer', ''),
            'tax_amount': ocr_data.get('tax_amount', 0.0),
            'amount_without_tax': ocr_data.get('amount_without_tax', 0.0),
            'tax_rate': ocr_data.get('tax_rate', ''),
            'amount_in_words': ocr_data.get('amount_in_words', ''),
            'vendor_name': ocr_data.get('vendor_name', ''),
            'vendor_tax_id': ocr_data.get('vendor_tax_id', ''),
            'purchaser_name': ocr_data.get('purchaser_name', ''),
            'purchaser_tax_id': ocr_data.get('purchaser_tax_id', ''),
            'ticket_type': ocr_data.get('ticket_type', ''),
        }
        
        # 创建费用记录
        expense = self.create(vals)
        
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