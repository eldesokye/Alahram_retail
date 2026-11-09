import { afterEach, describe, expect, test } from '@odoo/hoot';
import { animationFrame } from '@odoo/hoot-mock';
import { Component, t, useProps, xml } from '@odoo/owl';
import { queryAll, queryFirst } from '@odoo/hoot-dom';
import { mountWithCleanup, patchTranslations } from '@web/../tests/web_test_helpers';
import { defineMailModels } from '@mail/../tests/mail_test_helpers';

import { registry } from '@web/core/registry';

import { ChatArtifactsPanel } from '@aypatech_ai_agent/ai/chat/artifacts/chat_artifacts_panel';
import '@aypatech_ai_agent/ai/chat/artifacts/types/attachments_type';

const ARTIFACT_TYPES = registry.category('aypatech_ai_agent.ai_artifact_types');

describe.current.tags('aypatech_wooai');
defineMailModels();
patchTranslations();

class FakeTab extends Component {
    static template = xml`
        <div class="ayp_fake_tab">
            <t t-foreach="this.props.items" t-as="item" t-key="item_index">
                <span class="ayp_fake_item" t-esc="JSON.stringify(item)"/>
            </t>
        </div>
    `;
    props = useProps({
        items: t.array(),
        session: t.object().optional(),
        onOpenAttachment: t.function().optional(),
    });
}

afterEach(() => {
    for (const id of ['fake', 'fake2']) {
        if (ARTIFACT_TYPES.contains(id)) {
            try {
                ARTIFACT_TYPES.remove(id);
            } catch {
                /* ignore */
            }
        }
    }
});

function mountPanel(sessionLike) {
    class Parent extends Component {
        static components = { ChatArtifactsPanel };
        props = useProps({});
        static template = xml`
            <ChatArtifactsPanel
                session="this.props.session"
                onClose="() => {}"
            />
        `;
    }
    Parent.props = { session: { type: Object } };
    return mountWithCleanup(Parent, { props: { session: sessionLike } });
}

test('a registered artifact type contributes a tab next to attachments', async () => {
    ARTIFACT_TYPES.add(
        'fake',
        {
            id: 'fake',
            label: 'Fake',
            icon: 'fa-flask',
            sequence: 50,
            component: FakeTab,
            collect: () => [{ a: 1 }, { b: 2 }],
        },
        { force: true },
    );
    const session = {
        state: {
            pendingAttachments: [{ id: 1, filename: 'a.png', mimetype: 'image/png' }],
            events: [],
        },
    };
    await mountPanel(session);
    const tabs = queryAll('.ayp_artifacts_panel .ayp_artifacts_tab');
    expect(tabs.length).toBe(2);
    const labels = tabs.map((t) => t.textContent.trim());
    expect(labels.some((l) => l.includes('Fake'))).toBe(true);
    expect(labels.some((l) => l.includes('Attachments'))).toBe(true);
});

test('initial active tab is the lowest-sequence registered type', async () => {
    ARTIFACT_TYPES.add(
        'fake2',
        {
            id: 'fake2',
            label: 'Fake2',
            icon: 'fa-flask',
            sequence: 50,
            component: FakeTab,
            collect: () => [{ a: 1 }, { b: 2 }],
        },
        { force: true },
    );
    const session = {
        state: {
            pendingAttachments: [{ id: 1, filename: 'a.png', mimetype: 'image/png' }],
            events: [],
        },
    };
    await mountPanel(session);
    await animationFrame();
    const tabs = queryAll('.ayp_artifacts_panel .ayp_artifacts_tab');
    const attBtn = tabs.find((t) => t.textContent.includes('Attachments'));
    const fakeBtn = tabs.find((t) => t.textContent.includes('Fake2'));
    expect(attBtn.classList.contains('active')).toBe(true);
    expect(fakeBtn.classList.contains('active')).toBe(false);
});

test('only a single non-empty type → no tab strip', async () => {
    const session = {
        state: {
            pendingAttachments: [{ id: 1, filename: 'a.png', mimetype: 'image/png' }],
            events: [],
        },
    };
    await mountPanel(session);
    await animationFrame();
    expect(queryFirst('.ayp_artifacts_panel .ayp_artifacts_tabs')).toBe(null);
});

test('assistant inline images (persisted /web/image markdown) appear as attachments', () => {
    const collect = ARTIFACT_TYPES.get('attachments').collect;
    const items = collect({
        pendingAttachments: [],
        events: [
            { kind: 'user_message', content: 'generate an image', attachments: [] },
            {
                kind: 'text',
                content:
                    'Here you go ![rocket logo](/web/image/1032) _(attachment 1032 — to set on a record use `image_1920="@attachment:1032"`)_',
            },
        ],
    });
    expect(items.length).toBe(1);
    expect(items[0].id).toBe(1032);
    expect(items[0].filename).toBe('rocket logo');
    expect(items[0].mimetype).toBe('image/png');
});

test('assistant inline images dedupe against repeated references', () => {
    const collect = ARTIFACT_TYPES.get('attachments').collect;
    const items = collect({
        pendingAttachments: [],
        events: [
            {
                kind: 'text',
                content: '![a](/web/image/7) and again ![a](/web/image/7)',
            },
            { kind: 'text', content: '![b](/web/image/8)' },
        ],
    });
    expect(items.map((i) => i.id)).toEqual([7, 8]);
});
