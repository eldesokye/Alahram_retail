/** @odoo-module **/

import { Component, proxy, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class AlahramExecutiveDashboard extends Component {
    static template = "alahram_retail_demo.ExecutiveDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = proxy({
            loading: true,
            activeTab: "overview", // overview | branches | inventory | expenses | alerts
            selectedBranch: "",
            selectedWarehouseId: "",
            data: null,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.loading = true;
        try {
            const filters = {};
            if (this.state.selectedBranch) {
                filters.branch_code = this.state.selectedBranch;
            }
            if (this.state.selectedWarehouseId) {
                filters.warehouse_id = this.state.selectedWarehouseId;
            }

            const res = await this.orm.call(
                "alahram.executive.dashboard",
                "get_dashboard_data",
                [],
                { filters }
            );
            this.state.data = res;
        } catch (err) {
            console.error("Error loading Al Ahram Executive Dashboard:", err);
            this.notification.add(_t("حدث خطأ أثناء تحميل بيانات لوحة التحكم: ") + (err.message || err), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    async onBranchChange(ev) {
        this.state.selectedBranch = ev.target.value;
        await this.loadDashboardData();
    }

    async onWarehouseChange(ev) {
        this.state.selectedWarehouseId = ev.target.value;
        await this.loadDashboardData();
    }

    async resetFilters() {
        this.state.selectedBranch = "";
        this.state.selectedWarehouseId = "";
        await this.loadDashboardData();
    }

    async refresh() {
        await this.loadDashboardData();
        this.notification.add(_t("تم تحديث بيانات لوحة التحكم التنفيذية بنجاح."), {
            type: "success",
        });
    }

    setActiveTab(tabName) {
        this.state.activeTab = tabName;
    }

    // -------------------------------------------------------------
    // Drill-Down Action Handlers
    // -------------------------------------------------------------
    openBranchSales(branchId) {
        if (!branchId) {
            this.openBranchAnalyticsList();
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "تحليل مبيعات وربحية الفرع",
            res_model: "alahram.branch.analytics",
            res_id: branchId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openBranchAnalyticsList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "تقرير أداء ومبيعات وربحية الفروع الموحد",
            res_model: "alahram.branch.analytics",
            views: [[false, "list"]],
            target: "current",
        });
    }

    openDeadStockReport() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "تقرير تحليل وتدوير المخزون الراكد (Dead Stock)",
            res_model: "product.template",
            domain: [["is_dead_stock", "=", true]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openLivePosOrders() {
        const domain = [["state", "in", ["paid", "done", "invoiced"]]];
        if (this.state.selectedBranch === "WH-SG") {
            domain.push(["config_id.name", "ilike", "سيدي جابر"]);
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "سجل مبيعات صالة العرض ونقاط البيع (Live POS Orders)",
            res_model: "pos.order",
            domain: domain,
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openOperatingExpenses() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "فواتير ومصروفات المشتريات والتشغيل (Posted Vendor Bills)",
            res_model: "account.move",
            domain: [["move_type", "=", "in_invoice"], ["state", "=", "posted"]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openStockRecommendations() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "التوصيات الذكية لنقل وتدوير المخزون",
            res_model: "alahram.stock.recommendation",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openWarehouseStock(whId) {
        const domain = [["location_id.usage", "=", "internal"], ["quantity", ">", 0]];
        if (whId) {
            domain.push(["location_id.warehouse_id", "=", whId]);
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "أرصدة المخزون التفصيلية",
            res_model: "stock.quant",
            domain: domain,
            views: [[false, "list"], [false, "pivot"]],
            target: "current",
        });
    }

    handleAlertAction(alert) {
        if (!alert || !alert.action_model) return;
        
        if (alert.action_model === "alahram.branch.analytics") {
            if (alert.action_res_id) {
                this.openBranchSales(alert.action_res_id);
            } else {
                this.openBranchAnalyticsList();
            }
        } else if (alert.action_model === "product.template") {
            this.openDeadStockReport();
        } else if (alert.action_model === "pos.order") {
            this.openLivePosOrders();
        } else if (alert.action_model === "alahram.stock.recommendation") {
            this.openStockRecommendations();
        }
    }

    // -------------------------------------------------------------
    // Formatters
    // -------------------------------------------------------------
    formatAmount(val) {
        const num = parseFloat(val) || 0.0;
        return num.toLocaleString("ar-EG", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    formatInteger(val) {
        const num = parseInt(val, 10) || 0;
        return num.toLocaleString("ar-EG");
    }
}

registry.category("actions").add("alahram_executive_dashboard", AlahramExecutiveDashboard);

