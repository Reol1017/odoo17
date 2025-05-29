# -*- coding: utf-8 -*-

import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class BaiduOcrController(http.Controller):
    
    @http.route('/baidu_ocr/upload_invoice', type='http', auth='user', methods=['POST'], csrf=False)
    def upload_invoice(self, **post):
        """上传发票进行OCR识别"""
        try:
            attachment_id = int(post.get('attachment_id'))
            expense_id = request.env['hr.expense'].sudo().create_from_ocr(attachment_id)
            data = {
                'success': True,
                'expense_id': expense_id,
            }
        except Exception as e:
            _logger.error("OCR上传错误: %s", str(e))
            data = {
                'success': False,
                'error': str(e),
            }
        
        return json.dumps(data)
    
    @http.route('/baidu_ocr/test_connection', type='http', auth='user')
    def test_connection(self, **post):
        """测试百度OCR API连接"""
        try:
            config_id = int(post.get('config_id'))
            config = request.env['baidu.ocr.config'].sudo().browse(config_id)
            token = config.get_access_token()
            data = {
                'success': True,
                'token': token[:10] + '...',
            }
        except Exception as e:
            data = {
                'success': False,
                'error': str(e),
            }
        
        return json.dumps(data)