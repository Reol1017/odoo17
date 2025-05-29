import io
import json
import xlsxwriter
from odoo import models
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import date_utils
import base64
from io import BytesIO
from PIL import Image

class SaleOrder(models.Model):
    """ Added a function that to print sale order excel report
            which is added through server action """
    _inherit = "sale.order"
    
    @api.model
    def create_quotation_with_sudo(self, values):
        """使用sudo权限创建报价单"""
        try:
            # 准备报价单基本数据
            quotation_vals = {
                'partner_id': values.get('partner_id'),
                'date_order': values.get('date_order'),
                'state': 'draft',  # 确保是草稿状态
            }
    
            # 使用sudo创建报价单
            quotation = self.sudo().create(quotation_vals)
    
            # 创建订单行
            order_lines = values.get('order_lines', [])
            for line in order_lines:
                # 为每个订单行添加order_id
                line['order_id'] = quotation.id
                self.env['sale.order.line'].sudo().create(line)
    
            # 返回创建的报价单ID和名称
            return {
                'success': True,
                'quotation_id': quotation.id,
                'quotation_name': quotation.name,
                'message': f'报价单 {quotation.name} 已成功创建'
            }
        except Exception as e:
            # 捕获并返回任何错误
            return {
                'success': False,
                'error': str(e)
            }
    @api.model
    def update_quotation_with_sudo(self, quotation_id, values):
        """使用sudo权限更新报价单"""
        try:
            # 获取报价单记录并使用sudo提升权限
            quotation = self.sudo().browse(quotation_id)

            # 安全检查：确保只更新草稿状态的报价单
            if quotation.state != 'draft':
                return {
                    'success': False,
                    'error': '只能更新草稿状态的报价单'
                }

            # 更新报价单基本信息
            update_vals = {
                'partner_id': values.get('partner_id'),
            }

            # 如果提供了日期，则更新日期
            if values.get('date_order'):
                update_vals['date_order'] = values.get('date_order')

            # 更新报价单基本信息
            quotation.write(update_vals)

            # 处理订单行：删除现有行并创建新行
            # 首先删除所有现有行
            if quotation.order_line:
                quotation.order_line.sudo().unlink()

            # 创建新的订单行
            order_lines = values.get('order_lines', [])
            for line in order_lines:
                # 为每个订单行添加order_id
                line['order_id'] = quotation.id
                self.env['sale.order.line'].sudo().create(line)

            return {
                'success': True,
                'message': '报价单已成功更新'
            }

        except Exception as e:
            # 捕获并返回任何错误
            return {
                'success': False,
                'error': str(e)
            }
    def print_excel_report(self):
        """Function to print the Excel report.
        It passes the sale order data through a JS file to print the Excel file in English without changing the system language."""
        
        # 获取选中的销售订单ID
        active_ids = self._context.get('active_ids', [])
        if not active_ids:
            active_ids = [self.id]
        # 准备报告数据
        report_data = {
            'model': 'sale.order',
            'output_format': 'xlsx',
            'options': json.dumps(active_ids, default=date_utils.json_default),
            'report_name': 'Sale/Quotation Excel Report',
        }
        
        # 返回报告动作，并在上下文中设置语言为英文
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'data': report_data,
            'context': dict(self._context, lang='en_US'),  # 临时设置语言为英文
        }


    def get_xlsx_report(self, datas, response):
        """ From this function we can create and design the Excel file template
                 and the map the values in the corresponding cells
            :param datas: Selected record ids
            :param response: Response after creating excel
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        # for printing multiple sheet per file, iterate the sale orders
        for sale in self.env['sale.order'].browse(datas):

            ref = str(
                sale.client_order_ref) if \
                sale.client_order_ref is not False else ''
            # Copy the value to a variable set black if it is null instead
            # of printing 'FALSE' in the report
            payment_term = str(
                sale.payment_term_id.name) if \
                sale.payment_term_id.name is not False else ''
            # Copy the value to a variable set black if it is null instead
            # of printing 'FALSE' in the report
            fiscal_position = str(
                sale.fiscal_position_id.name) if \
                sale.fiscal_position_id.name is not False else ''
            sheet = workbook.add_worksheet(
                sale.name)  # set the sheet name as sale order name
            sheet.set_column(0, 8, 20)
            sale_date = sale.date_order.strftime('%Y/%m/%d')
            validity_date= sale.validity_date.strftime('%Y/%m/%d') if sale.validity_date else ''
            shipping = str(sale.incoterm.with_context(lang='en_US').name) if sale.incoterm else ''
            port = str(sale.incoterm_location) if sale.incoterm_location else ''
            address = str(sale.partner_id.contact_address_complete)
            # 查找最后一个逗号的位置
            comma_index = address.rfind(',')

            # 如果找到了逗号，则去除最后一个逗号及其后面的内容
            if comma_index != -1:
                address = address[:comma_index]
                
            # 获取币种
            currency_symbol = sale.currency_id.symbol
            currency_name = sale.currency_id.name
            
            # 获取联系人信息
            partner = str(sale.partner_id.child_ids[0].name) if sale.partner_id.child_ids else str(sale.partner_id.name)
            
            # 获取联系人电话和邮箱
            contact_email = ''
            contact_phone = ''
            
            # 首先尝试从第一个子联系人获取联系方式
            if sale.partner_id.child_ids:
                contact = sale.partner_id.child_ids[0]
                contact_email = contact.email or ''
                contact_phone = contact.phone or contact.mobile or ''
            # 如果没有子联系人或子联系人没有联系方式，尝试从主联系人获取
            else:
                contact_email = sale.partner_id.email or ''
                contact_phone = sale.partner_id.phone or sale.partner_id.mobile or ''
            
            # 获取销售员的电话和邮箱
            salesperson_email = sale.user_id.email or ''
            salesperson_phone = sale.user_id.phone or sale.user_id.mobile or ''
            
            # 定义格式 - 更改为兼容Office的格式
            # 1. 使用数字而非字符串表示字体大小
            # 2. 添加字体回退机制
            # 3. 修正边框样式为标准类型
            # 4. 确保颜色格式一致性
            
            head = workbook.add_format({
                'font_name': '微软雅黑',
                'font_size': 28,              # 数字而非字符串
                'align': 'center', 
                'bold': True, 
                'italic': True, 
                'border': 1                   # 使用标准边框值
            })
            
            txt = workbook.add_format({
                'font_name': '微软雅黑',
                'font_size': 10,              # 数字而非字符串
                'font_color': '#000000',
                'align': 'center', 
                'bold': True, 
                'border': 1                   # 使用标准边框值
            })
            
            txt_2 = workbook.add_format({
                'font_name': '微软雅黑',
                'font_size': 10,              # 数字而非字符串
                'font_color': '#000000',
                'align': 'left', 
                'bold': True, 
                'border': 0
            })
            
            txt_head = workbook.add_format({
                'font_name': '微软雅黑',
                'font_size': 36,              # 数字而非字符串
                'font_color': '#000000',
                'align': 'center', 
                'bold': True, 
                'border': 1                   # 使用标准边框值
            })
            
            txt_h2 = workbook.add_format({
                'font_name': '微软雅黑',
                'font_size': 20,              # 数字而非字符串
                'font_color': '#000000',
                'align': 'left', 
                'bold': True, 
                'border': 0
            })
            
            # 修改边框设置为更兼容的格式
            txt_line = workbook.add_format({
                'font_name': '微软雅黑',
                'font_size': 10,              # 数字而非字符串
                'font_color': '#000000',
                'align': 'center', 
                'valign': 'vcenter',
                'bold': True, 
                'border': 1,                  # 使用标准边框
                'border_color': '#808080'     # 边框颜色
            })
            
            txt_line_wrap = workbook.add_format({
                'font_name': '微软雅黑',
                'font_size': 10,              # 数字而非字符串
                'font_color': '#000000',
                'align': 'left', 
                'valign': 'vcenter', 
                'border': 1,                  # 使用标准边框
                'border_color': '#808080',    # 边框颜色
                'text_wrap': True
            })
            
            txt_line_right = workbook.add_format({
                'font_name': '微软雅黑',
                'font_size': 10,              # 数字而非字符串
                'font_color': '#000000',
                'align': 'right',
                'bold': True, 
                'border': 1,                  # 使用标准边框
                'border_color': '#808080'     # 边框颜色
            })
            
            txt_border = workbook.add_format({
                'font_name': '微软雅黑',
                'font_size': 8,               # 数字而非字符串
                'text_wrap': True,
                'bg_color': '#000000',
                'align': 'center', 
                'bold': True, 
                'border': 1                   # 使用标准边框值
            })
            
            txt_thead = workbook.add_format({
                'font_name': '微软雅黑',
                'font_size': 10,              # 数字而非字符串
                'bg_color': '#002060',
                'font_color': '#FFFFFF',
                'align': 'center', 
                'valign': 'vcenter', 
                'bold': True, 
                'border': 1                   # 添加边框以便于在Office中更好显示
            })
            
            border = workbook.add_format({
                'font_name': '微软雅黑',
                'font_size': 10,              # 数字而非字符串
                'border': 1,                  # 使用标准边框
                'text_wrap': True,
                'align': 'center',  
                'valign': 'vcenter', 
                'bg_color': '#EDF3F3',
            })
            
            # 设置列宽
            sheet.set_column('A:A', 10)  
            sheet.set_column('B:B', 12)
            sheet.set_column('C:C', 14) 
            sheet.set_column('D:D', 26)
            sheet.set_column('E:E', 12)
            sheet.set_column('F:F', 9)
            sheet.set_column('G:H', 9)
            sheet.set_column('I:I', 12)
            
            # 以下是填充数据的部分，保持不变
            sheet.write('A3', '报价单号', txt)
            sheet.write('A4', sale.name, txt)
            sheet.merge_range('B3:C3', '报价日期', txt)
            sheet.merge_range('B4:C4', sale_date, txt)
            sheet.write('D3', '报价有效期至', txt)
            sheet.write('D4', validity_date, txt)
            sheet.merge_range('E1:I4', '报价单', txt_head)
            #客户信息
            sheet.merge_range('A6:B6', '收件单位:', txt)
            sheet.merge_range('C6:D6', sale.partner_id.name, txt)
            sheet.merge_range('A7:B7', '项目地址:', txt)
            sheet.merge_range('C7:D7', address, txt)
            sheet.merge_range('A8:B8', '联系人:', txt)
            sheet.merge_range('C8:D8', partner, txt)
            sheet.merge_range('A9:B9', '联系电话:', txt)
            sheet.merge_range('C9:D9', contact_phone, txt)
            sheet.merge_range('A10:B10', '邮箱:', txt)
            sheet.merge_range('C10:D10', contact_email, txt)

            sheet.merge_range('E6:F6', '报价单位:', txt)
            sheet.merge_range('G6:I6', '南京优配架金属制品有限公司', txt)
            sheet.merge_range('E7:F7', '公司地址:', txt)
            sheet.merge_range('G7:I7', '上海市松江区虬泾路8号E栋103室', txt)
            sheet.merge_range('E8:F8', '联系人:', txt)
            sheet.merge_range('G8:I8', sale.user_id.name, txt)
            sheet.merge_range('E9:F9', '联系电话:', txt)
            sheet.merge_range('G9:I9', salesperson_phone, txt)
            sheet.merge_range('E10:F10', '邮箱:', txt)
            sheet.merge_range('G10:I10', salesperson_email, txt)
            
            #合计金额
            sheet.merge_range('A12:B12', '合计总金额:', txt_h2)
            sheet.write('C12', currency_name, txt_h2)  # 使用动态币种名称替代RMB
            sheet.merge_range('D12:I12', f'{sale.amount_total:,.2f}', txt_h2)
            sheet.merge_range('C13:I13', '13%增值税专用发票:', txt_2)
            
            #表头
            sheet.write('A15', '序号', txt_thead)
            sheet.write('B15', '品名', txt_thead) 
            sheet.write('C15', '颜色', txt_thead)
            sheet.write('D15', '规格', txt_thead) 
            sheet.write('E15', "数量", txt_thead) 
            sheet.write('F15', '单位', txt_thead) 
            sheet.merge_range('G15:H15', '单价', txt_thead)
            sheet.write('I15', '金额', txt_thead) 
            row = 14
            self._add_order_line(sheet, sale, row, txt_line_right, txt_line, txt_line_wrap, txt_thead, txt, currency_symbol)
            
        
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    def _add_order_line(self, sheet, sale, row, txt_line_right, txt_line, txt_line_wrap, txt_thead, txt, currency_symbol):
        # 遍历订单行
        line_count = 1
        total_amount = 0
        for line in sale.order_line:
            row += 1
            if line.display_type in ['line_section', 'line_note']:
                # 合并0-6列显示小节或备注文本
                if total_amount>0:
                    sheet.merge_range(row, 0, row, 7, '小计', txt_line_right)
                    sheet.write(row, 8, f"{currency_symbol}{total_amount:,.2f}", txt_line)
                    total_amount=0
                    row += 2
                line_name = line.name or ''
                if '-' in line_name:
                    # 以 '-' 分割文本
                    parts = line_name.split('-', 1)  # 只分割第一个'-'
                    left_part = parts[0].strip()
                    right_part = parts[1].strip() if len(parts) > 1 else ''
                    
                    # 写入分割前的文本到前面的列
                    sheet.merge_range(row, 0, row, 6, left_part, txt_line)
                    
                    # 检查右侧部分是否包含冒号
                    if '：' in right_part or ':' in right_part:
                        # 优先检查中文冒号，如果没有则检查英文冒号
                        if '：' in right_part:
                            colon_parts = right_part.split('：', 1)
                        else:
                            colon_parts = right_part.split(':', 1)
                        
                        # 将冒号前的文本放在第7列
                        sheet.write(row, 7, colon_parts[0].strip(), txt_line)
                        # 将冒号后的文本放在第8列
                        sheet.write(row, 8, colon_parts[1].strip(), txt_line)
                    else:
                        # 如果没有冒号，就将整个右侧部分合并到7-8列
                        sheet.merge_range(row, 7, row, 8, right_part, txt_line)
                else:
                    # 没有分隔符的情况，按原来的处理方式
                    sheet.merge_range(row, 0, row, 6, line_name, txt_line)
                    # 添加空白单元格在其他列保持格式一致
                    sheet.write(row, 7, '', txt_line)
                    sheet.write(row, 8, '', txt_line)
                   
                continue  # 跳到下一行
           
            color = line.product_color_id.name if line.product_color_id else ""
            spec = f"{line.warehouse_weight_id.specification or ''} - {line.warehouse_weight_id.name or ''}" 
            line_number = line_count  # 序号
            
            # 填写订单行数据
            sheet.write(row, 0, line_number, txt_line)  # 序号
            sheet.write(row, 1, line.product_id.name, txt_line)  # 品名
            sheet.write(row, 2, color, txt_line)  
            sheet.write(row, 3, spec, txt_line)  
            sheet.write(row, 4, line.product_uom_qty, txt_line)  # 数量
            sheet.write(row, 5, line.product_uom.name, txt_line)  # 单位
            
            # 单价 - 合并G和H列
            sheet.merge_range(row, 6, row, 7, f"{currency_symbol}{line.price_unit:,.2f}", txt_line)
            
            # 金额
            subtotal = line.price_subtotal
            sheet.write(row, 8, f"{currency_symbol}{subtotal:,.2f}", txt_line)
            
            # 累加总金额
            total_amount += subtotal
            
            line_count += 1
        row += 1
        sheet.merge_range(row, 0, row, 7, '小计', txt_line_right)
        sheet.write(row, 8, f"{currency_symbol}{total_amount:,.2f}", txt_line)
        row += 2
        self._add_order_footer(sheet, sale, row, txt_thead, txt_line, txt_line_wrap, txt, currency_symbol)
        
        return row

    def _add_order_footer(self, sheet, sale, row, txt_thead, txt_line, txt_line_wrap, txt, currency_symbol):
        row += 2
        sheet.write(row, 0, '付款方式', txt_line)
        payment_term = sale.payment_term_id.name if sale.payment_term_id else ''
        sheet.merge_range(row, 1, row, 4, payment_term, txt_line_wrap)
        sheet.write(row, 7, '合计', txt_line)
        row += 1
        sheet.set_row(row, 25)
        sheet.set_row(row+1, 25)
        sheet.merge_range(row, 0, row+1, 0, '付款资料', txt_line)
        payment_info = "企业名称：南京优配架金属制品有限公司\n开  户  行：农业银行南京支行横梁支行\n账        号：1011 7901 0400 068 26"
        sheet.merge_range(row, 1, row+1, 4, payment_info, txt_line_wrap)
        sheet.merge_range(row, 7, row+1, 7, '最终报价', txt_thead)
        sheet.merge_range(row, 8, row+1, 8, f'{currency_symbol}{sale.amount_total:,.2f}', txt_thead)  # 使用实际总金额
        row += 2
        sheet.write(row, 0, '交货期', txt_line)
        row += 1
        sheet.write(row, 0, '客户需求', txt_line)
        sheet.merge_range(row, 1, row, 8, '无其他需求', txt_line)
        row += 2
        sheet.merge_range(row, 6, row+3, 6, f'签字/盖章', txt_line)
        row += 3
     
        return row