# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class VatInvoice(models.Model):
    """增值税发票独立模型 - 用于复杂查询和报表"""
    _name = 'vat.invoice'
    _description = '增值税发票'
    _rec_name = 'invoice_number'
    _order = 'invoice_date desc, id desc'

    # 关联字段
    expense_id = fields.Many2one('hr.expense', string='关联费用', ondelete='cascade', index=True)
    
    # 基本信息
    name = fields.Char('发票标题', compute='_compute_name', store=True)
    invoice_code = fields.Char('发票代码', readonly=True)
    invoice_number = fields.Char('发票号码', readonly=True, required=True)
    invoice_date = fields.Char('开票日期', readonly=True)
    invoice_type = fields.Char('发票类型', readonly=True, default='电子发票(普通发票)')
    
    # 金额信息
    amount = fields.Float('发票金额', readonly=True)
    amount_without_tax = fields.Float('不含税金额', readonly=True)
    tax_amount = fields.Float('税额', readonly=True)
    amount_in_words = fields.Char('价税合计(大写)', readonly=True)
    tax_rate = fields.Char('税率', readonly=True)
    
    # 销售方信息
    vendor_name = fields.Char('销售方名称', readonly=True)
    vendor_tax_id = fields.Char('销售方税号', readonly=True)
    vendor_address = fields.Char('销售方地址', readonly=True)
    vendor_bank = fields.Char('销售方开户行', readonly=True)
    
    # 购买方信息
    purchaser_name = fields.Char('购买方名称', readonly=True)
    purchaser_tax_id = fields.Char('购买方税号', readonly=True)
    purchaser_address = fields.Char('购买方地址', readonly=True)
    purchaser_bank = fields.Char('购买方开户行', readonly=True)
    
    # 商品信息
    commodity_name = fields.Char('商品名称', readonly=True)
    commodity_type = fields.Char('商品类型', readonly=True)
    commodity_unit = fields.Char('商品单位', readonly=True)
    commodity_quantity = fields.Float('商品数量', readonly=True)
    commodity_price = fields.Float('商品单价', readonly=True)
    commodity_amount = fields.Float('商品金额', readonly=True)
    
    # 其他信息
    drawer = fields.Char('开票人', readonly=True)
    payee = fields.Char('收款人', readonly=True)
    checker = fields.Char('复核人', readonly=True)
    remarks = fields.Text('备注', readonly=True)
    
    # OCR原始数据
    ocr_raw_data = fields.Text('OCR原始数据', readonly=True)
    
    @api.depends('invoice_number', 'vendor_name')
    def _compute_name(self):
        for record in self:
            if record.invoice_number and record.vendor_name:
                record.name = f"{record.vendor_name} - {record.invoice_number}"
            elif record.invoice_number:
                record.name = record.invoice_number
            else:
                record.name = '增值税发票'
    
    @api.model
    def create_from_ocr_data(self, ocr_result, expense_id):
        """从OCR结果创建增值税发票记录"""
        if not ocr_result.get('words_result'):
            return False
            
        words_result = ocr_result['words_result'][0]['result']
        
        # 处理税率
        tax_rate = self._process_tax_rate(words_result.get('CommodityTaxRate', []))
        
        # 处理金额
        amount_in_figures = self._get_field_value(words_result, 'AmountInFiguers')
        total_amount = self._get_field_value(words_result, 'TotalAmount')
        total_tax = self._get_field_value(words_result, 'TotalTax')
        
        # 转换为浮点数
        try:
            amount = float(amount_in_figures.replace(',', '')) if amount_in_figures else 0.0
        except (ValueError, TypeError):
            amount = 0.0
            
        try:
            amount_without_tax = float(total_amount.replace(',', '')) if total_amount else 0.0
        except (ValueError, TypeError):
            amount_without_tax = 0.0
            
        try:
            tax_amount = float(total_tax.replace(',', '')) if total_tax else 0.0
        except (ValueError, TypeError):
            tax_amount = 0.0
        
        vals = {
            'expense_id': expense_id,
            'invoice_number': self._get_field_value(words_result, 'InvoiceNum'),
            'invoice_code': self._get_field_value(words_result, 'InvoiceCode'),
            'invoice_date': self._get_field_value(words_result, 'InvoiceDate'),
            'invoice_type': self._get_field_value(words_result, 'InvoiceTypeOrg'),
            'amount': amount,
            'amount_without_tax': amount_without_tax,
            'tax_amount': tax_amount,
            'amount_in_words': self._get_field_value(words_result, 'AmountInWords'),
            'tax_rate': tax_rate,
            'vendor_name': self._get_field_value(words_result, 'SellerName'),
            'vendor_tax_id': self._get_field_value(words_result, 'SellerRegisterNum'),
            'vendor_address': self._get_field_value(words_result, 'SellerAddress'),
            'vendor_bank': self._get_field_value(words_result, 'SellerBank'),
            'purchaser_name': self._get_field_value(words_result, 'PurchaserName'),
            'purchaser_tax_id': self._get_field_value(words_result, 'PurchaserRegisterNum'),
            'purchaser_address': self._get_field_value(words_result, 'PurchaserAddress'),
            'purchaser_bank': self._get_field_value(words_result, 'PurchaserBank'),
            'commodity_name': self._get_commodity_names(words_result.get('CommodityName', [])),
            'drawer': self._get_field_value(words_result, 'NoteDrawer'),
            'payee': self._get_field_value(words_result, 'Payee'),
            'checker': self._get_field_value(words_result, 'Checker'),
            'remarks': self._get_field_value(words_result, 'Remarks'),
            'ocr_raw_data': str(ocr_result),
        }
        
        return self.create(vals)
    
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
        """处理税率，如果所有税率相同则显示该税率，否则显示混合税率"""
        if not tax_rate_list:
            return ''
        
        # 获取所有税率值
        rates = [item.get('word', '') for item in tax_rate_list if item.get('word')]
        
        if not rates:
            return ''
        
        # 检查是否所有税率相同
        if len(set(rates)) == 1:
            return rates[0]
        else:
            return '混合税率'