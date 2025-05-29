# -*- coding: utf-8 -*-

import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class OcrExpenseWizard(models.TransientModel):
    _name = 'ocr.expense.wizard'
    _description = 'OCR费用识别向导'
    
    invoice_file = fields.Binary(string='发票图像', required=True)
    file_name = fields.Char(string='文件名')
    company_id = fields.Many2one('res.company', string='公司', default=lambda self: self.env.company)
    
    def action_recognize(self):
        """识别发票并创建费用"""
        self.ensure_one()
        
        if not self.invoice_file:
            raise UserError(_('请上传发票图像'))
        
        # 创建附件
        attachment_vals = {
            'name': self.file_name or '发票_OCR.jpg',
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