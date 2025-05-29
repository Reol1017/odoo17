# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'
    
    # 新增字段
    organization_contact = fields.Char(
        string='组织/联系人',
        help='Organization or contact person'
    )
    project_name = fields.Char(
        string='项目名称',
        help='Project name'
    )