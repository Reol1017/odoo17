from odoo import models, fields, api, _

class CrmLead(models.Model):
    _inherit = 'crm.lead'
    
    expense_ids = fields.Many2many('hr.expense', string='相关费用')
    expense_count = fields.Integer(compute='_compute_expense_count', string='费用数量')
    
    def _compute_expense_count(self):
        for lead in self:
            lead.expense_count = len(lead.expense_ids)
    
    def action_view_expenses(self):
        self.ensure_one()
        return {
            'name': _('线索费用'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.expense_ids.ids)],
            'context': {
                'default_employee_id': self.env.user.employee_id.id,
                'default_name': self.name,
                'default_company_id': self.company_id.id,
            }
        }
    class HrExpense(models.Model):
        _inherit = 'hr.expense'
    
        crm_lead_ids = fields.Many2many('crm.lead', string='相关线索')