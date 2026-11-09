from __future__ import annotations

from .api import api_method


@api_method('usage.summary')
def usage_summary(env):
    Session = env['aypatech_wooai.session']
    rows = Session.search_read(
        [],
        ['agent_id', 'user_id', 'total_cost', 'total_input_tokens', 'total_output_tokens'],
        limit=5000,
        order='id desc',
    )
    by_agent: dict[str, dict] = {}
    by_user: dict[str, dict] = {}
    total_cost = 0.0
    total_tokens = 0
    for row in rows:
        cost = row['total_cost'] or 0.0
        tokens = (row['total_input_tokens'] or 0) + (row['total_output_tokens'] or 0)
        total_cost += cost
        total_tokens += tokens
        agent = row['agent_id'][1] if row['agent_id'] else '-'
        user = row['user_id'][1] if row['user_id'] else '-'
        slot = by_agent.setdefault(agent, {'name': agent, 'cost': 0.0, 'tokens': 0, 'sessions': 0})
        slot['cost'] += cost
        slot['tokens'] += tokens
        slot['sessions'] += 1
        slot = by_user.setdefault(user, {'name': user, 'cost': 0.0, 'tokens': 0, 'sessions': 0})
        slot['cost'] += cost
        slot['tokens'] += tokens
        slot['sessions'] += 1
    return {
        'total_cost': total_cost,
        'total_tokens': total_tokens,
        'session_count': len(rows),
        'by_agent': sorted(by_agent.values(), key=lambda r: -r['cost']),
        'by_user': sorted(by_user.values(), key=lambda r: -r['cost']),
    }
