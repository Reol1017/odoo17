import base64
import urllib.parse
import requests
import json
import logging
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
    
    def recognize_invoice(self, file_data):
        """识别发票使用百度OCR API - 支持图片和PDF"""
        self.ensure_one()
        
        # 确保我们有有效的访问令牌
        if not self.access_token or (self.token_expiry and self.token_expiry < fields.Datetime.now()):
            self.get_access_token()
        
        # 检测文件类型
        is_pdf = self._is_pdf_data(file_data)
        file_type = "PDF" if is_pdf else "图片"
        
        print(f"🔍 开始识别 {file_type} 文件，大小: {len(file_data)} 字节")
        
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/multiple_invoice?access_token={self.access_token}"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        # 准备文件数据 - 百度OCR支持base64编码的图片和PDF
        file_base64 = base64.b64encode(file_data).decode('utf-8')
        
        # 根据文件类型设置参数
        if is_pdf:
            # PDF参数
            params = {
                "pdf_file": file_base64,
                "pdf_file_num": "1"  # 处理第一页
            }
            print("📄 使用PDF模式识别")
        else:
            # 图片参数
            params = {
                "image": file_base64
            }
            print("🖼️ 使用图片模式识别")
        
        data = urllib.parse.urlencode(params)
        
        try:
            response = requests.post(url, data=data, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            print(f"✅ 百度OCR API返回结果 ({file_type}):")
            _logger.info("百度OCR API返回结果: %s", result)
            
            if 'error_code' in result:
                error_msg = result.get('error_msg', 'Unknown error')
                error_code = result.get('error_code')
                _logger.error("OCR API error: %s - %s", error_code, error_msg)
                raise UserError(_("OCR API error: %s - %s") % (error_code, error_msg))
            
            return self._process_ocr_result(result)
        except Exception as e:
            _logger.error("Error recognizing %s: %s", file_type, str(e))
            raise UserError(_("Error recognizing %s: %s") % (file_type, str(e)))
    
    def _is_pdf_data(self, file_data):
        """检测文件数据是否为PDF格式"""
        # PDF文件以 %PDF- 开头
        if len(file_data) >= 4:
            return file_data[:4] == b'%PDF'
        return False
    
    def _process_ocr_result(self, result):
        """处理OCR结果 - 简化版本"""
        import json
        
        # 完整显示接收到的原始数据
        _logger.info("=" * 80)
        _logger.info("OCR API 完整原始返回结果:")
        _logger.info("=" * 80)
        _logger.info(json.dumps(result, ensure_ascii=False, indent=2))
        _logger.info("=" * 80)
        
        print("=" * 80)
        print("OCR API 完整原始返回结果:")
        print("=" * 80)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("=" * 80)
        
        # 初始化处理后的数据
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
            'commodity_type': None,
            'commodity_unit': None,
            'commodity_num': None,
            'commodity_price': 0.0,
            'commodity_amount': 0.0,
            'commodity_tax_rate': None,
            'commodity_tax': 0.0,
            'total_tax': 0.0,
            'amount_in_words': None,
            'drawer': None,
        }
        
        if 'words_result' not in result:
            print("⚠️ OCR结果中没有words_result字段")
            _logger.warning("OCR结果中没有words_result字段")
            processed_data.update({
                'description': 'OCR识别费用',
                'total_amount': 0.0,
                'vendor': '未知供应商'
            })
            return processed_data

        words_result = result['words_result']
        print(f"✓ 获取到 words_result，类型: {type(words_result)}")
        
        # 处理多发票识别结果
        if isinstance(words_result, list) and len(words_result) > 0:
            # 取第一个发票的识别结果
            first_invoice = words_result[0]
            
            if 'result' in first_invoice:
                invoice_data = first_invoice['result']
                invoice_type = first_invoice.get('type', 'unknown')
                
                print(f"\n处理发票类型: {invoice_type}")
                
                # 安全提取字段值
                def safe_extract(data, field_name):
                    """安全提取字段值"""
                    if field_name not in data:
                        return None
                    field_data = data[field_name]
                    if not field_data or not isinstance(field_data, list) or len(field_data) == 0:
                        return None
                    first_item = field_data[0]
                    if isinstance(first_item, dict) and 'word' in first_item:
                        return first_item['word']
                    return None

                def safe_extract_amount(data, field_name):
                    """安全提取金额"""
                    value = safe_extract(data, field_name)
                    if not value:
                        return 0.0
                    try:
                        # 清理金额字符串
                        amount_str = str(value).replace('¥', '').replace(',', '').replace('￥', '')
                        amount_str = ''.join(c for c in amount_str if c.isdigit() or c == '.' or c == '-')
                        return float(amount_str) if amount_str else 0.0
                    except (ValueError, TypeError):
                        return 0.0

                # 提取所有字段 - 修正字段映射
                processed_data.update({
                    'invoice_type': invoice_type,
                    'vendor': safe_extract(invoice_data, 'SellerName'),
                    'seller_name': safe_extract(invoice_data, 'SellerName'),
                    'seller_register_num': safe_extract(invoice_data, 'SellerRegisterNum'),
                    'purchaser_name': safe_extract(invoice_data, 'PurchaserName'),
                    'purchaser_register_num': safe_extract(invoice_data, 'PurchaserRegisterNum'),
                    'date': safe_extract(invoice_data, 'InvoiceDate'),
                    'invoice_date': safe_extract(invoice_data, 'InvoiceDate'),
                    'invoice_number': safe_extract(invoice_data, 'InvoiceNum'),
                    'invoice_code': safe_extract(invoice_data, 'InvoiceCode'),
                    'drawer': safe_extract(invoice_data, 'NoteDrawer'),
                    # 修正金额字段映射
                    'total_amount': safe_extract_amount(invoice_data, 'AmountInFiguers'),  # 含税总金额583.05
                    'amount_without_tax': safe_extract_amount(invoice_data, 'TotalAmount'),  # 不含税金额550.05
                    'tax_amount': safe_extract_amount(invoice_data, 'TotalTax'),  # 税额33.00
                    'total_tax': safe_extract_amount(invoice_data, 'TotalTax'),
                    'amount_in_words': safe_extract(invoice_data, 'AmountInWords'),
                    'commodity_name': safe_extract(invoice_data, 'CommodityName'),
                    'commodity_type': safe_extract(invoice_data, 'CommodityType'),
                    'commodity_tax_rate': safe_extract(invoice_data, 'CommodityTaxRate'),
                    'commodity_tax': safe_extract_amount(invoice_data, 'CommodityTax'),
                })

                print(f"\n✅ 修正后的字段映射:")
                print(f"  AmountInFiguers (含税总金额): {safe_extract_amount(invoice_data, 'AmountInFiguers')}")
                print(f"  TotalAmount (不含税金额): {safe_extract_amount(invoice_data, 'TotalAmount')}")
                print(f"  TotalTax (税额): {safe_extract_amount(invoice_data, 'TotalTax')}")
                print(f"  CommodityTaxRate (税率): {safe_extract(invoice_data, 'CommodityTaxRate')}")
                print(f"  CommodityTax (商品税额): {safe_extract_amount(invoice_data, 'CommodityTax')}")

                # 简化商品名称
                if processed_data.get('commodity_name'):
                    commodity_name = processed_data['commodity_name']
                    # 移除*号
                    commodity_name = str(commodity_name).replace('*', '')
                    # 如果包含服务，截取到服务为止
                    if '服务' in commodity_name:
                        service_index = commodity_name.find('服务')
                        if service_index >= 0:
                            commodity_name = commodity_name[:service_index + 2]
                    processed_data['commodity_name'] = commodity_name.strip()

                processed_data['description'] = processed_data.get('commodity_name', 'OCR识别费用')
        
        # 确保必要字段有默认值
        if not processed_data.get('vendor'):
            processed_data['vendor'] = '未知供应商'
        if not processed_data.get('description'):
            processed_data['description'] = 'OCR识别费用'
        if not processed_data.get('total_amount'):
            processed_data['total_amount'] = 0.0
            
        print(f"\n" + "=" * 60)
        print("最终处理结果:")
        print("=" * 60)
        for key, value in processed_data.items():
            print(f"  {key}: {value}")
        print("=" * 60 + "\n")
            
        _logger.info("最终处理结果: %s", processed_data)
        return processed_data