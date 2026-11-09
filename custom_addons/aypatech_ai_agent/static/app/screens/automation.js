(function () {
    "use strict";
    const { T, h, icon, api, toast, toastError, dialog, emptyState } = window.AIApp;

    function triggers() {
        return [
            ['on_create', T.automation_on_create],
            ['on_create_or_write', T.automation_on_create_or_write],
            ['on_time', T.automation_on_time],
        ];
    }

    async function openModelPicker(input, datalistEl) {
        const rows = await api("automation.models", { query: input.value });
        datalistEl.replaceChildren(...rows.map((r) => h("option", { value: r.model }, r.name)));
    }

    async function openRuleDialog(ctx, rule) {
        const agents = await api("chat.agents");
        const nameInput = h("input", { class: "aa-input", type: "text", value: rule ? rule.name : "" });
        const modelDatalist = h("datalist", { id: "aa-model-list" });
        const modelInput = h("input", {
            class: "aa-input", type: "text", list: "aa-model-list",
            value: rule ? rule.model : "", placeholder: T.automation_model_placeholder,
        });
        modelInput.addEventListener("input", () => openModelPicker(modelInput, modelDatalist));
        openModelPicker(modelInput, modelDatalist);

        const triggerSelect = h("select", { class: "aa-input" },
            ...triggers().map(([val, label]) => h("option", { value: val, selected: rule && rule.trigger === val }, label)));

        const dateFieldInput = h("input", { class: "aa-input", type: "text", value: rule ? rule.trg_date_field : "",
            placeholder: T.automation_date_field_placeholder });
        const dateRangeInput = h("input", { class: "aa-input", type: "number", value: rule ? rule.trg_date_range : 1 });
        const dateModeSelect = h("select", { class: "aa-input" },
            h("option", { value: "before", selected: rule && rule.trg_date_range_mode === "before" }, T.automation_before),
            h("option", { value: "after", selected: !rule || rule.trg_date_range_mode === "after" }, T.automation_after));
        const dateTypeSelect = h("select", { class: "aa-input" },
            ...["minutes", "hour", "day", "month"].map((v) =>
                h("option", { value: v, selected: rule ? rule.trg_date_range_type === v : v === "day" }, v)));
        const dateGroup = h("div", { class: "aa-form", style: rule && rule.trigger !== "on_time" ? "display:none" : "" },
            h("label", {}, T.automation_date_field), dateFieldInput,
            h("div", { class: "aa-date-range-row" }, dateRangeInput, dateModeSelect, dateTypeSelect));
        triggerSelect.addEventListener("change", () => {
            dateGroup.style.display = triggerSelect.value === "on_time" ? "" : "none";
        });

        const domainInput = h("textarea", { class: "aa-input aa-textarea", rows: "2",
            placeholder: '[["qty_available", "<", 10]]' }, rule ? rule.filter_domain : "");
        const agentSelect = h("select", { class: "aa-input" },
            ...agents.map((a) => h("option", { value: a.id, selected: rule && rule.agent_id === a.id }, a.name)));
        const promptInput = h("textarea", { class: "aa-input aa-textarea", rows: "3" }, rule ? rule.prompt : "");
        const dispatchSelect = h("select", { class: "aa-input" },
            h("option", { value: "single", selected: !rule || rule.dispatch_mode === "single" }, T.automation_single),
            h("option", { value: "per_record", selected: rule && rule.dispatch_mode === "per_record" }, T.automation_per_record));

        const { close } = dialog({
            title: rule ? rule.name : T.create,
            wide: true,
            body: h("div", { class: "aa-form" },
                h("label", {}, T.name), nameInput,
                h("label", {}, T.automation_target_model), modelInput, modelDatalist,
                h("label", {}, T.automation_trigger), triggerSelect,
                dateGroup,
                h("label", {}, T.automation_condition_domain), domainInput,
                h("label", {}, T.pick_agent), agentSelect,
                h("label", {}, T.automation_prompt_template), promptInput,
                h("label", {}, T.automation_dispatch_mode), dispatchSelect),
            actions: h("button", { class: "aa-btn aa-btn-primary", type: "button", onclick: async () => {
                try {
                    await api("automation.rule_save", {
                        rule_id: rule ? rule.id : null,
                        name: nameInput.value,
                        model: modelInput.value,
                        trigger: triggerSelect.value,
                        filter_domain: domainInput.value,
                        trg_date_field: dateFieldInput.value,
                        trg_date_range: dateRangeInput.value,
                        trg_date_range_mode: dateModeSelect.value,
                        trg_date_range_type: dateTypeSelect.value,
                        agent_id: agentSelect.value,
                        prompt: promptInput.value,
                        dispatch_mode: dispatchSelect.value,
                    });
                    close();
                    ctx.reload();
                } catch (err) {
                    toastError(err);
                }
            } }, T.save),
        });
    }

    function ruleRow(ctx, rule) {
        const triggerLabel = dict(triggers())[rule.trigger] || rule.trigger_label;
        const menuBtn = h("button", { class: "aa-session-more", type: "button", title: T.edit },
            icon("more", "aa-icon-sm"));
        const menu = h("div", { class: "aa-session-menu" },
            h("button", { class: "aa-session-menu-item", type: "button",
                onclick: (ev) => { ev.stopPropagation(); openRuleDialog(ctx, rule); } },
                icon("edit", "aa-icon-sm"), T.edit),
            h("button", { class: "aa-session-menu-item", type: "button",
                onclick: async (ev) => {
                    ev.stopPropagation();
                    try {
                        await api("automation.rule_toggle", { rule_id: rule.id });
                        ctx.reload();
                    } catch (err) {
                        toastError(err);
                    }
                } }, icon(rule.active ? "close" : "check", "aa-icon-sm"),
                rule.active ? T.automation_deactivate : T.automation_activate),
            h("button", { class: "aa-session-menu-item aa-session-menu-danger", type: "button",
                onclick: async (ev) => {
                    ev.stopPropagation();
                    if (!window.confirm(T.confirm_delete)) {
                        return;
                    }
                    try {
                        await api("automation.rule_delete", { rule_id: rule.id });
                        ctx.reload();
                    } catch (err) {
                        toastError(err);
                    }
                } }, icon("trash", "aa-icon-sm"), T.delete));
        menuBtn.onclick = (ev) => { ev.stopPropagation(); wrap.classList.toggle("aa-session-menu-open"); };
        document.addEventListener("click", () => wrap.classList.remove("aa-session-menu-open"));
        const wrap = h("div", { class: "aa-session-wrap aa-card aa-automation-row" },
            h("div", { class: "aa-automation-main" },
                h("div", { class: "aa-automation-head" },
                    h("strong", {}, rule.name),
                    h("span", { class: "aa-badge " + (rule.active ? "aa-badge-done" : "aa-badge-sm") },
                        rule.active ? T.active : T.automation_inactive)),
                h("div", { class: "aa-muted" }, rule.model + " · " + triggerLabel + " · " + rule.agent_name),
                rule.filter_domain ? h("code", { class: "aa-automation-domain" }, rule.filter_domain) : null),
            menuBtn, menu);
        return wrap;
    }

    function dict(pairs) {
        const out = {};
        for (const [k, v] of pairs) {
            out[k] = v;
        }
        return out;
    }

    window.AIApp.screens.automation = async function automationScreen(ctx) {
        ctx.setHeader(T.nav_automation, "",
            h("button", { class: "aa-btn aa-btn-primary", type: "button", onclick: () => openRuleDialog(ctx, null) },
                icon("plus", "aa-icon-sm"), T.create));
        const rules = await api("automation.rules");
        if (!rules.length) {
            return emptyState({
                title: T.no_automation_title,
                text: T.no_automation_text,
                iconName: "agents",
            });
        }
        return h("div", { class: "aa-automation-list" }, ...rules.map((r) => ruleRow(ctx, r)));
    };
})();
