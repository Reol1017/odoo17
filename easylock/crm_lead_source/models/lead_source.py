from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class LeadSource(models.Model):
    _name = 'crm.lead.source'
    _description = '商机来源'
    _order = 'sequence, name'
    _rec_name = 'name'

    code = fields.Char('来源ID', help='用于标识来源的唯一编码')
    name = fields.Char('来源途径', required=True, translate=True)
    description = fields.Text('描述')
    sequence = fields.Integer('序号', default=10)
    
    # 统计字段
    lead_count = fields.Integer(
        '商机数量', 
        compute='_compute_lead_count',
        help='使用此来源的商机数量'
    )
    
    @api.depends('name')
    def _compute_lead_count(self):
        for source in self:
            source.lead_count = self.env['crm.lead'].search_count([
                ('lead_source_id', '=', source.id)
            ])
    
    @api.constrains('code')
    def _check_code_unique(self):
        for record in self:
            if record.code:
                domain = [('code', '=', record.code), ('id', '!=', record.id)]
                if self.search_count(domain):
                    raise ValidationError(_('来源ID必须唯一！'))
    
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.code:
                name = f'[{record.code}] {name}'
            result.append((record.id, name))
        return result
    
    def action_view_leads(self):
        """查看此来源的所有商机"""
        return {
            'name': _('商机: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'tree,form',
            'domain': [('lead_source_id', '=', self.id)],
            'context': {'default_lead_source_id': self.id},
        }