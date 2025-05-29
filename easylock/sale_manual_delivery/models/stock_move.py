from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_new_picking_values(self):
        # 重载以设置手动发货向导中的carrier_id
        # 注意：sale_manual_delivery应是manual.delivery记录
        res = super()._get_new_picking_values()
        manual_delivery = self.env.context.get("sale_manual_delivery")
        if manual_delivery:
            if manual_delivery.partner_id:
                res["partner_id"] = manual_delivery.partner_id.id
            if manual_delivery.carrier_id:
                res["carrier_id"] = manual_delivery.carrier_id.id
        return res

    def _search_picking_for_assignation(self):
        # 重载以过滤carrier_id
        # 注意：sale_manual_delivery应是manual.delivery记录
        manual_delivery = self.env.context.get("sale_manual_delivery")
        if manual_delivery:
            # super()中使用的原始域
            domain = self._search_picking_for_assignation_domain()
            # 按承运商过滤
            if manual_delivery.carrier_id:
                domain += [
                    ("carrier_id", "=", manual_delivery.carrier_id.id),
                ]
            return self.env["stock.picking"].search(domain, limit=1)
        else:
            return super()._search_picking_for_assignation()
