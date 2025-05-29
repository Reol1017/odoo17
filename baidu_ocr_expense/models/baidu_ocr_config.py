# -*- coding: utf-8 -*-

import base64
import json
import logging
import requests
import os
import tempfile
import urllib.parse
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class BaiduOcrConfig(models.Model):
    _name = 'baidu.ocr.config'
    _description = '百度OCR配置'

    name = fields.Char('配置名称', required=True)
    app_id = fields.Char('APP ID', required=True)
    api_key = fields.Char('API Key', required=True)
    secret_key = fields.Char('Secret Key', required=True)
    access_token = fields.Char('Access Token', readonly=True)
    token_expiry_date = fields.Datetime('Token过期时间', readonly=True)
    active = fields.Boolean('是否启用', default=True)
    is_default = fields.Boolean('是否默认', default=False)
    
    @api.constrains('is_default')
    def _check_default(self):
        """确保只有一个默认配置"""
        for record in self:
            if record.is_default:
                self.search([('id', '!=', record.id), ('is_default', '=', True)]).write({'is_default': False})
    
    @api.model
    def get_default_config(self):
        """获取默认配置"""
        config = self.search([('is_default', '=', True), ('active', '=', True)], limit=1)
        if not config:
            config = self.search([('active', '=', True)], limit=1)
        
        if not config:
            raise UserError(_('未找到有效的百度OCR配置，请先设置配置信息'))
        return config
    
    def action_get_token(self):
        """获取百度OCR的access_token"""
        self.ensure_one()
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            'grant_type': 'client_credentials',
            'client_id': self.api_key,
            'client_secret': self.secret_key
        }
        
        try:
            response = requests.post(url, params=params)
            result = response.json()
            
            if 'access_token' in result:
                # 计算过期时间，百度token通常有效期为30天
                expiry_date = datetime.now() + timedelta(seconds=result.get('expires_in', 2592000))
                self.write({
                    'access_token': result['access_token'],
                    'token_expiry_date': expiry_date
                })
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('成功'),
                        'message': _('成功获取Access Token'),
                        'sticky': False,
                        'type': 'success',
                    }
                }
            else:
                error_msg = result.get('error_description', '未知错误')
                raise UserError(_('获取百度OCR access_token失败: %s') % error_msg)
        except Exception as e:
            raise UserError(_('获取百度OCR access_token时发生错误: %s') % str(e))
    
    def action_test_connection(self):
        """测试百度OCR连接"""
        self.ensure_one()
        try:
            # 如果没有token或token已过期，则获取新token
            if not self.access_token or (self.token_expiry_date and self.token_expiry_date < datetime.now()):
                self.action_get_token()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('成功'),
                    'message': _('连接测试成功'),
                    'sticky': False,
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('错误'),
                    'message': str(e),
                    'sticky': False,
                    'type': 'danger',
                }
            }
    
    def _is_pdf_data(self, file_data):
        """检测文件数据是否为PDF格式"""
        # PDF文件以 %PDF- 开头
        if len(file_data) >= 4:
            return file_data[:4] == b'%PDF'
        return False
    
    def recognize_invoice(self, file_content):
        """调用百度OCR识别发票"""
        # 确保有access_token
        if not self.access_token or (self.token_expiry_date and self.token_expiry_date < datetime.now()):
            self.action_get_token()
            
        # 检测文件类型
        is_pdf = self._is_pdf_data(file_content)
        file_type = "PDF" if is_pdf else "图片"
        _logger.info("开始识别 %s 文件，大小: %d 字节", file_type, len(file_content))
            
        # 准备API调用
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/multiple_invoice?access_token={self.access_token}"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        try:
            # 准备文件数据 - 直接使用base64编码的图片数据
            file_base64 = base64.b64encode(file_content).decode('utf-8')
            
            # 根据文件类型设置参数
            if is_pdf:
                # PDF参数
                data = {
                    "pdf_file": file_base64,
                    "pdf_file_num": "1"  # 处理第一页
                }
                _logger.info("使用PDF模式识别")
            else:
                # 图片参数
                data = {
                    "image": file_base64
                }
                _logger.info("使用图片模式识别")
            
            # 编码请求数据
            encoded_data = urllib.parse.urlencode(data)
            
            # 发送请求
            response = requests.post(url, headers=headers, data=encoded_data)
            result = response.json()
            
            # 记录返回结果
            _logger.info("百度OCR API返回结果: %s", json.dumps(result, ensure_ascii=False))
            
            # 检查是否有错误
            if 'error_code' in result:
                error_msg = result.get('error_msg', '未知错误')
                error_code = result.get('error_code')
                _logger.error("OCR API错误: %s - %s", error_code, error_msg)
                raise UserError(_('百度OCR识别失败: %s') % error_msg)
                
            return result
        except Exception as e:
            _logger.exception("调用百度OCR API时发生错误: %s", str(e))
            raise UserError(_('调用百度OCR API时发生错误: %s') % str(e)) 