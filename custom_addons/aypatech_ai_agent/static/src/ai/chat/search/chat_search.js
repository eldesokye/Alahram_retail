import { Component, onMounted, signal, t, useProps } from '@odoo/owl';

/** In-conversation search bar with match navigation controls. */
export class ChatSearch extends Component {
    static template = 'aypatech_ai_agent.ai_ChatSearch';
    props = useProps({
        query: t.string(),
        total: t.number(),
        currentIdx: t.number(),
        onChange: t.function(),
        onPrev: t.function(),
        onNext: t.function(),
        onClose: t.function(),
    });
    setup() {
        this.inputRef = signal.ref();
        onMounted(() => {
            if (this.inputRef()) {
                this.inputRef().focus();
                this.inputRef().select();
            }
        });
    }
    onInput(ev) {
        this.props.onChange(ev.target.value);
    }
    onKeyDown(ev) {
        if (ev.key === 'Escape') {
            ev.preventDefault();
            this.props.onClose();
        } else if (ev.key === 'Enter') {
            ev.preventDefault();
            if (ev.shiftKey) {
                this.props.onPrev();
            } else {
                this.props.onNext();
            }
        }
    }
    get counterLabel() {
        if (!this.props.query) return '';
        if (!this.props.total) return '0 of 0';
        return `${this.props.currentIdx + 1} of ${this.props.total}`;
    }
}
