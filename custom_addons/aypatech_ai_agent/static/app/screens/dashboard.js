(function () {
    "use strict";
    const { T, h, money, number, emptyState } = window.AIApp;

    function usageRow(row) {
        return h("tr", {},
            h("td", {}, row.name),
            h("td", { class: "aa-num" }, row.sessions),
            h("td", { class: "aa-num" }, number(row.tokens)),
            h("td", { class: "aa-num" }, money(row.cost)));
    }

    function usageTable(title, rows) {
        return h("div", { class: "aa-card" },
            h("h3", {}, title),
            rows.length
                ? h("table", { class: "aa-table" },
                    h("thead", {}, h("tr", {}, h("th", {}, T.name), h("th", {}, T.sessions), h("th", {}, T.total_tokens), h("th", {}, T.total_cost))),
                    h("tbody", {}, ...rows.map(usageRow)))
                : h("p", { class: "aa-muted" }, T.no_usage_text));
    }

    window.AIApp.screens.usage = async function usageScreen(ctx) {
        ctx.setHeader(T.nav_usage, "");
        const data = await window.AIApp.api("usage.summary");
        if (!data.session_count) {
            return emptyState({ title: T.no_usage_title, text: T.no_usage_text, iconName: "usage" });
        }
        return h("div", {},
            h("div", { class: "aa-kpi-row" },
                h("div", { class: "aa-card aa-kpi" },
                    h("div", { class: "aa-kpi-label" }, T.total_cost),
                    h("div", { class: "aa-kpi-value" }, money(data.total_cost))),
                h("div", { class: "aa-card aa-kpi" },
                    h("div", { class: "aa-kpi-label" }, T.total_tokens),
                    h("div", { class: "aa-kpi-value" }, number(data.total_tokens))),
                h("div", { class: "aa-card aa-kpi" },
                    h("div", { class: "aa-kpi-label" }, T.sessions),
                    h("div", { class: "aa-kpi-value" }, number(data.session_count)))),
            h("div", { class: "aa-grid aa-grid-2" },
                usageTable(T.by_agent, data.by_agent),
                usageTable(T.by_user, data.by_user)));
    };
})();
