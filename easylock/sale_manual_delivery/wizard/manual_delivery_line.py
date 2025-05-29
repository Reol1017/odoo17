from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ManualDeliveryLine(models.TransientModel):
    _name = "manual.delivery.line"
    _description = "手动发货行"

    manual_delivery_id = fields.Many2one(
        "manual.delivery",
        string="发货向导",
        ondelete="cascade",
        required=True,
        readonly=True,
    )
    order_line_id = fields.Many2one(
        "sale.order.line",
        string="销售订单行",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(related="order_line_id.product_id", string="产品")
    name = fields.Text(related="order_line_id.name", string="描述")
    qty_ordered = fields.Float(
        string="订单数量",
        related="order_line_id.product_uom_qty",
        help="销售订单中的订购数量",
        readonly=True,
    )
    order_id = fields.Many2one(related="order_line_id.order_id", string="订单")
    qty_procured = fields.Float(related="order_line_id.qty_procured", string="已发货数量")
    price_unit = fields.Float(related="order_line_id.price_unit", string="单价")
    total_price = fields.Float(string='本次出货产品总价￥', compute='_compute_total_price', store=True)
    quantity = fields.Float(string="本次发货数量")
    sequence = fields.Integer(string='序号', default=10)
    order_partner_id = fields.Many2one(
        related="order_line_id.order_id.partner_id",
        string="客户",
        readonly=True,
        store=True,
        help="销售订单行关联的客户。",
    )

    @api.depends('quantity', 'price_unit')
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.quantity * record.price_unit
            
    @api.onchange('quantity', 'order_line_id')
    def _onchange_quantity(self):
        """验证发货数量不超过待发货数量"""
        for record in self:
            if record.order_line_id and record.quantity > record.order_line_id.qty_to_procure:
                record.quantity = record.order_line_id.qty_to_procure
                return {'warning': {
                    'title': '数量超限',
                    'message': f'发货数量不能超过待发货数量 {record.order_line_id.qty_to_procure}'
                }}
    
    @api.constrains('quantity', 'order_line_id')
    def _check_quantity(self):
        """确保发货数量不超过待发货数量"""
        for record in self:
            if record.quantity < 0:
                raise ValidationError("发货数量不能为负数")
            if record.order_line_id and record.quantity > record.order_line_id.qty_to_procure:
                raise ValidationError(f"发货数量不能超过待发货数量 {record.order_line_id.qty_to_procure}")

    @api.model
    def create(self, vals):
        # 获取当前向导的所有行
        manual_delivery_id = vals.get("manual_delivery_id")
        if manual_delivery_id:
            existing_lines = self.env["manual.delivery.line"].search(
                [("manual_delivery_id", "=", manual_delivery_id)]
            )
            # 获取当前行的客户
            new_order_line = self.env["sale.order.line"].browse(vals.get("order_line_id"))
            new_partner_id = new_order_line.order_id.partner_id

            # 检查是否有客户不一致的情况
            if existing_lines and any(line.order_partner_id != new_partner_id for line in existing_lines):
                raise ValidationError("非同一客户货物，无法新增订单行！")

        return super(ManualDeliveryLine, self).create(vals)

    def write(self, vals):
        # 如果修改了 order_line_id，检查客户一致性
        if "order_line_id" in vals:
            for record in self:
                new_order_line = self.env["sale.order.line"].browse(vals["order_line_id"])
                new_partner_id = new_order_line.order_id.partner_id

                # 获取当前向导的所有行
                existing_lines = self.env["manual.delivery.line"].search(
                    [("manual_delivery_id", "=", record.manual_delivery_id.id)]
                )

                # 检查是否有客户不一致的情况
                if existing_lines and any(line.order_partner_id != new_partner_id for line in existing_lines):
                    raise ValidationError("非同一客户货物，无法新增订单行！")

        return super(ManualDeliveryLine, self).write(vals)