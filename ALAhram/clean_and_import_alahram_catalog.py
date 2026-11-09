# -*- coding: utf-8 -*-
"""
Alahram Enterprise Purge & Full Catalog Import
==============================================
1. Purges / deactivates all non-Alahram demo products (Clothes, Food, Furniture, etc.)
   and clears them completely from POS, Sales, and Inventory.
2. Creates the official Al-Ahram Cookware POS categories.
3. Imports the full scraped catalog from products_with_base64.csv into Odoo 20:
   - High-resolution product images (image_1920)
   - Real categories and descriptions
   - Correct pricing
   - POS activation with mapped categories
   - Showroom and Backroom warehouse stock quants
"""

import csv
import os
import re
import sys
from pathlib import Path

import odoo
from odoo.tools import config
from odoo.modules.registry import Registry

def determine_pos_category(name: str, cat_str: str) -> str:
    combined = f"{name} {cat_str}".lower()
    if "جرانيت" in combined or "granite" in combined:
        return "أطقم حلل جرانيت"
    if "ستانلس" in combined or "stainless" in combined or "زينوكس" in combined:
        return "أطقم ستانلس ستيل"
    if ("ألومنيوم" in combined or "aluminum" in combined) and any(w in combined for w in ["حلة", "حلل", "طقم", "pot"]):
        return "أواني ألومنيوم كلاسيك"
    if any(w in combined for w in ["صواني", "صينية", "طاجن", "قالب", "فرن", "بسكويت", "خبز", "bakeware", "roaster", "بيتزا"]):
        return "صواني وطواجن فرن"
    if any(w in combined for w in ["كريب", "مقلاية", "طاسة", "جريل", "pan", "fry"]):
        return "طاسات ومقالي كريب"
    if any(w in combined for w in ["خلاط", "بلندر", "مضرب", "أجهزة", "appliances", "beater", "blender"]):
        return "أجهزة كهربائية وخلاطات"
    if any(w in combined for w in ["معالق", "ملاعق", "سكين", "شوك", "مقص", "cutlery", "knife", "fork", "spoon", "scissors"]):
        return "أطقم ملاعق وسكاكين"
    if any(w in combined for w in ["سرفيس", "شاي", "قهوة", "تقديم", "كاس", "كوب", "زجاج", "جاتوه", "بورسلين", "tray", "jug", "cup", "tea"]):
        return "صواني تقديم وزجاجيات"
    return "إكسسوارات ومفروشات مطبخ"


def determine_material_type(name: str, desc: str) -> str:
    combined = f"{name} {desc}".lower()
    if "جرانيت" in combined or "granite" in combined:
        return "granite"
    if "ستانلس" in combined or "stainless" in combined or "زينوكس" in combined:
        return "stainless"
    if "تيفال" in combined or "tefal" in combined or "غير لاصق" in combined:
        return "tefal"
    accessories_keywords = [
        "مفرش", "مفروشات", "قماش", "سيرفيس", "خشب", "طقم قهوه", "طقم قهوة",
        "فنجان", "مقص", "سكين", "شوكة", "ملعقة", "مج", "بولة", "علبة ثلاجة",
        "حامل", "توابل", "سليكون", "مضرب", "خلاط", "لوفة", "فوطة", "مغرفة",
        "سباتولا", "طبق", "صينية تقديم", "بورسلين", "زجاج", "ملامين"
    ]
    for kw in accessories_keywords:
        if kw in combined:
            return "accessories"
    return "aluminum"


def get_or_create_internal_category(env, cat_path: str):
    Category = env["product.category"]
    parts = [p.strip() for p in cat_path.replace(">", "/").split("/") if p.strip()]
    if not parts:
        parts = ["منتجات الأهرام", "عام"]

    parent_id = False
    for part in parts:
        domain = [("name", "=", part)]
        if parent_id:
            domain.append(("parent_id", "=", parent_id))
        else:
            domain.append(("parent_id", "=", False))

        cat = Category.search(domain, limit=1)
        if not cat:
            cat = Category.create({"name": part, "parent_id": parent_id})
        parent_id = cat.id

    return Category.browse(parent_id)


def setup_pos_categories(env):
    PosCategory = env["pos.category"]
    categories = [
        "أطقم حلل جرانيت",
        "أطقم ستانلس ستيل",
        "أواني ألومنيوم كلاسيك",
        "صواني وطواجن فرن",
        "طاسات ومقالي كريب",
        "أجهزة كهربائية وخلاطات",
        "أطقم ملاعق وسكاكين",
        "صواني تقديم وزجاجيات",
        "إكسسوارات ومفروشات مطبخ",
    ]
    mapping = {}
    for name in categories:
        cat = PosCategory.search([("name", "=", name)], limit=1)
        if not cat:
            cat = PosCategory.create({"name": name})
        mapping[name] = cat
    return mapping


def purge_demo_products(env):
    print("[*] Purging non-Alahram demo products (Clothes, Food, Furniture, etc.)...")
    ProductTemplate = env["product.template"]
    ProductCategory = env["product.category"]
    PosCategory = env["pos.category"]

    # 0. Unlink demo combo items and combos
    if "product.combo.item" in env:
        env["product.combo.item"].sudo().search([]).unlink()
    if "product.combo" in env:
        env["product.combo"].sudo().search([]).unlink()

    # 1. Identify demo categories to remove from POS
    demo_cats = ProductCategory.search([
        ("name", "in", ["Clothes", "Food", "Furniture", "Home Construction", "Expenses", "Office", "Outdoor", "Desks", "Chairs"])
    ])
    demo_cat_ids = demo_cats.ids
    for dc in demo_cats:
        children = ProductCategory.search([("parent_id", "child_of", dc.id)])
        demo_cat_ids.extend(children.ids)
    demo_cat_ids = list(set(demo_cat_ids))

    demo_products = ProductTemplate.search([
        "|",
        ("categ_id", "in", demo_cat_ids),
        ("name", "in", [
            "Acoustic Bloc Screens", "Apple In-Ear Headphones", "Apple Wireless Keyboard",
            "Bacon Burger", "Cabinet with Doors", "Conference Chair", "Corner Desk Left Sit",
            "Corner Desk Right Sit", "Desk Combination", "Desk Pad", "Desk Stand with Screen",
            "Drawer Black", "Four Person Desk", "Large Cabinet", "Large Desk", "Large Meeting Table",
            "Office Chair Black", "Storage Box", "T-Shirt", "Three-Seat Sofa", "Whiteboard", "Whiteboard Pen"
        ])
    ])

    print(f"[*] Found {len(demo_products)} non-Alahram demo products to clean up.")

    archived_count = 0
    for p in demo_products:
        p.write({
            "available_in_pos": False,
            "active": False,
            "sale_ok": False,
            "purchase_ok": False,
            "pos_categ_ids": [(5, 0, 0)],
        })
        archived_count += 1

    print(f"[+] Cleaned Demo Products: {archived_count} permanently archived & hidden from POS and Sales.")

    # 2. Deactivate demo POS categories
    demo_pos_cats = PosCategory.search([
        ("name", "in", ["Misc", "Desks", "Chairs", "Upper body", "Lower body", "Others", "Breads", "Pastries"])
    ])
    for pc in demo_pos_cats:
        try:
            pc.unlink()
        except Exception:
            pass


def main():
    print("[*] Initializing Odoo 20 Enterprise Environment...")
    config.parse_config(["-c", "/etc/odoo/odoo.conf", "-d", "odoo20"])
    registry = Registry("odoo20")

    csv_path = "/mnt/ALAhram/scraped_products/products_with_base64.csv"
    if not os.path.exists(csv_path):
        csv_path = "/mnt/ALAhram/scraped_products/alahram_odoo_products_with_base64_50.csv"

    print(f"[*] Reading products from: {csv_path}")

    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        ProductTemplate = env["product.template"]
        ProductProduct = env["product.product"]
        StockLocation = env["stock.location"]
        StockQuant = env["stock.quant"]

        # 1. Purge demo items
        purge_demo_products(env)

        # 2. Setup POS categories
        pos_cat_mapping = setup_pos_categories(env)

        # 3. Locate branch warehouses
        loc_sg_showroom = StockLocation.search([("complete_name", "ilike", "WH-SG%Showroom")], limit=1)
        loc_sg_backroom = StockLocation.search([("complete_name", "ilike", "WH-SG%Backroom")], limit=1)
        loc_main = StockLocation.search([("complete_name", "ilike", "WH-MAIN%Stock")], limit=1)

        # 4. Import all scraped products
        products_data = []
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                products_data.append(row)

        print(f"[*] Processing {len(products_data)} Alahram Cookware products into Odoo 20 catalog...")

        created_count = 0
        updated_count = 0

        for idx, row in enumerate(products_data, start=1):
            name = row.get("name", "").strip()
            if not name:
                continue

            sku = row.get("default_code", "").strip()
            if not sku:
                sku = f"AH-{idx:04d}"

            cat_str = row.get("categ_id", "منتجات الأهرام").strip()
            internal_cat = get_or_create_internal_category(env, cat_str)

            # Map POS Category
            pos_cat_name = determine_pos_category(name, cat_str)
            pos_cat = pos_cat_mapping.get(pos_cat_name)

            try:
                list_price = float(row.get("list_price") or 0.0)
            except ValueError:
                list_price = 0.0

            try:
                standard_price = float(row.get("standard_price") or 0.0)
            except ValueError:
                standard_price = round(list_price * 0.72, 2) if list_price else 0.0

            if standard_price <= 0 and list_price > 0:
                standard_price = round(list_price * 0.72, 2)

            description_sale = row.get("description_sale", "").strip()
            image_b64 = row.get("image_1920", "").strip()
            if image_b64.startswith("http"):
                image_b64 = False

            material = determine_material_type(name, description_sale)
            official_url = row.get("website_url", "")
            bin_loc = f"الممر {(idx % 4) + 1} - الرف {(idx % 6) + 1} - م{(idx % 3) + 1}"

            existing = ProductTemplate.search([
                "|", ("default_code", "=", sku), ("name", "=", name)
            ], limit=1)

            vals = {
                "name": name,
                "default_code": sku,
                "categ_id": internal_cat.id,
                "list_price": list_price,
                "standard_price": standard_price,
                "description_sale": description_sale,
                "material_type": material,
                "official_url": official_url,
                "bin_location": bin_loc,
                "is_storable": True,
                "available_in_pos": True,
                "sale_ok": True,
                "purchase_ok": True,
            }
            if pos_cat:
                vals["pos_categ_ids"] = [(6, 0, [pos_cat.id])]

            if image_b64:
                vals["image_1920"] = image_b64

            if existing:
                existing.write(vals)
                template = existing
                updated_count += 1
            else:
                template = ProductTemplate.create(vals)
                created_count += 1

            # Update stock in showroom & backroom
            product_variant = template.product_variant_id or ProductProduct.search([
                ("product_tmpl_id", "=", template.id)
            ], limit=1)

            if product_variant:
                sh_qty = 6.0 + (idx % 14)
                bk_qty = 25.0 + (idx % 30)
                mn_qty = 80.0 + (idx % 40)

                for loc, qty in [(loc_sg_showroom, sh_qty), (loc_sg_backroom, bk_qty), (loc_main, mn_qty)]:
                    if not loc:
                        continue
                    quant = StockQuant.search([
                        ("product_id", "=", product_variant.id),
                        ("location_id", "=", loc.id)
                    ], limit=1)
                    if quant:
                        quant.sudo().write({"quantity": qty})
                    else:
                        StockQuant.sudo().create({
                            "product_id": product_variant.id,
                            "location_id": loc.id,
                            "quantity": qty,
                        })

            if idx % 50 == 0 or idx == len(products_data):
                print(f"  -> Processed {idx}/{len(products_data)} products...")

        cr.commit()

        print("\n" + "=" * 65)
        print("Alahram Full Catalog Import & Cleanup Complete!")
        print(f"Total Products Created: {created_count}")
        print(f"Total Products Updated: {updated_count}")
        print(f"Active POS Categories:  {len(pos_cat_mapping)}")
        print("=" * 65)

if __name__ == "__main__":
    main()
