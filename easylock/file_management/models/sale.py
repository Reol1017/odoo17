from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    document_ids = fields.Many2many('document.document', string='相关文档')
    document_count = fields.Integer(compute='_compute_document_count', string='文档数量')
    
    drawing_ids = fields.Many2many('document.drawing', string='相关图纸')
    drawing_count = fields.Integer(compute='_compute_drawing_count', string='图纸数量')
    
    contract_ids = fields.Many2many('document.contract', string='相关合同')
    contract_count = fields.Integer(compute='_compute_contract_count', string='合同数量')
    
    def _compute_document_count(self):
        for order in self:
            order.document_count = len(order.document_ids)
    
    def _compute_drawing_count(self):
        for order in self:
            order.drawing_count = len(order.drawing_ids)
    
    def _compute_contract_count(self):
        for order in self:
            order.contract_count = len(order.contract_ids)
    
    def action_view_documents(self):
        self.ensure_one()
        return {
            'name': _('报价单文档'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.document_ids.ids)],
            'context': {'default_partner_id': self.partner_id.id}
        }
    
    def action_view_drawings(self):
        self.ensure_one()
        return {
            'name': _('报价单图纸'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.drawing',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.drawing_ids.ids)],
            'context': {'default_partner_id': self.partner_id.id}
        }
    
    def action_view_contracts(self):
        self.ensure_one()
        return {
            'name': _('报价单合同'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.contract',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.contract_ids.ids)],
            'context': {'default_partner_id': self.partner_id.id}
        }

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    document_id = fields.Many2one('document.document', string='关联文档', 
                                 copy=True, tracking=True)
    drawing_id = fields.Many2one('document.drawing', string='关联图纸', 
                                copy=True, tracking=True)
    contract_id = fields.Many2one('document.contract', string='关联合同', 
                                 copy=True, tracking=True)
    
    document_version = fields.Char(related='document_id.version', 
                                  string='文档版本', readonly=True)
    drawing_version = fields.Char(related='drawing_id.version', 
                                 string='图纸版本', readonly=True)
    contract_version = fields.Char(related='contract_id.version', 
                                  string='合同版本', readonly=True)
    
    def action_select_document(self):
        self.ensure_one()
        action = {
            'name': _('选择文档'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'view_mode': 'tree,form',
            'target': 'new',
            'domain': [('is_drawing', '=', False), ('is_contract', '=', False), ('state', '=', 'approved')],
            'context': {
                'default_partner_id': self.order_id.partner_id.id,
                'default_product_id': self.product_id.id,
            }
        }
        # 如果只有一个文档可用，直接选择
        documents = self.env['document.document'].search(
            [('product_id', '=', self.product_id.id), 
             ('is_drawing', '=', False), 
             ('is_contract', '=', False), 
             ('state', '=', 'approved')]
        )
        if len(documents) == 1:
            self.document_id = documents.id
            return self._update_description()
        return action
    
    def action_select_drawing(self):
        self.ensure_one()
        action = {
            'name': _('选择图纸'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.drawing',
            'view_mode': 'tree,form',
            'target': 'new',
            'domain': [('state', '=', 'approved')],
            'context': {
                'default_partner_id': self.order_id.partner_id.id,
                'default_product_id': self.product_id.id,
            }
        }
        # 如果只有一个图纸可用，直接选择
        drawings = self.env['document.drawing'].search(
            [('product_id', '=', self.product_id.id), ('state', '=', 'approved')]
        )
        if len(drawings) == 1:
            self.drawing_id = drawings.id
            return self._update_description()
        return action
    
    def action_select_contract(self):
        self.ensure_one()
        action = {
            'name': _('选择合同'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.contract',
            'view_mode': 'tree,form',
            'target': 'new',
            'domain': [('contract_state', 'in', ['signed', 'active'])],
            'context': {
                'default_partner_id': self.order_id.partner_id.id,
                'default_product_id': self.product_id.id,
            }
        }
        # 如果只有一个合同可用，直接选择
        contracts = self.env['document.contract'].search(
            [('product_id', '=', self.product_id.id), 
             ('contract_state', 'in', ['signed', 'active']),
             ('partner_id', '=', self.order_id.partner_id.id)]
        )
        if len(contracts) == 1:
            self.contract_id = contracts.id
            return self._update_description()
        return action
    
    def _update_description(self):
        """更新订单行描述，添加文档、图纸和合同信息"""
        for line in self:
            description_parts = []
            if line.name:
                description_parts.append(line.name)
            
            if line.document_id:
                doc_info = f"[文档: {line.document_id.document_number}-{line.document_id.version}]"
                if doc_info not in (line.name or ''):
                    description_parts.append(doc_info)
            
            if line.drawing_id:
                drawing_info = f"[图纸: {line.drawing_id.document_number}-{line.drawing_id.version}]"
                if drawing_info not in (line.name or ''):
                    description_parts.append(drawing_info)
            
            if line.contract_id:
                contract_info = f"[合同: {line.contract_id.document_number}-{line.contract_id.version}]"
                if contract_info not in (line.name or ''):
                    description_parts.append(contract_info)
            
            if len(description_parts) > 1:
                line.name = " ".join(description_parts)
        return True
    
    @api.onchange('product_id')
    def _onchange_product_id_documents(self):
        """当选择产品时，自动关联相关文档、图纸和合同"""
        if self.product_id:
            # 查找该产品最新的已批准文档
            latest_document = self.env['document.document'].search(
                [('product_id', '=', self.product_id.id), 
                 ('is_drawing', '=', False), 
                 ('is_contract', '=', False),
                 ('state', '=', 'approved')], 
                order='create_date desc', 
                limit=1
            )
            if latest_document:
                self.document_id = latest_document.id
            
            # 查找该产品最新的已批准图纸
            latest_drawing = self.env['document.drawing'].search(
                [('product_id', '=', self.product_id.id), 
                 ('state', '=', 'approved')], 
                order='create_date desc', 
                limit=1
            )
            if latest_drawing:
                self.drawing_id = latest_drawing.id
            
            # 查找该客户与产品关联的有效合同
            latest_contract = self.env['document.contract'].search(
                [('product_id', '=', self.product_id.id),
                 ('partner_id', '=', self.order_id.partner_id.id),
                 ('contract_state', 'in', ['signed', 'active'])],
                order='date_start desc',
                limit=1
            )
            if latest_contract:
                self.contract_id = latest_contract.id
                
            # 更新描述
            self._update_description()
    
    @api.onchange('document_id', 'drawing_id', 'contract_id')
    def _onchange_documents(self):
        """当文档、图纸或合同变更时，更新订单行描述"""
        self._update_description()
        
        # 如果选择了合同，将合同关联到整个订单
        if self.contract_id and self.contract_id.id not in self.order_id.contract_ids.ids:
            self.order_id.write({'contract_ids': [(4, self.contract_id.id)]})
        
        # 如果选择了图纸，将图纸关联到整个订单
        if self.drawing_id and self.drawing_id.id not in self.order_id.drawing_ids.ids:
            self.order_id.write({'drawing_ids': [(4, self.drawing_id.id)]})
        
        # 如果选择了文档，将文档关联到整个订单
        if self.document_id and self.document_id.id not in self.order_id.document_ids.ids:
            self.order_id.write({'document_ids': [(4, self.document_id.id)]})