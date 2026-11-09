import odoo
from odoo import api, SUPERUSER_ID
from odoo.tools import config
from odoo.modules.registry import Registry

config.parse_config(['-c', '/etc/odoo/odoo.conf'])
registry = Registry('odoo20')
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    Channel = env['discuss.channel']
    ch25 = Channel.browse(25)
    print("Channel 25:", ch25.name, ch25.channel_type)
    print("Fields in discuss.channel:")
    for f in ch25._fields:
        if 'ai' in f or 'agent' in f or 'session' in f or 'bot' in f:
            print(f"  {f}: {getattr(ch25, f, None)}")

