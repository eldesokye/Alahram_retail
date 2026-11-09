# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class AlahramBridalPackageWizard(models.TransientModel):
    _name = 'alahram.bridal.package.wizard'
    _description = 'معالج باكدج العروسة السريع بصالة العرض'

    partner_id = fields.Many2one('res.partner', string='العميل / العروسة', required=True)
    target_budget = fields.Float(string='الميزانية المستهدفة (ج.م)', default=20000.0, required=True)
    tier = fields.Selection([
        ('silver_15k', 'باكدج فضي اقتصادي (15,000 ج.م)'),
        ('gold_20k', 'باكدج ذهبي مميز (20,000 ج.م)'),
        ('platinum_30k', 'باكدج بلاتينيوم متكامل (30,000 ج.م)'),
        ('royal_45k', 'باكدج ملكي فاخر (45,000 ج.م)'),
        ('custom', 'ميزانية مخصصة'),
    ], string='فئة الباكدج', default='gold_20k')

    # قطاعات جهاز العروسة
    sector_granite = fields.Boolean(string='أطقم حلل جرانيت (صحي غير لاصق)', default=True)
    sector_stainless = fields.Boolean(string='أطقم ستانلس ستيل 18/10 (سيجنتشر / زينوكس)', default=True)
    sector_aluminum = fields.Boolean(string='أطقم ألومنيوم كلاسيك للطهي (نقي 99.5%)', default=False)
    sector_bakeware = fields.Boolean(string='صواني فرن ومخبوزات وقوالب كيك وبسكويت', default=True)
    sector_frypans = fields.Boolean(string='طاسات تحمير ومقالي كريب وشوايات جريل', default=True)
    sector_appliances = fields.Boolean(string='أجهزة كهربائية صغيرة وخلاطات وهاند بلندر', default=False)
    sector_cutlery = fields.Boolean(string='أطقم ملاعق وسكاكين وشوك ومقصات مطبخ', default=False)
    sector_serveware = fields.Boolean(string='صواني تقديم وأطقم شاي وقهوة وزجاجيات', default=False)
    sector_accessories = fields.Boolean(string='أدوات ومفروشات وموزعات سيليكون', default=False)

    @api.onchange('tier')
    def _onchange_tier(self):
        if self.tier == 'silver_15k':
            self.target_budget = 15000.0
        elif self.tier == 'gold_20k':
            self.target_budget = 20000.0
        elif self.tier == 'platinum_30k':
            self.target_budget = 30000.0
        elif self.tier == 'royal_45k':
            self.target_budget = 45000.0

    def action_generate_and_open_configurator(self):
        self.ensure_one()
        configurator = self.env['alahram.bridal.configurator'].create({
            'partner_id': self.partner_id.id,
            'target_budget': self.target_budget,
            'package_tier': self.tier,
            'sector_granite': self.sector_granite,
            'sector_stainless': self.sector_stainless,
            'sector_aluminum': self.sector_aluminum,
            'sector_bakeware': self.sector_bakeware,
            'sector_frypans': self.sector_frypans,
            'sector_appliances': self.sector_appliances,
            'sector_cutlery': self.sector_cutlery,
            'sector_serveware': self.sector_serveware,
            'sector_accessories': self.sector_accessories,
        })
        configurator.action_suggest_package_from_sectors()
        return {
            'name': _('مُهيئ باكدج العروسة الذكي'),
            'type': 'ir.actions.act_window',
            'res_model': 'alahram.bridal.configurator',
            'res_id': configurator.id,
            'view_mode': 'form',
            'target': 'current',
        }
