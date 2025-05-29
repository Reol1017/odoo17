# -*- coding: utf-8 -*-

import logging
import re
import smtplib
import sys

from odoo import api, fields, models, _
from odoo.addons.base.models.ir_mail_server import is_ascii, extract_rfc2822_addresses, MailDeliveryException
from odoo.tools import ustr

_logger = logging.getLogger(__name__)
_test_logger = logging.getLogger('odoo.tests')


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"
    _order = "sequence"

    # 用设置的默认发件人当 bounce ，将会出现“由***代发”字样
    # todo: 此处已不需要，注意直接设置好参数 mail.bounce.alias 和默认发件人一样即可。 或者将 mail.bounce.alias 清空
    def _get_default_bounce_address(self):
        mail_bounce = self._get_default_from_address()
        if mail_bounce:
            return mail_bounce
        return super(IrMailServer, self)._get_default_bounce_address()

    # @api.model
    # 改默认发邮件逻辑，优先找发件人的 server 设置，其次才使用 Bounce 设置发件
    def send_email(self, message, mail_server_id=None, smtp_server=None, smtp_port=None,
                   smtp_user=None, smtp_password=None, smtp_encryption=None,
                   smtp_ssl_certificate=None, smtp_ssl_private_key=None,
                   smtp_debug=False, smtp_session=None):
        smtp = smtp_session
        if not smtp:
            smtp = self.connect(
                smtp_server, smtp_port, smtp_user, smtp_password, smtp_encryption,
                smtp_from=message['From'], ssl_certificate=smtp_ssl_certificate, ssl_private_key=smtp_ssl_private_key,
                smtp_debug=smtp_debug, mail_server_id=mail_server_id,)
            if smtp:
                smtp_session = smtp
        smtp_from, smtp_to_list, message = self._prepare_email_message(message, smtp)
        if smtp_from and not mail_server_id:
            mail_server = self.sudo().search([('smtp_user', '=', smtp_from)], order='sequence', limit=1).exists()
            if mail_server:
                mail_server_id = mail_server.id
        return super(IrMailServer, self).send_email(message, mail_server_id, smtp_server, smtp_port,
                                                    smtp_user, smtp_password, smtp_encryption,
                                                    smtp_ssl_certificate, smtp_ssl_private_key,
                                                    smtp_debug, smtp_session)
