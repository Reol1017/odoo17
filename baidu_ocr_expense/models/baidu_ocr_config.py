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

    name = fields.Char('名称', required=True)
    app_id = fields.Char('App ID', required=True)
    api_key = fields.Char('API Key', required=True)
    secret_key = fields.Char('Secret Key', required=True)
    access_token = fields.Char('Access Token', readonly=True)
    token_expiry_date = fields.Datetime('Token过期时间', readonly=True)
    active = fields.Boolean('有效', default=True)
    is_default = fields.Boolean('是否默认', default=False)
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', '配置名称必须唯一!')
    ]
    
    @api.constrains('is_default')
    def _check_default(self):
        """确保只有一个默认配置"""
        for record in self:
            if record.is_default:
                self.search([('id', '!=', record.id), ('is_default', '=', True)]).write({'is_default': False})
    
    @api.model
    def get_default_config(self):
        """获取默认配置"""
        config = self.search([('active', '=', True)], limit=1)
        return config
    
    def get_access_token(self):
        """获取百度OCR API的访问令牌"""
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
                return result['access_token']
            else:
                error_msg = result.get('error_description', '未知错误')
                _logger.error("获取百度OCR访问令牌失败: %s", error_msg)
                raise UserError(_('获取百度OCR访问令牌失败: %s') % error_msg)
                
        except Exception as e:
            _logger.exception("获取百度OCR访问令牌时发生错误: %s", str(e))
            raise UserError(_('获取百度OCR访问令牌时发生错误: %s') % str(e))
    
    def recognize_invoice(self, file_content):
        """识别票据"""
        # 获取访问令牌
        access_token = self.get_access_token()
        
        # 设置请求URL和参数
        url = "https://aip.baidubce.com/rest/2.0/ocr/v1/multiple_invoice"
        params = {'access_token': access_token}
        
        # 准备请求数据
        data = {
            'image': base64.b64encode(file_content).decode('utf-8'),
            'detect_direction': 'true'
        }
        
        # 发送请求
        try:
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            response = requests.post(url, params=params, data=data, headers=headers)
            result = response.json()
            
            if 'error_code' in result:
                error_msg = result.get('error_msg', '未知错误')
                _logger.error("百度OCR识别失败: %s", error_msg)
                raise UserError(_('百度OCR识别失败: %s') % error_msg)
            
            return result
            
        except Exception as e:
            _logger.exception("调用百度OCR API时发生错误: %s", str(e))
            raise UserError(_('调用百度OCR API时发生错误: %s') % str(e))
    
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