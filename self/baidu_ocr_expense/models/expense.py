# -*- coding: utf-8 -*-

import base64
import logging
import re
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import os

_logger = logging.getLogger(__name__)

class HrExpense(models.Model):
    _inherit = 'hr.expense'
    
    # Odoo 17 兼容性字段 - 添加直接字段而不是计算字段
    unit_amount = fields.Float(string='单价', digits='Product Price')
    amount = fields.Monetary(string='金额')
    
    # 发票类型分类
    INVOICE_TYPE_CATEGORIES = [
        ('vat_invoice', '增值税发票'),
        ('taxi_receipt', '出租车票'),
        ('train_ticket', '火车票'),
        ('quota_invoice', '定额发票'),
        ('air_ticket', '飞机行程单'),
        ('roll_normal_invoice', '卷票'),
        ('printed_invoice', '机打发票'),
        ('printed_elec_invoice', '机打电子发票'),
        ('bus_ticket', '汽车票'),
        ('toll_invoice', '过路过桥费发票'),
        ('ferry_ticket', '船票'),
        ('motor_vehicle_invoice', '机动车销售发票'),
        ('used_vehicle_invoice', '二手车发票'),
        ('taxi_online_ticket', '网约车行程单'),
        ('limit_invoice', '限额发票'),
        ('shopping_receipt', '购物小票'),
        ('pos_invoice', 'POS小票'),
        ('others', '其他'),
    ]
    
    invoice_type_category = fields.Selection(
        INVOICE_TYPE_CATEGORIES, 
        string='发票类型分类',
        default='vat_invoice',
        help='OCR识别的发票类型分类'
    )
    
    # 中国发票字段
    vat_invoice_code = fields.Char(string='发票代码')
    vat_invoice_number = fields.Char(string='发票号码')
    vat_invoice_date = fields.Date(string='发票日期')
    vat_invoice_type = fields.Char(string='发票类型')
    vat_vendor_name = fields.Char(string='供应商名称')
    vat_vendor_tax_id = fields.Char(string='供应商税号')
    vat_purchaser_name = fields.Char(string='购买方名称')
    vat_purchaser_tax_id = fields.Char(string='购买方税号')
    vat_drawer = fields.Char(string='开票人')
    vat_service_type = fields.Char(string='服务类型')
    vat_tax_rate = fields.Char(string='发票税率')  # 改为Char类型，不与原生税率关联
    vat_tax_amount = fields.Monetary(string='发票税额')
    vat_amount_with_tax = fields.Monetary(string='含税金额')
    vat_amount_in_words = fields.Char(string='金额大写')
    
    # 火车票专用字段
    train_starting_station = fields.Char(string='出发站')
    train_destination_station = fields.Char(string='到达站')
    train_seat_category = fields.Char(string='座位类型')
    train_seat_num = fields.Char(string='座位号')
    train_passenger_name = fields.Char(string='乘客姓名')
    train_passenger_id = fields.Char(string='乘客身份证')
    train_num = fields.Char(string='车次')
    train_time = fields.Char(string='发车时间')
    train_ticket_num = fields.Char(string='车票号')
    train_elec_ticket_num = fields.Char(string='电子票号')
    
    # OCR相关字段
    ocr_extracted = fields.Boolean(string='OCR提取', default=False)
    ocr_raw_data = fields.Text(string='OCR原始数据', readonly=True)
    
    # 在Odoo 17中使用total_amount字段
    total_amount = fields.Monetary(string='总计', compute='_compute_total_amount', store=True)
    
    # 标记是否为多种税率
    has_multiple_tax_rates = fields.Boolean(string='多种税率', default=False)
    
    @api.depends('amount', 'quantity')
    def _compute_total_amount(self):
        """计算总金额 - Odoo 17 兼容性计算"""
        for expense in self:
            expense.total_amount = expense.amount * expense.quantity if expense.amount else 0.0
    
    @api.onchange('vat_amount_with_tax')
    def _onchange_vat_amount_with_tax(self):
        """当OCR识别的含税金额变化时，同步到原生总计字段"""
        if self.ocr_extracted and self.vat_amount_with_tax:
            # 更新总金额和单价
            self.total_amount = self.vat_amount_with_tax
            # 根据数量计算单价
            if self.quantity and self.quantity > 0:
                self.unit_amount = self.vat_amount_with_tax / self.quantity
            else:
                self.unit_amount = self.vat_amount_with_tax
            # 设置金额等于总计（因为税额已经包含在内）
            self.amount = self.vat_amount_with_tax
    
    @api.onchange('total_amount', 'amount')
    def _onchange_total_amount(self):
        """当原生总计或金额变化时，同步到OCR识别的含税金额"""
        if self.ocr_extracted:
            # 如果总计变化，同步到含税金额
            if self.total_amount:
                self.vat_amount_with_tax = self.total_amount
            # 如果金额变化，同步到含税金额
            elif self.amount:
                self.vat_amount_with_tax = self.amount
    
    @api.onchange('vat_tax_rate')
    def _onchange_vat_tax_rate(self):
        """当OCR识别的税率变化时，如果不是多种税率，同步到原生税率"""
        if self.ocr_extracted and self.vat_tax_rate and self.vat_tax_rate != "多种税率":
            # 尝试提取数字部分
            try:
                # 移除%符号并转换为数字
                tax_rate_str = self.vat_tax_rate.replace('%', '').replace('％', '').strip()
                tax_rate = float(tax_rate_str)
                # 更新原生税率（如果有相关字段）
                if hasattr(self, 'tax_ids'):
                    # 查找对应税率的税收记录
                    tax = self.env['account.tax'].search([
                        ('type_tax_use', '=', 'purchase'),
                        ('amount', '=', tax_rate),
                        ('company_id', '=', self.company_id.id)
                    ], limit=1)
                    if tax:
                        self.tax_ids = [(6, 0, [tax.id])]
            except (ValueError, AttributeError):
                pass
    
    @api.model
    def create_from_ocr(self, attachment_id):
        """根据OCR数据创建费用记录"""
        attachment = self.env['ir.attachment'].browse(attachment_id)
        if not attachment.exists():
            raise UserError(_("附件未找到"))
        
        # 获取OCR配置
        ocr_config = self.env['baidu.ocr.config'].search([
            ('company_id', '=', self.env.company.id),
            ('active', '=', True)
        ], limit=1)
        
        if not ocr_config:
            raise UserError(_("未找到百度OCR配置"))
        
        # 获取文件数据
        file_data = base64.b64decode(attachment.datas)
        file_name = attachment.name
        file_extension = ''
        
        if file_name:
            file_extension = os.path.splitext(file_name)[1].lower()
        
        # 检查文件内容的前几个字节来确定文件类型
        is_pdf = False
        if file_extension == '.pdf' or (len(file_data) > 4 and file_data[0:4] == b'%PDF'):
            is_pdf = True
        
        # 处理PDF文件
        if is_pdf:
            _logger.info("处理PDF文件: %s", file_name)
            try:
                # 调用PDF处理方法
                result = ocr_config.recognize_invoice_pdf(file_data)
            except Exception as e:
                _logger.error("PDF处理错误: %s", str(e))
                raise UserError(_("PDF处理错误: %s") % str(e))
        else:
            # 处理图片文件
            _logger.info("处理图片文件: %s", file_name)
            try:
                result = ocr_config.recognize_invoice(file_data)
            except Exception as e:
                _logger.error("图片处理错误: %s", str(e))
                raise UserError(_("图片处理错误: %s") % str(e))
        
        # 处理OCR识别结果
        try:
            expense_vals = self._prepare_expense_vals_from_ocr(result)
            expense_vals.update({
                'attachment_ids': [(4, attachment_id)],
                'ocr_extracted': True,
                'ocr_raw_data': str(result),
            })
            
            expense = self.create(expense_vals)
            return expense.id
        except Exception as e:
            _logger.error("OCR费用创建错误: %s", str(e))
            raise UserError(_("OCR费用创建错误: %s") % str(e))
    
    def _prepare_expense_vals_from_ocr(self, ocr_result):
        """从OCR结果准备费用记录的值 - 完善字段映射"""
        _logger.info("处理OCR结果: %s", ocr_result)
        
        # 使用处理后的数据结构，这些数据来自baidu_ocr_config.py的_process_ocr_result方法
        if not ocr_result:
            raise UserError(_("OCR结果为空，无法创建费用"))
        
        # 获取发票类型分类
        invoice_type_category = ocr_result.get('invoice_type_category', 'vat_invoice')
        
        # 提取基本信息
        vat_invoice_vendor_name = ocr_result.get('vendor') or ocr_result.get('seller_name') or ''
        vat_invoice_number = ocr_result.get('invoice_number') or ''
        vat_invoice_code = ocr_result.get('invoice_code') or ''
        vat_invoice_vendor_tax_id = ocr_result.get('seller_register_num') or ''
        vat_invoice_purchaser_name = ocr_result.get('purchaser_name') or ''
        vat_invoice_purchaser_tax_id = ocr_result.get('purchaser_register_num') or ''
        vat_invoice_type = ocr_result.get('invoice_type') or ''
        vat_invoice_drawer = ocr_result.get('drawer') or ''
        vat_invoice_service_type = ocr_result.get('service_type') or ''
        vat_invoice_amount_in_words = ocr_result.get('amount_in_words') or ''
        
        # 处理日期
        vat_invoice_date_str = ocr_result.get('date') or ocr_result.get('invoice_date')
        vat_invoice_date = fields.Date.today()
        if vat_invoice_date_str:
            vat_invoice_date = self._parse_chinese_date(vat_invoice_date_str)
        
        # 提取商品信息
        commodity_name = (ocr_result.get('commodity_name') or 
                         ocr_result.get('description') or 
                         'OCR识别费用')
        
        # 提取金额信息
        # 优先使用总金额
        expense_amount = ocr_result.get('total_amount') or 0.0
        
        # 处理数量
        quantity = 1.0
        
        # 计算单价
        unit_amount = expense_amount / quantity if quantity > 0 else expense_amount
        
        # 税额信息
        vat_invoice_tax_amount = ocr_result.get('total_tax') or 0.0
        
        # 含税总金额
        vat_invoice_amount_with_tax = ocr_result.get('amount_in_figuers') or (expense_amount + vat_invoice_tax_amount)
        
        # 处理税率 - 检查是否有多种不同税率
        tax_rates = ocr_result.get('tax_rates', [])
        has_multiple_tax_rates = False
        if not tax_rates:
            vat_invoice_tax_rate = "0%"
        elif len(set(tax_rates)) == 1:
            vat_invoice_tax_rate = tax_rates[0]
        else:
            vat_invoice_tax_rate = "多种税率"
            has_multiple_tax_rates = True
        
        # 准备费用名称
        name = commodity_name
        if vat_invoice_vendor_name:
            name += f" ({vat_invoice_vendor_name})"
        
        # 查找合适的费用产品
        product_id = self._find_suitable_product(commodity_name)
        
        # 确保有必要的字段值
        if not vat_invoice_vendor_name:
            vat_invoice_vendor_name = '未知供应商'
        if not name or name.strip() == '':
            name = 'OCR识别费用'
        
        # 准备返回值 - 适配Odoo 17
        vals = {
            'name': name,
            'unit_amount': unit_amount,  # 单价
            'amount': expense_amount,    # 总金额（不含税）
            'quantity': quantity,
            'date': vat_invoice_date,
            'vat_invoice_code': vat_invoice_code,
            'vat_invoice_number': vat_invoice_number,
            'vat_invoice_date': vat_invoice_date,
            'vat_invoice_type': vat_invoice_type,
            'vat_vendor_name': vat_invoice_vendor_name,
            'vat_vendor_tax_id': vat_invoice_vendor_tax_id,
            'vat_purchaser_name': vat_invoice_purchaser_name,
            'vat_purchaser_tax_id': vat_invoice_purchaser_tax_id,
            'vat_drawer': vat_invoice_drawer,
            'vat_service_type': vat_invoice_service_type,
            'vat_tax_rate': vat_invoice_tax_rate,
            'vat_tax_amount': vat_invoice_tax_amount,
            'vat_amount_with_tax': vat_invoice_amount_with_tax,
            'vat_amount_in_words': vat_invoice_amount_in_words,
            'product_id': product_id,
            'company_id': self.env.company.id,
            'employee_id': self.env.user.employee_id.id,
            'payment_mode': 'company_account',
            'has_multiple_tax_rates': has_multiple_tax_rates,
            'total_amount': vat_invoice_amount_with_tax,  # 设置原生总计字段为含税金额
            'invoice_type_category': invoice_type_category,
        }
        
        # 如果是火车票，添加火车票特有字段
        if invoice_type_category == 'train_ticket':
            vals.update({
                'train_starting_station': ocr_result.get('starting_station'),
                'train_destination_station': ocr_result.get('destination_station'),
                'train_seat_category': ocr_result.get('seat_category'),
                'train_seat_num': ocr_result.get('seat_num'),
                'train_passenger_name': ocr_result.get('passenger_name') or ocr_result.get('name'),
                'train_passenger_id': ocr_result.get('ID_card'),
                'train_num': ocr_result.get('train_num'),
                'train_time': ocr_result.get('time'),
                'train_ticket_num': ocr_result.get('ticket_num'),
                'train_elec_ticket_num': ocr_result.get('elec_ticket_num'),
            })
        
        # 如果不是多种税率，尝试设置原生税率
        if not has_multiple_tax_rates and vat_invoice_tax_rate != "0%":
            try:
                # 移除%符号并转换为数字
                tax_rate_str = vat_invoice_tax_rate.replace('%', '').replace('％', '').strip()
                tax_rate = float(tax_rate_str)
                # 查找对应税率的税收记录
                tax = self.env['account.tax'].search([
                    ('type_tax_use', '=', 'purchase'),
                    ('amount', '=', tax_rate),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)
                if tax:
                    vals['tax_ids'] = [(6, 0, [tax.id])]
            except (ValueError, AttributeError):
                pass
        
        _logger.info("准备的费用数据: %s", vals)
        return vals
    
    def _find_suitable_product(self, commodity_name):
        """根据商品名称查找合适的费用产品"""
        # 费用产品映射规则
        product_mappings = [
            # 办公用品类
            (['办公', '文具', '用品', '纸张', '笔', '本子'], '办公用品'),
            # 设备类
            (['电脑', '打印机', '设备', '硬件', '显示器'], '办公设备'),
            # 交通类
            (['出租车', '交通', '车费', '机票', '火车'], '交通费'),
            # 餐饮类
            (['餐饮', '食品', '饮料', '招待'], '餐饮费'),
            # 住宿类
            (['住宿', '酒店', '宾馆'], '住宿费'),
            # 通讯类
            (['通讯', '电话', '网络', '流量'], '通讯费'),
        ]
        
        # 搜索关键词
        search_text = (commodity_name or '').lower()
        
        # 根据映射规则查找产品
        for keywords, product_name in product_mappings:
            if any(keyword in search_text for keyword in keywords):
                product = self.env['product.product'].search([
                    ('can_be_expensed', '=', True),
                    ('name', 'ilike', product_name)
                ], limit=1)
                if product:
                    return product.id
        
        # 如果找不到特定产品，返回默认的费用产品
        default_product = self.env['product.product'].search([
            ('can_be_expensed', '=', True)
        ], limit=1)
        
        return default_product.id if default_product else False
    
    def _parse_chinese_date(self, date_str):
        """解析中文日期格式 - 增强版本"""
        if not date_str:
            return fields.Date.today()
            
        try:
            # 清理日期字符串
            date_str = str(date_str).strip()
            
            # 处理中文格式: "2025年05月08日"
            if '年' in date_str and '月' in date_str:
                date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
                parts = [p.strip() for p in date_str.split('-') if p.strip()]
                if len(parts) >= 3:
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])
                    return fields.Date.from_string(f"{year:04d}-{month:02d}-{day:02d}")
            
            # 处理标准格式
            elif '-' in date_str:
                parts = [p.strip() for p in date_str.split('-') if p.strip()]
                if len(parts) >= 3:
                    return fields.Date.from_string(f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}")
            
            # 处理斜杠格式
            elif '/' in date_str:
                parts = [p.strip() for p in date_str.split('/') if p.strip()]
                if len(parts) >= 3:
                    return fields.Date.from_string(f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}")
                    
        except Exception as e:
            _logger.warning("日期解析失败，使用今天日期: %s, 错误: %s", date_str, str(e))
        
        return fields.Date.today()