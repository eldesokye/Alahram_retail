import { Component, t, useProps } from '@odoo/owl';

import { _t } from '@web/core/l10n/translation';
import { useService } from '@web/core/utils/hooks';

import { AIShareDialog } from '@aypatech_ai_agent/ai/chat/share/share_dialog';

/**
 * Who a chat is shared with, stated above the composer.
 *
 * A sentence and some faces, nothing more: the picker lives in a dialog, so
 * opening it never changes the height of anything around the transcript.
 */
export class AIChatShareUsers extends Component {
    static template = 'aypatech_ai_agent.ai_ChatShareUsers';
    props = useProps({
        sessionId: t.number(),
        readonly: t.boolean().optional(),
        shareIds: t.array().optional(),
        onChanged: t.function().optional(),
    });

    setup() {
        this.dialog = useService('dialog');
    }

    get canShare() {
        return !this.props.readonly;
    }

    get shareIds() {
        return this.props.shareIds || [];
    }

    get summary() {
        const count = this.shareIds.length;
        if (!count) {
            return this.canShare ? _t('Only you can read this chat') : '';
        }
        return count === 1
            ? _t('1 person can read this chat')
            : _t('%s people can read this chat', count);
    }

    avatar(userId) {
        return `/web/image/res.users/${userId}/avatar_128`;
    }

    openDialog() {
        this.dialog.add(AIShareDialog, {
            sessionId: this.props.sessionId,
            onChanged: () => this.props.onChanged?.(),
        });
    }
}
