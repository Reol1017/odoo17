# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import json
import re
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class VatInvoice(models.Model):
    """增值税发票 - 继承hr.expense，使用重命名字段避免冲突"""
    _name = 'vat.invoice'
    _description = '增值税发票'
    _inherit = ['hr.expense']  # 继承hr.expense
    _rec_name = 'name'
    _order = 'date desc, id desc'

    # ========== 不需要重新定义hr.expense已有的基本字段 ==========
    # 只定义增值税发票特有字段和需要覆盖的字段
    
    # 重新定义tax_ids字段，使用不同的关联表
    tax_ids = fields.Many2many(
        'account.tax',
        'vat_invoice_tax_rel',  # 使用不同的关联表名
        'invoice_id',
        'tax_id',
        string='税',
        domain=[('type_tax_use', '=', 'purchase')]
    )
    
    # ========== 增值税发票特有字段 - 重命名避免与hr.expense冲突 ==========
    
    # 发票基本信息
    vat_invoice_code = fields.Char('发票代码', readonly=True)
    vat_invoice_number = fields.Char('发票号码', readonly=True)
    vat_invoice_date = fields.Date('开票日期', readonly=True)
    vat_invoice_type = fields.Char('发票类型', readonly=True)
    
    # 税务信息 - 重命名避免与hr.expense的税务字段冲突
    vat_amount_without_tax = fields.Monetary('不含税金额', readonly=True)
    vat_tax_amount = fields.Monetary('税额', readonly=True)
    vat_amount_in_words = fields.Char('价税合计(大写)', readonly=True)
    vat_tax_rate = fields.Char('税率', readonly=True)
    
    # 销售方信息
    vat_vendor_name = fields.Char('销售方名称', readonly=True)
    vat_vendor_tax_id = fields.Char('销售方税号', readonly=True)
    vat_vendor_address = fields.Char('销售方地址', readonly=True)
    vat_vendor_bank = fields.Char('销售方开户行', readonly=True)
    
    # 购买方信息
    vat_purchaser_name = fields.Char('购买方名称', readonly=True)
    vat_purchaser_tax_id = fields.Char('购买方税号', readonly=True)
    vat_purchaser_address = fields.Char('购买方地址', readonly=True)
    vat_purchaser_bank = fields.Char('购买方开户行', readonly=True)
    
    # 商品信息
    vat_commodity_name = fields.Char('商品名称', readonly=True)
    vat_commodity_type = fields.Char('商品类型', readonly=True)
    vat_commodity_unit = fields.Char('商品单位', readonly=True)
    vat_commodity_quantity = fields.Float('商品数量', readonly=True)
    vat_commodity_price = fields.Monetary('商品单价', readonly=True)
    vat_commodity_amount = fields.Monetary('商品金额', readonly=True)
    
    # 其他发票信息
    vat_drawer = fields.Char('开票人', readonly=True)
    vat_payee = fields.Char('收款人', readonly=True)
    vat_checker = fields.Char('复核人', readonly=True)
    vat_remarks = fields.Text('发票备注', readonly=True)
    
    # OCR数据
    vat_ocr_raw_data = fields.Text('OCR原始数据')
    
    # 标识字段
    is_vat_invoice = fields.Boolean('是增值税发票', default=True, readonly=True)
    
    @api.model
    def create_from_ocr_data(self, ocr_result, employee_id=None):
        """从OCR结果创建增值税发票记录"""
        try:
            if not ocr_result.get('words_result'):
                return False
                
            words_result = ocr_result['words_result'][0]['result']
            
            # 获取员工信息
            if not employee_id:
                employee_id = self.env.user.employee_id.id
                if not employee_id:
                    raise UserError(_('当前用户没有关联的员工记录'))
            
            # 查找或创建产品
            product = self._find_or_create_product()
            
            # 基本信息提取
            amount_str = self._get_field_value(words_result, 'AmountInFiguers')
            amount = self._safe_float_conversion(amount_str)
            
            # 解析日期
            invoice_date_str = self._get_field_value(words_result, 'InvoiceDate')
            invoice_date = self._parse_date_safe(invoice_date_str)
            
            # 商品名称和销售方
            commodity_names = self._get_commodity_names(words_result.get('CommodityName', []))
            vendor_name = self._get_field_value(words_result, 'SellerName')
            
            vals = {
                # hr.expense 基本字段
                'name': commodity_names or vendor_name or '增值税发票',
                'date': invoice_date,
                'employee_id': employee_id,
                'product_id': product.id,
                'unit_amount': amount,
                'quantity': 1.0,
                'description': "发票号码: %s" % self._get_field_value(words_result, 'InvoiceNum'),
                
                # 增值税发票特有字段 - 使用重命名的字段
                'vat_invoice_number': self._get_field_value(words_result, 'InvoiceNum'),
                'vat_invoice_code': self._get_field_value(words_result, 'InvoiceCode'),
                'vat_invoice_date': invoice_date,
                'vat_invoice_type': self._get_field_value(words_result, 'InvoiceTypeOrg'),
                'vat_amount_without_tax': self._safe_float_conversion(self._get_field_value(words_result, 'TotalAmount')),
                'vat_tax_amount': self._safe_float_conversion(self._get_field_value(words_result, 'TotalTax')),
                'vat_amount_in_words': self._get_field_value(words_result, 'AmountInWords'),
                'vat_tax_rate': self._process_tax_rate(words_result.get('CommodityTaxRate', [])),
                'vat_vendor_name': vendor_name,
                'vat_vendor_tax_id': self._get_field_value(words_result, 'SellerRegisterNum'),
                'vat_vendor_address': self._get_field_value(words_result, 'SellerAddress'),
                'vat_vendor_bank': self._get_field_value(words_result, 'SellerBank'),
                'vat_purchaser_name': self._get_field_value(words_result, 'PurchaserName'),
                'vat_purchaser_tax_id': self._get_field_value(words_result, 'PurchaserRegisterNum'),
                'vat_purchaser_address': self._get_field_value(words_result, 'PurchaserAddress'),
                'vat_purchaser_bank': self._get_field_value(words_result, 'PurchaserBank'),
                'vat_commodity_name': commodity_names,
                'vat_commodity_type': self._get_field_value(words_result, 'CommodityType'),
                'vat_commodity_unit': self._get_field_value(words_result, 'CommodityUnit'),
                'vat_commodity_quantity': self._safe_float_conversion(self._get_field_value(words_result, 'CommodityNum')),
                'vat_commodity_price': self._safe_float_conversion(self._get_field_value(words_result, 'CommodityPrice')),
                'vat_commodity_amount': self._safe_float_conversion(self._get_field_value(words_result, 'CommodityAmount')),
                'vat_drawer': self._get_field_value(words_result, 'NoteDrawer'),
                'vat_payee': self._get_field_value(words_result, 'Payee'),
                'vat_checker': self._get_field_value(words_result, 'Checker'),
                'vat_remarks': self._get_field_value(words_result, 'Remarks'),
                'vat_ocr_raw_data': json.dumps(ocr_result, ensure_ascii=False, indent=2),
                'is_vat_invoice': True,
            }
            
            return self.create(vals)
            
        except Exception as e:
            _logger.exception("创建增值税发票记录时发生错误: %s", str(e))
            raise UserError(_('创建增值税发票记录失败: %s') % str(e))
    
    def _find_or_create_product(self):
        """查找或创建增值税发票产品"""
        product = self.env['product.product'].search([
            ('name', '=', '增值税发票'),
            ('can_be_expensed', '=', True)
        ], limit=1)
        
        if not product:
            try:
                category = self.env.ref('product.cat_expense', raise_if_not_found=False)
                if not category:
                    category = self.env['product.category'].search([], limit=1)
                
                product = self.env['product.product'].create({
                    'name': '增值税发票',
                    'detailed_type': 'service',
                    'categ_id': category.id if category else False,
                    'can_be_expensed': True,
                    'sale_ok': False,
                    'purchase_ok': True,
                })
            except Exception as e:
                _logger.error("创建产品失败: %s", str(e))
                # 使用任何可用的费用产品
                product = self.env['product.product'].search([
                    ('can_be_expensed', '=', True)
                ], limit=1)
                if not product:
                    raise UserError(_('无法找到或创建费用产品'))
        
        return product
    
    def _get_field_value(self, words_result, field_name):
        """获取字段值"""
        field_data = words_result.get(field_name, [])
        if field_data and isinstance(field_data, list) and len(field_data) > 0:
            return field_data[0].get('word', '')
        return ''
    
    def _get_commodity_names(self, commodity_list):
        """获取商品名称列表"""
        if not commodity_list:
            return ''
        names = [item.get('word', '') for item in commodity_list if item.get('word')]
        return ', '.join(names)
    
    def _process_tax_rate(self, tax_rate_list):
        """处理税率"""
        if not tax_rate_list:
            return ''
        rates = [item.get('word', '') for item in tax_rate_list if item.get('word')]
        if not rates:
            return ''
        unique_rates = set(rates)
        return rates[0] if len(unique_rates) == 1 else '混合税率'
    
    def _safe_float_conversion(self, value_str):
        """安全转换字符串为浮点数"""
        if not value_str:
            return 0.0
        try:
            cleaned_str = str(value_str).replace(',', '').replace('￥', '').replace('¥', '').strip()
            return float(cleaned_str)
        except (ValueError, TypeError, AttributeError):
            return 0.0
    
    def _parse_date_safe(self, date_str):
        """安全解析日期字符串"""
        if not date_str:
            return fields.Date.today()
        
        try:
            # 中文日期格式
            match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', str(date_str))
            if match:
                year, month, day = match.groups()
                parsed_date = datetime(int(year), int(month), int(day))
                return fields.Date.to_string(parsed_date)
        except Exception:
            pass
        
        return fields.Date.today()
        
    # ========== 继承hr.expense方法 ==========
    def action_submit_expenses(self):
        """提交费用"""
        if any(expense.state != 'draft' for expense in self):
            raise UserError(_("只能提交草稿状态的费用"))
        self.write({'state': 'reported'})
        
    def action_approve_expenses(self):
        """批准费用"""
        if any(expense.state != 'reported' for expense in self):
            raise UserError(_("只能批准已提交的费用"))
        self.write({'state': 'approved'})
        
    def action_view_sheet(self):
        """查看报告"""
        self.ensure_one()
        if not self.sheet_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet',
            'res_id': self.sheet_id.id
        }
        
    def attach_document(self, **kwargs):
        """附加文档"""
        # 这个方法在视图中被调用，但实际上是通过widget来处理的
        return True
        
    def action_reset_to_draft(self):
        """重置为草稿"""
        self.write({'state': 'draft'})
        
    def action_split_wizard(self):
        """拆分费用"""
        # 这个方法在hr.expense中有实现，但对于vat.invoice可能不需要
        return {
            'type': 'ir.actions.act_window',
            'name': _('拆分费用'),
            'res_model': 'hr.expense.split.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_expense_id': self.id,
            }
        }