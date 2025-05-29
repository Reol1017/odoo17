# -*- coding: utf-8 -*-
{
    'name': 'Save Confirm',
    'version': '17.0.1.0.0',
    'category': 'Tools',
    'summary': '返回页面时弹窗确认是否保存记录',
    'description': """
        此模块在用户离开表单或列表视图时，
        会弹出确认对话框询问是否保存更改。
    """,
    'author': 'Grit-江西一方信息技术有限公司',
    'website': 'https://www.ifangtech.com',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'save_confirm/static/src/js/save_confirm.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}