import { registry } from '@web/core/registry';

registry.category('web_tour.tours').add('aypatech_woomcp_playground_tour', {
    steps: () => [
        {
            trigger: '.o_aypatech_woomcp_playground',
        },
        {
            trigger: '.o_aypatech_woomcp_keybar button:contains(Generate new)',
            run: 'click',
        },
        {
            trigger: '.o_aypatech_woomcp_keybar .badge.text-bg-success',
        },
        {
            trigger: '.o_aypatech_woomcp_list input[type=search]',
            run: 'edit whoami',
        },
        {
            trigger: '.o_aypatech_woomcp_tool:contains(whoami)',
            run: 'click',
        },
        {
            trigger: '.o_aypatech_woomcp_detail button:contains(Try it):not([disabled])',
            run: 'click',
        },
        {
            trigger: '.alert.alert-success',
        },
    ],
});
