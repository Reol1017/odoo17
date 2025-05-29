# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re

class WarehouseWeight(models.Model):
    _name = 'warehouse.weight'
    _description = '世仓重量表'
    _rec_name = 'name'  # 使用specification作为记录名称
    _order = 'product_id'  # 按产品ID排序
    
    specification = fields.Char(
        string='规格',
        compute='_compute_specification',
        store=True,
        index=True,
        help='自动生成的规格名称，格式为：高度-宽度，或单一规格'
    )
    
    name = fields.Char(string='型号', index=True)
    
    product_id = fields.Many2one('product.product', string='产品', required=True, index=True,
                               help='关联的产品')
    # 关联到产品类别的字段，只读模式
    product_categ_id = fields.Many2one('product.category', 
                                     string='产品类别', 
                                     related='product_id.categ_id',
                                     store=True,
                                     readonly=False,
                                     index=True)
    
    # 拆分的规格字段
    diameter = fields.Char(string='直径(D)', 
                         help='产品直径，例如：100mm',
                         placeholder="例如：100mm")
    height = fields.Char(string='高度(H)', 
                       help='产品高度，例如：200mm',
                       placeholder="例如：200mm")
    
    weight = fields.Float(string='重量', digits=(10, 2), help='单位：千克(kg)')
    notes = fields.Text(string='备注')
    active = fields.Boolean(default=True, string='有效',
                          help='如果取消勾选，此记录将从查询中隐藏，但仍然可以访问')
    
    @api.depends('diameter', 'height')
    def _compute_specification(self):
        for record in self:
            if record.height and record.diameter:
                # 两者都有，使用组合格式
                record.specification = f"{record.diameter}-{record.height}"
            elif record.height:
                # 只有高度
                record.specification = f"H:{record.height}"
            elif record.diameter:
                # 只有直径
                record.specification = f"D:{record.diameter}"
            else:
                # 都没有
                record.specification = False
    
    # 当选择产品时自动填充相关信息
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            # 自动填充重量
            if self.product_id.weight:
                self.weight = self.product_id.weight
            # 不需要手动设置 product_categ_id，因为它现在是 related 字段
    
    # 当修改产品类别时，更新产品的类别
    @api.onchange('product_categ_id')
    def _onchange_product_categ_id(self):
        if self.product_id and self.product_categ_id and self.product_id.categ_id != self.product_categ_id:
            # 由于我们将 product_categ_id 设置为 related 字段，
            # 这个 onchange 方法可能不再必要，但如果您想在界面上立即显示更改效果，可以保留
            self.product_id.categ_id = self.product_categ_id
    
    # 搜索功能
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, order=None, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', '|', '|', '|',
                     ('specification', operator, name),
                     ('product_id.name', operator, name),
                     ('name', operator, name),
                     ('diameter', operator, name),
                     ('height', operator, name),
                     ('product_categ_id.name', operator, name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
    
    def write(self, vals):
        """
        重写写入方法，确保关联关系得到正确处理
        """
        result = super(WarehouseWeight, self).write(vals)
        
        # 如果修改了产品类别，确保更新到产品
        if 'product_categ_id' in vals and not self._context.get('skip_warehouse_weight_update'):
            for record in self:
                if record.product_id and record.product_categ_id:
                    if record.product_id.categ_id.id != record.product_categ_id.id:
                        record.product_id.with_context(skip_warehouse_weight_update=True).write({
                            'categ_id': record.product_categ_id.id
                        })
        
        return result