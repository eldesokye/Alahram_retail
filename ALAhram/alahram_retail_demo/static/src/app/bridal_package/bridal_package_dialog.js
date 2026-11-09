/** @odoo-module **/

import { Component, proxy, onMounted, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { BranchReservationDialog } from "@alahram_retail_demo/app/branch_reservation/branch_reservation_dialog";

export class BridalPackageDialog extends Component {
    static template = "alahram_retail_demo.BridalPackageDialog";
    static components = { Dialog };
    props = useProps();

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");

        const currentOrder = this.pos.getOrder ? this.pos.getOrder() : null;
        const initialPartner = currentOrder && currentOrder.getPartner ? currentOrder.getPartner() : null;

        this.state = proxy({
            activeTab: "lines", // "setup", "lines", "discount"
            customerName: initialPartner ? (initialPartner.name || "") : "",
            customerPhone: initialPartner ? (initialPartner.phone || initialPartner.mobile || "") : "",
            partnerId: initialPartner ? initialPartner.id : false,
            targetBudget: 20000.0,
            packageTier: "gold_20k",
            lowerBound: 18000.0,
            preferredUpperBound: 22500.0,
            absoluteUpperBound: 23000.0,
            budgetMatchStatus: "matches_budget",
            recommendedPackages: [],
            selectedPackageType: "best_match",
            hasSolution: true,
            noSolutionMessage: "",
            noSolutionSuggestions: [],
            sectors: {
                granite: true,
                stainless: true,
                aluminum: false,
                bakeware: true,
                frypans: true,
                appliances: false,
                cutlery: false,
                serveware: false,
                accessories: false,
            },
            deliveryPreference: "all_together",
            fulfillmentStrategy: "consolidated",
            expectedDeliveryDate: "",
            customerNotes: "",
            lines: [],
            catalogProducts: [],
            searchQuery: "",
            totalOriginalPrice: 0.0,
            budgetVariance: 0.0,
            budgetFeedbackMessage: "",
            requestedDiscountPct: 0.0,
            discountState: "no_discount",
            discountAmount: 0.0,
            finalPackagePrice: 0.0,
            managerPin: "",
            isSubmitting: false,
            isLoadingStock: false,
            activeAlternativeLineIndex: null,
            alternativesList: [],
            activeSourcingLineIndex: null,
            packageId: null,
            packageName: "",
            reservationId: null,
            reservationName: "",
            isReserved: false,
            userPermissions: {
                is_branch_manager: false,
                is_ops_manager: false,
                is_owner: false,
                user_name: "",
            },
            currentWarehouseId: false,
            currentWarehouseName: "",
        });

        onMounted(() => {
            this.loadInitialData();
        });
    }

    async loadInitialData() {
        try {
            const configId = this.pos.config?.id || false;
            const res = await this.orm.call(
                "alahram.bridal.configurator",
                "get_pos_bridal_init_data",
                [configId]
            );
            if (res && res.success) {
                this.state.catalogProducts = res.products || [];
                this.state.userPermissions = res.user_permissions || {};
                this.state.currentWarehouseId = res.current_warehouse_id;
                this.state.currentWarehouseName = res.current_warehouse_name;

                // Auto-suggest package lines if empty
                if (this.state.lines.length === 0) {
                    await this.suggestSmartPackage();
                }
            }
        } catch (err) {
            console.error("Error loading initial bridal package data:", err);
            this.notification.add(_t("تعذر تحميل بيانات الباكدج الأولية: ") + (err.message || err), { type: "danger" });
        }
    }

    formatAmount(val, decimals = 2) {
        const num = parseFloat(val);
        if (isNaN(num)) {
            return (0).toFixed(decimals);
        }
        return num.toFixed(decimals);
    }

    onTargetBudgetChange(newBudget) {
        const val = Math.max(0.0, parseFloat(newBudget) || 0.0);
        this.state.targetBudget = val;
        this.recalculateTotals();
    }

    onTierSelect(tierCode, budget) {
        this.state.packageTier = tierCode;
        this.state.targetBudget = parseFloat(budget) || 0.0;
        this.recalculateTotals();
    }

    toggleSector(sectorCode) {
        this.state.sectors[sectorCode] = !this.state.sectors[sectorCode];
    }

    async suggestSmartPackage() {
        this.state.isLoadingStock = true;
        try {
            const configId = this.pos.config?.id || false;
            const targetB = parseFloat(this.state.targetBudget) || 20000.0;
            const res = await this.orm.call(
                "alahram.bridal.configurator",
                "suggest_package_pos",
                [{
                    target_budget: targetB,
                    sectors: this.state.sectors,
                    pos_config_id: configId,
                    partner_id: this.state.partnerId,
                }]
            );
            if (res && res.success) {
                this.state.lowerBound = res.lower_bound != null ? res.lower_bound : Math.max(0, targetB - 2000.0);
                this.state.preferredUpperBound = res.preferred_upper_bound != null ? res.preferred_upper_bound : (targetB + 2500.0);
                this.state.absoluteUpperBound = res.absolute_upper_bound != null ? res.absolute_upper_bound : (targetB + 3000.0);

                if (res.has_solution) {
                    this.state.hasSolution = true;
                    this.state.noSolutionMessage = "";
                    this.state.noSolutionSuggestions = [];
                    this.state.recommendedPackages = res.recommendations || [];
                    const activePkg = res.active_recommendation || (res.recommendations && res.recommendations[0]);
                    if (activePkg) {
                        this.selectRecommendedPackage(activePkg, false);
                    }
                    this.notification.add(_t("تم بنجاح توليد باكدجات مقيدة بميزانية العميل."), { type: "info" });
                } else {
                    this.state.hasSolution = false;
                    this.state.noSolutionMessage = res.message || _t("لا يمكن تشكيل باكدج يغطي جميع القطاعات المطلوبة ضمن ميزانية العميل.");
                    this.state.noSolutionSuggestions = res.suggestions || [];
                    this.state.budgetFeedbackMessage = this.state.noSolutionMessage;
                    this.state.budgetMatchStatus = "no_solution";
                    this.state.recommendedPackages = [];
                    this.notification.add(this.state.noSolutionMessage, { type: "warning" });
                }
            }
        } catch (err) {
            console.error("Error suggesting smart package:", err);
            this.notification.add(_t("خطأ أثناء اقتراح التشكيلة: ") + (err.message || err), { type: "danger" });
        } finally {
            this.state.isLoadingStock = false;
        }
    }

    selectRecommendedPackage(pkg, showNotification = true) {
        if (!pkg) return;
        this.state.selectedPackageType = pkg.type;
        this.state.lines = pkg.lines || [];
        this.state.totalOriginalPrice = pkg.total_price || 0.0;
        this.state.budgetVariance = pkg.variance || 0.0;
        this.state.budgetFeedbackMessage = pkg.reason || "";
        this.state.budgetMatchStatus = pkg.variance_status || "matches_budget";
        this.recalculateTotals();
        if (showNotification) {
            this.notification.add(_t(`تم تفعيل: ${pkg.name} (${this.formatAmount(pkg.total_price, 2)} ج.م)`), { type: "success" });
        }
    }

    recalculateTotals() {
        let total = 0.0;
        for (const line of this.state.lines) {
            line.price_subtotal = (parseFloat(line.quantity) || 1.0) * (parseFloat(line.unit_price) || 0.0);
            total += line.price_subtotal;
        }
        this.state.totalOriginalPrice = total;
        const B = parseFloat(this.state.targetBudget) || 0.0;
        this.state.targetBudget = B;
        const variance = total - B;
        this.state.budgetVariance = variance;

        const L = Math.max(0.0, B - 2000.0);
        const U_pref = B + 2500.0;
        const U_abs = B + 3000.0;
        this.state.lowerBound = L;
        this.state.preferredUpperBound = U_pref;
        this.state.absoluteUpperBound = U_abs;

        if (this.state.lines.length === 0) {
            this.state.budgetMatchStatus = "no_solution";
            this.state.budgetFeedbackMessage = "";
        } else if (total > U_abs || (L > 0 && total < L)) {
            this.state.budgetMatchStatus = "out_of_bounds";
            if (total > U_abs) {
                this.state.budgetFeedbackMessage = `السعر الإجمالي (${this.formatAmount(total, 2)} ج.م) يتجاوز الحد الأقصى المطلق للميزانية (${this.formatAmount(U_abs, 2)} ج.م) بمقدار +${this.formatAmount(total - B, 2)} ج.م!`;
            } else {
                this.state.budgetFeedbackMessage = `السعر الإجمالي (${this.formatAmount(total, 2)} ج.م) أقل من الحد الأدنى المقبول للميزانية (${this.formatAmount(L, 2)} ج.م) بمقدار ${this.formatAmount(L - total, 2)} ج.م (وفارق ${this.formatAmount(B - total, 2)} ج.م عن الميزانية المستهدفة).`;
            }
        } else if (total > U_pref && total <= U_abs) {
            this.state.budgetMatchStatus = "slightly_above_preferred";
            this.state.budgetFeedbackMessage = `السعر الإجمالي (${this.formatAmount(total, 2)} ج.م) أعلى من النطاق المفضل بقليل (+${this.formatAmount(variance, 2)} ج.م)، ولكنه ضمن الحد الأقصى (${this.formatAmount(U_abs, 2)} ج.م).`;
        } else if (Math.abs(variance) < 1.0) {
            this.state.budgetMatchStatus = "matches_budget";
            this.state.budgetFeedbackMessage = `السعر مطابق تماماً للميزانية المستهدفة (${this.formatAmount(total, 2)} ج.م)`;
        } else if (total < B) {
            this.state.budgetMatchStatus = "below_budget";
            this.state.budgetFeedbackMessage = `باكدج اقتصادي مناسب: الإجمالي ${this.formatAmount(total, 2)} ج.م (أقل من الميزانية بـ ${this.formatAmount(Math.abs(variance), 2)} ج.م - توفير متاح للعروسة)`;
        } else {
            this.state.budgetMatchStatus = "within_preferred";
            this.state.budgetFeedbackMessage = `السعر الإجمالي (${this.formatAmount(total, 2)} ج.م) ضمن نطاق التسامح المفضل للميزانية (+${this.formatAmount(variance, 2)} ج.م)`;
        }

        const pct = Math.min(7.0, Math.max(0.0, this.state.requestedDiscountPct || 0.0));
        const discAmt = parseFloat((total * (pct / 100.0)).toFixed(2));
        this.state.discountAmount = discAmt;
        this.state.finalPackagePrice = parseFloat((total - discAmt).toFixed(2));
    }

    onQuantityChange(index, newQty) {
        const qty = Math.max(1.0, parseFloat(newQty) || 1.0);
        if (this.state.lines[index]) {
            this.state.lines[index].quantity = qty;
            this.recalculateTotals();
        }
    }

    removeLine(index) {
        this.state.lines.splice(index, 1);
        this.recalculateTotals();
    }

    addProductToPackage(product) {
        if (!product) return;
        const existing = this.state.lines.find(l => l.product_id === product.id);
        if (existing) {
            existing.quantity += 1.0;
        } else {
            this.state.lines.push({
                product_id: product.id,
                name: product.display_name || product.name,
                default_code: product.default_code || "",
                barcode: product.barcode || "",
                quantity: 1.0,
                unit_price: product.list_price || 0.0,
                price_subtotal: product.list_price || 0.0,
                categ_name: product.categ_name || "",
                is_alternative: false,
                current_branch_free: 0.0,
                remote_free: 0.0,
                total_network_free: 0.0,
                branches: [],
                sourcing_status: "draft",
                fulfillment_type: "transfer",
            });
            // Fetch live stock for this product
            this.refreshLineStock(this.state.lines.length - 1, product.id);
        }
        this.recalculateTotals();
    }

    async refreshLineStock(index, productId) {
        try {
            const configId = this.pos.config?.id || false;
            const res = await this.orm.call(
                "alahram.branch.reservation",
                "get_branch_stock_availability",
                [[productId], configId]
            );
            if (res && res.success && res.products && res.products[productId]) {
                const info = res.products[productId];
                const line = this.state.lines[index];
                if (line) {
                    line.branches = info.branches || [];
                    line.total_network_free = info.total_network_free || 0.0;
                    let localFree = 0.0;
                    let remoteFree = 0.0;
                    for (const b of line.branches) {
                        if (b.is_current) localFree += b.qty_free;
                        else remoteFree += b.qty_free;
                    }
                    line.current_branch_free = localFree;
                    line.remote_free = remoteFree;
                    line.sourcing_status = localFree >= line.quantity ? "local_available" : (remoteFree >= line.quantity ? "remote_available" : "waitlisted");
                }
            }
        } catch (err) {
            console.error("Error refreshing line stock:", err);
        }
    }

    get filteredCatalog() {
        const query = (this.state.searchQuery || "").trim().toLowerCase();
        if (!query) return this.state.catalogProducts.slice(0, 15);
        return this.state.catalogProducts.filter(p => {
            const name = (p.display_name || p.name || "").toLowerCase();
            const code = (p.default_code || "").toLowerCase();
            const barcode = (p.barcode || "").toLowerCase();
            return name.includes(query) || code.includes(query) || barcode.includes(query);
        }).slice(0, 25);
    }

    async openAlternativesModal(index) {
        const line = this.state.lines[index];
        if (!line) return;
        this.state.activeAlternativeLineIndex = index;
        this.state.isLoadingStock = true;
        try {
            const configId = this.pos.config?.id || false;
            const res = await this.orm.call(
                "alahram.bridal.configurator",
                "get_product_alternatives_pos",
                [line.product_id, configId]
            );
            if (res && res.success) {
                this.state.alternativesList = res.alternatives || [];
            }
        } catch (err) {
            console.error("Error fetching alternatives:", err);
            this.notification.add(_t("تعذر جلب البدائل: ") + (err.message || err), { type: "danger" });
        } finally {
            this.state.isLoadingStock = false;
        }
    }

    closeAlternativesModal() {
        this.state.activeAlternativeLineIndex = null;
        this.state.alternativesList = [];
    }

    applyAlternative(altProduct) {
        const idx = this.state.activeAlternativeLineIndex;
        if (idx === null || !this.state.lines[idx]) return;
        const originalLine = this.state.lines[idx];

        // Replace product with approved alternative
        this.state.lines[idx] = {
            product_id: altProduct.id,
            original_product_id: originalLine.product_id,
            name: altProduct.display_name || altProduct.name,
            default_code: altProduct.default_code || "",
            barcode: altProduct.barcode || "",
            quantity: originalLine.quantity,
            unit_price: altProduct.list_price || 0.0,
            price_subtotal: originalLine.quantity * (altProduct.list_price || 0.0),
            categ_name: altProduct.categ_name || "",
            is_alternative: true,
            substitution_reason: `استبدال بموافقة العميل بدلاً من ${originalLine.name}`,
            customer_approved: true,
            current_branch_free: 0.0,
            remote_free: 0.0,
            total_network_free: altProduct.total_network_free || 0.0,
            branches: altProduct.branches || [],
            sourcing_status: "local_available",
            fulfillment_type: "transfer",
        };

        this.refreshLineStock(idx, altProduct.id);
        this.recalculateTotals();
        this.closeAlternativesModal();
        this.notification.add(_t("تم استبدال الصنف بالبديل المعتمد بنجاح."), { type: "success" });
    }

    openSourcingModal(index) {
        this.state.activeSourcingLineIndex = index;
    }

    closeSourcingModal() {
        this.state.activeSourcingLineIndex = null;
    }

    setSourcingBranch(branchId, fulfillmentType) {
        const idx = this.state.activeSourcingLineIndex;
        if (idx === null || !this.state.lines[idx]) return;
        const line = this.state.lines[idx];
        line.source_warehouse_id = branchId;
        line.fulfillment_type = fulfillmentType;
        if (fulfillmentType === "pickup") {
            line.sourcing_status = "source_pickup_ready";
        } else if (fulfillmentType === "direct_delivery") {
            line.sourcing_status = "direct_delivery_ready";
        } else {
            line.sourcing_status = "transfer_requested";
        }
        this.closeSourcingModal();
    }

    onDiscountChange(newPct) {
        const pct = parseFloat(newPct) || 0.0;
        if (pct > 7.0) {
            this.notification.add(_t("الحد الأقصى للخصم في شركة الأهرام هو 7% بتصريح مدير العمليات فقط!"), { type: "danger" });
            this.state.requestedDiscountPct = 7.0;
        } else if (pct < 0.0) {
            this.state.requestedDiscountPct = 0.0;
        } else {
            this.state.requestedDiscountPct = pct;
        }

        if (this.state.requestedDiscountPct === 0.0) {
            this.state.discountState = "no_discount";
        } else if (this.state.requestedDiscountPct <= 5.0) {
            this.state.discountState = "pending_bm";
        } else {
            this.state.discountState = "pending_ops";
        }
        this.recalculateTotals();
    }

    approveDiscountDirectly() {
        const pct = this.state.requestedDiscountPct;
        const perms = this.state.userPermissions;
        if (pct <= 5.0) {
            if (perms.is_branch_manager || perms.is_ops_manager || perms.is_owner) {
                this.state.discountState = "approved";
                this.notification.add(_t("تم اعتماد الخصم رسمياً بواسطة مدير الفرع."), { type: "success" });
                this.recalculateTotals();
            } else {
                this.notification.add(_t("اعتماد الخصم حتى 5% يتطلب صلاحية مدير الفرع!"), { type: "warning" });
            }
        } else if (pct <= 7.0) {
            if (perms.is_ops_manager || perms.is_owner) {
                this.state.discountState = "approved";
                this.notification.add(_t("تم اعتماد الخصم الاستثنائي بواسطة مدير العمليات."), { type: "success" });
                this.recalculateTotals();
            } else {
                this.notification.add(_t("اعتماد الخصم فوق 5% يتطلب حصرياً صلاحية مدير العمليات والتوسع!"), { type: "warning" });
            }
        }
    }

    closeDialog() {
        if (typeof this.props?.close === "function") {
            this.props.close();
        }
    }

    async confirmAndReservePackage() {
        if (!this.state.lines || this.state.lines.length === 0) {
            this.notification.add(_t("يرجى اختيار أصناف الباكدج أولاً!"), { type: "warning" });
            return;
        }

        const total = this.state.totalOriginalPrice;
        const absMax = this.state.absoluteUpperBound;
        if (total > absMax && this.state.discountState !== "approved") {
            this.notification.add(_t("إجمالي الباكدج يتجاوز الحد الأقصى للميزانية! يلزم موافقة مدير العمليات."), { type: "danger" });
            return;
        }

        if (this.state.requestedDiscountPct > 7.0) {
            this.notification.add(_t("الحد الأقصى للخصم المسموح به في شركة الأهرام هو 7%!"), { type: "danger" });
            return;
        }

        if (this.state.requestedDiscountPct > 0 && this.state.discountState !== "approved") {
            this.notification.add(_t("لا يمكن تأكيد الباكدج قبل اعتماد نسبة الخصم المطلوبة من الإدارة!"), { type: "warning" });
            return;
        }

        this.state.isSubmitting = true;
        try {
            const configId = this.pos.config?.id || false;
            const sessionId = this.pos.pos_session?.id || false;
            const idempotencyKey = `BRIDAL-${Date.now()}-${Math.floor(Math.random() * 1000)}`;

            const payload = {
                partner_id: this.state.partnerId,
                customer_name: this.state.customerName,
                customer_phone: this.state.customerPhone,
                target_budget: this.state.targetBudget,
                requested_discount_pct: this.state.requestedDiscountPct,
                pos_config_id: configId,
                pos_session_id: sessionId,
                fulfillment_strategy: this.state.fulfillmentStrategy,
                delivery_preference: this.state.deliveryPreference,
                expected_delivery_date: this.state.expectedDeliveryDate,
                customer_notes: this.state.customerNotes,
                idempotency_key: idempotencyKey,
                manager_approved: (this.state.discountState === "approved"),
                do_reserve: false,
                lines: this.state.lines.map(l => ({
                    product_id: l.product_id,
                    original_product_id: l.original_product_id || false,
                    is_alternative: Boolean(l.is_alternative),
                    substitution_reason: l.substitution_reason || "",
                    customer_approved: Boolean(l.customer_approved),
                    quantity: l.quantity,
                    unit_price: l.unit_price,
                    fulfillment_type: l.fulfillment_type || "transfer",
                    source_warehouse_id: l.source_warehouse_id || this.state.currentWarehouseId,
                    sourcing_status: l.sourcing_status || "draft",
                })),
            };

            const res = await this.orm.call(
                "alahram.bridal.configurator",
                "save_and_reserve_package_pos",
                [payload]
            );

            if (res && res.success) {
                this.state.packageId = res.package_id;
                this.state.packageName = res.name;

                this.closeDialog();

                // Seamlessly open BranchReservationDialog
                this.dialog.add(BranchReservationDialog, {
                    bridalPackageId: res.package_id,
                    bridalPackageName: res.name,
                    customerName: this.state.customerName,
                    customerPhone: this.state.customerPhone,
                    partnerId: this.state.partnerId,
                    initialItems: this.state.lines.map(l => ({
                        product_id: l.product_id,
                        product_name: l.product_name,
                        quantity: l.quantity,
                        unit_price: l.unit_price,
                        fulfillment_type: l.fulfillment_type || "transfer",
                        source_warehouse_id: l.source_warehouse_id,
                    })),
                });

                this.notification.add(_t(`تم حفظ باكدج العروسة ${res.name}. جاري فتح نافذة توزيع وحجز الفروع...`), { type: "info" });
            } else {
                this.notification.add(_t("فشل حفظ الباكدج: ") + (res?.error || ""), { type: "danger" });
            }
        } catch (err) {
            console.error("Error confirming and reserving bridal package:", err);
            this.notification.add(_t("خطأ أثناء تأكيد الحجز: ") + (err.message || err), { type: "danger" });
        } finally {
            this.state.isSubmitting = false;
        }
    }

    async loadIntoPosCart() {
        if (!this.state.lines || this.state.lines.length === 0) {
            this.notification.add(_t("يرجى اختيار أصناف الباكدج أولاً!"), { type: "warning" });
            return;
        }

        if (this.state.requestedDiscountPct > 7.0) {
            this.notification.add(_t("الحد الأقصى للخصم المسموح به في شركة الأهرام هو 7%!"), { type: "danger" });
            return;
        }

        if (this.state.requestedDiscountPct > 0 && this.state.discountState !== "approved") {
            this.notification.add(_t("لا يمكن تحصيل الباكدج في الـ POS قبل اعتماد الخصم المطلوب من الإدارة!"), { type: "warning" });
            return;
        }

        let order = this.pos.getOrder ? this.pos.getOrder() : null;
        if (!order && this.pos.addNewOrder) {
            order = this.pos.addNewOrder();
        }
        if (!order) {
            this.notification.add(_t("لا يوجد طلب نشط في نقطة البيع."), { type: "danger" });
            return;
        }

        try {
            // Set customer on order if partner is known
            if (this.state.partnerId && typeof order.setPartner === "function") {
                const partnerModel = this.pos.models?.["res.partner"];
                const partner = (partnerModel?.get ? partnerModel.get(this.state.partnerId) : null) ||
                                (partnerModel?.records ? partnerModel.records.find(p => p.id === this.state.partnerId) : null);
                if (partner) {
                    order.setPartner(partner);
                }
            }

            const discountToApply = (this.state.discountState === "approved") ? this.state.requestedDiscountPct : 0.0;
            const prodModel = this.pos.models?.["product.product"] || this.pos.models?.["product.template"];

            let addedCount = 0;
            for (const line of this.state.lines) {
                const pid = line.product_id;
                const product = (prodModel?.get ? prodModel.get(pid) : null) ||
                                (prodModel?.records ? prodModel.records.find(p => p.id === pid) : null);

                if (product && typeof this.pos.addLineToCurrentOrder === "function") {
                    await this.pos.addLineToCurrentOrder({
                        product_id: product,
                        product_tmpl_id: product.product_tmpl_id || product,
                        qty: Number(line.quantity || 1.0),
                        price_unit: Number(line.unit_price || product.lst_price || 0.0),
                        discount: discountToApply,
                    }, {}, false);
                    addedCount++;
                }
            }

            this.notification.add(_t(`تم تحويل ${addedCount} أصناف من باكدج العروسة إلى سلة البيع بنجاح للدفع الفوري!`), { type: "success" });

            this.closeDialog();
        } catch (err) {
            console.error("Error loading into POS cart:", err);
            this.notification.add(_t("خطأ أثناء التحميل لسلة البيع: ") + (err.message || err), { type: "danger" });
        }
    }
}

