import { Component, onMounted, proxy, signal, t, useProps } from '@odoo/owl';

import { _t } from '@web/core/l10n/translation';
import { Dialog } from '@web/core/dialog/dialog';

/** Modal dialog prompting for a new session name. */
export class RenameDialog extends Component {
    static template = 'aypatech_ai_agent.ai_RenameDialog';
    static components = { Dialog };
    props = useProps({
        close: t.function(),
        title: t.string().optional(_t('Rename chat')),
        initial: t.string().optional(''),
        placeholder: t.string().optional(_t('Chat name')),
        onConfirm: t.function(),
    });
    setup() {
        this.state = proxy({ value: this.props.initial || '' });
        this.inputRef = signal.ref();
        onMounted(() => {
            const el = this.inputRef();
            if (el) {
                el.focus();
                el.select();
            }
        });
    }
    get canConfirm() {
        const v = (this.state.value || '').trim();
        return !!v && v !== this.props.initial;
    }
    onInput(ev) {
        this.state.value = ev.target.value;
    }
    onKeydown(ev) {
        if (ev.key === 'Enter' && !ev.isComposing) {
            ev.preventDefault();
            this.confirm();
        }
    }
    confirm() {
        if (!this.canConfirm) {
            return;
        }
        this.props.onConfirm(this.state.value.trim());
        this.props.close();
    }
    cancel() {
        this.props.close();
    }
}
