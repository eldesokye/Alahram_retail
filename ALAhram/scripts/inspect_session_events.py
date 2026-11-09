import odoo
from odoo import api, SUPERUSER_ID
from odoo.tools import config
from odoo.modules.registry import Registry

config.parse_config(['-c', '/etc/odoo/odoo.conf'])
registry = Registry('odoo20')
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    session = env['ai.session'].browse(19)
    print("Session 19 loop_state:", session.loop_state)
    print("Session 19 events:")
    for ev in session.event_ids:
        print(f"  Event {ev.id}: type={getattr(ev, 'event_type', None)}, name={getattr(ev, 'name', None)}")
        for ef in ev._fields:
            v = getattr(ev, ef, None)
            if v and ef not in ('create_uid', 'write_uid', 'create_date', 'write_date'):
                print(f"    {ef}: {v}")

