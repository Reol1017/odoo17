{
    'name': 'Sales Purchase Bridge',
    'version': '1.0',
    'category': 'Sales/Purchase',
    'summary': '销售订单与采购订单的桥接模块',
    'description': """
        在权限隔离的情况下实现销售订单与采购订单之间的转换和协作流程。
        功能包括：
        - 销售订单需要询价时提醒采购人员
        - 销售下单后自动通知采购人员
        - 采购人员可以分配销售订单行给不同供应商
    """,
    'author': 'GRIT-江西一方信息技术有限公司',
    'website': 'https://www.ifangtech.com',
    'depends': ['sale_management', 'purchase', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/sale_purchase_request_views.xml',
        'views/menu_views.xml',
        'wizards/assign_supplier_views.xml',
        'wizards/assign_purchaser_views.xml',
        'data/mail_template_data.xml',
        # 'data/automated_actions.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3'
}