from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64

class DocumentCategory(models.Model):
    _name = 'document.category'
    _description = '文档类别'
    
    name = fields.Char('类别名称', required=True)
    code = fields.Char('类别代码')
    description = fields.Text('描述')
    is_drawing = fields.Boolean('图纸类别', help="勾选此项表示此类别用于图纸")
    is_contract = fields.Boolean('合同类别', help="勾选此项表示此类别用于合同")
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', '类别名称必须唯一!')
    ]

class DocumentTag(models.Model):
    _name = 'document.tag'
    _description = '文档标签'
    
    name = fields.Char('标签名称', required=True)
    color = fields.Integer('颜色索引')

class Document(models.Model):
    _name = 'document.document'
    _description = '文档'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, name'
    
    name = fields.Char('文档名称', required=True, tracking=True)
    document_number = fields.Char('文档编号', required=True, tracking=True)
    category_id = fields.Many2one('document.category', string='类别', tracking=True)
    description = fields.Text('描述')
    
    # 文件属性
    file = fields.Binary('文件', attachment=True)
    filename = fields.Char('文件名')
    file_type = fields.Selection([
        ('pdf', 'PDF文档'),
        ('doc', 'Word文档'),
        ('xls', 'Excel表格'),
        ('ppt', 'PowerPoint演示文稿'),
        ('img', '图片'),
        ('cad', 'CAD文件'),
        ('other', '其他')
    ], string='文件类型', default='pdf')
    
    # 版本控制
    version = fields.Char('版本号', default='1.0', tracking=True)
    previous_version_id = fields.Many2one('document.document', string='上一版本')
    next_version_id = fields.Many2one('document.document', string='下一版本')
    
    # 关联字段
    partner_id = fields.Many2one('res.partner', string='相关客户')
    product_id = fields.Many2one('product.template', string='相关产品')
    project_id = fields.Many2one('project.project', string='相关项目')
    task_ids = fields.Many2many('project.task', string='相关任务')
    sale_order_id = fields.Many2one('sale.order', string='相关销售订单')
    
    sale_order_ids = fields.Many2many('sale.order', string='相关销售订单')
    sale_line_ids = fields.One2many('sale.order.line', 'document_id', string='销售订单行')
    
    # 状态和负责人
    state = fields.Selection([
        ('draft', '草稿'),
        ('submitted', '已提交'),
        ('approved', '已批准'),
        ('rejected', '已拒绝'),
        ('archived', '已归档')
    ], default='draft', string='状态', tracking=True)
    
    user_id = fields.Many2one('res.users', string='负责人', default=lambda self: self.env.user)
    reviewer_id = fields.Many2one('res.users', string='审核人')
    create_date = fields.Datetime('创建日期', readonly=True)
    approval_date = fields.Datetime('批准日期')
    
    # 标签
    tag_ids = fields.Many2many('document.tag', string='标签')
    
    # 文档类型
    is_drawing = fields.Boolean('是图纸', related='category_id.is_drawing', store=True)
    is_contract = fields.Boolean('是合同', related='category_id.is_contract', store=True)
    
    _sql_constraints = [
        ('document_number_version_uniq', 'unique(document_number, version)', '相同文档编号的版本号必须唯一!')
    ]
    
    @api.constrains('file')
    def _check_file_size(self):
        for record in self:
            if record.file and len(record.file) > 50 * 1024 * 1024:  # 50MB
                raise ValidationError(_('文件大小不能超过50MB'))
    
    def action_submit(self):
        self.write({'state': 'submitted'})
        return True
    
    def action_approve(self):
        self.write({
            'state': 'approved',
            'reviewer_id': self.env.user.id,
            'approval_date': fields.Datetime.now()
        })
        return True
    
    def action_reject(self):
        self.write({
            'state': 'rejected',
            'reviewer_id': self.env.user.id
        })
        return True
    
    def action_archive(self):
        self.write({'state': 'archived'})
        return True
    
    def action_draft(self):
        self.write({'state': 'draft'})
        return True
    
    def action_create_new_version(self):
        """创建文档的新版本"""
        self.ensure_one()
        
        # 计算新版本号
        try:
            version_parts = self.version.split('.')
            if len(version_parts) > 1:
                minor = int(version_parts[1]) + 1
                new_version = f"{version_parts[0]}.{minor}"
            else:
                new_version = f"{float(self.version) + 0.1:.1f}"
        except:
            new_version = f"{self.version}.1"
        
        # 创建新版本文档
        new_doc = self.copy({
            'version': new_version,
            'previous_version_id': self.id,
            'state': 'draft',
            'reviewer_id': False,
            'approval_date': False,
        })
        
        # 更新当前文档指向新版本
        self.write({'next_version_id': new_doc.id})
        
        return {
            'name': _('新版本文档'),
            'view_mode': 'form',
            'res_model': 'document.document',
            'res_id': new_doc.id,
            'type': 'ir.actions.act_window',
        }