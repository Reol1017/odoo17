{
    'name': '销售订单转换采购订单',
    'version': '1.0',
    'summary': '允许在销售订单中选择供应商并生成采购订单。',
    'description': '''
        此模块提供了从销售订单直接创建采购订单的功能。
        允许用户指定供应商，并基于销售订单行快速生成对应的采购订单。
        支持识别产品的首选供应商，提高采购流程效率。
    ''',
    'category': 'Sales/Purchase',
    'author': '江西一方信息技术有限公司',
    'website': 'https://www.ifangtech.com',
    'license': 'LGPL-3',
    'depends': ['sale', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/purchase_order_wizard_view.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}