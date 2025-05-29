from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class Contract(models.Model):
    _name = 'document.contract'
    _description = '合同'
    _inherits = {'document.document': 'document_id'}
    
    document_id = fields.Many2one('document.document', string='基础文档', required=True, ondelete='cascade')
    
    # 合同特有字段
    contract_type = fields.Selection([
        ('sales', '销售合同'),
        ('purchase', '采购合同'),
        ('employment', '雇佣合同'),
        ('service', '服务合同'),
        ('lease', '租赁合同'),
        ('other', '其他')
    ], string='合同类型')
    
    date_start = fields.Date('开始日期', required=True, default=fields.Date.today)
    date_end = fields.Date('结束日期')
    
    currency_id = fields.Many2one('res.currency', string='币种', default=lambda self: self.env.company.currency_id.id)
    amount_total = fields.Monetary('合同金额', currency_field='currency_id')
    
    # 合同状态（扩展文档状态）
    contract_state = fields.Selection([
        ('draft', '草稿'),
        ('sent', '已发送'),
        ('signed', '已签署'),
        ('active', '生效中'),
        ('expired', '已到期'),
        ('terminated', '已终止')
    ], string='合同状态', default='draft', tracking=True)
    
    signing_date = fields.Date('签署日期')
    signer_id = fields.Many2one('res.partner', string='签署人')
    
    # 付款计划
    payment_term_id = fields.Many2one('account.payment.term', string='付款条款')
    
    # 合同条款和条件
    terms_conditions = fields.Html('条款和条件')
    
    @api.model_create_multi
    def create(self, vals_list):
        # 确保在创建合同时，文档类别被设置为合同类别
        for vals in vals_list:
            if 'category_id' in vals:
                category = self.env['document.category'].browse(vals['category_id'])
                if not category.is_contract:
                    # 查找合同类别，没有则创建
                    contract_category = self.env['document.category'].search([('is_contract', '=', True)], limit=1)
                    if not contract_category:
                        contract_category = self.env['document.category'].create({
                            'name': '合同',
                            'code': 'CTR',
                            'is_contract': True
                        })
                    vals['category_id'] = contract_category.id
                    
        return super().create(vals_list)
    
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for contract in self:
            if contract.date_end and contract.date_start > contract.date_end:
                raise ValidationError(_('结束日期必须晚于开始日期'))
    
    def action_send(self):
        self.write({'contract_state': 'sent'})
        return True
    
    def action_sign(self):
        self.write({
            'contract_state': 'signed',
            'signing_date': fields.Date.today()
        })
        return True
    
    def action_activate(self):
        self.write({'contract_state': 'active'})
        # 同时更新基础文档状态
        self.document_id.write({'state': 'approved'})
        return True
    
    def action_expire(self):
        self.write({'contract_state': 'expired'})
        return True
    
    def action_terminate(self):
        self.write({'contract_state': 'terminated'})
        # 同时更新基础文档状态
        self.document_id.write({'state': 'archived'})
        return True
        
    def action_submit(self):
        return self.document_id.action_submit()
    
    def action_approve(self):
        return self.document_id.action_approve()
    
    def action_reject(self):
        return self.document_id.action_reject()
    
    def action_archive(self):
        return self.document_id.action_archive()
    
    def action_draft(self):
        return self.document_id.action_draft()
    
    def action_create_new_version(self):
        return self.document_id.action_create_new_version()
