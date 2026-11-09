import { Component, proxy, signal, t, useProps } from '@odoo/owl';

import { _t } from '@web/core/l10n/translation';
import { useLayoutEffect } from '@web/owl2/utils';

import { getRecentSkillNames } from '@aypatech_ai_agent/skills/chat/recent_skills';

/** Browsable list of the session skills, grouped into recent and all. */
export class SkillsPanel extends Component {
    static template = 'aypatech_ai_agent.skills_SkillsPanel';
    props = useProps({
        skills: t.array(),
        lockedSkills: t.array().optional(() => []),
        autofocus: t.boolean().optional(false),
        onSelect: t.function(),
        onClose: t.function(),
    });
    setup() {
        this.rootRef = signal.ref();
        this.searchRef = signal.ref();
        this.state = proxy({ filter: '', activeIndex: 0 });
        useLayoutEffect(
            () => {
                const target = this.props.autofocus ? this.searchRef : this.rootRef;
                target()?.focus();
            },
            () => [],
        );
        useLayoutEffect(
            () => {
                this.state.activeIndex = 0;
            },
            () => [this.entries.length],
        );
    }
    /** Return the matching skills, recently used first, tagged with their group. */
    get entries() {
        const filter = this.state.filter.trim().toLowerCase();
        const recent = getRecentSkillNames();
        const used = recent
            .map((name) => this.props.skills.find((skill) => skill.name === name))
            .filter(Boolean);
        const ordered = [
            ...used,
            ...this.props.skills.filter((skill) => !used.includes(skill)),
        ];
        const recentNames = new Set(recent);
        let previous = null;
        return ordered
            .filter((skill) =>
                filter
                    ? `${skill.label || ''} ${skill.name} ${skill.description || ''}`
                          .toLowerCase()
                          .includes(filter)
                    : true,
            )
            .map((skill) => {
                const group = recentNames.has(skill.name)
                    ? _t('Recently used')
                    : _t('All skills');
                const first = group !== previous;
                previous = group;
                return { skill, group, first };
            });
    }
    /** Return the skills the pinned context withholds, matching the search. */
    get lockedEntries() {
        const filter = this.state.filter.trim().toLowerCase();
        return this.props.lockedSkills.filter((skill) =>
            filter
                ? `${skill.label || ''} ${skill.name} ${skill.description || ''}`
                      .toLowerCase()
                      .includes(filter)
                : true,
        );
    }
    onFilterInput(event) {
        this.state.filter = event.target.value;
    }
    hoverSkill(index) {
        this.state.activeIndex = index;
    }
    pickSkill(index) {
        const entry = this.entries[index];
        if (entry) {
            this.props.onSelect(entry.skill.name);
        }
    }
    onKeydown(event) {
        const count = this.entries.length;
        if (event.key === 'Escape') {
            event.preventDefault();
            this.props.onClose();
            return;
        }
        if (!count) {
            return;
        }
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            this.state.activeIndex = (this.state.activeIndex + 1) % count;
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            this.state.activeIndex = (this.state.activeIndex - 1 + count) % count;
        } else if (event.key === 'Enter' && !event.isComposing) {
            event.preventDefault();
            this.pickSkill(this.state.activeIndex);
        }
    }
}
