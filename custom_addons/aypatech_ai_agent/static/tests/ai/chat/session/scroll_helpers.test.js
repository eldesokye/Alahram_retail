import { describe, expect, test } from '@odoo/hoot';
import { animationFrame, Deferred } from '@odoo/hoot-mock';
import { Component, signal, useProps, xml } from '@odoo/owl';
import { mountWithCleanup } from '@web/../tests/web_test_helpers';
import { defineMailModels } from '@mail/../tests/mail_test_helpers';

import {
    onScrollUpNearTop,
    preserveAnchor,
} from '@aypatech_ai_agent/ai/chat/session/use_scroll_anchor';

describe.current.tags('aypatech_wooai');
defineMailModels();

/**
 * Force a scroll metric onto an element, since the test fixture never scrolls.
 * @param {HTMLElement} el element to fake
 * @param {string} name metric name (``scrollTop`` or ``scrollHeight``)
 * @param {number} value value to report
 */
function setMetric(el, name, value) {
    Object.defineProperty(el, name, { configurable: true, writable: true, value });
}

/**
 * Move a scroller to an absolute offset and notify its listeners.
 * @param {HTMLElement} el scroll container
 * @param {number} top new ``scrollTop`` value
 */
function scrollTo(el, top) {
    setMetric(el, 'scrollTop', top);
    el.dispatchEvent(new Event('scroll'));
}

/**
 * Mount a scroller wired to ``onScrollUpNearTop`` and hand back its element.
 * @param {Function} callback handler passed to the hook
 * @param {number} [thresholdPx] distance from the top that triggers the callback
 * @returns {Promise<HTMLElement>} the mounted scroll container
 */
async function mountScroller(callback, thresholdPx) {
    let scrollRef;
    class Harness extends Component {
        props = useProps({});
        static template = xml`
            <div t-ref="this.scrollRef" class="ayp_scroller">
                <div class="ayp_scroller_content"/>
            </div>
        `;
        setup() {
            scrollRef = signal.ref();
            this.scrollRef = scrollRef;
            onScrollUpNearTop(scrollRef, callback, thresholdPx);
        }
    }
    await mountWithCleanup(Harness, { props: {} });
    return scrollRef();
}

/**
 * Build a detached element reporting the given scroll metrics.
 * @param {number} scrollHeight total scrollable height
 * @param {number} scrollTop current offset
 * @returns {Function} a ref-like signal reading back the element
 */
function fakeScrollerRef(scrollHeight, scrollTop) {
    const el = document.createElement('div');
    setMetric(el, 'scrollHeight', scrollHeight);
    setMetric(el, 'scrollTop', scrollTop);
    return () => el;
}

// onScrollUpNearTop

test('scrolling down into the top zone never pages older history', async () => {
    const calls = [];
    const el = await mountScroller(() => calls.push('load'));
    scrollTo(el, 100);
    scrollTo(el, 900);
    expect(calls).toEqual([]);
});

test('scrolling up into the top zone pages older history once', async () => {
    const calls = [];
    const el = await mountScroller(() => calls.push('load'));
    scrollTo(el, 900);
    scrollTo(el, 50);
    expect(calls).toEqual(['load']);
});

test('scrolling up above the threshold leaves history alone', async () => {
    const calls = [];
    const el = await mountScroller(() => calls.push('load'), 200);
    scrollTo(el, 1000);
    scrollTo(el, 500);
    expect(calls).toEqual([]);
    scrollTo(el, 150);
    expect(calls).toEqual(['load']);
});

test('a custom threshold widens the zone that pages older history', async () => {
    const calls = [];
    const el = await mountScroller(() => calls.push('load'), 600);
    scrollTo(el, 1000);
    scrollTo(el, 500);
    expect(calls).toEqual(['load']);
});

test('a second scroll while a page is in flight does not fetch twice', async () => {
    const calls = [];
    const gates = [];
    const el = await mountScroller(() => {
        calls.push('load');
        const gate = new Deferred();
        gates.push(gate);
        return gate;
    }, 200);
    scrollTo(el, 1000);
    scrollTo(el, 100);
    expect(calls).toEqual(['load']);
    scrollTo(el, 400);
    scrollTo(el, 50);
    expect(calls).toEqual(['load']);

    gates[0].resolve();
    await animationFrame();
    scrollTo(el, 400);
    scrollTo(el, 20);
    expect(calls).toEqual(['load', 'load']);
    gates[1].resolve();
    await animationFrame();
});

// preserveAnchor

test('preserveAnchor keeps the viewport on the same content after a prepend', async () => {
    const ref = fakeScrollerRef(1000, 200);
    await preserveAnchor(ref, () => {
        setMetric(ref(), 'scrollHeight', 1500);
    });
    await animationFrame();
    expect(ref().scrollTop).toBe(700);
});

test('preserveAnchor awaits the mutation before restoring the anchor', async () => {
    const ref = fakeScrollerRef(1000, 200);
    const deferred = new Deferred();
    const running = preserveAnchor(ref, async () => {
        await deferred;
        setMetric(ref(), 'scrollHeight', 2000);
    });
    await animationFrame();
    expect(ref().scrollTop).toBe(200);
    deferred.resolve();
    await running;
    await animationFrame();
    expect(ref().scrollTop).toBe(1200);
});

test('preserveAnchor restores the anchor even when the mutation fails', async () => {
    const ref = fakeScrollerRef(1000, 200);
    let caught = null;
    try {
        await preserveAnchor(ref, () => {
            setMetric(ref(), 'scrollHeight', 1500);
            throw new Error('history fetch failed');
        });
    } catch (error) {
        caught = error;
    }
    await animationFrame();
    expect(caught.message).toBe('history fetch failed');
    expect(ref().scrollTop).toBe(700);
});
