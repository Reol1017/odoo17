# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class VatInvoice(models.Model):
    _name = 'vat.invoice'
    _description = '增值税发票'
    _inherit = ['base.ticket']
    
    # 发票基本信息
    invoice_code = fields.Char('发票代码')
    invoice_number = fields.Char('发票号码')
    invoice_date = fields.Date('开票日期')
    invoice_type = fields.Char('发票类型')
    drawer = fields.Char('开票人')
    
    # 金额信息
    amount = fields.Float('含税金额', digits=(16, 2))
    amount_without_tax = fields.Float('不含税金额', digits=(16, 2))
    tax_amount = fields.Float('税额', digits=(16, 2))
    tax_rate = fields.Char('税率')
    amount_in_words = fields.Char('价税合计(大写)')
    
    # 销售方信息
    vendor_name = fields.Char('销售方名称')
    vendor_tax_id = fields.Char('销售方税号')
    vendor_address = fields.Char('销售方地址')
    vendor_bank = fields.Char('销售方开户行')
    
    # 购买方信息
    purchaser_name = fields.Char('购买方名称')
    purchaser_tax_id = fields.Char('购买方税号')
    purchaser_address = fields.Char('购买方地址')
    purchaser_bank = fields.Char('购买方开户行')
    
    # 商品信息
    commodity_name = fields.Char('商品名称')
    commodity_type = fields.Char('商品类型')
    commodity_unit = fields.Char('商品单位')
    commodity_quantity = fields.Float('商品数量')
    commodity_price = fields.Float('商品单价')
    commodity_amount = fields.Float('商品金额')
    
    # 其他信息
    remarks = fields.Text('备注')
    
    @api.model
    def create_from_ocr_data(self, result_data, raw_data=None):
        """从OCR数据创建增值税发票记录"""
        # 提取发票信息
        invoice_num = self._get_first_value(result_data.get('InvoiceNum', []))
        invoice_code = self._get_first_value(result_data.get('InvoiceCode', []))
        invoice_date_str = self._get_first_value(result_data.get('InvoiceDate', []))
        invoice_date = self._parse_date(invoice_date_str) if invoice_date_str else False
        invoice_type = self._get_first_value(result_data.get('InvoiceType', []))
        drawer = self._get_first_value(result_data.get('NoteDrawer', []))
        
        # 提取金额信息
        total_amount_str = self._get_first_value(result_data.get('TotalAmount', []))
        total_amount = float(total_amount_str) if total_amount_str else 0.0
        
        amount_in_figures_str = self._get_first_value(result_data.get('AmountInFiguers', []))
        amount_in_figures = float(amount_in_figures_str) if amount_in_figures_str else 0.0
        
        total_tax_str = self._get_first_value(result_data.get('TotalTax', []))
        total_tax = float(total_tax_str) if total_tax_str else 0.0
        
        # 处理税率
        tax_rates = []
        if 'CommodityTaxRate' in result_data:
            for tax_rate in result_data['CommodityTaxRate']:
                if 'word' in tax_rate:
                    tax_rates.append(tax_rate['word'])
        
        tax_rate = ''
        if tax_rates:
            # 检查是否所有税率都相同
            if all(rate == tax_rates[0] for rate in tax_rates):
                tax_rate = tax_rates[0]
            else:
                tax_rate = '混合税率'
        
        amount_in_words = self._get_first_value(result_data.get('AmountInWords', []))
        
        # 提取销售方和购买方信息
        vendor_name = self._get_first_value(result_data.get('SellerName', []))
        vendor_tax_id = self._get_first_value(result_data.get('SellerRegisterNum', []))
        vendor_address = self._get_first_value(result_data.get('SellerAddress', []))
        vendor_bank = self._get_first_value(result_data.get('SellerBank', []))
        
        purchaser_name = self._get_first_value(result_data.get('PurchaserName', []))
        purchaser_tax_id = self._get_first_value(result_data.get('PurchaserRegisterNum', []))
        purchaser_address = self._get_first_value(result_data.get('PurchaserAddress', []))
        purchaser_bank = self._get_first_value(result_data.get('PurchaserBank', []))
        
        # 提取商品信息
        commodity_name = self._get_first_value(result_data.get('CommodityName', []))
        commodity_type = self._get_first_value(result_data.get('CommodityType', []))
        commodity_unit = self._get_first_value(result_data.get('CommodityUnit', []))
        
        # 提取备注信息
        remarks = self._get_first_value(result_data.get('Remarks', []))
        
        # 创建增值税发票记录
        vals = {
            'name': f"发票 {invoice_num or ''}",
            'invoice_number': invoice_num,
            'invoice_code': invoice_code,
            'invoice_date': invoice_date,
            'invoice_type': invoice_type,
            'drawer': drawer,
            'amount': total_amount,
            'amount_without_tax': amount_in_figures,
            'tax_amount': total_tax,
            'tax_rate': tax_rate,
            'amount_in_words': amount_in_words,
            'vendor_name': vendor_name,
            'vendor_tax_id': vendor_tax_id,
            'vendor_address': vendor_address,
            'vendor_bank': vendor_bank,
            'purchaser_name': purchaser_name,
            'purchaser_tax_id': purchaser_tax_id,
            'purchaser_address': purchaser_address,
            'purchaser_bank': purchaser_bank,
            'commodity_name': commodity_name,
            'commodity_type': commodity_type,
            'commodity_unit': commodity_unit,
            'remarks': remarks,
        }
        
        if raw_data:
            vals['ocr_raw_data'] = raw_data
            
        return self.create(vals)
    
    def _get_first_value(self, data_list):
        """从列表中获取第一个元素的值"""
        if data_list and isinstance(data_list, list) and len(data_list) > 0:
            if isinstance(data_list[0], dict) and 'word' in data_list[0]:
                return data_list[0]['word']
        return ""
    
    def _parse_date(self, date_str):
        """解析日期字符串"""
        if not date_str:
            return False
            
        import re
        from datetime import datetime
        
        # 尝试匹配常见的日期格式
        patterns = [
            # 2025年05月23日
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            # 2025-05-23
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            # 2025/05/23
            r'(\d{4})/(\d{1,2})/(\d{1,2})',
            # 05/23/2025
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    # 根据不同格式调整年月日的位置
                    if pattern == r'(\d{1,2})/(\d{1,2})/(\d{4})':
                        # 月/日/年格式
                        month, day, year = groups
                    else:
                        # 年/月/日格式
                        year, month, day = groups
                    
                    try:
                        return fields.Date.to_string(datetime(int(year), int(month), int(day)))
                    except ValueError:
                        continue
        
        return False 