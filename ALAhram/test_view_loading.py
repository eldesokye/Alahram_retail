import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'odoo20'])
registry = Registry('odoo20')

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    model = env['alahram.stock.recommendation']
    
    # Test get_views for kanban, list, form
    views_info = model.get_views([(False, 'kanban'), (False, 'list'), (False, 'form')])
    print("✅ get_views SUCCESS!")
    print("Available views:", list(views_info['views'].keys()))
    kanban_arch = views_info['views']['kanban']['arch']
    print("Kanban arch contains '<t t-name=\"card\">':", '<t t-name="card">' in kanban_arch)

