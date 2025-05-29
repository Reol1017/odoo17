# -*- coding: utf-8 -*-
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
* 支持增值税发票自动识别和数据提取
* 自动填充HR费用报销单相关字段
* 可扩展支持多种发票类型
* 提供完整的发票信息管理界面

支持的发票类型:
--------------
* 增值税发票 (vat_invoice)
* 后续将支持: 出租车票、火车票、飞机行程单等17种发票类型

技术特性:
--------
* 基于Odoo 17.0开发
* 继承并扩展hr_expense模块
* 模块化设计，每种发票类型独立模型和视图
* 完整的权限控制和安全配置
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'hr_expense',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/baidu_ocr_config_views.xml',
        'views/ocr_menu.xml',
        'views/hr_expense_views.xml',
        'views/separate_models_views.xml',
        'wizard/ocr_upload_wizard_views.xml',
        'wizard/ocr_debug_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}