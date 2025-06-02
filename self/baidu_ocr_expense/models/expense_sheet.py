# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'
    
    has_ocr_expenses = fields.Boolean(string='包含OCR识别费用', compute='_compute_has_ocr_expenses', store=True)
    
    @api.depends('expense_line_ids', 'expense_line_ids.ocr_extracted')
    def _compute_has_ocr_expenses(self):
        """计算是否包含OCR识别的费用"""
        for sheet in self:
            sheet.has_ocr_expenses = any(expense.ocr_extracted for expense in sheet.expense_line_ids)
    
    def action_ocr_expense_wizard(self):
        """打开OCR费用识别向导"""
        self.ensure_one()
        return {
            'name': _('OCR费用识别'),
            'type': 'ir.actions.act_window',
            'res_model': 'ocr.expense.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sheet_id': self.id,
            }
        } 