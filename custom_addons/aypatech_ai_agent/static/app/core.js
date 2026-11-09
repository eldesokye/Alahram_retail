(function () {
    "use strict";

    const CONFIG = JSON.parse(document.getElementById("aa-config").textContent);
    const T = CONFIG.terms;

    const ICONS = {
        chat: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
        agents: "M12 2a3 3 0 0 1 3 3v2h1a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3v-6a3 3 0 0 1 3-3h1V5a3 3 0 0 1 3-3zM9 13h.01M15 13h.01",
        providers: "M4 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2zM4 14a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2zM7 7.5h0M7 14.5h0",
        reports: "M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6M8 13h8M8 17h5",
        usage: "M3 3v18h18M8 17v-6M13 17V7M18 17v-3",
        plus: "M12 5v14M5 12h14",
        send: "M22 2L11 13M22 2l-7 20-4-9-9-4z",
        check: "M5 12l5 5L20 7",
        alert: "M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z",
        close: "M18 6L6 18M6 6l12 12",
        menu: "M3 6h18M3 12h18M3 18h18",
        moon: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z",
        sun: "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
        back: "M19 12H5M12 19l-7-7 7-7",
        panel: "M3 3h18v18H3zM9 3v18",
        clock: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2",
        edit: "M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z",
        trash: "M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6",
        key: "M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4",
        plug: "M9 2v6M15 2v6M8 14c0 4 4 8 4 8s4-4 4-8V9H8z",
        bot: "M12 2a2 2 0 0 1 2 2v1h1a3 3 0 0 1 3 3v7a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V8a3 3 0 0 1 3-3h1V4a2 2 0 0 1 2-2zM8 13h.01M16 13h.01",
        retry: "M1 4v6h6M3.5 15a9 9 0 1 0 2.1-9.4L1 10",
        more: "M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM19 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM5 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z",
        tool: "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94z",
        telegram: "M22 2L2 10l7 2 2 7 3-4 5 4z",
    };

    const PALETTE = ["#6c4fd6", "#22c3ee", "#f26d7d", "#2fb380", "#e0a526", "#8a6fe8",
        "#4aa7d6", "#d6618f", "#52b36a", "#c08a2f"];

    function h(tag, attrs, ...children) {
        const el = document.createElement(tag);
        for (const [key, value] of Object.entries(attrs || {})) {
            if (value === false || value === null || value === undefined) {
                continue;
            }
            if (key.startsWith("on")) {
                el.addEventListener(key.slice(2), value);
            } else if (key === "class") {
                el.className = value;
            } else if (key === "style") {
                el.style.cssText = value;
            } else if (key === "html") {
                el.innerHTML = value;
            } else {
                el.setAttribute(key, value === true ? "" : value);
            }
        }
        for (const child of children.flat(Infinity)) {
            if (child === null || child === undefined || child === false) {
                continue;
            }
            el.append(child instanceof Node ? child : document.createTextNode(String(child)));
        }
        return el;
    }

    function icon(name, cls) {
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("viewBox", "0 0 24 24");
        svg.setAttribute("class", "aa-icon " + (cls || ""));
        svg.setAttribute("aria-hidden", "true");
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", ICONS[name] || "");
        svg.append(path);
        return svg;
    }

    async function api(method, params) {
        const response = await fetch(CONFIG.api + method + "?csrf_token=" + encodeURIComponent(CONFIG.csrf), {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(params || {}),
        });
        if (response.redirected || response.status === 401) {
            window.location.href = "/web/login?redirect=" + encodeURIComponent(location.pathname + location.hash);
            throw new Error("session expired");
        }
        let data;
        try {
            data = await response.json();
        } catch {
            throw new Error(T.error);
        }
        if (data.error) {
            throw new Error(data.error);
        }
        return data.result;
    }

    const locale = (CONFIG.lang || "en_US").replace("_", "-");
    const number = (value, digits = 0) =>
        new Intl.NumberFormat(locale, { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value || 0);
    const money = (value, currency) => {
        const digits = value && Math.abs(value) < 1 ? 4 : 2;
        try {
            return new Intl.NumberFormat(locale, { style: "currency", currency: currency || "USD",
                minimumFractionDigits: digits, maximumFractionDigits: digits })
                .format(value || 0);
        } catch {
            return number(value, digits) + " " + (currency || "");
        }
    };
    const dateTime = (iso) => (iso ? new Date(iso.replace(" ", "T") + "Z").toLocaleString(locale, {
        month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
    }) : T.never);

    function toast(text, isError) {
        document.querySelectorAll(".aa-toast").forEach((el) => el.remove());
        const el = h("div", { class: "aa-toast" + (isError ? " aa-error" : ""), role: "status" },
            icon(isError ? "alert" : "check", "aa-icon-sm"), text);
        document.body.append(el);
        setTimeout(() => el.remove(), isError ? 6000 : 3200);
    }

    function dialog({ title, body, actions, onClose, wide }) {
        const close = () => {
            backdrop.remove();
            document.removeEventListener("keydown", onKey);
            onClose && onClose();
        };
        const onKey = (ev) => ev.key === "Escape" && close();
        const backdrop = h("div", { class: "aa-backdrop", onmousedown: (ev) => ev.target === backdrop && close() },
            h("div", { class: "aa-dialog" + (wide ? " aa-dialog-wide" : ""), role: "dialog", "aria-modal": "true", "aria-label": title },
                h("div", { class: "aa-dialog-head" }, h("h2", {}, title),
                    h("button", { class: "aa-btn aa-btn-ghost aa-icon-btn", type: "button", title: T.close, onclick: close }, icon("close"))),
                h("div", { class: "aa-dialog-body" }, body),
                actions ? h("div", { class: "aa-dialog-foot" }, actions) : null));
        document.addEventListener("keydown", onKey);
        document.body.append(backdrop);
        const first = backdrop.querySelector("input, select, textarea");
        first && first.focus();
        return { close };
    }

    function emptyState({ title, text, action, iconName }) {
        return h("div", { class: "aa-card aa-empty" },
            h("div", { class: "aa-empty-icon" }, icon(iconName || "bot", "aa-icon-lg")),
            h("h2", {}, title),
            h("p", {}, text),
            action || null);
    }

    const BRAND_MARK = '<img src="/aypatech_ai_agent/static/description/icon.png" alt="">';

    window.AIApp = {
        CONFIG, T, ICONS, PALETTE, BRAND_MARK,
        h, icon, api, number, money, dateTime, toast, dialog, emptyState,
        screens: {},
        state: { boot: null },
    };
})();
