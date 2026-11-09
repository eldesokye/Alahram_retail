import { Component, proxy, useProps } from '@odoo/owl';

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { useLayoutEffect } from '@web/owl2/utils';

import { ChatWindow } from '@aypatech_ai_agent/ai/chat/window/chat_window';
import { dockWidth } from '@aypatech_ai_agent/ai/chat/window/chat_window_service';

/** Root container rendering all open chat windows from the chat-window service. */
export class ChatWindowContainer extends Component {
    static template = 'aypatech_ai_agent.ai_ChatWindowContainer';
    static components = { ChatWindow };
    props = useProps({});
    setup() {
        this.cw = useService('aypatech_ai_agent.ai_chat_window');
        this.state = proxy(this.cw.state);
        this.mailStore = useService('mail.store');
        useLayoutEffect(
            () => this.remeasureDiscuss(),
            () => [this.state.windows.length],
        );
    }
    /**
     * Ask Discuss to trim its open row to what still fits beside the dock.
     * It only does so when its own state changes, so a window opening or
     * closing here would otherwise leave windows stranded underneath us.
     */
    remeasureDiscuss() {
        this.mailStore.chatHub.onRecompute();
    }
    /**
     * Measure the corner both docks share, so this one can sit beside Discuss
     * instead of on top of it. Read from Discuss's own layout constants and
     * from what it can actually show — `opened` stays populated while the
     * Discuss app is active and mail renders nothing — so a workspace that
     * never opens a chat keeps the dock flush right.
     * @returns {number} reserved width in pixels
     */
    get discussReservedWidth() {
        const hub = this.mailStore.chatHub;
        if (!hub.canShowOpened.length && !hub.canShowFolded.length) {
            return 0;
        }
        const shown = hub.compact
            ? hub.canShowOpened.filter((window) => window.bypassCompact)
            : hub.canShowOpened;
        const bubbles = hub.BUBBLE_START + hub.BUBBLE + hub.BUBBLE_OUTER * 2;
        return bubbles + shown.length * (hub.WINDOW + hub.WINDOW_INBETWEEN * 2);
    }
    get dockWidth() {
        return dockWidth(this.state.windows.length);
    }
}

registry.category('main_components').add('aypatech_ai_agent.ai_ChatWindowContainer', {
    Component: ChatWindowContainer,
});
