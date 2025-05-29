from odoo import models, fields

class Color(models.Model):
    _name = 'product.color'
    _description = '颜色模型'

    name = fields.Char(string='颜色', required=True)
    notes = fields.Text(string='备注', help='颜色的附加说明信息')