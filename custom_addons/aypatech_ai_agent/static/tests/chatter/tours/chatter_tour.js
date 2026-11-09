import { registry } from '@web/core/registry';

registry.category('web_tour.tours').add('aypatech_wooai_chatter_tour', {
    steps: () => [
        {
            trigger: '.o-mail-Chatter-wooAiSessions:contains("1")',
            content: 'The chatter topbar counts the sessions linked to the record',
        },
        {
            trigger: '.o-mail-Chatter-wooAiSessions',
            content: 'The list stays out of the way until it is asked for',
            run: () => {
                if (document.querySelector('.o-mail-WooAISessionBox')) {
                    throw new Error(
                        'the AI sessions were listed before being asked for',
                    );
                }
            },
        },
        {
            trigger: '.o-mail-Chatter-wooAiSessions',
            content: 'Show the AI sessions',
            run: 'click',
        },
        {
            trigger: '.o-mail-WooAISessionBox:contains("AI Sessions")',
            content: 'The AI Sessions section renders on the linked record',
        },
        {
            trigger: '.o-mail-WooAISessionBox-item:contains("Tour Session")',
            content: 'The session linked to this record is listed',
        },
        {
            trigger:
                '.o-mail-WooAISessionBox-item .o-mail-WooAISessionBox-state.o-state-done',
            content: 'Its state is carried by the colour of a dot',
        },
    ],
});
