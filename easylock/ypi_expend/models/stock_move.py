from odoo import models, api, fields

class StockMove(models.Model):
    _inherit = 'stock.move'

    description_picking = fields.Text(compute='_compute_description_picking', store=True, readonly=False)

    # 目前不做反向同步逻辑，如需扩展可在此添加 

    @api.depends('sale_line_id', 'sale_line_id.name', 'product_id', 'product_id.name')
    def _compute_description_picking(self):
        for move in self:
            # 情况1：关联销售订单行且描述不为空
            if move.sale_line_id and move.sale_line_id.name:
                move.description_picking = move.sale_line_id.name
            # 情况2：关联销售订单行但描述为空，使用产品名称
            elif move.sale_line_id and not move.sale_line_id.name and move.product_id:
                move.description_picking = move.product_id.name
            # 情况3：没有关联销售订单行，保留当前值，为空则使用产品名称
            elif not move.sale_line_id:
                if not move.description_picking and move.product_id:
                    move.description_picking = move.product_id.name
                # 其他情况保持原值
            # 情况4：兜底处理，确保不为空
            if not move.description_picking and move.product_id:
                move.description_picking = move.product_id.name
            elif not move.description_picking:
                move.description_picking = "/" 