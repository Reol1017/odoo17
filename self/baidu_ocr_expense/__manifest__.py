# ========== 清理后的 __manifest__.py ==========
{
    'name': '百度OCR费用识别',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': '基于百度OCR的发票识别，扩展HR费用管理',
    'description': """
百度OCR费用识别模块
======================

功能特性:
--------
* 集成百度OCR API进行发票识别
* 每种发票类型独立的模型和视图
* 完整继承hr_expense的所有功能
* 目前支持增值税发票，后续扩展其他类型

支持的发票类型:
--------------
* 增值税发票 (vat_invoice) - 完整支持
* 其他发票类型将逐步添加

技术特性:
--------
* 基于Odoo 17.0开发
* 独立模型设计，不污染原生hr_expense
* 每种发票类型都是完整的费用记录
* 模块化架构，易于扩展
    """,
    'author': 'Your Company',
    'depends': [
        'base',
        'hr_expense',
        'product',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/baidu_ocr_config_views.xml',
        'views/vat_invoice_views.xml',
        'wizard/ocr_upload_wizard_views.xml',
        'wizard/ocr_debug_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}