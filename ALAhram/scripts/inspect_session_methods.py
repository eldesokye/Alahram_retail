import odoo
from odoo import api, SUPERUSER_ID
from odoo.tools import config
from odoo.modules.registry import Registry

config.parse_config(['-c', '/etc/odoo/odoo.conf'])
registry = Registry('odoo20')
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Session = env['ai.session']
    methods = [m for m in dir(Session) if not m.startswith('__') and ('step' in m or 'turn' in m or 'exec' in m or 'run' in m or 'loop' in m or 'process' in m or 'message' in m or 'post' in m or 'generate' in m or 'respond' in m or 'reply' in m)]
    print("Methods matching in ai.session:", methods)
    
    # Also let's inspect discuss.channel methods related to ai
    Channel = env['discuss.channel']
    ch_methods = [m for m in dir(Channel) if not m.startswith('__') and 'ai' in m]
    print("Channel AI methods:", ch_methods)

