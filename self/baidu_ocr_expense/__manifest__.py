{
    'name': '百度 OCR 费用识别',
    'version': '1.0',
    'category': 'Accounting/Expenses',
    'summary': 'Recognize expense invoices using Baidu OCR API',
    'description': """
Baidu OCR Invoice Recognition
=============================
This module integrates Baidu OCR API to automatically extract information from 
invoice images and create expense records.

Features:
- Configure Baidu OCR API credentials
- Upload invoice images for automatic recognition
- Extract vendor, date, amount, and other information
- Create expense records with extracted data
- Support for multiple invoice types
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'hr_expense', 'account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/baidu_ocr_config_views.xml',
        'wizard/ocr_wizard_views.xml',
        'wizard/ocr_debug_wizard_views.xml',
        'views/expense_views.xml',
        'views/hr_expense_sheet_views.xml',
        'views/menu_views.xml',
        # 'views/templates.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'baidu_ocr_expense/static/src/js/ocr_upload.js',
    #         'baidu_ocr_expense/static/src/css/style.css',
    #     ],
    # },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}