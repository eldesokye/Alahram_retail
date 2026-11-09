import { Component, proxy, signal, t, useProps } from '@odoo/owl';

import { _t } from '@web/core/l10n/translation';
import { useLayoutEffect } from '@web/owl2/utils';

import { AttachmentCard } from '@aypatech_ai_agent/ai/core/attachment/attachment_card';
import { SLASH_COMMANDS } from '@aypatech_ai_agent/ai/chat/session/use_ai_session';

let fileInputCounter = 0;

const ACCEPT = [
    'image/png',
    'image/jpeg',
    'image/webp',
    'image/gif',
    'application/pdf',
    'text/plain',
    'text/csv',
    'text/markdown',
    '.md',
].join(',');

export const chatComposerProps = {
    value: t.string(),
    placeholder: t.string(),
    readonly: t.boolean().optional(false),
    readonlyOwner: t.string().optional(''),
    canSend: t.boolean().optional(false),
    canStop: t.boolean().optional(false),
    isQueueing: t.boolean().optional(false),
    attachments: t.array().optional(() => []),
    canAttach: t.boolean().optional(false),
    agents: t.array().optional(() => []),
    activeAgentId: t.any().optional(),
    sessionId: t.any().optional(),
    viewContext: t.any().optional(),
    onInput: t.function(),
    onSend: t.function(),
    onStop: t.function().optional(),
    onAttachFiles: t.function().optional(),
    onRemoveAttachment: t.function().optional(),
    onOpenAttachment: t.function().optional(),
    onSelectAgent: t.function().optional(),
    focusToken: t.or([t.number(), t.string()]).optional(),
};

/**
 * Message composer: text input, attachments, slash commands, and send/stop.
 *
 * Read only, it states so instead of drawing its input row, so every control
 * an extension contributes to that row goes with it.
 */
export class ChatComposer extends Component {
    static template = 'aypatech_ai_agent.ai_ChatComposer';
    static components = { AttachmentCard };
    props = useProps(chatComposerProps);
    accept = ACCEPT;
    setup() {
        this.inputRef = signal.ref();
        this.fileInputRef = signal.ref();
        fileInputCounter += 1;
        this.fileInputId = `aypatech_wooai_file_${fileInputCounter}`;
        this.localState = proxy({ slashActive: 0 });
        useLayoutEffect(
            () => {
                const el = this.inputRef();
                if (!el) {
                    return;
                }
                const active = document.activeElement;
                if (
                    active &&
                    active !== el &&
                    active.matches('textarea, input, [contenteditable="true"]')
                ) {
                    return;
                }
                el.focus();
            },
            () => [this.props.focusToken],
        );
        useLayoutEffect(() => {
            const el = this.inputRef();
            if (!el) return;
            const next = this.props.value || '';
            if (el.value !== next) {
                el.value = next;
            }
            const cs = getComputedStyle(el);
            const lh = parseFloat(cs.lineHeight) || 22;
            const pad = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
            const maxH = lh * 4 + pad;
            el.style.height = 'auto';
            el.style.height = Math.min(el.scrollHeight, maxH) + 'px';
            el.style.overflowY = el.scrollHeight > maxH ? 'auto' : 'hidden';
        });
        useLayoutEffect(
            () => {
                this.localState.slashActive = 0;
            },
            () => [this.menuItems.length],
        );
    }
    get slashCommands() {
        const value = (this.props.value || '').trim();
        if (!value.startsWith('/')) {
            return [];
        }
        const prefix = value.split(/\s+/)[0].toLowerCase();
        return SLASH_COMMANDS.filter((c) => c.name.startsWith(prefix));
    }
    get isAgentMode() {
        return /^\/agent(\s|$)/.test((this.props.value || '').trimStart());
    }
    get agentMatches() {
        if (!this.isAgentMode) {
            return [];
        }
        const query = (this.props.value || '')
            .trimStart()
            .replace(/^\/agent\s*/, '')
            .toLowerCase();
        return (this.props.agents || []).filter((a) =>
            (a.name || '').toLowerCase().includes(query),
        );
    }
    /**
     * State the chat is somebody else's, naming them when they are known.
     * @returns {string} the notice shown in place of the input row
     */
    get readonlyNotice() {
        return this.props.readonlyOwner
            ? _t('Read only — %s shared this chat with you.', this.props.readonlyOwner)
            : _t('Read only — this chat was shared with you.');
    }
    get menuItems() {
        return this.isAgentMode ? this.agentMatches : this.slashCommands;
    }
    get showSlashMenu() {
        return this.menuItems.length > 0;
    }
    onKeydown(event) {
        if (this.showSlashMenu) {
            const count = this.menuItems.length;
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                this.localState.slashActive = (this.localState.slashActive + 1) % count;
                return;
            }
            if (event.key === 'ArrowUp') {
                event.preventDefault();
                this.localState.slashActive =
                    (this.localState.slashActive - 1 + count) % count;
                return;
            }
            if (event.key === 'Tab' && !event.shiftKey) {
                event.preventDefault();
                this.pickActive(this.localState.slashActive);
                return;
            }
            if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
                event.preventDefault();
                if (this.isAgentMode) {
                    this.pickAgent(this.localState.slashActive);
                    return;
                }
                const cmd = this.slashCommands[this.localState.slashActive];
                const typed = (this.props.value || '').trim().toLowerCase();
                const wasAutocomplete = cmd && typed !== cmd.name;
                this.pickSlashCommand(this.localState.slashActive);
                const holdSend =
                    cmd && (cmd.opensPicker || (cmd.destructive && wasAutocomplete));
                if (cmd && !holdSend) {
                    this.onSendOrStop();
                }
                return;
            }
            if (event.key === 'Escape') {
                event.preventDefault();
                this.props.onInput('');
                return;
            }
        }
        if (event.key !== 'Enter' || event.isComposing || event.shiftKey) {
            return;
        }
        event.preventDefault();
        this.onSendOrStop();
    }
    pickActive(index) {
        if (this.isAgentMode) {
            this.pickAgent(index);
        } else {
            this.pickSlashCommand(index);
        }
    }
    pickSlashCommand(index) {
        const cmd = this.slashCommands[index];
        if (!cmd) {
            return;
        }
        const value = this.props.value || '';
        const tailMatch = value.match(/^\/\S*(\s.*)?$/);
        const tail = tailMatch?.[1] || '';
        this.props.onInput(cmd.name + tail);
        this.localState.slashActive = 0;
    }
    pickAgent(index) {
        const agent = this.agentMatches[index];
        if (!agent) {
            return;
        }
        if (this.props.onSelectAgent) {
            this.props.onSelectAgent(agent.id);
        }
        this.props.onInput('');
        this.localState.slashActive = 0;
    }
    hoverSlashCommand(index) {
        this.localState.slashActive = index;
    }
    onInputChange(event) {
        this.props.onInput(event.target.value);
    }
    onSendOrStop() {
        const hasLiveText = !!(this.inputRef() && this.inputRef().value.trim());
        const canSend = this.props.canSend || hasLiveText;
        if (canSend && this.props.isQueueing) {
            this.props.onSend();
            return;
        }
        if (this.props.canStop && this.props.onStop) {
            this.props.onStop();
            return;
        }
        if (canSend) {
            this.props.onSend();
        }
    }
    onLabelClick(event) {
        if (!this.props.canAttach) {
            event.preventDefault();
            return;
        }
        const input = this.fileInputRef();
        if (!input) {
            return;
        }
        event.preventDefault();
        input.click();
    }
    onFileInputChange(event) {
        const files = Array.from(event.target.files || []);
        if (files.length && this.props.onAttachFiles) {
            this.props.onAttachFiles(files);
        }
        event.target.value = '';
    }
    onPaste(event) {
        if (!this.props.canAttach) {
            return;
        }
        const items = (event.clipboardData && event.clipboardData.items) || [];
        const files = [];
        for (const item of items) {
            if (item.kind === 'file') {
                const file = item.getAsFile();
                if (file) {
                    files.push(file);
                }
            }
        }
        if (files.length && this.props.onAttachFiles) {
            event.preventDefault();
            this.props.onAttachFiles(files);
        }
    }
    onRemoveAttachment(attachment) {
        if (this.props.onRemoveAttachment) {
            this.props.onRemoveAttachment(attachment.id);
        }
    }
    onOpenAttachment(attachment) {
        if (this.props.onOpenAttachment) {
            this.props.onOpenAttachment(attachment);
        }
    }
}
