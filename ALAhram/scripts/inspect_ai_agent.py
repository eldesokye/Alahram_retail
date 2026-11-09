import odoo
from odoo import api, SUPERUSER_ID
from odoo.tools import config
from odoo.modules.registry import Registry

config.parse_config(['-c', '/etc/odoo/odoo.conf'])
registry = Registry('odoo20')
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    agent = env['ai.agent'].browse(1)
    print("AI Agent 1:", agent.name)
    for f in agent._fields:
        val = getattr(agent, f, None)
        if isinstance(val, (str, int, float, bool)):
            print(f"  {f}: {val}")
        elif hasattr(val, '_name'):
            print(f"  {f}: {val._name}({val.ids})")
            
    session = env['ai.session'].browse(19)
    print("\nSession 19:")
    for f in session._fields:
        val = getattr(session, f, None)
        if isinstance(val, (str, int, float, bool)):
            print(f"  {f}: {val}")
        elif hasattr(val, '_name'):
            print(f"  {f}: {val._name}({val.ids})")

