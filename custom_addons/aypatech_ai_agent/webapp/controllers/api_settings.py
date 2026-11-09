from __future__ import annotations

from odoo.exceptions import UserError

from .api import api_method


def _provider(env, provider_id):
    provider = env['aypatech_wooai.provider'].browse(int(provider_id)).exists()
    if not provider:
        raise UserError(env._('This provider no longer exists.'))
    return provider


def _provider_row(provider):
    return {
        'id': provider.id,
        'name': provider.name,
        'label': provider.display_name,
        'active': provider.active,
        'has_key': bool(provider.sudo().api_key),
        'base_url': provider.base_url or '',
        'default_model_id': provider.default_model_id.id,
        'default_model_name': provider.default_model_id.name or '',
        'model_count': len(provider.model_ids),
        'last_test_ok': provider.last_test_ok,
        'last_test_message': provider.last_test_message or '',
        'last_tested_at': str(provider.last_tested_at) if provider.last_tested_at else None,
    }


@api_method('settings.providers')
def settings_providers(env):
    providers = env['aypatech_wooai.provider'].search([], order='sequence, name')
    return [_provider_row(p) for p in providers]


@api_method('settings.provider_models')
def settings_provider_models(env, provider_id):
    provider = _provider(env, provider_id)
    return [
        {'id': m.id, 'name': m.name, 'technical_name': m.technical_name}
        for m in provider.model_ids
    ]


@api_method('settings.provider_save', group='admin')
def settings_provider_save(env, provider_id, api_key=None, base_url=None, default_model_id=None, active=None):
    provider = _provider(env, provider_id)
    vals = {}
    if api_key is not None and api_key.strip():
        vals['api_key'] = api_key.strip()
    if base_url is not None:
        vals['base_url'] = base_url.strip() or False
    if default_model_id is not None:
        vals['default_model_id'] = int(default_model_id) or False
    if active is not None:
        vals['active'] = bool(active)
    if vals:
        provider.sudo().write(vals)
    return _provider_row(provider)


@api_method('settings.provider_test', group='admin')
def settings_provider_test(env, provider_id):
    provider = _provider(env, provider_id)
    ok, message = provider.test_connection()
    return {'ok': ok, 'message': message}


def _agent_row(agent):
    return {
        'id': agent.id,
        'name': agent.name,
        'description': agent.description or '',
        'active': agent.active,
        'model_id': agent.model_id.id,
        'model_name': agent.model_id.name or '',
        'approval_mode': agent.approval_mode,
        'allow_handoff': agent.allow_handoff,
    }


@api_method('settings.agents')
def settings_agents(env):
    agents = env['aypatech_wooai.agent'].search([], order='sequence, name')
    return [_agent_row(a) for a in agents]


@api_method('settings.agent_save', group='admin')
def settings_agent_save(env, agent_id=None, name=None, description=None, system_prompt=None, active=None):
    Agent = env['aypatech_wooai.agent']
    vals = {}
    if name is not None:
        vals['name'] = name.strip()
    if description is not None:
        vals['description'] = description
    if system_prompt is not None:
        vals['system_prompt'] = system_prompt
    if active is not None:
        vals['active'] = bool(active)
    if agent_id:
        agent = Agent.browse(int(agent_id)).exists()
        if not agent:
            raise UserError(env._('This agent no longer exists.'))
        if vals:
            agent.write(vals)
    else:
        if not vals.get('name'):
            raise UserError(env._('Name the agent first.'))
        agent = Agent.create(vals)
    return _agent_row(agent)


@api_method('settings.agent_delete', group='admin')
def settings_agent_delete(env, agent_id):
    agent = env['aypatech_wooai.agent'].browse(int(agent_id)).exists()
    if agent:
        agent.active = False
    return True
