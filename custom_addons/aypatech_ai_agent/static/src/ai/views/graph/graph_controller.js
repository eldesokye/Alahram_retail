import { onMounted, onPatched } from '@odoo/owl';

import { patch } from '@web/core/utils/patch';
import { GraphController } from '@web/views/graph/graph_controller';

import { useAdjustTarget } from '@aypatech_ai_agent/ai/views/adjust';
import { makeGraphContextDispatch } from '@aypatech_ai_agent/ai/views/context';

/** Capture the active graph view as AI view context for open chat windows. */
patch(GraphController.prototype, {
    setup() {
        super.setup(...arguments);
        if (!this.env.services['aypatech_ai_agent.ai_chat_window']) {
            return;
        }
        useAdjustTarget(this);
        const dispatch = makeGraphContextDispatch(this);
        onMounted(dispatch);
        onPatched(dispatch);
    },
});
