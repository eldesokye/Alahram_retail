import { _t } from '@web/core/l10n/translation';

import { toolBlockDecorators } from '@aypatech_ai_agent/ai/chat/session/turns';

/**
 * Read the skill name out of an ``invoke_skill`` call's arguments.
 *
 * Providers hand the arguments over either already parsed or as the raw JSON
 * string they arrived in, and a malformed payload must not cost the card its
 * name.
 * @param {object} entry the tool_call session event
 * @returns {string} the skill name, or an empty string
 */
function invokedSkillName(entry) {
    const args = entry?.arguments;
    try {
        const parsed = typeof args === 'string' ? JSON.parse(args) : args;
        return parsed?.skill_name || '';
    } catch {
        return '';
    }
}

toolBlockDecorators.add('aypatech_ai_agent.skills_invoke_skill', (block, entry) => {
    if (!String(block.name || '').endsWith('invoke_skill')) {
        return;
    }
    const name = invokedSkillName(entry);
    if (name) {
        block.label = _t('Skill: %s', name);
    }
});
