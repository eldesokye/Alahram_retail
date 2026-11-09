# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

class AlahramStockRecommendation(models.Model):
    _name = 'alahram.stock.recommendation'
    _description = 'لوحة التوصيات الذكية لنقل المخزون وتدوير الركود'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority_score desc, id desc'

    name = fields.Char(string='رقم التوصية', required=True, copy=False, readonly=True, default=lambda self: _('REC-NEW'))
    product_id = fields.Many2one('product.product', string='الصنف المرشح للنقل', required=True, tracking=True)
    product_code = fields.Char(related='product_id.default_code', string='كود الصنف')
    product_barcode = fields.Char(related='product_id.barcode', string='الباركود')
    categ_id = fields.Many2one('product.category', related='product_id.categ_id', string='التصنيف')
    list_price = fields.Float(related='product_id.list_price', string='سعر البيع الرسمي')
    standard_price = fields.Float(related='product_id.standard_price', string='متوسط التكلفة')

    src_warehouse_id = fields.Many2one('stock.warehouse', string='الفرع المصدر (المخزون الراكد / الفائض)', required=True, tracking=True)
    dest_warehouse_id = fields.Many2one('stock.warehouse', string='فرع الوجهة (فرع النقص / الطلب المرتفع)', required=True, tracking=True)
    
    suggested_qty = fields.Float(string='الكمية المقترح نقلها', default=10.0, required=True, tracking=True)
    dead_stock_qty = fields.Float(string='رصيد المخزون في الفرع المصدر', default=0.0)
    dead_stock_cost = fields.Float(string='قيمة التكلفة المجمدة (ج.م)', default=0.0)
    october_sales = fields.Float(string='مبيعات أكتوبر بالفرع المصدر', default=0.0)
    
    reason = fields.Text(string='مبررات التوصية والتحليل الذكي', tracking=True)
    priority = fields.Selection([
        ('urgent', 'عاجل (تصفية ركود حاد)'),
        ('high', 'مرتفع (طلب سيدي جابر)'),
        ('medium', 'متوسط (إعادة توازن)'),
        ('low', 'منخفض (إمداد دوري)'),
    ], string='درجة الأولوية', default='high', tracking=True)
    priority_score = fields.Integer(string='درجة الأهمية', compute='_compute_priority_score', store=True)

    state = fields.Selection([
        ('pending', 'بانتظار اعتماد مدير العمليات'),
        ('approved', 'تم الاعتماد وإنشاء أمر النقل'),
        ('rejected', 'تم تجاهل التوصية'),
    ], string='الحالة', default='pending', tracking=True)

    picking_id = fields.Many2one('stock.picking', string='إذن التحويل المخزني المنشأ', readonly=True)
    data_source_indicator = fields.Char(
        string='مصدر البيانات',
        default='توصية ذكية محسوبة من بيانات المخزون والمبيعات (1–28 أكتوبر 2026)',
        readonly=True
    )

    @api.depends('priority')
    def _compute_priority_score(self):
        scores = {'urgent': 4, 'high': 3, 'medium': 2, 'low': 1}
        for rec in self:
            rec.priority_score = scores.get(rec.priority, 1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('REC-NEW')) == _('REC-NEW'):
                count = self.env['alahram.stock.recommendation'].search_count([]) + 1
                vals['name'] = f"REC-2026-{count:04d}"
        return super().create(vals_list)

    def action_approve_recommendation(self):
        """Operations Manager approves recommendation and creates real stock.picking"""
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_("هذه التوصية تمت معالجتها بالفعل!"))

        # Clean context to prevent leaked default_* keys (e.g. default_priority='urgent' from Kanban groupBy)
        clean_ctx = {k: v for k, v in self.env.context.items() if not k.startswith('default_')}
        clean_ctx['default_priority'] = '1' if self.priority in ('urgent', 'high') else '0'
        StockPicking = self.env['stock.picking'].sudo().with_context(clean_ctx)
        StockMove = self.env['stock.move'].sudo().with_context(clean_ctx)

        src_loc = self.src_warehouse_id.lot_stock_id
        dest_loc = self.dest_warehouse_id.lot_stock_id

        if not src_loc or not dest_loc:
            raise UserError(_("لم يتم إعداد مواقع التخزين للفروع المحددة!"))

        picking_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', self.src_warehouse_id.id),
            ('code', '=', 'internal')
        ], limit=1) or self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)

        picking = StockPicking.create({
            'picking_type_id': picking_type.id,
            'location_id': src_loc.id,
            'location_dest_id': dest_loc.id,
            'origin': f"اعتماد توصية ذكية: {self.name}",
            'priority': '1' if self.priority in ('urgent', 'high') else '0',
        })

        StockMove.create({
            'product_id': self.product_id.id,
            'product_uom_qty': self.suggested_qty,
            'uom_id': self.product_id.uom_id.id,
            'picking_id': picking.id,
            'location_id': src_loc.id,
            'location_dest_id': dest_loc.id,
        })
        picking.action_confirm()

        self.write({
            'state': 'approved',
            'picking_id': picking.id,
        })
        self.message_post(body=_(
            "تم اعتماد التوصية الذكية بنجاح بواسطة مدير العمليات: %s.<br/>تم إنشاء إذن التحويل المخزني رقم: <b>%s</b>."
        ) % (self.env.user.name, picking.name))

        return {
            'name': _('إذن التحويل المخزني المعتمد'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_reject_recommendation(self):
        """Operations Manager rejects/dismisses recommendation"""
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_("هذه التوصية تمت معالجتها بالفعل!"))
        self.write({'state': 'rejected'})
        self.message_post(body=_("تم تجاهل التوصية بواسطة مدير العمليات: %s") % self.env.user.name)
        return True

    def action_view_picking(self):
        """Open created stock picking"""
        self.ensure_one()
        if not self.picking_id:
            raise UserError(_("لا يوجد إذن تحويل مرتبط بهذه التوصية!"))
        return {
            'name': _('إذن التحويل المخزني'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def action_seed_demo_recommendations(self):
        """Initializes mandatory master prompt recommendation records if not existing"""
        Product = self.env['product.product']
        Warehouse = self.env['stock.warehouse']

        wh_main = Warehouse.search([('code', '=', 'WH-MAIN')], limit=1) or Warehouse.search([], limit=1)
        wh_sg = Warehouse.search([('code', '=', 'WH-SG')], limit=1) or Warehouse.search([], limit=1)
        wh_roshdy = Warehouse.search([('code', '=', 'WH-ROSHDY')], limit=1) or Warehouse.search([], limit=1)

        demos = [
            {
                'barcode': '1414000000042', # شواية جرانيت Bio trade grip يد بكاليت 28
                'src': wh_main.id,
                'dest': wh_sg.id,
                'qty': 50.0,
                'dead_qty': 438.0,
                'dead_cost': 190183.98,
                'oct_sales': 0.0,
                'priority': 'urgent',
                'reason': 'الصنف راكد بدون أي حركة بيع في أكتوبر (438 قطعة بتكلفة 190,184 ج.م). التوصية: نقل 50 قطعة إلى فرع سيدي جابر لعرضها ضمن باكدجات العرائس وتسييل السيولة.',
            },
            {
                'barcode': '1433000000067', # حلة سيجنتشر ستايل ستانلس 24
                'src': wh_main.id,
                'dest': wh_sg.id,
                'qty': 40.0,
                'dead_qty': 317.0,
                'dead_cost': 176342.66,
                'oct_sales': 0.0,
                'priority': 'high',
                'reason': 'رصيد راكد 317 قطعة بتكلفة مجمدة 176,343 ج.م بدون مبيعات في أكتوبر. التوصية: إعادة توزيع 40 قطعة على معرض سيدي جابر لتلبية طلبات التجهيزات الفردانية.',
            },
            {
                'barcode': '1414000000073', # صينية فرن جرانيت 30
                'src': wh_main.id,
                'dest': wh_sg.id,
                'qty': 60.0,
                'dead_qty': 580.0,
                'dead_cost': 203510.40,
                'oct_sales': 156.0,
                'priority': 'medium',
                'reason': 'رصيد وفير (580 قطعة) مع مبيعات نشطة 156 قطعة وهامش ربح 50.62%. التوصية: دعم مخزون سيدي جابر بـ 60 قطعة تمهيداً لحملة تخفيضات 25%.',
            },
            {
                'barcode': '6221049803894', # مقلاية جرانيت Bio trade grip 20
                'src': wh_main.id,
                'dest': wh_sg.id,
                'qty': 15.0,
                'dead_qty': 27.0,
                'dead_cost': 10500.00,
                'oct_sales': 107.0,
                'priority': 'urgent',
                'reason': 'عجز حرج في معرض سيدي جابر (رصيد صفر ومبيعات أكتوبر 107 قطعة!). يتوفر في مخزن الإدارة 27 قطعة. التوصية: تحويل عاجل 15 قطعة لتفادي ضياع المبيعات.',
            },
            {
                'barcode': '6221049011701', # حلة صحي ومفيد 24
                'src': wh_roshdy.id,
                'dest': wh_sg.id,
                'qty': 3.0,
                'dead_qty': 3.0,
                'dead_cost': 1800.00,
                'oct_sales': 9.0,
                'priority': 'urgent',
                'reason': 'رصيد سيدي جابر صفر مع وجود 3 قطع في فرع رشدي القريب. التوصية: تحويل فوري ثنائي الخطوة (WH-ROSHDY -> WH-TRANSIT -> WH-SG).',
            },
        ]

        for d in demos:
            prod = Product.search([('barcode', '=', d['barcode'])], limit=1)
            if prod:
                existing = self.search([('product_id', '=', prod.id), ('state', '=', 'pending')], limit=1)
                if not existing:
                    self.create({
                        'product_id': prod.id,
                        'src_warehouse_id': d['src'],
                        'dest_warehouse_id': d['dest'],
                        'suggested_qty': d['qty'],
                        'dead_stock_qty': d['dead_qty'],
                        'dead_stock_cost': d['dead_cost'],
                        'october_sales': d['oct_sales'],
                        'priority': d['priority'],
                        'reason': d['reason'],
                    })
        return True
