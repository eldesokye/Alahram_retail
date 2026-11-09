import { _t } from '@web/core/l10n/translation';
import { registry } from '@web/core/registry';
import { user } from '@web/core/user';

import { seedSessionContext } from '@aypatech_ai_agent/ai/views/context';

const providerRegistry = registry.category('command_provider');

async function openChat(env, sessionId) {
    await env.services.action.doAction({
        type: 'ir.actions.client',
        tag: 'aypatech_ai_agent.ai_chat',
        params: sessionId ? { session_id: sessionId } : {},
    });
}

providerRegistry.add('aypatech_wooai_sessions', {
    namespace: '%',
    async provide(env, options) {
        const needle = (options.searchValue || '').trim();
        const domain = [['user_id', '=', user.userId]];
        if (needle) {
            domain.push(['name', 'ilike', needle]);
        }
        const sessions = await env.services.orm.searchRead(
            'aypatech_wooai.session',
            domain,
            ['id', 'name'],
            { limit: 20, order: 'create_date DESC' },
        );
        const commands = [
            {
                name: _t('New Chat'),
                category: 'aypatech_wooai',
                async action() {
                    const [sessionId] = await env.services.orm.create(
                        'aypatech_wooai.session',
                        [
                            {
                                name:
                                    needle ||
                                    _t('Chat %s', new Date().toLocaleString()),
                            },
                        ],
                    );
                    await seedSessionContext(env, sessionId);
                    await openChat(env, sessionId);
                },
            },
        ];
        for (const session of sessions) {
            commands.push({
                name: session.name || _t('Chat %s', session.id),
                category: 'aypatech_wooai',
                action() {
                    openChat(env, session.id);
                },
            });
        }
        return commands;
    },
});
