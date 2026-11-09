(function () {
    "use strict";
    const { T, h, icon, api, toast, emptyState, BRAND_MARK, screens, state } = window.AIApp;

    const NAV = [
        { section: "section_workspace" },
        { key: "chat", label: "nav_chat", icon: "chat" },
        { key: "reports", label: "nav_reports", icon: "reports" },
        { key: "usage", label: "nav_usage", icon: "usage" },
        { key: "automation", label: "nav_automation", icon: "plug" },
        { section: "section_setup" },
        { key: "agents", label: "nav_agents", icon: "agents" },
        { key: "providers", label: "nav_providers", icon: "providers" },
    ];

    const storage = {
        get(key) {
            try {
                return window.localStorage.getItem("aa." + key);
            } catch {
                return null;
            }
        },
        set(key, value) {
            try {
                window.localStorage.setItem("aa." + key, value);
            } catch {
            }
        },
    };

    function applyTheme(theme) {
        const dark = theme ? theme === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
        document.documentElement.dataset.theme = dark ? "dark" : "light";
    }

    let shell;

    function build() {
        const user = state.boot.user;
        const nav = h("nav", { class: "aa-nav", "aria-label": T.app_name });
        const title = h("h1", {});
        const subtitle = h("div", { class: "aa-topbar-sub" });
        const actions = h("div", { class: "aa-topbar-end" });
        const content = h("main", { class: "aa-content", tabindex: "-1" });
        const themeBtn = h("button", { class: "aa-rail-btn", type: "button", title: T.theme, onclick: toggleTheme });
        const app = h("div", { class: "aa-app" },
            h("aside", { class: "aa-rail" },
                h("div", { class: "aa-brand" },
                    h("span", { class: "aa-brand-mark", html: BRAND_MARK }),
                    h("div", { class: "aa-brand-text" },
                        h("div", { class: "aa-brand-name" }, T.app_name),
                        h("div", { class: "aa-brand-sub" }, "Agents · MCP · Automation"))),
                nav,
                h("div", { class: "aa-rail-foot" },
                    h("img", { src: user.avatar, alt: "" }),
                    h("div", { class: "aa-rail-user", title: user.email }, user.name),
                    themeBtn,
                    h("button", { class: "aa-rail-btn", type: "button", title: T.back_to_odoo,
                        onclick: () => { window.location.href = "/odoo"; } }, icon("back", "aa-icon-sm aa-icon-flip")),
                    h("button", { class: "aa-rail-btn", type: "button", title: T.collapse_menu,
                        onclick: () => {
                            app.classList.toggle("aa-rail-collapsed");
                            storage.set("rail", app.classList.contains("aa-rail-collapsed") ? "collapsed" : "");
                        } }, icon("panel", "aa-icon-sm")))),
            h("div", { class: "aa-main" },
                h("header", { class: "aa-topbar" },
                    h("button", { class: "aa-btn aa-btn-ghost aa-icon-btn aa-menu-btn", type: "button", title: T.app_name,
                        onclick: () => app.classList.toggle("aa-rail-open") }, icon("menu")),
                    h("div", {}, title, subtitle),
                    actions),
                content));
        if (storage.get("rail") === "collapsed") {
            app.classList.add("aa-rail-collapsed");
        }
        document.getElementById("aa-root").replaceChildren(app);
        shell = { app, nav, title, subtitle, actions, content, themeBtn };
        renderThemeButton();
    }

    function toggleTheme() {
        const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
        storage.set("theme", next);
        applyTheme(next);
        renderThemeButton();
        route();
    }

    function renderThemeButton() {
        shell.themeBtn.replaceChildren(icon(document.documentElement.dataset.theme === "dark" ? "sun" : "moon", "aa-icon-sm"));
    }

    function renderNav(active) {
        shell.nav.replaceChildren(...NAV.map((item) => item.section
            ? h("div", { class: "aa-nav-section" }, T[item.section])
            : h("a", { class: "aa-nav-item" + (item.key === active ? " aa-active" : ""), href: "#" + item.key,
                title: T[item.label], "aria-current": item.key === active ? "page" : false,
                onclick: () => shell.app.classList.remove("aa-rail-open") },
            icon(item.icon), h("span", { class: "aa-nav-label" }, T[item.label]))));
    }

    const ctx = {
        setHeader(titleText, sub, ...buttons) {
            shell.title.textContent = titleText;
            shell.subtitle.textContent = sub || "";
            shell.actions.replaceChildren(...buttons.flat().filter(Boolean));
            document.title = titleText + " · " + T.app_name;
        },
        go(key) {
            location.hash = "#" + key;
        },
        reload(quiet) {
            return route(quiet === true);
        },
    };

    function currentKey() {
        const key = location.hash.slice(1).split("/")[0];
        return NAV.some((n) => n.key === key) ? key : "chat";
    }

    let routeToken = 0;
    async function route(quiet) {
        const key = currentKey();
        const token = ++routeToken;
        const keepScroll = quiet === true ? shell.content.scrollTop : 0;
        renderNav(key);
        if (quiet !== true) {
            shell.content.replaceChildren(h("div", { class: "aa-skeleton", style: "height:120px;margin-top:8px" }));
        }
        try {
            const node = await screens[key](ctx);
            if (token === routeToken) {
                shell.content.replaceChildren(node);
                shell.content.scrollTop = keepScroll;
            }
        } catch (err) {
            if (token === routeToken) {
                shell.content.replaceChildren(emptyState({
                    title: T.error, text: err.message, iconName: "alert",
                    action: h("button", { class: "aa-btn aa-btn-primary", type: "button", onclick: route }, T.retry),
                }));
            }
        }
    }

    async function start() {
        applyTheme(storage.get("theme"));
        window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
            if (!storage.get("theme")) {
                applyTheme(null);
                route();
            }
        });
        try {
            state.boot = await api("bootstrap");
        } catch (err) {
            document.getElementById("aa-root").replaceChildren(
                h("div", { class: "aa-boot" }, h("div", { class: "aa-empty", style: "color:#fff" }, T.error, " ", err.message)));
            return;
        }
        build();
        window.addEventListener("hashchange", () => route());
        await route();
    }

    window.AIApp.ctx = ctx;
    window.AIApp.start = start;
    window.AIApp.toastError = (err) => toast(err.message || String(err), true);
})();
