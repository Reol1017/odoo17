import base64
import urllib.parse
import requests
import json
import logging
import tempfile
import os
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class BaiduOcrConfig(models.Model):
    _name = 'baidu.ocr.config'
    _description = 'Baidu OCR API Configuration'

    name = fields.Char(string='Configuration Name', required=True)
    api_key = fields.Char(string='API Key', required=True)
    secret_key = fields.Char(string='Secret Key', required=True)
    access_token = fields.Char(string='Access Token', readonly=True)
    token_expiry = fields.Datetime(string='Token Expiry', readonly=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('company_uniq', 'unique(company_id)', 'Only one configuration per company is allowed!')
    ]

    def get_access_token(self):
        """Get or refresh Baidu OCR API access token"""
        self.ensure_one()
        
        if not self.api_key or not self.secret_key:
            raise UserError(_("Please configure API Key and Secret Key"))
        
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        try:
            response = requests.post(url, params=params)
            response.raise_for_status()
            result = response.json()
            
            if 'access_token' in result:
                self.access_token = result.get('access_token')
                # Calculate expiry date based on response (typically 30 days)
                expiry_seconds = result.get('expires_in', 2592000)  # Default to 30 days
                self.token_expiry = fields.Datetime.now() + relativedelta(seconds=expiry_seconds)
                return self.access_token
            else:
                error_msg = result.get('error_description', 'Unknown error')
                raise UserError(_("Failed to get access token: %s") % error_msg)
        except Exception as e:
            _logger.error("Error getting Baidu access token: %s", str(e))
            raise UserError(_("Connection error: %s") % str(e))
    
    def recognize_invoice(self, image_data):
        """Recognize invoice using Baidu OCR API"""
        self.ensure_one()
        
        # Ensure we have a valid access token
        if not self.access_token or (self.token_expiry and self.token_expiry < fields.Datetime.now()):
            self.get_access_token()
        
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/multiple_invoice?access_token={self.access_token}"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        # Prepare image data
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        params = {"image": image_base64}
        data = urllib.parse.urlencode(params)
        
        try:
            response = requests.post(url, data=data, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            _logger.info("百度OCR API返回结果: %s", result)
            
            if 'error_code' in result:
                error_msg = result.get('error_msg', 'Unknown error')
                error_code = result.get('error_code')
                _logger.error("OCR API error: %s - %s", error_code, error_msg)
                raise UserError(_("OCR API error: %s - %s") % (error_code, error_msg))
            
            return self._process_ocr_result(result)
        except Exception as e:
            _logger.error("Error recognizing invoice: %s", str(e))
            raise UserError(_("Error recognizing invoice: %s") % str(e))
    
    def _process_ocr_result(self, result):
        """处理OCR结果 - 增强版本"""
        _logger.info("开始处理OCR结果: %s", result)
        
        # 初始化处理后的数据 - 添加vat_invoice_前缀
        processed_data = {
            'vendor': None,
            'date': None,
            'total_amount': 0.0,
            'tax_amount': 0.0,
            'currency': 'CNY',
            'invoice_number': None,
            'description': '',
            'invoice_code': None,
            'invoice_date': None,
            'invoice_type': None,
            'seller_name': None,
            'seller_register_num': None,
            'purchaser_name': None,
            'purchaser_register_num': None,
            'commodity_name': None,
            'service_type': None,
            'total_tax': 0.0,
            'amount_in_words': None,
            'drawer': None,
            'amount_in_figuers': 0.0,
            'tax_rates': [],
            'invoice_type_category': 'vat_invoice',  # 默认为增值税发票
        }
        
        if 'words_result' not in result:
            _logger.warning("OCR结果中没有words_result字段")
            # 如果没有识别结果，创建一个基础记录
            processed_data.update({
                'description': 'OCR识别费用',
                'total_amount': 0.0,
                'vendor': '未知供应商'
            })
            return processed_data
        
        words_result = result['words_result']
        _logger.info("words_result类型: %s, 内容: %s", type(words_result), words_result)
        
        # 处理多发票识别结果
        if isinstance(words_result, list) and len(words_result) > 0:
            # 取第一个发票的识别结果
            first_invoice = words_result[0]
            
            # 设置发票类型分类
            if 'type' in first_invoice:
                invoice_type = first_invoice.get('type')
                processed_data['invoice_type_category'] = invoice_type
            
            if 'result' in first_invoice:
                invoice_data = first_invoice['result']
                invoice_type = first_invoice.get('type', 'unknown')
                
                _logger.info("处理发票类型: %s, 数据: %s", invoice_type, invoice_data)
                
                # 提取基本发票信息
                processed_data.update({
                    'invoice_type': self._extract_field_value(invoice_data, 'InvoiceType') or self._extract_field_value(invoice_data, 'InvoiceTypeOrg'),
                    'vendor': self._extract_field_value(invoice_data, 'SellerName'),
                    'seller_name': self._extract_field_value(invoice_data, 'SellerName'),
                    'seller_register_num': self._extract_field_value(invoice_data, 'SellerRegisterNum'),
                    'date': self._extract_field_value(invoice_data, 'InvoiceDate'),
                    'invoice_date': self._extract_field_value(invoice_data, 'InvoiceDate'),
                    'invoice_number': self._extract_field_value(invoice_data, 'InvoiceNum') or self._extract_field_value(invoice_data, 'InvoiceNumConfirm'),
                    'invoice_code': self._extract_field_value(invoice_data, 'InvoiceCode'),
                    'purchaser_name': self._extract_field_value(invoice_data, 'PurchaserName'),
                    'purchaser_register_num': self._extract_field_value(invoice_data, 'PurchaserRegisterNum'),
                    'drawer': self._extract_field_value(invoice_data, 'NoteDrawer'),
                    'service_type': self._extract_field_value(invoice_data, 'ServiceType'),
                })
                
                # 提取金额信息
                vat_invoice_total_amount = self._extract_amount(invoice_data, 'TotalAmount')
                vat_invoice_total_tax = self._extract_amount(invoice_data, 'TotalTax')
                vat_invoice_amount_in_figures = self._extract_amount(invoice_data, 'AmountInFiguers')  # 注意：API字段拼写
                
                processed_data.update({
                    'total_amount': vat_invoice_total_amount,
                    'tax_amount': vat_invoice_total_tax,
                    'total_tax': vat_invoice_total_tax,
                    'amount_in_words': self._extract_field_value(invoice_data, 'AmountInWords'),
                    'amount_in_figuers': vat_invoice_amount_in_figures,
                })
                
                # 提取商品名称（取第一行商品）
                commodity_name = self._extract_commodity_name(invoice_data)
                processed_data['commodity_name'] = commodity_name
                
                # 提取税率列表
                processed_data['tax_rates'] = self._extract_tax_rates(invoice_data)
                
                # 如果商品名称为空，使用发票类型作为描述
                if not processed_data.get('commodity_name'):
                    processed_data['commodity_name'] = self._get_invoice_type_description(invoice_type)
                
                processed_data['description'] = processed_data.get('commodity_name', 'OCR识别费用')
                
                # 处理特定类型的发票数据
                if invoice_type == 'train_ticket':
                    self._process_train_ticket_data(invoice_data, processed_data)
            
        # 如果还是没有有效数据，尝试其他格式
        if not processed_data.get('total_amount') and not processed_data.get('vendor'):
            processed_data = self._process_alternative_formats(words_result, processed_data)
        
        # 确保必要字段有默认值
        if not processed_data.get('vendor'):
            processed_data['vendor'] = '未知供应商'
        if not processed_data.get('description'):
            processed_data['description'] = 'OCR识别费用'
        if not processed_data.get('total_amount'):
            processed_data['total_amount'] = 0.0
            
        _logger.info("最终处理结果: %s", processed_data)
        return processed_data
    
    def _extract_field_value(self, invoice_data, field_name):
        """从发票数据中提取字段值"""
        if field_name not in invoice_data:
            return None
            
        field_data = invoice_data[field_name]
        if not field_data or not isinstance(field_data, list):
            return None
            
        if len(field_data) > 0:
            first_item = field_data[0]
            if isinstance(first_item, dict):
                return first_item.get('word', '')
                
        return None
    
    def _extract_amount(self, invoice_data, field_name):
        """提取金额字段"""
        value = self._extract_field_value(invoice_data, field_name)
        if not value:
            return 0.0
            
        try:
            # 清理金额字符串
            amount_str = str(value).replace('¥', '').replace(',', '').replace('￥', '')
            # 移除非数字字符，保留小数点
            amount_str = ''.join(c for c in amount_str if c.isdigit() or c == '.')
            return float(amount_str) if amount_str else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _extract_commodity_name(self, invoice_data):
        """提取商品名称"""
        if 'CommodityName' not in invoice_data:
            return None
            
        field_data = invoice_data['CommodityName']
        if not isinstance(field_data, list) or not field_data:
            return None
            
        # 取第一行商品名称
        for item in field_data:
            if isinstance(item, dict) and item.get('row') == '1':
                return item.get('word', '')
                
        # 如果没有找到指定行，返回第一个
        if field_data and isinstance(field_data[0], dict):
            return field_data[0].get('word', '')
                
        return None
    
    def _extract_tax_rates(self, invoice_data):
        """提取所有税率"""
        tax_rates = []
        
        if 'CommodityTaxRate' not in invoice_data:
            return tax_rates
            
        field_data = invoice_data['CommodityTaxRate']
        if not isinstance(field_data, list):
            return tax_rates
            
        for item in field_data:
            if isinstance(item, dict) and 'word' in item:
                tax_rate = item.get('word', '')
                if tax_rate:
                    tax_rates.append(tax_rate)
                    
        return tax_rates
    
    def _get_invoice_type_description(self, invoice_type):
        """根据发票类型获取描述"""
        type_descriptions = {
            'vat_invoice': '增值税发票',
            'normal_invoice': '普通发票',
            'special_invoice': '专用发票', 
            'electronic_invoice': '电子发票',
            'taxi_receipt': '出租车票',
            'train_ticket': '火车票',
            'air_ticket': '机票',
            'bus_ticket': '汽车票',
            'receipt': '收据',
        }
        return type_descriptions.get(invoice_type, '发票费用')
    
    def _process_alternative_formats(self, words_result, processed_data):
        """处理其他格式的OCR结果"""
        _logger.info("尝试处理其他格式的OCR结果")
        
        # 如果是旧版本的API结果格式
        if isinstance(words_result, dict):
            if 'vat_invoice' in words_result:
                vat_data = words_result['vat_invoice']
                # 尝试提取税率
                tax_rate = None
                if 'tax_rate' in vat_data:
                    tax_rate = vat_data.get('tax_rate', {}).get('word', '')
                
                processed_data.update({
                    'vendor': vat_data.get('seller_name', {}).get('word', ''),
                    'date': vat_data.get('invoice_date', {}).get('word', ''),
                    'total_amount': self._parse_amount(vat_data.get('total_amount', {}).get('word', '0')),
                    'tax_amount': self._parse_amount(vat_data.get('total_tax', {}).get('word', '0')),
                    'invoice_number': f"{vat_data.get('invoice_code', {}).get('word', '')} {vat_data.get('invoice_number', {}).get('word', '')}".strip(),
                    'description': vat_data.get('title', {}).get('word', '增值税发票'),
                    'amount_in_figuers': self._parse_amount(vat_data.get('amount_in_figuers', {}).get('word', '0')),
                    'invoice_type_category': 'vat_invoice',
                })
                
                # 如果有税率，添加到税率列表
                if tax_rate:
                    processed_data['tax_rates'] = [tax_rate]
                
            elif 'receipt' in words_result:
                receipt_data = words_result['receipt']
                processed_data.update({
                    'vendor': receipt_data.get('seller', {}).get('word', ''),
                    'date': receipt_data.get('date', {}).get('word', ''),
                    'total_amount': self._parse_amount(receipt_data.get('total', {}).get('word', '0')),
                    'invoice_number': receipt_data.get('receipt_number', {}).get('word', ''),
                    'description': receipt_data.get('title', {}).get('word', '收据'),
                    'amount_in_figuers': self._parse_amount(receipt_data.get('total', {}).get('word', '0')),
                    'invoice_type_category': 'others',
                })
                # 收据通常没有税率
                processed_data['tax_rates'] = ['0%']
            
            elif 'taxi_receipt' in words_result:
                taxi_data = words_result['taxi_receipt']
                total_amount = self._parse_amount(taxi_data.get('total', {}).get('word', '0'))
                processed_data.update({
                    'vendor': '出租车费',
                    'date': taxi_data.get('date', {}).get('word', ''),
                    'total_amount': total_amount,
                    'invoice_number': f"{taxi_data.get('invoice_code', {}).get('word', '')} {taxi_data.get('invoice_number', {}).get('word', '')}".strip(),
                    'description': f"出租车费 {taxi_data.get('date', {}).get('word', '')}",
                    'amount_in_figuers': total_amount,
                    'invoice_type_category': 'taxi_receipt',
                })
                # 出租车票通常是3%税率
                processed_data['tax_rates'] = ['3%']
                
            elif 'train_ticket' in words_result:
                train_data = words_result['train_ticket']
                total_amount = self._parse_amount(train_data.get('ticket_price', {}).get('word', '0'))
                processed_data.update({
                    'vendor': '火车票',
                    'date': train_data.get('date', {}).get('word', ''),
                    'total_amount': total_amount,
                    'invoice_number': train_data.get('ticket_number', {}).get('word', ''),
                    'description': f"火车票 {train_data.get('starting_station', {}).get('word', '')} 到 {train_data.get('destination_station', {}).get('word', '')}",
                    'amount_in_figuers': total_amount,
                    'invoice_type_category': 'train_ticket',
                    # 添加火车票特有字段
                    'starting_station': train_data.get('starting_station', {}).get('word', ''),
                    'destination_station': train_data.get('destination_station', {}).get('word', ''),
                    'seat_category': train_data.get('seat_category', {}).get('word', ''),
                    'seat_num': train_data.get('seat_num', {}).get('word', ''),
                    'passenger_name': train_data.get('name', {}).get('word', ''),
                    'ID_card': train_data.get('ID_card', {}).get('word', ''),
                    'train_num': train_data.get('train_num', {}).get('word', ''),
                    'time': train_data.get('time', {}).get('word', ''),
                    'ticket_num': train_data.get('ticket_num', {}).get('word', ''),
                    'elec_ticket_num': train_data.get('elec_ticket_num', {}).get('word', ''),
                })
                # 火车票通常没有税率
                processed_data['tax_rates'] = ['0%']
        
        # 如果是简单的文字识别结果
        elif isinstance(words_result, list):
            all_words = []
            for item in words_result:
                if isinstance(item, dict) and 'words' in item:
                    all_words.append(item['words'])
            
            if all_words:
                processed_data.update({
                    'description': ' '.join(all_words)[:100] if all_words else 'OCR识别费用',
                    'vendor': '未知供应商',
                    'total_amount': 0.0,
                    'amount_in_figuers': 0.0,
                    'invoice_type_category': 'others',
                })
                # 默认没有税率
                processed_data['tax_rates'] = ['0%']
        
        return processed_data
    
    def _parse_amount(self, amount_str):
        """解析金额字符串为浮点数"""
        if not amount_str:
            return 0.0
            
        try:
            # 移除货币符号和逗号
            amount_str = str(amount_str).replace('¥', '').replace('￥', '').replace(',', '').strip()
            # 移除任何非数字字符除了小数点
            amount_str = ''.join(c for c in amount_str if c.isdigit() or c == '.')
            return float(amount_str) if amount_str else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def recognize_invoice_pdf(self, pdf_data):
        """处理PDF文件并识别发票"""
        self.ensure_one()
        
        # 确保我们有有效的访问令牌
        if not self.access_token or (self.token_expiry and self.token_expiry < fields.Datetime.now()):
            self.get_access_token()
        
        try:
            # 创建临时文件保存PDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf.write(pdf_data)
                temp_pdf_path = temp_pdf.name
            
            _logger.info("临时PDF文件已创建: %s", temp_pdf_path)
            
            # 尝试使用通用票据识别API（更适合发票）
            url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/multiple_invoice?access_token={self.access_token}"
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            # 读取PDF文件并转换为base64
            with open(temp_pdf_path, 'rb') as pdf_file:
                pdf_base64 = base64.b64encode(pdf_file.read()).decode('utf-8')
            
            # 删除临时文件
            os.unlink(temp_pdf_path)
            
            # 准备参数 - 使用PDF参数
            params = {
                "pdf_file": pdf_base64,
                "pdf_file_num": "1"  # 只处理第一页
            }
            data = urllib.parse.urlencode(params)
            
            # 发送请求
            response = requests.post(url, data=data, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            _logger.info("百度OCR PDF API返回结果: %s", result)
            
            if 'error_code' in result:
                # 如果通用票据识别API失败，尝试使用文档分析API
                if result.get('error_code') == 216201:  # 图片格式错误
                    _logger.info("尝试使用文档分析API处理PDF")
                    return self._recognize_pdf_with_doc_api(pdf_base64)
                else:
                    error_msg = result.get('error_msg', 'Unknown error')
                    error_code = result.get('error_code')
                    _logger.error("OCR PDF API错误: %s - %s", error_code, error_msg)
                    raise UserError(_("OCR PDF API错误: %s - %s") % (error_code, error_msg))
            
            return self._process_ocr_result(result)
            
        except Exception as e:
            _logger.error("PDF识别错误: %s", str(e))
            raise UserError(_("PDF识别错误: %s") % str(e))
    
    def _recognize_pdf_with_doc_api(self, pdf_base64):
        """使用文档分析API处理PDF"""
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/doc_analysis_office?access_token={self.access_token}"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        # 准备参数
        params = {
            "pdf_file": pdf_base64,
            "pdf_file_num": "1"  # 只处理第一页
        }
        data = urllib.parse.urlencode(params)
        
        # 发送请求
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        _logger.info("百度文档分析API返回结果: %s", result)
        
        if 'error_code' in result:
            error_msg = result.get('error_msg', 'Unknown error')
            error_code = result.get('error_code')
            _logger.error("文档分析API错误: %s - %s", error_code, error_msg)
            raise UserError(_("文档分析API错误: %s - %s") % (error_code, error_msg))
        
        # 将PDF识别结果转换为与图片识别结果相同的格式
        converted_result = self._convert_pdf_result_to_invoice_format(result)
        return self._process_ocr_result(converted_result)
    
    def _convert_pdf_result_to_invoice_format(self, pdf_result):
        """将PDF识别结果转换为发票格式"""
        _logger.info("转换PDF结果为发票格式: %s", pdf_result)
        
        # 初始化转换后的结果
        converted_result = {
            'words_result': []
        }
        
        try:
            if 'results' not in pdf_result:
                _logger.warning("PDF结果中没有results字段")
                return converted_result
            
            # 提取文本内容
            all_text = ""
            for page in pdf_result.get('results', []):
                for content in page.get('content', []):
                    all_text += content.get('text', '') + " "
            
            # 尝试从文本中提取税率
            tax_rates = self._extract_tax_rates_from_text(all_text)
            
            # 创建模拟的发票结果
            invoice_data = {
                'type': 'vat_invoice',
                'result': {
                    # 尝试从文本中提取关键信息
                    'SellerName': [{'word': self._extract_from_text(all_text, ['名称:', '销售方:', '供应商:'])}],
                    'SellerRegisterNum': [{'word': self._extract_from_text(all_text, ['税号:', '纳税人识别号:'])}],
                    'InvoiceDate': [{'word': self._extract_from_text(all_text, ['日期:', '开票日期:'])}],
                    'InvoiceNum': [{'word': self._extract_from_text(all_text, ['发票号码:', '号码:'])}],
                    'InvoiceCode': [{'word': self._extract_from_text(all_text, ['发票代码:', '代码:'])}],
                    'PurchaserName': [{'word': self._extract_from_text(all_text, ['购买方名称:', '客户名称:'])}],
                    'PurchaserRegisterNum': [{'word': self._extract_from_text(all_text, ['购买方税号:'])}],
                    'TotalAmount': [{'word': str(self._extract_amount_from_text(all_text, ['金额:', '合计金额:']))}],
                    'TotalTax': [{'word': str(self._extract_amount_from_text(all_text, ['税额:', '合计税额:']))}],
                    'AmountInFiguers': [{'word': str(self._extract_amount_from_text(all_text, ['价税合计:', '总计:']))}],
                    'AmountInWords': [{'word': self._extract_from_text(all_text, ['大写:', '人民币大写:'])}],
                    'CommodityTaxRate': self._format_tax_rates_for_api(tax_rates),
                }
            }
            
            converted_result['words_result'].append(invoice_data)
            _logger.info("转换后的发票数据: %s", invoice_data)
            
        except Exception as e:
            _logger.error("转换PDF结果错误: %s", str(e))
        
        return converted_result
    
    def _extract_tax_rates_from_text(self, text):
        """从文本中提取税率"""
        tax_rates = []
        
        # 常见的税率模式
        tax_patterns = [
            r'税率[：:]\s*(\d+)%',
            r'税率[：:]\s*(\d+)％',
            r'税率[：:]\s*(\d+)',
            r'(\d+)%税率',
            r'(\d+)％税率',
        ]
        
        for pattern in tax_patterns:
            import re
            matches = re.findall(pattern, text)
            for match in matches:
                tax_rate = f"{match}%"
                if tax_rate not in tax_rates:
                    tax_rates.append(tax_rate)
        
        return tax_rates
    
    def _format_tax_rates_for_api(self, tax_rates):
        """将税率列表格式化为API响应格式"""
        result = []
        for i, rate in enumerate(tax_rates):
            result.append({
                'row': str(i+1),
                'word': rate
            })
        return result
    
    def _extract_from_text(self, text, keywords):
        """从文本中提取关键信息"""
        if not text:
            return None
            
        text = text.lower()
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in text:
                # 找到关键词的位置
                pos = text.find(keyword_lower)
                # 提取关键词后面的内容，直到下一个标点符号或空格
                start = pos + len(keyword_lower)
                end = start
                while end < len(text) and text[end] not in ',:;，：；\n\r\t ':
                    end += 1
                
                value = text[start:end].strip()
                if value:
                    return value
        
        return None
    
    def _extract_amount_from_text(self, text, keywords):
        """从文本中提取金额"""
        value = self._extract_from_text(text, keywords)
        if value:
            try:
                # 移除非数字字符，保留小数点
                cleaned_value = ''.join(c for c in value if c.isdigit() or c == '.')
                return float(cleaned_value)
            except (ValueError, TypeError):
                pass
        
        return 0.0
    
    def _process_train_ticket_data(self, invoice_data, processed_data):
        """处理火车票特有数据"""
        # 提取火车票特有字段
        processed_data.update({
            'starting_station': self._extract_field_value(invoice_data, 'starting_station'),
            'destination_station': self._extract_field_value(invoice_data, 'destination_station'),
            'seat_category': self._extract_field_value(invoice_data, 'seat_category'),
            'seat_num': self._extract_field_value(invoice_data, 'seat_num'),
            'passenger_name': self._extract_field_value(invoice_data, 'name'),
            'ID_card': self._extract_field_value(invoice_data, 'ID_card'),
            'train_num': self._extract_field_value(invoice_data, 'train_num'),
            'time': self._extract_field_value(invoice_data, 'time'),
            'ticket_num': self._extract_field_value(invoice_data, 'ticket_num'),
            'elec_ticket_num': self._extract_field_value(invoice_data, 'elec_ticket_num'),
        })
        
        # 设置金额信息
        ticket_price = self._extract_amount(invoice_data, 'ticket_rates')
        if ticket_price > 0:
            processed_data['total_amount'] = ticket_price
            processed_data['amount_in_figuers'] = ticket_price
        
        # 设置描述
        starting = processed_data.get('starting_station') or ''
        destination = processed_data.get('destination_station') or ''
        train_num = processed_data.get('train_num') or ''
        if starting and destination:
            processed_data['description'] = f"火车票 {train_num} {starting}→{destination}"
        else:
            processed_data['description'] = f"火车票 {train_num}" 