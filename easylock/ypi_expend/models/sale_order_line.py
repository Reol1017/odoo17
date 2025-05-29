from odoo import models, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('name')
    def _onchange_name_sync_to_stock(self):
        for line in self:
            stock_moves = self.env['stock.move'].search([('sale_line_id', '=', line.id)])
            for sm in stock_moves:
                sm.description_picking = line.name
