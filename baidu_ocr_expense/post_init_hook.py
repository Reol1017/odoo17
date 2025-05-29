# -*- coding: utf-8 -*-

import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    """模块安装后的数据清理"""
    _logger.info("开始执行百度OCR费用模块的数据清理...")
    
    # 清理hr.expense中可能存在的非数字字段值
    expenses = env['hr.expense'].search([
        '|', '|',
        ('total_amount', '!=', False),
        ('total_tax', '!=', False),
        ('amount_in_figures', '!=', False)
    ])
    
    for expense in expenses:
        update_vals = {}
        
        # 清理total_amount字段
        if hasattr(expense, 'total_amount') and expense.total_amount:
            if isinstance(expense.total_amount, str):
                try:
                    update_vals['total_amount'] = float(expense.total_amount.replace(',', ''))
                except (ValueError, TypeError):
                    update_vals['total_amount'] = 0.0
        
        # 清理total_tax字段  
        if hasattr(expense, 'total_tax') and expense.total_tax:
            if isinstance(expense.total_tax, str):
                try:
                    update_vals['total_tax'] = float(expense.total_tax.replace(',', ''))
                except (ValueError, TypeError):
                    update_vals['total_tax'] = 0.0
        
        # 清理amount_in_figures字段
        if hasattr(expense, 'amount_in_figures') and expense.amount_in_figures:
            if isinstance(expense.amount_in_figures, str):
                try:
                    update_vals['amount_in_figures'] = float(expense.amount_in_figures.replace(',', ''))
                except (ValueError, TypeError):
                    update_vals['amount_in_figures'] = 0.0
        
        # 如果有需要更新的字段，执行更新
        if update_vals:
            try:
                expense.write(update_vals)
                _logger.info(f"更新费用记录 {expense.id}: {update_vals}")
            except Exception as e:
                _logger.error(f"更新费用记录 {expense.id} 失败: {e}")
    
    _logger.info("百度OCR费用模块数据清理完成")