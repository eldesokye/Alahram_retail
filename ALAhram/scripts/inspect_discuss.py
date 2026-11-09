import odoo
from odoo import api, SUPERUSER_ID
from odoo.tools import config
from odoo.modules.registry import Registry

config.parse_config(['-c', '/etc/odoo/odoo.conf'])
registry = Registry('odoo20')
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    channels = env['discuss.channel'].search([])
    for c in channels:
        print(f"Channel ID: {c.id}, Name: {c.name}, Type: {c.channel_type}")
        messages = env['mail.message'].search([('res_id', '=', c.id), ('model', '=', 'discuss.channel')], order='id desc', limit=5)
        for m in messages:
            print(f"   Msg {m.id} from {m.author_id.name}: {m.body}")
