from odoo import models, fields, api, _

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    sale_request_id = fields.Many2one('sale.purchase.request', '销售请求', ondelete='set null')
    sale_order_id = fields.Many2one('sale.order', '源销售订单', related='sale_request_id.sale_order_id', store=True, readonly=True)
    
    @api.model
    def create_from_sale_request(self, request, supplier_id, lines=None):
        """从销售请求创建采购订单"""
        if not lines:
            lines = request.sale_line_ids
            
        # 检查是否已有该供应商的采购订单
        existing_po = self.search([
            ('sale_request_id', '=', request.id),
            ('partner_id', '=', supplier_id),
            ('state', 'in', ['draft', 'sent'])
        ], limit=1)
        
        if existing_po:
            po = existing_po
        else:
            # 使用销售订单的name作为源单据
            origin = request.sale_order_id.name if request.sale_order_id else request.name
            po_vals = {
                'partner_id': supplier_id,
                'sale_request_id': request.id,
                'origin': origin,
                'date_order': fields.Datetime.now(),
                'company_id': request.company_id.id,
            }
            po = self.create(po_vals)
        
        # 添加采购订单行
        for line in lines:
            if line.state == 'waiting' and line.sale_line_id:
                vals = {
                    'order_id': po.id,
                    'product_id': line.product_id.id,
                    'name': line.name or line.product_id.name,
                    'product_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'price_unit': 0.0,  # 由采购人员填写
                    'date_planned': fields.Datetime.now(),
                    'sale_line_id': line.sale_line_id.id,  # 关联销售订单行
                }
                po_line = self.env['purchase.order.line'].create(vals)
                
                # 更新请求行
                line.write({
                    'purchase_line_ids': [(4, po_line.id)],
                    'assigned_to_id': supplier_id,
                })
                
                # 更新采购订单行的多对多关系
                po_line.write({
                    'sale_request_line_ids': [(4, line.id)]
                })
        
        # 更新请求状态
        if all(line.state != 'waiting' for line in request.sale_line_ids):
            request.write({'state': 'purchasing'})
        
        # 确保销售订单行与采购订单行的关联关系
        request.update_sale_line_relations()
            
        return po
    
    def button_confirm(self):
        """确认采购订单时更新相关销售请求"""
        res = super(PurchaseOrder, self).button_confirm()
        
        for order in self:
            if order.sale_request_id:
                # 更新请求行状态
                for line in order.order_line:
                    request_lines = self.env['sale.purchase.request.line'].search([
                        ('purchase_line_ids', 'in', line.id)
                    ])
                    if request_lines:
                        request_lines.write({'state': 'purchased'})
                
                # 检查请求是否全部完成
                order.sale_request_id.check_done()
                
        return res
    
    def button_cancel(self):
        """取消采购订单时更新相关销售请求"""
        res = super(PurchaseOrder, self).button_cancel()
        
        for order in self:
            if order.sale_request_id:
                # 查找所有关联的请求行
                request_lines = self.env['sale.purchase.request.line'].search([
                    ('purchase_line_ids', 'in', order.order_line.ids)
                ])
                
                if request_lines:
                    # 触发相关计算字段的更新
                    for line in request_lines:
                        line.invalidate_recordset(['qty_purchased', 'qty_remaining'])
                    
                    # 等待计算字段更新后，再次读取以触发状态计算
                    # 这比手动调用计算方法更可靠，因为它会遵循Odoo的字段依赖关系
                    request_lines.read(['qty_purchased', 'qty_remaining', 'state'])
                
                # 确保请求单状态被重新计算
                request = order.sale_request_id
                request.invalidate_recordset(['state'])
                request.check_done()
                
        return res
    
    def _prepare_invoice(self):
        """准备供应商发票时关联销售请求"""
        invoice_vals = super(PurchaseOrder, self)._prepare_invoice()
        if self.sale_request_id:
            invoice_vals['sale_request_id'] = self.sale_request_id.id
        return invoice_vals


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    
    sale_request_line_id = fields.Many2one('sale.purchase.request.line', '销售请求行', deprecated=True)  # 已废弃，使用多对多关系
    sale_request_line_ids = fields.Many2many('sale.purchase.request.line', 'purchase_line_request_line_rel',
                                          'purchase_line_id', 'request_line_id', string='销售请求行')
    sale_line_id = fields.Many2one('sale.order.line', '销售订单行')
    
    def _prepare_stock_moves(self, picking):
        """准备库存移动时传递销售请求信息"""
        res = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
        
        for move_dict in res:
            # 不再传递 sale_request_line_id 字段，因为 stock.move 模型中不存在此字段
            if self.sale_line_id:
                move_dict['sale_line_id'] = self.sale_line_id.id
                
        return res
    
    @api.onchange('product_id')
    def onchange_product_id(self):
        result = super(PurchaseOrderLine, self).onchange_product_id()
        
        # 如果是从销售请求创建的采购订单行，保持数量不变
        if self.sale_request_line_id:
            self.product_qty = self.sale_request_line_id.product_uom_qty
            
        return result
    
    @api.model
    def create(self, vals):
        res = super(PurchaseOrderLine, self).create(vals)
        # 确保在创建采购订单行时，正确关联销售订单行
        if res.sale_line_id and not res.sale_line_id.purchase_line_ids.filtered(lambda l: l.id == res.id):
            # 这里利用 Odoo 17 原生的关联字段 purchase_line_ids
            # 确保销售订单行知道它被哪些采购订单行引用
            self.env['sale.order.line'].browse(res.sale_line_id.id).write({
                'purchase_line_ids': [(4, res.id)]
            })
        return res
    
    def _update_received_qty(self):
        """重写此方法，在收货数量更新时检查是否已完全收货"""
        super(PurchaseOrderLine, self)._update_received_qty()
        
        for line in self:
            # 检查是否存在对应的采购请求行
            request_lines = self.env['sale.purchase.request.line'].search([
                ('purchase_line_ids', 'in', line.id),
                ('state', '=', 'purchased')
            ])
            
            for request_line in request_lines:
                # 检查是否已完全收货
                if line.qty_received >= line.product_qty:
                    # 更新采购请求行状态为完成
                    request_line.write({'state': 'done'})
                    
                    # 检查整个采购请求是否可以标记为完成
                    if line.order_id.sale_request_id:
                        line.order_id.sale_request_id.check_done()