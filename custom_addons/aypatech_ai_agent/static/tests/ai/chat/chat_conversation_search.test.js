import { describe, expect, test } from '@odoo/hoot';
import { press, queryAll, queryFirst } from '@odoo/hoot-dom';
import { advanceTime, animationFrame } from '@odoo/hoot-mock';
import { mockService, mountWithCleanup, onRpc } from '@web/../tests/web_test_helpers';
import { defineMailModels } from '@mail/../tests/mail_test_helpers';

import { AIChat } from '@aypatech_ai_agent/ai/chat/chat';
import { ChatSearch } from '@aypatech_ai_agent/ai/chat/search/chat_search';

describe.current.tags('aypatech_wooai');
defineMailModels();

const EVENTS = [
    { event_id: 1, kind: 'user_message', content: 'alpha and alpha', attachments: [] },
    { event_id: 2, kind: 'text', content: 'the **alpha** report' },
    { event_id: 3, kind: 'user_message', content: 'beta only', attachments: [] },
];

const SESSION_RECORD = {
    id: 7,
    name: 'Demo session',
    state: 'done',
    pending_ask: null,
    view_context: null,
    last_text: '',
    error_message: null,
    iteration_count: 1,
    total_input_tokens: 0,
    total_output_tokens: 0,
    last_input_tokens: 0,
    context_window: 8000,
    total_cost: 0,
    user_id: false,
    agent_id: false,
    override_approval_mode: false,
    effective_approval_mode: 'ask',
    pending_user_messages: [],
};

function baseMocks() {
    onRpc('aypatech_wooai.session', 'search_read', () => [
        { id: 7, name: 'Demo', state: 'done', create_date: '2026-04-20 10:00:00' },
    ]);
    onRpc('aypatech_wooai.session', 'read', ({ args }) => [
        { ...SESSION_RECORD, id: args[0][0] },
    ]);
    onRpc('aypatech_wooai.session', 'get_snapshot', () => ({
        id: 7,
        state: 'done',
        events: EVENTS,
        oldest_sequence: null,
        has_more_older: false,
        pending_ask: null,
        view_context: null,
        error_message: null,
        iteration_count: 1,
        total_input_tokens: 0,
        total_output_tokens: 0,
        total_cost: 0,
        last_input_tokens: 0,
        context_window: 8000,
        override_approval_mode: false,
        effective_approval_mode: 'ask',
        pending_user_messages: [],
    }));
    onRpc('aypatech_wooai.agent', 'search_read', () => []);
    onRpc('aypatech_wooai.space', 'fetch_spaces', () => []);
    onRpc('aypatech_wooai.space', 'fetch_general_domain', () => [['space_id', '=', false]]);
    mockService('aypatech_ai_agent.ai_chat_window', {
        state: { windows: [] },
        open: () => {},
        close: () => {},
        toggleMinimized: () => {},
        get activeSessionId() {
            return null;
        },
    });
    mockService('bus_service', {
        addChannel() {},
        deleteChannel() {},
        subscribe() {},
        unsubscribe() {},
    });
    mockService('notification', { add: () => {} });
}

async function mountChat() {
    baseMocks();
    const chat = await mountWithCleanup(AIChat, { props: {} });
    await chat.onSelectSession(7);
    await animationFrame();
    return chat;
}

test('searching highlights every occurrence and scrolls to the first one', async () => {
    const chat = await mountChat();
    chat.toggleSearch();
    await animationFrame();
    chat.onSearchChange('alpha');
    await animationFrame();
    expect(chat.searchMatches).toHaveLength(3);
    expect(chat.searchIndex).toHaveLength(3);
    expect(chat.state.activeMatchIdx).toBe(0);
    expect(chat.state.scrollTarget).toBe(null);
    expect(queryAll('mark.ayp_search_hit, mark.ayp_search_hit_active')).toHaveLength(3);
    expect(queryAll('mark.ayp_search_hit_active')).toHaveLength(1);
    expect(queryFirst('.ayp_search_pulse')).not.toBe(null);
});

test('the scroll pulse is cleared again so it cannot pile up', async () => {
    const chat = await mountChat();
    chat.toggleSearch();
    chat.onSearchChange('alpha');
    await animationFrame();
    expect(queryFirst('.ayp_search_pulse')).not.toBe(null);
    await advanceTime(700);
    expect(queryFirst('.ayp_search_pulse')).toBe(null);
});

test('the active highlight follows next and wraps around', async () => {
    const chat = await mountChat();
    chat.toggleSearch();
    chat.onSearchChange('alpha');
    await animationFrame();
    chat.onSearchNext();
    await animationFrame();
    expect(chat.state.activeMatchIdx).toBe(1);
    expect(queryFirst('mark.ayp_search_hit_active').textContent).toBe('alpha');
    chat.onSearchNext();
    chat.onSearchNext();
    await animationFrame();
    expect(chat.state.activeMatchIdx).toBe(0);
});

test('previous wraps to the last match', async () => {
    const chat = await mountChat();
    chat.toggleSearch();
    chat.onSearchChange('alpha');
    await animationFrame();
    chat.onSearchPrev();
    await animationFrame();
    expect(chat.state.activeMatchIdx).toBe(2);
    expect(chat.state.scrollTarget).toBe(null);
});

test('a query with no hit clears the scroll target and renders no marks', async () => {
    const chat = await mountChat();
    chat.toggleSearch();
    chat.onSearchChange('gamma');
    await animationFrame();
    expect(chat.searchMatches).toEqual([]);
    expect(chat.state.scrollTarget).toBe(null);
    expect(queryAll('mark.ayp_search_hit, mark.ayp_search_hit_active')).toHaveLength(0);
    chat.onSearchNext();
    chat.onSearchPrev();
    expect(chat.state.activeMatchIdx).toBe(0);
});

test('closing the search drops the query and the highlights', async () => {
    const chat = await mountChat();
    chat.toggleSearch();
    chat.onSearchChange('alpha');
    await animationFrame();
    expect(queryAll('mark.ayp_search_hit, mark.ayp_search_hit_active').length).toBe(3);
    chat.toggleSearch();
    await animationFrame();
    expect(chat.state.searchOpen).toBe(false);
    expect(chat.state.searchQuery).toBe('');
    expect(chat.state.activeMatchIdx).toBe(0);
    expect(queryAll('mark.ayp_search_hit, mark.ayp_search_hit_active')).toHaveLength(0);
});

test('search results are memoised per turn list and query', async () => {
    const chat = await mountChat();
    chat.toggleSearch();
    chat.onSearchChange('alpha');
    await animationFrame();
    const matches = chat.searchMatches;
    const index = chat.searchIndex;
    expect(chat.searchMatches).toBe(matches);
    expect(chat.searchIndex).toBe(index);
    chat.onSearchChange('beta');
    await animationFrame();
    expect(chat.searchMatches).not.toBe(matches);
});

test('an out-of-range active index is clamped to the match list', async () => {
    const chat = await mountChat();
    chat.toggleSearch();
    chat.onSearchChange('alpha');
    await animationFrame();
    chat.state.activeMatchIdx = 9;
    expect(chat.clampedActiveMatchIdx).toBe(2);
    chat.state.activeMatchIdx = -3;
    expect(chat.clampedActiveMatchIdx).toBe(0);
    chat.state.activeMatchIdx = 1;
    expect(chat.clampedActiveMatchIdx).toBe(1);
});

test('the index and matches stay empty while the search bar is closed', async () => {
    const chat = await mountChat();
    chat.state.searchQuery = 'alpha';
    expect(chat.searchIndex).toEqual([]);
    expect(chat.searchMatches).toEqual([]);
    expect(chat.clampedActiveMatchIdx).toBe(0);
});

test('unsearched text is rendered verbatim and null becomes empty', async () => {
    const chat = await mountChat();
    expect(chat.renderUserText('a < b')).toBe('a < b');
    expect(chat.renderUserText(null)).toBe('');
    expect(String(chat.renderAssistantMarkdown('**bold**'))).toMatch(
        /<strong>bold<\/strong>/,
    );
});

test('ChatSearch reports its position and closes on Escape', async () => {
    const events = [];
    await mountWithCleanup(ChatSearch, {
        props: {
            query: 'alpha',
            total: 3,
            currentIdx: 1,
            onChange: (value) => events.push(['change', value]),
            onPrev: () => events.push(['prev']),
            onNext: () => events.push(['next']),
            onClose: () => events.push(['close']),
        },
    });
    expect(queryFirst('.ayp_search_counter').textContent).toBe('2 of 3');
    await press('Escape');
    expect(events).toEqual([['close']]);
});

test('ChatSearch steps through matches with Enter and Shift+Enter', async () => {
    const events = [];
    await mountWithCleanup(ChatSearch, {
        props: {
            query: 'alpha',
            total: 2,
            currentIdx: 0,
            onChange: (value) => events.push(['change', value]),
            onPrev: () => events.push(['prev']),
            onNext: () => events.push(['next']),
            onClose: () => events.push(['close']),
        },
    });
    await press('Enter');
    await press(['Shift', 'Enter']);
    expect(events).toEqual([['next'], ['prev']]);
});

test('ChatSearch shows no counter until something is typed', async () => {
    const noop = () => {};
    await mountWithCleanup(ChatSearch, {
        props: {
            query: '',
            total: 0,
            currentIdx: 0,
            onChange: noop,
            onPrev: noop,
            onNext: noop,
            onClose: noop,
        },
    });
    expect(queryFirst('.ayp_search_counter').textContent).toBe('');
    expect(queryFirst('.ayp_search_next').disabled).toBe(true);
});

test('ChatSearch reports zero hits for a query that matches nothing', async () => {
    const noop = () => {};
    await mountWithCleanup(ChatSearch, {
        props: {
            query: 'zzz',
            total: 0,
            currentIdx: 0,
            onChange: noop,
            onPrev: noop,
            onNext: noop,
            onClose: noop,
        },
    });
    expect(queryFirst('.ayp_search_counter').textContent).toBe('0 of 0');
});
