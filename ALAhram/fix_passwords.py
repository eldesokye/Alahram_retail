import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'odoo20'])
registry = Registry('odoo20')

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # 1. Update user 43 (Owner)
    u_owner = env['res.users'].browse(43)
    u_owner.write({'login': 'owner@alahram.com', 'password': 'owner'})
    print(f"Updated Owner: id={u_owner.id}, login={u_owner.login}")

    # 2. Update user 44 (Operations Manager)
    u_ops = env['res.users'].browse(44)
    u_ops.write({'login': 'ops.manager@alahram.com', 'password': 'operations'})
    print(f"Updated Ops Manager: id={u_ops.id}, login={u_ops.login}")

    # 3. Update user 45 (Branch Manager Sidi Gaber)
    u_bm = env['res.users'].browse(45)
    u_bm.write({'login': 'manager.sg@alahram.com', 'password': 'manager'})
    print(f"Updated Branch Manager: id={u_bm.id}, login={u_bm.login}")

    # 4. Update user 46 (Salesperson Sidi Gaber)
    u_sales = env['res.users'].browse(46)
    u_sales.write({'login': 'salesperson.sg@alahram.com', 'password': 'salesperson'})
    print(f"Updated Salesperson: id={u_sales.id}, login={u_sales.login}")

    # 5. Update user 47 (Cashier 1 Sidi Gaber)
    u_cashier = env['res.users'].browse(47)
    u_cashier.write({'login': 'cashier1@alahram.com', 'password': 'cashier1'})
    print(f"Updated Cashier: id={u_cashier.id}, login={u_cashier.login}")

    # 6. Update user 2 (Admin)
    u_admin = env['res.users'].browse(2)
    u_admin.write({'login': 'admin', 'password': 'admin'})
    print(f"Updated Admin: id={u_admin.id}, login={u_admin.login}")

    cr.commit()

# Now test authentication for each user!
print("\n--- TESTING AUTHENTICATION ---")
credentials = [
    ('admin', 'admin'),
    ('owner@alahram.com', 'owner'),
    ('ops.manager@alahram.com', 'operations'),
    ('manager.sg@alahram.com', 'manager'),
    ('salesperson.sg@alahram.com', 'salesperson'),
    ('cashier1@alahram.com', 'cashier1'),
]

for login, password in credentials:
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        auth_res = env['res.users'].authenticate({'type': 'password', 'login': login, 'password': password}, {})
        print(f"✅ Auth SUCCESS for '{login}' -> Result: {auth_res}")
