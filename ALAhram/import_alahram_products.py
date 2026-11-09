# -*- coding: utf-8 -*-
"""
Import Scraped Alahram Cookware Products into Odoo 20 Enterprise
==============================================================
Reads scraped products from /mnt/ALAhram/scraped_products/
and creates/updates product.template and product.product records
with high-res photos, Arabic categories, specifications, prices,
and branch inventory quants.
"""

import csv
import os
import re
import sys
from pathlib import Path

import odoo
from odoo.tools import config
from odoo.modules.registry import Registry

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
        "سباتولا", "طبق", "صينية تقديم", "بورسلين", "زجاج", "ملامين", "cutlery",
        "textile", "knife", "fork", "spoon", "scissors", "tray", "wood", "silicone"
    ]
    for kw in accessories_keywords:
        if kw in combined:
            return "accessories"
    return "aluminum"


def get_or_create_category(env, cat_path: str):
    Category = env["product.category"]
    parts = [p.strip() for p in cat_path.replace(">", "/").split("/") if p.strip()]
    if not parts:
        parts = ["الأهرام هوم", "عام"]

    parent_id = False
    for part in parts:
        # Search for category with this name and parent
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


def main():
    print("[*] Initializing Odoo 20 Enterprise Environment...")
    config.parse_config(["-c", "/etc/odoo/odoo.conf", "-d", "odoo20"])
    registry = Registry("odoo20")

    export_dir = "/mnt/ALAhram/alahram_odoo_export" if os.path.exists("/mnt/ALAhram/alahram_odoo_export") else "/mnt/ALAhram/scraped_products"
    csv_b64_path = os.path.join(export_dir, "alahram_odoo_products_with_base64_50.csv")
    csv_url_path = os.path.join(export_dir, "alahram_odoo_products_50.csv")

    if not os.path.exists(csv_b64_path):
        print(f"[!] Error: File not found: {csv_b64_path}")
        return

    # Load URL mappings if available
    url_map = {}
    if os.path.exists(csv_url_path):
        with open(csv_url_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get("default_code", "").strip()
                if code:
                    url_map[code] = row.get("website_url", "")

    # Load base64 products
    products_data = []
    with open(csv_b64_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            products_data.append(row)

    print(f"[*] Loaded {len(products_data)} products from CSV.")

    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        ProductTemplate = env["product.template"]
        ProductProduct = env["product.product"]
        StockLocation = env["stock.location"]
        StockQuant = env["stock.quant"]

        # Find key branch locations
        loc_sg_showroom = StockLocation.search([("complete_name", "ilike", "WH-SG%Showroom")], limit=1)
        loc_sg_backroom = StockLocation.search([("complete_name", "ilike", "WH-SG%Backroom")], limit=1)
        loc_main = StockLocation.search([("complete_name", "ilike", "WH-MAIN%Stock")], limit=1)
        loc_roshdy = StockLocation.search([("complete_name", "ilike", "WH-ROSHDY%Stock")], limit=1)

        print(f"[*] Target Locations: Showroom={loc_sg_showroom.id}, Backroom={loc_sg_backroom.id}, Main={loc_main.id}")

        created_count = 0
        updated_count = 0
        inventory_updated = 0

        for idx, row in enumerate(products_data, start=1):
            name = row.get("name", "").strip()
            sku = row.get("default_code", "").strip()
            if not sku:
                sku = f"AH-{idx:04d}"

            cat_str = row.get("categ_id", "الأهرام هوم / تشكيلة المنزل").strip()
            category = get_or_create_category(env, cat_str)

            try:
                list_price = float(row.get("list_price") or 0.0)
            except ValueError:
                list_price = 0.0

            try:
                standard_price = float(row.get("standard_price") or 0.0)
            except ValueError:
                standard_price = list_price * 0.7 if list_price else 0.0

            if standard_price <= 0 and list_price > 0:
                standard_price = round(list_price * 0.72, 2)

            description_sale = row.get("description_sale", "").strip()
            image_b64 = row.get("image_1920", "").strip()
            # If image_b64 is a URL (fallback), clear it so base64 decoder doesn't fail
            if image_b64.startswith("http"):
                image_b64 = False

            material = determine_material_type(name, description_sale)
            official_url = url_map.get(sku, "")
            bin_loc = f"الممر {(idx % 4) + 1} - الرف {(idx % 5) + 1} - م{(idx % 3) + 1}"

            # Check if template already exists
            existing = ProductTemplate.search([
                "|", ("default_code", "=", sku), ("name", "=", name)
            ], limit=1)

            vals = {
                "name": name,
                "default_code": sku,
                "categ_id": category.id,
                "list_price": list_price,
                "standard_price": standard_price,
                "description_sale": description_sale,
                "material_type": material,
                "official_url": official_url,
                "bin_location": bin_loc,
                "is_storable": True,
                "sale_ok": True,
                "purchase_ok": True,
            }
            if image_b64:
                vals["image_1920"] = image_b64

            if existing:
                existing.write(vals)
                template = existing
                updated_count += 1
            else:
                template = ProductTemplate.create(vals)
                created_count += 1

            # Get variant product
            product_variant = template.product_variant_id or ProductProduct.search([
                ("product_tmpl_id", "=", template.id)
            ], limit=1)

            if product_variant:
                # Add realistic showroom & backroom quantities
                # e.g. Showroom: 6-18 units, Backroom: 25-60 units
                showroom_qty = 8.0 + (idx % 12)
                backroom_qty = 28.0 + (idx % 35)
                main_qty = 80.0 + (idx % 50)

                for loc, qty in [(loc_sg_showroom, showroom_qty), (loc_sg_backroom, backroom_qty), (loc_main, main_qty)]:
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
                inventory_updated += 1

            if idx % 10 == 0:
                print(f"  -> Processed {idx}/{len(products_data)} products...")

        cr.commit()

        print("\n" + "=" * 65)
        print(f"[+] Odoo 20 Import Complete!")
        print(f"[+] Newly Created Products: {created_count}")
        print(f"[+] Updated Products:        {updated_count}")
        print(f"[+] Products with Stock:     {inventory_updated}")
        print("=" * 65)

if __name__ == "__main__":
    main()

