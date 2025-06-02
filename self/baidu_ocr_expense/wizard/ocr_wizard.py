# -*- coding: utf-8 -*-

import base64
import os
import tempfile
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class OcrExpenseWizard(models.TransientModel):
    _name = 'ocr.expense.wizard'
    _description = 'OCR费用识别向导'
    
    invoice_file = fields.Binary(string='发票文件', required=True)
    file_name = fields.Char(string='文件名')
    company_id = fields.Many2one('res.company', string='公司', default=lambda self: self.env.company)
    sheet_id = fields.Many2one('hr.expense.sheet', string='费用报告')
    
    def action_recognize(self):
        """识别发票并创建费用"""
        self.ensure_one()
        
        if not self.invoice_file:
            raise UserError(_('请上传发票文件'))
        
        # 检查文件类型
        file_extension = ''
        if self.file_name:
            file_extension = os.path.splitext(self.file_name)[1].lower()
        
        # 创建附件
        attachment_vals = {
            'name': self.file_name or '发票_OCR.pdf' if file_extension == '.pdf' else '发票_OCR.jpg',
            'datas': self.invoice_file,
            'res_model': 'hr.expense',
            'type': 'binary',
        }
        attachment = self.env['ir.attachment'].create(attachment_vals)
        
        try:
            # 创建OCR费用
            expense_id = self.env['hr.expense'].create_from_ocr(attachment.id)
            expense = self.env['hr.expense'].browse(expense_id)
            
            # 如果有关联的费用报告，将费用添加到报告中
            if self.sheet_id:
                expense.write({'sheet_id': self.sheet_id.id})
                # 返回到费用报告表单
                return {
                    'name': _('费用报告'),
                    'view_mode': 'form',
                    'res_model': 'hr.expense.sheet',
                    'res_id': self.sheet_id.id,
                    'type': 'ir.actions.act_window',
                    'context': {'form_view_initial_mode': 'edit'},
                }
            else:
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
            _logger.error("OCR识别失败: %s", str(e))
            raise UserError(_('OCR识别失败: %s') % str(e))