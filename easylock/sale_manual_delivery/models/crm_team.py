from odoo import fields, models


class CrmTeam(models.Model):
    _inherit = "crm.team"

    manual_delivery = fields.Boolean(
        help="如果启用，销售订单确认时不会创建发货单。您需要使用创建发货按钮来预留和发送货物。",
    )
