from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    purchase_request_ids = fields.One2many('sale.purchase.request', 'sale_order_id', '采购请求')
    purchase_request_count = fields.Integer('采购请求数', compute='_compute_purchase_request_count')
    
    @api.depends('purchase_request_ids')
    def _compute_purchase_request_count(self):
        for order in self:
            order.purchase_request_count = len(order.purchase_request_ids)
    
    def action_view_purchase_requests(self):
        self.ensure_one()
        action = self.env.ref('sale_purchase_bridge.action_sale_purchase_requests').read()[0]
        if len(self.purchase_request_ids) > 1:
            action['domain'] = [('id', 'in', self.purchase_request_ids.ids)]
        elif len(self.purchase_request_ids) == 1:
            action['views'] = [(self.env.ref('sale_purchase_bridge.view_sale_purchase_request_form').id, 'form')]
            action['res_id'] = self.purchase_request_ids.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    
    def action_request_purchase(self):
        """创建采购请求并打开分配采购员向导"""
        self.ensure_one()
        
        # 检查是否有可采购的产品
        purchase_lines = self.order_line.filtered(lambda l: l.product_id.type in ['product', 'consu'])
        
        if not purchase_lines:
            raise UserError(_('没有可采购的产品行'))
        
        # 创建采购请求
        request_vals = {
            'sale_order_id': self.id,
            'requester_id': self.env.user.id,
            'name': self.name + '/PR',
            'state': 'draft',
            'notes':self.note,
        }
        
        request_line_vals = []
        for line in purchase_lines:
            request_line_vals.append((0, 0, {
                'sale_line_id': line.id,
                'product_id': line.product_id.id,
                'name': line.name,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': line.product_uom.id,
            }))
            
        if request_line_vals:
            request_vals['sale_line_ids'] = request_line_vals
            request = self.env['sale.purchase.request'].create(request_vals)
            
            # 打开分配采购员向导，而不是直接确认请求
            return {
                'name': _('分配采购员'),
                'type': 'ir.actions.act_window',
                'res_model': 'assign.purchaser.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'active_id': request.id,
                    'active_model': 'sale.purchase.request'
                }
            }
            
        return True


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    purchase_line_ids = fields.One2many('purchase.order.line', 'sale_line_id', string='采购订单行')
    purchase_line_count = fields.Integer(string='采购行数量', compute='_compute_purchase_line_count')
    
    @api.depends('purchase_line_ids')
    def _compute_purchase_line_count(self):
        for line in self:
            line.purchase_line_count = len(line.purchase_line_ids)