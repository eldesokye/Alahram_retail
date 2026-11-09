(function () {
    "use strict";
    const { T, h, icon, api, toast, toastError, dialog, emptyState, dateTime } = window.AIApp;

    async function openScheduleDialog(ctx, schedule) {
        const agents = await api("chat.agents");
        const nameInput = h("input", { class: "aa-input", type: "text", value: schedule ? schedule.name : "" });
        const agentSelect = h("select", { class: "aa-input" },
            ...agents.map((a) => h("option", { value: a.id,
                selected: schedule && schedule.agent_id === a.id }, a.name)));
        const promptInput = h("textarea", { class: "aa-input aa-textarea", rows: "3" });
        const freqSelect = h("select", { class: "aa-input" },
            ...["daily", "weekly", "monthly"].map((f) => h("option", { value: f,
                selected: schedule && schedule.frequency === f }, f)));
        const { close } = dialog({
            title: schedule ? schedule.name : T.create,
            body: h("div", { class: "aa-form" },
                h("label", {}, T.name), nameInput,
                h("label", {}, T.pick_agent), agentSelect,
                h("label", {}, T.prompt), promptInput,
                h("label", {}, T.frequency), freqSelect),
            actions: h("button", { class: "aa-btn aa-btn-primary", type: "button", onclick: async () => {
                try {
                    await api("reports.schedule_save", {
                        schedule_id: schedule ? schedule.id : null,
                        name: nameInput.value,
                        agent_id: agentSelect.value,
                        prompt: promptInput.value,
                        frequency: freqSelect.value,
                    });
                    close();
                    ctx.reload();
                } catch (err) {
                    toastError(err);
                }
            } }, T.save),
        });
    }

    function scheduleCard(ctx, schedule) {
        return h("div", { class: "aa-card aa-schedule-card" },
            h("div", { class: "aa-schedule-head" },
                icon("reports", "aa-icon-lg"),
                h("div", {},
                    h("div", { class: "aa-schedule-name" }, schedule.name),
                    h("div", { class: "aa-muted" }, schedule.agent_name))),
            h("div", { class: "aa-schedule-meta" },
                h("span", {}, T.frequency + ": " + schedule.frequency),
                h("span", {}, T.next_run + ": " + dateTime(schedule.next_run)),
                schedule.telegram_enabled ? h("span", { class: "aa-badge aa-badge-sm" }, icon("telegram", "aa-icon-sm"), "Telegram") : null),
            h("div", { class: "aa-schedule-foot" },
                h("button", { class: "aa-btn aa-btn-ghost", type: "button", onclick: async () => {
                    try {
                        await api("reports.run_now", { schedule_id: schedule.id });
                        toast(T.run_now);
                        ctx.reload();
                    } catch (err) {
                        toastError(err);
                    }
                } }, T.run_now),
                h("button", { class: "aa-btn aa-btn-ghost", type: "button", onclick: () => openScheduleDialog(ctx, schedule) },
                    icon("edit", "aa-icon-sm"), T.edit),
                h("button", { class: "aa-btn aa-btn-ghost aa-btn-danger", type: "button", onclick: async () => {
                    if (!window.confirm(T.confirm_delete)) {
                        return;
                    }
                    try {
                        await api("reports.schedule_delete", { schedule_id: schedule.id });
                        ctx.reload();
                    } catch (err) {
                        toastError(err);
                    }
                } }, icon("trash", "aa-icon-sm"))));
    }

    window.AIApp.screens.reports = async function reportsScreen(ctx) {
        ctx.setHeader(T.nav_reports, "",
            h("button", { class: "aa-btn aa-btn-primary", type: "button", onclick: () => openScheduleDialog(ctx, null) },
                icon("plus", "aa-icon-sm"), T.create));
        const schedules = await api("reports.schedules");
        if (!schedules.length) {
            return emptyState({ title: T.no_reports_title, text: T.no_reports_text, iconName: "reports" });
        }
        return h("div", { class: "aa-grid" }, ...schedules.map((s) => scheduleCard(ctx, s)));
    };
})();
