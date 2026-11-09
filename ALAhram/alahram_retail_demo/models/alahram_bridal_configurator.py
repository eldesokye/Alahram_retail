# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError
import json

class AlahramBridalConfigurator(models.Model):
    _name = 'alahram.bridal.configurator'
    _description = 'مُهيئ باكدج العروسة وتوليد عروض المبيعات الذكية'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='رقم الباكدج',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('جديد')
    )
    partner_id = fields.Many2one('res.partner', string='العميل / العروسة', required=True, tracking=True)
    target_budget = fields.Float(string='الميزانية المستهدفة (جنيه)', default=20000.0, required=True, tracking=True)
    package_tier = fields.Selection([
        ('silver_15k', 'باكدج فضي اقتصادي (15,000 ج.م)'),
        ('gold_20k', 'باكدج ذهبي مميز (20,000 ج.م)'),
        ('platinum_30k', 'باكدج بلاتينيوم متكامل (30,000 ج.م)'),
        ('royal_45k', 'باكدج ملكي فاخر (45,000 ج.م)'),
        ('custom', 'ميزانية مخصصة'),
    ], string='فئة الباكدج', default='gold_20k', tracking=True)

    # 🎯 1. القطاعات والمكونات المطلوب تجهيزها في جهاز العروسة (يختارها البائع)
    sector_granite = fields.Boolean(string='أطقم حلل جرانيت (صحي غير لاصق)', default=True)
    sector_stainless = fields.Boolean(string='أطقم ستانلس ستيل 18/10 (سيجنتشر / زينوكس)', default=True)
    sector_aluminum = fields.Boolean(string='أطقم ألومنيوم كلاسيك للطهي (نقي 99.5%)', default=False)
    sector_bakeware = fields.Boolean(string='صواني فرن ومخبوزات وقوالب كيك وبسكويت', default=True)
    sector_frypans = fields.Boolean(string='طاسات تحمير ومقالي كريب وشوايات جريل', default=True)
    sector_appliances = fields.Boolean(string='أجهزة كهربائية صغيرة وخلاطات وهاند بلندر', default=False)
    sector_cutlery = fields.Boolean(string='أطقم ملاعق وسكاكين وشوك ومقصات مطبخ', default=False)
    sector_serveware = fields.Boolean(string='صواني تقديم وأطقم شاي وقهوة وزجاجيات', default=False)
    sector_accessories = fields.Boolean(string='أدوات ومفروشات وموزعات سيليكون', default=False)

    line_ids = fields.One2many('alahram.bridal.configurator.line', 'configurator_id', string='بنود وتشكيلة الباكدج')

    # 💰 2. الحساب المالي بدون أي خصم تلقائي عشوائي
    total_original_price = fields.Float(
        string='إجمالي السعر الأصلي للباكدج (ج.م)',
        compute='_compute_totals',
        store=True,
        tracking=True
    )
    budget_variance = fields.Float(
        string='فارق الميزانية (ج.م)',
        compute='_compute_totals',
        store=True
    )
    budget_feedback_message = fields.Char(
        string='بيان مطابقة الميزانية',
        compute='_compute_totals',
        store=True
    )

    # 📊 2.1 ذكاء الميزانية والتوصيات المقيدة (Intelligent Budget Recommendations)
    recommendation_type = fields.Selection([
        ('economy', 'باكدج اقتصادي (أقل من الميزانية)'),
        ('best_match', 'الباكدج الأفضل تطابقاً مع الميزانية'),
        ('premium', 'باكدج مميز (ضمن حدود التسامح)'),
        ('extended', 'خيار موسع (أعلى من الحدود المفضلة بقليل)'),
        ('custom', 'تشكيلة مخصصة يدوياً'),
    ], string='نوع التوصية', default='best_match', tracking=True)

    budget_match_status = fields.Selection([
        ('below_budget', 'أقل من الميزانية (اقتصادي)'),
        ('matches_budget', 'مطابق تماماً للميزانية'),
        ('within_preferred', 'ضمن نطاق التسامح المفضل'),
        ('slightly_above_preferred', 'أعلى من النطاق المفضل بقليل (نطاق موسع)'),
        ('out_of_bounds', 'خارج نطاق الميزانية والتسامح المسموح'),
        ('no_solution', 'لا توجد أصناف كافية لتغطية الميزانية والقطاعات'),
    ], string='حالة مطابقة الميزانية', compute='_compute_totals', store=True, tracking=True)

    lower_bound = fields.Float(
        string='الحد الأدنى للميزانية (ج.م)',
        compute='_compute_totals',
        store=True,
        help='Lower Bound = max(0, Budget - tolerance_below)'
    )
    preferred_upper_bound = fields.Float(
        string='الحد الأقصى المفضل (ج.م)',
        compute='_compute_totals',
        store=True,
        help='Preferred Upper Bound = Budget + tolerance_above_pref'
    )
    absolute_upper_bound = fields.Float(
        string='الحد الأقصى المطلق (ج.م)',
        compute='_compute_totals',
        store=True,
        help='Absolute Upper Bound = Budget + tolerance_above_abs'
    )

    tax_amount = fields.Float(
        string='إجمالي قيمة الضريبة (14% VAT)',
        compute='_compute_totals',
        store=True
    )
    tax_included_total = fields.Float(
        string='الإجمالي شامل الضريبة (ج.م)',
        compute='_compute_totals',
        store=True
    )

    recommendation_options_json = fields.Text(
        string='Recommendation Options Cache JSON',
        help='Stores generated packages (Economy, Best Match, Premium) for quick POS retrieval.'
    )
    recommendation_reason = fields.Text(
        string='سبب التوصية ومعايير الاختيار'
    )

    # 🔒 3. حوكمة الخصومات متعددة المستويات (0-5% مدير فرع / 5-7% مدير عمليات / >7% محظور تماماً)
    requested_discount_pct = fields.Float(
        string='نسبة الخصم المطلوبة %',
        default=0.0,
        tracking=True,
        help='يحدد البائع نسبة الخصم المرغوبة (حتى 5% لمدير الفرع، وحتى 7% لمدير العمليات).'
    )
    requested_discount_amount = fields.Float(
        string='قيمة الخصم المطلوبة (ج.م)',
        compute='_compute_totals',
        store=True
    )
    discount_state = fields.Selection([
        ('no_discount', 'بدون خصم (معتمد تلقائياً)'),
        ('pending_bm', 'بانتظار موافقة مدير الفرع (خصم حتى 5%)'),
        ('pending_ops', 'بانتظار موافقة مدير العمليات (استثنائي حتى 7%)'),
        ('approved', 'تم اعتماد الخصم رسمياً'),
        ('refused', 'تم رفض الخصم من الإدارة'),
    ], string='حالة اعتماد الخصم', default='no_discount', tracking=True)

    discount_approver_id = fields.Many2one('res.users', string='معتمد الخصم', readonly=True)
    discount_approval_date = fields.Datetime(string='تاريخ ووقت الاعتماد', readonly=True)
    discount_refusal_reason = fields.Char(string='سبب رفض الخصم')

    package_discount_amount = fields.Float(
        string='الخصم الفعلي المعتمد (ج.م)',
        compute='_compute_totals',
        store=True
    )
    final_package_price = fields.Float(
        string='صافي سعر الباكدج للعميل (ج.م)',
        compute='_compute_totals',
        store=True,
        tracking=True
    )
    total_savings_percentage = fields.Float(
        string='نسبة التوفير المعتمدة %',
        compute='_compute_totals',
        store=True
    )

    state = fields.Selection([
        ('draft', 'مسودة / اختيار القطاعات'),
        ('calculated', 'تم تشكيل الباكدج الذكي'),
        ('reserved', 'محجوز بالفروع'),
        ('order_created', 'تم إصدار أمر البيع'),
        ('sent_to_pos', 'تم الإرسال للكاشير (POS)'),
    ], string='الحالة', default='draft', tracking=True)

    sale_order_id = fields.Many2one('sale.order', string='أمر البيع المنشأ', readonly=True)
    pos_order_id = fields.Many2one('pos.order', string='أمر الكاشير (POS)', readonly=True)
    notes = fields.Text(string='ملاحظات وتوصيات البائع / الذكاء الاصطناعي')

    # POS Tablet & Multi-Branch Integration Fields
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Selling Branch / الفرع البائع',
        default=lambda self: self._default_warehouse_id()
    )
    pos_session_id = fields.Many2one('pos.session', string='POS Session / جلسة البيع')
    pos_config_id = fields.Many2one('pos.config', string='POS Terminal / نقطة البيع')
    salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson / البائع',
        default=lambda self: self.env.user
    )
    reservation_id = fields.Many2one(
        'alahram.branch.reservation',
        string='Cross-Branch Reservation / حجز الفروع المرتبط',
        ondelete='set null'
    )
    fulfillment_strategy = fields.Selection([
        ('consolidated', 'Consolidated / شحن وتجميع بالفرع البائع'),
        ('split', 'Split Sourcing / تجهيز متعدد الفروع'),
        ('source_pickup', 'Source Branch Pickup / استلام العميل من الفرع المصدر'),
    ], string='Fulfillment Strategy / استراتيجية التجهيز', default='consolidated')
    delivery_preference = fields.Selection([
        ('all_together', 'Deliver All Together / تسليم كامل الباكدج دفعة واحدة'),
        ('as_ready', 'Deliver As Ready / تسليم جزئي حسب جاهزية الأصناف'),
    ], string='Delivery Preference / تفضيل التسليم', default='all_together')
    expected_delivery_date = fields.Date(string='Expected Delivery Date / تاريخ التسليم المتوقع')
    customer_notes = fields.Text(string='Customer Notes / ملاحظات العروسة والطلب')
    substitution_history = fields.Text(string='Substitution History / سجل استبدال الأصناف')
    idempotency_key = fields.Char(string='Idempotency Key', index=True, copy=False)

    @api.model
    def _default_warehouse_id(self):
        wh_sg = self.env['stock.warehouse'].search([('code', '=', 'WH-SG')], limit=1)
        if wh_sg:
            return wh_sg.id
        wh = self.env['stock.warehouse'].search([], limit=1)
        return wh.id if wh else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('جديد')) == _('جديد'):
                vals['name'] = self.env['ir.sequence'].next_by_code('alahram.bridal.configurator') or _('BRIDAL-%04d') % (self.env['alahram.bridal.configurator'].search_count([]) + 1)
        return super().create(vals_list)

    @api.onchange('package_tier')
    def _onchange_package_tier(self):
        if self.package_tier == 'silver_15k':
            self.target_budget = 15000.0
        elif self.package_tier == 'gold_20k':
            self.target_budget = 20000.0
        elif self.package_tier == 'platinum_30k':
            self.target_budget = 30000.0
        elif self.package_tier == 'royal_45k':
            self.target_budget = 45000.0

    @api.constrains('requested_discount_pct')
    def _check_max_discount_limit(self):
        for rec in self:
            if rec.requested_discount_pct > 7.0:
                raise ValidationError(_(
                    "❌ خطأ حرج في حوكمة الخصومات بالأهرام:\n"
                    "الحد الأقصى المطلق للخصم في نظام شركة الأهرام بالكامل هو 7%% بتصريح مدير العمليات فقط!\n"
                    "غير مسموح نهائياً بمنح أو طلب خصم يتجاوز 7%% (النسبة المطلوبة: %.2f%%)."
                ) % rec.requested_discount_pct)
            if rec.requested_discount_pct < 0.0:
                raise ValidationError(_("لا يمكن أن تكون نسبة الخصم سالبة!"))

    @api.depends('line_ids.price_subtotal', 'target_budget', 'requested_discount_pct', 'discount_state')
    def _compute_totals(self):
        for rec in self:
            orig = sum(rec.line_ids.mapped('price_subtotal'))
            rec.total_original_price = orig

            # Tolerance boundaries from configuration
            tol_cfg = rec.get_bridal_budget_tolerance_config()
            B = rec.target_budget or 0.0
            L = max(0.0, B - tol_cfg['tolerance_below'])
            U_pref = B + tol_cfg['tolerance_above_pref']
            U_abs = B + tol_cfg['tolerance_above_abs']
            rec.lower_bound = L
            rec.preferred_upper_bound = U_pref
            rec.absolute_upper_bound = U_abs

            # Calculate difference without forcing automatic discount
            variance = orig - B
            rec.budget_variance = variance

            # Compute taxes via native Odoo compute_all
            total_tax = 0.0
            for line in rec.line_ids:
                if line.product_id:
                    taxes = line.product_id.taxes_id
                    if rec.partner_id and hasattr(rec.partner_id, 'property_account_position_id') and rec.partner_id.property_account_position_id:
                        taxes = rec.partner_id.property_account_position_id.map_tax(taxes)
                    tax_res = taxes.compute_all(line.unit_price, quantity=line.quantity or 1.0, product=line.product_id, partner=rec.partner_id)
                    total_tax += (tax_res['total_included'] - tax_res['total_excluded'])
            rec.tax_amount = round(total_tax, 2)
            rec.tax_included_total = round(orig + total_tax if total_tax > 0 and orig > 0 else orig, 2)

            # Determine budget match status
            if not rec.line_ids:
                rec.budget_match_status = 'no_solution'
                rec.budget_feedback_message = False
            elif orig > U_abs or (L > 0 and orig < L):
                rec.budget_match_status = 'out_of_bounds'
                if orig > U_abs:
                    rec.budget_feedback_message = _(
                        "السعر الإجمالي (%.2f ج.م) يتجاوز الحد الأقصى المطلق للميزانية (%.2f ج.م) بمقدار +%.2f ج.م!"
                    ) % (orig, U_abs, orig - B)
                else:
                    rec.budget_feedback_message = _(
                        "السعر الإجمالي (%.2f ج.م) أقل من الحد الأدنى المقبول للميزانية (%.2f ج.م) بمقدار %.2f ج.م (وفارق %.2f ج.م عن الميزانية المستهدفة)."
                    ) % (orig, L, L - orig, B - orig)
            elif orig > U_pref and orig <= U_abs:
                rec.budget_match_status = 'slightly_above_preferred'
                rec.budget_feedback_message = _(
                    "السعر الإجمالي (%.2f ج.م) أعلى من النطاق المفضل بقليل (+%.2f ج.م)، ولكنه يقع ضمن الحد الأقصى المطلق (%.2f ج.م)."
                ) % (orig, orig - B, U_abs)
            elif abs(variance) < 1.0:
                rec.budget_match_status = 'matches_budget'
                rec.budget_feedback_message = _("السعر مطابق تماماً للميزانية المستهدفة (%.2f ج.م).") % orig
            elif orig < B:
                rec.budget_match_status = 'below_budget'
                rec.budget_feedback_message = _(
                    "باكدج اقتصادي مناسب: إجمالي الأصناف هو %.2f ج.م (أقل من الميزانية بـ %.2f ج.م، التوفير متاح للعميل)."
                ) % (orig, abs(variance))
            else:
                rec.budget_match_status = 'within_preferred'
                rec.budget_feedback_message = _(
                    "السعر الإجمالي (%.2f ج.م) ضمن نطاق التسامح المفضل للميزانية (+%.2f ج.م)."
                ) % (orig, variance)

            # Discount calculation based on approval governance
            req_amount = round(orig * (rec.requested_discount_pct / 100.0), 2)
            rec.requested_discount_amount = req_amount

            if rec.discount_state == 'approved' and rec.requested_discount_pct > 0:
                rec.package_discount_amount = req_amount
                rec.final_package_price = orig - req_amount
                rec.total_savings_percentage = rec.requested_discount_pct
            else:
                # If no discount or pending or refused -> full original price
                rec.package_discount_amount = 0.0
                rec.final_package_price = orig
                rec.total_savings_percentage = 0.0

    # -------------------------------------------------------------------------
    # 🎯 محرك التوصيات الذكي المقيد بميزانية العميل وتسامح الفروع
    # -------------------------------------------------------------------------
    @api.model
    def get_bridal_budget_tolerance_config(self):
        """Retrieves configurable budget tolerance policy from ir.config_parameter."""
        ICP = self.env['ir.config_parameter'].sudo()
        try:
            if hasattr(ICP, 'get_float'):
                tol_below = ICP.get_float('alahram.bridal_tolerance_below', 2000.0)
            else:
                param = ICP.search([('key', '=', 'alahram.bridal_tolerance_below')], limit=1)
                tol_below = float(param.value) if param and param.value else 2000.0
        except Exception:
            tol_below = 2000.0

        try:
            if hasattr(ICP, 'get_float'):
                tol_above_pref = ICP.get_float('alahram.bridal_tolerance_above_pref', 2500.0)
            else:
                param = ICP.search([('key', '=', 'alahram.bridal_tolerance_above_pref')], limit=1)
                tol_above_pref = float(param.value) if param and param.value else 2500.0
        except Exception:
            tol_above_pref = 2500.0

        try:
            if hasattr(ICP, 'get_float'):
                tol_above_abs = ICP.get_float('alahram.bridal_tolerance_above_abs', 3000.0)
            else:
                param = ICP.search([('key', '=', 'alahram.bridal_tolerance_above_abs')], limit=1)
                tol_above_abs = float(param.value) if param and param.value else 3000.0
        except Exception:
            tol_above_abs = 3000.0

        try:
            if hasattr(ICP, 'get_int'):
                max_recs = ICP.get_int('alahram.bridal_max_recommendations', 3)
            else:
                param = ICP.search([('key', '=', 'alahram.bridal_max_recommendations')], limit=1)
                max_recs = int(param.value) if param and param.value else 3
        except Exception:
            max_recs = 3

        try:
            if hasattr(ICP, 'get_bool'):
                enable_ext = ICP.get_bool('alahram.bridal_enable_extended_range', True)
            else:
                param = ICP.search([('key', '=', 'alahram.bridal_enable_extended_range')], limit=1)
                enable_ext = param.value in ['True', 'true', '1', True] if param else True
        except Exception:
            enable_ext = True

        try:
            if hasattr(ICP, 'get_bool'):
                cross_branch = ICP.get_bool('alahram.bridal_consider_cross_branch', True)
            else:
                param = ICP.search([('key', '=', 'alahram.bridal_consider_cross_branch')], limit=1)
                cross_branch = param.value in ['True', 'true', '1', True] if param else True
        except Exception:
            cross_branch = True

        tol_below = max(0.0, tol_below)
        tol_above_pref = max(0.0, tol_above_pref)
        tol_above_abs = max(tol_above_pref, tol_above_abs)
        max_recs = max(1, max_recs)

        return {
            'tolerance_below': tol_below,
            'tolerance_above_pref': tol_above_pref,
            'tolerance_above_abs': tol_above_abs,
            'max_recommendations': max_recs,
            'enable_extended_range': enable_ext,
            'consider_cross_branch': cross_branch,
        }

    @api.model
    def compute_tax_included_price(self, product, pricelist=False, partner=False):
        """Native Odoo calculation of tax-inclusive payable customer price."""
        if not product:
            return 0.0, 0.0, 0.0
        unit_price = product.lst_price
        if pricelist:
            try:
                unit_price = pricelist._get_product_price(product, 1.0, partner=partner)
            except Exception:
                unit_price = product.lst_price
        taxes = product.taxes_id
        if partner and hasattr(partner, 'property_account_position_id') and partner.property_account_position_id:
            taxes = partner.property_account_position_id.map_tax(taxes)
        tax_res = taxes.compute_all(unit_price, quantity=1.0, product=product, partner=partner)
        tot_inc = tax_res.get('total_included', unit_price)
        tot_exc = tax_res.get('total_excluded', unit_price)
        tax_amt = tot_inc - tot_exc
        return round(tot_inc, 2), round(unit_price, 2), round(tax_amt, 2)

    @api.model
    def generate_budget_constrained_recommendations(self, target_budget, active_sectors, pos_config_id=False, partner_id=False, pricelist_id=False):
        """
        Intelligent combinatorial optimization engine for Bridal Packages.
        Generates realistic candidate combinations strictly constrained by customer budget:
          Lower Bound = max(0, B - tolerance_below)
          Preferred Upper Bound = B + tolerance_above_pref
          Absolute Upper Bound = B + tolerance_above_abs
        Returns up to 3 distinct package options (Economy, Best Match, Premium) or diagnostic explanations.
        """
        Product = self.env['product.product']
        res_model = self.env['alahram.branch.reservation']
        tol_cfg = self.get_bridal_budget_tolerance_config()

        B = float(target_budget or 0.0)
        if B <= 0:
            return {
                'success': True,
                'has_solution': False,
                'target_budget': B,
                'lower_bound': 0.0,
                'preferred_upper_bound': tol_cfg['tolerance_above_pref'],
                'absolute_upper_bound': tol_cfg['tolerance_above_abs'],
                'error_type': 'zero_or_negative_budget',
                'message': _("يرجى إدخال ميزانية صالحة أكبر من صفر لتوليد باكدجات مقيدة بالميزانية."),
                'recommendations': [],
            }

        L = max(0.0, B - tol_cfg['tolerance_below'])
        U_pref = B + tol_cfg['tolerance_above_pref']
        U_abs = B + tol_cfg['tolerance_above_abs']

        partner = self.env['res.partner'].browse(partner_id) if partner_id else False
        pricelist = False
        if pricelist_id:
            pricelist = self.env['product.pricelist'].browse(pricelist_id)
        elif pos_config_id:
            pos_conf = self.env['pos.config'].browse(pos_config_id)
            if pos_conf and pos_conf.pricelist_id:
                pricelist = pos_conf.pricelist_id

        # Normalize active_sectors (supports dict, list, set, tuple and aliases)
        if isinstance(active_sectors, (list, set, tuple)):
            active_dict = {str(k): True for k in active_sectors}
            if 'cookware_sets' in active_dict:
                active_dict['granite'] = True
                active_dict['stainless'] = True
            if 'pressure_cookers' in active_dict or 'catering_pots' in active_dict:
                active_dict['stainless'] = True
            if 'trays_cake' in active_dict:
                active_dict['bakeware'] = True
            active_sectors = active_dict
        elif isinstance(active_sectors, dict):
            active_sectors = dict(active_sectors)
            if active_sectors.get('cookware_sets'):
                active_sectors['granite'] = True
                active_sectors['stainless'] = True
            if active_sectors.get('trays_cake'):
                active_sectors['bakeware'] = True
        else:
            active_sectors = {}

        # Sector Definitions (authentic Al Ahram Cookware sectors)
        sector_definitions = [
            ('granite', active_sectors.get('granite', False), 'أطقم حلل جرانيت', ['جرانيت'], 'granite', 500.0, 0.35),
            ('stainless', active_sectors.get('stainless', False), 'أطقم حلل ستانلس', ['ستانلس', 'زينوكس'], 'stainless', 400.0, 0.25),
            ('aluminum', active_sectors.get('aluminum', False), 'أطقم ألومنيوم كلاسيك', ['ألومنيوم'], 'aluminum', 300.0, 0.20),
            ('bakeware', active_sectors.get('bakeware', False), 'صواني وطواجن فرن', ['صواني', 'صينية', 'طاجن', 'بسكويت'], False, 50.0, 0.10),
            ('frypans', active_sectors.get('frypans', False), 'طاسات ومقالي وجريل', ['كريب', 'مقلاية', 'طاسة', 'جريل'], False, 50.0, 0.10),
            ('appliances', active_sectors.get('appliances', False), 'أجهزة وخلاطات', ['خلاط', 'بلندر'], False, 100.0, 0.15),
            ('cutlery', active_sectors.get('cutlery', False), 'أطقم ملاعق وسكاكين', ['ملاعق', 'سكين', 'مقص', 'مائدة'], False, 30.0, 0.08),
            ('serveware', active_sectors.get('serveware', False), 'صواني تقديم وزجاجيات', ['سرفيس', 'شاي', 'قهوة', 'تقديم'], False, 50.0, 0.08),
            ('accessories', active_sectors.get('accessories', False), 'إكسسوارات ومفروشات', ['سيليكون', 'فوطة', 'جوانتي'], 'accessories', 20.0, 0.04),
        ]

        selected_sector_defs = [s for s in sector_definitions if s[1]]
        if not selected_sector_defs:
            return {
                'success': True,
                'has_solution': False,
                'target_budget': B,
                'lower_bound': L,
                'preferred_upper_bound': U_pref,
                'absolute_upper_bound': U_abs,
                'error_type': 'no_sectors_selected',
                'message': _("يرجى اختيار قطاع واحد على الأقل من قطاعات جهاز العروسة."),
                'recommendations': [],
            }

        # Filter candidate products per sector
        sector_candidates = {}
        all_candidate_ids = []
        for code, is_active, label, keywords, mat, min_p, weight in selected_sector_defs:
            or_clauses = [('name', 'ilike', kw) for kw in keywords]
            if mat:
                or_clauses.append(('material_type', '=', mat))
            sector_dom = ['|'] * (len(or_clauses) - 1) + or_clauses if len(or_clauses) > 1 else or_clauses
            base_dom = [('sale_ok', '=', True), ('active', '=', True)] + sector_dom

            # Prefer authentic items with price >= min_p
            prods = Product.search(base_dom + [('list_price', '>=', min_p)], order='list_price asc')
            if not prods:
                prods = Product.search(base_dom + [('list_price', '>', 0)], order='list_price asc')

            if not prods:
                return {
                    'success': True,
                    'has_solution': False,
                    'target_budget': B,
                    'lower_bound': L,
                    'preferred_upper_bound': U_pref,
                    'absolute_upper_bound': U_abs,
                    'error_type': 'sector_missing_products',
                    'message': _("لا توجد منتجات مسجلة في الكتالوج لقطاع %s.") % label,
                    'recommendations': [],
                }

            # Select representative tiered candidate products
            n = len(prods)
            if n <= 5:
                chosen = list(prods)
            else:
                indices = sorted(list(set([0, max(0, n // 5), max(0, (2 * n) // 5), max(0, (3 * n) // 5), max(0, (4 * n) // 5), n - 1])))
                chosen = [prods[i] for i in indices]

            sector_candidates[code] = {
                'label': label,
                'weight': weight,
                'products': chosen,
            }
            all_candidate_ids.extend([p.id for p in chosen])

        # Batch query branch availability
        all_candidate_ids = list(set(all_candidate_ids))
        stock_res = res_model.get_branch_stock_availability(all_candidate_ids, pos_config_id)
        prods_stock = stock_res.get('products', {}) if stock_res.get('success') else {}
        current_wh_id = stock_res.get('current_warehouse_id')

        # Cache product pricing and stock
        product_cache = {}
        for pid in all_candidate_ids:
            p = Product.browse(pid)
            tax_inc, unit_p, tax_amt = self.compute_tax_included_price(p, pricelist, partner)
            stock_info = prods_stock.get(p.id, {})
            branches = stock_info.get('branches', [])
            cur_free = 0.0
            rem_free = 0.0
            for b in branches:
                if b.get('is_current'):
                    cur_free += b.get('qty_free', 0.0)
                else:
                    rem_free += b.get('qty_free', 0.0)
            avail_score = 100 if cur_free >= 1.0 else (60 if rem_free >= 1.0 else 10)
            product_cache[p.id] = {
                'product': p,
                'tax_included_price': tax_inc,
                'unit_price': unit_p,
                'tax_amount': tax_amt,
                'current_branch_free': cur_free,
                'remote_free': rem_free,
                'total_network_free': stock_info.get('total_network_free', 0.0),
                'branches': branches,
                'avail_score': avail_score,
            }

        # Check Hard Constraint Bounds
        sector_codes = list(sector_candidates.keys())
        min_possible_total = sum(min(product_cache[p.id]['tax_included_price'] for p in sector_candidates[c]['products']) for c in sector_codes)
        max_possible_total = sum(max(product_cache[p.id]['tax_included_price'] for p in sector_candidates[c]['products']) for c in sector_codes)

        if min_possible_total > U_abs:
            diff = min_possible_total - U_abs
            sector_breakdown = [f"{sector_candidates[c]['label']}: {min(product_cache[p.id]['tax_included_price'] for p in sector_candidates[c]['products']):.2f} ج.م" for c in sector_codes]
            diag = {
                'error_type': 'budget_too_low',
                'min_possible_total': min_possible_total,
                'diff': diff,
                'sector_breakdown': sector_breakdown,
                'message': _(
                    "لا يمكن تشكيل باكدج يغطي جميع القطاعات المطلوبة ضمن ميزانية العميل.\n"
                    "أقل تكلفة ممكنة للأصناف الأساسية هي %(min_tot).2f ج.م، "
                    "وهي تتجاوز سقف الميزانية الأقصى (%(abs_bound).2f ج.م) بمقدار +%(diff).2f ج.م."
                ) % {'min_tot': min_possible_total, 'abs_bound': U_abs, 'diff': diff},
                'suggestions': [
                    _("إلغاء تحديد بعض القطاعات التكميلية (مثل الأجهزة أو أطقم المائدة)."),
                    _("زيادة ميزانية العميل المستهدفة لتتناسب مع القطاعات المحددة."),
                ],
            }
            return {
                'success': True,
                'has_solution': False,
                'target_budget': B,
                'lower_bound': L,
                'preferred_upper_bound': U_pref,
                'absolute_upper_bound': U_abs,
                'bounds': {
                    'lower_bound': L,
                    'preferred_upper_bound': U_pref,
                    'absolute_upper_bound': U_abs,
                },
                'min_possible_total': min_possible_total,
                'error_type': 'budget_too_low',
                'message': diag['message'],
                'suggestions': diag['suggestions'],
                'sector_breakdown': sector_breakdown,
                'no_solution_diagnostics': diag,
                'recommendations': [],
            }

        if max_possible_total < L:
            return {
                'success': True,
                'has_solution': False,
                'target_budget': B,
                'lower_bound': L,
                'preferred_upper_bound': U_pref,
                'absolute_upper_bound': U_abs,
                'max_possible_total': max_possible_total,
                'error_type': 'budget_too_high_for_sectors',
                'message': _(
                    "الميزانية المستهدفة (%(budget).2f ج.م) أعلى من قيمة القطاعات المختارة.\n"
                    "أعلى تكلفة ممكنة للقطاعات هي %(max_tot).2f ج.م (أقل من الحد الأدنى %(lower).2f ج.م)."
                ) % {'budget': B, 'max_tot': max_possible_total, 'lower': L},
                'suggestions': [
                    _("إضافة قطاعات إضافية لتجهيز العروسة للوصول للميزانية المستهدفة."),
                    _("تعديل الميزانية لتتوافق مع القطاعات المطلوبة."),
                ],
                'recommendations': [],
            }

        # Bounded Branch-and-Bound Combination Search
        mins = [min(product_cache[p.id]['tax_included_price'] for p in sector_candidates[c]['products']) for c in sector_codes]
        maxs = [max(product_cache[p.id]['tax_included_price'] for p in sector_candidates[c]['products']) for c in sector_codes]
        k = len(sector_codes)

        min_suffix = [0.0] * (k + 1)
        max_suffix = [0.0] * (k + 1)
        for i in range(k - 1, -1, -1):
            min_suffix[i] = min_suffix[i + 1] + mins[i]
            max_suffix[i] = max_suffix[i + 1] + maxs[i]

        valid_combinations = []

        def search_combos(idx, current_price, current_items):
            if idx == k:
                if L <= current_price <= U_abs:
                    valid_combinations.append((current_price, list(current_items)))
                return
            if current_price + min_suffix[idx] > U_abs:
                return
            if current_price + max_suffix[idx] < L:
                return
            code = sector_codes[idx]
            for p in sector_candidates[code]['products']:
                price = product_cache[p.id]['tax_included_price']
                if current_price + price + min_suffix[idx + 1] <= U_abs:
                    current_items.append(p.id)
                    search_combos(idx + 1, current_price + price, current_items)
                    current_items.pop()

        search_combos(0, 0.0, [])

        if not valid_combinations:
            return {
                'success': True,
                'has_solution': False,
                'target_budget': B,
                'lower_bound': L,
                'preferred_upper_bound': U_pref,
                'absolute_upper_bound': U_abs,
                'bounds': {
                    'lower_bound': L,
                    'preferred_upper_bound': U_pref,
                    'absolute_upper_bound': U_abs,
                },
                'error_type': 'no_combination_in_range',
                'message': _("لم يتم العثور على تشكيلة مطابقة بدقة ضمن نطاق الميزانية المسموح."),
                'suggestions': [
                    _("تعديل القطاعات المختارة أو توسيع نطاق التسامح بالميزانية."),
                ],
                'no_solution_diagnostics': {
                    'error_type': 'no_combination_in_range',
                    'suggestions': [
                        _("تعديل القطاعات المختارة أو توسيع نطاق التسامح بالميزانية."),
                    ],
                },
                'recommendations': [],
            }

        # Partition combinations
        pref_combos = [c for c in valid_combinations if c[0] <= U_pref]
        ext_combos = [c for c in valid_combinations if c[0] > U_pref and c[0] <= U_abs]

        def build_option_dict(opt_type, name, tot_price, item_ids, reason, status):
            lines = []
            tot_tax = 0.0
            tot_undisc = 0.0
            loc_count = 0
            rem_count = 0
            wait_count = 0
            for pid in item_ids:
                info = product_cache[pid]
                p = info['product']
                lines.append({
                    'product_id': p.id,
                    'name': p.display_name,
                    'default_code': p.default_code or '',
                    'barcode': p.barcode or '',
                    'quantity': 1.0,
                    'unit_price': info['unit_price'],
                    'price_subtotal': info['unit_price'],
                    'tax_included_price': info['tax_included_price'],
                    'tax_amount': info['tax_amount'],
                    'categ_name': p.categ_id.name if p.categ_id else '',
                    'is_alternative': False,
                    'current_branch_free': info['current_branch_free'],
                    'remote_free': info['remote_free'],
                    'total_network_free': info['total_network_free'],
                    'branches': info['branches'],
                    'sourcing_status': 'local_available' if info['current_branch_free'] >= 1.0 else ('remote_available' if info['remote_free'] >= 1.0 else 'waitlisted'),
                    'fulfillment_type': 'transfer',
                })
                tot_tax += info['tax_amount']
                tot_undisc += info['unit_price']
                if info['current_branch_free'] >= 1.0:
                    loc_count += 1
                elif info['remote_free'] >= 1.0:
                    rem_count += 1
                else:
                    wait_count += 1

            variance = tot_price - B
            return {
                'type': opt_type,
                'name': name,
                'total_price': round(tot_price, 2),
                'undiscounted_price': round(tot_undisc, 2),
                'tax_amount': round(tot_tax, 2),
                'variance': round(variance, 2),
                'variance_status': status,
                'item_count': len(item_ids),
                'local_item_count': loc_count,
                'remote_item_count': rem_count,
                'waitlist_item_count': wait_count,
                'lines': lines,
                'reason': reason,
                'item_ids': item_ids,
            }

        recommendations = []
        selected_item_signatures = set()

        # 1. Best Budget Match (Primary)
        pool = pref_combos if pref_combos else ext_combos
        pool_sorted = sorted(pool, key=lambda c: (abs(c[0] - B), -sum(product_cache[pid]['avail_score'] for pid in c[1])))
        best = pool_sorted[0]
        sig_best = tuple(sorted(best[1]))
        selected_item_signatures.add(sig_best)

        status_best = 'slightly_above_preferred' if best[0] > U_pref else ('matches_budget' if abs(best[0] - B) < 1.0 else ('below_budget' if best[0] < B else 'within_preferred'))
        recommendations.append(build_option_dict(
            'best_match',
            _('الباكدج الأفضل تطابقاً مع الميزانية'),
            best[0],
            best[1],
            _('توازن مثالي وأقرب سعر للميزانية المستهدفة مع تغطية كاملة لكافة القطاعات المختارة.'),
            status_best
        ))

        # 2. Economy Option (Below or close to budget)
        econ_candidates = [c for c in pref_combos if c[0] <= B and tuple(sorted(c[1])) not in selected_item_signatures]
        if not econ_candidates:
            econ_candidates = [c for c in pref_combos if tuple(sorted(c[1])) not in selected_item_signatures]
        if econ_candidates:
            econ_candidates_sorted = sorted(econ_candidates, key=lambda c: (c[0], -sum(product_cache[pid]['avail_score'] for pid in c[1])))
            econ = econ_candidates_sorted[0]
            selected_item_signatures.add(tuple(sorted(econ[1])))
            status_econ = 'below_budget' if econ[0] <= B else 'within_preferred'
            recommendations.append(build_option_dict(
                'economy',
                _('باكدج اقتصادي مناسب'),
                econ[0],
                econ[1],
                _('أعلى قيمة توفير تحت سقف الميزانية مع الحفاظ على الجودة المعتمدة لشركة الأهرام.'),
                status_econ
            ))

        # 3. Premium Option (Upgrade within Preferred Tolerance)
        prem_candidates = [c for c in pref_combos if c[0] >= B and tuple(sorted(c[1])) not in selected_item_signatures]
        if not prem_candidates:
            prem_candidates = [c for c in pref_combos if tuple(sorted(c[1])) not in selected_item_signatures]
        if prem_candidates:
            prem_candidates_sorted = sorted(prem_candidates, key=lambda c: (-c[0], -sum(product_cache[pid]['avail_score'] for pid in c[1])))
            prem = prem_candidates_sorted[0]
            selected_item_signatures.add(tuple(sorted(prem[1])))
            status_prem = 'within_preferred' if prem[0] <= U_pref else 'slightly_above_preferred'
            recommendations.append(build_option_dict(
                'premium',
                _('باكدج مميز ضمن حدود التسامح'),
                prem[0],
                prem[1],
                _('ترقية وموديلات أرقى ضمن الحد المفضل للميزانية (+2,500 ج.م كحد أقصى).'),
                status_prem
            ))

        # 4. Extended Option if no preferred candidates existed
        if not pref_combos and ext_combos and tol_cfg.get('enable_extended_range'):
            ext_candidates_sorted = sorted(ext_combos, key=lambda c: abs(c[0] - B))
            ext = ext_candidates_sorted[0]
            if tuple(sorted(ext[1])) not in selected_item_signatures:
                recommendations.append(build_option_dict(
                    'extended',
                    _('خيار موسع (أعلى من الحدود المفضلة بقليل)'),
                    ext[0],
                    ext[1],
                    _('لا تتوفر تشكيلة في النطاق المفضل، وهذا الخيار يقع في النطاق الموسع حتى الحد الأقصى المطلق.'),
                    'slightly_above_preferred'
                ))

        # Sort recommendations by total price ascending for clear presentation
        recommendations = sorted(recommendations, key=lambda r: r['total_price'])

        # Primary recommended option (prefer best_match, else first)
        primary = next((r for r in recommendations if r['type'] == 'best_match'), recommendations[0])

        return {
            'success': True,
            'has_solution': True,
            'target_budget': B,
            'lower_bound': L,
            'preferred_upper_bound': U_pref,
            'absolute_upper_bound': U_abs,
            'bounds': {
                'lower_bound': L,
                'preferred_upper_bound': U_pref,
                'absolute_upper_bound': U_abs,
            },
            'tolerance_config': tol_cfg,
            'recommendations': recommendations,
            'active_recommendation': primary,
            'current_warehouse_id': current_wh_id,
            # Backwards compatibility keys
            'lines': primary['lines'],
            'total_original_price': primary['total_price'],
            'budget_variance': primary['variance'],
            'budget_feedback_message': primary['reason'],
        }

    # -------------------------------------------------------------------------
    # الخوارزمية الذكية لاقتراح وتشكيل الباكدج بناءً على القطاعات والأسعار
    # -------------------------------------------------------------------------
    def action_auto_generate_balanced_package(self):
        """Backward compatibility alias for action_suggest_package_from_sectors."""
        return self.action_suggest_package_from_sectors()

    def action_suggest_package_from_sectors(self):
        """Intelligently suggests and builds bridal package lines based on seller selected sectors and budget."""
        self.ensure_one()
        active_sectors = {
            'granite': self.sector_granite,
            'stainless': self.sector_stainless,
            'aluminum': self.sector_aluminum,
            'bakeware': self.sector_bakeware,
            'frypans': self.sector_frypans,
            'appliances': self.sector_appliances,
            'cutlery': self.sector_cutlery,
            'serveware': self.sector_serveware,
            'accessories': self.sector_accessories,
        }
        res = self.generate_budget_constrained_recommendations(
            self.target_budget,
            active_sectors,
            pos_config_id=self.pos_config_id.id if self.pos_config_id else False,
            partner_id=self.partner_id.id if self.partner_id else False
        )
        if not res.get('has_solution'):
            raise UserError(res.get('message', _("تعذر العثور على تشكيلة مناسبة ضمن حدود الميزانية.")))

        # Clear existing lines
        self.line_ids.unlink()

        primary = res.get('active_recommendation')
        lines_vals = []
        for line_data in primary.get('lines', []):
            lines_vals.append((0, 0, {
                'product_id': line_data['product_id'],
                'quantity': line_data.get('quantity', 1.0),
                'unit_price': line_data.get('unit_price', 0.0),
                'category_name': line_data.get('categ_name') or 'الأهرام كوك وير',
                'sourcing_status': line_data.get('sourcing_status', 'draft'),
                'fulfillment_type': line_data.get('fulfillment_type', 'transfer'),
            }))

        self.write({
            'line_ids': lines_vals,
            'state': 'calculated',
            'recommendation_type': primary.get('type', 'best_match'),
            'recommendation_reason': primary.get('reason', ''),
            'recommendation_options_json': json.dumps(res.get('recommendations', []), ensure_ascii=False),
        })

        feedback = _(
            "تم تشكيل باكدج العروسة المقيد بالميزانية بنجاح.\n"
            "الخيار المعتمد: %s | إجمالي السعر: %.2f ج.م | الميزانية: %.2f ج.م (الفرق: %+.2f ج.م).\n"
            "%s"
        ) % (
            primary.get('name'),
            primary.get('total_price'),
            self.target_budget,
            primary.get('variance'),
            primary.get('reason')
        )
        self.write({'notes': feedback})
        self.message_post(body=feedback)
        return True

    # -------------------------------------------------------------------------
    # 🔒 حوكمة طلب واعتماد ورفض الخصومات (0-5% مدير فرع / 5-7% مدير عمليات)
    # -------------------------------------------------------------------------
    def action_request_discount(self):
        """Seller submits requested discount for managerial approval"""
        self.ensure_one()
        pct = self.requested_discount_pct

        if pct <= 0.0:
            self.write({
                'discount_state': 'no_discount',
                'discount_approver_id': False,
                'discount_approval_date': False,
            })
            self.message_post(body=_("ℹ️ تم تثبيت الباكدج بالسعر الأصلي دون طلب أي خصم."))
            return True

        if pct > 7.0:
            raise ValidationError(_(
                "❌ الحد الأقصى المطلق للخصم في نظام الأهرام بالكامل هو 7% بتصريح مدير العمليات فقط! غير مسموح بنسبة تتجاوز 7%."
            ))

        if pct <= 5.0:
            self.write({'discount_state': 'pending_bm'})
            self.message_post(body=_(
                "📢 طلب اعتماد خصم صالة عرض: قام البائع بطلب خصم %.2f%% (قيمة: %.2f ج.م).\n"
                "الحالة: بانتظار موافقة مدير الفرع (سيدي جابر) للاعتماد أو الرفض."
            ) % (pct, self.requested_discount_amount))
        else:
            self.write({'discount_state': 'pending_ops'})
            self.message_post(body=_(
                "🚨 طلب اعتماد خصم استثنائي: قام البائع بطلب خصم %.2f%% (قيمة: %.2f ج.م).\n"
                "النسبة تتجاوز 5%% وتتطلب حصرياً موافقة مدير العمليات والتوسع (Ops Manager)."
            ) % (pct, self.requested_discount_amount))
        return True

    def action_approve_discount_branch_manager(self):
        """Branch Manager approves discounts up to 5%"""
        self.ensure_one()
        user = self.env.user
        is_bm = user.has_group('alahram_retail_demo.group_alahram_branch_manager')
        is_ops = user.has_group('alahram_retail_demo.group_alahram_ops_manager')
        is_owner = user.has_group('alahram_retail_demo.group_alahram_owner')
        is_admin = user.has_group('base.group_system')

        if not (is_bm or is_ops or is_owner or is_admin):
            raise AccessError(_("عفواً! اعتماد الخصم حتى 5% يتطلب صلاحية 'مدير الفرع' (Branch Manager) أو الإدارة العليا!"))

        if self.requested_discount_pct > 5.0 and not (is_ops or is_owner or is_admin):
            raise AccessError(_(
                "عفواً! صلاحية مدير الفرع تتيح اعتماد خصومات حتى 5.0%% فقط!\n"
                "الخصم المطلوب (%.2f%%) يتجاوز الحد المسموح ويتطلب حصرياً اعتماد مدير العمليات والتوسع."
            ) % self.requested_discount_pct)

        self.write({
            'discount_state': 'approved',
            'discount_approver_id': user.id,
            'discount_approval_date': fields.Datetime.now(),
        })
        self.message_post(body=_(
            "✅ تم اعتماد الخصم بنسبة %.2f%% (قيمة: %.2f ج.م) بنجاح بواسطة مدير الفرع: %s.\n"
            "صافي سعر الباكدج للعروسة بعد الخصم: %.2f ج.م."
        ) % (self.requested_discount_pct, self.requested_discount_amount, user.name, self.final_package_price))
        return True

    def action_approve_discount_ops_manager(self):
        """Operations Manager approves special discounts up to 7%"""
        self.ensure_one()
        user = self.env.user
        is_ops = user.has_group('alahram_retail_demo.group_alahram_ops_manager')
        is_owner = user.has_group('alahram_retail_demo.group_alahram_owner')
        is_admin = user.has_group('base.group_system')

        if not (is_ops or is_owner or is_admin):
            raise AccessError(_("عفواً! اعتماد الخصم الاستثنائي يتطلب حصرياً صلاحية 'مدير العمليات والتوسع' (Operations Manager)!"))

        if self.requested_discount_pct > 7.0:
            raise ValidationError(_("الحد الأقصى المطلق للخصم في نظام الأهرام بالكامل هو 7%!"))

        self.write({
            'discount_state': 'approved',
            'discount_approver_id': user.id,
            'discount_approval_date': fields.Datetime.now(),
        })
        self.message_post(body=_(
            "🌟 تم اعتماد الخصم الاستثنائي بنسبة %.2f%% (قيمة: %.2f ج.م) بواسطة مدير العمليات: %s.\n"
            "صافي سعر الباكدج للعروسة بعد الخصم: %.2f ج.م."
        ) % (self.requested_discount_pct, self.requested_discount_amount, user.name, self.final_package_price))
        return True

    def action_refuse_discount(self):
        """Branch Manager or Operations Manager refuses the requested discount"""
        self.ensure_one()
        user = self.env.user
        is_bm = user.has_group('alahram_retail_demo.group_alahram_branch_manager')
        is_ops = user.has_group('alahram_retail_demo.group_alahram_ops_manager')
        is_owner = user.has_group('alahram_retail_demo.group_alahram_owner')
        is_admin = user.has_group('base.group_system')

        if not (is_bm or is_ops or is_owner or is_admin):
            raise AccessError(_("عفواً! رفض الخصم يتطلب صلاحية مدير الفرع أو مدير العمليات!"))

        old_pct = self.requested_discount_pct
        self.write({
            'discount_state': 'refused',
            'requested_discount_pct': 0.0,
            'discount_approver_id': user.id,
            'discount_approval_date': fields.Datetime.now(),
        })
        self.message_post(body=_(
            "❌ تم رفض طلب الخصم (%.2f%%) بواسطة %s.\n"
            "تمت إعادة سعر الباكدج للعروسة إلى السعر الأصلي كاملاً (%.2f ج.م) بدون خصم."
        ) % (old_pct, user.name, self.total_original_price))
        return True

    # -------------------------------------------------------------------------
    # 📝 إصدار أمر البيع الرسمي
    # -------------------------------------------------------------------------
    def action_create_sale_order(self):
        """Create confirmed Odoo sale.order with approved discount governance"""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("يرجى تشكيل بنود الباكدج أولاً!"))

        # Verify discount approval state
        if self.discount_state in ('pending_bm', 'pending_ops'):
            raise UserError(_(
                "⚠️ لا يمكن إصدار أمر البيع قبل اعتماد الخصم المطلوب (%.2f%%) من الإدارة المختصة!\n"
                "يرجى اعتماد الخصم أو رفضه أولاً."
            ) % self.requested_discount_pct)

        SaleOrder = self.env['sale.order']
        SaleOrderLine = self.env['sale.order.line']

        order = SaleOrder.create({
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'note': _("باكدج العروسة الذكي - ميزانية مستهدفة: %.2f ج.م | صافي الباكدج: %.2f ج.م") % (
                self.target_budget, self.final_package_price
            ),
        })

        discount_to_apply = self.requested_discount_pct if self.discount_state == 'approved' else 0.0

        for line in self.line_ids:
            SaleOrderLine.create({
                'order_id': order.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'price_unit': line.unit_price,
                'discount': discount_to_apply,
            })

        self.write({
            'sale_order_id': order.id,
            'state': 'order_created',
        })

        self.message_post(body=_(
            "📝 تم إصدار أمر البيع الرسمي رقم %s بمبلغ إجمالي %.2f ج.م (خصم مطبق: %.2f%%)."
        ) % (order.name, self.final_package_price, discount_to_apply))

        return {
            'name': _('أمر البيع المنشأ'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
        }

    # -------------------------------------------------------------------------
    # 💳 تحويل مباشر للكاشير وشاشة الـ POS (Point of Sale)
    # -------------------------------------------------------------------------
    def action_send_to_pos(self):
        """Creates draft order in open branch POS session ready for checkout"""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("يرجى تشكيل بنود الباكدج أولاً!"))

        if self.discount_state in ('pending_bm', 'pending_ops'):
            raise UserError(_(
                "⚠️ لا يمكن تحويل الطلب إلى الكاشير (POS) قبل اعتماد الخصم المطلوب (%.2f%%)!\n"
                "يرجى اعتماد الخصم أو رفضه أولاً."
            ) % self.requested_discount_pct)

        # 1. Ensure Sale Order is created first if not already done
        if not self.sale_order_id:
            self.action_create_sale_order()

        # 2. Find an active open POS session for Sidi Gaber branch
        PosSession = self.env['pos.session']
        open_session = PosSession.search([
            ('state', '=', 'opened'),
            ('config_id.name', 'ilike', 'سيدي جابر')
        ], order='id desc', limit=1)

        if not open_session:
            open_session = PosSession.search([('state', '=', 'opened')], order='id desc', limit=1)

        if not open_session:
            raise UserError(_(
                "⚠️ لم يتم العثور على جلسة كاشير (POS) مفتوحة حالياً في فرع سيدي جابر!\n"
                "يرجى فتح جلسة كاشير 1 من شاشة Point of Sale أولاً لاستلام الطلب."
            ))

        PosOrder = self.env['pos.order']
        discount_to_apply = self.requested_discount_pct if self.discount_state == 'approved' else 0.0

        pos_lines = []
        for line in self.line_ids:
            pos_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'qty': line.quantity,
                'price_unit': line.unit_price,
                'discount': discount_to_apply,
                'price_subtotal': round(line.quantity * line.unit_price * (1.0 - discount_to_apply / 100.0), 2),
                'price_subtotal_incl': round(line.quantity * line.unit_price * (1.0 - discount_to_apply / 100.0), 2),
            }))

        pos_order = PosOrder.create({
            'session_id': open_session.id,
            'partner_id': self.partner_id.id,
            'lines': pos_lines,
            'pos_reference': f"POS-BRIDAL/{self.name}",
            'amount_total': self.final_package_price,
            'amount_tax': 0.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'state': 'draft',
        })

        self.write({
            'pos_order_id': pos_order.id,
            'state': 'sent_to_pos',
        })

        self.message_post(body=_(
            "💳 تم تحويل باكدج العروسة بنجاح إلى شاشة الكاشير (POS):\n"
            "- جلسة الكاشير: %s (%s)\n"
            "- رقم أمر الكاشير: %s\n"
            "- إجمالي المبلغ المطلوب تحصيله: %.2f ج.م (شامل الخصم المعتمد %.2f%%).\n"
            "الطلب جاهز حالياً على جهاز الكاشير لطباعة الفاتورة الفورية واستلام النقدية أو الفيزا."
        ) % (open_session.name, open_session.config_id.name, pos_order.pos_reference, self.final_package_price, discount_to_apply))

        return {
            'name': _('أمر الكاشير (Point of Sale)'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'res_id': pos_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # -------------------------------------------------------------------------
    # 📱 POS Tablet Service API & Integration Methods
    # -------------------------------------------------------------------------
    @api.model
    def get_pos_bridal_init_data(self, pos_config_id=False):
        """Returns initial metadata for POS Smart Bridal Package tablet dialog."""
        pos_cfg = self.env['pos.config'].browse(pos_config_id) if pos_config_id else False
        res_model = self.env['alahram.branch.reservation']
        current_wh_id = res_model._get_branch_from_pos_config(pos_cfg)
        current_wh = self.env['stock.warehouse'].browse(current_wh_id)

        sectors = [
            {'code': 'granite', 'name': 'أطقم حلل جرانيت (صحي غير لاصق)', 'icon': 'fa-shield', 'default': True},
            {'code': 'stainless', 'name': 'أطقم ستانلس ستيل 18/10 (سيجنتشر / زينوكس)', 'icon': 'fa-cutlery', 'default': True},
            {'code': 'aluminum', 'name': 'أطقم ألومنيوم كلاسيك (نقي 99.5%)', 'icon': 'fa-circle-o', 'default': False},
            {'code': 'bakeware', 'name': 'صواني فرن ومخبوزات وقوالب كيك', 'icon': 'fa-square-o', 'default': True},
            {'code': 'frypans', 'name': 'طاسات تحمير ومقالي كريب وشوايات جريل', 'icon': 'fa-fire', 'default': True},
            {'code': 'appliances', 'name': 'أجهزة كهربائية صغيرة وخلاطات وهاند بلندر', 'icon': 'fa-bolt', 'default': False},
            {'code': 'cutlery', 'name': 'أطقم ملاعق وسكاكين وشوك ومقصات مطبخ', 'icon': 'fa-spoon', 'default': False},
            {'code': 'serveware', 'name': 'صواني تقديم وأطقم شاي وقهوة وزجاجيات', 'icon': 'fa-coffee', 'default': False},
            {'code': 'accessories', 'name': 'إكسسوارات ومفروشات وموزعات سيليكون', 'icon': 'fa-magic', 'default': False},
        ]

        # Fetch active products suitable for bridal packages
        products = self.env['product.product'].search([
            ('sale_ok', '=', True),
            ('active', '=', True)
        ], limit=300)

        prods_data = []
        for p in products:
            prods_data.append({
                'id': p.id,
                'name': p.name,
                'display_name': p.display_name,
                'default_code': p.default_code or '',
                'barcode': p.barcode or '',
                'list_price': p.lst_price,
                'categ_id': p.categ_id.id if p.categ_id else False,
                'categ_name': p.categ_id.name if p.categ_id else '',
                'material_type': getattr(p.product_tmpl_id, 'material_type', 'aluminum'),
            })

        user = self.env.user
        is_bm = user.has_group('alahram_retail_demo.group_alahram_branch_manager') or user.has_group('base.group_system')
        is_ops = user.has_group('alahram_retail_demo.group_alahram_ops_manager') or user.has_group('base.group_system')
        is_owner = user.has_group('alahram_retail_demo.group_alahram_owner') or user.has_group('base.group_system')

        tiers = [
            {'code': 'silver_15k', 'name': 'باكدج فضي اقتصادي', 'budget': 15000.0},
            {'code': 'gold_20k', 'name': 'باكدج ذهبي مميز', 'budget': 20000.0},
            {'code': 'platinum_30k', 'name': 'باكدج بلاتينيوم متكامل', 'budget': 30000.0},
            {'code': 'royal_45k', 'name': 'باكدج ملكي فاخر', 'budget': 45000.0},
            {'code': 'custom', 'name': 'ميزانية مخصصة', 'budget': 20000.0},
        ]

        return {
            'success': True,
            'current_warehouse_id': current_wh_id,
            'current_warehouse_name': current_wh.name if current_wh else '',
            'sectors': sectors,
            'tiers': tiers,
            'products': prods_data,
            'user_permissions': {
                'is_branch_manager': is_bm,
                'is_ops_manager': is_ops,
                'is_owner': is_owner,
                'user_name': user.name,
                'user_id': user.id,
            }
        }

    @api.model
    def get_product_alternatives_pos(self, product_id, pos_config_id=False):
        """Finds eligible substitute products and their live multi-branch availability."""
        product = self.env['product.product'].browse(product_id)
        if not product.exists():
            return {'success': False, 'error': 'الصنف غير موجود.'}

        categ_id = product.categ_id.id
        material_type = getattr(product.product_tmpl_id, 'material_type', False)

        domain = [
            ('id', '!=', product.id),
            ('sale_ok', '=', True),
            ('active', '=', True),
        ]
        if categ_id:
            domain.append(('categ_id', '=', categ_id))
        elif material_type:
            domain.append(('product_tmpl_id.material_type', '=', material_type))

        candidates = self.env['product.product'].search(domain, limit=8)
        if not candidates and material_type:
            candidates = self.env['product.product'].search([
                ('id', '!=', product.id),
                ('product_tmpl_id.material_type', '=', material_type)
            ], limit=8)

        if not candidates:
            return {'success': True, 'alternatives': []}

        # Check real stock availability across branches
        res_model = self.env['alahram.branch.reservation']
        stock_res = res_model.get_branch_stock_availability(candidates.ids, pos_config_id)
        prods_stock = stock_res.get('products', {}) if stock_res.get('success') else {}

        alternatives = []
        for c in candidates:
            stock_info = prods_stock.get(c.id, {})
            price_diff = c.lst_price - product.lst_price
            alternatives.append({
                'id': c.id,
                'name': c.name,
                'display_name': c.display_name,
                'default_code': c.default_code or '',
                'barcode': c.barcode or '',
                'list_price': c.lst_price,
                'price_diff': price_diff,
                'categ_name': c.categ_id.name if c.categ_id else '',
                'total_network_free': stock_info.get('total_network_free', 0.0),
                'branches': stock_info.get('branches', []),
            })

        # Sort: products with positive network stock first, then closest price
        alternatives.sort(key=lambda x: (x['total_network_free'] <= 0, abs(x['price_diff'])))

        return {
            'success': True,
            'original_product_id': product.id,
            'original_product_name': product.display_name,
            'original_price': product.lst_price,
            'alternatives': alternatives,
        }

    @api.model
    def suggest_package_pos(self, vals):
        """Generates intelligent package suggestion from sectors and target budget for POS tablet."""
        target_budget = float(vals.get('target_budget', 20000.0))
        active_sectors = vals.get('sectors', {})
        pos_config_id = vals.get('pos_config_id', False)
        partner_id = vals.get('partner_id', False)

        return self.generate_budget_constrained_recommendations(
            target_budget=target_budget,
            active_sectors=active_sectors,
            pos_config_id=pos_config_id,
            partner_id=partner_id
        )

    @api.model
    def save_and_reserve_package_pos(self, vals):
        """Atomic POS method to save bridal package and execute multi-branch reservation."""
        if not vals:
            raise UserError(_("بيانات الباكدج غير مكتملة."))

        idempotency_key = vals.get('idempotency_key')
        if idempotency_key:
            existing = self.search([('idempotency_key', '=', idempotency_key)], limit=1)
            if existing:
                return {
                    'success': True,
                    'package_id': existing.id,
                    'name': existing.name,
                    'final_package_price': existing.final_package_price,
                    'state': existing.state,
                    'is_duplicate': True
                }

        partner_id = vals.get('partner_id')
        cust_name = vals.get('customer_name')
        cust_phone = vals.get('customer_phone')
        target_budget = float(vals.get('target_budget', 20000.0))
        requested_discount_pct = float(vals.get('requested_discount_pct', 0.0))
        pos_config_id = vals.get('pos_config_id')
        pos_session_id = vals.get('pos_session_id')
        lines_data = vals.get('lines', [])

        if not lines_data:
            raise UserError(_("لا توجد أصناف في الباكدج!"))

        # Smart Partner Resolution (prevent walk-in crashes)
        if not partner_id:
            if cust_phone:
                partner = self.env['res.partner'].search([('phone', '=', cust_phone)], limit=1)
                if not partner:
                    partner = self.env['res.partner'].create({
                        'name': cust_name or f"عميل {cust_phone}",
                        'phone': cust_phone,
                    })
                partner_id = partner.id
            elif cust_name:
                partner = self.env['res.partner'].search([('name', '=', cust_name)], limit=1)
                if not partner:
                    partner = self.env['res.partner'].create({
                        'name': cust_name,
                    })
                partner_id = partner.id
            else:
                generic = self.env['res.partner'].search([('name', '=', 'عميل باكدج عروسة عام')], limit=1)
                if not generic:
                    generic = self.env['res.partner'].create({'name': 'عميل باكدج عروسة عام'})
                partner_id = generic.id

        # Budget Tolerance Boundary Enforcement
        tol_cfg = self.get_bridal_budget_tolerance_config()
        abs_bound = target_budget + tol_cfg['tolerance_above_abs']
        lower_bound = max(0.0, target_budget - tol_cfg['tolerance_below'])
        total_undisc = sum(float(l.get('quantity', 1.0)) * float(l.get('unit_price', 0.0)) for l in lines_data)
        if total_undisc > abs_bound:
            is_ops = self.env.user.has_group('alahram_retail_demo.group_alahram_ops_manager') or self.env.user.has_group('base.group_system')
            if not is_ops and not vals.get('manager_approved'):
                raise ValidationError(_(
                    "خطأ في سقف الميزانية:\n"
                    "إجمالي سعر الباكدج (%.2f ج.م) يتجاوز الحد الأقصى المطلق لميزانية العميل (%.2f ج.م) بمقدار +%.2f ج.م!\n"
                    "لا يمكن تأكيد الباكدج كتوصية ميزانية معتمدة إلا بموافقة مدير العمليات أو تعديل التشكيلة لتناسب سقف الميزانية."
                ) % (total_undisc, abs_bound, total_undisc - target_budget))
        if lower_bound > 0 and total_undisc < lower_bound:
            is_bm = self.env.user.has_group('alahram_retail_demo.group_alahram_branch_manager') or self.env.user.has_group('alahram_retail_demo.group_alahram_ops_manager') or self.env.user.has_group('base.group_system')
            if not is_bm and not vals.get('manager_approved'):
                raise ValidationError(_(
                    "تنبيه حد الميزانية الأدنى:\n"
                    "إجمالي سعر الباكدج (%.2f ج.م) أقل من الحد الأدنى المقبول (%.2f ج.م) بعجز قدره %.2f ج.م عن الحد الأدنى (وفارق %.2f ج.م عن الميزانية المستهدفة).\n"
                    "يرجى استكمال بنود الباكدج أو اعتماد مدير الفرع."
                ) % (total_undisc, lower_bound, lower_bound - total_undisc, target_budget - total_undisc))

        # Discount Governance Validation
        if requested_discount_pct > 7.0:
            raise ValidationError(_(
                "خطأ حرج في حوكمة الخصومات بالأهرام:\n"
                "الحد الأقصى المطلق للخصم في نظام شركة الأهرام بالكامل هو 7% بتصريح مدير العمليات فقط!\n"
                "غير مسموح نهائياً بمنح أو طلب خصم يتجاوز 7% (النسبة المطلوبة: %.2f%%)."
            ) % requested_discount_pct)
        if requested_discount_pct < 0.0:
            raise ValidationError(_("لا يمكن أن تكون نسبة الخصم سالبة!"))

        user = self.env.user
        approver_id = False
        approval_date = False
        discount_state = 'no_discount'

        if requested_discount_pct > 0.0:
            is_bm = user.has_group('alahram_retail_demo.group_alahram_branch_manager')
            is_ops = user.has_group('alahram_retail_demo.group_alahram_ops_manager')
            is_admin = user.has_group('base.group_system') or user.has_group('alahram_retail_demo.group_alahram_owner')

            # Check if manager approval was provided directly
            manager_pin_verified = vals.get('manager_approved', False)
            if requested_discount_pct <= 5.0:
                if is_bm or is_ops or is_admin or manager_pin_verified:
                    discount_state = 'approved'
                    approver_id = user.id
                    approval_date = fields.Datetime.now()
                else:
                    discount_state = 'pending_bm'
            else: # 5.01% to 7.0%
                if is_ops or is_admin or (manager_pin_verified and vals.get('manager_role') == 'ops'):
                    discount_state = 'approved'
                    approver_id = user.id
                    approval_date = fields.Datetime.now()
                else:
                    discount_state = 'pending_ops'

        pos_cfg = self.env['pos.config'].browse(pos_config_id) if pos_config_id else False
        res_model = self.env['alahram.branch.reservation']
        current_wh_id = res_model._get_branch_from_pos_config(pos_cfg)

        package_vals = {
            'partner_id': partner_id,
            'target_budget': target_budget,
            'requested_discount_pct': requested_discount_pct,
            'discount_state': discount_state,
            'discount_approver_id': approver_id,
            'discount_approval_date': approval_date,
            'warehouse_id': current_wh_id,
            'pos_config_id': pos_config_id,
            'pos_session_id': pos_session_id,
            'salesperson_id': user.id,
            'fulfillment_strategy': vals.get('fulfillment_strategy', 'consolidated'),
            'delivery_preference': vals.get('delivery_preference', 'all_together'),
            'expected_delivery_date': vals.get('expected_delivery_date') or False,
            'customer_notes': vals.get('customer_notes') or '',
            'substitution_history': json.dumps(vals.get('substitution_history', []), ensure_ascii=False),
            'idempotency_key': idempotency_key,
            'recommendation_type': vals.get('package_type', 'best_match'),
            'state': 'calculated',
        }

        package = self.create(package_vals)

        # Create package lines
        created_lines = []
        reservation_items = []
        for l in lines_data:
            prod_id = l.get('product_id')
            prod = self.env['product.product'].browse(prod_id)
            if not prod.exists():
                continue
            qty = float(l.get('quantity', 1.0))
            price = float(l.get('unit_price', prod.lst_price))
            fulfillment_type = l.get('fulfillment_type', 'transfer')
            source_wh_id = l.get('source_warehouse_id') or current_wh_id

            line = self.env['alahram.bridal.configurator.line'].create({
                'configurator_id': package.id,
                'product_id': prod.id,
                'original_product_id': l.get('original_product_id') or False,
                'is_alternative': bool(l.get('is_alternative')),
                'substitution_reason': l.get('substitution_reason') or '',
                'customer_approved': bool(l.get('customer_approved')),
                'quantity': qty,
                'unit_price': price,
                'category_name': prod.categ_id.name if prod.categ_id else '',
                'fulfillment_type': fulfillment_type,
                'source_warehouse_id': source_wh_id,
                'destination_warehouse_id': current_wh_id,
                'sourcing_status': l.get('sourcing_status', 'draft'),
            })
            created_lines.append(line)

            # Build item payload for atomic reservation call
            allocations = l.get('allocations', [])
            if not allocations:
                # Default single allocation from selected source warehouse
                allocations = [{
                    'source_warehouse_id': source_wh_id,
                    'qty': qty,
                    'fulfillment_type': fulfillment_type,
                }]
            reservation_items.append({
                'product_id': prod.id,
                'qty_requested': qty,
                'price_unit': price,
                'allocations': allocations,
            })

        # Atomic Multi-Branch Reservation via Existing Engine
        do_reserve = vals.get('do_reserve', True)
        reservation_result = {}
        if do_reserve and reservation_items:
            res_payload = {
                'partner_id': partner_id,
                'customer_name': package.partner_id.name,
                'customer_phone': package.partner_id.phone or package.partner_id.mobile,
                'pos_config_id': pos_config_id,
                'pos_session_id': pos_session_id,
                'salesperson_id': user.id,
                'idempotency_key': f"RES-{idempotency_key}" if idempotency_key else False,
                'notes': f"Bridal Package Reservation: {package.name}",
                'items': reservation_items,
            }
            reservation_result = res_model.create_from_pos(res_payload)
            if reservation_result.get('success'):
                res_id = reservation_result.get('reservation_id')
                res_record = res_model.browse(res_id)
                res_record.bridal_configurator_id = package.id
                package.reservation_id = res_id

                # Map allocations back to package lines
                for line in created_lines:
                    alloc = res_record.allocation_ids.filtered(lambda a: a.product_id == line.product_id)[:1]
                    if alloc:
                        line.allocation_id = alloc.id
                        line.picking_id = alloc.picking_id.id if alloc.picking_id else False
                        if alloc.fulfillment_type == 'pickup':
                            line.sourcing_status = 'source_pickup_ready'
                        elif alloc.fulfillment_type == 'direct_delivery':
                            line.sourcing_status = 'direct_delivery_ready'
                        elif alloc.source_warehouse_id.id == current_wh_id:
                            line.sourcing_status = 'local_reserved'
                        else:
                            line.sourcing_status = 'transfer_requested'
                    else:
                        wait = res_record.waitlist_line_ids.filtered(lambda w: w.product_id == line.product_id)[:1]
                        if wait:
                            line.sourcing_status = 'waitlisted'

        package._compute_totals()

        return {
            'success': True,
            'package_id': package.id,
            'configurator_id': package.id,
            'name': package.name,
            'total_original_price': package.total_original_price,
            'requested_discount_pct': package.requested_discount_pct,
            'package_discount_amount': package.package_discount_amount,
            'final_package_price': package.final_package_price,
            'discount_state': package.discount_state,
            'reservation_id': package.reservation_id.id if package.reservation_id else False,
            'reservation_name': package.reservation_id.name if package.reservation_id else '',
            'reservation_result': reservation_result,
        }

    @api.model
    def load_package_to_pos_cart(self, package_id, pos_session_id=False):
        """Prepares confirmed package items with approved discounts for POS cart injection."""
        package = self.browse(package_id)
        if not package.exists():
            return {'success': False, 'error': 'باكدج العروسة غير موجود.'}

        if package.discount_state in ('pending_bm', 'pending_ops'):
            return {
                'success': False,
                'error': _('لا يمكن تحصيل قيمة الباكدج في الـ POS قبل اعتماد الخصم المطلوب (%.2f%%) من الإدارة!') % package.requested_discount_pct
            }

        discount_to_apply = package.requested_discount_pct if package.discount_state == 'approved' else 0.0

        cart_items = []
        for line in package.line_ids:
            cart_items.append({
                'product_id': line.product_id.id,
                'name': line.product_id.display_name,
                'quantity': line.quantity,
                'price_unit': line.unit_price,
                'discount': discount_to_apply,
            })

        return {
            'success': True,
            'package_id': package.id,
            'package_name': package.name,
            'partner_id': package.partner_id.id,
            'partner_name': package.partner_id.name,
            'final_package_price': package.final_package_price,
            'discount': discount_to_apply,
            'items': cart_items,
        }

    def action_cancel_package_and_reservation(self):
        """Cancels bridal package and releases its cross-branch reservations atomically."""
        for rec in self:
            if rec.reservation_id and rec.reservation_id.state != 'cancelled':
                rec.reservation_id.action_cancel()
            rec.line_ids.write({'sourcing_status': 'exception'})
            rec.state = 'draft'
            rec.message_post(body=_("تم إلغاء باكدج العروسة وإلغاء حجز الفروع والمخازن المرتبطة به بنجاح."))
        return True


class AlahramBridalConfiguratorLine(models.Model):
    _name = 'alahram.bridal.configurator.line'
    _description = 'بند تشكيلة باكدج العروسة'

    configurator_id = fields.Many2one('alahram.bridal.configurator', string='الباكدج', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='الصنف', required=True)
    product_barcode = fields.Char(related='product_id.barcode', string='الباركود')
    category_name = fields.Char(string='التصنيف العائلي')
    quantity = fields.Float(string='الكمية', default=1.0)
    unit_price = fields.Float(string='سعر الوحدة (ج.م)')
    price_subtotal = fields.Float(string='الإجمالي (ج.م)', compute='_compute_subtotal', store=True)

    # Substitution & Multi-Branch Sourcing Fields
    original_product_id = fields.Many2one('product.product', string='Original Product / الصنف الأصلي المستبدل')
    is_alternative = fields.Boolean(string='Is Alternative / صنف بديل', default=False)
    substitution_reason = fields.Char(string='Substitution Reason / سبب الاستبدال')
    customer_approved = fields.Boolean(string='Customer Approved / موافقة العميل', default=False)
    sourcing_status = fields.Selection([
        ('draft', 'Draft / مسودة'),
        ('local_available', 'Available Locally / متوفر بالفرع'),
        ('local_reserved', 'Reserved Locally / محجوز بالفرع'),
        ('remote_available', 'Available Remotely / متوفر بفرع آخر'),
        ('transfer_requested', 'Transfer Requested / طلب تحويل'),
        ('in_transit', 'In Transit / بالطريق'),
        ('received', 'Received at Branch / تم الاستلام بالفرع'),
        ('source_pickup_ready', 'Ready for Pickup / جاهز للاستلام من الفرع'),
        ('direct_delivery_ready', 'Ready for Direct Delivery / جاهز للشحن المباشر'),
        ('waitlisted', 'Waitlisted / قائمة الانتظار'),
        ('exception', 'Exception / استثناء أو عجز')
    ], string='Sourcing Status / حالة التوفير', default='draft')
    source_warehouse_id = fields.Many2one('stock.warehouse', string='Source Branch / فرع التجهيز')
    destination_warehouse_id = fields.Many2one('stock.warehouse', string='Dest Branch / فرع الاستلام')
    fulfillment_type = fields.Selection([
        ('transfer', 'Internal Transfer / شحن للفرع البائع'),
        ('pickup', 'Source Branch Pickup / استلام من الفرع المصدر'),
        ('direct_delivery', 'Direct Delivery / توصيل مباشر للعميل')
    ], string='Fulfillment Method / طريقة الاستلام', default='transfer')
    allocation_id = fields.Many2one('alahram.branch.reservation.allocation', string='Allocation / التخصيص', ondelete='set null')
    picking_id = fields.Many2one('stock.picking', string='Stock Picking / حركة المخزن', ondelete='set null')

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = round(line.quantity * line.unit_price, 2)
