(function () {
    "use strict";
    const { T, h, icon, api, toast, toastError, dialog, emptyState } = window.AIApp;

    const LOGO_URL = (name) => "/aypatech_ai_agent/static/app/logos/" + name + ".svg";

    function logoBadge(name, label, size) {
        return h("span", { class: "aa-logo-badge" + (size === "sm" ? " aa-logo-badge-sm" : "") },
            h("img", { src: LOGO_URL(name), alt: label || name, loading: "lazy" }));
    }

    function openProviderDialog(ctx, provider) {
        const keyInput = h("input", { class: "aa-input", type: "password", placeholder: provider.has_key ? "••••••••" : T.api_key });
        const urlInput = h("input", { class: "aa-input", type: "text", value: provider.base_url || "", placeholder: T.endpoint_url });
        const statusLine = h("div", { class: "aa-muted" },
            provider.last_tested_at ? (provider.last_test_ok ? T.tested_ok : provider.last_test_message) : "");
        const { close } = dialog({
            title: provider.label,
            body: h("div", { class: "aa-form" },
                h("label", {}, T.api_key), keyInput,
                h("label", {}, T.endpoint_url), urlInput,
                statusLine),
            actions: h("div", { class: "aa-dialog-actions" },
                h("button", { class: "aa-btn aa-btn-ghost", type: "button", onclick: async () => {
                    try {
                        await api("settings.provider_save", { provider_id: provider.id, api_key: keyInput.value, base_url: urlInput.value });
                        const result = await api("settings.provider_test", { provider_id: provider.id });
                        toast(result.message, !result.ok);
                        close();
                        ctx.reload();
                    } catch (err) {
                        toastError(err);
                    }
                } }, T.test_connection),
                h("button", { class: "aa-btn aa-btn-primary", type: "button", onclick: async () => {
                    try {
                        await api("settings.provider_save", { provider_id: provider.id, api_key: keyInput.value, base_url: urlInput.value });
                        toast(T.saved);
                        close();
                        ctx.reload();
                    } catch (err) {
                        toastError(err);
                    }
                } }, T.save)),
        });
    }

    function providerCard(ctx, provider) {
        return h("div", { class: "aa-card aa-provider-card" + (provider.has_key ? " aa-provider-ready" : "") },
            h("div", { class: "aa-provider-head" },
                logoBadge(provider.name, provider.label),
                h("div", {},
                    h("div", { class: "aa-provider-name" }, provider.label),
                    h("div", { class: "aa-muted" }, provider.model_count + " models"))),
            h("div", { class: "aa-provider-model" },
                provider.default_model_name
                    ? h("span", { class: "aa-model-line" }, logoBadge(provider.name, provider.label, "sm"), provider.default_model_name)
                    : "-"),
            h("div", { class: "aa-provider-foot" },
                h("span", { class: "aa-badge " + (provider.has_key ? "aa-badge-done" : "aa-badge-sm") },
                    provider.has_key ? T.api_key : "—"),
                h("button", { class: "aa-btn aa-btn-ghost", type: "button", onclick: () => openProviderDialog(ctx, provider) },
                    icon("key", "aa-icon-sm"), T.edit)));
    }

    window.AIApp.screens.providers = async function providersScreen(ctx) {
        ctx.setHeader(T.nav_providers, "");
        const providers = await api("settings.providers");
        if (!providers.length) {
            return emptyState({ title: T.no_providers_title, text: T.no_providers_text, iconName: "providers" });
        }
        return h("div", { class: "aa-grid" }, ...providers.map((p) => providerCard(ctx, p)));
    };
})();
