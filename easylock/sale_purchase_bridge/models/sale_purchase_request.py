from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class SalePurchaseRequest(models.Model):
    _name = 'sale.purchase.request'
    _description = '销售采购请求'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_request desc'
    
    name = fields.Char('参考编号', required=True, copy=False, readonly=True, index=True, default=lambda self: _('新请求'))
    sale_order_id = fields.Many2one('sale.order', '销售订单', readonly=True, index=True)
    sale_line_ids = fields.One2many('sale.purchase.request.line', 'request_id', '销售订单行')
    state = fields.Selection([
        ('draft', '草稿'),
        ('waiting', '等待采购处理'),
        ('purchasing', '采购中'),
        ('purchased', '采购完成'),
        ('done', '已完成'),
        ('cancel', '已取消')
    ], string='状态', default='draft', tracking=True)
    requester_id = fields.Many2one('res.users', '请求人', readonly=True, default=lambda self: self.env.user)
    date_request = fields.Datetime('请求日期', default=fields.Datetime.now, readonly=True)
    purchase_ids = fields.One2many('purchase.order', 'sale_request_id', '相关采购订单')
    purchase_count = fields.Integer('采购订单数', compute='_compute_purchase_count')
    company_id = fields.Many2one('res.company', '公司', required=True, default=lambda self: self.env.company)
    notes = fields.Html('备注')
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('新请求')) == _('新请求'):
            vals['name'] = self.env['ir.sequence'].next_by_code('sale.purchase.request') or _('新请求')
        return super(SalePurchaseRequest, self).create(vals)
    
    def _compute_purchase_count(self):
        for record in self:
            record.purchase_count = len(record.purchase_ids)
    
    def action_view_purchase_orders(self):
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        if len(self.purchase_ids) > 1:
            action['domain'] = [('id', 'in', self.purchase_ids.ids)]
        elif len(self.purchase_ids) == 1:
            action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            action['res_id'] = self.purchase_ids.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    
    def action_confirm(self):
        for record in self:
            if record.state == 'draft':
                record.write({'state': 'waiting'})
                # 发送通知
                self._notify_purchase_team()
    
    def action_cancel(self):
        for record in self:
            if record.state not in ['done', 'cancel']:
                record.write({'state': 'cancel'})
                # 可能需要取消相关采购订单
                for po in record.purchase_ids.filtered(lambda p: p.state in ['draft', 'sent']):
                    po.button_cancel()
    
    def action_reset_to_draft(self):
        """将请求重置为草稿状态"""
        for record in self:
            if record.state in ['waiting', 'cancel', 'purchasing', 'purchased']:
                # 检查关联的采购订单
                draft_pos = record.purchase_ids.filtered(lambda p: p.state in ['draft', 'sent'])
                if draft_pos:
                    # 如果有草稿状态的采购订单，建议用户先处理
                    message = _('此请求有 %s 个草稿状态的采购订单，建议先取消这些采购订单。') % len(draft_pos)
                    record.message_post(
                        body=message,
                        subtype_id=self.env.ref('mail.mt_note').id
                    )
                
                # 重置为草稿状态
                record.write({'state': 'draft'})
                
                # 通知相关人员
                record.message_post(
                    body=_('请求已重置为草稿状态'),
                    subtype_id=self.env.ref('mail.mt_note').id
                )
    
    def _notify_purchase_team(self):
        self.ensure_one()
        # 获取采购用户组的所有用户
        purchase_users = self.env.ref('purchase.group_purchase_user').users
        
        if purchase_users:
            # 创建通知消息
            note = _('来自销售订单 %s 的新采购请求需要处理') % self.sale_order_id.name
            self.message_post(
                body=note,
                partner_ids=purchase_users.mapped('partner_id').ids,
                subtype_id=self.env.ref('mail.mt_note').id,
                author_id=self.env.user.partner_id.id,
                message_type='notification'
            )
            
            # 创建活动
            for user in purchase_users:
                self.env['mail.activity'].create({
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'note': note,
                    'res_id': self.id,
                    'res_model_id': self.env['ir.model']._get('sale.purchase.request').id,
                    'user_id': user.id,
                    'summary': _('处理销售采购请求')
                })
    
    def action_create_purchase_orders(self):
        """创建采购订单的向导"""
        self.ensure_one()
        
        # 获取有剩余数量的请求行
        unassigned_lines = self.sale_line_ids.filtered(lambda l: l.qty_remaining > 0.001)
        
        if not unassigned_lines:
            raise UserError(_('没有待处理的采购请求行'))
            
        return {
            'name': _('创建采购订单'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.purchase.create.po',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_line_ids': [(6, 0, unassigned_lines.ids)]
            }
        }
    
    def check_done(self):
        """根据请求行状态更新请求单状态"""
        self.ensure_one()
        
        if not self.sale_line_ids:
            return False
            
        # 避免递归计算
        if self.env.context.get('skip_line_recompute'):
            return False
            
        # 获取所有请求行的状态
        line_states = self.sale_line_ids.mapped('state')
        
        # 检查是否有剩余采购数量
        has_remaining_qty = any(line.qty_remaining > 0.001 for line in self.sale_line_ids)
        
        # 状态更新逻辑
        if all(state == 'done' for state in line_states):
            # 所有请求行都已完成收货
            if self.state != 'done':
                self.write({'state': 'done'})
                return True
        elif all(state in ['purchased', 'done'] for state in line_states) and not has_remaining_qty:
            # 所有请求行都已采购完成（可能部分已收货）且没有剩余数量
            if self.state != 'purchased':
                self.write({'state': 'purchased'})
                return True
        elif any(state in ['partial', 'purchased', 'done'] for state in line_states) or has_remaining_qty:
            # 至少有一行处于采购中/已采购状态，或有剩余采购数量
            if self.state not in ['purchasing', 'purchased', 'done']:
                self.write({'state': 'purchasing'})
                return True
        elif all(state == 'waiting' for state in line_states):
            # 所有行都在等待处理
            if self.state not in ['waiting', 'draft']:
                self.write({'state': 'waiting'})
                return True
                
        return False
        
    def update_sale_line_relations(self):
        """更新销售订单行与采购订单行的关联关系"""
        for request in self:
            for line in request.sale_line_ids:
                if line.purchase_line_ids and line.sale_line_id:
                    # 确保每个采购订单行都正确关联到销售订单行
                    for purchase_line in line.purchase_line_ids:
                        # 设置采购订单行的sale_line_id字段
                        if purchase_line.sale_line_id.id != line.sale_line_id.id:
                            purchase_line.sale_line_id = line.sale_line_id.id
                        
                        # 确保销售订单行的purchase_line_ids包含此采购订单行
                        if not line.sale_line_id.purchase_line_ids.filtered(lambda l: l.id == purchase_line.id):
                            self.env['sale.order.line'].browse(line.sale_line_id.id).write({
                                'purchase_line_ids': [(4, purchase_line.id)]
                            })


class SalePurchaseRequestLine(models.Model):
    _name = 'sale.purchase.request.line'
    _description = '销售采购请求行'
    
    request_id = fields.Many2one('sale.purchase.request', '请求', ondelete='cascade')
    sale_line_id = fields.Many2one('sale.order.line', '销售订单行', ondelete='cascade')
    product_id = fields.Many2one('product.product', '产品', required=True)
    name = fields.Text('描述')
    product_uom_qty = fields.Float('数量', required=True, default=1.0)
    product_uom = fields.Many2one('uom.uom', '单位')
    price_unit = fields.Float('单价', deprecated=True)  # 标记为已废弃，不再使用
    purchase_line_ids = fields.Many2many('purchase.order.line', 'purchase_line_request_line_rel', 
                                        'request_line_id', 'purchase_line_id', string='采购订单行')
    purchase_orders = fields.Many2many('purchase.order', string='采购订单', compute='_compute_purchase_orders', store=True)
    purchase_line_id = fields.Many2one('purchase.order.line', '主采购订单行', compute='_compute_main_purchase_line', store=True)
    purchase_order_id = fields.Many2one('purchase.order', '主采购订单', related='purchase_line_id.order_id', store=True)
    
    qty_purchased = fields.Float('已采购数量', compute='_compute_qty_purchased', store=True)
    qty_remaining = fields.Float('剩余数量', compute='_compute_qty_remaining', store=True)
    
    state = fields.Selection([
        ('waiting', '等待处理'),
        ('partial', '部分采购'),
        ('purchased', '采购完成'),
        ('done', '已完成')
    ], string='状态', default='waiting', compute='_compute_state', store=True)
    
    @api.depends('purchase_line_ids')
    def _compute_purchase_orders(self):
        for line in self:
            line.purchase_orders = line.purchase_line_ids.mapped('order_id')
    
    @api.depends('purchase_line_ids')
    def _compute_main_purchase_line(self):
        """计算主采购订单行，用于兼容性"""
        for line in self:
            line.purchase_line_id = line.purchase_line_ids[0] if line.purchase_line_ids else False
    
    @api.depends('purchase_line_ids', 'purchase_line_ids.product_qty', 'purchase_line_ids.state', 
                'purchase_line_ids.order_id.state', 'product_uom_qty')
    def _compute_qty_purchased(self):
        """计算已采购数量 - 只计算已确认订单的数量"""
        for line in self:
            # 只统计状态为已确认(purchase/done)且未取消(cancel)的采购订单行
            confirmed_lines = line.purchase_line_ids.filtered(
                lambda pl: pl.state in ['purchase', 'done'] and pl.order_id.state != 'cancel'
            )
            line.qty_purchased = sum(confirmed_lines.mapped('product_qty'))
    
    @api.depends('product_uom_qty', 'qty_purchased')
    def _compute_qty_remaining(self):
        """计算剩余需要采购的数量"""
        for line in self:
            line.qty_remaining = max(0, line.product_uom_qty - line.qty_purchased)
    
    @api.depends('purchase_line_ids', 'purchase_line_ids.state', 'purchase_line_ids.qty_received', 
                'purchase_line_ids.order_id.state', 'qty_purchased', 'product_uom_qty', 'qty_remaining')
    def _compute_state(self):
        """计算状态 - 更加严谨的实现"""
        for line in self:
            # 如果没有关联采购订单行，则状态为等待处理
            if not line.purchase_line_ids:
                line.state = 'waiting'
                continue
                
            # 计算已采购的有效数量（只考虑已确认且未取消的采购订单行）
            confirmed_lines = line.purchase_line_ids.filtered(
                lambda pl: pl.state in ['purchase', 'done'] and pl.order_id.state != 'cancel'
            )
            if not confirmed_lines:
                # 如果没有已确认的采购订单行，检查是否有询价单
                if line.purchase_line_ids.filtered(lambda pl: pl.state in ['draft', 'sent'] and pl.order_id.state != 'cancel'):
                    line.state = 'partial'  # 有询价单但未确认
                else:
                    line.state = 'waiting'  # 没有有效的采购订单行
                continue
            
            # 使用已计算的字段值，这些字段已经考虑了采购订单状态
            if line.qty_remaining > 0.001:  # 使用微小的误差值来处理浮点数计算误差
                # 仍有数量未采购，状态为部分采购
                line.state = 'partial'
            else:
                # 所有数量都已采购，检查收货情况
                # 计算已确认采购订单行的收货数量
                received_qty = sum(confirmed_lines.mapped('qty_received'))
                
                if received_qty >= line.product_uom_qty:
                    # 所有数量都已收货，状态为已完成
                    line.state = 'done'
                else:
                    # 采购完成但尚未全部收货
                    line.state = 'purchased'
            
            # 状态变化后更新请求单状态
            if line.request_id and not self.env.context.get('skip_request_state_update'):
                line.request_id.with_context(skip_line_recompute=True).check_done()
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            self.product_uom = self.product_id.uom_id
            
    @api.onchange('sale_line_id')
    def _onchange_sale_line_id(self):
        if self.sale_line_id:
            self.product_id = self.sale_line_id.product_id
            self.name = self.sale_line_id.name
            self.product_uom_qty = self.sale_line_id.product_uom_qty
            self.product_uom = self.sale_line_id.product_uom
            
    @api.model
    def create(self, vals):
        res = super(SalePurchaseRequestLine, self).create(vals)
        if res.sale_line_id and res.purchase_line_ids:
            for purchase_line in res.purchase_line_ids:
                purchase_line.sale_line_id = res.sale_line_id.id
        return res
        
    def write(self, vals):
        res = super(SalePurchaseRequestLine, self).write(vals)
        
        # 如果修改了可能影响状态的字段，则检查更新请求单状态
        state_affecting_fields = ['purchase_line_ids', 'product_uom_qty', 'qty_purchased', 'qty_remaining', 'state']
        if any(field in vals for field in state_affecting_fields) and self:
            # 获取所有相关的请求单
            requests = self.mapped('request_id')
            for request in requests:
                if request:
                    request.with_context(skip_line_recompute=True).check_done()
        
        # 处理销售行与采购行的关联关系
        if 'purchase_line_ids' in vals:
            for record in self:
                if record.sale_line_id:
                    for purchase_line in record.purchase_line_ids:
                        if purchase_line.sale_line_id.id != record.sale_line_id.id:
                            purchase_line.sale_line_id = record.sale_line_id.id
                    
                    for purchase_line in record.purchase_line_ids:
                        if not record.sale_line_id.purchase_line_ids.filtered(lambda l: l.id == purchase_line.id):
                            self.env['sale.order.line'].browse(record.sale_line_id.id).write({
                                'purchase_line_ids': [(4, purchase_line.id)]
                            })
        return res