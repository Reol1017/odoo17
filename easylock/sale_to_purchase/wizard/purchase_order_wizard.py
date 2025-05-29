from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from collections import Counter
import logging
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

class PurchaseOrderWizard(models.TransientModel):
    _name = 'purchase.order.wizard'
    _description = '采购订单向导'

    sale_order_id = fields.Many2one('sale.order', required=True, readonly=True)
    vendor_id = fields.Many2one(
        'res.partner', 
        domain="[('supplier_rank', '>', 0)]", 
        required=True, 
        string="供应商"
    )
    line_ids = fields.One2many(
        'purchase.order.wizard.lines', 
        'wizard_id', 
        string='采购明细'
    )
    purchase_order_type = fields.Selection(
        selection=[
            ('po', '采购订单'),
            ('rfq', '询价单')
        ],
        string='订单类型',
        default='po',
        required=True
    )

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        """智能生成向导行及供应商默认值"""
        self.ensure_one()
        if self.sale_order_id:
            lines = []
            vendors = []
            
            # 批量预取产品数据
            products = self.sale_order_id.order_line.mapped('product_id')
            product_sellers = {
                p.id: p._select_seller() 
                for p in products
            }

            for line in self.sale_order_id.order_line:
                max_qty = line.product_uom_qty - line.related_purchased_qty
                seller = product_sellers.get(line.product_id.id)
                vendor = seller.partner_id if seller else False
                if line.related_purchased_qty ==  line.product_uom_qty:
                    continue  # 跳过不可采购的行
                lines.append((0, 0, {
                    'sale_line_id': line.id,
                    'purchase_qty': max_qty if max_qty > 0 else 0,
                    'max_qty': max_qty,
                    'preferred_vendor_id': vendor.id if vendor else False,
                }))
                
                if vendor:
                    vendors.append(vendor.id)
            
            self.line_ids = lines
            
            # 智能选择供应商策略
            if vendors:
                vendor_counts = Counter(vendors)
                most_common = vendor_counts.most_common(1)
                self.vendor_id = most_common[0][0] if most_common else False

    
    def action_create_purchase_order(self):
        """简化版采购订单创建逻辑（无价格/单位验证）"""
        self.ensure_one()
        if not self.vendor_id:
            raise UserError(_("必须选择供应商"))

        valid_lines = self.line_ids.filtered(lambda l: l.purchase_qty > 0)
        if not valid_lines:
            raise UserError(_("至少需要一个采购数量大于0的产品"))

        try:
            with self.env.cr.savepoint():
                po_vals = {
                    'partner_id': self.vendor_id.id,
                    'origin': self.sale_order_id.name,
                    'order_line': [],
                    'date_order': fields.Datetime.now(),
                }

                for line in valid_lines:
                    # 直接使用销售单位（移除单位转换逻辑）
                    product_uom = line.sale_line_id.product_uom
                    
                    po_line_vals = {
                        'product_id': line.product_id.id,
                        'product_qty': line.purchase_qty,
                        'product_uom': product_uom.id,
                        'price_unit': line.product_id.standard_price,  # 默认价格为0，允许手动修改
                        'name': line.product_id.display_name,
                        'date_planned': fields.Datetime.now(),
                        'origin_so_line': line.sale_line_id.id,
                    }
                    po_vals['order_line'].append((0, 0, po_line_vals))

                po = self.env['purchase.order'].create(po_vals)
                if self.purchase_order_type == 'po':
                    try:
                        po.button_confirm()
                    except Exception as e:
                        raise UserError(f"确认采购订单失败: {str(e)}")
                else:
                    # 可选：添加提示信息
                    po.message_post(body="由于供应商订单类型为询价单，未自动确认")


                return {
                    'name': _('采购订单'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_mode': 'form',
                    'res_id': po.id,
                    'views': [(False, 'form')],
                    'context': {'create': False},
                    'target': 'current',
                }

        except Exception as e:
            _logger.error("采购订单创建失败，错误详情：%s", str(e))
            raise UserError(_("创建采购订单失败，请联系系统管理员"))

class PurchaseOrderWizardLine(models.TransientModel):
    _name = 'purchase.order.wizard.lines'
    _description = '向导采购明细'
    
    wizard_id = fields.Many2one('purchase.order.wizard')
    sale_line_id = fields.Many2one('sale.order.line', required=True)
    product_id = fields.Many2one(
        related='sale_line_id.product_id', 
        readonly=True,
        store=True
    )
    purchase_qty = fields.Float(
        string="采购数量",
        digits=(12, 0),
        required=True
    )
    max_qty = fields.Float(
        string="可采购量", 
        digits=(12, 0),
        compute='_compute_max_qty',
        store=True,
        readonly=True
    )
    product_uom = fields.Many2one(
        'uom.uom', 
        related="product_id.uom_po_id",
        string="采购单位",
        readonly=True
    )
    unit_price = fields.Float(
        string="单价",
        compute="_compute_unit_price",
        digits=(12, 2)
    )
    # 新增: 首选供应商字段
    preferred_vendor_id = fields.Many2one(
        'res.partner',
        string="首选供应商",
        readonly=True
    )

    @api.depends('sale_line_id.product_uom_qty', 'sale_line_id.related_purchased_qty')
    def _compute_max_qty(self):
        for record in self:
            record.max_qty = (
                record.sale_line_id.product_uom_qty 
                - record.sale_line_id.related_purchased_qty
            )

    @api.constrains('purchase_qty')
    def _check_purchase_qty(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for record in self:
            if float_compare(record.purchase_qty, 0.0, precision_digits=precision) < 0:
                raise ValidationError(_("采购数量不能为负数"))
            if float_compare(record.purchase_qty, record.max_qty, precision_digits=precision) > 0:
                raise ValidationError(_(
                    "产品 %s 的采购数量不能超过最大可采购量 %s"
                ) % (record.product_id.name, record.max_qty))

    @api.depends('product_id', 'wizard_id.vendor_id', 'purchase_qty')
    def _compute_unit_price(self):
        for line in self:
            price = 0.0
            if line.product_id and line.wizard_id.vendor_id:
                seller = line.product_id._select_seller(
                    partner_id=line.wizard_id.vendor_id.id,
                    quantity=line.purchase_qty,
                    uom_id=line.product_uom
                )
                price = seller.price if seller else line.product_id.standard_price
            line.unit_price = price
    


    @api.onchange('product_id')
    def _onchange_product_id(self):
        """智能数量建议"""
        if self.product_id and self.max_qty > 0:
            self.purchase_qty = min(self.max_qty, self.sale_line_id.product_uom_qty)