# -*- coding: utf-8 -*-

import base64
import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

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
        if self.env.context.get('default_expense_sheet_id'):
            res['expense_sheet_id'] = self.env.context.get('default_expense_sheet_id')
            
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
            
            # 根据票据类型处理
            if ticket_type == 'vat_invoice':
                return self._process_vat_invoice(result_data, ocr_result)
            elif ticket_type == 'train_ticket':
                return self._process_train_ticket(result_data, ocr_result)
            else:
                raise UserError(_('不支持的票据类型: %s') % ticket_type)
                
        except Exception as e:
            _logger.exception("OCR识别过程中发生错误: %s", str(e))
            raise UserError(_('OCR识别失败: %s') % str(e))
    
    def _process_vat_invoice(self, result_data, raw_data):
        """处理增值税发票并创建费用记录"""
        # 提取发票信息
        invoice_num = self._get_first_value(result_data.get('InvoiceNum', []))
        invoice_code = self._get_first_value(result_data.get('InvoiceCode', []))
        invoice_date_str = self._get_first_value(result_data.get('InvoiceDate', []))
        invoice_date = self._parse_date(invoice_date_str)
        
        # 提取金额信息 - 使用TotalAmount替代AmountInFiguers
        total_amount_str = self._get_first_value(result_data.get('TotalAmount', []))
        total_amount = float(total_amount_str) if total_amount_str else 0.0
        
        # 提取含税价格
        amount_in_figures_str = self._get_first_value(result_data.get('AmountInFiguers', []))
        amount_in_figures = float(amount_in_figures_str) if amount_in_figures_str else 0.0
        
        # 提取税额合计
        total_tax_str = self._get_first_value(result_data.get('TotalTax', []))
        total_tax = float(total_tax_str) if total_tax_str else 0.0
        
        # 提取价税合计大写
        amount_in_words = self._get_first_value(result_data.get('AmountInWords', []))
        
        # 提取开票人
        note_drawer = self._get_first_value(result_data.get('NoteDrawer', []))
        
        # 提取税率
        tax_rate = self._process_tax_rates(result_data.get('CommodityTaxRate', []))
        
        # 提取备注
        remarks = self._get_first_value(result_data.get('Remarks', []))
        
        # 提取销售方和购买方信息
        vendor_name = self._get_first_value(result_data.get('SellerName', []))
        vendor_tax_id = self._get_first_value(result_data.get('SellerRegisterNum', []))
        purchaser_name = self._get_first_value(result_data.get('PurchaserName', []))
        purchaser_tax_id = self._get_first_value(result_data.get('PurchaserRegisterNum', []))
        
        # 商品名称
        commodity_name = self._get_first_value(result_data.get('CommodityName', []))
        
        # 创建增值税发票记录（用于参考）
        vat_invoice = self.env['vat.invoice'].create({
            'name': f"发票 {invoice_num or ''}",
            'invoice_number': invoice_num,
            'invoice_code': invoice_code,
            'invoice_date': invoice_date,
            'amount': total_amount,
            'vendor_name': vendor_name,
            'vendor_tax_id': vendor_tax_id,
            'purchaser_name': purchaser_name,
            'purchaser_tax_id': purchaser_tax_id,
            'commodity_name': commodity_name,
            'tax_rate': float(tax_rate.replace('%', '')) if tax_rate and '%' in tax_rate else 0.0,
            'tax_amount': total_tax,
            'amount_in_words': amount_in_words,
            'drawer': note_drawer,
            'remarks': remarks,
            'ocr_raw_data': json.dumps(raw_data, ensure_ascii=False, indent=2)
        })
        
        # 查找或创建产品
        product = self._find_or_create_expense_product(commodity_name or vendor_name or '其他费用')
        
        # 准备OCR数据
        description = remarks if remarks else ""
        
        ocr_data = {
            'name': commodity_name or f"{vendor_name} 的费用",
            'date': invoice_date or fields.Date.today(),
            'total_amount': total_amount,
            'product_id': product.id,
            'description': description,
            'invoice_code': invoice_code,
            'invoice_number': invoice_num,
            'vendor_name': vendor_name,
            'invoice_date': invoice_date,
            'note_drawer': note_drawer,
            'total_tax': total_tax,
            'amount_in_figures': amount_in_figures,
            'amount_in_words': amount_in_words,
            'tax_rate': tax_rate,
            'remarks': remarks,
            'purchaser_name': purchaser_name,
            'purchaser_register_num': purchaser_tax_id,
            'seller_register_num': vendor_tax_id,
            'ocr_recognized': True,  # 确保设置OCR识别标志
        }
        
        # 准备附件数据
        attachment = None
        if self.invoice_file:
            attachment = {
                'name': self.filename or f"发票_{invoice_num}.pdf",
                'datas': self.invoice_file,
            }
        
        # 创建费用记录
        expense = self.env['hr.expense'].create_from_ocr_data(ocr_data, attachment)
        
        # 如果有关联的费用报销单，将新费用添加到报销单中
        if self.expense_sheet_id:
            expense.sheet_id = self.expense_sheet_id.id
        
        # 返回跳转到费用表单的动作
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense',
            'res_id': expense.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
        }
    
    def _process_train_ticket(self, result_data, raw_data):
        """处理火车票并创建费用记录"""
        # 提取车票信息
        ticket_number = self._get_first_value(result_data.get('InvoiceNum', []))
        train_number = self._get_first_value(result_data.get('TrainNum', []))
        departure_date_str = self._get_first_value(result_data.get('Date', []))
        departure_date = self._parse_date(departure_date_str)
        
        # 提取金额信息
        amount_str = self._get_first_value(result_data.get('Amount', []))
        amount = float(amount_str) if amount_str else 0.0
        
        # 提取行程信息
        origin = self._get_first_value(result_data.get('Origin', []))
        destination = self._get_first_value(result_data.get('Destination', []))
        
        # 创建火车票记录（用于参考）
        train_ticket = self.env['train.ticket'].create({
            'name': f"火车票 {train_number or ''}",
            'ticket_number': ticket_number,
            'train_number': train_number,
            'date': departure_date,
            'amount': amount,
            'origin': origin,
            'destination': destination,
            'ocr_raw_data': json.dumps(raw_data, ensure_ascii=False, indent=2)
        })
        
        # 查找或创建产品
        product = self._find_or_create_expense_product('火车票')
        
        # 准备OCR数据
        reference_info = f"车次: {train_number}" if train_number else f"{origin} - {destination}"
        description = f"车次: {train_number}\n出发站: {origin}\n到达站: {destination}\n车票号: {ticket_number}\n参考: {reference_info}"
        
        # 为火车票设置所有必要的字段，避免界面上出现空白
        ocr_data = {
            'name': f"火车票 {origin} 到 {destination}",
            'date': departure_date or fields.Date.today(),
            'total_amount': amount,  # 使用total_amount替代amount
            'amount_in_figures': amount,  # 设置含税价格
            'product_id': product.id,
            'description': description,
            'remarks': description,  # 添加备注
            'ocr_recognized': True,  # 确保设置OCR识别标志
            
            # 设置其他必要字段，即使为空
            'invoice_number': ticket_number,
            'invoice_code': '',
            'invoice_date': departure_date,
            'note_drawer': '',
            'total_tax': 0.0,
            'amount_in_words': '',
            'tax_rate': '',
            'purchaser_name': '',
            'purchaser_register_num': '',
            'vendor_name': f"火车票 {train_number}",
            'seller_register_num': '',
        }
        
        # 准备附件数据
        attachment = None
        if self.invoice_file:
            attachment = {
                'name': self.filename or f"火车票_{train_number}.pdf",
                'datas': self.invoice_file,
            }
        
        # 创建费用记录
        expense = self.env['hr.expense'].create_from_ocr_data(ocr_data, attachment)
        
        # 如果有关联的费用报销单，将新费用添加到报销单中
        if self.expense_sheet_id:
            expense.sheet_id = self.expense_sheet_id.id
        
        # 返回跳转到费用表单的动作
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense',
            'res_id': expense.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
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
        """处理税率信息
        如果所有税率都相同，返回该税率
        如果有不同的税率，返回"混合税率"
        """
        if not tax_rates or not isinstance(tax_rates, list):
            return ""
            
        # 提取所有税率值
        rates = []
        for rate in tax_rates:
            if isinstance(rate, dict) and 'word' in rate:
                rates.append(rate['word'])
                
        # 如果没有税率，返回空字符串
        if not rates:
            return ""
            
        # 检查是否所有税率都相同
        unique_rates = set(rates)
        if len(unique_rates) == 1:
            return rates[0]  # 返回唯一的税率
        else:
            return "混合税率"  # 返回混合税率
    
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