# -*- coding: utf-8 -*-

import base64
import json
import logging
import os
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class OcrDebugWizard(models.TransientModel):
    _name = 'ocr.debug.wizard'
    _description = 'OCR调试向导'
    
    test_file = fields.Binary('测试文件', required=True)
    test_filename = fields.Char('文件名')
    raw_result = fields.Text('原始结果', readonly=True)
    ticket_type = fields.Char('票据类型', readonly=True)
    image_preview = fields.Binary('图片预览', readonly=True)
    
    def action_test_ocr(self):
        """测试OCR识别"""
        self.ensure_one()
        
        if not self.test_file:
            raise UserError(_('请先上传测试文件'))
        
            # 获取OCR配置
        config = self.env['baidu.ocr.config'].get_default_config()
        if not config:
            raise UserError(_('未找到有效的百度OCR配置，请先设置配置信息'))
        
        try:
            # 获取文件内容
            file_content = base64.b64decode(self.test_file)
            
            # 检查文件大小
            file_size = len(file_content)
            _logger.info("上传的文件大小: %d 字节", file_size)
            
            # 检查文件类型
            file_ext = os.path.splitext(self.test_filename)[1].lower() if self.test_filename else ''
            _logger.info("上传的文件类型: %s", file_ext)
            
            # 百度OCR支持的图片格式：PNG、JPG、JPEG、BMP、PDF
            supported_formats = ['.png', '.jpg', '.jpeg', '.bmp', '.pdf']
            if file_ext not in supported_formats:
                raise UserError(_('不支持的文件格式: %s，请上传PNG、JPG、JPEG、BMP或PDF格式的文件') % file_ext)
            
            # 设置图片预览
            self.image_preview = self.test_file
            
            # 调用百度OCR API
            _logger.info("开始调用百度OCR API...")
            ocr_result = config.recognize_invoice(file_content)
            _logger.info("百度OCR API调用完成")
            
            # 提取票据类型
            ticket_type = '未知'
            if ocr_result and 'words_result' in ocr_result and ocr_result['words_result']:
                # 检查words_result是否为列表
                if isinstance(ocr_result['words_result'], list) and len(ocr_result['words_result']) > 0:
                    first_result = ocr_result['words_result'][0]
                    ticket_type = first_result.get('type', '未知')
                    _logger.info("识别到的票据类型: %s", ticket_type)
            
            # 更新向导
            self.write({
                'raw_result': json.dumps(ocr_result, ensure_ascii=False, indent=2),
                'ticket_type': ticket_type
            })
            
            # 显示成功消息
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'ocr.debug.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'new',
                'flags': {'mode': 'readonly'},
                'context': self.env.context
            }
            
        except Exception as e:
            _logger.exception("OCR调试过程中发生错误: %s", str(e))
            error_message = str(e)
            
            # 添加更多错误信息
            if "image format error" in error_message:
                error_message += "\n可能原因：图片格式不正确或损坏，请确保上传的是有效的图片文件。"
            elif "IAM authentication failed" in error_message:
                error_message += "\n可能原因：API Key或Secret Key不正确，请检查配置。"
            
            raise UserError(_('OCR调试失败: %s') % error_message) 