from odoo import api, fields, models, _

class SelectOrderLines(models.TransientModel):
    _name = "select.order.lines"
    _description = "选择订单行"

    line_ids = fields.Many2many(
        'sale.order.line',
        string="订单行",
        domain="[('order_id.partner_id', 'child_of', commercial_partner_id), ('product_id.type', '!=', 'service')]"
    )
    commercial_partner_id = fields.Many2one('res.partner', string="商业伙伴")
    manual_delivery_id = fields.Many2one('manual.delivery', string="手动发货向导")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        manual_delivery_id = self.env.context.get('active_id')
        if manual_delivery_id:
            manual_delivery = self.env['manual.delivery'].browse(manual_delivery_id)

            # 获取已添加的订单行ID
            existing_line_ids = manual_delivery.line_ids.mapped('order_line_id').ids

            # 获取符合条件的订单行
            domain = [
                ('order_id.partner_id', 'child_of', manual_delivery.commercial_partner_id.id),
                ('product_id.type', '!=', 'service'),
                ('id', 'not in', existing_line_ids)
            ]

            # 获取所有符合条件的订单行
            all_lines = self.env['sale.order.line'].search(domain)

            # 过滤出 qty_to_procure > 0 的行
            filtered_lines = all_lines.filtered(lambda l: l.qty_to_procure > 0)

            res['manual_delivery_id'] = manual_delivery_id
            res['commercial_partner_id'] = manual_delivery.commercial_partner_id.id
            res['line_ids'] = [(6, 0, filtered_lines.ids)]
        return res

    def add_lines(self):
        self.ensure_one()
        if not self.line_ids or not self.manual_delivery_id:
            return {'type': 'ir.actions.act_window_close'}

        # 准备要添加的行数据
        vals_list = []
        for line in self.line_ids:
            # 再次检查 qty_to_procure 是否大于 0
            if line.qty_to_procure <= 0:
                continue

            vals_list.append({
                'manual_delivery_id': self.manual_delivery_id.id,
                'order_line_id': line.id,
                'name': line.name,
                'product_id': line.product_id.id,
                'qty_ordered': line.product_uom_qty,
                'qty_procured': line.qty_procured,
                'quantity': line.qty_to_procure,
                'price_unit': line.price_unit,
            })

        # 创建新的manual.delivery.line记录
        if vals_list:
            self.env['manual.delivery.line'].create(vals_list)

        # 返回到原始向导
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'manual.delivery',
            'view_mode': 'form',
            'res_id': self.manual_delivery_id.id,
            'target': 'new',
            'context': self.env.context,
        }