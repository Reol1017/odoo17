/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

// 补丁 FormController
patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    },
    
    // 检查是否有实际的更改需要保存
    hasRealChanges() {
        // 检查表单是否真正有更改（不只是脏标记）
        const record = this.model.root;
        if (!record.isDirty) return false;
        
        // 检查是否是新记录
        if (record.isNew) return true;
        
        // 检查是否有字段值发生了实际改变
        const changes = record._changes || {};
        return Object.keys(changes).length > 0;
    },
    
    async beforeLeave() {
        // 只在有实际更改时才显示确认对话框
        if (this.hasRealChanges()) {
            return new Promise((resolve) => {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("保存确认"),
                    body: _t("您有未保存的更改。是否要保存这些更改？"),
                    confirm: async () => {
                        try {
                            await this.model.root.save();
                            this.notification.add(_t("保存成功"), {
                                type: "success",
                            });
                            resolve(true);
                        } catch (e) {
                            console.error("保存失败:", e);
                            this.notification.add(_t("保存失败"), {
                                type: "danger",
                            });
                            resolve(false);
                        }
                    },
                    confirmLabel: _t("保存"),
                    cancel: async () => {
                        await this.model.root.discard();
                        resolve(true);
                    },
                    cancelLabel: _t("放弃更改"),
                });
            });
        }
        return true;
    },
    
    async canBeRemoved() {
        if (this.hasRealChanges()) {
            return await this.beforeLeave();
        }
        return super.canBeRemoved(...arguments);
    },
});

// 补丁 ListController
patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    },
    
    // 检查列表中是否有实际的更改需要保存
    hasRealChanges() {
        return this.model.root.records.some(record => {
            if (!record.isDirty) return false;
            
            // 新记录
            if (record.isNew) return true;
            
            // 已存在记录有实际更改
            const changes = record._changes || {};
            return Object.keys(changes).length > 0;
        });
    },
    
    async beforeLeave() {
        // 只在有实际更改时才显示确认对话框
        if (this.hasRealChanges()) {
            return new Promise((resolve) => {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("保存确认"),
                    body: _t("您有未保存的更改。是否要保存这些更改？"),
                    confirm: async () => {
                        try {
                            // 只保存有实际更改的记录
                            const changedRecords = this.model.root.records.filter(record => {
                                if (!record.isDirty) return false;
                                if (record.isNew) return true;
                                const changes = record._changes || {};
                                return Object.keys(changes).length > 0;
                            });
                            
                            await Promise.all(changedRecords.map(record => record.save()));
                            this.notification.add(_t("保存成功"), {
                                type: "success",
                            });
                            resolve(true);
                        } catch (e) {
                            console.error("保存失败:", e);
                            this.notification.add(_t("保存失败"), {
                                type: "danger",
                            });
                            resolve(false);
                        }
                    },
                    confirmLabel: _t("保存"),
                    cancel: async () => {
                        // 丢弃所有有实际更改的记录
                        const changedRecords = this.model.root.records.filter(record => {
                            if (!record.isDirty) return false;
                            if (record.isNew) return true;
                            const changes = record._changes || {};
                            return Object.keys(changes).length > 0;
                        });
                        
                        await Promise.all(changedRecords.map(record => record.discard()));
                        resolve(true);
                    },
                    cancelLabel: _t("放弃更改"),
                });
            });
        }
        return true;
    },
    
    async canBeRemoved() {
        if (this.hasRealChanges()) {
            return await this.beforeLeave();
        }
        return super.canBeRemoved(...arguments);
    },
});

// 补丁表单的保存行为，防止自动保存
patch(FormController.prototype, {
    async save(options = {}) {
        // 如果没有实际更改，不执行保存
        if (!this.hasRealChanges()) {
            return;
        }
        return super.save(options);
    },
});