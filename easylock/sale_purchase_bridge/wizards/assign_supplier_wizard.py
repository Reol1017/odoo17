from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SalePurchaseAssignSupplier(models.TransientModel):
    _name = 'sale.purchase.assign.supplier'
    _description = '分配供应商向导'
    
    request_line_id = fields.Many2one('sale.purchase.request.line', '请求行', required=True)
    supplier_id = fields.Many2one('res.partner', '供应商', required=True, 
                                  domain=[('supplier_rank', '>', 0), ('is_company', '=', True)])
    product_id = fields.Many2one('product.product', '产品', related='request_line_id.product_id', readonly=True)
    
    # 修改字段定义，支持指定采购数量
    total_quantity = fields.Float('总数量', related='request_line_id.product_uom_qty', readonly=True)
    purchased_quantity = fields.Float('已采购数量', related='request_line_id.qty_purchased', readonly=True)
    remaining_quantity = fields.Float('剩余数量', related='request_line_id.qty_remaining', readonly=True)
    quantity = fields.Float('本次采购数量', required=True)
    
    # 添加采购状态选择
    purchase_state = fields.Selection([
        ('rfq', '询价'),
        ('purchase', '确认订单')
    ], string='采购状态', default='rfq', required=True)
    
    @api.onchange('request_line_id')
    def _onchange_request_line_id(self):
        if self.request_line_id:
            # 获取产品的主供应商
            if self.request_line_id.product_id.seller_ids:
                self.supplier_id = self.request_line_id.product_id.seller_ids[0].partner_id
            
            # 设置默认采购数量为剩余数量，从数据库重新获取
            request_line = self.env['sale.purchase.request.line'].browse(self.request_line_id.id)
            self.quantity = request_line.qty_remaining
    
    @api.onchange('quantity')
    def _onchange_quantity(self):
        """验证数量不能超过剩余数量"""
        if self.quantity <= 0:
            return {'warning': {'title': _('警告'), 'message': _('采购数量必须大于0')}}
            
        # 获取最新的剩余数量，避免使用缓存值
        remaining_qty = 0
        if self.request_line_id:
            request_line = self.env['sale.purchase.request.line'].browse(self.request_line_id.id)
            remaining_qty = request_line.qty_remaining
            
        if self.quantity > remaining_qty:
            self.quantity = remaining_qty
            return {'warning': {'title': _('警告'), 'message': _('采购数量不能超过剩余数量 %.2f') % remaining_qty}}
    
    def action_confirm(self):
        self.ensure_one()
        
        # 检查数量
        if self.quantity <= 0:
            raise UserError(_('采购数量必须大于0'))
            
        # 重新读取最新剩余数量，确保使用最新计算值
        self.request_line_id.invalidate_recordset(['qty_remaining'])
        remaining_qty = self.request_line_id.qty_remaining
        
        if self.quantity > remaining_qty:
            raise UserError(_('采购数量不能超过剩余数量 %.2f') % remaining_qty)
            
        # 创建采购订单
        request = self.request_line_id.request_id
        
        # 检查是否已有该供应商的采购订单
        existing_po = self.env['purchase.order'].search([
            ('sale_request_id', '=', request.id),
            ('partner_id', '=', self.supplier_id.id),
            ('state', 'in', ['draft', 'sent'])
        ], limit=1)
        
        if existing_po:
            po = existing_po
        else:
            # 使用销售订单的name作为源单据
            origin = request.sale_order_id.name if request.sale_order_id else request.name
            po_vals = {
                'partner_id': self.supplier_id.id,
                'sale_request_id': request.id,
                'origin': origin,
                'date_order': fields.Datetime.now(),
                'company_id': request.company_id.id,
                'notes':request.notes,
            }
            po = self.env['purchase.order'].create(po_vals)
            
        # 创建采购订单行
        po_line_vals = {
            'order_id': po.id,
            'product_id': self.request_line_id.product_id.id,
            'name': self.request_line_id.name or self.request_line_id.product_id.name,
            'product_qty': self.quantity,  # 使用指定的数量
            'product_uom': self.request_line_id.product_uom.id,
            'date_planned': fields.Datetime.now(),
            'sale_line_id': self.request_line_id.sale_line_id.id,  # 关联销售订单行
        }
        po_line = self.env['purchase.order.line'].create(po_line_vals)
        
        # 更新请求行，添加到多对多关系中
        self.request_line_id.write({
            'purchase_line_ids': [(4, po_line.id)],
        })
        
        # 同时更新采购订单行的多对多关系
        po_line.write({
            'sale_request_line_ids': [(4, self.request_line_id.id)]
        })
        
        # 如果选择直接确认订单
        if self.purchase_state == 'purchase':
            po.button_confirm()
        
        # 强制触发请求单状态重新计算
        request.invalidate_recordset(['state'])
        request.check_done()
        
        # 打开采购订单
        return {
            'name': _('采购订单'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': po.id,
            'target': 'current',
        }

class SalePurchaseCreatePOLine(models.TransientModel):
    _name = 'sale.purchase.create.po.line'
    _description = '创建采购订单向导行'
    
    wizard_id = fields.Many2one('sale.purchase.create.po', string='向导', ondelete='cascade')
    request_line_id = fields.Many2one('sale.purchase.request.line', string='请求行', required=True)
    product_id = fields.Many2one('product.product', string='产品', related='request_line_id.product_id', readonly=True)
    name = fields.Text('描述', related='request_line_id.name', readonly=True)
    product_uom_qty = fields.Float('总数量', related='request_line_id.product_uom_qty', readonly=True)
    qty_purchased = fields.Float('已采购数量', related='request_line_id.qty_purchased', readonly=True)
    qty_remaining = fields.Float('剩余数量', related='request_line_id.qty_remaining', readonly=True)
    product_uom = fields.Many2one('uom.uom', string='单位', related='request_line_id.product_uom', readonly=True)
    quantity = fields.Float('本次采购数量', required=True)
    
    @api.onchange('request_line_id')
    def _onchange_request_line_id(self):
        if self.request_line_id:
            # 获取最新剩余数量
            request_line = self.env['sale.purchase.request.line'].browse(self.request_line_id.id)
            self.quantity = request_line.qty_remaining
    
    @api.onchange('quantity')
    def _onchange_quantity(self):
        """验证数量不能超过剩余数量"""
        if self.quantity <= 0:
            return {'warning': {'title': _('警告'), 'message': _('采购数量必须大于0')}}
            
        # 获取最新的剩余数量
        remaining_qty = 0
        if self.request_line_id:
            request_line = self.env['sale.purchase.request.line'].browse(self.request_line_id.id)
            remaining_qty = request_line.qty_remaining
            
        if self.quantity > remaining_qty:
            self.quantity = remaining_qty
            return {'warning': {'title': _('警告'), 'message': _('采购数量不能超过剩余数量 %.2f') % remaining_qty}}


class SalePurchaseCreatePO(models.TransientModel):
    _name = 'sale.purchase.create.po'
    _description = '创建采购订单向导'
    
    request_id = fields.Many2one('sale.purchase.request', '采购请求', required=True)
    line_ids = fields.One2many('sale.purchase.create.po.line', 'wizard_id', string='请求行')
    supplier_id = fields.Many2one('res.partner', '供应商', required=True,
                                 domain=[('supplier_rank', '>', 0), ('is_company', '=', True)])
    # 添加采购状态选择
    purchase_state = fields.Selection([
        ('rfq', '询价'),
        ('purchase', '确认订单')
    ], string='采购状态', default='rfq', required=True)
    
    @api.model
    def default_get(self, fields):
        res = super(SalePurchaseCreatePO, self).default_get(fields)
        
        if 'request_id' in res and res['request_id']:
            request = self.env['sale.purchase.request'].browse(res['request_id'])
            
            # 尝试找到常用供应商
            suppliers = []
            for line in request.sale_line_ids:
                if line.product_id and line.product_id.seller_ids:
                    for seller in line.product_id.seller_ids:
                        if seller.partner_id:
                            suppliers.append(seller.partner_id)
            
            if suppliers:
                res['supplier_id'] = suppliers[0].id
                
            # 处理默认的请求行
            if 'line_ids' in fields and 'default_line_ids' in self._context:
                request_lines = self.env['sale.purchase.request.line'].browse(self._context['default_line_ids'][0][2])
                
                # 确保获取最新的剩余数量
                request_lines.invalidate_recordset(['qty_remaining'])
                
                wizard_lines = []
                for line in request_lines:
                    if line.qty_remaining > 0:
                        wizard_lines.append((0, 0, {
                            'request_line_id': line.id,
                            'quantity': line.qty_remaining,
                        }))
                res['line_ids'] = wizard_lines
                
        return res
    
    def action_confirm(self):
        self.ensure_one()
        
        if not self.line_ids:
            raise UserError(_('请选择至少一个请求行'))
        
        # 创建采购订单
        request = self.request_id
        
        # 检查是否已有该供应商的采购订单
        existing_po = self.env['purchase.order'].search([
            ('sale_request_id', '=', request.id),
            ('partner_id', '=', self.supplier_id.id),
            ('state', 'in', ['draft', 'sent'])
        ], limit=1)
        
        if existing_po:
            po = existing_po
        else:
            # 使用销售订单的name作为源单据
            origin = request.sale_order_id.name if request.sale_order_id else request.name
            po_vals = {
                'partner_id': self.supplier_id.id,
                'sale_request_id': request.id,
                'origin': origin,
                'date_order': fields.Datetime.now(),
                'company_id': request.company_id.id,
                'notes': request.notes, 
            }
            po = self.env['purchase.order'].create(po_vals)
        
        # 为每个请求行创建采购订单行
        updated_request_lines = self.env['sale.purchase.request.line']
        for wizard_line in self.line_ids:
            # 检查数量
            if wizard_line.quantity <= 0:
                raise UserError(_('产品 %s 的采购数量必须大于0') % wizard_line.product_id.name)
            
            # 重新获取最新的剩余数量
            line = wizard_line.request_line_id
            line.invalidate_recordset(['qty_remaining'])
            
            if wizard_line.quantity > line.qty_remaining:
                raise UserError(_('产品 %s 的采购数量不能超过剩余数量 %.2f') % (
                    line.product_id.name, line.qty_remaining))
                
            po_line_vals = {
                'order_id': po.id,
                'product_id': line.product_id.id,
                'name': line.name or line.product_id.name,
                'product_qty': wizard_line.quantity,  # 使用用户指定的数量
                'product_uom': line.product_uom.id,
                'date_planned': fields.Datetime.now(),
                'sale_line_id': line.sale_line_id.id,  # 关联销售订单行
            }
            po_line = self.env['purchase.order.line'].create(po_line_vals)
            
            # 更新请求行，添加到多对多关系中
            line.write({
                'purchase_line_ids': [(4, po_line.id)],
            })
            
            # 同时更新采购订单行的多对多关系
            po_line.write({
                'sale_request_line_ids': [(4, line.id)]
            })
            
            updated_request_lines |= line
        
        # 如果选择直接确认订单
        if self.purchase_state == 'purchase':
            po.button_confirm()
        
        # 强制触发请求单状态重新计算
        request.invalidate_recordset(['state'])
        request.check_done()
        
        # 打开采购订单
        return {
            'name': _('采购订单'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': po.id,
            'target': 'current',
        }