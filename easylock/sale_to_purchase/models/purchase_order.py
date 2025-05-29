from odoo import models, fields


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    origin_so_line = fields.Many2one(
        'sale.order.line',
        string='来源销售行',
        ondelete='set null',
        index=True,
        help="关联的原始销售订单行"
    )
    related_so_id = fields.Many2one(
        'sale.order',
        string='来源销售单',
        related='origin_so_line.order_id',
        store=True,
        index=True
    )
class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_vendor_price(self, partner_id, quantity, date, uom_id):
        self.ensure_one()
        seller = self._select_seller(
            partner_id=partner_id,
            quantity=quantity,
            date=date,
            uom_id=uom_id
        )
        return seller.price if seller else 0.0