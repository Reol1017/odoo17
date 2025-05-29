/** @odoo-module **/

import {registry} from '@web/core/registry';
import {onWillStart, useState, Component, useRef} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {NotificationService} from "@web/core/notifications/notification_service";

class QuoteAction extends Component {
    setup() {
        
        this.rootRef = useRef("root");
        this.action = useService("action");
        this.orm = useService("orm");
        this.user = useService("user");
        this.notification = useService("notification");
        this.removeProduct = this.removeProduct.bind(this);
        this.updateProductSpec = this.updateProductSpec.bind(this);
        this.addCustomProduct = this.addCustomProduct.bind(this);
        this.updateCustomProductName = this.updateCustomProductName.bind(this);
        this.updateCustomProductCategory = this.updateCustomProductCategory.bind(this);
        this.updateCustomProductModelName = this.updateCustomProductModelName.bind(this);
        this.updateCustomProductSpec = this.updateCustomProductSpec.bind(this);
        this.updateCustomProductPrice = this.updateCustomProductPrice.bind(this);
        this.updateProductQuantity = this.updateProductQuantity.bind(this); // 确保这个方法已定义
        this.searchProductsByCategory = this.searchProductsByCategory.bind(this);
        //联系人
        this.searchPartners = this.searchPartners.bind(this);
        this.selectPartner = this.selectPartner.bind(this);
        this.loadCompanyContacts = this.loadCompanyContacts.bind(this);
        this.searchContacts = this.searchContacts.bind(this);
        this.selectContact = this.selectContact.bind(this);
        this.selectContactById = this.selectContactById.bind(this);
        //地址
        this.loadCompanyAddresses = this.loadCompanyAddresses.bind(this);
        this.selectAddressById = this.selectAddressById.bind(this);
        //订单
        this.searchQuotations = this.searchQuotations.bind(this);
        this.selectQuotation = this.selectQuotation.bind(this);
        this.formatDate = this.formatDate.bind(this);
        //规格

        this._fetchProductSpecs = this._fetchProductSpecs.bind(this);
        this.handleSpecInput = this.handleSpecInput.bind(this);
        this.validateSpecFormat = this.validateSpecFormat.bind(this);
        this.findMatchingSpec = this.findMatchingSpec.bind(this);
        this.parseSpecDimensions = this.parseSpecDimensions.bind(this);
        this._fetchModelsByProduct = this._fetchModelsByProduct.bind(this);
        this.selectProductModel = this.selectProductModel.bind(this);
        //颜色
        this.updateProductColor = this.updateProductColor.bind(this);
        this._fetchColors = this._fetchColors.bind(this);
        //保存订单数据
        this.updateCustomProductWeight = this.updateCustomProductWeight.bind(this);
        this.updateQuotation = this.updateQuotation.bind(this);
        this.createQuotation = this.createQuotation.bind(this);
        //拖动
        this.handleDragStart = this.handleDragStart.bind(this);
        this.handleDragOver = this.handleDragOver.bind(this);
        this.handleDrop = this.handleDrop.bind(this);
        this.updateWeightUnitPrice = this.updateWeightUnitPrice.bind(this);
        this.state = useState({
            name: '',
            date: '',
            user: '',
            partnername: '',
            products: [],
            availableProducts: [],
            totalAmount: 0,
            totalWeight: 0, 
            loading: true,
            error: null,
            recordData: null,
            dragSource: null,
            //产品类别参数
            availableSpecs: [],
            categories: [],
            productSearchTerm: '',
            productSearchResults: [],
            isSearching: false,
            //搜索客户参数
            partnerSearchTerm: '',
            partnerSearchResults: [],
            selectedPartner: null,
            selectedContact: null,
            contactSearchResults: [],
            isSearchingPartner: false,
            isSearchingContact: false,
            //地址
            addressSearchResults: [],
            selectedAddress: null,
            isSearchingAddress: false,
            companyAddress: '', // 存储公司默认地址
            //订单
            saleOrderSearchTerm: '',
            saleOrderSearchResults: [],
            isSearchingSaleOrder: false,
            selectedQuotation: null, // 添加选中的报价单
            //报价人
            userMobile: '',
            userEmail: '',
            userCompanyAddress: '',
            //规格
            quantity: 1,
            selectedProduct: null,
            modelsByProduct: {},
            //颜色
            colors: [], // 存储所有可用颜色
            selectedCategoryId: null,
            isUpdating: false,
            updateSuccess: null,
            updateError: null,
            isCreating: false,
            createSuccess: null,
            createError: null,
        });

        // 获取传递过来的记录 ID
        const recordId = this.props.action.context.default_record_id;
        console.log("传递过来的记录ID:", recordId);
        onWillStart(async () => {
            await this._fetchQuoteData(recordId);
            await this._fetchAvailableProducts();
            await this._fetchCategories();
            await this._fetchCurrentUserInfo();
            await this._fetchColors(); // 添加获取颜色的调用
            await this._fetchModelsByProduct();
        });
    }
    async _fetchModelsByProduct() {
        try {
            // 从warehouse.weight表获取所有型号数据
            const modelRecords = await this.orm.searchRead(
                'warehouse.weight',
                [],
                ['id', 'name', 'product_id', 'diameter', 'height', 'weight']
            );
            
            // 按产品ID和型号名称组织型号
            const modelsByProduct = {};
            const modelNamesByProduct = {}; // 新增：存储每个产品的唯一型号名称
            
            modelRecords.forEach(record => {
                if (record.product_id && record.product_id[0]) {
                    const productId = record.product_id[0];
                    
                    // 初始化产品的型号列表和型号名称集合
                    if (!modelsByProduct[productId]) {
                        modelsByProduct[productId] = [];
                        modelNamesByProduct[productId] = new Set();
                    }
                    
                    // 避免添加重复的型号ID
                    const existingModel = modelsByProduct[productId].find(m => m.id === record.id);
                    if (!existingModel) {
                        modelsByProduct[productId].push({
                            id: record.id,
                            name: record.name,
                            diameter: record.diameter,
                            height: record.height,
                            weight: record.weight || 0
                        });
                        
                        // 添加型号名称到集合中（自动去重）
                        modelNamesByProduct[productId].add(record.name);
                    }
                }
            });
            
            // 为每个产品创建去重后的型号名称数组
            const uniqueModelNamesByProduct = {};
            for (const productId in modelNamesByProduct) {
                uniqueModelNamesByProduct[productId] = Array.from(modelNamesByProduct[productId]);
            }
            
            this.state.modelsByProduct = modelsByProduct;
            this.state.uniqueModelNamesByProduct = uniqueModelNamesByProduct; // 添加到状态中
            
            console.log("产品型号映射:", modelsByProduct);
            console.log("产品唯一型号名称:", uniqueModelNamesByProduct);
        } catch (error) {
            console.error("获取型号列表失败:", error);
        }
    }
selectProductModel(index, modelName) {
    if (!modelName) return;
    
    const product = this.state.products[index];
    if (!product) return;
    
    // 找到该产品下所有具有相同名称的型号
    const availableModels = this.state.modelsByProduct[product.product_id] || [];
    const matchingModels = availableModels.filter(model => model.name === modelName);
    
    if (matchingModels.length > 0) {
        // 保存选中的型号名称
        product.model_name = modelName;
        
        // 默认选择第一个匹配的型号作为规格参考
        const selectedModel = matchingModels[0];
        
        // 将所有同型号的ID保存到产品中，用于后续规格匹配
        product.model_ids = matchingModels.map(model => model.id);
        product.matching_models = matchingModels;
        
        // 设置默认规格值（使用第一个型号的值）
        product.selected_spec_id = selectedModel.id;
        product.warehouse_weight_id = selectedModel.id;
        product.weight = selectedModel.weight || 0;
        
        // 更新规格信息
        product.product_diameter = selectedModel.diameter || '';
        product.product_height = selectedModel.height || '';
        
        // 更新显示的规格文本
        // 优先使用specification字段，与后端计算逻辑保持一致
        let specDisplay = selectedModel.specification || '';
        if (!specDisplay) {
            if (selectedModel.diameter && selectedModel.height) {
                specDisplay = `${selectedModel.diameter}-${selectedModel.height}`;
            } else if (selectedModel.diameter) {
                specDisplay = `D:${selectedModel.diameter}`;
            } else if (selectedModel.height) {
                specDisplay = `H:${selectedModel.height}`;
            }
        }
        
        product.userInputSpec = specDisplay;
        product.matchedSpec = specDisplay;
        
        // 清除错误
        product.specFormatError = null;
        product.specMatchError = null;
        
        // 计算单价
        product.unit_price = product.weight * (product.weight_unit_price || 0);
        
        // 更新总价
        product.total_price = product.unit_price * product.quantity;
        
        console.log(`更新产品 ${index} 的型号为 ${modelName}，规格为 ${specDisplay}，重量为 ${selectedModel.weight}kg`);
        console.log(`该型号下有 ${matchingModels.length} 个规格可供匹配`);
        
        // 重新计算总金额
        this._calculateTotal();
    }
}
    updateWeightUnitPrice(index, price) {
        const product = this.state.products[index];
        if (!product) return;
    
        product.weight_unit_price = parseFloat(price) || 0;
        
        // Calculate unit price based on weight and weight unit price
        product.unit_price = product.weight * product.weight_unit_price;
        
        // Calculate total price based on unit price and quantity
        product.total_price = product.unit_price * product.quantity;
        
        // Recalculate total
        this._calculateTotal();
    }

    displayNotification(params) {
        try {
            console.log("显示通知:", params);
            if (this.notification) {
                // 使用正确的通知服务 API
                this.notification.add(params.message || "", {
                    type: params.type || "info",
                    sticky: params.sticky !== undefined ? params.sticky : false,
                    title: params.title || "",
                });
            } else {
                console.error("通知服务未初始化");
                alert(`${params.title}: ${params.message}`);
            }
        } catch (error) {
            console.error("显示通知失败:", error);
            alert(`${params.title}: ${params.message}`);
        }
    }

    testNotification() {
        console.log("测试通知");
        try {
            // 使用 alert 确认函数被调用
            alert("测试通知函数被调用");

            // 直接使用通知服务的原始方法
            if (this.notification) {
                // 使用最简单的参数
                this.notification.add("这是一个测试消息", {
                    type: "success",
                });

                // 如果上面的方法不起作用，尝试这种格式
                /*
                this.notification.add({
                    message: "这是一个测试消息",
                    type: "success",
                });
                */

                console.log("通知方法已调用");
            } else {
                console.error("通知服务未初始化");
                alert("通知服务未初始化");
            }
        } catch (error) {
            console.error("测试通知失败:", error);
            alert("测试通知失败: " + (error.message || "未知错误"));
        }
    }
    // 修改拖拽相关方法，只有当用户抓住拖动把手时才能拖动
    handleDragStart(event, index) {
        // 检查事件源是否是拖动把手或其子元素
        const isDragHandle = event.target.closest('.drag-handle');
        
        // 如果不是从拖动把手开始的拖动，则取消拖动
        if (!isDragHandle) {
            event.preventDefault();
            event.stopPropagation();
            return false;
        }
        
        this.state.dragSource = index;
        // 设置拖拽效果和数据
        event.dataTransfer.effectAllowed = 'move';
        // 添加一些数据到dataTransfer
        event.dataTransfer.setData('text/plain', index);
        
        // 添加自定义样式到拖拽项
        setTimeout(() => {
            event.target.closest('tr').classList.add('dragging');
        }, 0);
    }
    
    handleDragOver(event, index) {
        event.preventDefault();
        
        const dragRow = document.querySelector('.dragging');
        if (!dragRow) return;
        
        const targetRow = event.currentTarget;
        
        const allRows = Array.from(document.querySelectorAll('tbody tr:not(.dragging)'));
        allRows.forEach(row => row.classList.remove('drag-over'));
        
        targetRow.classList.add('drag-over');
    }
    // 判断是否为备注、小节等非产品项
    isDescriptionLine(product) {
        // 使用明确的标记来识别，或者通过产品特征推断
        return product && (
            product.isDescription === true || 
            (!product.product_id && product.unit_price === 0 && product.quantity === 0) ||
            (product.display_type === 'line_note' || product.display_type === 'line_section')
        );
    }
    addDescriptionLine() {
        // 创建一个备注行对象
        const descriptionLine = {
            product_id: 0,
            product_name: "", // 默认为空，让用户输入
            quantity: 0,
            unit_price: 0,
            total_price: 0,
            isCustom: false,
            isDescription: true, // 明确标记为描述行
            display_type: 'line_section',
            weight: 0
        };
    
        this.state.products.push(descriptionLine);
        // 不需要重新计算总价，因为描述行不影响总价
    }
    handleDrop(event, dropIndex) {
        event.preventDefault();
        
        document.querySelectorAll('tr').forEach(row => {
            row.classList.remove('dragging', 'drag-over');
        });
        
        if (this.state.dragSource === null || this.state.dragSource === dropIndex) return;
        
        const newProducts = [...this.state.products];
        
        const [movedItem] = newProducts.splice(this.state.dragSource, 1);
        newProducts.splice(dropIndex, 0, movedItem);
        
        this.state.products = newProducts;
        this.state.dragSource = null;
        
        this._calculateTotal();
    }
    async updateQuotation() {
    try {
        // 显示加载状态
        this.state.isUpdating = true;

        // 检查是否选择了报价单
        if (!this.state.selectedQuotation || !this.state.selectedQuotation.id) {
            this.notification.add("请先选择要更新的报价单", {
                type: "danger",
                sticky: false,
            });
            this.state.isUpdating = false;
            return;
        }

        // 检查是否选择了客户
        if (!this.state.selectedPartner) {
            this.notification.add("请先选择客户", {
                type: "danger",
                sticky: false,
            });
            this.state.isUpdating = false;
            return;
        }

        // 检查是否有产品
        if (this.state.products.length === 0) {
            this.notification.add("请至少添加一个产品", {
                type: "danger",
                sticky: false,
            });
            this.state.isUpdating = false;
            return;
        }

        // 准备订单行数据
        const orderLines = [];
        for (const product of this.state.products) {
            // 检查产品数据是否完整
            if (!product.product_name) {
                this.notification.add("产品名称不能为空", {
                    type: "danger",
                    sticky: false,
                });
                this.state.isUpdating = false;
                return;
            }

            // 创建订单行数据
            const line = {
                product_uom_qty: product.quantity || 1,
                price_unit: product.unit_price || 0,
                weight_unit_price: product.weight_unit_price || 0,
            };

            // 如果是描述行，添加display_type
            if (product.isDescription) {
                line.display_type = product.display_type || 'line_section';
                line.name = product.product_name;
                // 描述行通常不需要数量和单价
                line.product_uom_qty = 0;
                line.price_unit = 0;
            } else {
                // 构建完整的产品描述
                let productDescription = product.product_name;
                if (product.isCustom) {
                    // 自定义产品：只用括号括起来，不加前缀
                    // 类别
                    if (product.categ_id && Array.isArray(product.categ_id)) {
                        const category = this.state.categories.find(cat => cat.id === product.categ_id[0]);
                        if (category) {
                            productDescription += ` (${category.name})`;
                        }
                    } else if (product.category) {
                        productDescription += ` (${product.category})`;
                    }
                    // 型号
                    if (product.model_name) {
                        productDescription += ` (${product.model_name})`;
                    }
                    // 规格
                    if (product.matchedSpec) {
                        productDescription += ` (${product.matchedSpec})`;
                    } else if (product.userInputSpec) {
                        productDescription += ` (${product.userInputSpec})`;
                    }
                    // 颜色
                    if (product.color_name) {
                        productDescription += ` (${product.color_name})`;
                    }
                } else {
                    // 普通产品：保持原有逻辑
                    // 添加产品类别信息
                    if (product.categ_id && Array.isArray(product.categ_id)) {
                        const category = this.state.categories.find(cat => cat.id === product.categ_id[0]);
                        if (category) {
                            productDescription += ` (类别: ${category.name})`;
                        }
                    } else if (product.category) {
                        productDescription += ` (类别: ${product.category})`;
                    }
                    // 添加型号信息
                    if (product.model_name) {
                        productDescription += ` (型号: ${product.model_name})`;
                    }
                    // 添加规格信息
                    if (product.matchedSpec) {
                        productDescription += ` (规格: ${product.matchedSpec})`;
                    } else if (product.userInputSpec) {
                        productDescription += ` (规格: ${product.userInputSpec})`;
                    }
                    // 添加颜色信息
                    if (product.color_name) {
                        productDescription += ` (颜色: ${product.color_name})`;
                    }
                }
                // 更新行描述
                line.name = productDescription;
                // 只有非自定义产品才设置product_id
                if (!product.isCustom && product.product_id > 0) {
                    line.product_id = product.product_id;
                }
                // 添加颜色信息
                if (product.color_id) {
                    line.product_color_id = product.color_id;
                }
                // 添加世仓规格信息
                if (product.selected_spec_id) {
                    line.warehouse_weight_id = product.selected_spec_id;
                }
                // 添加直径和高度信息
                if (product.product_diameter) {
                    line.product_diameter = product.product_diameter;
                }
                if (product.product_height) {
                    line.product_height = product.product_height;
                }
            }
            orderLines.push(line);
        }

        console.log("准备的订单行数据:", orderLines);

        // 调用自定义方法使用sudo权限更新报价单
        const result = await this.orm.call(
            'sale.order',
            'update_quotation_with_sudo',
            [
                this.state.selectedQuotation.id,
                {
                    partner_id: this.state.selectedPartner.id,
                    date_order: this.state.date || new Date().toISOString(),
                    order_lines: orderLines
                }
            ]
        );

        console.log("更新报价单结果:", result);

        if (result.success) {
            // 显示成功消息
            this.notification.add(`报价单 ${this.state.selectedQuotation.name} 已成功更新`, {
                type: "success",
                sticky: false,
            });

            // 重新加载报价单数据
            const updatedQuotation = await this.orm.read(
                'sale.order',
                [this.state.selectedQuotation.id],
                ['name', 'partner_id', 'date_order', 'order_line']
            );

            if (updatedQuotation && updatedQuotation.length > 0) {
                this.state.selectedQuotation = updatedQuotation[0];
                
                // 可选：重新加载产品列表以反映更新后的状态
                await this.selectQuotation(updatedQuotation[0]);
            }
        } else {
            // 显示错误消息
            this.notification.add(result.error || "更新报价单失败", {
                type: "danger",
                sticky: true,
            });
        }
    } catch (error) {
        console.error("更新报价单时出错:", error);
        // 尝试提取更详细的错误信息
        let errorMessage = "更新报价单失败";
        if (error.data && error.data.message) {
            errorMessage += ": " + error.data.message;
        } else if (error.message) {
            errorMessage += ": " + error.message;
        }

        // 显示错误消息
        this.notification.add(errorMessage, {
            type: "danger",
            sticky: true,
        });
    } finally {
        this.state.isUpdating = false;
    }
}
async createQuotation() {
    try {
        // 显示加载状态
        this.state.isCreating = true;

        // 检查是否选择了客户
        if (!this.state.selectedPartner) {
            this.notification.add("请先选择客户", {
                type: "danger",
                sticky: false,
            });
            this.state.isCreating = false;
            return;
        }

        // 检查是否有产品
        if (this.state.products.length === 0) {
            this.notification.add("请至少添加一个产品", {
                type: "danger",
                sticky: false,
            });
            this.state.isCreating = false;
            return;
        }

        // 准备订单行数据
        const orderLines = [];

        for (const product of this.state.products) {
            // 检查产品数据是否完整（仅对非描述行）
            if (!product.isDescription && !product.product_name) {
                this.notification.add("产品名称不能为空", {
                    type: "danger",
                    sticky: false,
                });
                this.state.isCreating = false;
                return;
            }

            // 创建行数据对象
            const line = {
                name: product.product_name,
                product_uom_qty: product.quantity || 1,
                price_unit: product.unit_price || 0,
                weight_unit_price: product.weight_unit_price || 0,
            };

            // 如果是描述行，添加 display_type
            if (product.isDescription) {
                line.display_type = product.display_type || 'line_section';
                // 描述行通常不需要数量和单价
                line.product_uom_qty = 0;
                line.price_unit = 0;
            } else {
                // 构建完整的产品描述
                let productDescription = product.product_name;
                if (product.isCustom) {
                    // 自定义产品：只用括号括起来，不加前缀
                    // 类别
                    if (product.categ_id && Array.isArray(product.categ_id)) {
                        const category = this.state.categories.find(cat => cat.id === product.categ_id[0]);
                        if (category) {
                            productDescription += ` (${category.name})`;
                        }
                    } else if (product.category) {
                        productDescription += ` (${product.category})`;
                    }
                    // 型号
                    if (product.model_name) {
                        productDescription += ` (${product.model_name})`;
                    }
                    // 规格
                    if (product.matchedSpec) {
                        productDescription += ` (${product.matchedSpec})`;
                    } else if (product.userInputSpec) {
                        productDescription += ` (${product.userInputSpec})`;
                    }
                    // 颜色
                    if (product.color_name) {
                        productDescription += ` (${product.color_name})`;
                    }
                } else {
                    // 普通产品：保持原有逻辑
                    // 添加产品类别信息
                    if (product.categ_id && Array.isArray(product.categ_id)) {
                        const category = this.state.categories.find(cat => cat.id === product.categ_id[0]);
                        if (category) {
                            productDescription += ` (类别: ${category.name})`;
                        }
                    } else if (product.category) {
                        productDescription += ` (类别: ${product.category})`;
                    }
                    // 添加型号信息
                    if (product.model_name) {
                        productDescription += ` (型号: ${product.model_name})`;
                    }
                    // 添加规格信息
                    if (product.matchedSpec) {
                        productDescription += ` (规格: ${product.matchedSpec})`;
                    } else if (product.userInputSpec) {
                        productDescription += ` (规格: ${product.userInputSpec})`;
                    }
                    // 添加颜色信息
                    if (product.color_name) {
                        productDescription += ` (颜色: ${product.color_name})`;
                    }
                }
                // 更新行描述
                line.name = productDescription;
                // 如果是自定义产品，查找或创建虚拟产品
                if (product.isCustom) {
                    const existing = await this.orm.searchRead('product.product', [
                        ['name', '=', '虚拟产品'],
                        ['type', '=', 'product'],
                        ['sale_ok', '=', true],
                    ], ['id']);

                    if (existing.length > 0) {
                        line.product_id = existing[0].id;
                    } else {
                        // 创建一个新的虚拟产品
                        line.product_id = await this.orm.create('product.product', [{
                            name: '虚拟产品',
                            type: 'product',
                            sale_ok: true,
                            list_price: product.unit_price || 0,
                        }]);
                    }
                } else if (product.product_id > 0) {
                    line.product_id = product.product_id;
                }
                // 添加颜色信息
                if (product.color_id) {
                    line.product_color_id = product.color_id;
                }
                // 添加世仓规格信息
                if (product.selected_spec_id) {
                    line.warehouse_weight_id = product.selected_spec_id;
                }
                // 添加直径和高度信息
                if (product.product_diameter) {
                    line.product_diameter = product.product_diameter;
                }
                if (product.product_height) {
                    line.product_height = product.product_height;
                }
            }
            orderLines.push(line);
        }

        console.log("准备的订单行数据:", orderLines);

        // 准备创建数据
        const createData = {
            partner_id: this.state.selectedPartner.id,
            order_line: [], // 将在下面填充
        };

        // 如果有日期，添加到创建数据
        if (this.state.date) {
            createData.date_order = this.state.date;
        } else {
            // 使用当前日期
            createData.date_order = new Date().toISOString().split('T')[0];
        }

        // 为每个新行创建命令 (0, 0, values) - 创建记录
        for (const line of orderLines) {
            createData.order_line.push([0, 0, line]);
        }

        console.log("发送到服务器的创建数据:", createData);

        // 调用ORM创建报价单
        const newQuotationId = await this.orm.create(
            'sale.order',
            [createData]
        );

        console.log("创建报价单结果:", newQuotationId);

        if (newQuotationId) {
            // 显示成功消息
            this.notification.add("新报价单已成功创建", {
                type: "success",
                sticky: false,
            });

            // 清空产品列表，准备下一个报价单
            this.state.products = [];

            // 重新计算总金额
            this._calculateTotal();
        } else {
            this.notification.add("创建报价单失败", {
                type: "danger",
                sticky: false,
            });
        }
    } catch (error) {
        console.error("创建报价单时出错:", error);
        // 尝试提取更详细的错误信息
        let errorMessage = "创建报价单失败";
        if (error.data && error.data.message) {
            errorMessage += ": " + error.data.message;
        } else if (error.message) {
            errorMessage += ": " + error.message;
        }

        // 显示错误消息
        this.notification.add(errorMessage, {
            type: "danger",
            sticky: true,
        });
    } finally {
        this.state.isCreating = false;
    }
}


    // 添加获取颜色的方法
    async _fetchColors() {
        try {
            const colors = await this.orm.searchRead(
                'product.color',
                [],
                ['id', 'name', 'notes']
            );
            this.state.colors = colors;
            console.log("获取到的颜色列表:", colors);
        } catch (error) {
            console.error("获取颜色列表失败:", error);
        }
    }

    // 更新自定义产品重量的方法
    updateCustomProductWeight(index, weight) {
        const product = this.state.products[index];
        if (!product) return;
    
        product.weight = parseFloat(weight) || 0;
    
        // Calculate unit price = weight × weight_unit_price
        product.unit_price = product.weight * (product.weight_unit_price || 0);
        
        // Update total price = unit_price × quantity
        product.total_price = product.unit_price * product.quantity;
    
        // Recalculate total
        this._calculateTotal();
    }

    // 添加更新产品颜色的方法
    updateProductColor(index, colorId) {
        if (!colorId) return;

        const product = this.state.products[index];
        if (!product) return;

        // 找到选中的颜色
        const selectedColor = this.state.colors.find(color => color.id === parseInt(colorId));
        if (selectedColor) {
            product.color_id = selectedColor.id;
            product.color_name = selectedColor.name;
            product.color_notes = selectedColor.notes;
            console.log(`更新产品 ${index} 的颜色为 ${selectedColor.name}`);
        }
    }
validateSpecFormat(specString) {
    if (!specString || !specString.trim()) return false;
    
    const cleanString = specString.trim().toLowerCase();
    
    // 检查字符串是否包含任何数字
    if (!/\d/.test(cleanString)) return false;
    
    // 有效模式:
    // 1. "数字-数字" 格式 (例如 "800-1800")
    const diameterHeightPattern = /^\d+(\.\d+)?[\s-]*\d+(\.\d+)?$/;
    
    // 2. "D:数字" 或 "D 数字" 或 "D数字" 格式
    const diameterPattern = /^d[\s:]*\d+(\.\d+)?$/i;
    
    // 3. "H:数字" 或 "H 数字" 或 "H数字" 格式
    const heightPattern = /^h[\s:]*\d+(\.\d+)?$/i;
    
    // 4. 单个数字 (默认视为直径)
    const singleNumberPattern = /^\d+(\.\d+)?$/;
    
    return diameterHeightPattern.test(cleanString) || 
           diameterPattern.test(cleanString) || 
           heightPattern.test(cleanString) || 
           singleNumberPattern.test(cleanString);
}

findMatchingSpec(inputSpec, availableSpecs) {
    if (!inputSpec || !availableSpecs || availableSpecs.length === 0) return null;
    
    // 获取当前活动产品索引和产品
    const product = this.state.products[this.state.activeProductIndex];
    if (!product) return null;
    
    // 清理和验证输入
    const cleanInput = inputSpec.trim().toLowerCase();
    if (!this.validateSpecFormat(cleanInput)) {
        console.warn("无效的规格格式:", cleanInput);
        return null;
    }
    
    // 根据模型选择确定要搜索的规格
    const specsToSearch = product.model_name && product.matching_models && product.matching_models.length > 0 
        ? product.matching_models 
        : availableSpecs;
    
    console.log("要搜索的规格:", specsToSearch.length, "个规格");
    
    // 首先尝试精确名称匹配
    const exactNameMatch = specsToSearch.find(spec => 
        spec.name && spec.name.trim().toLowerCase() === cleanInput);
    if (exactNameMatch) {
        console.log("找到精确名称匹配:", exactNameMatch.name);
        return exactNameMatch;
    }
    
    // 如果可用，尝试精确规格匹配
    const exactSpecMatch = specsToSearch.find(spec => 
        spec.specification && spec.specification.trim().toLowerCase() === cleanInput);
    if (exactSpecMatch) {
        console.log("找到精确规格匹配:", exactSpecMatch.specification);
        return exactSpecMatch;
    }
    
    // 从输入中解析尺寸
    const inputDimensions = this.parseSpecDimensions(cleanInput);
    console.log("解析的尺寸:", inputDimensions);
    
    // 创建带有尺寸的规格对象进行比较
    const specsWithDimensions = specsToSearch.map(spec => ({
        spec: spec,
        d: this.extractNumber(spec.diameter || '0'),
        h: this.extractNumber(spec.height || '0'),
        hasDiameter: !!spec.diameter,
        hasHeight: !!spec.height
    }));
    
    // 情况 1: 同时指定了直径和高度
    if (inputDimensions.d > 0 && inputDimensions.h > 0) {
        console.log("匹配 D-H 模式");
        
        // 首先尝试精确的 D-H 匹配
        const exactDHMatch = specsWithDimensions.find(item => 
            Math.abs(item.d - inputDimensions.d) < 0.01 && 
            Math.abs(item.h - inputDimensions.h) < 0.01);
        
        if (exactDHMatch) {
            console.log("找到精确的 D-H 匹配");
            return exactDHMatch.spec;
        }
        
        // 尝试找到覆盖请求尺寸的规格（两个维度都更大）
        const coveringSpecs = specsWithDimensions.filter(item => 
            item.hasDiameter && item.hasHeight && 
            item.d >= inputDimensions.d && item.h >= inputDimensions.h);
        
        if (coveringSpecs.length > 0) {
            console.log("找到覆盖规格:", coveringSpecs.length);
            // 按面积差异最小排序，找到最接近的匹配
            coveringSpecs.sort((a, b) => {
                const aDiff = (a.d * a.h) - (inputDimensions.d * inputDimensions.h);
                const bDiff = (b.d * b.h) - (inputDimensions.d * inputDimensions.h);
                return aDiff - bDiff;
            });
            
            return coveringSpecs[0].spec;
        }
        
        // 如果没有覆盖规格，按总尺寸差异找到最接近的匹配
        const bothDimensionSpecs = specsWithDimensions.filter(item => item.hasDiameter && item.hasHeight);
        if (bothDimensionSpecs.length > 0) {
            bothDimensionSpecs.sort((a, b) => {
                const aDiff = Math.abs(a.d - inputDimensions.d) + Math.abs(a.h - inputDimensions.h);
                const bDiff = Math.abs(b.d - inputDimensions.d) + Math.abs(b.h - inputDimensions.h);
                return aDiff - bDiff;
            });
            
            console.log("使用最接近的总体匹配");
            return bothDimensionSpecs[0].spec;
        }
    }
    
    // 情况 2: 仅指定直径
    if (inputDimensions.d > 0 && inputDimensions.h === 0) {
        console.log("匹配仅直径模式");
        
        // 首先尝试只有直径没有高度的规格（精确匹配单规格）
        const diameterOnlySpecs = specsWithDimensions.filter(item => 
            item.hasDiameter && !item.hasHeight);
        
        if (diameterOnlySpecs.length > 0) {
            // 找精确或最接近的单规格直径
            const exactDMatch = diameterOnlySpecs.find(item => 
                Math.abs(item.d - inputDimensions.d) < 0.01);
            
            if (exactDMatch) {
                console.log("找到精确直径匹配（无高度）");
                return exactDMatch.spec;
            }
            
            // 找最接近的
            diameterOnlySpecs.sort((a, b) => 
                Math.abs(a.d - inputDimensions.d) - Math.abs(b.d - inputDimensions.d));
            
            console.log("使用最接近的直径匹配（无高度）");
            return diameterOnlySpecs[0].spec;
        }
        
        // 其次尝试有直径也有高度的规格
        const diameterSpecs = specsWithDimensions.filter(item => item.hasDiameter);
        if (diameterSpecs.length === 0) return null;
        
        // 尝试精确直径匹配
        const exactDMatch = diameterSpecs.find(item => 
            Math.abs(item.d - inputDimensions.d) < 0.01);
        
        if (exactDMatch) {
            console.log("找到精确直径匹配");
            return exactDMatch.spec;
        }
        
        // 找到直径 >= 输入的规格（覆盖规格）
        const coveringDSpecs = diameterSpecs.filter(item => item.d >= inputDimensions.d);
        
        if (coveringDSpecs.length > 0) {
            console.log("找到覆盖直径规格");
            // 按最小直径优先排序
            coveringDSpecs.sort((a, b) => a.d - b.d);
            return coveringDSpecs[0].spec;
        }
        
        // 如果没有覆盖规格，找到最接近的直径
        diameterSpecs.sort((a, b) => 
            Math.abs(a.d - inputDimensions.d) - Math.abs(b.d - inputDimensions.d));
        
        console.log("使用最接近的直径匹配");
        return diameterSpecs[0].spec;
    }
    
    // 情况 3: 仅指定高度
    if (inputDimensions.d === 0 && inputDimensions.h > 0) {
        console.log("匹配仅高度模式");
        
        // 首先尝试只有高度没有直径的规格（精确匹配单规格）
        const heightOnlySpecs = specsWithDimensions.filter(item => 
            !item.hasDiameter && item.hasHeight);
        
        if (heightOnlySpecs.length > 0) {
            // 找精确或最接近的单规格高度
            const exactHMatch = heightOnlySpecs.find(item => 
                Math.abs(item.h - inputDimensions.h) < 0.01);
            
            if (exactHMatch) {
                console.log("找到精确高度匹配（无直径）");
                return exactHMatch.spec;
            }
            
            // 找最接近的
            heightOnlySpecs.sort((a, b) => 
                Math.abs(a.h - inputDimensions.h) - Math.abs(b.h - inputDimensions.h));
            
            console.log("使用最接近的高度匹配（无直径）");
            return heightOnlySpecs[0].spec;
        }
        
        // 其次尝试有高度也有直径的规格
        const heightSpecs = specsWithDimensions.filter(item => item.hasHeight);
        if (heightSpecs.length === 0) return null;
        
        // 尝试精确高度匹配
        const exactHMatch = heightSpecs.find(item => 
            Math.abs(item.h - inputDimensions.h) < 0.01);
        
        if (exactHMatch) {
            console.log("找到精确高度匹配");
            return exactHMatch.spec;
        }
        
        // 找到高度 >= 输入的规格（覆盖规格）
        const coveringHSpecs = heightSpecs.filter(item => item.h >= inputDimensions.h);
        
        if (coveringHSpecs.length > 0) {
            console.log("找到覆盖高度规格");
            // 按最小高度优先排序
            coveringHSpecs.sort((a, b) => a.h - b.h);
            return coveringHSpecs[0].spec;
        }
        
        // 如果没有覆盖规格，找到最接近的高度
        heightSpecs.sort((a, b) => 
            Math.abs(a.h - inputDimensions.h) - Math.abs(b.h - inputDimensions.h));
        
        console.log("使用最接近的高度匹配");
        return heightSpecs[0].spec;
    }
    
    // 未找到有效尺寸
    console.warn("未找到匹配的尺寸模式");
    return null;
}
parseSpecDimensions(specString) {
    if (!specString) return {d: 0, h: 0};
    
    const cleanString = specString.trim().toLowerCase();
    
    // 情况 1: "数字-数字" 格式 (例如 "800-1800")
    if (cleanString.includes('-')) {
        const parts = cleanString.split('-').map(part => part.trim());
        return {
            d: this.extractNumber(parts[0]),
            h: this.extractNumber(parts[1])
        };
    }
    
    // 情况 2: "D:数字" 格式 (匹配更多D前缀变体)
    if (/^d[\s:]*\d/i.test(cleanString)) {
        return {
            d: this.extractNumber(cleanString),
            h: 0
        };
    }
    
    // 情况 3: "H:数字" 格式 (匹配更多H前缀变体)
    if (/^h[\s:]*\d/i.test(cleanString)) {
        return {
            d: 0,
            h: this.extractNumber(cleanString)
        };
    }
    
    // 情况 4: 单个数字 (默认视为直径)
    return {
        d: this.extractNumber(cleanString),
        h: 0
    };
}
// 处理规格输入的方法
handleSpecInput(index, inputValue) {
    const product = this.state.products[index];
    if (!product) return;

    // 保存当前操作的产品索引
    this.state.activeProductIndex = index;
    
    // 清除之前的匹配结果
    product.selected_spec_id = null;
    product.warehouse_weight_id = null;
    product.product_diameter = '';
    product.product_height = '';
    product.weight = 0;
    product.total_price = 0;
    product.matchSuccess = null;

    // 保存用户输入
    product.userInputSpec = inputValue;

    // 如果输入为空，清空所有相关信息并返回
    if (!inputValue.trim()) {
        product.specFormatError = null;
        product.specMatchError = null;
        return;
    }

    // 验证格式
    if (!this.validateSpecFormat(inputValue)) {
        product.specFormatError = "格式不正确，请输入有效的规格格式";
        product.specMatchError = null;
        return;
    }
    
    product.specFormatError = null;

    // 查找匹配的规格
    const matchingSpec = this.findMatchingSpec(inputValue, product.matching_models || product.available_specs);

    if (matchingSpec) {
        product.selected_spec_id = matchingSpec.id;
        product.warehouse_weight_id = matchingSpec.id;
        product.weight = matchingSpec.weight || 0;
        
        // 存储匹配到的直径和高度
        product.product_diameter = matchingSpec.diameter || '';
        product.product_height = matchingSpec.height || '';
        
        // 计算单价和总价
        product.unit_price = product.weight * (product.weight_unit_price || 0);
        product.total_price = product.unit_price * product.quantity;
        
        // 分析用户输入的格式
        const inputDimensions = this.parseSpecDimensions(inputValue);
        const isDiameterOnly = inputDimensions.d > 0 && inputDimensions.h === 0;
        const isHeightOnly = inputDimensions.d === 0 && inputDimensions.h > 0;
        
        // 使用匹配到的记录的规格字段 (specification) 作为显示值
        // 如果没有规格字段，则根据匹配记录的直径和高度构建显示
        let matchedSpecDisplay = '';
        
        if (matchingSpec.specification) {
            // 优先使用后端计算的规格字段
            matchedSpecDisplay = matchingSpec.specification;
        } else if (matchingSpec.diameter && matchingSpec.height) {
            matchedSpecDisplay = `${matchingSpec.diameter}-${matchingSpec.height}`;
        } else if (matchingSpec.diameter) {
            matchedSpecDisplay = `D:${matchingSpec.diameter}`;
        } else if (matchingSpec.height) {
            matchedSpecDisplay = `H:${matchingSpec.height}`;
        }
        
        // 根据用户输入类型和匹配结果定制成功提示
        if (isDiameterOnly) {
            // 用户只输入了直径
            if (matchingSpec.diameter && !matchingSpec.height) {
                // 匹配到只有直径的记录
                product.matchSuccess = "完全匹配直径规格：" + matchedSpecDisplay;
            } else if (matchingSpec.diameter && matchingSpec.height) {
                // 匹配到直径和高度都有的记录
                product.matchSuccess = "找到符合直径的规格：" + matchedSpecDisplay;
            }
        } else if (isHeightOnly) {
            // 用户只输入了高度
            if (matchingSpec.height && !matchingSpec.diameter) {
                // 匹配到只有高度的记录
                product.matchSuccess = "完全匹配高度规格：" + matchedSpecDisplay;
            } else if (matchingSpec.diameter && matchingSpec.height) {
                // 匹配到直径和高度都有的记录
                product.matchSuccess = "找到符合高度的规格：" + matchedSpecDisplay;
            }
        } else {
            // 用户输入了双规格（直径和高度）
            if (matchingSpec.diameter && matchingSpec.height) {
                const dMatch = Math.abs(inputDimensions.d - this.extractNumber(matchingSpec.diameter)) < 0.01;
                const hMatch = Math.abs(inputDimensions.h - this.extractNumber(matchingSpec.height)) < 0.01;
                
                if (dMatch && hMatch) {
                    product.matchSuccess = "完全匹配规格：" + matchedSpecDisplay;
                } else {
                    product.matchSuccess = "找到最接近的规格：" + matchedSpecDisplay;
                }
            }
        }
        
        // 为显示设置匹配的规格文本
        product.matchedSpec = matchedSpecDisplay;
        product.specMatchError = null;
        
        // 记录匹配结果
        console.log(`产品 ${index} 匹配成功: ${product.matchSuccess}`);
        console.log(`匹配规格ID: ${matchingSpec.id}, 重量: ${matchingSpec.weight}kg`);
        console.log(`用户输入: ${inputValue}, 匹配显示: ${matchedSpecDisplay}`);
    } else {
        product.specMatchError = "未找到匹配的规格";
        console.warn(`产品 ${index} 未找到匹配规格，用户输入: ${inputValue}`);
    }

    // 重新计算总金额
    this._calculateTotal();
}
formatSpecDisplay(spec) {
    if (!spec) return '';
    
    // 如果规格对象有specification字段，优先使用它
    if (spec.specification) {
        return spec.specification;
    }
    
    // 否则，按照与后端相同的逻辑构造规格显示
    let display = '';
    if (spec.diameter && spec.height) {
        // 两者都有，使用组合格式
        display = `${spec.diameter}-${spec.height}`;
    } else if (spec.height) {
        // 只有高度
        display = `H:${spec.height}`;
    } else if (spec.diameter) {
        // 只有直径
        display = `D:${spec.diameter}`;
    }
    
    // 可选地添加重量信息
    if (display && spec.weight) {
        display += ` (${spec.weight}kg)`;
    }
    
    return display;
}
    async _fetchProductSpecs(productId) {
    if (!productId) return [];

    try {
        // 查询warehouse.weight表中与所选产品相关的规格
        const specs = await this.orm.searchRead(
            'warehouse.weight',
            [['product_id', '=', productId]],
            ['id', 'name', 'specification', 'diameter', 'height', 'weight']
        );

        console.log(`获取到产品ID ${productId} 的规格:`, specs);
        return specs;
    } catch (error) {
        console.error(`获取产品规格失败:`, error);
        return [];
    }
}

    // 格式化日期的辅助方法
    formatDate(dateString) {
        if (!dateString) return '';

        // 处理Odoo日期时间格式
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return dateString; // 如果无法解析，返回原始字符串

        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    }

    // 修改获取当前用户信息的方法
    async _fetchCurrentUserInfo() {
        try {
            // 获取当前用户ID
            const currentUserId = await this.user.userId;

            if (!currentUserId) {
                console.error("无法获取当前用户ID");
                return;
            }

            // 获取当前用户信息
            const currentUser = await this.orm.call(
                'res.users',
                'read',
                [currentUserId], // 使用用户服务获取的用户ID
                {fields: ['name', 'mobile', 'email', 'company_id']}
            );

            if (currentUser && currentUser.length > 0) {
                const user = currentUser[0];
                this.state.user = user.name || '';
                this.state.userMobile = user.mobile || '';
                this.state.userEmail = user.email || '';

                // 如果有公司ID，获取公司地址
                if (user.company_id && user.company_id[0]) {
                    const companyInfo = await this.orm.read(
                        'res.company',
                        [user.company_id[0]],
                        ['name', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id']
                    );

                    if (companyInfo && companyInfo.length > 0) {
                        const company = companyInfo[0];
                        // 格式化公司地址
                        let address = [];
                        if (company.street) address.push(company.street);
                        if (company.street2) address.push(company.street2);
                        if (company.city) address.push(company.city);
                        if (company.state_id && company.state_id[1]) address.push(company.state_id[1]);
                        if (company.zip) address.push(company.zip);
                        if (company.country_id && company.country_id[1]) address.push(company.country_id[1]);

                        this.state.userCompanyAddress = address.join(', ');
                    }
                }
            }
        } catch (error) {
            console.error("获取用户信息失败:", error);
        }
    }

   // Modify the searchQuotations method to filter by the selected partner
    async searchQuotations(term) {
        if (!term) {
            this.state.saleOrderSearchResults = [];
            return;
        }
    
        this.state.isSearchingSaleOrder = true;
        try {
            // Create base domain
            let domain = [['state', '=', 'draft']]; // Only search for quotations (draft state)
            
            // Add search term filter
            domain.push('|', ['name', 'ilike', term], ['partner_id.name', 'ilike', term]);
            
            // If a partner is selected, add partner filter
            if (this.state.selectedPartner && this.state.selectedPartner.id) {
                domain.push(['partner_id', '=', this.state.selectedPartner.id]);
            }
            
            // Use orm service to search for quotations with the constructed domain
            const quotations = await this.orm.searchRead(
                'sale.order',
                domain,
                ['id', 'name', 'partner_id', 'date_order', 'order_line'],
                {limit: 10}
            );
            this.state.saleOrderSearchResults = quotations;
        } catch (error) {
            console.error("搜索报价单失败:", error);
        } finally {
            this.state.isSearchingSaleOrder = false;
        }
    }

   // 修改为选择报价单的方法，并填充产品
// 修改为选择报价单的方法，并填充产品
async selectQuotation(quotation) {
    this.state.selectedQuotation = quotation;
    this.state.saleOrderSearchTerm = quotation.name;
    this.state.saleOrderSearchResults = [];
    
    // 提取并设置报价单日期
    if (quotation.date_order) {
        try {
            // 处理Odoo日期时间格式，提取日期部分
            const dateObj = new Date(quotation.date_order);
            if (!isNaN(dateObj.getTime())) {
                // 格式化为YYYY-MM-DD格式，适用于HTML日期输入
                const year = dateObj.getFullYear();
                const month = String(dateObj.getMonth() + 1).padStart(2, '0');
                const day = String(dateObj.getDate()).padStart(2, '0');
                this.state.date = `${year}-${month}-${day}`;
                console.log("设置报价单日期:", this.state.date);
            }
        } catch (error) {
            console.error("解析报价单日期失败:", error);
            // 如果解析失败，不设置日期
        }
    }
    
    // 如果报价单有关联的客户，自动选择该客户
    if (quotation.partner_id && quotation.partner_id[0]) {
        try {
            const partner = await this.orm.read(
                'res.partner',
                [quotation.partner_id[0]],
                ['id', 'name', 'email', 'mobile', 'phone', 'is_company']
            );
    
            if (partner && partner.length > 0) {
                this.selectPartner(partner[0]);
            }
        } catch (error) {
            console.error("获取客户详情失败:", error);
        }
    }
    
    // 清空现有产品列表
    this.state.products = [];
    
    // 如果报价单有订单行，加载产品
    if (quotation.order_line && quotation.order_line.length > 0) {
        try {
            // 获取订单行详细信息，包括颜色和世仓规格字段
            const orderLines = await this.orm.read(
                'sale.order.line',
                quotation.order_line,
                ['product_id', 'name', 'product_uom_qty', 'price_unit', 'price_subtotal', 
                 'display_type', 'product_color_id', 'product_diameter', 'product_height', 
                 'warehouse_weight_id', 'weight_unit_price']
            );
    
            // 获取产品详细信息
            const productIds = orderLines
                .filter(line => line.product_id && line.product_id[0])
                .map(line => line.product_id[0]);
    
            let productMap = {};
            if (productIds.length > 0) {
                const products = await this.orm.read(
                    'product.product',
                    productIds,
                    ['id', 'name', 'categ_id', 'list_price', 'default_code', 'uom_id', 'type']
                );
    
                // 创建产品映射以便快速查找
                products.forEach(product => {
                    productMap[product.id] = product;
                });
            }
            
            // 获取所有warehouse_weight_id的详细信息
            const warehouseWeightIds = orderLines
                .filter(line => line.warehouse_weight_id && line.warehouse_weight_id[0])
                .map(line => line.warehouse_weight_id[0]);
                
            let warehouseWeightMap = {};
            if (warehouseWeightIds.length > 0) {
                const warehouseWeights = await this.orm.read(
                    'warehouse.weight',
                    warehouseWeightIds,
                    ['id', 'name', 'specification', 'diameter', 'height', 'weight']
                );
                
                // 创建型号映射以便快速查找
                warehouseWeights.forEach(model => {
                    warehouseWeightMap[model.id] = model;
                });
            }
    
            // 将订单行转换为产品列表项
            for (const line of orderLines) {
                // 判断是否为备注行或节标题行
                if (line.display_type === 'line_note' || line.display_type === 'line_section' || 
                    (!line.product_id && (line.price_unit === 0 || line.price_unit === null))) {
                    // 处理备注行或节标题行
                    this.state.products.push({
                        product_id: 0,
                        product_name: line.name || "",
                        specs: '',
                        userInputSpec: '',
                        quantity: 0,
                        unit_price: 0,
                        total_price: 0,
                        isCustom: false,
                        isDescription: true, // 标记为描述行
                        display_type: line.display_type || 'line_section',
                        weight_unit_price: line.weight_unit_price || 0,
                        weight: 0,
                        color_id: line.product_color_id ? line.product_color_id[0] : null,
                        color_name: line.product_color_id ? line.product_color_id[1] : '',
                        warehouse_weight_id: line.warehouse_weight_id ? line.warehouse_weight_id[0] : null,
                        model_name: ''
                    });
                    continue;
                }
    
                if (!line.product_id || !line.product_id[0]) {
                    // 处理没有产品ID的普通订单行（可能是自定义产品）
                    this.state.products.push({
                        product_id: 0,
                        product_name: line.name || "自定义产品",
                        specs: '',
                        userInputSpec: '',
                        quantity: line.product_uom_qty || 1,
                        unit_price: line.price_unit || 0,
                        total_price: line.price_subtotal || 0,
                        uom: '个',
                        isCustom: true,
                        isDescription: false,
                        color_id: line.product_color_id ? line.product_color_id[0] : null,
                        color_name: line.product_color_id ? line.product_color_id[1] : '',
                        weight: 0,
                        weight_unit_price: line.weight_unit_price || 0,
                        warehouse_weight_id: line.warehouse_weight_id ? line.warehouse_weight_id[0] : null,
                        product_diameter: line.product_diameter || '',
                        product_height: line.product_height || '',
                        model_name: ''
                    });
                    continue;
                }
    
                // 处理普通产品行
                const productId = line.product_id[0];
                const product = productMap[productId];
    
                if (product) {
                    // 获取产品规格
                    const specs = await this._fetchProductSpecs(productId);
                    
                    // 查找匹配的世仓规格
                    let weight = 0;
                    let selectedSpecId = null;
                    let modelName = '';
                    
                    // 如果订单行中已有世仓规格，优先使用它
                    if (line.warehouse_weight_id && line.warehouse_weight_id[0]) {
                        const warehouseWeightId = line.warehouse_weight_id[0];
                        const modelInfo = warehouseWeightMap[warehouseWeightId];
                        
                        if (modelInfo) {
                            weight = modelInfo.weight || 0;
                            selectedSpecId = modelInfo.id;
                            modelName = modelInfo.name || '';
                            
                            // 找出该型号下的所有规格（相同name的记录）
                            const matchingModels = specs.filter(spec => spec.name === modelName);
                            
                            if (matchingModels.length > 0) {
                                // 将匹配的型号规格保存到产品对象中
                                product.matching_models = matchingModels;
                            }
                        }
                    } else if (specs.length > 0) {
                        // 否则使用第一个规格
                        weight = specs[0].weight || 0;
                        selectedSpecId = specs[0].id;
                        modelName = specs[0].name || '';
                    }
                    
                    // 构建直径和高度的显示值
                    let specDisplayValue = '';
                    if (line.product_diameter && line.product_height) {
                        specDisplayValue = `${line.product_diameter}-${line.product_height}`;
                    } else if (line.product_diameter) {
                        specDisplayValue = `D:${line.product_diameter}`;
                    } else if (line.product_height) {
                        specDisplayValue = `H:${line.product_height}`;
                    }
                    
                    // 找出该型号下的所有规格（相同name的记录）
                    const matchingModels = modelName ? specs.filter(spec => spec.name === modelName) : [];
                    
                    // 检查是否为服务类型产品
                    const isService = product.type === 'service';
                    
                    // 创建产品项
                    this.state.products.push({
                        product_id: product.id,
                        product_name: product.name,  // 使用产品名称
                        specs: product.default_code || '',
                        userInputSpec: specDisplayValue,
                        matchedSpec: specDisplayValue,
                        specFormatError: null,
                        specMatchError: null,
                        quantity: line.product_uom_qty || 1,
                        unit_price: line.price_unit || product.list_price,
                        total_price: line.price_subtotal || 0,
                        uom: product.uom_id && product.uom_id[1] ? product.uom_id[1] : '个',
                        categ_id: product.categ_id,
                        available_specs: specs,
                        matching_models: matchingModels, // 保存匹配的型号规格
                        selected_spec_id: selectedSpecId,
                        warehouse_weight_id: line.warehouse_weight_id ? line.warehouse_weight_id[0] : null,
                        // 如果是服务类型产品，设置默认重量为1，否则使用原有逻辑
                        weight: isService ? 1 : weight,
                        weight_unit_price: line.weight_unit_price || 0,
                        color_id: line.product_color_id ? line.product_color_id[0] : null,
                        color_name: line.product_color_id ? line.product_color_id[1] : '',
                        color_notes: line.product_color_id ? (this.state.colors.find(c => c.id === line.product_color_id[0])?.notes || '') : '',
                        isCustom: false,
                        isDescription: false,
                        product_diameter: line.product_diameter || '',
                        product_height: line.product_height || '',
                        model_name: modelName
                    });
                }
            }
    
            // 计算总金额
            this._calculateTotal();
        } catch (error) {
            console.error("加载报价单产品失败:", error);
        }
    }
}
// 增强的数字提取
extractNumber(str) {
    if (!str) return 0;
    const match = str.match(/\d+(\.\d+)?/);
    return match ? parseFloat(match[0]) : 0;
}

    // 修改 searchPartners 方法，当搜索词为空时清除选中的客户
    async searchPartners(term) {
        // 如果搜索词为空并且有选中的客户，清除客户和相关过滤器
        if (!term && this.state.selectedPartner) {
            this.state.selectedPartner = null;
            this.state.partnerSearchResults = [];
            this.state.selectedContact = null;
            this.state.contactSearchResults = [];
            this.state.selectedAddress = null;
            this.state.addressSearchResults = [];
            this.state.companyAddress = '';
            
            // 清除报价单过滤器但保留搜索词
            const currentSearchTerm = this.state.saleOrderSearchTerm;
            if (currentSearchTerm) {
                // 在下一个事件循环中重新搜索，以确保界面状态更新
                setTimeout(() => this.searchQuotations(currentSearchTerm), 0);
            }
            
            return;
        }
        
        // 原有的搜索逻辑
        if (!term) {
            this.state.partnerSearchResults = [];
            return;
        }
    
        this.state.isSearchingPartner = true;
        try {
            // 使用 orm 服务搜索公司客户
            const partners = await this.orm.searchRead(
                'res.partner',
                [['name', 'ilike', term], ['is_company', '=', true]], // 只搜索公司
                ['id', 'name', 'email', 'phone', 'mobile', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id'],
                {limit: 10}
            );
            this.state.partnerSearchResults = partners;
        } catch (error) {
            console.error("搜索客户失败:", error);
        } finally {
            this.state.isSearchingPartner = false;
        }
    }

    // 添加选择客户的方法
    selectPartner(partner) {
        this.state.selectedPartner = partner;
        this.state.partnerSearchTerm = partner.name;
        this.state.partnername = partner.name; // 使用新的partnername字段存储公司名称
        this.state.partnerSearchResults = [];

        // 保存公司地址作为默认地址
        let formattedParts = [];
        if (partner.street) formattedParts.push(partner.street);
        if (partner.street2) formattedParts.push(partner.street2);
        if (partner.city) formattedParts.push(partner.city);
        if (partner.state_id && partner.state_id[1]) formattedParts.push(partner.state_id[1]);
        if (partner.zip) formattedParts.push(partner.zip);
        if (partner.country_id && partner.country_id[1]) formattedParts.push(partner.country_id[1]);

        this.state.companyAddress = formattedParts.join(', ');

        // 设置默认地址为公司地址
        this.state.selectedAddress = {
            id: null,
            name: partner.name + " (默认地址)",
            street: partner.street || '',
            street2: partner.street2 || '',
            city: partner.city || '',
            state_id: partner.state_id || [0, ''],
            zip: partner.zip || '',
            country_id: partner.country_id || [0, ''],
            formattedAddress: this.state.companyAddress
        };

        // 自动加载该公司的联系人和地址
        this.loadCompanyContacts(partner.id);
        this.loadCompanyAddresses(partner.id);
    }

    // 修改选择联系人的方法，接收联系人ID作为参数
    selectContactById(contactIdStr) {
        if (!contactIdStr) {
            this.state.selectedContact = null;
            return;
        }

        const contactId = parseInt(contactIdStr);
        const contact = this.state.contactSearchResults.find(c => c.id === contactId);

        if (contact) {
            this.state.selectedContact = contact;
        }
    }

    // 添加选择联系人的方法
    selectContact(contact) {
        this.state.selectedContact = contact;
    }

    // 修改加载公司联系人的方法，只加载type=contact的联系人
    async loadCompanyContacts(companyId) {
        this.state.isSearchingContact = true;
        try {
            // 搜索该公司下的所有联系人，类型为contact
            const contacts = await this.orm.searchRead(
                'res.partner',
                [
                    ['parent_id', '=', companyId],
                    ['is_company', '=', false],
                    ['type', '=', 'contact'] // 只加载类型为联系人的记录
                ],
                ['id', 'name', 'email', 'phone', 'mobile', 'function'],
                {limit: 20}
            );
            this.state.contactSearchResults = contacts;
        } catch (error) {
            console.error("加载联系人失败:", error);
        } finally {
            this.state.isSearchingContact = false;
        }
    }

    // 修改搜索联系人的方法，只搜索type=contact的联系人
    async searchContacts(term) {
        if (!this.state.selectedPartner || !term) {
            this.state.contactSearchResults = [];
            return;
        }

        this.state.isSearchingContact = true;
        try {
            // 在选中的公司下搜索匹配的联系人，类型为contact
            const contacts = await this.orm.searchRead(
                'res.partner',
                [
                    ['parent_id', '=', this.state.selectedPartner.id],
                    ['name', 'ilike', term],
                    ['is_company', '=', false],
                    ['type', '=', 'contact'] // 只搜索类型为联系人的记录
                ],
                ['id', 'name', 'email', 'phone', 'mobile', 'function'],
                {limit: 10}
            );
            this.state.contactSearchResults = contacts;
        } catch (error) {
            console.error("搜索联系人失败:", error);
        } finally {
            this.state.isSearchingContact = false;
        }
    }

    // 修改加载公司地址的方法，加载所有非contact类型的子联系人
    async loadCompanyAddresses(companyId) {
        this.state.isSearchingAddress = true;
        try {
            // 搜索该公司的所有地址记录（非contact类型的子联系人）
            const addresses = await this.orm.searchRead(
                'res.partner',
                [
                    ['parent_id', '=', companyId],
                    ['is_company', '=', false],
                    ['type', '!=', 'contact'] // 排除contact类型，包括delivery、invoice等类型
                ],
                ['id', 'name', 'type', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id'],
                {limit: 20}
            );

            // 为每个地址添加格式化的地址字符串
            this.state.addressSearchResults = addresses.map(address => {
                let formattedParts = [];
                if (address.street) formattedParts.push(address.street);
                if (address.street2) formattedParts.push(address.street2);
                if (address.city) formattedParts.push(address.city);
                if (address.state_id && address.state_id[1]) formattedParts.push(address.state_id[1]);
                if (address.zip) formattedParts.push(address.zip);
                if (address.country_id && address.country_id[1]) formattedParts.push(address.country_id[1]);

                address.formattedAddress = formattedParts.join(', ');
                return address;
            });
        } catch (error) {
            console.error("加载地址失败:", error);
        } finally {
            this.state.isSearchingAddress = false;
        }
    }

    // 修改选择地址的方法，如果没有选择地址则使用公司默认地址
    selectAddressById(addressIdStr) {
        if (!addressIdStr) {
            // 如果没有选择地址，使用公司默认地址
            if (this.state.selectedPartner) {
                this.state.selectedAddress = {
                    id: null,
                    name: this.state.selectedPartner.name + " (默认地址)",
                    street: this.state.selectedPartner.street || '',
                    street2: this.state.selectedPartner.street2 || '',
                    city: this.state.selectedPartner.city || '',
                    state_id: this.state.selectedPartner.state_id || [0, ''],
                    zip: this.state.selectedPartner.zip || '',
                    country_id: this.state.selectedPartner.country_id || [0, ''],
                    formattedAddress: this.state.companyAddress || ''
                };
            } else {
                this.state.selectedAddress = null;
            }
            return;
        }

        const addressId = parseInt(addressIdStr);
        const address = this.state.addressSearchResults.find(a => a.id === addressId);

        if (address) {
            this.state.selectedAddress = address;
        }
    }

    async _fetchAvailableProducts() {
        try {
            // 直接从数据库获取产品列表
            const products = await this.orm.searchRead(
                'product.product',
                [['sale_ok', '=', true]],
                ['id', 'name', 'list_price', 'default_code', 'uom_id', 'categ_id', 'type']
            );
            this.state.availableProducts = products;
            console.log("获取到的产品列表:", products);
        } catch (error) {
            console.error("获取产品列表失败:", error);
            this.state.error = error.message || '获取产品列表时发生错误';
        }
    }

    async _fetchCategories() {
        try {
            // 从数据库获取所有产品类别
            const categories = await this.orm.searchRead(
                'product.category',
                [],
                ['id', 'name', 'display_name']
            );
            this.state.categories = categories;
            console.log("获取到的产品类别:", categories);
        } catch (error) {
            console.error("获取产品类别失败:", error);
            this.state.error = error.message || '获取产品类别时发生错误';
        }
    }

    async _fetchQuoteData(recordId) {
        // 这里可以根据 recordId 调用后端接口，获取该记录的所有数据
        try {
            const response = await fetch('/quote_system/get_quote_data', {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({id: recordId}),
            });
            if (response.status === 200) {
                const result = await response.json();
                console.log("获取到的结果:", result);

                // 根据后端返回的数据进行处理
                this.state.recordData = result.result.data;
                this.state.name = result.result.data.name || '';
                this.state.date = result.result.data.date || '';
                this.state.user = result.result.data.username || '';

            } else {
                console.log("失败");
                this.state.error = '获取数据失败';
                this.state.loading = false;
            }
            // 获取可用产品列表
            this.state.loading = false;
        } catch (error) {
            console.error("获取数据出错:", error);
            this.state.error = error.message || '获取数据时发生错误';
            this.state.loading = false;
        }
    }

   onProductChange(event) {
        const productId = parseInt(event.target.value);
        const selectedProduct = this.state.availableProducts.find(p => p.id === productId) || null;
        
        if (selectedProduct) {
            const quantity = this.state.quantity || 1;
            
            // 获取该产品的所有可用型号
            const availableModels = this.state.modelsByProduct[productId] || [];
            
            // 判断是否为服务类型产品
            const isService = selectedProduct.type === 'service';
            
            // 添加产品到列表
            this.state.products.push({
                product_id: selectedProduct.id,
                product_name: selectedProduct.name,
                specs: selectedProduct.default_code || '',
                userInputSpec: '',
                matchedSpec: '',
                specFormatError: null,
                specMatchError: null,
                quantity: quantity,
                weight_unit_price: 0,
                unit_price: 0,
                total_price: 0,
                uom: selectedProduct.uom_id[1] || '个',
                categ_id: selectedProduct.categ_id,
                available_specs: [],
                selected_spec_id: null,
                warehouse_weight_id: null,
                // 如果是服务类型产品，默认重量为1，否则为0
                weight: isService ? 1 : 0,
                color_id: null,
                color_name: '',
                model_name: ''
            });
            
            // 重置选中的产品和数量
            this.state.selectedProduct = null;
            this.state.quantity = 1;
            
            // 重新计算总金额
            this._calculateTotal();
        }
    }

    onQuantityChange(event) {
        this.state.quantity = parseInt(event.target.value) || 1;
    }

    searchProductsByCategory(categoryId) {
        // 更新选中的类别ID
        this.state.selectedCategoryId = categoryId ? parseInt(categoryId) : null;

        if (!categoryId) {
            this.state.productSearchResults = [];
            return;
        }

        this.state.isSearching = true;
        // 找到选中的类别名称并更新 state.name
        const selectedCategory = this.state.categories.find(cat => cat.id === parseInt(categoryId));
        if (selectedCategory) {
            this.state.name = selectedCategory.name; // 更新报价单名称为产品品类名称
        }
        const filteredProducts = this.state.availableProducts.filter(product => {
            // 检查产品的类别是否匹配选定的类别
            if (Array.isArray(product.categ_id)) {
                return product.categ_id[0] === parseInt(categoryId);
            } else {
                return product.categ_id === parseInt(categoryId);
            }
        });

        this.state.productSearchResults = filteredProducts;
        this.state.isSearching = false;
    }

    updateProductSpec(index, specId) {
        if (!specId) return;

        const product = this.state.products[index];
        if (!product || !product.available_specs) return;

        // 找到选中的规格
        const selectedSpec = product.available_specs.find(spec => spec.id === parseInt(specId));
        if (selectedSpec) {
            product.selected_spec_id = selectedSpec.id;
            product.specs = selectedSpec.dimensions || '';
            product.weight = selectedSpec.weight || 0;

            // 更新总价 = 重量 × 单价 × 数量
            product.total_price = product.weight * product.unit_price * product.quantity;

            console.log(`更新产品 ${index} 的规格为 ${selectedSpec.dimensions}，重量为 ${selectedSpec.weight}kg，总价为 ${product.total_price}`);

            // 重新计算总金额
            this._calculateTotal();
        }
    }

    updateProductPrice(index, price) {
        const product = this.state.products[index];
        product.unit_price = parseFloat(price) || 0;
        // 修正：更新总价 = 重量 × 单价 × 数量
        product.total_price = product.weight * product.unit_price * product.quantity;
        this._calculateTotal();
    }

    removeProduct(index) {
        // 创建一个新数组而不是直接修改原数组
        const newProducts = [...this.state.products];
        newProducts.splice(index, 1);
        this.state.products = newProducts;
        this._calculateTotal();
    }

    _calculateTotal() {
        this.state.totalAmount = this.state.products.reduce(
            (sum, product) => sum + (product.total_price || 0),
            0
        );
        
        // 计算总重量 = 所有产品的(重量 × 数量)之和
        this.state.totalWeight = this.state.products.reduce(
            (sum, product) => sum + (product.weight || 0) * (product.quantity || 1),
            0
        );
    }

    formatCurrency(amount) {
        return amount.toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
    }

    addCustomProduct() {
        // 自定义产品的默认值
        const customProduct = {
            product_id: 0, // 使用0表示自定义产品
            product_name: "", // 默认名称，可编辑
            specs: '',
            userInputSpec: '', // 用户输入的规格
            quantity: null,
            unit_price: 0,
            weight_unit_price: null,
            total_price: 0,
            uom: '个',
            isCustom: true, // 标识自定义产品的标志
            isDescription: false, // 明确标记不是描述行
            color_id: null,
            color_name: '',
            weight: 0,
            isService: false, // 默认不是服务类型
            category: '', // 初始化类别字段
            model_name: '' // 初始化型号字段
        };
    
        this.state.products.push(customProduct);
        this._calculateTotal();
    }

    updateCustomProductName(index, name) {
        this.state.products[index].product_name = name;
    }

    updateCustomProductCategory(index, category) {
        this.state.products[index].category = category;
    }

    updateCustomProductModelName(index, modelName) {
        this.state.products[index].model_name = modelName;
    }

    updateCustomProductSpec(index, spec) {
        this.state.products[index].userInputSpec = spec;
    }

    updateCustomProductPrice(index, price) {
        // Redirect to updateWeightUnitPrice instead, since unit price is now calculated
        this.updateWeightUnitPrice(index, price);
    }

    updateProductQuantity(index, quantity) {
        const product = this.state.products[index];
        if (!product) return;
    
        product.quantity = parseInt(quantity) || 1;
    
        // Update total price based on unit price * quantity
        product.total_price = product.unit_price * product.quantity;
    
        // Recalculate total
        this._calculateTotal();
    }

}

QuoteAction.template = "quote_system.quote_static_page";
registry.category("actions").add("quote_action", QuoteAction);

export default QuoteAction;