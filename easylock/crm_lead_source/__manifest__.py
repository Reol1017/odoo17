{
    'name': '商机来源管理',
    'version': '17.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': '添加商机来源管理功能',
    'description': """
        添加商机来源管理功能
        ==================
        * 在CRM配置菜单下添加商机来源管理
        * 在商机表单中添加商机来源字段
        * 在商机搜索视图中添加商机来源筛选
    """,
    'author': 'Your Company',
    'depends': ['crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/lead_source_views.xml',
        'views/crm_lead_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}