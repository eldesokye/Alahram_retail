/** @odoo-module **/

import { Component, proxy, onMounted, onWillUnmount, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useBarcodeReader } from "@point_of_sale/app/hooks/barcode_reader_hook";
import { _t } from "@web/core/l10n/translation";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

export class BranchReservationDialog extends Component {
    static template = "alahram_retail_demo.BranchReservationDialog";
    static components = { Dialog };
    props = useProps();

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.ui = useService("ui");

        const props = this.props || {};
        const currentOrder = this.pos.getOrder ? this.pos.getOrder() : null;
        const initialPartner = currentOrder && currentOrder.getPartner ? currentOrder.getPartner() : null;

        const customerName = props.customerName || (initialPartner ? (initialPartner.name || "") : "");
        const customerPhone = props.customerPhone || (initialPartner ? (initialPartner.phone || initialPartner.mobile || "") : "");
        const partnerId = props.partnerId || (initialPartner ? initialPartner.id : false);

        this.lastSelectedPartnerName = partnerId ? customerName : "";

        this.state = proxy({
            searchQuery: "",
            customerName: customerName,
            customerPhone: customerPhone,
            partnerId: partnerId,
            bridalPackageId: props.bridalPackageId || false,
            bridalPackageName: props.bridalPackageName || "",
            addToCart: props.bridalPackageId ? false : true,
            isSubmitting: false,
            isLoadingStock: false,
            selectedItems: [], // [{ product, qty_requested, allocations: [{ warehouse_id, qty, fulfillment_type }] }]
            stockData: {},     // keyed by product_id
            branches: [],      // list of warehouse metadata
            currentWarehouseId: false,
        });

        this.onBarcodeScanned = this.onBarcodeScanned.bind(this);

        try {
            useBarcodeReader({
                product: (code) => this.onBarcodeScanned(code?.base_code || code?.code || code),
            });
        } catch (e) {
            console.warn("Barcode reader hook not initialized:", e);
        }

        onMounted(async () => {
            const props = this.props || {};
            if (props.initialItems && props.initialItems.length > 0) {
                await this.initFromInitialItems(props.initialItems);
            } else {
                // Pre-populate with items already in POS cart if any
                this.initFromCart();
            }
        });
    }

    closeDialog() {
        if (typeof this.props?.close === "function") {
            this.props.close();
        }
    }

    onCustomerNameInput(value) {
        this.state.customerName = value;
        if (this.state.partnerId && this.lastSelectedPartnerName && value.trim() !== this.lastSelectedPartnerName.trim()) {
            this.state.partnerId = false;
        }
    }

    onCustomerPhoneInput(value) {
        this.state.customerPhone = value;
    }

    clearPartner() {
        this.state.partnerId = false;
        this.lastSelectedPartnerName = "";
    }

    async selectPartner() {
        const dialogService = this.dialog || this.env?.services?.dialog || this.pos?.dialog;
        if (!dialogService) {
            console.error("Dialog service not found on component:", this);
            return;
        }

        const currentOrder = this.pos.getOrder ? this.pos.getOrder() : null;
        let currentPartner = null;
        if (this.state.partnerId) {
            currentPartner = (this.pos.models?.["res.partner"]?.get ? this.pos.models["res.partner"].get(this.state.partnerId) : null) ||
                             (this.pos.models?.["res.partner"]?.records ? this.pos.models["res.partner"].records.find(p => p.id === this.state.partnerId) : null) ||
                             (currentOrder?.getPartner?.()?.id === this.state.partnerId ? currentOrder.getPartner() : null);
        } else if (currentOrder?.getPartner) {
            currentPartner = currentOrder.getPartner();
        }

        try {
            const partner = await makeAwaitable(dialogService, PartnerList, {
                partner: currentPartner || null,
            });

            if (partner) {
                this.state.customerName = partner.name || "";
                this.state.customerPhone = partner.phone || partner.mobile || "";
                this.state.partnerId = partner.id;
                this.lastSelectedPartnerName = partner.name || "";

                // Synchronize with the current POS order
                if (currentOrder && currentOrder.getPartner?.()?.id !== partner.id) {
                    if (typeof currentOrder.setPartner === "function") {
                        currentOrder.setPartner(partner);
                    } else if (typeof currentOrder.set_partner === "function") {
                        currentOrder.set_partner(partner);
                    } else if (typeof this.pos.setPartnerToCurrentOrder === "function") {
                        this.pos.setPartnerToCurrentOrder(partner);
                    }
                }
            }
        } catch (err) {
            console.error("Error in selectPartner dialog:", err);
        }
    }

    async initFromInitialItems(items) {
        try {
            const prodModel = this.pos.models?.["product.product"] || this.pos.models?.["product.template"];
            const productIds = [];
            for (const item of items) {
                const pid = typeof item.product_id === "object" ? item.product_id.id : item.product_id;
                if (pid) productIds.push(pid);
            }

            await this.fetchStockForProducts(productIds);

            for (const item of items) {
                const pid = typeof item.product_id === "object" ? item.product_id.id : item.product_id;
                const product = (prodModel?.get ? prodModel.get(pid) : null) ||
                                (prodModel?.records ? prodModel.records.find(p => p.id === pid) : null) ||
                                { id: pid, display_name: item.product_name || `صنف #${pid}`, lst_price: item.unit_price || 0.0 };

                const qty = Number(item.quantity || item.qty_requested || 1.0);
                const newItem = {
                    product: product,
                    qty_requested: Math.max(1, qty),
                    allocations: [],
                };
                this.state.selectedItems.push(newItem);
                this.autoAllocateItem(newItem);
            }
        } catch (e) {
            console.error("Error initializing from bridal package items:", e);
        }
    }

    initFromCart() {
        try {
            const order = this.pos.getOrder ? this.pos.getOrder() : null;
            if (!order) return;
            const lines = order.lines || (order.getOrderlines ? order.getOrderlines() : []);
            if (lines && lines.length > 0) {
                for (const line of lines) {
                    if (line.product_id) {
                        const qty = typeof line.getQuantity === "function" ? line.getQuantity() : (line.qty || 1);
                        this.addProductToReservation(line.product_id, qty);
                    }
                }
            }
        } catch (e) {
            console.warn("Could not prefill from cart:", e);
        }
    }

    onBarcodeScanned(barcode) {
        if (!barcode) return;
        const model = this.pos.models?.["product.product"] || this.pos.models?.["product.template"];
        const product = (model?.getBy ? model.getBy("barcode", barcode) : null) ||
                        (model?.records ? model.records.find(p => p.barcode === barcode) : null);
        if (product) {
            this.addProductToReservation(product, 1);
            this.notification.add(_t("تمت إضافة الصنف بالباركود: ") + (product.display_name || product.name), { type: "info" });
        } else {
            this.notification.add(_t("لم يتم العثور على صنف بالباركود: ") + barcode, { type: "warning" });
        }
    }

    get availableProducts() {
        try {
            const query = (this.state.searchQuery || "").trim().toLowerCase();
            const model = this.pos.models?.["product.product"] || this.pos.models?.["product.template"];
            const allProds = (model?.getAll ? model.getAll() : (model?.records || []));
            if (!query) {
                return allProds.slice(0, 10);
            }
            return allProds.filter(p => {
                const name = String(p.display_name || p.name || "").toLowerCase();
                const barcode = String(p.barcode || "").toLowerCase();
                const code = String(p.default_code || "").toLowerCase();
                return name.includes(query) || barcode.includes(query) || code.includes(query);
            }).slice(0, 20);
        } catch (e) {
            console.error("Error in availableProducts:", e);
            return [];
        }
    }

    async addProductToReservation(product, initialQty = 1) {
        if (!product || !product.id) return;
        const existing = this.state.selectedItems.find(i => i.product && i.product.id === product.id);
        if (existing) {
            existing.qty_requested += initialQty;
            this.autoAllocateItem(existing);
            return;
        }

        const newItem = {
            product: product,
            qty_requested: Math.max(1, initialQty),
            allocations: [], // [{ warehouse_id, qty, fulfillment_type }]
        };

        this.state.selectedItems.push(newItem);
        await this.fetchStockForProducts([product.id]);
        this.autoAllocateItem(newItem);
    }

    removeProduct(index) {
        if (index >= 0 && index < this.state.selectedItems.length) {
            this.state.selectedItems.splice(index, 1);
        }
    }

    async fetchStockForProducts(productIds) {
        if (!productIds || productIds.length === 0) return;
        this.state.isLoadingStock = true;
        try {
            const configId = this.pos.config ? this.pos.config.id : false;
            const res = await this.orm.call(
                "alahram.branch.reservation",
                "get_branch_stock_availability",
                [productIds, configId]
            );
            if (res && res.success) {
                this.state.currentWarehouseId = res.current_warehouse_id;
                this.state.branches = res.branches || [];
                for (const pid in res.products) {
                    this.state.stockData[pid] = res.products[pid];
                }
            }
        } catch (e) {
            console.error("Error fetching branch stock:", e);
        } finally {
            this.state.isLoadingStock = false;
        }
    }

    getStockInfo(productId) {
        if (!productId) return null;
        return this.state.stockData[productId] || this.state.stockData[String(productId)] || null;
    }

    autoAllocateItem(item) {
        if (!item || !item.product) return;
        const stockInfo = this.getStockInfo(item.product.id);
        if (!stockInfo || !stockInfo.branches) return;

        let needed = item.qty_requested;
        item.allocations = [];

        // Try to fulfill from branches with available stock
        for (const branch of stockInfo.branches) {
            if (needed <= 0) break;
            const free = Math.max(0, branch.qty_free || 0);
            if (free > 0) {
                const allocQty = Math.min(needed, free);
                item.allocations.push({
                    warehouse_id: branch.warehouse_id,
                    warehouse_name: branch.warehouse_name,
                    warehouse_code: branch.warehouse_code,
                    is_current: branch.is_current,
                    qty: allocQty,
                    fulfillment_type: branch.is_current ? "transfer" : "transfer",
                });
                needed -= allocQty;
            }
        }
    }

    updateRequestedQty(item, delta) {
        const newQty = item.qty_requested + delta;
        if (newQty < 1) return;
        item.qty_requested = newQty;
        this.autoAllocateItem(item);
    }

    changeAllocationQty(item, alloc, delta) {
        const newQty = alloc.qty + delta;
        if (newQty < 0) return;
        alloc.qty = newQty;
    }

    onSelectBranch(item, ev) {
        const val = parseInt(ev.target.value, 10);
        if (val) {
            this.addAllocationBranch(item, val);
            ev.target.value = "";
        }
    }

    addAllocationBranch(item, warehouseId) {
        if (!warehouseId || !item) return;
        const exists = item.allocations.find(a => a.warehouse_id === warehouseId);
        if (exists) return;
        const branchMeta = this.state.branches.find(b => b.warehouse_id === warehouseId);
        item.allocations.push({
            warehouse_id: warehouseId,
            warehouse_name: branchMeta ? branchMeta.name : _t("Branch"),
            warehouse_code: branchMeta ? branchMeta.code : "",
            is_current: branchMeta ? branchMeta.is_current : false,
            qty: 1,
            fulfillment_type: "transfer",
        });
    }

    removeAllocation(item, index) {
        if (item && item.allocations && index >= 0 && index < item.allocations.length) {
            item.allocations.splice(index, 1);
        }
    }

    getItemTotalAllocated(item) {
        if (!item || !item.allocations) return 0;
        return item.allocations.reduce((sum, a) => sum + (Number(a.qty) || 0), 0);
    }

    getItemDeficit(item) {
        if (!item) return 0;
        return Math.max(0, item.qty_requested - this.getItemTotalAllocated(item));
    }

    get summaryTotals() {
        let requested = 0;
        let reserved = 0;
        let waiting = 0;
        let amount = 0;
        try {
            for (const item of (this.state.selectedItems || [])) {
                const req = Number(item.qty_requested) || 0;
                requested += req;
                const allocSum = this.getItemTotalAllocated(item);
                reserved += allocSum;
                waiting += Math.max(0, req - allocSum);
                const price = Number(item.product?.lst_price || item.product?.price || item.product?.list_price || 0);
                amount += (req * price);
            }
        } catch (e) {
            console.error("Error computing summaryTotals:", e);
        }
        return { requested, reserved, waiting, amount: Math.round(amount * 100) / 100 };
    }

    generateClientUuid() {
        return 'res-' + Date.now() + '-' + Math.random().toString(36).substring(2, 9);
    }

    async submitReservation() {
        if (this.state.selectedItems.length === 0) {
            this.notification.add(_t("برجاء اختيار صنف واحد على الأقل للحجز."), { type: "danger" });
            return;
        }

        if (!this.state.customerName && !this.state.customerPhone) {
            this.notification.add(_t("برجاء إدخال اسم أو رقم هاتف العميل."), { type: "warning" });
            return;
        }

        this.state.isSubmitting = true;
        const clientUuid = this.generateClientUuid();

        const payload = {
            idempotency_key: clientUuid,
            partner_id: this.state.partnerId || false,
            customer_name: this.state.customerName || "عميل نقدي",
            customer_phone: this.state.customerPhone || "",
            pos_session_id: this.pos.pos_session?.id,
            pos_config_id: this.pos.config?.id,
            bridal_configurator_id: this.state.bridalPackageId || false,
            items: this.state.selectedItems.map(item => ({
                product_id: item.product.id,
                qty_requested: item.qty_requested,
                price_unit: Number(item.product.lst_price || item.product.price || 0.0),
                allocations: item.allocations.map(a => ({
                    source_warehouse_id: a.warehouse_id,
                    qty: a.qty,
                    fulfillment_type: a.fulfillment_type || "transfer",
                }))
            }))
        };

        try {
            const res = await this.orm.call(
                "alahram.branch.reservation",
                "create_from_pos",
                [payload]
            );

            if (res && res.success) {
                const msg = _t("تم إنشاء حجز الفروع بنجاح برقم: ") + res.name + 
                            _t(" (محجوز: ") + res.total_qty_reserved + 
                            (res.total_qty_waiting > 0 ? (_t("، قيد الانتظار: ") + res.total_qty_waiting) : "") + ")";
                
                this.notification.add(msg, { type: "success" });

                // If Add to Cart is checked, add items to current POS order
                if (this.state.addToCart) {
                    let order = this.pos.getOrder ? this.pos.getOrder() : null;
                    if (!order && this.pos.addNewOrder) {
                        order = this.pos.addNewOrder();
                    }
                    if (order) {
                        if (this.state.partnerId && order.getPartner?.()?.id !== this.state.partnerId) {
                            const partner = (this.pos.models?.["res.partner"]?.get ? this.pos.models["res.partner"].get(this.state.partnerId) : null) ||
                                            (this.pos.models?.["res.partner"]?.records ? this.pos.models["res.partner"].records.find(p => p.id === this.state.partnerId) : null);
                            if (partner) {
                                if (typeof order.setPartner === "function") {
                                    order.setPartner(partner);
                                } else if (typeof order.set_partner === "function") {
                                    order.set_partner(partner);
                                }
                            }
                        }
                        for (const item of this.state.selectedItems) {
                            for (const alloc of item.allocations) {
                                if (alloc.qty > 0) {
                                    try {
                                        if (typeof this.pos.addLineToCurrentOrder === "function") {
                                            await this.pos.addLineToCurrentOrder({
                                                product_id: item.product,
                                                product_tmpl_id: item.product.product_tmpl_id || item.product,
                                                qty: alloc.qty,
                                                price_unit: Number(item.product.lst_price || item.product.price || 0.0),
                                            });
                                        }
                                        const lines = order.lines || [];
                                        const lastLine = lines[lines.length - 1];
                                        if (lastLine) {
                                            lastLine.fulfillment_type = alloc.fulfillment_type;
                                        }
                                    } catch (lineErr) {
                                        console.warn("Could not add line to order:", lineErr);
                                    }
                                }
                            }
                        }
                    }
                }

                this.closeDialog();
            } else {
                this.notification.add(_t("فشل تسجيل الحجز: ") + (res.error || ""), { type: "danger" });
            }
        } catch (err) {
            console.error("Reservation Error:", err);
            this.notification.add(_t("حدث خطأ أثناء حفظ الحجز: ") + (err.message || ""), { type: "danger" });
        } finally {
            this.state.isSubmitting = false;
        }
    }
}
