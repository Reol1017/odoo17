# -*- coding: utf-8 -*-
{
    'name': '百度OCR费用识别',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Expenses',
    'summary': '使用百度OCR API识别费用票据',
    'description': """
百度OCR费用识别
==============
使用百度OCR API识别不同类型的票据，并自动创建费用记录。
支持多种票据类型，如增值税发票、火车票等。
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['hr_expense'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu_views.xml',
        'views/hr_expense_views.xml',
        'views/ticket_types/vat_invoice/vat_invoice_views.xml',
        'wizard/ocr_upload_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
} 