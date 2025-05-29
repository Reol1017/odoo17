{
    'name': 'CRM Business Module',
    'version': '17.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'CRM Business Process Customization',
    'description': '''
CRM Business Process Customization Module
=========================================

This module provides:
- Business opportunity management
- Custom sales stages
- Enhanced lead tracking
- Automated workflow processes

Features:
- Organization/Contact fields
- Project name tracking
- Custom sales pipeline
- Stage-based automation
    ''',
    'depends': ['crm', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}