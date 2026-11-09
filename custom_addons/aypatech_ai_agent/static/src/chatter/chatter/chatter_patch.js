import { proxy } from '@odoo/owl';

import { patch } from '@web/core/utils/patch';

import { Chatter } from '@mail/chatter/web_portal_project/chatter';

import { WooAISessionBox } from '@aypatech_ai_agent/chatter/chatter/ai_session_box';

/** Register the AI session box as a sub-component of the chatter. */
Object.assign(Chatter.components, { WooAISessionBox });

patch(Chatter.prototype, {
    /**
     * Hold whether the AI sessions are shown, and how many there are.
     *
     * The toggle sits in the topbar and the list in the thread below it, so
     * neither can own the state. The count is filled in by the list once it
     * has fetched, which is what lets the toggle carry a number the way the
     * paperclip carries the attachment count.
     */
    setup() {
        super.setup(...arguments);
        this.wooAiSessions = proxy({ open: false, total: 0 });
    },

    toggleWooAISessions() {
        this.wooAiSessions.open = !this.wooAiSessions.open;
    },
});
