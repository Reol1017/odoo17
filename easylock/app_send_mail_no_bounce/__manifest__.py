

{
    'name': "Send Email Fix, No Bounce Patch.优先使用发件人邮局设置作为回邮地址，不再用Bounce跳转",
    'version': '17.0.25.01.05',
    'author': 'odooai.cn',
    'category': 'Base',
    'website': 'https://www.odooai.cn',
    'live_test_url': 'https://demo.odooapp.cn',
    'license': 'OPL-1',
    'sequence': 2,
    'price': 38.00,
    'currency': 'EUR',
    'images': ['static/description/banner.png'],
    'depends': [
    ],
    'summary': """
    fix email mail send, fix mail delivery failed. send mail without bounce. fixed mail error.
    fix SMTPSenderRefused 501. fix mail from address must be same as authorization user.
    eg.Tencent QQMail and Ali mail enterprise and in China must apply this app. Use the sender mail as reply mail address.
    """,
    'description': """
    Remember to set User Preferences to use Notification 'Handle by email', not in odoo. 
    After install the apps, the top priority server would be the mail sender, which show on the from.
    And the mail.bounce.alias setting would has no effect.
    """,
    'data': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
