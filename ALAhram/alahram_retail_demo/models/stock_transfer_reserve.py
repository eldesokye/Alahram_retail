# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AlahramCrossBranchReserve(models.Model):
    _name = 'alahram.cross.branch.reserve'
    _description = 'طلب حجز وتحويل مخزني فوري بين الفروع'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='رقم طلب الحجز', required=True, copy=False, readonly=True, default=lambda self: _('جديد'))
    partner_id = fields.Many2one('res.partner', string='العميل / مقدم الطلب', tracking=True)
    product_id = fields.Many2one('product.product', string='الصنف المطلوب', required=True, tracking=True)
    product_code = fields.Char(related='product_id.default_code', string='كود الصنف')
    product_barcode = fields.Char(related='product_id.barcode', string='الباركود')
    quantity = fields.Float(string='الكمية المطلوبة', default=1.0, required=True, tracking=True)

    src_warehouse_id = fields.Many2one('stock.warehouse', string='الفرع / المخزن المصدر (المتوفر لديه)', required=True, tracking=True)
    dest_warehouse_id = fields.Many2one('stock.warehouse', string='فرع الاستلام (سيدي جابر)', required=True, tracking=True)
    transit_location_id = fields.Many2one('stock.location', string='موقع بضاعة بالطريق (Transfer Store)', tracking=True)

    state = fields.Selection([
        ('draft', 'مسودة حجز'),
        ('reserved', 'تم تأكيد الحجز'),
        ('shipped', 'تم الشحن بالطريق (WH-TRANSIT)'),
        ('received', 'تم الاستلام بالفرع (مكتمل)'),
        ('cancelled', 'ملغي'),
    ], string='حالة التحويل', default='draft', tracking=True)

    picking_out_id = fields.Many2one('stock.picking', string='إذن خروج من الفرع المصدر', readonly=True)
    picking_in_id = fields.Many2one('stock.picking', string='إذن استلام بالفرع الوجهة', readonly=True)
    notes = fields.Text(string='ملاحظات التحويل الفوري')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('جديد')) == _('جديد'):
                vals['name'] = self.env['ir.sequence'].next_by_code('alahram.cross.branch.reserve') or _('RES-%05d') % self.env['alahram.cross.branch.reserve'].search_count([])
        return super().create(vals_list)

    def action_confirm_reservation(self):
        """Step 1: Confirm reservation"""
        for rec in self:
            rec.state = 'reserved'
            rec.message_post(body=_("تم تأكيد حجز %s قطعة من الصنف [%s] %s لصالح فرع %s") % (
                rec.quantity, rec.product_code or '', rec.product_id.name, rec.dest_warehouse_id.name
            ))

    def action_ship_to_transit(self):
        """Step 2: Ship from source branch to Transit Store (WH-TRANSIT)"""
        StockPicking = self.env['stock.picking']
        StockMove = self.env['stock.move']
        for rec in self:
            src_loc = rec.src_warehouse_id.lot_stock_id
            transit_loc = rec.transit_location_id or self.env['stock.location'].search([
                ('complete_name', 'ilike', 'Transfer Store')
            ], limit=1) or self.env['stock.location'].search([
                ('usage', '=', 'transit')
            ], limit=1)

            # Look up internal transfer picking type
            picking_type = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', rec.src_warehouse_id.id),
                ('code', '=', 'internal')
            ], limit=1) or self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)

            clean_ctx = {k: v for k, v in self.env.context.items() if not k.startswith('default_')}
            picking_vals = {
                'picking_type_id': picking_type.id,
                'location_id': src_loc.id,
                'location_dest_id': transit_loc.id,
                'origin': rec.name,
                'priority': '0',
            }
            picking = StockPicking.sudo().with_context(clean_ctx).create(picking_vals)
            StockMove.sudo().with_context(clean_ctx).create({
                'product_id': rec.product_id.id,
                'product_uom_qty': rec.quantity,
                'uom_id': rec.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': src_loc.id,
                'location_dest_id': transit_loc.id,
            })
            picking.action_confirm()
            rec.write({
                'picking_out_id': picking.id,
                'state': 'shipped',
            })
            rec.message_post(body=_("تم شحن البضاعة إلى مخزن البضاعة بالطريق (WH-TRANSIT) عبر الإذن: %s") % picking.name)

    def action_receive_at_branch(self):
        """Step 3: Receive from Transit Store to Destination Showroom / Backroom"""
        StockPicking = self.env['stock.picking']
        StockMove = self.env['stock.move']
        for rec in self:
            dest_loc = rec.dest_warehouse_id.lot_stock_id
            transit_loc = rec.transit_location_id or self.env['stock.location'].search([
                ('complete_name', 'ilike', 'Transfer Store')
            ], limit=1) or self.env['stock.location'].search([
                ('usage', '=', 'transit')
            ], limit=1)

            picking_type = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', rec.dest_warehouse_id.id),
                ('code', '=', 'internal')
            ], limit=1) or self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)

            picking_vals = {
                'picking_type_id': picking_type.id,
                'location_id': transit_loc.id,
                'location_dest_id': dest_loc.id,
                'origin': rec.name,
            }
            picking = StockPicking.create(picking_vals)
            StockMove.create({
                'product_id': rec.product_id.id,
                'product_uom_qty': rec.quantity,
                'uom_id': rec.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': transit_loc.id,
                'location_dest_id': dest_loc.id,
            })
            picking.action_confirm()
            rec.write({
                'picking_in_id': picking.id,
                'state': 'received',
            })
            rec.message_post(body=_("تم استلام البضاعة بنجاح في فرع %s عبر الإذن: %s") % (
                rec.dest_warehouse_id.name, picking.name
            ))
