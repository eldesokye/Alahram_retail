import { _t } from '@web/core/l10n/translation';
import { usePopover } from '@web/core/popover/popover_hook';

import { registerComposerAction } from '@mail/core/common/composer_actions';

import { makeTextComposerAdapter } from '@aypatech_ai_agent/chatter/composer/adapters';
import { ComposePanel } from '@aypatech_ai_agent/chatter/composer/compose_panel';

registerComposerAction('aypatech-wooai-write', {
    // Staff only, and stated as such: a guest has no `self_user` at all,
    // and a merely falsy `share` would offer them a panel they may not use.
    condition: ({ store }) => store.self_user?.share === false,
    icon: 'ayp_icon_ai',
    name: _t('Write with AI'),
    setup: ({ owner }) => {
        owner.aypatechWooAiWritePopover = usePopover(ComposePanel, {
            position: 'top-start',
            popoverClass: 'o-mail-ComposePanel-popover',
            // Clicking away leaves the panel open on purpose: a draft the
            // user is reading is thrown away by the stray click that put the
            // cursor back in the message. Escape and Discard close it.
            closeOnClickAway: false,
        });
    },
    onSelected: ({ composer, owner }) => {
        // Anchored on the composer root, which outlives the re-renders typing
        // causes: a popover whose anchor is replaced under it drifts off to a
        // corner of the screen.
        const anchor = owner.root?.() || owner.inputContainerRef?.();
        if (!anchor) {
            return;
        }
        owner.aypatechWooAiWritePopover.open(anchor, {
            adapter: makeTextComposerAdapter(composer, owner.ref?.()),
            close: () => owner.aypatechWooAiWritePopover.close(),
        });
    },
    sequenceQuick: 25,
});
