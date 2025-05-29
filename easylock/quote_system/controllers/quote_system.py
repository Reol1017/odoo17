from odoo import http
from odoo.http import request
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class QuoteController(http.Controller):

    @http.route('/quote_system/get_quote_data', type='json', auth='user', methods=['POST'])
    def get_quote_data(self):
        # 使用 request.httprequest.get_json() 获取请求中的 JSON 数据
        data = request.httprequest.get_json() or {}
        record_id = data.get('id')
        _logger.info("传入的记录ID: %s", record_id)

        if not record_id:
            _logger.error("缺少记录ID")
            return {'status': 'error', 'message': 'Missing record id'}

        # 根据ID查询记录
        quote = request.env['quote.system'].sudo().browse(int(record_id))
        if not quote.exists():
            _logger.error("记录不存在，ID: %s", record_id)
            return {'status': 'error', 'message': 'Record not found'}

        _logger.info("查询到记录：ID: %s, name: %s", quote.id, quote.name)

        # 获取当前用户
        current_user = request.env.user

       
        # 构造返回数据
        data = {
            'id': quote.id,
            'name': quote.name,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'username': current_user.name,
        }
        return {'status': 'success', 'data': data}