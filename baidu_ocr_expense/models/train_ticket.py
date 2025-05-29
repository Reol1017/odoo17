# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class TrainTicket(models.Model):
    """火车票独立模型 - 用于复杂查询和报表"""
    _name = 'train.ticket'
    _description = '火车票'
    _rec_name = 'name'
    _order = 'date desc, id desc'

    # 关联字段
    expense_id = fields.Many2one('hr.expense', string='关联费用', ondelete='cascade', index=True)
    
    # 基本信息
    name = fields.Char('票据标题', compute='_compute_name', store=True)
    ticket_number = fields.Char('票号', readonly=True)
    train_number = fields.Char('车次', readonly=True)
    date = fields.Char('乘车日期', readonly=True)
    amount = fields.Float('票价', readonly=True)
    
    # 行程信息
    origin = fields.Char('出发站', readonly=True)
    destination = fields.Char('到达站', readonly=True)
    departure_time = fields.Char('出发时间', readonly=True)
    arrival_time = fields.Char('到达时间', readonly=True)
    
    # 座位信息
    seat_type = fields.Char('座位类型', readonly=True)
    seat_number = fields.Char('座位号', readonly=True)
    
    # 乘客信息
    passenger_name = fields.Char('乘客姓名', readonly=True)
    passenger_id = fields.Char('身份证号', readonly=True)
    
    # OCR原始数据
    ocr_raw_data = fields.Text('OCR原始数据', readonly=True)
    
    @api.depends('train_number', 'origin', 'destination')
    def _compute_name(self):
        for record in self:
            if record.train_number and record.origin and record.destination:
                record.name = f"{record.train_number} {record.origin}-{record.destination}"
            elif record.train_number:
                record.name = record.train_number
            else:
                record.name = '火车票'
    
    @api.model
    def create_from_ocr_data(self, ocr_result, expense_id):
        """从OCR结果创建火车票记录"""
        if not ocr_result.get('words_result'):
            return False
            
        words_result = ocr_result['words_result'][0]['result']
        
        # 处理金额
        ticket_price = self._get_field_value(words_result, 'TicketPrice')
        try:
            amount = float(ticket_price.replace(',', '')) if ticket_price else 0.0
        except (ValueError, TypeError):
            amount = 0.0
        
        vals = {
            'expense_id': expense_id,
            'ticket_number': self._get_field_value(words_result, 'TicketNum'),
            'train_number': self._get_field_value(words_result, 'TrainNum'),
            'date': self._get_field_value(words_result, 'Date'),
            'amount': amount,
            'origin': self._get_field_value(words_result, 'StartingStation'),
            'destination': self._get_field_value(words_result, 'DestinationStation'),
            'departure_time': self._get_field_value(words_result, 'DepartureTime'),
            'arrival_time': self._get_field_value(words_result, 'ArrivalTime'),
            'seat_type': self._get_field_value(words_result, 'PassengerClass'),
            'seat_number': self._get_field_value(words_result, 'SeatNumber'),
            'passenger_name': self._get_field_value(words_result, 'PassengerName'),
            'passenger_id': self._get_field_value(words_result, 'PassengerIdNum'),
            'ocr_raw_data': str(ocr_result),
        }
        
        return self.create(vals)
    
    def _get_field_value(self, words_result, field_name):
        """获取字段值"""
        field_data = words_result.get(field_name, [])
        if field_data and isinstance(field_data, list) and len(field_data) > 0:
            return field_data[0].get('word', '')
        return ''