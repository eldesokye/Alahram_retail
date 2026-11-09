import { patch } from '@web/core/utils/patch';

import { Thread } from '@mail/core/common/thread_model';

export const AI_SESSION_MODEL = 'aypatech_wooai.session';

/**
 * Return the client action descriptor that opens the AI chat for a session.
 *
 * @param {number} sessionId Database id of the ``aypatech_wooai.session`` record.
 * @returns {object} An ``ir.actions.client`` descriptor for ``aypatech_ai_agent.ai_chat``.
 */
export function aiSessionChatAction(sessionId) {
    return {
        type: 'ir.actions.client',
        tag: 'aypatech_ai_agent.ai_chat',
        params: { session_id: sessionId },
    };
}

// Opening a thread from the inbox, a notification or a link goes through this
// request, and the inbox marks the message as done once it resolves.
patch(Thread.prototype, {
    get openRecordActionRequest() {
        if (this.model === AI_SESSION_MODEL) {
            return aiSessionChatAction(this.id);
        }
        return super.openRecordActionRequest;
    },
});
