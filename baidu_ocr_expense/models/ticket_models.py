# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class BaseTicket(models.AbstractModel):
    """所有票据类型的基础模型"""
    _name = 'base.ticket'
    _description = '基础票据模型'
    
    name = fields.Char('名称', required=True)
    date = fields.Date('日期')
    amount = fields.Float('金额', digits=(16, 2))
    ocr_raw_data = fields.Text('OCR原始数据', readonly=True)

class TrainTicket(models.Model):
    _name = 'train.ticket'
    _description = '火车票'
    _inherit = ['base.ticket']
    
    # 车票基本信息
    ticket_number = fields.Char('车票号码')
    train_number = fields.Char('车次')
    seat_type = fields.Char('座位类型')
    seat_number = fields.Char('座位号')
    
    # 行程信息
    origin = fields.Char('出发站')
    destination = fields.Char('到达站')
    departure_time = fields.Datetime('出发时间')
    arrival_time = fields.Datetime('到达时间')
    
    # 乘客信息
    passenger_name = fields.Char('乘客姓名')
    passenger_id = fields.Char('乘客身份证号')

class VatInvoice(models.Model):
    _name = 'vat.invoice'
    _description = '增值税发票'
    _inherit = ['base.ticket']
    
    # 发票基本信息
    invoice_code = fields.Char('发票代码')
    invoice_number = fields.Char('发票号码')
    invoice_date = fields.Date('开票日期')
    invoice_type = fields.Char('发票类型')
    
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
    
    # 税务信息
    tax_rate = fields.Float('税率(%)', digits=(5, 2))
    tax_amount = fields.Float('税额')
    amount_without_tax = fields.Float('不含税金额')
    amount_in_words = fields.Char('合计大写')
    
    # 其他信息
    drawer = fields.Char('开票人')
    payee = fields.Char('收款人')
    checker = fields.Char('复核人')
    remarks = fields.Text('备注') 