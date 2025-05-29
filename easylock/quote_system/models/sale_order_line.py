from odoo import models, fields, api, _
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    # 颜色字段，关联到颜色模型
    product_color_id = fields.Many2one(
        'product.color',
        string='颜色',
        help='产品颜色'
    )
    # 直径字段，关联到世仓重量表
    product_diameter = fields.Char(
        string='直径(D)',
        help='产品直径'
    )
    # 高度字段，关联到世仓重量表
    product_height = fields.Char(
        string='高度(H)',
        help='产品高度'
    )
    # 关联的世仓重量表记录
    warehouse_weight_id = fields.Many2one(
        'warehouse.weight',
        string='重量表型号',
        domain="[('product_id', '=', product_id)]"
    )
    # 添加一个存储字段用于显示重量
    weight_factor = fields.Float(
        string='重量系数',
        compute='_compute_weight_factor',
        store=True,
        help='从世仓规格获取的重量系数'
    )
    
    # 新增重量单价字段
    weight_unit_price = fields.Float(
        string='重量单价',
        digits='Product Price',
        help='按重量计算的单价'
    )
    
    # 修改原有单价字段，使其计算并且不可编辑
    price_unit = fields.Float(
        string='产品单价',
        compute='_compute_price_unit',
        store=True,
        digits='Product Price',
        help='基于重量单价计算的产品单价'
    )
    
    # 计算单价的方法
    @api.depends('weight_unit_price', 'weight_factor')
    def _compute_price_unit(self):
        for line in self:
            weight_factor = line.weight_factor if line.weight_factor else 1.0
            line.price_unit = line.weight_unit_price * weight_factor
    
    # 计算重量系数
    @api.depends('warehouse_weight_id')
    def _compute_weight_factor(self):
        for line in self:
            if line.warehouse_weight_id and line.warehouse_weight_id.weight:
                line.weight_factor = line.warehouse_weight_id.weight
            else:
                line.weight_factor = 1.0  # 默认为1，不影响计算
    
    # 重写计算金额的方法，考虑重量因素
    @api.depends('product_uom_qty', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        计算金额的方法，使总价 = 数量 × 单价
        单价已经包含了重量因素：单价 = 重量单价 × 重量系数
        """
        for line in self:
            # 对于描述行或节标题行，金额为0
            if line.display_type:
                line.price_subtotal = 0.0
                line.price_tax = 0.0
                line.price_total = 0.0
                continue
            
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            quantity = line.product_uom_qty or 0.0
            
            # 计算基础金额（不含税）
            subtotal = price * quantity
            
            # 计算税额
            taxes = line.tax_id.compute_all(
                price_unit=price,
                currency=line.order_id.currency_id,
                quantity=quantity,
                product=line.product_id,
                partner=line.order_id.partner_shipping_id or line.order_id.partner_id
            )
            
            # 设置金额字段
            line.update({
                'price_subtotal': taxes['total_excluded'],
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
            })
            
            # 如果是外币，转换为公司币种
            if line.order_id.currency_id and line.order_id.company_id and line.order_id.currency_id != line.order_id.company_id.currency_id:
                line.price_subtotal = line.order_id.currency_id._convert(
                    line.price_subtotal,
                    line.order_id.company_id.currency_id,
                    line.order_id.company_id,
                    line.order_id.date_order or fields.Date.today()
                )
    
    # 当产品变更时，清空相关规格字段
    @api.onchange('product_id')
    def _onchange_product_id_for_weight(self):
        if self.product_id:
            self.warehouse_weight_id = False
            self.product_diameter = False
            self.product_height = False
            self.weight_factor = 1.0  # 重置重量系数
    
    # 当选择世仓重量表记录时，自动填充直径和高度
    @api.onchange('warehouse_weight_id')
    def _onchange_warehouse_weight_id(self):
        if self.warehouse_weight_id:
            self.product_diameter = self.warehouse_weight_id.diameter
            self.product_height = self.warehouse_weight_id.height
            self.weight_factor = self.warehouse_weight_id.weight or 1.0
            # 通过更新weight_factor，会触发price_unit的重新计算