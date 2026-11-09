import { Component, t, useProps } from '@odoo/owl';

import { AttachmentCard } from '@aypatech_ai_agent/ai/core/attachment/attachment_card';

/** Artifacts tab listing the session's attachments as cards. */
export class AttachmentsTab extends Component {
    static template = 'aypatech_ai_agent.ai_AttachmentsTab';
    static components = { AttachmentCard };
    props = useProps({
        items: t.array(),
        session: t.object().optional(),
        onOpenAttachment: t.function().optional(),
    });
    onOpen(attachment) {
        if (this.props.onOpenAttachment) {
            this.props.onOpenAttachment(attachment);
        }
    }
}
