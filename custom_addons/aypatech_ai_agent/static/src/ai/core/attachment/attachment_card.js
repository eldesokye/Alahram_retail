import { Component, t, useProps } from '@odoo/owl';

import { humanSize } from '@web/core/utils/binary';

import { toFileModel } from '@aypatech_ai_agent/ai/core/attachment/attachment';

/** Compact card previewing a single attachment with name, size, and thumbnail. */
export class AttachmentCard extends Component {
    static template = 'aypatech_ai_agent.ai_AttachmentCard';
    props = useProps({
        attachment: t.object(),
        removable: t.boolean().optional(false),
        compact: t.boolean().optional(false),
        onOpen: t.function().optional(),
        onRemove: t.function().optional(),
    });
    get file() {
        return toFileModel(this.props.attachment);
    }
    get humanSize() {
        const size = this.props.attachment.size || this.props.attachment.file_size;
        return size ? humanSize(size) : '';
    }
    onClick() {
        if (this.props.onOpen) {
            this.props.onOpen(this.props.attachment);
        }
    }
    onRemove(event) {
        event.stopPropagation();
        if (this.props.onRemove) {
            this.props.onRemove(this.props.attachment);
        }
    }
}
