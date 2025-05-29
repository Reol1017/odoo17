from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ManualDelivery(models.TransientModel):
    _name = "manual.delivery"
    _description = "手动发货"
    _order = "create_date desc"

    total_shipment_price = fields.Float(string='本次出货产品总价', compute='_compute_total_shipment_price', store=True)

    @api.depends('line_ids.total_price')
    def _compute_total_shipment_price(self):
        for record in self:
            record.total_shipment_price = sum(line.total_price for line in record.line_ids)
    def add_more_order_lines(self):
        """打开向导以添加更多订单行"""
        self.ensure_one()
    
        return {
            'name': '添加订单行',
            'type': 'ir.actions.act_window',
            'res_model': 'select.order.lines',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id}
        }

    @api.model
    def add_selected_lines(self, manual_delivery_id, line_ids):
        """将选定的销售订单行添加到手动发货向导"""
        manual_delivery = self.browse(manual_delivery_id)
        sale_lines = self.env['sale.order.line'].browse(line_ids)
    
        # 为每个选定的销售订单行创建manual.delivery.line记录
        vals_list = []
        for line in sale_lines:
            vals_list.append({
                'manual_delivery_id': manual_delivery.id,
                'order_line_id': line.id,
                'name': line.name,
                'product_id': line.product_id.id,
                'qty_ordered': line.product_uom_qty,
                'qty_procured': line.qty_procured,
                'quantity': line.qty_to_procure,
                'price_unit': line.price_unit,
            })
    
        # 创建新的manual.delivery.line记录
        self.env['manual.delivery.line'].create(vals_list)

        # 返回更新后的手动发货向导视图
        return {
            'name': '手动发货',
            'type': 'ir.actions.act_window',
            'res_model': 'manual.delivery',
            'view_mode': 'form',
            'res_id': manual_delivery.id,
            'target': 'new',
            'context': self.env.context,
        }
    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        # 如果active_model是sale.order/sale.order.line，获取行
        sale_lines = self.env["sale.order.line"]
        active_model = self.env.context["active_model"]
        if active_model == "sale.order.line":
            sale_ids = self.env.context["active_ids"] or []
            sale_lines = self.env["sale.order.line"].browse(sale_ids)
        elif active_model == "sale.order":
            sale_ids = self.env.context["active_ids"] or []
            sale_lines = self.env["sale.order"].browse(sale_ids).mapped("order_line")
        if len(sale_lines.mapped("order_id.partner_id")) > 1:
            raise UserError("请选择同一客户的订单行！")
        if sale_lines:
            # 从这些行获取合作伙伴
            partner = sale_lines.mapped("order_id.partner_id")
            res["partner_id"] = partner.id
            res["commercial_partner_id"] = partner.commercial_partner_id.id
            # 转换为manual.delivery.lines
            res["line_ids"] = [
                (
                    0,
                    0,
                    {
                        "order_line_id": line.id,
                        "name": line.name,
                        "product_id": line.product_id.id,
                        "qty_ordered": line.product_uom_qty,
                        "qty_procured": line.qty_procured,
                        "quantity": line.qty_to_procure,
                        "price_unit": line.price_unit,
                    },
                )
                for line in sale_lines
                if line.qty_to_procure and line.product_id.type != "service"
            ]
        return res

    commercial_partner_id = fields.Many2one(
        "res.partner",
        string="商业伙伴",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="客户地址",
        domain="['|',"
        "('id', '=', commercial_partner_id),"
        "('parent_id', '=', commercial_partner_id)]",
        ondelete="cascade",
    )
    carrier_id = fields.Many2one(
        "delivery.carrier",
        string="运输承运商",
        ondelete="cascade",
    )
    route_id = fields.Many2one(
        "stock.route",
        string="使用特定路线",
        domain=[("sale_selectable", "=", True)],
        ondelete="cascade",
        help="留空以使用销售行中的相同路线",
    )
    line_ids = fields.One2many(
        "manual.delivery.line",
        "manual_delivery_id",
        string="待验证行",
    )
    date_planned = fields.Datetime(string="计划日期")

    def confirm(self):
        """创建手动调拨并打开新建的装箱单"""
        self.ensure_one()
        
        # 获取原始订单行关联的所有装箱单ID
        original_picking_ids = self.line_ids.mapped("order_line_id.move_ids.picking_id").ids
        
        # 执行库存规则生成调拨
        sale_lines = self.line_ids.mapped("order_line_id")
        sale_lines.with_context(
            sale_manual_delivery=self
        )._action_launch_stock_rule_manual()
        
        # 获取新生成的装箱单（排除已存在的）
        new_pickings = sale_lines.mapped("move_ids.picking_id").filtered(
            lambda p: p.id not in original_picking_ids
        )
        
        # 处理跳转逻辑
        if new_pickings:
            # 生成标准装箱单动作
            action = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
            action.update({
                'context': self.env.context
            })
            
            # 智能视图跳转
            if len(new_pickings) == 1:
                # 单个直接打开表单
                action.update({
                    'views': [(False, 'form')],
                    'res_id': new_pickings.id,
                    'target': 'main'  # 确保在主窗口打开
                })
            else:
                # 多个显示列表
                action['domain'] = [('id', 'in', new_pickings.ids)]
            action['context'] = {
                'default_origin': sale_lines.mapped("order_id.name")[0],
                'create': False  # 禁用新建按钮
            }
            return action
        
        # 无新建装箱单时的处理
        raise UserError("本次操作未生成新的调拨单，可能原因：\n1. 产品为服务类型无需物流\n2. 可用库存不足\n3. 路由配置异常")
