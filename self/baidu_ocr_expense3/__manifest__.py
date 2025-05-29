{
    'name': 'Baidu OCR Expense',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'OCR发票识别费用管理',
    'description': """
    使用百度OCR API识别中国发票并自动创建费用记录
    
    功能特点:
    - 支持多种中国发票格式识别
    - 自动提取发票信息并创建费用记录
    - 包含OCR调试工具
    - 支持固定资产标记
    - 完整的税务信息处理
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['hr_expense', 'base'],
    'data': [
        # 安全文件
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # 核心模型视图
        'views/baidu_ocr_config_views.xml',
        'views/expense_views.xml',
        
        # 向导视图
        'wizard/ocr_wizard_views.xml',
        'wizard/ocr_debug_wizard_views.xml',
        
        # 模板数据（如果存在）
        # 'data/templates.xml',
    ],
    'demo': [],
    'installable': False,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
    'external_dependencies': {
        'python': ['requests'],
    },
}