import { onMounted, onPatched } from '@odoo/owl';

import { patch } from '@web/core/utils/patch';
import { PivotController } from '@web/views/pivot/pivot_controller';

import { useAdjustTarget } from '@aypatech_ai_agent/ai/views/adjust';
import { makePivotContextDispatch } from '@aypatech_ai_agent/ai/views/context';

/** Capture the active pivot view as AI view context for open chat windows. */
patch(PivotController.prototype, {
    setup() {
        super.setup(...arguments);
        if (!this.env.services['aypatech_ai_agent.ai_chat_window']) {
            return;
        }
        useAdjustTarget(this);
        const dispatch = makePivotContextDispatch(this);
        onMounted(dispatch);
        onPatched(dispatch);
    },
});
