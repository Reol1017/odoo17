odoo.define('baidu_ocr_expense.upload', function (require) {
    "use strict";

    var core = require('web.core');
    var Sidebar = require('web.Sidebar');
    var ListController = require('web.ListController');
    var session = require('web.session');
    var _t = core._t;

    // Add OCR upload button to expense list view sidebar
    ListController.include({
        renderSidebar: function ($node) {
            var self = this;
            this._super.apply(this, arguments);
            
            if (this.modelName === 'hr.expense' && this.sidebar) {
                this.sidebar.add_items('other', [{
                    label: _t('OCR Upload'),
                    callback: function () {
                        self._onOCRUpload();
                    }
                }]);
            }
        },
        
        _onOCRUpload: function () {
            var self = this;
            var $input = $('<input type="file" accept="image/*">');
            
            $input.on('change', function (e) {
                var file = e.target.files[0];
                if (!file) return;
                
                var reader = new FileReader();
                reader.onload = function (e) {
                    var data = e.target.result;
                    self._uploadInvoiceForOCR(data, file.name);
                };
                reader.readAsDataURL(file);
            });
            
            $input.click();
        },
        
        _uploadInvoiceForOCR: function (data, fileName) {
            var self = this;
            
            // First create attachment
            this._rpc({
                model: 'ir.attachment',
                method: 'create',
                args: [{
                    name: fileName,
                    datas: data.split(',')[1],
                    res_model: 'hr.expense',
                    type: 'binary',
                }],
            }).then(function (attachmentId) {
                return $.ajax({
                    url: '/baidu_ocr/upload_invoice',
                    type: 'POST',
                    data: {
                        'attachment_id': attachmentId
                    }
                });
            }).then(function (result) {
                var response = JSON.parse(result);
                if (response.success) {
                    self.do_notify(_t('Success'), _t('Expense created from OCR'));
                    self.reload();
                    // Open the created expense
                    self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'hr.expense',
                        res_id: response.expense_id,
                        views: [[false, 'form']],
                        target: 'current'
                    });
                } else {
                    self.do_warn(_t('Error'), response.error);
                }
            }).guardedCatch(function (error) {
                self.do_warn(_t('Error'), _t('Failed to process the invoice'));
            });
        }
    });
});