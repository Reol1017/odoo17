# -*- coding: utf-8 -*-
{
    'name': '百度OCR费用',
    'version': '1.0',
    'summary': '使用百度OCR识别费用单据',
    'description': """
        使用百度OCR API识别费用单据，支持：
        - 增值税发票
        - 火车票
    """,
    'category': 'Accounting/Expenses',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'hr_expense', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/baidu_ocr_config_views.xml',
        'views/ticket_views.xml',
        'views/hr_expense_views.xml',
        'views/ocr_views.xml',
        'wizard/ocr_debug_wizard_views.xml',
        'wizard/ocr_upload_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
} 