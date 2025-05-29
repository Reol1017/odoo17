from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AssignPurchaserWizard(models.TransientModel):
    _name = 'assign.purchaser.wizard'
    _description = '分配采购员向导'
    
    request_id = fields.Many2one('sale.purchase.request', string='采购请求', required=True)
    purchaser_ids = fields.Many2many('res.users', string='采购员', 
                                   domain="[('groups_id', 'in', [purchase_group_id])]",
                                   required=True)
    purchase_group_id = fields.Many2one('res.groups', string='采购用户组',
                                       default=lambda self: self.env.ref('purchase.group_purchase_user').id,
                                       readonly=True)
    
    @api.model
    def default_get(self, fields_list):
        res = super(AssignPurchaserWizard, self).default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            res['request_id'] = active_id
        return res
    
    def action_confirm(self):
        self.ensure_one()
        
        if not self.purchaser_ids:
            raise UserError(_('请选择至少一名采购员'))
        
        request = self.request_id
        
        # 将采购员添加为关注者
        partner_ids = self.purchaser_ids.mapped('partner_id').ids
        request.message_subscribe(partner_ids=partner_ids)
        
        # 创建通知消息
        note = _('来自销售订单 %s 的新采购请求需要处理') % request.sale_order_id.name
        
        # 发送通知邮件
        request.message_post(
            body=note,
            partner_ids=partner_ids,
            subtype_id=self.env.ref('mail.mt_note').id,
            author_id=self.env.user.partner_id.id,
            message_type='notification'
        )
        
        # 创建活动
        for user in self.purchaser_ids:
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'note': note,
                'res_id': request.id,
                'res_model_id': self.env['ir.model']._get('sale.purchase.request').id,
                'user_id': user.id,
                'summary': _('处理销售采购请求')
            })
        
        # 更新请求状态为等待采购处理
        if request.state == 'draft':
            request.write({'state': 'waiting'})
        
        return {'type': 'ir.actions.act_window_close'} 