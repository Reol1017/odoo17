from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_procured = fields.Float(
        string="已发货数量",
        help="已计划或已发货的数量（已创建库存移动）",
        compute="_compute_qty_procured",
        digits=(12, 0),
        store=True,
    )
    qty_to_procure = fields.Float(
        string="待发货数量",
        help="需要添加到发货的待处理数量",
        compute="_compute_qty_to_procure",
        readonly=True,
        digits=(12, 0),
        store=True,
    )
    delivery_status = fields.Selection([
        ('not_delivered', '未发货'),
        ('partially_delivered', '部分发货'),
        ('fully_delivered', '已全发'),
    ], string='交货状态', compute='_compute_delivery_status', store=True)

    def add_more_order_lines(self):
        """打开向导以添加更多订单行"""
        self.ensure_one()
    
        return {
            'name': _('添加订单行'),
            'type': 'ir.actions.act_window',
            'res_model': 'select.order.lines',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id}
        }

    @api.depends('qty_procured', 'product_uom_qty')
    def _compute_delivery_status(self):
        """
        计算交货状态：
        - 如果已交货数量 = 0，则状态为"未发货"。
        - 如果已交货数量 > 0 且 < 订单数量，则状态为"部分发货"。
        - 如果已交货数量 >= 订单数量，则状态为"已全发"。
        """
        for record in self:
            if record.qty_procured >= record.product_uom_qty:
                record.delivery_status = 'fully_delivered'
            elif record.qty_procured > 0:
                record.delivery_status = 'partially_delivered'
            else:
                record.delivery_status = 'not_delivered'

    @api.depends(
        "move_ids.state",
        "move_ids.scrapped",
        "move_ids.product_uom_qty",
        "move_ids.product_uom",
        "move_ids.location_id",
        "move_ids.location_dest_id",
        "move_ids.picking_id.state",  # 添加对调拨单状态的依赖
    )
    def _compute_qty_procured(self):
        """
        根据现有库存移动计算给定销售订单行的已计划数量
        """
        for line in self:
            # 使用标准的qty_delivered计算，但确保在取消调拨时重新计算
            line.qty_procured = line.qty_delivered

    @api.depends("product_uom_qty", "qty_procured")
    def _compute_qty_to_procure(self):
        """计算销售订单行上剩余待计划的数量"""
        for line in self:
            line.qty_to_procure = max(0, line.product_uom_qty - line.qty_procured)

    def _get_procurement_group(self):
        # 重载以获取正确日期/合作伙伴的procurement.group
        # 注意：sale_manual_delivery应是manual.delivery记录
        manual_delivery = self.env.context.get("sale_manual_delivery")
        if manual_delivery:
            domain = [
                ("partner_id", "=", manual_delivery.partner_id.id),
            ]
            if manual_delivery.date_planned:
                domain += [
                    ("date_planned", "=", manual_delivery.date_planned),
                ]
            return self.env["procurement.group"].search(domain, limit=1)
        else:
            return super()._get_procurement_group()

    def _prepare_procurement_group_vals(self):
        # 重载以添加manual.delivery字段到procurement.group
        # 注意：sale_manual_delivery应是manual.delivery记录
        res = super()._prepare_procurement_group_vals()
        manual_delivery = self.env.context.get("sale_manual_delivery")
        if manual_delivery:
            res["partner_id"] = manual_delivery.partner_id.id
            res["date_planned"] = manual_delivery.date_planned
        return res

    def _prepare_procurement_values(self, group_id=False):
        # 重载以处理手动发货的计划日期和路由
        # 此方法最终准备库存移动值，其结果将发送到StockRule._get_stock_move_values
        # 注意：sale_manual_delivery应是manual.delivery记录
        res = super()._prepare_procurement_values(group_id=group_id)
        manual_delivery = self.env.context.get("sale_manual_delivery")
        if manual_delivery:
            if manual_delivery.date_planned:
                res["date_planned"] = manual_delivery.date_planned
            if manual_delivery.route_id:
                # `_get_stock_move_values`需要一个recordset
                res["route_ids"] = manual_delivery.route_id
        return res
    
    def _action_launch_stock_rule_manual(self, previous_product_uom_qty=False):
        # 注意：sale_manual_delivery应是manual.delivery记录
        manual_delivery = self.env.context.get("sale_manual_delivery")
        
        # 检查manual_delivery是否为None
        if not manual_delivery:
            raise UserError(_("上下文中缺少手动发货数据。"))

        # 确保manual_delivery有line_ids
        if not manual_delivery.line_ids:
            raise UserError(_("手动发货中未找到任何行。"))

        procurements = []
        group_id = None

        for line in self:
            if line.state != "sale" or line.product_id.type not in ("consu", "product"):
                continue

            # 筛选当前订单行的手动发货行
            manual_line = manual_delivery.line_ids.filtered(
                lambda mdl, ln=line: mdl.order_line_id == ln
            )
            if not manual_line or not manual_line.quantity:
                continue

            # 获取或创建采购组
            if not group_id:
                group_id = self.env["procurement.group"].create({
                    "name": line.order_id.name or _("手动发货组"),
                    "move_type": line.order_id.picking_policy,
                    # 如果company_id不是有效字段则移除
                    # "company_id": self.env.company.id,
                })
            else:
                # 如有必要更新组
                if group_id.move_type != line.order_id.picking_policy:
                    group_id.write({"move_type": line.order_id.picking_policy})

            # 准备采购值
            values = line._prepare_procurement_values(group_id=group_id)
            line_uom = line.product_uom
            quant_uom = line.product_id.uom_id
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(
                manual_line.quantity, quant_uom
            )
            procurements.append(
                self.env["procurement.group"].Procurement(
                    line.product_id,
                    product_qty,
                    procurement_uom,
                    line.order_id.partner_shipping_id.property_stock_customer,
                    line.name,
                    line.order_id.name,
                    line.order_id.company_id,
                    values,
                )
            )

        if procurements:
            self.env["procurement.group"].run(procurements)

        # 基于第一个订单行创建单个库存调拨（发货单）
        # 确保此代码块只执行一次
        if not group_id:
            first_order_line = manual_delivery.line_ids[0].order_line_id
            sale_order = first_order_line.order_id
            picking_type = sale_order.warehouse_id.out_type_id

            picking_vals = {
                "origin": sale_order.name,  # 使用销售订单名称作为来源
                "partner_id": sale_order.partner_shipping_id.id,
                "picking_type_id": picking_type.id,
                "location_id": sale_order.warehouse_id.lot_stock_id.id,
                "location_dest_id": sale_order.partner_shipping_id.property_stock_customer.id,
                "company_id": sale_order.company_id.id,
                "move_type": sale_order.picking_policy,
                "group_id": group_id.id,
            }

            picking = self.env["stock.picking"].create(picking_vals)

            # 为所有手动发货行准备库存移动行
            moves = []
            for manual_line in manual_delivery.line_ids:
                order_line = manual_line.order_line_id
                if order_line.state != "sale" or order_line.product_id.type not in ("consu", "product"):
                    continue

                move_vals = {
                    "product_id": order_line.product_id.id,
                    "product_uom_qty": manual_line.quantity,
                    "product_uom": order_line.product_uom.id,
                    "quantity": manual_line.quantity,
                    "location_id": sale_order.warehouse_id.lot_stock_id.id,
                    "location_dest_id": sale_order.partner_shipping_id.property_stock_customer.id,
                    "picking_id": picking.id,
                    "name": order_line.name,
                    "group_id": group_id.id,
                    "sale_line_id": order_line.id,  # 确保链接到销售订单行
                }
                moves.append(move_vals)

            if moves:
                stock_moves = self.env["stock.move"].create(moves)
                picking.action_confirm()
                
                # 移除手动更新销售订单行的代码，让Odoo标准机制处理
                # for move in stock_moves:
                #     sale_line = move.sale_line_id
                #     if sale_line:
                #         sale_line.qty_delivered += move.product_uom_qty

        return True

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        # 重载以跳过手动发货行的库存规则启动
        # 我们只在从手动发货向导调用时启动它们
        # 注意：sale_manual_delivery应是manual.delivery记录
        manual_delivery_lines = self.filtered("order_id.manual_delivery")
        lines_to_launch = self - manual_delivery_lines
        return super(SaleOrderLine, lines_to_launch)._action_launch_stock_rule(
            previous_product_uom_qty=previous_product_uom_qty
        )
