# -*- coding: utf-8 -*-

import base64
import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# 票据类型映射表
TICKET_TYPE_MAPPING = {
    'vat_invoice': '增值税发票',
    'taxi_receipt': '出租车票',
    'train_ticket': '火车票',
    'quota_invoice': '定额发票',
    'air_ticket': '飞机行程单',
    'roll_normal_invoice': '卷票',
    'printed_invoice': '机打发票',
    'printed_elec_invoice': '机打电子发票',
    'bus_ticket': '汽车票',
    'toll_invoice': '过路过桥费发票',
    'ferry_ticket': '船票',
    'motor_vehicle_invoice': '机动车销售发票',
    'used_vehicle_invoice': '二手车发票',
    'taxi_online_ticket': '网约车行程单',
    'limit_invoice': '限额发票',
    'shopping_receipt': '购物小票',
    'pos_invoice': 'POS小票',
    'others': '其他',
}

class OcrUploadWizard(models.TransientModel):
    _name = 'ocr.upload.wizard'
    _description = 'OCR上传向导'
    
    invoice_file = fields.Binary('票据文件', required=True)
    filename = fields.Char('文件名')
    expense_id = fields.Many2one('hr.expense', '关联费用')
    expense_sheet_id = fields.Many2one('hr.expense.sheet', '关联费用报销单')
    
    @api.model
    def default_get(self, fields_list):
        """获取默认值"""
        res = super(OcrUploadWizard, self).default_get(fields_list)
        
        # 从上下文中获取关联的费用或费用报销单
        if self.env.context.get('default_expense_id'):
            res['expense_id'] = self.env.context.get('default_expense_id')
        elif self.env.context.get('default_expense_sheet_id'):
            res['expense_sheet_id'] = self.env.context.get('default_expense_sheet_id')
        # 兼容旧的上下文参数
        elif self.env.context.get('default_sheet_id'):
            res['expense_sheet_id'] = self.env.context.get('default_sheet_id')
            
        return res
    
    def action_upload_and_recognize(self):
        """上传并识别票据"""
        self.ensure_one()
        
        if not self.invoice_file:
            raise UserError(_('请先上传票据文件'))
        
        # 获取OCR配置
        config = self.env['baidu.ocr.config'].get_default_config()
        if not config:
            raise UserError(_('未找到有效的百度OCR配置，请先设置配置信息'))
        
        try:
            # 获取文件内容
            file_content = base64.b64decode(self.invoice_file)
            
            # 调用百度OCR API
            ocr_result = config.recognize_invoice(file_content)
            
            # 检查OCR结果
            if not ocr_result or 'words_result' not in ocr_result or not ocr_result['words_result']:
                raise UserError(_('OCR识别失败，未能识别出有效信息'))
            
            # 提取票据类型和结果
            first_result = ocr_result['words_result'][0]
            ticket_type = first_result.get('type', 'unknown')
            result_data = first_result.get('result', {})
            
            # 根据票据类型直接创建相应的独立模型记录
            if ticket_type == 'vat_invoice':
                return self._create_and_show_vat_invoice(ocr_result, result_data)
            elif ticket_type == 'train_ticket':
                return self._create_and_show_train_ticket(ocr_result, result_data)
            else:
                # 对于不支持的类型，创建通用费用记录
                return self._create_and_show_generic_expense(ocr_result, ticket_type, result_data)
                
        except Exception as e:
            _logger.exception("OCR识别过程中发生错误: %s", str(e))
            raise UserError(_('OCR识别失败: %s') % str(e))
    
    def _create_and_show_vat_invoice(self, ocr_result, result_data):
        """创建并显示增值税发票"""
        # 创建增值税发票记录
        vat_invoice = self.env['vat.invoice'].create_from_ocr_data(ocr_result, 0)
        
        # 同时创建费用记录
        expense_data = self._prepare_vat_invoice_data(result_data)
        product = self._find_or_create_expense_product('增值税发票')
        expense_data['product_id'] = product.id
        expense = self.env['hr.expense'].create(expense_data)
        
        # 关联记录
        vat_invoice.expense_id = expense.id
        
        # 如果有关联的费用报销单，将新费用添加到报销单中
        if self.expense_sheet_id:
            expense.sheet_id = self.expense_sheet_id.id
        
        # 返回跳转到增值税发票视图
        return {
            'type': 'ir.actions.act_window',
            'name': _('增值税发票 - OCR识别结果'),
            'res_model': 'vat.invoice',
            'res_id': vat_invoice.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
        }
    
    def _create_and_show_train_ticket(self, ocr_result, result_data):
        """创建并显示火车票"""
        # 创建火车票记录
        train_ticket = self.env['train.ticket'].create_from_ocr_data(ocr_result, 0)
        
        # 同时创建费用记录
        expense_data = self._prepare_train_ticket_data(result_data)
        product = self._find_or_create_expense_product('火车票')
        expense_data['product_id'] = product.id
        expense = self.env['hr.expense'].create(expense_data)
        
        # 关联记录
        train_ticket.expense_id = expense.id
        
        # 如果有关联的费用报销单，将新费用添加到报销单中
        if self.expense_sheet_id:
            expense.sheet_id = self.expense_sheet_id.id
        
        # 返回跳转到火车票视图
        return {
            'type': 'ir.actions.act_window',
            'name': _('火车票 - OCR识别结果'),
            'res_model': 'train.ticket',
            'res_id': train_ticket.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
        }
    
    def _create_and_show_generic_expense(self, ocr_result, ticket_type, result_data):
        """创建并显示通用费用记录"""
        # 创建费用记录
        expense_data = self._prepare_other_ticket_data(result_data, ticket_type)
        # 获取票据类型的中文名称
        ticket_type_name = TICKET_TYPE_MAPPING.get(ticket_type, '其他票据')
        product = self._find_or_create_expense_product(ticket_type_name)
        expense_data['product_id'] = product.id
        expense = self.env['hr.expense'].create(expense_data)
        
        # 如果有关联的费用报销单，将新费用添加到报销单中
        if self.expense_sheet_id:
            expense.sheet_id = self.expense_sheet_id.id
        
        # 返回跳转到费用表单
        return {
            'type': 'ir.actions.act_window',
            'name': _('费用记录 - OCR识别结果'),
            'res_model': 'hr.expense',
            'res_id': expense.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
        }
    
    def _create_expense_from_ocr(self, ocr_result, ticket_type, result_data):
        """从OCR结果创建费用记录"""
        
        # 根据票据类型处理基本信息
        if ticket_type == 'vat_invoice':
            expense_data = self._prepare_vat_invoice_data(result_data)
            # 创建增值税发票记录
            self.env['vat.invoice'].create_from_ocr_data(ocr_result, 0)  # 临时传0，后面会更新
        elif ticket_type == 'train_ticket':
            expense_data = self._prepare_train_ticket_data(result_data)
            # 创建火车票记录
            self.env['train.ticket'].create_from_ocr_data(ocr_result, 0)  # 临时传0，后面会更新
        else:
            expense_data = self._prepare_other_ticket_data(result_data, ticket_type)
        
        # 查找或创建产品
        ticket_type_name = TICKET_TYPE_MAPPING.get(ticket_type, '其他票据')
        product = self._find_or_create_expense_product(ticket_type_name)
        expense_data['product_id'] = product.id
        
        # 创建费用记录
        expense = self.env['hr.expense'].create(expense_data)
        
        # 更新独立模型记录的expense_id
        if ticket_type == 'vat_invoice':
            vat_invoice = self.env['vat.invoice'].search([('expense_id', '=', 0)], limit=1, order='id desc')
            if vat_invoice:
                vat_invoice.expense_id = expense.id
        elif ticket_type == 'train_ticket':
            train_ticket = self.env['train.ticket'].search([('expense_id', '=', 0)], limit=1, order='id desc')
            if train_ticket:
                train_ticket.expense_id = expense.id
        
        return expense
    
    def _prepare_vat_invoice_data(self, result_data):
        """准备增值税发票的费用数据"""
        invoice_num = self._get_first_value(result_data.get('InvoiceNum', []))
        vendor_name = self._get_first_value(result_data.get('SellerName', []))
        amount_str = self._get_first_value(result_data.get('AmountInFiguers', []))
        invoice_date_str = self._get_first_value(result_data.get('InvoiceDate', []))
        commodity_name = self._get_first_value(result_data.get('CommodityName', []))
        
        # 提取总金额
        total_amount_str = self._get_first_value(result_data.get('TotalAmount', []))
        
        try:
            amount = float(amount_str.replace(',', '')) if amount_str else 0.0
            total_amount = float(total_amount_str.replace(',', '')) if total_amount_str else amount
        except (ValueError, TypeError):
            amount = 0.0
            total_amount = 0.0
        
        # 解析日期
        parsed_date = self._parse_date(invoice_date_str) or fields.Date.today()
        
        return {
            'name': commodity_name or vendor_name or f"发票 {invoice_num}",
            'total_amount': total_amount,  # 公司币种的总金额
            'total_amount_currency': total_amount,  # 原始币种的总金额
            'price_unit': total_amount,  # 单价
            'quantity': 1.0,  # 数量
            'date': parsed_date,
            'description': f"发票号码: {invoice_num}",
            'ocr_recognized': True,
            'ocr_invoice_type': 'vat_invoice',
            'invoice_number': invoice_num,
            'vendor_name': vendor_name,
            'invoice_date': parsed_date,  # 使用解析后的日期
            'amount_in_figures': amount_str,
            'total_tax': self._get_first_value(result_data.get('TotalTax', [])),
            'tax_rate': self._process_tax_rates(result_data.get('CommodityTaxRate', [])),
            'amount_in_words': self._get_first_value(result_data.get('AmountInWords', [])),
            'note_drawer': self._get_first_value(result_data.get('NoteDrawer', [])),
            'purchaser_name': self._get_first_value(result_data.get('PurchaserName', [])),
            'purchaser_register_num': self._get_first_value(result_data.get('PurchaserRegisterNum', [])),
            'seller_register_num': self._get_first_value(result_data.get('SellerRegisterNum', [])),
        }
    
    def _prepare_train_ticket_data(self, result_data):
        """准备火车票的费用数据"""
        train_number = self._get_first_value(result_data.get('TrainNum', []))
        origin = self._get_first_value(result_data.get('StartingStation', []))
        destination = self._get_first_value(result_data.get('DestinationStation', []))
        amount_str = self._get_first_value(result_data.get('TicketPrice', []))
        date_str = self._get_first_value(result_data.get('Date', []))
        
        try:
            amount = float(amount_str.replace(',', '')) if amount_str else 0.0
        except (ValueError, TypeError):
            amount = 0.0
        
        # 解析日期
        parsed_date = self._parse_date(date_str) or fields.Date.today()
        
        return {
            'name': f"火车票 {origin}-{destination}",
            'total_amount': amount,  # 公司币种的总金额
            'total_amount_currency': amount,  # 原始币种的总金额
            'price_unit': amount,  # 单价
            'quantity': 1.0,  # 数量
            'date': parsed_date,
            'description': f"车次: {train_number}, {origin} → {destination}",
            'ocr_recognized': True,
            'ocr_invoice_type': 'train_ticket',
            'train_number': train_number,
            'departure_station': origin,
            'arrival_station': destination,
            'departure_time': self._get_first_value(result_data.get('DepartureTime', [])),
            'seat_class': self._get_first_value(result_data.get('PassengerClass', [])),
            'passenger_name': self._get_first_value(result_data.get('PassengerName', [])),
            'passenger_id': self._get_first_value(result_data.get('PassengerIdNum', [])),
            'invoice_date': parsed_date,  # 使用解析后的日期
        }
    
    def _prepare_other_ticket_data(self, result_data, ticket_type):
        """准备其他类型票据的费用数据"""
        # 通用字段提取
        amount_str = (self._get_first_value(result_data.get('TotalAmount', [])) or 
                     self._get_first_value(result_data.get('Amount', [])) or 
                     self._get_first_value(result_data.get('TicketPrice', [])))
        
        # 提取日期
        date_str = (self._get_first_value(result_data.get('Date', [])) or 
                   self._get_first_value(result_data.get('InvoiceDate', [])) or 
                   self._get_first_value(result_data.get('Time', [])))
        
        try:
            amount = float(amount_str.replace(',', '')) if amount_str else 0.0
        except (ValueError, TypeError):
            amount = 0.0
        
        # 获取票据类型的中文名称
        ticket_type_name = TICKET_TYPE_MAPPING.get(ticket_type, '其他票据')
        
        # 解析日期
        parsed_date = self._parse_date(date_str) or fields.Date.today()
        
        return {
            'name': f"{ticket_type_name}",
            'total_amount': amount,  # 公司币种的总金额
            'total_amount_currency': amount,  # 原始币种的总金额
            'price_unit': amount,  # 单价
            'quantity': 1.0,  # 数量
            'date': parsed_date,
            'description': f"OCR识别的{ticket_type_name}",
            'ocr_recognized': True,
            'ocr_invoice_type': ticket_type,
            'invoice_date': parsed_date,  # 使用解析后的日期
        }
    
    def _find_or_create_expense_product(self, name):
        """查找或创建费用产品"""
        # 先尝试查找现有的费用产品
        product = self.env['product.product'].search([
            ('name', 'ilike', name),
            ('detailed_type', '=', 'service')
        ], limit=1)
        
        if not product:
            # 查找默认的费用产品类别
            category = self.env.ref('product.cat_expense', raise_if_not_found=False)
            if not category:
                category = self.env['product.category'].search([], limit=1)
            
            # 创建新的费用产品
            product = self.env['product.product'].create({
                'name': name,
                'detailed_type': 'service',
                'categ_id': category.id,
                'sale_ok': False,
                'purchase_ok': True,
            })
        
        return product
    
    def _process_tax_rates(self, tax_rates):
        """处理税率信息"""
        if not tax_rates or not isinstance(tax_rates, list):
            return ""
            
        # 提取所有税率值
        rates = []
        for rate in tax_rates:
            if isinstance(rate, dict) and 'word' in rate:
                rates.append(rate['word'])
                
        if not rates:
            return ""
            
        # 检查是否所有税率都相同
        unique_rates = set(rates)
        if len(unique_rates) == 1:
            return rates[0]
        else:
            return "混合税率"
    
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
        import logging
        
        _logger = logging.getLogger(__name__)
        _logger.info("尝试解析日期: %s", date_str)
        
        # 尝试匹配常见的日期格式
        patterns = [
            # 2025年05月23日
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            # 2025年05月23
            r'(\d{4})年(\d{1,2})月(\d{1,2})',
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
                        date_obj = datetime(int(year), int(month), int(day))
                        result = fields.Date.to_string(date_obj)
                        _logger.info("成功解析日期: %s -> %s", date_str, result)
                        return result
                    except ValueError as e:
                        _logger.warning("日期值错误: %s, 错误: %s", date_str, str(e))
                        continue
        
        # 如果上面的模式都不匹配，尝试匹配只有年月的格式
        year_month_patterns = [
            # 2025年05月
            r'(\d{4})年(\d{1,2})月',
            # 2025-05
            r'(\d{4})-(\d{1,2})',
            # 2025/05
            r'(\d{4})/(\d{1,2})',
        ]
        
        for pattern in year_month_patterns:
            match = re.search(pattern, date_str)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    year, month = groups
                    
                    try:
                        # 使用月份的第一天作为默认日期
                        date_obj = datetime(int(year), int(month), 1)
                        result = fields.Date.to_string(date_obj)
                        _logger.info("成功解析年月日期: %s -> %s", date_str, result)
                        return result
                    except ValueError as e:
                        _logger.warning("年月日期值错误: %s, 错误: %s", date_str, str(e))
                        continue
        
        # 如果以上都不匹配，尝试直接使用fields.Date.to_date
        try:
            # 尝试直接转换
            result = fields.Date.to_date(date_str)
            if result:
                _logger.info("使用Odoo内置函数解析日期成功: %s -> %s", date_str, result)
                return result
        except Exception as e:
            _logger.warning("Odoo内置日期解析失败: %s, 错误: %s", date_str, str(e))
        
        _logger.warning("无法解析日期: %s，使用今天的日期", date_str)
        return fields.Date.today()