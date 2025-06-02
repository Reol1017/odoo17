{
    'name': 'Hello',
    'version': '1.0',
    'summary': '简单的Hello模块',
    'description': """
        这是一个示例模块，用于展示Odoo模块的基本结构。
    """,
    'category': 'Uncategorized',
    'author': 'Your Name',
    'website': 'https://www.example.com',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/hello_views.xml',
        'views/hello_menus.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
} 