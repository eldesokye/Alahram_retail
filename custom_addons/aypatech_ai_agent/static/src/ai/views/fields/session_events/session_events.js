import { Component, markup, proxy, useProps } from '@odoo/owl';

import { _t } from '@web/core/l10n/translation';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { standardFieldProps } from '@web/views/fields/standard_field_props';

import { AttachmentCard } from '@aypatech_ai_agent/ai/core/attachment/attachment_card';
import { ToolCard } from '@aypatech_ai_agent/ai/chat/tools/tool_card';
import { ToolGroup, buildTurnItems } from '@aypatech_ai_agent/ai/chat/tools/tool_group';
import { renderMarkdown as renderMarkdownToHtml } from '@aypatech_ai_agent/ai/core/markdown/markdown';
import { buildRenderedTurns } from '@aypatech_ai_agent/ai/chat/session/turns';
import { formatTimestamp } from '@aypatech_ai_agent/ai/chat/utils';
import {
    askArgsText,
    askViewMode,
    toggleAskViewMode,
} from '@aypatech_ai_agent/ai/chat/session/ask_view';

/**
 * Read-only field rendering a session's events as a chat-style transcript.
 *
 * The shared transcript templates ask a session what it allows, so the field
 * hands them one that allows nothing beyond reading.
 */
export class SessionEventsField extends Component {
    static template = 'aypatech_ai_agent.ai_SessionEventsField';
    static components = { AttachmentCard, ToolCard, ToolGroup };
    props = useProps({
        ...standardFieldProps,
    });
    setup() {
        this.notification = useService('notification');
        this.state = proxy({
            expandedTools: {},
            askViews: {},
        });
        this.session = {
            state: { pendingAsk: null, readonly: true },
            canWrite: () => false,
            canRegenerate: () => false,
            copyText: (text) => this.copyText(text),
        };
    }
    get turns() {
        const value = this.props.record.data[this.props.name];
        if (!Array.isArray(value) || !value.length) {
            return [];
        }
        return buildRenderedTurns(value);
    }
    turnItems(turn) {
        return buildTurnItems(turn.blocks, (block) =>
            this.isToolHiddenForAsk(block, turn),
        );
    }
    get isCompact() {
        return true;
    }
    get hideSources() {
        return true;
    }
    renderMarkdown(source) {
        return markup(renderMarkdownToHtml(source));
    }
    renderUserText(text) {
        return text == null ? '' : String(text);
    }
    renderAssistantMarkdown(text) {
        return this.renderMarkdown(text);
    }
    isToolExpanded(callId) {
        return !!this.state.expandedTools[callId];
    }
    isToolHiddenForAsk(block, turn) {
        if (block.result !== null && block.result !== undefined) {
            return false;
        }
        return turn.blocks.some((b) => b.type === 'ask' && b.callId === block.callId);
    }
    isToolStreaming() {
        return false;
    }
    toggleToolBlock(callId) {
        this.state.expandedTools = {
            ...this.state.expandedTools,
            [callId]: !this.state.expandedTools[callId],
        };
    }
    askViewMode(block) {
        return askViewMode(block, this.state.askViews);
    }
    toggleAskView(callId) {
        if (!callId) {
            return;
        }
        const block = this.turns
            .flatMap((turn) => turn.blocks || [])
            .find((b) => b.callId === callId);
        this.state.askViews[callId] = toggleAskViewMode(block, this.state.askViews);
    }
    askArgsText(block) {
        return askArgsText(block);
    }
    formatTimestamp(at) {
        return formatTimestamp(at);
    }
    copyText(text) {
        if (!text || !navigator.clipboard) {
            return;
        }
        navigator.clipboard.writeText(String(text)).then(
            () => this.notification.add(_t('Copied to clipboard'), { type: 'success' }),
            () => this.notification.add(_t('Copy failed'), { type: 'danger' }),
        );
    }
    onOpenAttachment() {}
}

export const sessionEventsField = {
    component: SessionEventsField,
    displayName: _t('AI Session Events'),
    supportedTypes: ['json'],
};

registry.category('fields').add('wooai_ai_session_events', sessionEventsField);
