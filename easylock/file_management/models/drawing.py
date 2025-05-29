from odoo import models, fields, api, _

class Drawing(models.Model):
    _name = 'document.drawing'
    _description = '技术图纸'
    _inherits = {'document.document': 'document_id'}
    
    document_id = fields.Many2one('document.document', string='基础文档', required=True, ondelete='cascade')
    sale_order_ids = fields.Many2many('sale.order', string='相关销售订单')
    sale_line_ids = fields.One2many('sale.order.line', 'drawing_id', string='销售订单行')
    
    # 图纸特有字段
    drawing_type = fields.Selection([
        ('assembly', '装配图'),
        ('part', '零件图'),
        ('electrical', '电气图'),
        ('mechanical', '机械图'),
        ('schematic', '原理图'),
        ('layout', '布局图'),
        ('other', '其他')
    ], string='图纸类型')
    
    scale = fields.Char('比例')
    paper_size = fields.Selection([
        ('A0', 'A0'),
        ('A1', 'A1'),
        ('A2', 'A2'),
        ('A3', 'A3'),
        ('A4', 'A4'),
        ('custom', '自定义')
    ], string='纸张尺寸')
    
    custom_size = fields.Char('自定义尺寸')
    
    # 添加继承方法，确保子模型可以访问父模型的方法
    def action_submit(self):
        return self.document_id.action_submit()
    
    def action_approve(self):
        return self.document_id.action_approve()
    
    def action_reject(self):
        return self.document_id.action_reject()
    
    def action_archive(self):
        return self.document_id.action_archive()
    
    def action_draft(self):
        return self.document_id.action_draft()
    
    def action_create_new_version(self):
        return self.document_id.action_create_new_version()
    
    @api.model_create_multi
    def create(self, vals_list):
        # 确保在创建图纸时，文档类别被设置为图纸类别
        for vals in vals_list:
            if 'category_id' in vals:
                category = self.env['document.category'].browse(vals['category_id'])
                if not category.is_drawing:
                    # 查找图纸类别，没有则创建
                    drawing_category = self.env['document.category'].search([('is_drawing', '=', True)], limit=1)
                    if not drawing_category:
                        drawing_category = self.env['document.category'].create({
                            'name': '技术图纸',
                            'code': 'DRW',
                            'is_drawing': True
                        })
                    vals['category_id'] = drawing_category.id
            
            # 确保文件类型合适
            if vals.get('file_type') not in ['cad', 'pdf', 'img']:
                vals['file_type'] = 'cad'
                
        return super().create(vals_list)