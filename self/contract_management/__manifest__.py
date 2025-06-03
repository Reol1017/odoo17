{
    'name': '合同管理',
    'version': '17.0.1.0.0',
    'summary': '合同模板管理和合同生成',
    'description': """
        合同管理模块
        ============
        
        功能包括：
        * 上传和管理合同模板
        * 填写合同信息
        * 生成Word和PDF格式的合同
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'category': 'Documents',
    'sequence': 10,
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/contract_template_views.xml',
        'views/contract_generation_views.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}