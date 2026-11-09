import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'odoo20'])
registry = Registry('odoo20')

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    RecModel = env['alahram.stock.recommendation']
    
    # Find or seed recommendations
    RecModel.action_seed_demo_recommendations()
    urgent_rec = RecModel.search([('priority', '=', 'urgent'), ('state', '=', 'pending')], limit=1)
    if not urgent_rec:
        urgent_rec = RecModel.search([('state', '=', 'pending')], limit=1)
    
    print(f"Testing recommendation: {urgent_rec.name} with priority: {urgent_rec.priority}")
    
    # Simulate web client context with default_priority='urgent' and group_by='priority'
    web_context = {
        'default_priority': 'urgent',
        'group_by': 'priority',
        'active_model': 'alahram.stock.recommendation',
        'active_id': urgent_rec.id,
    }
    
    # Execute action_approve_recommendation with simulated web context!
    res = urgent_rec.with_context(web_context).action_approve_recommendation()
    print("✅ action_approve_recommendation SUCCESS!")
    print(f"Result Action: {res.get('name')}, Res ID (Picking ID): {res.get('res_id')}")
    
    picking = env['stock.picking'].browse(res['res_id'])
    print(f"Created Picking: {picking.name}, State: {picking.state}, Priority: {picking.priority}")
    cr.commit()

