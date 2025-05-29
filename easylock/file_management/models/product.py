from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    document_ids = fields.One2many('document.document', 'product_id', string='相关文档')
    document_count = fields.Integer(compute='_compute_document_count', string='文档数量')
    
    drawing_ids = fields.One2many('document.drawing', 'product_id', string='相关图纸')
    drawing_count = fields.Integer(compute='_compute_drawing_count', string='图纸数量')
    
    contract_ids = fields.One2many('document.contract', 'product_id', string='相关合同')
    contract_count = fields.Integer(compute='_compute_contract_count', string='合同数量')
    
    def _compute_document_count(self):
        for product in self:
            product.document_count = self.env['document.document'].search_count([
                ('product_id', '=', product.id),
                ('is_drawing', '=', False),
                ('is_contract', '=', False)
            ])
    
    def _compute_drawing_count(self):
        for product in self:
            product.drawing_count = self.env['document.drawing'].search_count([
                ('product_id', '=', product.id)
            ])
    
    def _compute_contract_count(self):
        for product in self:
            product.contract_count = self.env['document.contract'].search_count([
                ('product_id', '=', product.id)
            ])
    
    def action_view_documents(self):
        self.ensure_one()
        return {
            'name': _('产品文档'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'view_mode': 'tree,form',
            'domain': [
                ('product_id', '=', self.id),
                ('is_drawing', '=', False),
                ('is_contract', '=', False)
            ],
            'context': {'default_product_id': self.id}
        }
    
    def action_view_drawings(self):
        self.ensure_one()
        return {
            'name': _('产品图纸'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.drawing',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id}
        }
    
    def action_view_contracts(self):
        self.ensure_one()
        return {
            'name': _('产品合同'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.contract',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id}
        }