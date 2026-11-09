# -*- coding: utf-8 -*-
"""
Idempotent Seeding Script for Al Ahram Cookware Odoo 20 Enterprise E2E Demo
Execution:
    docker compose exec -T odoo /usr/bin/odoo shell -c /etc/odoo/odoo.conf -d odoo20 < /mnt/ALAhram/scripts/seed_alahram_demo_data.py
"""
import logging

_logger = logging.getLogger('alahram_seeder')
print("\n" + "="*80)
print("🚀 Starting Al Ahram Cookware Demo Data Seeder (Odoo 20 Enterprise)")
print("="*80)

# 1. Update Passwords for all 7 Demo Users
users_data = {
    'owner@alahram.com': 'alahram2026',
    'ops.manager@alahram.com': 'alahram2026',
    'bm.sidigaber@alahram.com': 'alahram2026',
    'sales.sidigaber@alahram.com': 'alahram2026',
    'cashier1.sidigaber@alahram.com': 'alahram2026',
    'cashier2.sidigaber@alahram.com': 'alahram2026',
    'warehouse.roshdy@alahram.com': 'alahram2026',
}

ResUsers = env['res.users']
for login, pwd in users_data.items():
    user = ResUsers.search([('login', '=', login)], limit=1)
    if user:
        user.password = pwd
        print(f"✅ Set password for demo user: {login} ({user.name})")

# 2. Locate / Ensure Sidi Gaber Showroom & Backroom Locations
Warehouse = env['stock.warehouse']
Location = env['stock.location']

wh_sg = Warehouse.search([('code', '=', 'WH-SG')], limit=1)
wh_main = Warehouse.search([('code', '=', 'WH-MAIN')], limit=1)
wh_roshdy = Warehouse.search([('code', '=', 'WH-ROSHDY')], limit=1)

if not wh_sg:
    raise RuntimeError("WH-SG (Sidi Gaber) not found!")

# Find or create Showroom and Backroom sub-locations under WH-SG Stock
loc_sg_stock = wh_sg.lot_stock_id

loc_showroom = Location.search([
    ('name', '=', 'Showroom'),
    ('location_id', '=', loc_sg_stock.id)
], limit=1)
if not loc_showroom:
    loc_showroom = Location.create({
        'name': 'Showroom',
        'location_id': loc_sg_stock.id,
        'usage': 'internal',
    })
print(f"✅ Verified Showroom location: {loc_showroom.complete_name}")

loc_backroom = Location.search([
    ('name', '=', 'Backroom'),
    ('location_id', '=', loc_sg_stock.id)
], limit=1)
if not loc_backroom:
    loc_backroom = Location.create({
        'name': 'Backroom',
        'location_id': loc_sg_stock.id,
        'usage': 'internal',
    })
print(f"✅ Verified Backroom location: {loc_backroom.complete_name}")

# Specific Backroom Bin for Item #42
loc_backroom_bin_tray = Location.search([
    ('name', '=', 'الممر 4 - الرف 2 - م1'),
    ('location_id', '=', loc_backroom.id)
], limit=1)
if not loc_backroom_bin_tray:
    loc_backroom_bin_tray = Location.create({
        'name': 'الممر 4 - الرف 2 - م1',
        'location_id': loc_backroom.id,
        'usage': 'internal',
    })

# 3. Seed Exact Product Balances (Table 3.D)
# Format: (barcode, main_wh_qty, sg_showroom_qty, sg_backroom_qty, roshdy_qty)
stock_distribution = [
    # 1. طقم ماكس 30ق
    ('6221049410474', 0, 1, 1, 1),
    # 2. طقم صحي ومفيد 16ق
    ('6221049300409', 0, 1, 2, 3),
    # 3. طقم وايركات 16ق
    ('6221049303509', 0, 1, 0, 1),
    # 4. طقم وايركات 10ق (عجز سيدي جابر = 0)
    ('6221049430625', 0, 0, 0, 2),
    # 5. طقم صحي ومفيد 10ق
    ('6221049428172', 2, 2, 2, 3),
    # 6. طقم صحي ومفيد 6ق
    ('6221049432001', 0, 0, 0, 2),
    # 7. طقم ستانلس ترنتو 10ق
    ('6221049431738', 0, 1, 0, 0),
    # 8. طقم ستانلس لارج 10ق
    ('6221049431721', 0, 1, 0, 0),
    # 9. طقم ستانلس 6ق
    ('1433000000050', 34, 2, 3, 22),
    # 10. طقم جرانيت 9ق بيج
    ('1430000003784', 0, 1, 0, 0),
    # 11. طقم جرانيت 7ق سماوي
    ('1430000003975', 0, 1, 1, 1),
    # 12. طقم تيفال 9ق أسود
    ('1430000003630', 0, 2, 2, 1),
    # 13. حلة ألومنيوم 16
    ('6221049011664', 6, 1, 1, 7),
    # 14. حلة ألومنيوم 18
    ('6221049011671', 8, 1, 1, 4),
    # 15. حلة ألومنيوم 20
    ('6221049011688', 7, 2, 2, 3),
    # 16. حلة ألومنيوم 22
    ('6221049011695', 1, 1, 2, 4),
    # 17. حلة ألومنيوم 24 (عجز سيدي جابر = 0)
    ('6221049011701', 3, 0, 0, 3),
    # 18. حلة ألومنيوم 26
    ('6221049011718', 0, 0, 0, 2),
    # 19. حلة ألومنيوم 30
    ('6221049011732', 0, 1, 0, 2),
    # 20. حلة ستانلس 18
    ('1433000000029', 28, 2, 3, 34),
    # 23. حلة ستانلس 24 (راكد)
    ('1433000000067', 221, 2, 5, 48),
    # 27. حلة جرانيت 24 (راكد)
    ('1414000000035', 233, 2, 3, 9),
    # 31. مقلاية جرانيت 20 (عجز سيدي جابر = 0، مبيعات 107)
    ('6221049803894', 27, 0, 0, 0),
    # 32. مقلاية جرانيت 24 (الأول مبيعاً: 232)
    ('6221049803900', 14, 2, 10, 1),
    # 33. مقلاية جرانيت 28 (الثاني مبيعاً: 171)
    ('6221049803917', 9, 2, 10, 2),
    # 35. شواية جرانيت 28 (راكد 438)
    ('1414000000042', 279, 2, 11, 35),
    # 39. صينية فرن 30 (مرشح عروض: 580)
    ('1414000000073', 484, 2, 2, 16),
    # 42. طقم طاجن 3ق (0 بالمعرض و6 بالمخزن الخلفي)
    ('6221049430762', 6, 0, 6, 5),
    # 43. طقم صينية 3ق
    ('6221049302519', 0, 2, 3, 4),
    # 45. صينية بيتزا 30 (راكد 266)
    ('1431000000124', 210, 2, 2, 4),
    # 46. كسرولة ستانلس 16
    ('1433000000005', 13, 2, 4, 29),
    # 49. طقم جوانتي وماسك
    ('1474000000527', 39, 8, 10, 32),
    # 50. طقم سيليكون 2ق
    ('1474000002552', 208, 2, 3, 3),
    # 51. طقم شاورما 5ق (راكد 63)
    ('1431000000278', 63, 0, 0, 0),
]

ProductProduct = env['product.product']
StockQuant = env['stock.quant']

seeded_count = 0
for barcode, q_main, q_sg_show, q_sg_back, q_roshdy in stock_distribution:
    prod = ProductProduct.search([('barcode', '=', barcode)], limit=1)
    if not prod:
        continue

    # Set quantities using StockQuant._update_available_quantity
    if q_main > 0 and wh_main:
        StockQuant._update_available_quantity(prod, wh_main.lot_stock_id, q_main)
    if q_sg_show > 0:
        StockQuant._update_available_quantity(prod, loc_showroom, q_sg_show)
    if q_sg_back > 0:
        target_back_loc = loc_backroom_bin_tray if barcode == '6221049430762' else loc_backroom
        StockQuant._update_available_quantity(prod, target_back_loc, q_sg_back)
    if q_roshdy > 0 and wh_roshdy:
        StockQuant._update_available_quantity(prod, wh_roshdy.lot_stock_id, q_roshdy)

    seeded_count += 1

print(f"✅ Seeded initial inventory balances for {seeded_count} products across warehouses.")

# 4. Verify Demo Customers
ResPartner = env['res.partner']
customer_bridal = ResPartner.search([('name', 'ilike', 'منال عبد الرحمن')], limit=1)
if not customer_bridal:
    customer_bridal = ResPartner.create({
        'name': 'منال عبد الرحمن (عروسة الإسكندرية)',
        'phone': '+20 100 1234567',
        'email': 'manal.bridal@example.com',
        'city': 'الإسكندرية',
        'customer_rank': 1,
    })
print(f"✅ Verified Bridal Customer: {customer_bridal.name}")

# Commit changes to database
env.cr.commit()
print("="*80)
print("🎉 Al Ahram Cookware Seeding Completed Successfully!")
print("="*80)

