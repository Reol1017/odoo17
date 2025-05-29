from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'
    
    lead_source_id = fields.Many2one(
        'crm.lead.source',
        string='商机来源',
        help='选择商机的来源',
        tracking=True
    )
    
    # 重写name_search以支持按来源搜索
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            # 搜索商机来源
            source_ids = self.env['crm.lead.source'].search([
                ('name', operator, name)
            ]).ids
            if source_ids:
                args = args or []
                args = ['|', ('lead_source_id', 'in', source_ids)] + args
        return super(CrmLead, self)._name_search(
            name=name, args=args, operator=operator, 
            limit=limit, name_get_uid=name_get_uid
        )
