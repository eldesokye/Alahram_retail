import { _t } from '@web/core/l10n/translation';
import { registry } from '@web/core/registry';

registry.category('command_setup').add('%', {
    debounceDelay: 200,
    name: _t('AI'),
    placeholder: _t('Search AI chats and agents…'),
    emptyMessage: _t('No AI chat or agent found.'),
});

registry
    .category('command_categories')
    .add('aypatech_wooai', { namespace: '%', name: _t('WooFusion AI') }, { sequence: 60 });
