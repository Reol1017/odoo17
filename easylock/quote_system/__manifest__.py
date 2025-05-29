{
    'name': '智能报价系统',
    'version': '1.0',
    'category': 'Sales/Quotation',
    'summary': '智能化报价单管理系统',
    'description': '提供完整的报价单管理功能，支持多种报价模板和自动化报价流程',
    'depends': ['web', 'product','sale','stock_barcode'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_action_data.xml',
        'views/menu_view.xml',
        'views/warehouse_weight_views.xml',
        'views/color.xml',
        'views/sale_order.xml',
        'views/sale_order_line.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/quote_system/static/src/js/quote_kanban.js',
            '/quote_system/static/src/xml/quote_kanban.xml',
            '/quote_system/static/src/js/excel_report.js'
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
