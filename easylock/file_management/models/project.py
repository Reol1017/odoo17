from odoo import models, fields, api, _

class Project(models.Model):
    _inherit = 'project.project'
    
    document_ids = fields.One2many('document.document', 'project_id', string='相关文档')
    document_count = fields.Integer(compute='_compute_document_count', string='文档数量')
    
    drawing_ids = fields.One2many('document.drawing', 'project_id', string='相关图纸')
    drawing_count = fields.Integer(compute='_compute_drawing_count', string='图纸数量')
    
    contract_ids = fields.One2many('document.contract', 'project_id', string='相关合同')
    contract_count = fields.Integer(compute='_compute_contract_count', string='合同数量')
    
    def _compute_document_count(self):
        for project in self:
            project.document_count = self.env['document.document'].search_count([
                ('project_id', '=', project.id),
                ('is_drawing', '=', False),
                ('is_contract', '=', False)
            ])
    
    def _compute_drawing_count(self):
        for project in self:
            project.drawing_count = self.env['document.drawing'].search_count([
                ('project_id', '=', project.id)
            ])
    
    def _compute_contract_count(self):
        for project in self:
            project.contract_count = self.env['document.contract'].search_count([
                ('project_id', '=', project.id)
            ])
    
    def action_view_documents(self):
        self.ensure_one()
        return {
            'name': _('项目文档'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'view_mode': 'tree,form',
            'domain': [
                ('project_id', '=', self.id),
                ('is_drawing', '=', False),
                ('is_contract', '=', False)
            ],
            'context': {'default_project_id': self.id}
        }
    
    def action_view_drawings(self):
        self.ensure_one()
        return {
            'name': _('项目图纸'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.drawing',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id}
        }
    
    def action_view_contracts(self):
        self.ensure_one()
        return {
            'name': _('项目合同'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.contract',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id}
        }

class Task(models.Model):
    _inherit = 'project.task'
    
    document_ids = fields.Many2many('document.document', string='相关文档')
    document_count = fields.Integer(compute='_compute_document_count', string='文档数量')
    
    def _compute_document_count(self):
        for task in self:
            task.document_count = len(task.document_ids)
    
    def action_view_documents(self):
        self.ensure_one()
        return {
            'name': _('任务文档'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.document_ids.ids)],
            'context': {'default_task_ids': [(6, 0, [self.id])]}
        }