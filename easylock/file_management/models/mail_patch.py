from odoo import models, api

# 为所有继承了mail.thread的模型添加通用的_get_mail_thread_data方法
def _generic_get_mail_thread_data(self, request_list):
    res = {}
    for thread in self:
        res[thread.id] = {
            'hasWriteAccess': thread.check_access_rights('write', raise_exception=False),
            'hasDeleteAccess': thread.check_access_rights('unlink', raise_exception=False),
            'mainAttachment': {
                'id': thread.id,
                'name': thread.name if hasattr(thread, 'name') else 'Document',
            }
        }
    return res

# 应用补丁
models.Model._get_mail_thread_data = _generic_get_mail_thread_data