/** @odoo-module **/

import { Component, proxy, onWillStart, t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useChart } from "@web/core/utils/chart_hook";
import { _t } from "@web/core/l10n/translation";

const CHART_PALETTE = [
    "#1d4ed8",
    "#059669",
    "#d97706",
    "#dc2626",
    "#0891b2",
    "#7c3aed",
    "#db2777",
    "#475569",
];

const CHART_ALPHA_BG = [
    "rgba(29, 78, 216, 0.20)",
    "rgba(5, 150, 105, 0.20)",
    "rgba(220, 38, 38, 0.20)",
    "rgba(217, 119, 6, 0.20)",
];

function shortLabel(str, maxLen = 22) {
    if (!str) return "";
    const s = String(str).trim();
    return s.length > maxLen ? `${s.slice(0, maxLen - 1)}…` : s;
}

function fmtNum(val, decimals = 2) {
    const num = Number(val);
    if (!Number.isFinite(num)) return "—";
    return num.toLocaleString("ar-EG", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    });
}

export class ExecutiveChart extends Component {
    static template = "alahram_retail_demo.ExecutiveChart";
    props = useProps({
        config: t.any(),
        height: t.any().optional(),
    });
    chart = useChart(() => this.getSafeConfig());

    getSafeConfig() {
        return (
            this.props.config || {
                type: "bar",
                data: { labels: [], datasets: [] },
                options: { responsive: true, maintainAspectRatio: false },
            }
        );
    }
}

export class AlahramExecutiveDashboard extends Component {
    static template = "alahram_retail_demo.ExecutiveDashboard";
    static components = { ExecutiveChart };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = proxy({
            loading: true,
            activeTab: "overview", // overview | inventory | expenses | alerts
            selectedBranch: "",
            selectedWarehouseId: "",
            periodPreset: "all", // all | oct_2026 | nov_2026 | current_month | last_7_days | last_30_days | custom
            dateFrom: "",
            dateTo: "",
            inventoryChartMetric: "qty", // qty | valuation
            expensesChartType: "bar", // bar | doughnut
            sortColumn: "actual_sales_inc_vat",
            sortDirection: "desc",
            data: null,
        });
        this._chartCache = {};

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.loading = true;
        try {
            const filters = {
                period_preset: this.state.periodPreset || "all",
            };
            if (this.state.selectedBranch) {
                filters.branch_code = this.state.selectedBranch;
            }
            if (this.state.selectedWarehouseId) {
                filters.warehouse_id = this.state.selectedWarehouseId;
            }
            if (this.state.periodPreset === "custom") {
                if (this.state.dateFrom) {
                    filters.date_from = this.state.dateFrom;
                }
                if (this.state.dateTo) {
                    filters.date_to = this.state.dateTo;
                }
            }

            const res = await this.orm.call(
                "alahram.executive.dashboard",
                "get_dashboard_data",
                [],
                { filters }
            );
            this._chartCache = {};
            this.state.data = res;
            if (res && res.filters_metadata) {
                this.state.periodPreset = res.filters_metadata.period_preset || "all";
                this.state.dateFrom = res.filters_metadata.date_from || "";
                this.state.dateTo = res.filters_metadata.date_to || "";
            }
        } catch (err) {
            console.error("Error loading Al Ahram Executive Dashboard:", err);
            this.notification.add(
                _t("حدث خطأ أثناء تحميل بيانات لوحة التحكم: ") + (err.message || err),
                { type: "danger" }
            );
        } finally {
            this.state.loading = false;
        }
    }

    // -------------------------------------------------------------
    // Filter Handlers
    // -------------------------------------------------------------
    async onBranchChange(ev) {
        this.state.selectedBranch = ev.target.value;
        await this.loadDashboardData();
    }

    async onWarehouseChange(ev) {
        this.state.selectedWarehouseId = ev.target.value;
        await this.loadDashboardData();
    }

    async onPresetChange(ev) {
        this.state.periodPreset = ev.target.value || "all";
        if (this.state.periodPreset !== "custom") {
            this.state.dateFrom = "";
            this.state.dateTo = "";
            await this.loadDashboardData();
        }
    }

    async onDateInputChange(field, ev) {
        this.state[field] = ev.target.value || "";
        this.state.periodPreset = "custom";
        await this.loadDashboardData();
    }

    async resetFilters() {
        this.state.selectedBranch = "";
        this.state.selectedWarehouseId = "";
        this.state.periodPreset = "all";
        this.state.dateFrom = "";
        this.state.dateTo = "";
        await this.loadDashboardData();
    }

    async refresh() {
        await this.loadDashboardData();
        this.notification.add(_t("تم تحديث مؤشرات لوحة التحكم التنفيذية بنجاح."), {
            type: "success",
        });
    }

    setActiveTab(tabName) {
        this.state.activeTab = tabName;
    }

    setInventoryChartMetric(metric) {
        if (this.state.inventoryChartMetric !== metric) {
            delete this._chartCache.inventory;
            this.state.inventoryChartMetric = metric;
        }
    }

    setExpensesChartType(type) {
        if (this.state.expensesChartType !== type) {
            delete this._chartCache.expenses;
            this.state.expensesChartType = type;
        }
    }

    // -------------------------------------------------------------
    // Sortable Unified Comparison Table
    // -------------------------------------------------------------
    toggleSort(column) {
        if (this.state.sortColumn === column) {
            this.state.sortDirection = this.state.sortDirection === "desc" ? "asc" : "desc";
        } else {
            this.state.sortColumn = column;
            this.state.sortDirection = column === "name" ? "asc" : "desc";
        }
    }

    getSortIconClass(column) {
        if (this.state.sortColumn !== column) return "oi oi-chevron-down text-muted opacity-25";
        return this.state.sortDirection === "asc"
            ? "oi oi-chevron-up text-primary"
            : "oi oi-chevron-down text-primary";
    }

    getSortedComparisonRows() {
        const rows = (this.state.data && this.state.data.comparison_rows) || [];
        const col = this.state.sortColumn;
        const dir = this.state.sortDirection === "asc" ? 1 : -1;

        return [...rows].sort((a, b) => {
            const va = a[col];
            const vb = b[col];
            const aNull = va === null || va === undefined;
            const bNull = vb === null || vb === undefined;
            if (aNull && bNull) return 0;
            if (aNull) return 1;
            if (bNull) return -1;
            if (typeof va === "string" || typeof vb === "string") {
                return String(va).localeCompare(String(vb), "ar") * dir;
            }
            return (Number(va) - Number(vb)) * dir;
        });
    }

    // -------------------------------------------------------------
    // Chart.js v4.5.0 Configurations (Memoized to prevent redraw on sort)
    // -------------------------------------------------------------
    getSalesTargetChartConfig() {
        if (!("salesTarget" in this._chartCache)) {
            this._chartCache.salesTarget = this._buildSalesTargetChartConfig();
        }
        return this._chartCache.salesTarget;
    }

    _buildSalesTargetChartConfig() {
        const c = this.state.data && this.state.data.charts && this.state.data.charts.sales_vs_target;
        if (!c || !c.labels || !c.labels.length) {
            return null;
        }
        const shortLabels = c.labels.map((l) => shortLabel(l, 20));
        const datasets = [
            {
                label: "المبيعات الفعلية (ج.م)",
                data: c.actual_sales,
                backgroundColor: c.has_any_target ? "rgba(29, 78, 216, 0.86)" : c.labels.map((_, idx) => CHART_PALETTE[idx % CHART_PALETTE.length]),
                borderColor: "#1e40af",
                borderWidth: 1,
                borderRadius: 6,
                barPercentage: 0.72,
            },
        ];

        if (c.has_any_target) {
            datasets.push({
                label: "المستهدف البيعي (ج.م)",
                data: c.sales_targets.map((v) => (v === null ? 0 : v)),
                backgroundColor: "rgba(16, 185, 129, 0.35)",
                borderColor: "#059669",
                borderWidth: 2,
                borderRadius: 6,
                barPercentage: 0.72,
            });
        }

        return {
            type: "bar",
            data: {
                labels: shortLabels,
                datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: {
                        display: true,
                        position: "top",
                        rtl: true,
                        textDirection: "rtl",
                        labels: { font: { family: "Cairo, sans-serif", size: 12, weight: "600" }, boxWidth: 14 },
                    },
                    tooltip: {
                        rtl: true,
                        textDirection: "rtl",
                        callbacks: {
                            title: (items) => (items[0] ? c.labels[items[0].dataIndex] : ""),
                            label: (ctx) => `${ctx.dataset.label}: ${fmtNum(ctx.parsed.y, 2)} ج.م`,
                            afterBody: (items) => {
                                if (!items.length) return [];
                                const i = items[0].dataIndex;
                                const lines = [
                                    `الترتيب: #${i + 1}`,
                                    `خط الأساس (أكتوبر): ${fmtNum(c.baseline_sales[i], 2)} ج.م`,
                                    `العمليات الحية (POS/SO): ${fmtNum(c.live_sales[i], 2)} ج.م`,
                                ];
                                if (c.achievement_pcts[i] !== null) {
                                    lines.push(`نسبة تحقيق المستهدف: ${c.achievement_pcts[i]}%`);
                                } else {
                                    lines.push("المستهدف: غير مهيأ في النظام");
                                }
                                return lines;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        ticks: { font: { size: 11, weight: "600" }, maxRotation: 30, minRotation: 0 },
                        grid: { display: false },
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (val) => {
                                const n = Number(val);
                                if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
                                if (n >= 1000) return `${(n / 1000).toFixed(0)}K`;
                                return n;
                            },
                        },
                    },
                },
            },
        };
    }

    getInventoryChartConfig() {
        if (!("inventory" in this._chartCache)) {
            this._chartCache.inventory = this._buildInventoryChartConfig();
        }
        return this._chartCache.inventory;
    }

    _buildInventoryChartConfig() {
        const inv = this.state.data && this.state.data.charts && this.state.data.charts.warehouse_inventory;
        if (!inv || !inv.has_data) {
            return null;
        }
        const shortLabels = inv.labels.map((l) => shortLabel(l, 20));
        const isValuation = this.state.inventoryChartMetric === "valuation";

        if (isValuation) {
            return {
                type: "bar",
                data: {
                    labels: shortLabels,
                    datasets: [
                        {
                            label: "قيمة المخزون بالتكلفة الفعلية (ج.م)",
                            data: inv.valuation,
                            backgroundColor: "rgba(79, 70, 229, 0.85)",
                            borderColor: "#4338ca",
                            borderWidth: 1,
                            borderRadius: 6,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "top",
                            rtl: true,
                            textDirection: "rtl",
                        },
                        tooltip: {
                            rtl: true,
                            textDirection: "rtl",
                            callbacks: {
                                title: (items) => (items[0] ? inv.labels[items[0].dataIndex] : ""),
                                label: (ctx) => `القيمة بالتكلفة: ${fmtNum(ctx.parsed.y, 2)} ج.م`,
                                afterBody: (items) => {
                                    if (!items.length) return [];
                                    const i = items[0].dataIndex;
                                    return [
                                        `إجمالي فعلي: ${fmtNum(inv.on_hand_qty[i], 0)} قطعة`,
                                        `متاح للبيع: ${fmtNum(inv.available_qty[i], 0)} | محجوز: ${fmtNum(inv.reserved_qty[i], 0)}`,
                                        `عدد الأصناف: ${inv.products_count[i]} صنف`,
                                    ];
                                },
                            },
                        },
                    },
                    scales: {
                        x: { grid: { display: false }, ticks: { font: { size: 11, weight: "600" } } },
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: (v) => (v >= 1000000 ? `${(v / 1000000).toFixed(1)}M` : `${(v / 1000).toFixed(0)}K`),
                            },
                        },
                    },
                },
            };
        }

        return {
            type: "bar",
            data: {
                labels: shortLabels,
                datasets: [
                    {
                        label: "الكمية المتاحة للبيع (Available)",
                        data: inv.available_qty,
                        backgroundColor: "rgba(14, 165, 233, 0.85)",
                        borderColor: "#0284c7",
                        borderWidth: 1,
                        borderRadius: 4,
                        stack: "stock",
                    },
                    {
                        label: "الكمية المحجوزة (Reserved)",
                        data: inv.reserved_qty,
                        backgroundColor: "rgba(245, 158, 11, 0.90)",
                        borderColor: "#d97706",
                        borderWidth: 1,
                        borderRadius: 4,
                        stack: "stock",
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: {
                        position: "top",
                        rtl: true,
                        textDirection: "rtl",
                        labels: { font: { size: 12, weight: "600" }, boxWidth: 14 },
                    },
                    tooltip: {
                        rtl: true,
                        textDirection: "rtl",
                        callbacks: {
                            title: (items) => (items[0] ? inv.labels[items[0].dataIndex] : ""),
                            label: (ctx) => `${ctx.dataset.label}: ${fmtNum(ctx.parsed.y, 0)} قطعة`,
                            afterBody: (items) => {
                                if (!items.length) return [];
                                const i = items[0].dataIndex;
                                return [
                                    `الرصيد الفعلي: ${fmtNum(inv.on_hand_qty[i], 0)} قطعة`,
                                    `تقييم التكلفة: ${fmtNum(inv.valuation[i], 2)} ج.م`,
                                    `عدد الأصناف: ${inv.products_count[i]} صنف`,
                                ];
                            },
                        },
                    },
                },
                scales: {
                    x: { stacked: true, grid: { display: false }, ticks: { font: { size: 11, weight: "600" } } },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        ticks: {
                            callback: (v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v),
                        },
                    },
                },
            },
        };
    }

    getExpensesChartConfig() {
        if (!("expenses" in this._chartCache)) {
            this._chartCache.expenses = this._buildExpensesChartConfig();
        }
        return this._chartCache.expenses;
    }

    _buildExpensesChartConfig() {
        const exp = this.state.data && this.state.data.charts && this.state.data.charts.expenses;
        if (!exp || !exp.has_data) {
            return null;
        }
        const shortLabels = exp.labels.map((l) => shortLabel(l, 24));
        const isDoughnut = this.state.expensesChartType === "doughnut";
        const colors = exp.labels.map((_, i) => CHART_PALETTE[(i + 3) % CHART_PALETTE.length]);

        if (isDoughnut) {
            return {
                type: "doughnut",
                data: {
                    labels: shortLabels,
                    datasets: [
                        {
                            label: "المصروفات التشغيلية (ج.م)",
                            data: exp.values,
                            backgroundColor: colors,
                            borderWidth: 2,
                            borderColor: "#ffffff",
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "58%",
                    plugins: {
                        legend: { position: "right", rtl: true, textDirection: "rtl" },
                        tooltip: {
                            rtl: true,
                            textDirection: "rtl",
                            callbacks: {
                                label: (ctx) => `${exp.labels[ctx.dataIndex]}: ${fmtNum(ctx.parsed, 2)} ج.م`,
                            },
                        },
                    },
                },
            };
        }

        return {
            type: "bar",
            data: {
                labels: shortLabels,
                datasets: [
                    {
                        label: exp.is_allocated_by_branch
                            ? "المصروفات التشغيلية المخصصة للفرع (ج.م)"
                            : "المصروفات التشغيلية المركزية حسب الحساب (ج.م)",
                        data: exp.values,
                        backgroundColor: colors,
                        borderRadius: 6,
                        barPercentage: 0.55,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top", rtl: true, textDirection: "rtl" },
                    tooltip: {
                        rtl: true,
                        textDirection: "rtl",
                        callbacks: {
                            title: (items) => (items[0] ? exp.labels[items[0].dataIndex] : ""),
                            label: (ctx) => `المبلغ المعتمد: ${fmtNum(ctx.parsed.y, 2)} ج.م`,
                        },
                    },
                },
                scales: {
                    x: { grid: { display: false } },
                    y: { beginAtZero: true },
                },
            },
        };
    }

    getPerformanceRadarConfig() {
        if (!("radar" in this._chartCache)) {
            this._chartCache.radar = this._buildPerformanceRadarConfig();
        }
        return this._chartCache.radar;
    }

    _buildPerformanceRadarConfig() {
        const rad = this.state.data && this.state.data.charts && this.state.data.charts.performance_radar;
        if (!rad || !rad.has_data) {
            return null;
        }
        const datasets = rad.datasets.map((ds, i) => ({
            label: shortLabel(ds.label, 22),
            data: ds.data,
            borderColor: CHART_PALETTE[i % CHART_PALETTE.length],
            backgroundColor: CHART_ALPHA_BG[i % CHART_ALPHA_BG.length],
            borderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
        }));

        return {
            type: "radar",
            data: {
                labels: rad.axes,
                datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "top",
                        rtl: true,
                        textDirection: "rtl",
                        labels: { font: { size: 11, weight: "600" }, boxWidth: 12 },
                    },
                    tooltip: {
                        rtl: true,
                        textDirection: "rtl",
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.r}%`,
                        },
                    },
                },
                scales: {
                    r: {
                        min: 0,
                        max: 100,
                        ticks: { stepSize: 25, backdropColor: "transparent" },
                        pointLabels: { font: { size: 11, weight: "600" } },
                    },
                },
            },
        };
    }

    getSalesTrendChartConfig() {
        if (!("salesTrend" in this._chartCache)) {
            this._chartCache.salesTrend = this._buildSalesTrendChartConfig();
        }
        return this._chartCache.salesTrend;
    }

    _buildSalesTrendChartConfig() {
        const tr = this.state.data && this.state.data.charts && this.state.data.charts.sales_trend;
        if (!tr || !tr.has_data) {
            return null;
        }
        return {
            type: "line",
            data: {
                labels: tr.labels,
                datasets: [
                    {
                        label: "إجمالي المبيعات اليومية الحية (POS + أوامر البيع)",
                        data: tr.total_sales,
                        borderColor: "#1d4ed8",
                        backgroundColor: "rgba(29, 78, 216, 0.12)",
                        fill: true,
                        tension: 0.3,
                        borderWidth: 2.5,
                        pointRadius: 4,
                        pointBackgroundColor: "#1d4ed8",
                    },
                    {
                        label: "مبيعات الكاشير POS (ج.م)",
                        data: tr.pos_sales,
                        borderColor: "#059669",
                        backgroundColor: "transparent",
                        borderDash: [4, 4],
                        tension: 0.3,
                        borderWidth: 2,
                        pointRadius: 3,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: { position: "top", rtl: true, textDirection: "rtl" },
                    tooltip: {
                        rtl: true,
                        textDirection: "rtl",
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${fmtNum(ctx.parsed.y, 2)} ج.م`,
                            afterBody: (items) => {
                                if (!items.length) return [];
                                const i = items[0].dataIndex;
                                return [`عدد الطلبات المؤكدة: ${tr.orders_count[i]} طلب`];
                            },
                        },
                    },
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v),
                        },
                    },
                },
            },
        };
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
            name: "تحليل مبيعات وربحية ومستهدف الفرع",
            res_model: "alahram.branch.analytics",
            res_id: branchId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openBranchAnalyticsList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "تقرير أداء ومبيعات ومستهدفات الفروع الموحد",
            res_model: "alahram.branch.analytics",
            views: [[false, "list"], [false, "form"]],
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
            domain.push("|", ["config_id.picking_type_id.warehouse_id.code", "=", "WH-SG"], ["config_id.name", "ilike", "سيدي جابر"]);
        } else if (this.state.selectedBranch) {
            domain.push(["config_id.picking_type_id.warehouse_id.code", "=", this.state.selectedBranch]);
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
            name: "القيود والفواتير المحاسبية (Posted Moves)",
            res_model: "account.move",
            domain: [["move_type", "in", ["in_invoice", "in_refund", "entry"]], ["state", "=", "posted"]],
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
        const domain = [["location_id.usage", "=", "internal"]];
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
        } else if (alert.action_model === "stock.quant") {
            this.openWarehouseStock(this.state.selectedWarehouseId ? Number(this.state.selectedWarehouseId) : false);
        } else if (alert.action_model === "account.move") {
            this.openOperatingExpenses();
        }
    }

    // -------------------------------------------------------------
    // Display & Template Helpers (No bare JS globals inside QWeb)
    // -------------------------------------------------------------
    isWarehouseSelected(whId) {
        return String(this.state.selectedWarehouseId || "") === String(whId || "");
    }

    getTargetProgressWidth() {
        const pct = Number(this.state.data?.overview?.target_achievement?.achievement_pct || 0);
        return Math.max(0, Math.min(100, pct));
    }

    openSelectedWarehouseStock() {
        const whId = this.state.selectedWarehouseId ? Number(this.state.selectedWarehouseId) : false;
        this.openWarehouseStock(whId);
    }

    formatAmount(val) {
        if (val === null || val === undefined) return "غير متاح";
        return fmtNum(val, 2);
    }

    formatCompactAmount(val) {
        if (val === null || val === undefined) return "غير متاح";
        const num = Number(val) || 0;
        return fmtNum(num, 2);
    }

    formatInteger(val) {
        if (val === null || val === undefined) return "—";
        const num = Math.round(Number(val) || 0);
        return num.toLocaleString("ar-EG");
    }
}

registry.category("actions").add("alahram_executive_dashboard", AlahramExecutiveDashboard);
