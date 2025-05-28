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