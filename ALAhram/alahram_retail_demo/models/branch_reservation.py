# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class AlahramBranchReservation(models.Model):
    _name = 'alahram.branch.reservation'
    _description = 'Al Ahram Multi-Branch POS Reservation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Reservation Reference / رقم الحجز',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        tracking=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer / العميل',
        tracking=True
    )
    customer_name = fields.Char(string='Customer Name / اسم العميل')
    customer_phone = fields.Char(string='Customer Phone / هاتف العميل')
    pos_order_id = fields.Many2one(
        'pos.order',
        string='POS Order / طلب نقطة البيع',
        ondelete='set null'
    )
    pos_session_id = fields.Many2one(
        'pos.session',
        string='POS Session / جلسة البيع'
    )
    pos_config_id = fields.Many2one(
        'pos.config',
        string='POS Terminal / نقطة البيع'
    )
    bridal_configurator_id = fields.Many2one(
        'alahram.bridal.configurator',
        string='Bridal Package / باكدج العروسة المرتبط',
        ondelete='set null'
    )
    salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson / البائع',
        default=lambda self: self.env.user
    )
    current_branch_id = fields.Many2one(
        'stock.warehouse',
        string='Current Branch / فرع الحجز الحالي',
        required=True,
        default=lambda self: self._default_current_branch()
    )
    state = fields.Selection([
        ('draft', 'Draft / مسودة'),
        ('reserved', 'Fully Reserved / محجوز بالكامل'),
        ('partially_reserved', 'Partially Reserved / حجز جزئي'),
        ('transferred', 'In Transit / قيد التحويل'),
        ('delivered', 'Delivered / تم التسليم'),
        ('cancelled', 'Cancelled / ملغي')
    ], string='Status / الحالة', default='draft', tracking=True)

    date_reservation = fields.Datetime(
        string='Reservation Date / تاريخ الحجز',
        default=fields.Datetime.now,
        required=True
    )
    line_ids = fields.One2many(
        'alahram.branch.reservation.line',
        'reservation_id',
        string='Reservation Lines / أصناف الحجز'
    )
    allocation_ids = fields.One2many(
        'alahram.branch.reservation.allocation',
        'reservation_id',
        string='Allocations / تخصيصات الفروع'
    )
    waitlist_line_ids = fields.One2many(
        'alahram.branch.waitlist.line',
        'reservation_id',
        string='Waiting List / قائمة الانتظار'
    )
    picking_ids = fields.Many2many(
        'stock.picking',
        compute='_compute_pickings',
        string='Stock Pickings / حركات المخزن المرتبطة'
    )
    idempotency_key = fields.Char(
        string='Idempotency Key',
        index=True,
        copy=False
    )
    notes = fields.Text(string='Notes / ملاحظات')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    total_qty_requested = fields.Float(
        string='Requested Qty / إجمالي المطلوب',
        compute='_compute_totals',
        store=True
    )
    total_qty_reserved = fields.Float(
        string='Reserved Qty / إجمالي المحجوز',
        compute='_compute_totals',
        store=True
    )
    total_qty_waiting = fields.Float(
        string='Waiting Qty / إجمالي قيد الانتظار',
        compute='_compute_totals',
        store=True
    )
    total_amount = fields.Float(
        string='Total Amount / إجمالي القيمة',
        compute='_compute_totals',
        store=True
    )

    @api.model
    def _default_current_branch(self):
        wh_sg = self.env['stock.warehouse'].search([('code', '=', 'WH-SG')], limit=1)
        if wh_sg:
            return wh_sg.id
        wh = self.env['stock.warehouse'].search([], limit=1)
        return wh.id if wh else False

    @api.model
    def _get_branch_from_pos_config(self, pos_config):
        """Resolves the physical branch warehouse from a pos.config record."""
        if not pos_config:
            return self._default_current_branch()
        name = pos_config.name or ''
        if 'سيدي جابر' in name or 'sidi' in name.lower():
            wh_sg = self.env['stock.warehouse'].search([('code', '=', 'WH-SG')], limit=1)
            if wh_sg:
                return wh_sg.id
        elif 'رشدي' in name or 'roshdy' in name.lower():
            wh_r = self.env['stock.warehouse'].search([('code', '=', 'WH-ROSHDY')], limit=1)
            if wh_r:
                return wh_r.id
        elif 'سموحة' in name or 'smouha' in name.lower():
            wh_s = self.env['stock.warehouse'].search([('code', '=', 'WH-SMOUHA')], limit=1)
            if wh_s:
                return wh_s.id
        if hasattr(pos_config, 'warehouse_id') and pos_config.warehouse_id and pos_config.warehouse_id.code != 'WH':
            return pos_config.warehouse_id.id
        if pos_config.picking_type_id and pos_config.picking_type_id.warehouse_id and pos_config.picking_type_id.warehouse_id.code != 'WH':
            return pos_config.picking_type_id.warehouse_id.id
        return self._default_current_branch()

    @api.depends('allocation_ids.picking_id')
    def _compute_pickings(self):
        for rec in self:
            rec.picking_ids = rec.allocation_ids.mapped('picking_id')

    @api.depends('line_ids.qty_requested', 'line_ids.qty_reserved', 'line_ids.qty_waiting', 'line_ids.price_subtotal')
    def _compute_totals(self):
        for rec in self:
            rec.total_qty_requested = sum(rec.line_ids.mapped('qty_requested'))
            rec.total_qty_reserved = sum(rec.line_ids.mapped('qty_reserved'))
            rec.total_qty_waiting = sum(rec.line_ids.mapped('qty_waiting'))
            rec.total_amount = sum(rec.line_ids.mapped('price_subtotal'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                seq = self.env['ir.sequence'].next_by_code('alahram.branch.reservation')
                vals['name'] = seq or 'New'
        return super().create(vals_list)

    @api.model
    def get_branch_stock_availability(self, product_ids, pos_config_id=False):
        """Returns stock availability across all active branches for the specified products."""
        if not product_ids:
            return {'success': False, 'error': 'No product IDs provided'}

        products = self.env['product.product'].browse(product_ids)
        if not products.exists():
            return {'success': False, 'error': 'Products not found'}

        pos_cfg = self.env['pos.config'].browse(pos_config_id) if pos_config_id else False
        current_wh_id = self._get_branch_from_pos_config(pos_cfg)

        warehouses = self.env['stock.warehouse'].search([('active', '=', True)])
        
        # Priority order: Current warehouse first, then WH-SG, WH-ROSHDY, WH-SMOUHA, WH-MAIN
        code_prio = {'WH-SG': 1, 'WH-ROSHDY': 2, 'WH-SMOUHA': 3, 'WH-MAIN': 4}
        def wh_sort_key(w):
            if w.id == current_wh_id:
                return -1
            return code_prio.get(w.code, 100)

        sorted_warehouses = sorted(warehouses, key=wh_sort_key)

        branches_meta = []
        for wh in sorted_warehouses:
            branches_meta.append({
                'warehouse_id': wh.id,
                'name': wh.name,
                'code': wh.code,
                'is_current': (wh.id == current_wh_id)
            })

        result_products = {}
        for prod in products:
            branch_data = []
            total_free = 0.0
            for wh in sorted_warehouses:
                p_ctx = prod.with_context(warehouse_id=wh.id)
                free = float(p_ctx.free_qty)
                on_hand = float(p_ctx.qty_available)
                total_free += max(0.0, free)
                branch_data.append({
                    'warehouse_id': wh.id,
                    'warehouse_name': wh.name,
                    'warehouse_code': wh.code,
                    'is_current': (wh.id == current_wh_id),
                    'qty_on_hand': on_hand,
                    'qty_free': free,
                })
            result_products[prod.id] = {
                'product_id': prod.id,
                'display_name': prod.display_name,
                'default_code': prod.default_code or '',
                'barcode': prod.barcode or '',
                'price': prod.lst_price,
                'uom_name': prod.uom_id.name,
                'branches': branch_data,
                'total_network_free': total_free
            }

        return {
            'success': True,
            'current_warehouse_id': current_wh_id,
            'branches': branches_meta,
            'products': result_products
        }

    @api.model
    def create_from_pos(self, reservation_vals):
        """Creates reservation, allocations, waitlist lines, and generates real stock pickings atomically."""
        if not reservation_vals:
            raise UserError(_("بيانات الحجز غير مكتملة."))

        idempotency_key = reservation_vals.get('idempotency_key')
        if idempotency_key:
            existing = self.search([('idempotency_key', '=', idempotency_key)], limit=1)
            if existing:
                return {
                    'success': True,
                    'reservation_id': existing.id,
                    'name': existing.name,
                    'state': existing.state,
                    'total_qty_requested': existing.total_qty_requested,
                    'total_qty_reserved': existing.total_qty_reserved,
                    'total_qty_waiting': existing.total_qty_waiting,
                    'is_duplicate': True
                }

        partner_id = reservation_vals.get('partner_id')
        cust_name = reservation_vals.get('customer_name')
        cust_phone = reservation_vals.get('customer_phone')

        if not partner_id and cust_phone:
            partner = self.env['res.partner'].search([('phone', '=', cust_phone)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': cust_name or f"Customer {cust_phone}",
                    'phone': cust_phone,
                })
            partner_id = partner.id
        elif partner_id and not cust_name:
            partner = self.env['res.partner'].browse(partner_id)
            cust_name = partner.name
            cust_phone = partner.phone

        pos_config_id = reservation_vals.get('pos_config_id')
        pos_cfg = self.env['pos.config'].browse(pos_config_id) if pos_config_id else False
        current_wh_id = self._get_branch_from_pos_config(pos_cfg)

        bridal_configurator_id = reservation_vals.get('bridal_configurator_id')
        header_vals = {
            'partner_id': partner_id or False,
            'customer_name': cust_name,
            'customer_phone': cust_phone,
            'pos_order_id': reservation_vals.get('pos_order_id') or False,
            'pos_session_id': reservation_vals.get('pos_session_id') or False,
            'pos_config_id': pos_config_id or False,
            'bridal_configurator_id': bridal_configurator_id or False,
            'salesperson_id': reservation_vals.get('salesperson_id') or self.env.user.id,
            'current_branch_id': current_wh_id,
            'idempotency_key': idempotency_key,
            'notes': reservation_vals.get('notes') or '',
            'state': 'draft',
        }

        reservation = self.create(header_vals)

        if bridal_configurator_id:
            bridal_pkg = self.env['alahram.bridal.configurator'].browse(bridal_configurator_id)
            if bridal_pkg.exists():
                bridal_pkg.write({
                    'reservation_id': reservation.id,
                    'state': 'reserved',
                })

        items = reservation_vals.get('items', [])
        for item in items:
            product_id = item.get('product_id')
            product = self.env['product.product'].browse(product_id)
            if not product.exists():
                continue
            qty_requested = float(item.get('qty_requested', 1.0))
            price_unit = float(item.get('price_unit', product.lst_price))

            line = self.env['alahram.branch.reservation.line'].create({
                'reservation_id': reservation.id,
                'product_id': product.id,
                'qty_requested': qty_requested,
                'price_unit': price_unit,
            })

            allocations_data = item.get('allocations', [])
            total_allocated_for_line = 0.0

            for alloc in allocations_data:
                qty_alloc = float(alloc.get('qty', 0.0))
                if qty_alloc <= 0:
                    continue
                source_wh_id = int(alloc.get('source_warehouse_id'))
                fulfillment_type = alloc.get('fulfillment_type', 'transfer')
                
                self.env['alahram.branch.reservation.allocation'].create({
                    'reservation_id': reservation.id,
                    'reservation_line_id': line.id,
                    'source_warehouse_id': source_wh_id,
                    'destination_warehouse_id': current_wh_id,
                    'fulfillment_type': fulfillment_type,
                    'qty_allocated': qty_alloc,
                    'state': 'draft',
                })
                total_allocated_for_line += qty_alloc

            # Handle partial reservation deficit -> Waitlist
            if total_allocated_for_line < qty_requested:
                deficit = qty_requested - total_allocated_for_line
                self.env['alahram.branch.waitlist.line'].create({
                    'reservation_id': reservation.id,
                    'reservation_line_id': line.id,
                    'product_id': product.id,
                    'partner_id': partner_id or False,
                    'qty_waiting': deficit,
                    'state': 'waiting',
                    'priority': 'normal',
                    'notification_notes': f"Requested {qty_requested}, reserved {total_allocated_for_line}, backordered deficit {deficit}"
                })

        # Confirm and execute stock operations
        reservation.action_confirm()

        return {
            'success': True,
            'reservation_id': reservation.id,
            'name': reservation.name,
            'state': reservation.state,
            'total_qty_requested': reservation.total_qty_requested,
            'total_qty_reserved': reservation.total_qty_reserved,
            'total_qty_waiting': reservation.total_qty_waiting,
            'total_amount': reservation.total_amount,
            'allocations': [{
                'id': a.id,
                'product_id': a.product_id.id,
                'source_branch': a.source_warehouse_id.name,
                'fulfillment_type': a.fulfillment_type,
                'qty': a.qty_allocated,
                'state': a.state,
                'picking_name': a.picking_id.name if a.picking_id else False,
            } for a in reservation.allocation_ids],
            'waitlist': [{
                'id': w.id,
                'product_id': w.product_id.id,
                'product_name': w.product_id.display_name,
                'qty_waiting': w.qty_waiting,
                'state': w.state,
            } for w in reservation.waitlist_line_ids]
        }

    def action_confirm(self):
        """Confirms reservation, generates real stock pickings, and updates state."""
        self.ensure_one()
        customer_loc = (
            self.partner_id.property_stock_customer.id
            if self.partner_id and self.partner_id.property_stock_customer
            else self.env.ref('stock.stock_location_customers').id
        )

        for allocation in self.allocation_ids.filtered(lambda a: a.state == 'draft'):
            source_wh = allocation.source_warehouse_id
            product = allocation.product_id
            qty = allocation.qty_allocated

            if allocation.fulfillment_type == 'transfer':
                is_local = (source_wh.id == self.current_branch_id.id)
                if is_local:
                    picking_type = source_wh.out_type_id or source_wh.int_type_id
                    dest_location_id = customer_loc
                    origin_str = f"Reservation Local {self.name}"
                else:
                    picking_type = source_wh.int_type_id
                    dest_location_id = self.current_branch_id.lot_stock_id.id
                    origin_str = f"Reservation Transfer {self.name}"

                if not picking_type:
                    raise UserError(_("لم يتم ضبط نوع العملية المخزنية للفرع %s") % source_wh.name)

                picking = self.env['stock.picking'].create({
                    'picking_type_id': picking_type.id,
                    'location_id': source_wh.lot_stock_id.id,
                    'location_dest_id': dest_location_id,
                    'origin': origin_str,
                    'partner_id': self.partner_id.id if self.partner_id else False,
                })

                move = self.env['stock.move'].create({
                    'description_picking': f"{'Local' if is_local else 'Transfer'} for {self.name} - {product.name}",
                    'product_id': product.id,
                    'product_uom_qty': qty,
                    'uom_id': product.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': source_wh.lot_stock_id.id,
                    'location_dest_id': dest_location_id,
                })

                picking.action_confirm()
                picking.action_assign()
                allocation.picking_id = picking.id
                allocation.state = 'reserved' if picking.state in ('assigned', 'confirmed') else 'draft'


            elif allocation.fulfillment_type == 'pickup':
                # Direct pickup at source branch: reserve at source warehouse for customer
                picking_type = source_wh.out_type_id
                if not picking_type:
                    raise UserError(_("لم يتم ضبط نوع تسليم البضاعة للفرع %s") % source_wh.name)

                picking = self.env['stock.picking'].create({
                    'picking_type_id': picking_type.id,
                    'location_id': source_wh.lot_stock_id.id,
                    'location_dest_id': customer_loc,
                    'origin': f"Direct Pickup {self.name}",
                    'partner_id': self.partner_id.id if self.partner_id else False,
                })

                move = self.env['stock.move'].create({
                    'description_picking': f"Direct Pickup {self.name} - {product.name}",
                    'product_id': product.id,
                    'product_uom_qty': qty,
                    'uom_id': product.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': source_wh.lot_stock_id.id,
                    'location_dest_id': customer_loc,
                })

                picking.action_confirm()
                picking.action_assign()
                allocation.picking_id = picking.id
                allocation.state = 'reserved' if picking.state in ('assigned', 'confirmed') else 'draft'

            elif allocation.fulfillment_type == 'direct_delivery':
                # Direct delivery from source branch to customer address
                picking_type = source_wh.out_type_id
                if not picking_type:
                    raise UserError(_("لم يتم ضبط نوع تسليم البضاعة للفرع %s") % source_wh.name)

                picking = self.env['stock.picking'].create({
                    'picking_type_id': picking_type.id,
                    'location_id': source_wh.lot_stock_id.id,
                    'location_dest_id': customer_loc,
                    'origin': f"Direct Delivery {self.name}",
                    'partner_id': self.partner_id.id if self.partner_id else False,
                })

                move = self.env['stock.move'].create({
                    'description_picking': f"Direct Delivery for {self.name} - {product.name}",
                    'product_id': product.id,
                    'product_uom_qty': qty,
                    'uom_id': product.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': source_wh.lot_stock_id.id,
                    'location_dest_id': customer_loc,
                })

                picking.action_confirm()
                picking.action_assign()
                allocation.picking_id = picking.id
                allocation.state = 'reserved' if picking.state in ('assigned', 'confirmed') else 'draft'

        # Compute header state
        if self.total_qty_waiting > 0 and self.total_qty_reserved > 0:
            self.state = 'partially_reserved'
        elif self.total_qty_waiting > 0 and self.total_qty_reserved == 0:
            self.state = 'draft'
        elif self.total_qty_reserved > 0:
            self.state = 'reserved'
        else:
            self.state = 'draft'

        self.message_post(body=_(
            "تم تأكيد حجز الفروع %s: إجمالي المطلوب %.2f، المحجوز %.2f، قيد الانتظار %.2f."
        ) % (self.name, self.total_qty_requested, self.total_qty_reserved, self.total_qty_waiting))
        return True

    def action_cancel(self):
        """Cancels open pickings, allocations, waitlist lines and reservation."""
        for rec in self:
            for alloc in rec.allocation_ids:
                if alloc.picking_id and alloc.picking_id.state not in ('done', 'cancel'):
                    alloc.picking_id.action_cancel()
                alloc.state = 'cancelled'

            rec.waitlist_line_ids.write({'state': 'cancelled'})
            rec.state = 'cancelled'
            rec.message_post(body=_("تم إلغاء الحجز وإلغاء حجز المخزون في جميع الفروع."))
        return True

    def action_retry_waiting_allocation(self):
        """Checks for newly available stock and reallocates items in the waiting list."""
        for rec in self:
            open_waitlist = rec.waitlist_line_ids.filtered(lambda w: w.state == 'waiting' and w.qty_waiting > 0)
            if not open_waitlist:
                continue

            warehouses = self.env['stock.warehouse'].search([('active', '=', True)])
            for wait_line in open_waitlist:
                prod = wait_line.product_id
                remaining_deficit = wait_line.qty_waiting

                # Ensure line_id exists
                line = wait_line.reservation_line_id
                if not line:
                    line = rec.line_ids.filtered(lambda l: l.product_id == prod)[:1]
                    if not line:
                        line = self.env['alahram.branch.reservation.line'].create({
                            'reservation_id': rec.id,
                            'product_id': prod.id,
                            'qty_requested': wait_line.qty_waiting,
                            'price_unit': prod.lst_price,
                        })
                    wait_line.reservation_line_id = line.id

                # Check warehouses (prefer preferred_warehouses if set, else all warehouses)
                candidate_whs = wait_line.preferred_warehouse_ids or warehouses
                for wh in candidate_whs:
                    if remaining_deficit <= 0:
                        break
                    free = prod.with_context(warehouse_id=wh.id).free_qty
                    if free > 0:
                        qty_to_alloc = min(free, remaining_deficit)
                        # Create allocation
                        self.env['alahram.branch.reservation.allocation'].create({
                            'reservation_id': rec.id,
                            'reservation_line_id': line.id,
                            'source_warehouse_id': wh.id,
                            'destination_warehouse_id': rec.current_branch_id.id,
                            'fulfillment_type': 'transfer',
                            'qty_allocated': qty_to_alloc,
                            'state': 'draft',
                        })
                        remaining_deficit -= qty_to_alloc

                if remaining_deficit < wait_line.qty_waiting:
                    allocated_now = wait_line.qty_waiting - remaining_deficit
                    wait_line.qty_waiting = remaining_deficit
                    if remaining_deficit == 0:
                        wait_line.state = 'allocated'
                    rec.message_post(body=_(
                        "تم تخصيص رصيد وارد جديد للصنف %s بكمية %.2f من قائمة الانتظار."
                    ) % (prod.display_name, allocated_now))

            rec.action_confirm()
        return True

    def action_complete_handover(self):
        """Marks reservation and pickings as delivered to customer."""
        for rec in self:
            for alloc in rec.allocation_ids:
                if alloc.picking_id and alloc.picking_id.state == 'assigned':
                    for move in alloc.picking_id.move_ids:
                        move.quantity = move.product_uom_qty
                    alloc.picking_id.button_validate()
                alloc.state = 'handed_over'

            rec.state = 'delivered'
            rec.message_post(body=_("تم تسليم كامل أصناف الحجز للعميل بنجاح."))
        return True


class AlahramBranchReservationLine(models.Model):
    _name = 'alahram.branch.reservation.line'
    _description = 'Al Ahram Branch Reservation Line'

    reservation_id = fields.Many2one(
        'alahram.branch.reservation',
        string='Reservation',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product / الصنف',
        required=True
    )
    qty_requested = fields.Float(
        string='Requested Qty / المطلوب',
        required=True,
        default=1.0
    )
    qty_reserved = fields.Float(
        string='Reserved Qty / المحجوز',
        compute='_compute_quantities',
        store=True
    )
    qty_waiting = fields.Float(
        string='Waiting Qty / قيد الانتظار',
        compute='_compute_quantities',
        store=True
    )
    price_unit = fields.Float(string='Unit Price / سعر الوحدة')
    price_subtotal = fields.Float(
        string='Subtotal / الإجمالي',
        compute='_compute_subtotal',
        store=True
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        related='product_id.uom_id',
        readonly=True
    )
    allocation_ids = fields.One2many(
        'alahram.branch.reservation.allocation',
        'reservation_line_id',
        string='Allocations'
    )
    waitlist_line_ids = fields.One2many(
        'alahram.branch.waitlist.line',
        'reservation_line_id',
        string='Waitlist Lines'
    )

    @api.depends('allocation_ids.qty_allocated', 'allocation_ids.state', 'waitlist_line_ids.qty_waiting', 'waitlist_line_ids.state')
    def _compute_quantities(self):
        for line in self:
            active_allocs = line.allocation_ids.filtered(lambda a: a.state != 'cancelled')
            line.qty_reserved = sum(active_allocs.mapped('qty_allocated'))
            active_wait = line.waitlist_line_ids.filtered(lambda w: w.state == 'waiting')
            line.qty_waiting = sum(active_wait.mapped('qty_waiting'))

    @api.depends('qty_requested', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = line.qty_requested * line.price_unit


class AlahramBranchReservationAllocation(models.Model):
    _name = 'alahram.branch.reservation.allocation'
    _description = 'Al Ahram Branch Reservation Allocation'

    reservation_id = fields.Many2one(
        'alahram.branch.reservation',
        string='Reservation',
        required=True,
        ondelete='cascade'
    )
    reservation_line_id = fields.Many2one(
        'alahram.branch.reservation.line',
        string='Reservation Line',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product / الصنف',
        related='reservation_line_id.product_id',
        store=True
    )
    source_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Source Branch / فرع الصرف',
        required=True
    )
    destination_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Dest Branch / فرع الاستلام'
    )
    fulfillment_type = fields.Selection([
        ('pickup', 'Customer Direct Pickup / استلام مباشر من الفرع'),
        ('transfer', 'Internal Transfer to POS Branch / شحن للفرع الحالي'),
        ('direct_delivery', 'Direct Delivery to Customer / شحن مباشر للعميل')
    ], string='Fulfillment Method / طريقة الاستلام', required=True, default='transfer')
    qty_allocated = fields.Float(
        string='Allocated Qty / الكمية المخصصة',
        required=True,
        default=1.0
    )
    state = fields.Selection([
        ('draft', 'Draft / مسودة'),
        ('reserved', 'Stock Reserved / محجوز بالمخزن'),
        ('transit', 'In Transit / بالطريق'),
        ('received', 'Received / تم الاستلام بالفرع'),
        ('handed_over', 'Handed to Customer / تم التسليم للعميل'),
        ('cancelled', 'Cancelled / ملغي')
    ], string='Status / الحالة', default='draft')
    picking_id = fields.Many2one(
        'stock.picking',
        string='Stock Picking / إذن المخزن',
        ondelete='set null'
    )


class AlahramBranchWaitlistLine(models.Model):
    _name = 'alahram.branch.waitlist.line'
    _description = 'Al Ahram Branch Reservation Waiting List'
    _inherit = ['mail.thread']
    _order = 'id desc'

    reservation_id = fields.Many2one(
        'alahram.branch.reservation',
        string='Reservation',
        required=True,
        ondelete='cascade'
    )
    reservation_line_id = fields.Many2one(
        'alahram.branch.reservation.line',
        string='Reservation Line',
        required=False,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product / الصنف',
        required=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer / العميل'
    )
    qty_waiting = fields.Float(
        string='Deficit Qty / الكمية بالعجز',
        required=True,
        default=1.0
    )
    preferred_warehouse_ids = fields.Many2many(
        'stock.warehouse',
        string='Preferred Branches / الفروع المفضلة للتحويل'
    )
    priority = fields.Selection([
        ('normal', 'Normal / عادي'),
        ('high', 'High / هام'),
        ('urgent', 'Urgent / عاجل')
    ], string='Priority / الأولوية', default='normal')
    state = fields.Selection([
        ('waiting', 'Waiting for Stock / بانتظار توفر رصيد'),
        ('allocated', 'Stock Allocated / تم التخصيص'),
        ('cancelled', 'Cancelled / ملغي')
    ], string='Status / الحالة', default='waiting', tracking=True)
    date_added = fields.Datetime(
        string='Date Added / تاريخ الإضافة',
        default=fields.Datetime.now
    )
    notification_notes = fields.Text(string='Notification Notes / ملاحظات الإشعار')
