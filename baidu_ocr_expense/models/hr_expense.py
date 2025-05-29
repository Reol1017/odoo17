# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class HrExpense(models.Model):
    _inherit = 'hr.expense'
    
    # OCR识别标志
    ocr_recognized = fields.Boolean('OCR已识别', default=False)
    ocr_invoice_type = fields.Selection([
        ('vat_invoice', '增值税发票'),
        ('train_ticket', '火车票'),
        ('taxi_receipt', '出租车票'),
        ('air_ticket', '飞机票'),
        ('other', '其他票据')
    ], string='票据类型')
    
    # 通用发票信息
    invoice_code = fields.Char('发票代码')
    invoice_number = fields.Char('发票号码')
    invoice_date = fields.Date('开票日期')
    vendor_name = fields.Char('销售方名称')
    total_amount = fields.Float('金额合计', digits=(16, 2))
    remarks = fields.Text('备注')
    
    # 增值税发票特有字段
    note_drawer = fields.Char('开票人')
    total_tax = fields.Float('税额合计', digits=(16, 2))
    amount_in_figures = fields.Char('含税价格')
    amount_in_words = fields.Char('价税合计(大写)')
    tax_rate = fields.Char('税率')
    purchaser_name = fields.Char('购买方名称')
    purchaser_register_num = fields.Char('购买方税号')
    seller_register_num = fields.Char('销售方税号')
    
    # 火车票特有字段
    train_number = fields.Char('车次')
    departure_station = fields.Char('出发站')
    arrival_station = fields.Char('到达站')
    departure_time = fields.Char('出发时间')
    seat_class = fields.Char('座位等级')
    passenger_name = fields.Char('乘客姓名')
    passenger_id = fields.Char('身份证号')
    
    # 出租车票特有字段
    taxi_plate_number = fields.Char('车牌号')
    taxi_departure = fields.Char('上车时间')
    taxi_destination = fields.Char('下车时间')
    taxi_distance = fields.Char('里程')
    taxi_waiting_time = fields.Char('等候时间')
    
    # 飞机票特有字段
    flight_number = fields.Char('航班号')
    departure_airport = fields.Char('出发机场')
    arrival_airport = fields.Char('到达机场')
    flight_date = fields.Date('航班日期')
    passenger_class = fields.Char('舱位等级')

class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'
    
    def action_ocr_recognize(self):
        """打开OCR识别向导"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ocr.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_expense_sheet_id': self.id},
        }