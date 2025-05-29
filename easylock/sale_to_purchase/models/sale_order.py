from odoo import models, fields, api
from odoo.exceptions import UserError

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    origin_so_line = fields.Many2one(
        'sale.order.line', 
        string="来源销售订单行",
        index=True
    )

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    purchase_state = fields.Selection(
        selection=[
            ('all_purchased', '全部采购'),
            ('not_purchased', '未采购'), 
            ('partially_purchased', '部分采购'),
        ],
        string='采购状态',
        compute='_compute_purchase_state',
        store=True
    )
    
    def action_open_purchase_order_wizard(self):
        return {
            'name': '创建采购订单',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_order_id': self.id},
        }

    @api.depends('order_line.related_purchased_qty')
    def _compute_purchase_state(self):
        for order in self:
            total_purchased = sum(order.order_line.mapped('related_purchased_qty'))
            total_ordered = sum(order.order_line.mapped('product_uom_qty'))
            
            if total_purchased <= 0:
                state = 'not_purchased'
            elif total_purchased >= total_ordered:
                state = 'all_purchased'
            else:
                state = 'partially_purchased'
            order.purchase_state = state

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    related_po_lines = fields.One2many(
        'purchase.order.line', 
        'origin_so_line',
        string="关联采购订单行"
    )
    
    related_purchased_qty = fields.Float(
        string='已采购量',
        compute='_compute_purchased_qty',
        store=True,
        digits=(12, 0),
        compute_sudo=True  # 新增：解决权限问题
    )

    # 修改重点：只考虑采购订单状态
    @api.depends('related_po_lines.product_qty', 'related_po_lines.order_id.state')
    def _compute_purchased_qty(self):
        """根据采购订单状态计算已采购量"""
        for line in self:
            valid_orders = ['purchase', 'done']
            total = 0.0
            
            # 获取关联的有效采购订单行
            valid_lines = line.related_po_lines.filtered(
                lambda l: l.order_id.state in valid_orders
            )
            
            # 处理单位转换（采购单位 -> 销售单位）
            for pol in valid_lines:
                total += pol.product_uom._compute_quantity(
                    pol.product_qty,
                    line.product_uom
                )
                
            line.related_purchased_qty = total
