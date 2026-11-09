import { describe, expect, test } from '@odoo/hoot';

import { Thread } from '@mail/core/common/thread_model';
import '@mail/core/web/thread_model_patch';

import '@aypatech_ai_agent/ai/webclient/notification/session_redirect';

describe.current.tags('aypatech_wooai');

const CHAT_ACTION_7 = {
    type: 'ir.actions.client',
    tag: 'aypatech_ai_agent.ai_chat',
    params: { session_id: 7 },
};

/**
 * Build a bare instance of a patched prototype wired to a recording action service.
 * @param {object} proto prototype carrying the patched methods
 * @param {object} [own] own properties to set on the instance
 * @returns {object} { instance, actions } where actions collects doAction payloads
 */
function withActionService(proto, own = {}) {
    const actions = [];
    const instance = Object.assign(Object.create(proto), own);
    instance.env = {
        services: {
            action: {
                doAction: (action) => {
                    actions.push(action);
                    return Promise.resolve();
                },
            },
        },
    };
    return { instance, actions };
}

// --------------------------------------------
// Thread.openRecordActionRequest
// --------------------------------------------

test('an AI session thread requests the chat action instead of a form view', () => {
    const thread = Object.assign(Object.create(Thread.prototype), {
        id: 7,
        model: 'aypatech_wooai.session',
    });
    expect(thread.openRecordActionRequest).toEqual(CHAT_ACTION_7);
});

test('any other thread keeps requesting its own form view', () => {
    const thread = Object.assign(Object.create(Thread.prototype), {
        id: 3,
        model: 'discuss.channel',
    });
    expect(thread.openRecordActionRequest).toEqual({
        context: { highlight_message_id: undefined },
        type: 'ir.actions.act_window',
        res_id: 3,
        res_model: 'discuss.channel',
        views: [[false, 'form']],
    });
});
