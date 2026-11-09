from __future__ import annotations

from odoo.exceptions import UserError

from .api import api_method

TRIGGER_OPTIONS = [
    ('on_create', 'On Creation'),
    ('on_create_or_write', 'On Creation or Update'),
    ('on_time', 'Based on a Date Field'),
]


def _rule(env, rule_id):
    rule = env['base.automation'].browse(int(rule_id)).exists()
    if not rule:
        raise UserError(env._('This automation rule no longer exists.'))
    return rule


def _agent_action(rule):
    return rule.action_server_ids.filtered(lambda a: a.state == 'wooai_agent')[:1]


def _rule_row(rule):
    action = _agent_action(rule)
    trigger_label = dict(TRIGGER_OPTIONS).get(rule.trigger, rule.trigger)
    return {
        'id': rule.id,
        'name': rule.name,
        'active': rule.active,
        'model': rule.model_id.model,
        'model_name': rule.model_id.name,
        'trigger': rule.trigger,
        'trigger_label': trigger_label,
        'filter_domain': rule.filter_domain or '',
        'trg_date_field': rule.trg_date_id.name or '',
        'trg_date_range': rule.trg_date_range,
        'trg_date_range_mode': rule.trg_date_range_mode,
        'trg_date_range_type': rule.trg_date_range_type,
        'agent_id': action.agent_id.id if action else False,
        'agent_name': action.agent_id.display_name if action else '',
        'prompt': action.wooai_agent_prompt if action else '',
        'dispatch_mode': action.wooai_agent_dispatch_mode if action else 'single',
        'action_id': action.id if action else False,
    }


@api_method('automation.rules', group='admin')
def automation_rules(env):
    actions = env['ir.actions.server'].search([('state', '=', 'wooai_agent'), ('base_automation_id', '!=', False)])
    rules = actions.mapped('base_automation_id')
    return [_rule_row(r) for r in rules]


@api_method('automation.models', group='admin')
def automation_models(env, query=None):
    domain = [('transient', '=', False), ('abstract', '=', False)]
    if query:
        domain += ['|', ('model', 'ilike', query), ('name', 'ilike', query)]
    models = env['ir.model'].search(domain, limit=50, order='model')
    return [{'model': m.model, 'name': m.name} for m in models]


@api_method('automation.model_fields', group='admin')
def automation_model_fields(env, model, date_only=False):
    if model not in env:
        return []
    domain = [('model', '=', model)]
    if date_only:
        domain.append(('ttype', 'in', ('date', 'datetime')))
    fields = env['ir.model.fields'].search(domain, order='field_description', limit=200)
    return [{'name': f.name, 'label': f.field_description, 'type': f.ttype} for f in fields]


@api_method('automation.rule_save', group='admin')
def automation_rule_save(
    env, rule_id=None, name=None, model=None, trigger=None, filter_domain=None,
    trg_date_field=None, trg_date_range=None, trg_date_range_mode=None, trg_date_range_type=None,
    agent_id=None, prompt=None, dispatch_mode=None,
):
    IrModel = env['ir.model']
    Automation = env['base.automation']
    ActionServer = env['ir.actions.server']

    if rule_id:
        rule = _rule(env, rule_id)
        action = _agent_action(rule)
    else:
        if not (name and model and trigger and agent_id and prompt):
            raise UserError(env._('Name, model, trigger, agent and prompt are required.'))
        rule = Automation
        action = ActionServer

    model_rec = IrModel.search([('model', '=', model)], limit=1) if model else (rule.model_id if rule else IrModel)
    if model and not model_rec:
        raise UserError(env._('Unknown model: %(model)s', model=model))

    automation_vals = {}
    if name is not None:
        automation_vals['name'] = name
    if model_rec:
        automation_vals['model_id'] = model_rec.id
    if trigger is not None:
        automation_vals['trigger'] = trigger
    if filter_domain is not None:
        automation_vals['filter_domain'] = filter_domain or False
    if trigger == 'on_time':
        if trg_date_field:
            field_rec = env['ir.model.fields'].search(
                [('model_id', '=', model_rec.id), ('name', '=', trg_date_field)], limit=1)
            automation_vals['trg_date_id'] = field_rec.id if field_rec else False
        automation_vals['trg_date_range'] = int(trg_date_range or 0)
        automation_vals['trg_date_range_mode'] = trg_date_range_mode or 'after'
        automation_vals['trg_date_range_type'] = trg_date_range_type or 'day'

    action_vals = {'state': 'wooai_agent', 'usage': 'base_automation'}
    if name is not None:
        action_vals['name'] = name
    if model_rec:
        action_vals['model_id'] = model_rec.id
    if agent_id is not None:
        action_vals['agent_id'] = int(agent_id)
    if prompt is not None:
        action_vals['wooai_agent_prompt'] = prompt
    if dispatch_mode is not None:
        action_vals['wooai_agent_dispatch_mode'] = dispatch_mode

    if rule_id:
        rule.write(automation_vals)
        if action:
            action.write(action_vals)
        else:
            action_vals['base_automation_id'] = rule.id
            ActionServer.create(action_vals)
    else:
        automation_vals.setdefault('model_id', model_rec.id)
        rule = Automation.create(automation_vals)
        action_vals['base_automation_id'] = rule.id
        ActionServer.create(action_vals)

    return _rule_row(rule)


@api_method('automation.rule_toggle', group='admin')
def automation_rule_toggle(env, rule_id):
    rule = _rule(env, rule_id)
    rule.active = not rule.active
    return _rule_row(rule)


@api_method('automation.rule_delete', group='admin')
def automation_rule_delete(env, rule_id):
    rule = _rule(env, rule_id)
    rule.unlink()
    return True
