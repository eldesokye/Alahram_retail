import { Component, onWillStart, onWillUnmount, proxy, signal, useProps } from '@odoo/owl';

import { _t } from '@web/core/l10n/translation';
import { registry } from '@web/core/registry';
import { user } from '@web/core/user';
import { useService } from '@web/core/utils/hooks';
import { useHotkey } from '@web/core/hotkeys/hotkey_hook';
import { isMacOS } from '@web/core/browser/feature_detection';
import { debounce } from '@web/core/utils/timing';
import { Dropdown } from '@web/core/dropdown/dropdown';
import { DropdownItem } from '@web/core/dropdown/dropdown_item';

import { useNotificationBadge } from '@aypatech_ai_agent/ai/core/notification_badge';

const SYSTRAY_LIMIT = 8;
const NEW_CHAT_HOTKEY = 'alt+shift+b';
const FULL_CHAT_HOTKEY = 'alt+shift+f';

/** Systray dropdown for launching AI chat windows and recent sessions. */
export class AypaTechAISystray extends Component {
    static template = 'aypatech_ai_agent.ai_Systray';
    static components = { Dropdown, DropdownItem };
    props = useProps({});
    setup() {
        this.orm = useService('orm');
        this.bus = useService('bus_service');
        this.action = useService('action');
        this.chatWindow = useService('aypatech_ai_agent.ai_chat_window');
        this.state = proxy({
            sessions: [],
            loaded: false,
        });
        this.badge = useNotificationBadge();
        this._busHandler = null;
        this._loadSeq = 0;
        this._debouncedLoad = debounce(() => this._load(), 500, {
            leading: true,
            trailing: true,
        });
        this.btnRef = signal.ref();
        useHotkey(NEW_CHAT_HOTKEY, () => this.onNewChat(), {
            global: true,
            bypassEditableProtection: true,
            withOverlay: () => this.btnRef(),
        });
        useHotkey(FULL_CHAT_HOTKEY, () => this.onOpenFullChat(), {
            global: true,
            bypassEditableProtection: true,
        });
        onWillStart(async () => {
            await this._load();
            this._connectBus();
        });
        onWillUnmount(() => {
            this._disconnectBus();
            this._debouncedLoad.cancel();
        });
    }
    async _load() {
        const seq = ++this._loadSeq;
        try {
            const [recent, unread] = await Promise.all([
                this.orm.searchRead(
                    'aypatech_wooai.session',
                    [['user_id', '=', user.userId]],
                    ['id', 'name', 'state'],
                    { limit: SYSTRAY_LIMIT, order: 'write_date DESC' },
                ),
                this.orm.searchRead(
                    'aypatech_wooai.session',
                    [
                        ['user_id', '=', user.userId],
                        ['notification_unread', '=', true],
                    ],
                    ['id', 'name', 'state'],
                    { limit: SYSTRAY_LIMIT, order: 'write_date DESC' },
                ),
            ]);
            if (seq === this._loadSeq) {
                this.state.sessions = this._mergeUnreadFirst(unread, recent);
            }
        } catch {
            if (seq === this._loadSeq) {
                this.state.sessions = [];
            }
        }
        this.state.loaded = true;
    }
    _mergeUnreadFirst(unread, recent) {
        const merged = [...unread];
        const seen = new Set(unread.map((s) => s.id));
        for (const session of recent) {
            if (!seen.has(session.id)) {
                seen.add(session.id);
                merged.push(session);
            }
        }
        return merged;
    }
    _connectBus() {
        this._busHandler = (payload) => this._onBusEvent(payload);
        this.bus.subscribe('aypatech_ai_agent.ai_session_state', this._busHandler);
    }
    _disconnectBus() {
        if (this._busHandler) {
            this.bus.unsubscribe('aypatech_ai_agent.ai_session_state', this._busHandler);
            this._busHandler = null;
        }
    }
    _onBusEvent(payload) {
        if (!payload || !payload.session_id) return;
        if (payload.deleted) {
            this.state.sessions = this.state.sessions.filter(
                (s) => s.id !== payload.session_id,
            );
            return;
        }
        const idx = this.state.sessions.findIndex((s) => s.id === payload.session_id);
        if (idx < 0) {
            this._debouncedLoad();
            return;
        }
        const updated = { ...this.state.sessions[idx] };
        if (payload.state) updated.state = payload.state;
        if (payload.name) updated.name = payload.name;
        this.state.sessions = [
            ...this.state.sessions.slice(0, idx),
            updated,
            ...this.state.sessions.slice(idx + 1),
        ];
    }
    get runningCount() {
        return this.state.sessions.filter(
            (s) => s.state === 'running' || s.state === 'waiting',
        ).length;
    }
    get hasRunning() {
        return this.runningCount > 0;
    }
    get badgeLabel() {
        return this.badge.count > 99 ? '99+' : String(this.badge.count);
    }
    get newChatHotkeyLabel() {
        return isMacOS() ? 'Ctrl+Shift+B' : 'Alt+Shift+B';
    }
    get fullChatHotkeyLabel() {
        return isMacOS() ? 'Ctrl+Shift+F' : 'Alt+Shift+F';
    }
    statusDotClass(state) {
        return (
            {
                new: 'ayp_state_new',
                running: 'ayp_state_running',
                waiting: 'ayp_state_waiting',
                done: 'ayp_state_done',
                error: 'ayp_state_error',
                stopped: 'ayp_state_stopped',
            }[state] || 'ayp_state_new'
        );
    }
    async onNewChat() {
        const name = _t('Chat %s', new Date().toLocaleString());
        const sessionId = await this.orm.create('aypatech_wooai.session', [{ name }]);
        const id = Array.isArray(sessionId) ? sessionId[0] : sessionId;
        this.chatWindow.open(id);
        await this._load();
    }
    onOpenSession(session) {
        this.chatWindow.open(session.id);
    }
    async onOpenFullChat() {
        await this.action.doAction({
            type: 'ir.actions.client',
            tag: 'aypatech_ai_agent.ai_chat',
        });
    }
}

registry
    .category('systray')
    .add('aypatech_ai_agent.ai_Systray', { Component: AypaTechAISystray }, { sequence: 60 });
