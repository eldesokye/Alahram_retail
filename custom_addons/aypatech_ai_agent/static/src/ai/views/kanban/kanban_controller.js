import { onMounted, onPatched } from '@odoo/owl';

import { patch } from '@web/core/utils/patch';
import { KanbanController } from '@web/views/kanban/kanban_controller';

import { useAdjustTarget } from '@aypatech_ai_agent/ai/views/adjust';
import { makeListContextDispatch } from '@aypatech_ai_agent/ai/views/context';

/** Capture the active kanban view as AI view context for open chat windows. */
patch(KanbanController.prototype, {
    setup() {
        super.setup(...arguments);
        if (!this.env.services['aypatech_ai_agent.ai_chat_window']) {
            return;
        }
        useAdjustTarget(this);
        const dispatch = makeListContextDispatch(this, 'kanban');
        onMounted(dispatch);
        onPatched(dispatch);
    },
});
