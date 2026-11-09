import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'odoo20'])
registry = Registry('odoo20')

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    for uid in [2, 43, 44, 45, 46, 47]:
        u = env['res.users'].browse(uid)
        print(f"\nUser {u.name} (id={u.id}, login='{u.login}'):")
        group_names = [g.name for g in u.group_ids]
        print(f"  Groups ({len(group_names)}): {', '.join(group_names[:5])}...")
        
        for model in ['alahram.stock.recommendation', 'product.template', 'pos.order', 'alahram.ai.assistant', 'sale.order']:
            has_read = env[model].with_user(u).has_access('read')
            has_write = env[model].with_user(u).has_access('write')
            print(f"    Model {model}: read={has_read}, write={has_write}")
