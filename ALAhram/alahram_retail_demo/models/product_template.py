# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    bin_location = fields.Char(
        string='موقع التخزين (الممر / الرف / المستوى)',
        help='موقع الصنف الدقيق في الفرع: الممر - الرف - المستوى'
    )
    official_url = fields.Char(
        string='رابط الموقع الرسمي',
        help='رابط الصنف على الموقع الرسمي alahramcookware.com'
    )
    material_type = fields.Selection([
        ('aluminum', 'ألومنيوم نقي 99.5%'),
        ('stainless', 'ستانلس ستيل 18/10'),
        ('granite', 'جرانيت غير لاصق'),
        ('tefal', 'تيفال صحي'),
        ('accessories', 'إكسسوارات ومفروشات المطبخ'),
    ], string='نوع الخامة', default='aluminum')

    qty_sg_showroom = fields.Float(
        string='رصيد صالة العرض سيدي جابر',
        compute='_compute_branch_stock_splits',
        digits='Product Unit of Measure'
    )
    qty_sg_backroom = fields.Float(
        string='رصيد مخزن سيدي جابر الخلفي',
        compute='_compute_branch_stock_splits',
        digits='Product Unit of Measure'
    )
    qty_wh_main = fields.Float(
        string='رصيد مخزن الإدارة الرئيسي',
        compute='_compute_branch_stock_splits',
        digits='Product Unit of Measure'
    )
    qty_wh_roshdy = fields.Float(
        string='رصيد فرع رشدي / لوران',
        compute='_compute_branch_stock_splits',
        digits='Product Unit of Measure'
    )
    cross_branch_stock_summary = fields.Text(
        string='بيان الأرصدة عبر الفروع',
        compute='_compute_branch_stock_splits'
    )
    is_dead_stock = fields.Boolean(
        string='صنف راكد (مخزون راكد بدون مبيعات)',
        default=False
    )
    october_sold_qty = fields.Integer(
        string='مبيعات أكتوبر 2026 (قطعة)',
        default=0
    )

    @api.constrains('default_code')
    def _check_unique_default_code(self):
        for record in self:
            if record.default_code:
                duplicate = self.search([
                    ('default_code', '=', record.default_code),
                    ('id', '!=', record.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(_(
                        "خطأ حرج في التكويد (منع فوضى نظام Fox/RM السابق):\n"
                        "كود الصنف '%s' مستخدم بالفعل للصنف '%s'!\n"
                        "نظام أودو 20 يمنع تكرار الأكواد نهائياً ويفرض التوحيد عبر المتغيرات."
                    ) % (record.default_code, duplicate.name))

    @api.constrains('barcode')
    def _check_unique_barcode(self):
        for record in self:
            if record.barcode:
                duplicate = self.search([
                    ('barcode', '=', record.barcode),
                    ('id', '!=', record.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(_(
                        "خطأ حرج في الباركود (منع فوضى نظام Fox/RM السابق):\n"
                        "الباركود '%s' مسجل بالفعل لصنف آخر '%s'!"
                    ) % (record.barcode, duplicate.name))

    def _compute_branch_stock_splits(self):
        StockQuant = self.env['stock.quant']
        Location = self.env['stock.location']
        for template in self:
            products = template.product_variant_ids
            if not products:
                template.qty_sg_showroom = 0.0
                template.qty_sg_backroom = 0.0
                template.qty_wh_main = 0.0
                template.qty_wh_roshdy = 0.0
                template.cross_branch_stock_summary = "{}"
                continue

            # Query locations by complete name pattern or external identifier
            loc_showroom = Location.search(['|', ('complete_name', 'ilike', 'WH-SG%Showroom'), ('name', '=', 'Showroom')], limit=1)
            loc_backroom = Location.search(['|', ('complete_name', 'ilike', 'WH-SG%Backroom'), ('name', '=', 'Backroom')], limit=1)
            wh_main_loc = Location.search([('complete_name', 'ilike', 'WH-MAIN%Stock')], limit=1)
            wh_roshdy_loc = Location.search([('complete_name', 'ilike', 'WH-ROSHDY%Stock')], limit=1)

            def get_qty(loc):
                if not loc:
                    return 0.0
                quants = StockQuant.search([
                    ('product_id', 'in', products.ids),
                    ('location_id', 'child_of', loc.id)
                ])
                return sum(quants.mapped('quantity'))

            template.qty_sg_showroom = get_qty(loc_showroom)
            template.qty_sg_backroom = get_qty(loc_backroom)
            template.qty_wh_main = get_qty(wh_main_loc)
            template.qty_wh_roshdy = get_qty(wh_roshdy_loc)

            # Build summary JSON
            summary = {
                'sg_showroom': template.qty_sg_showroom,
                'sg_backroom': template.qty_sg_backroom,
                'wh_main': template.qty_wh_main,
                'wh_roshdy': template.qty_wh_roshdy,
                'total_company': template.qty_available,
            }
            template.cross_branch_stock_summary = json.dumps(summary, ensure_ascii=False)

    def action_reserve_from_another_branch(self):
        """1-Click Cross-Branch Stock Reservation Wizard launcher"""
        self.ensure_one()
        return {
            'name': _('طلب حجز وتحويل مخزني فوري من فرع آخر'),
            'type': 'ir.actions.act_window',
            'res_model': 'alahram.cross.branch.reserve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.product_variant_id.id if self.product_variant_id else False,
                'default_dest_warehouse_id': self.env['stock.warehouse'].search([('code', '=', 'WH-SG')], limit=1).id,
            }
        }

    def action_pull_from_backroom(self):
        """Pulls stock from Backroom to Showroom in Sidi Gaber (Scene 3 scenario)"""
        self.ensure_one()
        Location = self.env['stock.location']
        loc_showroom = Location.search([('name', '=', 'Showroom'), ('location_id.name', 'ilike', 'سيدي جابر')], limit=1)
        loc_backroom = Location.search([('name', '=', 'Backroom'), ('location_id.name', 'ilike', 'سيدي جابر')], limit=1)

        if not loc_backroom or not loc_showroom:
            loc_showroom = Location.search([('complete_name', 'ilike', 'WH-SG/Stock')], limit=1)
            loc_backroom = loc_showroom

        product = self.product_variant_id
        if not product:
            raise ValidationError(_("لا يوجد متغير متاح لهذا الصنف!"))

        wh_sg = self.env['stock.warehouse'].search([('code', '=', 'WH-SG')], limit=1)
        picking_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', wh_sg.id),
            ('code', '=', 'internal')
        ], limit=1) or self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)

        pull_qty = 2.0 if self.qty_sg_backroom >= 2.0 else (self.qty_sg_backroom if self.qty_sg_backroom > 0 else 1.0)
        clean_ctx = {k: v for k, v in self.env.context.items() if not k.startswith('default_')}
        StockPicking = self.env['stock.picking'].sudo().with_context(clean_ctx)
        StockMove = self.env['stock.move'].sudo().with_context(clean_ctx)

        picking = StockPicking.create({
            'picking_type_id': picking_type.id,
            'location_id': loc_backroom.id,
            'location_dest_id': loc_showroom.id,
            'origin': f"سحب مخزن خلفي - {self.default_code or self.name}",
            'priority': '0',
        })
        StockMove.create({
            'product_id': product.id,
            'product_uom_qty': pull_qty,
            'uom_id': product.uom_id.id,
            'picking_id': picking.id,
            'location_id': loc_backroom.id,
            'location_dest_id': loc_showroom.id,
        })
        picking.sudo().action_confirm()
        return {
            'name': _('إذن سحب البضاعة من المخزن الخلفي لصالة العرض (WH-SG)'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    qty_sg_showroom = fields.Float(related='product_tmpl_id.qty_sg_showroom')
    qty_sg_backroom = fields.Float(related='product_tmpl_id.qty_sg_backroom')
    qty_wh_main = fields.Float(related='product_tmpl_id.qty_wh_main')
    qty_wh_roshdy = fields.Float(related='product_tmpl_id.qty_wh_roshdy')
    bin_location = fields.Char(related='product_tmpl_id.bin_location')

    def action_reserve_from_another_branch(self):
        return self.product_tmpl_id.action_reserve_from_another_branch()

    def action_pull_from_backroom(self):
        return self.product_tmpl_id.action_pull_from_backroom()

