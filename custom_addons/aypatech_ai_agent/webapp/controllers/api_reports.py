from __future__ import annotations

from odoo.exceptions import UserError

from .api import api_method


def _schedule(env, schedule_id):
    schedule = env['aypatech_wooai.report.schedule'].browse(int(schedule_id)).exists()
    if not schedule:
        raise UserError(env._('This report schedule no longer exists.'))
    return schedule


def _schedule_row(schedule):
    return {
        'id': schedule.id,
        'name': schedule.name,
        'active': schedule.active,
        'agent_id': schedule.agent_id.id,
        'agent_name': schedule.agent_id.display_name or '',
        'frequency': schedule.frequency,
        'next_run': str(schedule.next_run) if schedule.next_run else None,
        'last_run': str(schedule.last_run) if schedule.last_run else None,
        'telegram_enabled': schedule.telegram_enabled,
        'run_count': len(schedule.run_ids),
    }


@api_method('reports.schedules')
def reports_schedules(env):
    schedules = env['aypatech_wooai.report.schedule'].search([], order='next_run, id')
    return [_schedule_row(s) for s in schedules]


@api_method('reports.schedule_save', group='admin')
def reports_schedule_save(env, schedule_id=None, name=None, agent_id=None, prompt=None,
                          frequency=None, hour=None, active=None):
    Schedule = env['aypatech_wooai.report.schedule']
    vals = {}
    if name is not None:
        vals['name'] = name.strip()
    if agent_id is not None:
        vals['agent_id'] = int(agent_id)
    if prompt is not None:
        vals['prompt'] = prompt
    if frequency is not None:
        vals['frequency'] = frequency
    if hour is not None:
        vals['hour'] = int(hour)
    if active is not None:
        vals['active'] = bool(active)
    if schedule_id:
        schedule = _schedule(env, schedule_id)
        if vals:
            schedule.write(vals)
    else:
        if not vals.get('name') or not vals.get('agent_id') or not vals.get('prompt'):
            raise UserError(env._('Name, agent and prompt are required.'))
        schedule = Schedule.create(vals)
    return _schedule_row(schedule)


@api_method('reports.schedule_delete', group='admin')
def reports_schedule_delete(env, schedule_id):
    _schedule(env, schedule_id).unlink()
    return True


@api_method('reports.run_now', group='admin')
def reports_run_now(env, schedule_id):
    schedule = _schedule(env, schedule_id)
    schedule.run_now()
    return _schedule_row(schedule)


@api_method('reports.runs')
def reports_runs(env, schedule_id=None, limit=50):
    domain = []
    if schedule_id:
        domain.append(('schedule_id', '=', int(schedule_id)))
    runs = env['aypatech_wooai.report.run'].search(domain, order='id desc', limit=int(limit or 50))
    return [
        {
            'id': r.id,
            'name': r.name,
            'state': r.state,
            'create_date': str(r.create_date) if r.create_date else None,
            'sent_to': r.sent_to or '',
            'error': r.error or '',
        }
        for r in runs
    ]
