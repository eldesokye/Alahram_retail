(function () {
    "use strict";
    const { T, h, icon, api, toast, toastError, dialog, emptyState } = window.AIApp;

    function openAgentDialog(ctx, agent) {
        const nameInput = h("input", { class: "aa-input", type: "text", value: agent ? agent.name : "" });
        const descInput = h("textarea", { class: "aa-input aa-textarea", rows: "2", placeholder: T.description },
            agent ? agent.description : "");
        const { close } = dialog({
            title: agent ? agent.name : T.create,
            body: h("div", { class: "aa-form" },
                h("label", {}, T.name), nameInput,
                h("label", {}, T.description), descInput),
            actions: h("button", { class: "aa-btn aa-btn-primary", type: "button", onclick: async () => {
                try {
                    await api("settings.agent_save", {
                        agent_id: agent ? agent.id : null,
                        name: nameInput.value,
                        description: descInput.value,
                    });
                    close();
                    ctx.reload();
                } catch (err) {
                    toastError(err);
                }
            } }, T.save),
        });
    }

    function agentCard(ctx, agent) {
        return h("div", { class: "aa-card aa-agent-card" },
            h("div", { class: "aa-agent-head" },
                icon("bot", "aa-icon-lg"),
                h("div", {},
                    h("div", { class: "aa-agent-name" }, agent.name),
                    h("div", { class: "aa-agent-model" }, agent.model_name || "-"))),
            h("p", { class: "aa-agent-desc" }, agent.description || ""),
            h("div", { class: "aa-agent-foot" },
                agent.allow_handoff ? h("span", { class: "aa-badge aa-badge-sm" }, "handoff") : null,
                h("button", { class: "aa-btn aa-btn-ghost", type: "button", onclick: () => openAgentDialog(ctx, agent) },
                    icon("edit", "aa-icon-sm"), T.edit),
                h("button", { class: "aa-btn aa-btn-ghost aa-btn-danger", type: "button", onclick: async () => {
                    if (!window.confirm(T.confirm_delete)) {
                        return;
                    }
                    try {
                        await api("settings.agent_delete", { agent_id: agent.id });
                        ctx.reload();
                    } catch (err) {
                        toastError(err);
                    }
                } }, icon("trash", "aa-icon-sm"))));
    }

    window.AIApp.screens.agents = async function agentsScreen(ctx) {
        ctx.setHeader(T.nav_agents, "",
            h("button", { class: "aa-btn aa-btn-primary", type: "button", onclick: () => openAgentDialog(ctx, null) },
                icon("plus", "aa-icon-sm"), T.create));
        const agents = await api("settings.agents");
        if (!agents.length) {
            return emptyState({ title: T.no_agents_title, text: T.no_agents_text, iconName: "agents" });
        }
        return h("div", { class: "aa-grid" }, ...agents.map((a) => agentCard(ctx, a)));
    };
})();
