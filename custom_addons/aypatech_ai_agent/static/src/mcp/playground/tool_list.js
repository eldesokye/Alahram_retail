import { Component, t, useProps } from '@odoo/owl';
import { categoryBadge, categoryLabel } from './utils';

/**
 * Searchable, category-grouped sidebar listing the available tools and emitting
 * selection and search events to the parent.
 */
export class ToolList extends Component {
    static template = 'aypatech_ai_agent.mcp_ToolList';
    props = useProps({
        groups: t.array(),
        selected: t.or([t.string(), t.literal(null)]).optional(),
        search: t.string(),
        onSearch: t.function(),
        onSelect: t.function(),
    });
    setup() {
        this.categoryLabel = categoryLabel;
        this.categoryBadge = categoryBadge;
    }
}
