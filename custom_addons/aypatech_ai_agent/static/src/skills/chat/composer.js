import { proxy, signal, t, useListener } from '@odoo/owl';

import { hasTouch } from '@web/core/browser/feature_detection';
import { patch } from '@web/core/utils/patch';

import {
    ChatComposer,
    chatComposerProps,
} from '@aypatech_ai_agent/ai/chat/composer/chat_composer';

import { skillScopeSatisfied } from '@aypatech_ai_agent/skills/chat/scope';
import { skillStore } from '@aypatech_ai_agent/skills/chat/skill_cache';
import { SkillsPanel } from '@aypatech_ai_agent/skills/chat/skills_panel';

ChatComposer.components = { ...ChatComposer.components, SkillsPanel };
Object.assign(chatComposerProps, {
    onInvokeSkill: t.function().optional(),
});

/** Merge visible skills into the slash suggestions and the skills panel. */
patch(ChatComposer.prototype, {
    setup() {
        super.setup();
        this.hostRef = signal.ref();
        this.skillState = proxy(skillStore);
        this.localState.skillsOpen = false;
        useListener(document, 'mousedown', (event) => {
            if (
                this.localState.skillsOpen &&
                !this.hostRef()?.contains(event.target)
            ) {
                this.localState.skillsOpen = false;
            }
        });
    },
    /** Close the panel as soon as the composer starts a slash command. */
    onInputChange(event) {
        if (event.target.value.trimStart().startsWith('/')) {
            this.localState.skillsOpen = false;
        }
        return super.onInputChange(event);
    },
    get slashCommands() {
        const builtIn = super.slashCommands;
        const value = (this.props.value || '').trim();
        if (!value.startsWith('/')) {
            return builtIn;
        }
        const prefix = value.split(/\s+/)[0].toLowerCase();
        const skillEntries = this.availableSkills.map((skill) => ({
            name: `/${skill.name}`,
            hint: skill.description
                ? `Skill: ${skill.description}`
                : `Invoke skill ${skill.label || skill.name}`,
            isSkill: true,
        }));
        const matchingSkills = skillEntries.filter((c) => c.name.startsWith(prefix));
        const seen = new Set(builtIn.map((c) => c.name));
        const merged = [...builtIn];
        for (const entry of matchingSkills) {
            if (!seen.has(entry.name)) {
                merged.push(entry);
                seen.add(entry.name);
            }
        }
        return merged;
    },
    /** Return the session skills through the reactive store, so fills re-render. */
    get sessionSkills() {
        return (this.props.sessionId && this.skillState[this.props.sessionId]) || [];
    },
    get availableSkills() {
        return this.sessionSkills.filter((skill) =>
            skillScopeSatisfied(skill, this.props.viewContext),
        );
    },
    get lockedSkills() {
        return this.sessionSkills.filter(
            (skill) => !skillScopeSatisfied(skill, this.props.viewContext),
        );
    },
    get hasSkills() {
        return this.sessionSkills.length > 0;
    },
    get showSkillsPanel() {
        return this.localState.skillsOpen;
    },
    /** Focus the panel search only where a keyboard will not cover the list. */
    get skillsAutofocus() {
        return !hasTouch();
    },
    /** Toggle the panel, dropping the composer caret so no keyboard covers it. */
    toggleSkillsPanel() {
        if (!this.localState.skillsOpen && this.showSlashMenu) {
            return;
        }
        this.localState.skillsOpen = !this.localState.skillsOpen;
        if (this.localState.skillsOpen) {
            this.inputRef()?.blur();
        }
    },
    closeSkillsPanel() {
        this.localState.skillsOpen = false;
        this.inputRef()?.focus();
    },
    invokeSkill(name) {
        this.localState.skillsOpen = false;
        this.props.onInvokeSkill?.(name);
    },
});
