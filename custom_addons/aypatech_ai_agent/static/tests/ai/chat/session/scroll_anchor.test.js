import { describe, expect, test } from '@odoo/hoot';
import { Component, useProps, xml } from '@odoo/owl';
import { mountWithCleanup } from '@web/../tests/web_test_helpers';
import { defineMailModels } from '@mail/../tests/mail_test_helpers';

import { useChatScrollAnchor } from '@aypatech_ai_agent/ai/chat/session/use_scroll_anchor';

describe.current.tags('aypatech_wooai');
defineMailModels();

function makeHarness() {
    let api;
    class Harness extends Component {
        props = useProps({});
        static template = xml`
            <div class="harness">
                <div t-ref="this.scrollRef" class="scroll" style="height: 200px; overflow: auto;">
                    <div class="content" style="height: 2000px;"/>
                </div>
            </div>
        `;
        setup() {
            api = useChatScrollAnchor();
            this.scrollRef = api.scrollRef;
        }
    }
    return { Harness, getApi: () => api };
}

test('scroll anchor initializes atBottom true and scrolls on mount', async () => {
    const harness = makeHarness();
    await mountWithCleanup(harness.Harness, { props: {} });
    const api = harness.getApi();
    expect(api.state.atBottom).toBe(true);
    expect(api.scrollRef()).not.toBe(null);
});

test('scrollToBottom(force) sets atBottom=true', async () => {
    const harness = makeHarness();
    await mountWithCleanup(harness.Harness, { props: {} });
    const api = harness.getApi();
    api.state.atBottom = false;
    api.scrollToBottom(true);
    expect(api.state.atBottom).toBe(true);
});

test('scrollToBottom without force and user scrolled up flips atBottom to false', async () => {
    const harness = makeHarness();
    await mountWithCleanup(harness.Harness, { props: {} });
    const api = harness.getApi();
    const el = api.scrollRef();
    Object.defineProperty(el, 'scrollHeight', { value: 2000, configurable: true });
    Object.defineProperty(el, 'clientHeight', { value: 200, configurable: true });
    el.scrollTop = 0;
    api.scrollToBottom(false);
    expect(api.state.atBottom).toBe(false);
});

test('scroll event at the bottom marks atBottom true', async () => {
    const harness = makeHarness();
    await mountWithCleanup(harness.Harness, { props: {} });
    const api = harness.getApi();
    const el = api.scrollRef();
    Object.defineProperty(el, 'scrollHeight', { value: 500, configurable: true });
    Object.defineProperty(el, 'clientHeight', { value: 500, configurable: true });
    el.scrollTop = 0;
    el.dispatchEvent(new Event('scroll'));
    expect(api.state.atBottom).toBe(true);
});

test('scroll event far from the bottom marks atBottom false', async () => {
    const harness = makeHarness();
    await mountWithCleanup(harness.Harness, { props: {} });
    const api = harness.getApi();
    const el = api.scrollRef();
    Object.defineProperty(el, 'scrollHeight', { value: 2000, configurable: true });
    Object.defineProperty(el, 'clientHeight', { value: 200, configurable: true });
    el.scrollTop = 0;
    el.dispatchEvent(new Event('scroll'));
    expect(api.state.atBottom).toBe(false);
});
