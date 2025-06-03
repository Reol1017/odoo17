# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import base64
import re
from datetime import datetime
import tempfile
import os
import logging

_logger = logging.getLogger(__name__)

class ContractGeneration(models.Model):
    _name = 'contract.generation'
    _description = '合同生成'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='合同编号', required=True, copy=False, readonly=True, 
                      default=lambda self: self.env['ir.sequence'].next_by_code('contract.generation') or '新建')
    
    template_id = fields.Many2one('contract.template', string='合同模板', required=True, tracking=True)
    template_type = fields.Selection(related='template_id.contract_type', string='合同类型', readonly=True)
    
    # 合同基本信息
    contract_title = fields.Char(string='合同标题', required=True)
    contract_date = fields.Date(string='合同日期', default=fields.Date.today)
    start_date = fields.Date(string='开始日期')
    end_date = fields.Date(string='结束日期')
    signing_date = fields.Date(string='签订日期')
    signing_date_year = fields.Integer(string='签订日期(年)', compute='_compute_signing_date_parts', store=True)
    signing_date_month = fields.Integer(string='签订日期(月)', compute='_compute_signing_date_parts', store=True)
    signing_date_day = fields.Integer(string='签订日期(日)', compute='_compute_signing_date_parts', store=True)
    
    # 付款后交付时间
    after_prepayment_days = fields.Integer(string='收到预付款后(天数)', help='收到预付款后多少天内交付')
    
    # 甲方信息
    party_a_partner_id = fields.Many2one('res.partner', string='甲方', tracking=True, domain=[('is_company', '=', True)])
    party_a_name = fields.Char(string='甲方名称', compute='_compute_party_a_name', store=True, readonly=False)
    
    # 甲方子联系人
    party_a_child_partner_id = fields.Many2one('res.partner', string='甲方子联系人', 
                                            domain="[('parent_id', '=', party_a_partner_id), ('type', '=', 'contact')]")
    
    party_a_legal_representative = fields.Char(string='甲方法定代表人')
    party_a_agent = fields.Char(string='甲方代理人')
    party_a_contact = fields.Char(string='甲方联系人')
    party_a_phone = fields.Char(string='甲方电话')
    party_a_address = fields.Text(string='甲方地址')
    party_a_bank = fields.Char(string='甲方开户银行')
    party_a_account = fields.Char(string='甲方账号')
    party_a_tax_id = fields.Char(string='甲方税号')
    
    # 乙方信息
    party_b_name = fields.Char(string='乙方名称')
    party_b_contact = fields.Char(string='乙方联系人')
    party_b_phone = fields.Char(string='乙方电话')
    party_b_address = fields.Text(string='乙方地址')
    party_b_agent = fields.Char(string='乙方代理人')
    
    # 工程信息
    project_name = fields.Char(string='工程名称')
    project_location = fields.Char(string='工程地点')
    project_total_price = fields.Float(string='工程总价')
    
    # 付款信息
    deposit_percentage = fields.Float(string='定金比例', help='百分比，例如: 30.0表示30%')
    deposit_amount = fields.Float(string='定金金额')
    loan_percentage = fields.Float(string='贷款比例', help='百分比，例如: 70.0表示70%')
    loan_amount = fields.Float(string='贷款金额')
    
    # 甲方联系人信息
    party_a_payment_contact = fields.Char(string='甲方付款联络人')
    party_a_payment_contact_phone = fields.Char(string='甲方付款联络人电话')
    
    # 收货和验收信息
    party_a_invoice_receiver = fields.Char(string='甲方发票接收人')
    party_a_goods_receiver = fields.Char(string='甲方货物接收负责人')
    party_a_goods_receiver_phone = fields.Char(string='甲方货物接收负责人电话')
    party_a_inspector = fields.Char(string='甲方工程验收负责人')
    party_a_inspector_phone = fields.Char(string='甲方工程验收负责人电话')
    
    # 合同金额
    contract_amount = fields.Float(string='合同金额')
    currency_id = fields.Many2one('res.currency', string='币种', 
                                 default=lambda self: self.env.company.currency_id)
    
    # 自定义字段（用于存储用户填写的其他信息）
    custom_fields = fields.Text(string='自定义字段', help='JSON格式存储的自定义字段值')
    
    # 生成的文件
    generated_word = fields.Binary(string='生成的Word文档')
    generated_word_filename = fields.Char(string='Word文档文件名')
    
    # 状态
    state = fields.Selection([
        ('draft', '草稿'),
        ('generated', '已生成'),
        ('confirmed', '已确认'),
        ('cancelled', '已取消')
    ], string='状态', default='draft', tracking=True)
    
    # 备注
    notes = fields.Text(string='备注')
    
    company_id = fields.Many2one('res.company', string='公司', default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='负责人', default=lambda self: self.env.user)

    @api.model
    def create(self, vals):
        if vals.get('name', '新建') == '新建':
            vals['name'] = self.env['ir.sequence'].next_by_code('contract.generation') or '新建'
        return super(ContractGeneration, self).create(vals)

    @api.depends('signing_date')
    def _compute_signing_date_parts(self):
        for record in self:
            if record.signing_date:
                record.signing_date_year = record.signing_date.year
                record.signing_date_month = record.signing_date.month
                record.signing_date_day = record.signing_date.day
            else:
                record.signing_date_year = 0
                record.signing_date_month = 0
                record.signing_date_day = 0

    @api.depends('party_a_partner_id')
    def _compute_party_a_name(self):
        for record in self:
            if record.party_a_partner_id:
                record.party_a_name = record.party_a_partner_id.name
            elif not record.party_a_name:
                record.party_a_name = False

    @api.onchange('party_a_child_partner_id')
    def _onchange_party_a_child_partner_id(self):
        """当选择子联系人时自动填充相关信息"""
        if self.party_a_child_partner_id:
            # 检查联系人的职位
            function = self.party_a_child_partner_id.function or ''
            function = function.lower() if function else ''
            
            # 检查是否是法人
            is_legal_rep = '法定代表人' in function or '法人' in function
            
            # 如果是法人，同时更新法定代表人、代理人和联系人字段
            if is_legal_rep:
                self.party_a_legal_representative = self.party_a_child_partner_id.name
                self.party_a_agent = self.party_a_child_partner_id.name
                self.party_a_contact = self.party_a_child_partner_id.name
            else:
                # 否则只更新联系人字段
                self.party_a_contact = self.party_a_child_partner_id.name
            
            # 更新电话字段
            self.party_a_phone = self.party_a_child_partner_id.mobile or self.party_a_child_partner_id.phone or ''

    @api.onchange('party_a_partner_id')
    def _onchange_party_a_partner_id(self):
        if self.party_a_partner_id:
            # 主联系人名称
            self.party_a_name = self.party_a_partner_id.name
            
            # 清空子联系人选择
            self.party_a_child_partner_id = False
            
            # 查找法人角色
            legal_rep = None
            
            # 查找所有子联系人
            child_contacts = self.env['res.partner'].search([
                ('parent_id', '=', self.party_a_partner_id.id),
                ('type', '=', 'contact')
            ])
            
            for child in child_contacts:
                function = child.function or ''
                function = function.lower() if function else ''
                
                # 法定代表人/法人
                if '法定代表人' in function or '法人' in function:
                    legal_rep = child
                    break  # 找到法人后立即退出循环
            
            # 如果找到法人，将三个字段都设置为法人信息
            if legal_rep:
                self.party_a_legal_representative = legal_rep.name
                self.party_a_agent = legal_rep.name
                self.party_a_contact = legal_rep.name
                self.party_a_phone = legal_rep.mobile or legal_rep.phone or ''
            elif child_contacts:
                # 如果没有找到法人但有子联系人，使用第一个子联系人
                self.party_a_contact = child_contacts[0].name
                self.party_a_phone = child_contacts[0].mobile or child_contacts[0].phone or ''
            else:
                # 如果没有子联系人，使用公司电话
                self.party_a_phone = self.party_a_partner_id.mobile or self.party_a_partner_id.phone or ''
            
            # 设置完整地址（从左到右：国家、省、市、街道）
            address_parts = []
            
            # 国家
            if self.party_a_partner_id.country_id:
                address_parts.append(self.party_a_partner_id.country_id.name)
            
            # 省
            if self.party_a_partner_id.state_id:
                address_parts.append(self.party_a_partner_id.state_id.name)
            
            # 城市
            if self.party_a_partner_id.city:
                address_parts.append(self.party_a_partner_id.city)
            
            # 街道
            if self.party_a_partner_id.street:
                address_parts.append(self.party_a_partner_id.street)
            
            # 街道2
            if self.party_a_partner_id.street2:
                address_parts.append(self.party_a_partner_id.street2)
                
            # 邮政编码
            if self.party_a_partner_id.zip:
                address_parts.append(self.party_a_partner_id.zip)
            
            # 组合完整地址
            self.party_a_address = ' '.join(address_parts)
            
            # 设置税号
            if self.party_a_partner_id.vat:
                self.party_a_tax_id = self.party_a_partner_id.vat

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError('开始日期不能晚于结束日期。')

    def action_generate_contract(self):
        """生成合同"""
        self.ensure_one()
        
        if not self.template_id or not self.template_id.template_file:
            raise UserError('请选择有效的合同模板。')
        
        try:
            # 准备替换变量
            variables = self._prepare_variables()
            
            # 生成Word文档
            word_content = self._generate_word_document(variables)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            word_filename = f"{self.contract_title or self.name}_{timestamp}.docx"
            
            # 保存Word文档
            self.generated_word = base64.b64encode(word_content)
            self.generated_word_filename = word_filename
            
            self.state = 'generated'
            
            self.message_post(body="合同文档生成成功！Word文件已生成。")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '成功',
                    'message': '合同已生成完成！请在"生成的文件"页签中下载文件。',
                    'type': 'success',
                }
            }
            
        except Exception as e:
            raise UserError(f'生成合同时出错: {str(e)}')

    def _prepare_variables(self):
        """准备模板变量替换字典"""
        variables = {}
        
        # 基本信息
        variables.update({
            'contract_number': self.name or '',
            'contract_title': self.contract_title or '',
            'contract_date': self.contract_date.strftime('%Y年%m月%d日') if self.contract_date else '',
            'start_date': self.start_date.strftime('%Y年%m月%d日') if self.start_date else '',
            'end_date': self.end_date.strftime('%Y年%m月%d日') if self.end_date else '',
            'signing_date': self.signing_date.strftime('%Y年%m月%d日') if self.signing_date else '',
            'signing_date_year': str(self.signing_date_year) if self.signing_date_year else '',
            'signing_date_month': str(self.signing_date_month) if self.signing_date_month else '',
            'signing_date_day': str(self.signing_date_day) if self.signing_date_day else '',
            'after_prepayment_days': str(self.after_prepayment_days) if self.after_prepayment_days is not None else '0',
        })
        
        # 甲方信息
        party_a_name = self.party_a_name
        if self.party_a_partner_id:
            party_a_name = self.party_a_partner_id.name
            
        # 甲方联系人信息
        party_a_legal_rep = self.party_a_legal_representative
        party_a_agent = self.party_a_agent
        party_a_contact = self.party_a_contact
        party_a_phone = self.party_a_phone
        
        # 如果选择了子联系人，优先使用子联系人的信息
        if self.party_a_child_partner_id:
            function = self.party_a_child_partner_id.function or ''
            function = function.lower() if function else ''
            
            # 如果是法人，更新所有字段
            if '法定代表人' in function or '法人' in function:
                party_a_legal_rep = self.party_a_child_partner_id.name
                party_a_agent = self.party_a_child_partner_id.name
                party_a_contact = self.party_a_child_partner_id.name
            # 否则只更新联系人
            else:
                party_a_contact = self.party_a_child_partner_id.name
                
            # 更新电话
            party_a_phone = self.party_a_child_partner_id.mobile or self.party_a_child_partner_id.phone or ''
            
        variables.update({
            'party_a_name': party_a_name or '',
            'party_a_legal_representative': party_a_legal_rep or '',
            'party_a_agent': party_a_agent or '',
            'party_a_contact': party_a_contact or '',
            'party_a_phone': party_a_phone or '',
            'party_a_address': self.party_a_address or '',
            'party_a_bank': self.party_a_bank or '',
            'party_a_account': self.party_a_account or '',
            'party_a_tax_id': self.party_a_tax_id or '',
        })
        
        # 乙方信息
        variables.update({
            'party_b_name': self.party_b_name or '',
            'party_b_contact': self.party_b_contact or '',
            'party_b_phone': self.party_b_phone or '',
            'party_b_address': self.party_b_address or '',
            'party_b_agent': self.party_b_agent or '',
        })
        
        # 工程信息
        variables.update({
            'project_name': self.project_name or '',
            'project_location': self.project_location or '',
            'project_total_price': f"{self.project_total_price:,.2f}" if self.project_total_price is not None else "0.00",
        })
        
        # 付款信息
        variables.update({
            'deposit_percentage': f"{self.deposit_percentage}" if self.deposit_percentage is not None and self.deposit_percentage > 0 else "0",
            'deposit_amount': f"{self.deposit_amount:,.2f}" if self.deposit_amount is not None else "0.00",
            'loan_percentage': f"{self.loan_percentage}" if self.loan_percentage is not None and self.loan_percentage > 0 else "0",
            'loan_amount': f"{self.loan_amount:,.2f}" if self.loan_amount is not None else "0.00",
        })
        
        # 甲方联系人信息
        variables.update({
            'party_a_payment_contact': self.party_a_payment_contact or '',
            'party_a_payment_contact_phone': self.party_a_payment_contact_phone or '',
        })
        
        # 收货和验收信息
        variables.update({
            'party_a_invoice_receiver': self.party_a_invoice_receiver or '',
            'party_a_goods_receiver': self.party_a_goods_receiver or '',
            'party_a_goods_receiver_phone': self.party_a_goods_receiver_phone or '',
            'party_a_inspector': self.party_a_inspector or '',
            'party_a_inspector_phone': self.party_a_inspector_phone or '',
        })
        
        # 合同金额
        variables['contract_amount'] = f"{self.contract_amount:,.2f}" if self.contract_amount is not None else "0.00"
        variables['currency'] = self.currency_id.name if self.currency_id else ''
        
        # 处理自定义字段
        if self.custom_fields:
            try:
                import json
                custom_data = json.loads(self.custom_fields)
                variables.update(custom_data)
            except:
                pass
        
        return variables

    def _generate_word_document(self, variables):
        """生成Word文档"""
        try:
            # 获取模板文件内容
            template_content = base64.b64decode(self.template_id.template_file)
            
            if self.template_id.template_filename and self.template_id.template_filename.lower().endswith('.docx'):
                # 处理Word模板
                return self._process_word_template(template_content, variables)
            elif self.template_id.template_filename and self.template_id.template_filename.lower().endswith('.doc'):
                # 处理老版本Word模板
                return self._process_old_word_template(template_content, variables)
            else:
                # 处理文本模板
                return self._process_text_template(template_content, variables)
                
        except Exception as e:
            raise UserError(f'处理模板文件时出错: {str(e)}')

    def _process_text_template(self, template_content, variables):
        """处理文本模板"""
        try:
            # 尝试多种编码解码文本内容
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin-1']
            text_content = None
            
            for encoding in encodings:
                try:
                    text_content = template_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if text_content is None:
                # 如果所有编码都失败，使用latin-1并忽略错误
                text_content = template_content.decode('latin-1', errors='ignore')
            
            # 替换变量
            for key, value in variables.items():
                placeholder = f"{{{{{key}}}}}"
                text_content = text_content.replace(placeholder, str(value))
            
            # 创建简单的Word格式（实际上是RTF格式）
            # 使用字符串拼接而不是f-string来处理反斜杠
            rtf_header = "{\\rtf1\\ansi\\deff0 {\\fonttbl {\\f0 Times New Roman;}}}\\f0\\fs24 "
            rtf_body = text_content.replace('\n', '\\par ')
            rtf_content = rtf_header + rtf_body + "}"
            return rtf_content.encode('utf-8')
            
        except Exception as e:
            raise UserError(f'处理文本模板时出错: {str(e)}')

    def _process_word_template(self, template_content, variables):
        """处理Word模板"""
        try:
            import zipfile
            from io import BytesIO
            import xml.etree.ElementTree as ET
            
            # 创建新的Word文档
            output_buffer = BytesIO()
            
            with zipfile.ZipFile(BytesIO(template_content), 'r') as template_zip:
                with zipfile.ZipFile(output_buffer, 'w', zipfile.ZIP_DEFLATED) as output_zip:
                    
                    for item in template_zip.infolist():
                        data = template_zip.read(item.filename)
                        
                        if item.filename == 'word/document.xml':
                            # 处理主文档内容
                            data = self._replace_variables_in_xml(data, variables)
                        
                        output_zip.writestr(item, data)
            
            output_buffer.seek(0)
            return output_buffer.getvalue()
            
        except Exception as e:
            # 如果Word处理失败，回退到文本处理
            return self._process_text_template(template_content, variables)

    def _replace_variables_in_xml(self, xml_data, variables):
        """在XML中替换变量"""
        try:
            xml_string = xml_data.decode('utf-8')
            
            # 替换变量
            for key, value in variables.items():
                placeholder = f"{{{{{key}}}}}"
                xml_string = xml_string.replace(placeholder, str(value))
            
            return xml_string.encode('utf-8')
            
        except Exception:
            return xml_data

    def _process_old_word_template(self, template_content, variables):
        """处理老版本Word模板"""
        try:
            # 对于.doc文件，我们将其转换为文本处理
            content_str = template_content.decode('latin-1', errors='ignore')
            
            # 替换变量
            for key, value in variables.items():
                placeholder = f"{{{{{key}}}}}"
                content_str = content_str.replace(placeholder, str(value))
            
            # 创建RTF格式输出
            rtf_header = "{\\rtf1\\ansi\\deff0 {\\fonttbl {\\f0 SimSun;}}}"
            rtf_body = "\\f0\\fs24 " + content_str.replace('\n', '\\par ')
            rtf_content = rtf_header + rtf_body + "}"
            
            return rtf_content.encode('utf-8')
            
        except Exception as e:
            # 如果处理失败，回退到文本处理
            return self._process_text_template(template_content, variables)

    def action_confirm(self):
        """确认合同"""
        self.state = 'confirmed'

    def action_cancel(self):
        """取消合同"""
        self.state = 'cancelled'

    def action_reset_to_draft(self):
        """重置为草稿"""
        self.state = 'draft'
        
    def action_download_word(self):
        """下载Word文档"""
        self.ensure_one()
        if not self.generated_word:
            raise UserError('请先生成合同文档。')
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=contract.generation&id={self.id}&field=generated_word&filename_field=generated_word_filename&download=true',
            'target': 'new',
        }