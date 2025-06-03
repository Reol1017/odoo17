# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
import re

class ContractTemplate(models.Model):
    _name = 'contract.template'
    _description = '合同模板'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='模板名称', required=True, tracking=True)
    description = fields.Text(string='描述')
    template_file = fields.Binary(string='模板文件', required=True)
    template_filename = fields.Char(string='文件名')
    active = fields.Boolean(string='启用', default=True)
    
    # 模板变量，用于识别模板中的占位符
    template_variables = fields.Text(string='模板变量', help='从模板文件中自动提取的变量，格式：{{变量名}}')
    
    # 合同类型
    contract_type = fields.Selection([
        ('service', '服务合同'),
        ('purchase', '采购合同'),
        ('employment', '劳动合同'),
        ('lease', '租赁合同'),
        ('other', '其他')
    ], string='合同类型', default='other', required=True)
    
    company_id = fields.Many2one('res.company', string='公司', default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='负责人', default=lambda self: self.env.user)
    
    create_date = fields.Datetime(string='创建时间', readonly=True)
    write_date = fields.Datetime(string='修改时间', readonly=True)

    @api.model
    def create(self, vals):
        record = super(ContractTemplate, self).create(vals)
        if record.template_file:
            record._extract_template_variables()
        return record

    def write(self, vals):
        result = super(ContractTemplate, self).write(vals)
        if 'template_file' in vals:
            self._extract_template_variables()
        return result

    def _extract_template_variables(self):
        """从模板文件中提取变量"""
        for record in self:
            if not record.template_file:
                continue
            
            try:
                # 解码文件内容
                file_content = base64.b64decode(record.template_file)
                
                # 检查文件类型
                if record.template_filename and record.template_filename.lower().endswith('.docx'):
                    # 处理Word文档
                    variables = record._extract_variables_from_docx(file_content)
                elif record.template_filename and record.template_filename.lower().endswith('.doc'):
                    # 老版本Word文档，尝试多种编码
                    variables = record._extract_variables_from_old_doc(file_content)
                else:
                    # 处理纯文本，尝试多种编码
                    variables = record._extract_variables_from_text_file(file_content)
                
                record.template_variables = '\n'.join(sorted(variables))
                
            except Exception as e:
                record.template_variables = f'提取变量时出错: {str(e)}'

    def _extract_variables_from_text(self, text):
        """从文本中提取变量"""
        try:
            # 查找 {{变量名}} 格式的占位符
            pattern = r'\{\{([^}]+)\}\}'
            matches = re.findall(pattern, text)
            return list(set(matches))
        except Exception:
            return []

    def _extract_variables_from_docx(self, file_content):
        """从Word文档中提取变量"""
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            from io import BytesIO
            
            variables = []
            
            # Word文档是一个zip文件
            with zipfile.ZipFile(BytesIO(file_content), 'r') as docx:
                # 读取主文档内容
                if 'word/document.xml' in docx.namelist():
                    document_xml = docx.read('word/document.xml')
                    
                    # 解析XML并提取文本
                    root = ET.fromstring(document_xml)
                    
                    # 提取所有文本内容
                    text_content = ''
                    for elem in root.iter():
                        if elem.text:
                            text_content += elem.text + ' '
                    
                    # 从文本中提取变量
                    variables = self._extract_variables_from_text(text_content)
            
            return variables
            
        except Exception:
            # 如果解析Word文档失败，返回空列表
            return []

    def _extract_variables_from_text_file(self, file_content):
        """从文本文件中提取变量，尝试多种编码"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin-1']
        
        for encoding in encodings:
            try:
                text_content = file_content.decode(encoding)
                return self._extract_variables_from_text(text_content)
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，返回空列表
        return []

    def _extract_variables_from_old_doc(self, file_content):
        """从老版本Word文档中提取变量"""
        try:
            # 老版本.doc文件是二进制格式，尝试提取文本内容
            # 这里简化处理，只提取可见的文本部分
            text_parts = []
            
            # 尝试找到文本内容（简单的字符串查找）
            content_str = file_content.decode('latin-1', errors='ignore')
            
            # 使用正则表达式查找可能的变量
            pattern = r'\{\{([^}]+)\}\}'
            matches = re.findall(pattern, content_str)
            
            return list(set(matches))
            
        except Exception:
            return []

    @api.constrains('template_file', 'template_filename')
    def _check_template_file(self):
        for record in self:
            if record.template_file and record.template_filename:
                if not record.template_filename.lower().endswith(('.docx', '.doc', '.txt')):
                    raise ValidationError('只支持Word文档(.docx, .doc)或文本文件(.txt)格式的模板文件。')

    def action_preview_variables(self):
        """预览模板变量"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'模板变量 - {self.name}',
            'res_model': 'contract.template',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('contract_management.contract_template_preview_form').id,
            'target': 'new',
        }