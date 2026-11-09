import { afterEach, describe, expect, test } from '@odoo/hoot';
import { animationFrame } from '@odoo/hoot-mock';
import { Component, t, useProps, xml } from '@odoo/owl';
import { click, queryAll, queryFirst } from '@odoo/hoot-dom';
import {
    contains,
    mountWithCleanup,
    patchTranslations,
} from '@web/../tests/web_test_helpers';
import { registry } from '@web/core/registry';
import { defineMailModels } from '@mail/../tests/mail_test_helpers';

import { ChatArtifactsPanel } from '@aypatech_ai_agent/ai/chat/artifacts/chat_artifacts_panel';
import '@aypatech_ai_agent/ai/chat/artifacts/types/attachments_type';

const ARTIFACT_TYPES = registry.category('aypatech_ai_agent.ai_artifact_types');

describe.current.tags('aypatech_wooai');
defineMailModels();
patchTranslations();

class ProbeTab extends Component {
    static template = xml`<div class="ayp_probe_tab" t-esc="this.props.items.length"/>`;
    props = useProps({
        items: t.array(),
        session: t.object().optional(),
        onOpenAttachment: t.function().optional(),
    });
}

/**
 * Register a throwaway artifact type for the duration of the current test.
 * @param {string} id registry key of the artifact type
 * @param {object} definition partial artifact-type definition to merge in
 */
function registerType(id, definition) {
    ARTIFACT_TYPES.add(
        id,
        { id, label: id, icon: 'fa-flask', sequence: 5, ...definition },
        { force: true },
    );
}

afterEach(() => {
    for (const id of ['boom', 'nocollect', 'probe']) {
        if (ARTIFACT_TYPES.contains(id)) {
            try {
                ARTIFACT_TYPES.remove(id);
            } catch {
                /* ignore */
            }
        }
    }
});

function makeSession({ pendingAttachments = [], events = [] } = {}) {
    return {
        state: {
            pendingAttachments,
            events,
        },
    };
}

function mountPanel(sessionLike, _opts = {}) {
    const closed = { count: 0 };
    const opened = [];
    class Parent extends Component {
        static components = { ChatArtifactsPanel };
        props = useProps({});
        static template = xml`
            <ChatArtifactsPanel
                session="this.props.session"
                onClose="() => this.props.onClose()"
                onOpenAttachment="(att) => this.props.onOpenAttachment(att)"
            />
        `;
    }
    Parent.props = {
        session: { type: Object },
        onClose: { type: Function },
        onOpenAttachment: { type: Function },
    };
    return mountWithCleanup(Parent, {
        props: {
            session: sessionLike,
            onClose: () => {
                closed.count += 1;
            },
            onOpenAttachment: (att) => opened.push(att),
        },
    }).then((parent) => ({ parent, closed, opened }));
}

test('renders attachments tab with two cards from pending + user events', async () => {
    const session = makeSession({
        pendingAttachments: [{ id: 1, filename: 'a.png', mimetype: 'image/png' }],
        events: [
            {
                kind: 'user_message',
                content: 'hello',
                attachments: [
                    { id: 2, filename: 'b.pdf', mimetype: 'application/pdf' },
                ],
            },
        ],
    });
    await mountPanel(session);
    const cards = queryAll('.ayp_artifacts_panel .ayp_att_card');
    expect(cards.length).toBe(2);
});

test('clicking a card forwards attachment via onOpenAttachment', async () => {
    const session = makeSession({
        events: [
            {
                kind: 'user_message',
                content: 'x',
                attachments: [{ id: 9, filename: 'c.txt', mimetype: 'text/plain' }],
            },
        ],
    });
    const { opened } = await mountPanel(session);
    await click(queryFirst('.ayp_artifacts_panel .ayp_att_card'));
    expect(opened.length).toBe(1);
    expect(opened[0].id).toBe(9);
});

test('close button triggers onClose prop', async () => {
    const session = makeSession({
        pendingAttachments: [{ id: 1, filename: 'a.png', mimetype: 'image/png' }],
    });
    const { closed } = await mountPanel(session);
    await click(queryFirst('.ayp_artifacts_panel .ayp_artifacts_close'));
    expect(closed.count).toBe(1);
});

test('panel renders empty placeholder when no artifacts contributed', async () => {
    const session = makeSession({});
    await mountPanel(session);
    const empty = queryFirst('.ayp_artifacts_panel .ayp_artifacts_empty');
    expect(empty).not.toBe(null);
});

test('an artifact type whose collect throws leaves the panel empty, not broken', async () => {
    registerType('boom', {
        component: ProbeTab,
        collect: () => {
            throw new Error('third-party artifact type blew up');
        },
    });
    await mountPanel(makeSession({}));
    expect('.ayp_artifacts_panel').toHaveCount(1);
    expect('.ayp_probe_tab').toHaveCount(0);
    expect(queryFirst('.ayp_artifacts_panel .ayp_artifacts_empty')).not.toBe(null);
});

test('a throwing artifact type does not take the healthy tabs down with it', async () => {
    registerType('boom', {
        component: ProbeTab,
        collect: () => {
            throw new Error('third-party artifact type blew up');
        },
    });
    await mountPanel(
        makeSession({
            pendingAttachments: [{ id: 1, filename: 'a.png', mimetype: 'image/png' }],
        }),
    );
    expect('.ayp_att_card').toHaveCount(1);
    expect('.ayp_probe_tab').toHaveCount(0);
    expect(queryFirst('.ayp_artifacts_panel .ayp_artifacts_tabs')).toBe(null);
});

test('an artifact type without a collect function contributes no tab', async () => {
    registerType('nocollect', { component: ProbeTab });
    await mountPanel(
        makeSession({
            pendingAttachments: [{ id: 1, filename: 'a.png', mimetype: 'image/png' }],
        }),
    );
    expect('.ayp_att_card').toHaveCount(1);
    expect('.ayp_probe_tab').toHaveCount(0);
    expect(queryFirst('.ayp_artifacts_panel .ayp_artifacts_tabs')).toBe(null);
});

test('the panel falls back to the first tab when the selected one runs dry', async () => {
    let probeItems = [{ a: 1 }];
    registerType('probe', {
        sequence: 50,
        component: ProbeTab,
        collect: () => probeItems,
    });
    const { parent } = await mountPanel(
        makeSession({
            pendingAttachments: [{ id: 1, filename: 'a.png', mimetype: 'image/png' }],
        }),
    );
    await contains('.ayp_artifacts_tab', { text: 'probe' }).click();
    expect('.ayp_probe_tab').toHaveCount(1);
    expect('.ayp_att_card').toHaveCount(0);

    probeItems = [];
    parent.render(true);
    await animationFrame();
    expect('.ayp_probe_tab').toHaveCount(0);
    expect('.ayp_att_card').toHaveCount(1);
    expect(queryFirst('.ayp_artifacts_panel .ayp_artifacts_empty')).toBe(null);
});

test('attachments dedupe by id across pending + events', async () => {
    const session = makeSession({
        pendingAttachments: [{ id: 5, filename: 'one.png', mimetype: 'image/png' }],
        events: [
            {
                kind: 'user_message',
                content: 'hi',
                attachments: [
                    { id: 5, filename: 'one.png', mimetype: 'image/png' },
                    { id: 6, filename: 'two.png', mimetype: 'image/png' },
                ],
            },
        ],
    });
    await mountPanel(session);
    const cards = queryAll('.ayp_artifacts_panel .ayp_att_card');
    expect(cards.length).toBe(2);
});
