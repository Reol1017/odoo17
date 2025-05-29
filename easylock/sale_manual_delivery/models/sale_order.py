from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    manual_delivery = fields.Boolean(
        string="分批发货",
        help="如果该订单产品非一次性发出，那么这个按钮就必须被勾选！！！",
        default=True,
    )

    has_pending_delivery = fields.Boolean(
        string="待发货?",
        compute="_compute_delivery_pending",
    )

    def _compute_delivery_pending(self):
        for rec in self:
            lines_pending = rec.order_line.filtered(
                lambda x: x.product_id.type != "service" and x.qty_to_procure > 0
            )
            rec.has_pending_delivery = bool(lines_pending)


    def action_manual_delivery_wizard(self):
        self.ensure_one()
        action = self.env.ref("sale_manual_delivery.action_wizard_manual_delivery")
        [action] = action.read()
        action["context"] = {"default_carrier_id": self.carrier_id.id}
        action["name"] = "手动发货向导"
        return action

    @api.constrains("manual_delivery")
    def _check_manual_delivery(self):
        if any(rec.state not in ["draft", "sent"] for rec in self):
            raise UserError(
                "只能在报价单状态下切换分批发货，已确认订单无法更改！"
            )
    
    @api.model
    def create(self, vals):
        # 调用原生create方法创建订单
        order = super(SaleOrder, self).create(vals)
        # 检查上下文标识，若存在则自动确认
        if self._context.get('auto_confirm_order'):
            order.action_confirm()
        return order
