import odoo
from odoo import api, SUPERUSER_ID
from odoo.tools import config
from odoo.modules.registry import Registry

config.parse_config(['-c', '/etc/odoo/odoo.conf'])
registry = Registry('odoo20')
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Products
    prods = env['product.template'].search([], limit=10)
    print("Products count:", env['product.template'].search_count([]))
    for p in prods:
        print(f"  {p.name} - Price: {p.list_price} - Categ: {p.categ_id.name}")
        
    # Bridal packages
    if 'alahram.bridal.package' in env:
        packages = env['alahram.bridal.package'].search([])
        print("\nBridal packages count:", len(packages))
        for pkg in packages:
            print(f"  {pkg.name} - Tier: {pkg.tier} - Price: {pkg.target_price}")
            
    # Warehouses
    whs = env['stock.warehouse'].search([])
    print("\nWarehouses count:", len(whs))
    for w in whs[:5]:
        print(f"  {w.name} ({w.code})")
        
    # Sales
    print("\nSales orders count:", env['sale.order'].search_count([]))
    print("POS orders count:", env['pos.order'].search_count([]))

