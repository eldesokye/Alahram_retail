(function () {
    "use strict";
    const { T, h, icon, api, toast, toastError, dialog, emptyState } = window.AIApp;

    let currentSessionId = null;
    let pollHandle = null;
    let agentsCache = null;

    function stopPoll() {
        if (pollHandle) {
            clearTimeout(pollHandle);
            pollHandle = null;
        }
    }

    async function loadAgents() {
        if (!agentsCache) {
            agentsCache = await api("chat.agents");
        }
        return agentsCache;
    }

    function eventNode(event) {
        if (event.kind === "text") {
            const bubble = h("div", { class: "aa-msg-bubble aa-markdown" });
            bubble.innerHTML = window.AIApp.renderMarkdown
                ? window.AIApp.renderMarkdown(event.content || "")
                : String(event.content || "");
            return h("div", { class: "aa-msg aa-msg-assistant" }, bubble);
        }
        if (event.kind === "tool_call") {
            return h("div", { class: "aa-msg aa-msg-tool" },
                h("div", { class: "aa-tool-chip" }, icon("tool", "aa-icon-sm"), event.name || T.tool_call));
        }
        if (event.kind === "user_message") {
            return h("div", { class: "aa-msg aa-msg-user" },
                h("div", { class: "aa-msg-bubble" }, event.content || ""));
        }
        return null;
    }

    function statusBadge(state) {
        const map = { running: "thinking", compacting: "thinking", waiting: "waiting", done: "done", error: "failed" };
        const key = map[state] || "done";
        return h("span", { class: "aa-badge aa-badge-" + key }, T[key] || state);
    }

    async function renderConversation(container, sessionId) {
        const snapshot = await api("chat.snapshot", { session_id: sessionId });
        container.replaceChildren(
            ...snapshot.events.map(eventNode).filter(Boolean),
        );
        container.scrollTop = container.scrollHeight;
        return snapshot;
    }

    function pollIfRunning(container, sessionId, statusEl) {
        stopPoll();
        const tick = async () => {
            if (currentSessionId !== sessionId) {
                return;
            }
            try {
                const snapshot = await renderConversation(container, sessionId);
                statusEl.replaceChildren(statusBadge(snapshot.state));
                if (snapshot.state === "running" || snapshot.state === "compacting") {
                    pollHandle = setTimeout(tick, 1200);
                }
            } catch (err) {
                statusEl.replaceChildren(statusBadge("error"));
            }
        };
        pollHandle = setTimeout(tick, 900);
    }

    async function openNewChatDialog(ctx) {
        const agents = await loadAgents();
        if (!agents.length) {
            toast(T.no_agents_title, true);
            return;
        }
        const select = h("select", { class: "aa-input" },
            ...agents.map((a) => h("option", { value: a.id }, a.name)));
        const textarea = h("textarea", { class: "aa-input aa-textarea", placeholder: T.type_message, rows: "3" });
        const { close } = dialog({
            title: T.new_chat,
            body: h("div", { class: "aa-form" },
                h("label", {}, T.pick_agent), select,
                h("label", {}, T.type_message), textarea),
            actions: h("button", { class: "aa-btn aa-btn-primary", type: "button", onclick: async () => {
                try {
                    const row = await api("chat.create", { agent_id: select.value, message: textarea.value });
                    close();
                    currentSessionId = row.id;
                    ctx.reload();
                } catch (err) {
                    toastError(err);
                }
            } }, T.create),
        });
    }

    function openRenameDialog(ctx, s) {
        const input = h("input", { class: "aa-input", type: "text", value: s.name || "" });
        const { close } = dialog({
            title: T.edit,
            body: h("div", { class: "aa-form" }, h("label", {}, T.name), input),
            actions: h("button", { class: "aa-btn aa-btn-primary", type: "button", onclick: async () => {
                try {
                    await api("chat.rename", { session_id: s.id, name: input.value });
                    close();
                    ctx.reload();
                } catch (err) {
                    toastError(err);
                }
            } }, T.save),
        });
    }

    function deleteSession(ctx, s) {
        if (!window.confirm(T.confirm_delete)) {
            return;
        }
        api("chat.delete", { session_id: s.id }).then(() => {
            if (currentSessionId === s.id) {
                currentSessionId = null;
            }
            ctx.reload();
        }).catch(toastError);
    }

    function sessionRow(ctx, s, active) {
        const menuBtn = h("button", { class: "aa-session-more", type: "button", title: T.edit,
            onclick: (ev) => { ev.stopPropagation(); } },
            icon("more", "aa-icon-sm"));
        const menu = h("div", { class: "aa-session-menu" },
            h("button", { class: "aa-session-menu-item", type: "button",
                onclick: (ev) => { ev.stopPropagation(); openRenameDialog(ctx, s); } },
                icon("edit", "aa-icon-sm"), T.edit),
            h("button", { class: "aa-session-menu-item aa-session-menu-danger", type: "button",
                onclick: (ev) => { ev.stopPropagation(); deleteSession(ctx, s); } },
                icon("trash", "aa-icon-sm"), T.delete));
        const wrap = h("div", { class: "aa-session-wrap" },
            h("button", { class: "aa-session-row" + (active ? " aa-active" : ""), type: "button",
                onclick: () => { currentSessionId = s.id; ctx.reload(); } },
                h("div", { class: "aa-session-agent" }, s.agent_name || "-"),
                h("div", { class: "aa-session-title" }, s.name || s.last_text || T.new_chat),
                h("div", { class: "aa-session-foot" },
                    h("span", { class: "aa-badge aa-badge-sm" }, s.state))),
            menuBtn, menu);
        menuBtn.onclick = (ev) => {
            ev.stopPropagation();
            wrap.classList.toggle("aa-session-menu-open");
        };
        document.addEventListener("click", () => wrap.classList.remove("aa-session-menu-open"));
        return wrap;
    }

    window.AIApp.screens.chat = async function chatScreen(ctx) {
        ctx.setHeader(T.nav_chat, "",
            h("button", { class: "aa-btn aa-btn-primary", type: "button", onclick: () => openNewChatDialog(ctx) },
                icon("plus", "aa-icon-sm"), T.new_chat));

        const sessions = await api("chat.sessions", {});
        if (!currentSessionId && sessions.length) {
            currentSessionId = sessions[0].id;
        }

        const sidebar = h("div", { class: "aa-chat-sidebar" },
            sessions.length
                ? sessions.map((s) => sessionRow(ctx, s, s.id === currentSessionId))
                : h("div", { class: "aa-empty-sidebar" }, T.no_sessions));

        const statusEl = h("div", { class: "aa-chat-status" });
        const conversation = h("div", { class: "aa-chat-conversation" });
        const composerInput = h("textarea", { class: "aa-input aa-textarea aa-composer-input",
            placeholder: T.type_message, rows: "1" });
        const sendBtn = h("button", { class: "aa-btn aa-btn-primary aa-icon-btn", type: "button", title: T.send },
            icon("send", "aa-icon-sm aa-icon-flip"));

        async function send() {
            const text = composerInput.value.trim();
            if (!text || !currentSessionId) {
                return;
            }
            composerInput.value = "";
            composerInput.style.height = "38px";
            try {
                await api("chat.send", { session_id: currentSessionId, message: text });
                await renderConversation(conversation, currentSessionId);
                pollIfRunning(conversation, currentSessionId, statusEl);
            } catch (err) {
                toastError(err);
            }
        }
        sendBtn.onclick = send;
        composerInput.addEventListener("keydown", (ev) => {
            if (ev.key === "Enter" && !ev.shiftKey) {
                ev.preventDefault();
                send();
            }
        });
        composerInput.addEventListener("input", () => {
            composerInput.style.height = "38px";
            composerInput.style.height = Math.min(composerInput.scrollHeight, 140) + "px";
        });

        const main = currentSessionId
            ? h("div", { class: "aa-chat-main" },
                statusEl,
                conversation,
                h("div", { class: "aa-composer" }, composerInput, sendBtn))
            : emptyState({ title: T.no_sessions_title, text: T.no_sessions_text, iconName: "chat" });

        if (currentSessionId) {
            const snapshot = await renderConversation(conversation, currentSessionId);
            statusEl.replaceChildren(statusBadge(snapshot.state));
            pollIfRunning(conversation, currentSessionId, statusEl);
        } else {
            stopPoll();
        }

        return h("div", { class: "aa-chat-layout" }, sidebar, main);
    };
})();
