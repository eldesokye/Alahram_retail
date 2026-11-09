from __future__ import annotations

from odoo.exceptions import UserError

from .api import api_method


def _session(env, session_id):
    session = env['aypatech_wooai.session'].browse(int(session_id)).exists()
    if not session:
        raise UserError(env._('This chat no longer exists.'))
    return session


def _session_row(session):
    return {
        'id': session.id,
        'name': session.name or session.agent_id.display_name or '',
        'state': session.state,
        'agent_id': session.agent_id.id,
        'agent_name': session.agent_id.display_name or '',
        'space_id': session.space_id.id if session.space_id else False,
        'last_text': (session.last_text or '')[:160],
        'write_date': str(session.write_date) if session.write_date else None,
    }


@api_method('bootstrap')
def bootstrap(env):
    user = env.user
    return {
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email or '',
            'avatar': '/web/image/res.users/%s/avatar_128' % user.id,
            'is_admin': user.has_group('base.group_system'),
        },
    }


@api_method('chat.spaces')
def chat_spaces(env):
    return env['aypatech_wooai.space'].fetch_spaces()


@api_method('chat.agents')
def chat_agents(env):
    agents = env['aypatech_wooai.agent'].search([('active', '=', True)], order='sequence, name')
    return [
        {'id': a.id, 'name': a.name, 'description': a.description or ''}
        for a in agents
    ]


@api_method('chat.sessions')
def chat_sessions(env, space_id=None, limit=50):
    domain = [('user_id', '=', env.uid)]
    if space_id:
        domain.append(('space_id', '=', int(space_id)))
    sessions = env['aypatech_wooai.session'].search(domain, order='write_date desc', limit=int(limit or 50))
    return [_session_row(s) for s in sessions]

@api_method('chat.create')
def chat_create(env, agent_id, space_id=None, message=None):
    agent = env['aypatech_wooai.agent'].browse(int(agent_id)).exists()
    if not agent or not agent.active:
        raise UserError(env._('Choose an agent first.'))
    vals = {'agent_id': agent.id}
    if space_id:
        vals['space_id'] = int(space_id)
    session = env['aypatech_wooai.session'].create(vals)
    if message:
        session.start(message)
    return _session_row(session)


@api_method('chat.send')
def chat_send(env, session_id, message):
    session = _session(env, session_id)
    if not (message or '').strip():
        raise UserError(env._('Type a message first.'))
    session.send_message(message.strip())
    return True


@api_method('chat.snapshot')
def chat_snapshot(env, session_id):
    session = _session(env, session_id)
    snapshot = session.get_snapshot(include_conversation=False)
    snapshot['agent_id'] = session.agent_id.id
    snapshot['agent_name'] = session.agent_id.display_name or ''
    snapshot['name'] = session.name or ''
    return snapshot


@api_method('chat.rename')
def chat_rename(env, session_id, name):
    session = _session(env, session_id)
    session.name = (name or '').strip()[:120] or session.name
    return True


@api_method('chat.delete')
def chat_delete(env, session_id):
    session = _session(env, session_id)
    session.unlink()
    return True
