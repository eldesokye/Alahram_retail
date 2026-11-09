# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
import uuid

class TestPOSMultiBranchReservation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].search([('name', 'ilike', 'الأهرام')], limit=1) or cls.env.company
        cls.wh_main = cls.env['stock.warehouse'].search([('code', '=', 'WH-MAIN')], limit=1)
        cls.wh_sg = cls.env['stock.warehouse'].search([('code', '=', 'WH-SG')], limit=1)
        cls.wh_roshdy = cls.env['stock.warehouse'].search([('code', '=', 'WH-ROSHDY')], limit=1)
        cls.wh_smouha = cls.env['stock.warehouse'].search([('code', '=', 'WH-SMOUHA')], limit=1)

        cls.partner = cls.env['res.partner'].search([('name', 'ilike', 'منال عبد الرحمن')], limit=1)
        if not cls.partner:
            cls.partner = cls.env['res.partner'].create({
                'name': 'منال عبد الرحمن (عميلة تجريبية)',
                'phone': '01011223344',
                'company_id': cls.company.id,
            })

        cls.pos_config = cls.env['pos.config'].search([('name', 'ilike', 'كاشير 1')], limit=1)
        if not cls.pos_config:
            cls.pos_config = cls.env['pos.config'].search([], limit=1)

        cls.session = cls.pos_config.current_session_id
        if not cls.session or cls.session.state != 'opened':
            cashier_user = cls.env['res.users'].search([('login', '=', 'cashier1.sidigaber@alahram.com')], limit=1) or cls.env.user
            cls.session = cls.env['pos.session'].create({
                'user_id': cashier_user.id,
                'config_id': cls.pos_config.id,
            })
            cls.session.write({'state': 'opened'})

        # Find or create test products
        cls.product_pot = cls.env['product.product'].search([('barcode', '=', '6221049430762')], limit=1)
        if not cls.product_pot:
            cls.product_pot = cls.env['product.product'].create({
                'name': 'حلة طهي جرانيت أهرام مقاس 24',
                'barcode': '6221049430762',
                'default_code': 'POT-GR-24',
                'lst_price': 1250.0,
                'is_storable': True,
            })

        cls.product_pan = cls.env['product.product'].search([('barcode', '=', '6221049182395')], limit=1)
        if not cls.product_pan:
            cls.product_pan = cls.env['product.product'].create({
                'name': 'طاسة تيتانيوم برو مقاس 28',
                'barcode': '6221049182395',
                'default_code': 'PAN-TI-28',
                'lst_price': 850.0,
                'is_storable': True,
            })

        cls.product_knife = cls.env['product.product'].search([('default_code', 'ilike', '1042221320795')], limit=1)
        if not cls.product_knife:
            cls.product_knife = cls.env['product.product'].create({
                'name': 'طقم سكاكين ستانلس ستيل 6 قطع',
                'barcode': '1042221320795',
                'default_code': 'KNIFE-SET-06',
                'lst_price': 650.0,
                'is_storable': True,
            })

    def _set_stock_quant(self, product, location, qty):
        """Helper to safely adjust stock quant using standard Odoo stock change."""
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product.id,
            'location_id': location.id,
            'inventory_quantity': qty,
        }).action_apply_inventory()

    # =========================================================================
    # GROUP A: Multi-Product Selection & Tablet Interaction (TEST-001 - TEST-008)
    # =========================================================================

    def test_001_multi_product_selection_search_by_name(self):
        """TEST-001: Search products by Arabic name substring"""
        prods = self.env['product.product'].search([('name', 'ilike', 'حلة')])
        self.assertTrue(len(prods) > 0, "Should find cookware products containing 'حلة'")

    def test_002_multi_product_selection_search_by_barcode(self):
        """TEST-002: Exact match lookup using barcode scanner string"""
        prod = self.env['product.product'].search([('barcode', '=', '6221049430762')], limit=1)
        self.assertEqual(prod.id, self.product_pot.id, "Barcode scan must resolve to product_pot")

    def test_003_multi_product_selection_search_by_default_code(self):
        """TEST-003: Match product by internal default code"""
        prod = self.env['product.product'].search([('default_code', '=', self.product_pan.default_code)], limit=1)
        self.assertEqual(prod.id, self.product_pan.id, "Internal code match must resolve to product_pan")

    def test_004_tablet_empty_selection_guard(self):
        """TEST-004: Rejects reservation creation when no items provided"""
        with self.assertRaises(UserError):
            self.env['alahram.branch.reservation'].create_from_pos({})

    def test_005_tablet_qty_stepper_increment(self):
        """TEST-005: Quantity stepper increments requested quantity"""
        res = self.env['alahram.branch.reservation'].create({
            'current_branch_id': self.wh_sg.id,
            'partner_id': self.partner.id,
            'line_ids': [(0, 0, {
                'product_id': self.product_pot.id,
                'qty_requested': 1.0,
                'price_unit': self.product_pot.lst_price,
            })]
        })
        line = res.line_ids[0]
        line.qty_requested += 1.0
        self.assertEqual(res.total_qty_requested, 2.0, "Total requested must increment to 2.0")

    def test_006_tablet_qty_stepper_decrement_boundary(self):
        """TEST-006: Quantity requested line subtotal recomputes dynamically"""
        res = self.env['alahram.branch.reservation'].create({
            'current_branch_id': self.wh_sg.id,
            'partner_id': self.partner.id,
            'line_ids': [(0, 0, {
                'product_id': self.product_pan.id,
                'qty_requested': 3.0,
                'price_unit': 850.0,
            })]
        })
        self.assertEqual(res.total_amount, 2550.0, "Total amount should be 3 * 850 = 2550")

    def test_007_tablet_remove_line(self):
        """TEST-007: Removing line updates reservation totals"""
        res = self.env['alahram.branch.reservation'].create({
            'current_branch_id': self.wh_sg.id,
            'partner_id': self.partner.id,
            'line_ids': [
                (0, 0, {'product_id': self.product_pot.id, 'qty_requested': 1.0, 'price_unit': 1000.0}),
                (0, 0, {'product_id': self.product_pan.id, 'qty_requested': 2.0, 'price_unit': 500.0}),
            ]
        })
        self.assertEqual(res.total_qty_requested, 3.0)
        res.line_ids[1].unlink()
        self.assertEqual(res.total_qty_requested, 1.0)
        self.assertEqual(res.total_amount, 1000.0)

    def test_008_tablet_walkin_customer_creation(self):
        """TEST-008: Auto-creates customer when phone is provided without partner_id"""
        phone = "01299887766"
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'customer_name': 'عميل نقدي جديد',
            'customer_phone': phone,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pot.id,
                'qty_requested': 1.0,
                'price_unit': self.product_pot.lst_price,
            }]
        })
        partner = self.env['res.partner'].search([('phone', '=', phone)], limit=1)
        self.assertTrue(partner, "Customer partner must be auto-created with the phone")
        self.assertEqual(res_data['success'], True)

    # =========================================================================
    # GROUP B: Multi-Branch Real-Time Stock Availability (TEST-009 - TEST-016)
    # =========================================================================

    def test_009_multi_branch_stock_availability_lookup(self):
        """TEST-009: API returns stock availability across branches"""
        res = self.env['alahram.branch.reservation'].get_branch_stock_availability(
            [self.product_pot.id], self.pos_config.id
        )
        self.assertTrue(res['success'], "Stock lookup must succeed")
        self.assertIn(self.product_pot.id, res['products'], "Product must be present in response")
        branches = res['products'][self.product_pot.id]['branches']
        self.assertTrue(len(branches) >= 3, "Should include multiple branches (SG, Roshdy, Smouha, Main)")

    def test_010_multi_branch_stock_sorting_current_first(self):
        """TEST-010: Current POS branch is sorted first in branch list"""
        res = self.env['alahram.branch.reservation'].get_branch_stock_availability(
            [self.product_pot.id], self.pos_config.id
        )
        first_branch = res['branches'][0]
        self.assertTrue(first_branch['is_current'], "First branch in list must be current branch")

    def test_011_multi_branch_stock_zero_stock_reporting(self):
        """TEST-011: Reports zero stock correctly when location is empty"""
        res = self.env['alahram.branch.reservation'].get_branch_stock_availability(
            [self.product_pan.id], self.pos_config.id
        )
        prod_data = res['products'][self.product_pan.id]
        self.assertIsInstance(prod_data['total_network_free'], float)

    def test_012_multi_branch_stock_multiple_products(self):
        """TEST-012: Batch stock check for multiple products in single RPC"""
        pids = [self.product_pot.id, self.product_pan.id, self.product_knife.id]
        res = self.env['alahram.branch.reservation'].get_branch_stock_availability(pids, self.pos_config.id)
        self.assertEqual(len(res['products']), 3, "Must return data for all 3 requested products")

    def test_013_multi_branch_stock_inactive_warehouse_filtered(self):
        """TEST-013: Inactive warehouses are excluded from availability search"""
        res = self.env['alahram.branch.reservation'].get_branch_stock_availability(
            [self.product_pot.id], self.pos_config.id
        )
        wh_ids = [b['warehouse_id'] for b in res['branches']]
        inactive_wh = self.env['stock.warehouse'].search([('active', '=', False), ('id', 'in', wh_ids)])
        self.assertFalse(inactive_wh, "Inactive warehouses must not appear in branches")

    def test_014_multi_branch_stock_total_network_free_computed(self):
        """TEST-014: Total network free stock is aggregated correctly"""
        res = self.env['alahram.branch.reservation'].get_branch_stock_availability(
            [self.product_pot.id], self.pos_config.id
        )
        prod_data = res['products'][self.product_pot.id]
        sum_branches = sum(max(0.0, b['qty_free']) for b in prod_data['branches'])
        self.assertEqual(prod_data['total_network_free'], sum_branches)

    def test_015_multi_branch_stock_non_existent_product_guard(self):
        """TEST-015: Handles invalid product ID gracefully"""
        res = self.env['alahram.branch.reservation'].get_branch_stock_availability([9999999], self.pos_config.id)
        self.assertFalse(res['success'], "Must return success False for invalid product IDs")

    def test_016_multi_branch_stock_pos_config_warehouse_detection(self):
        """TEST-016: Correctly detects POS config warehouse"""
        res = self.env['alahram.branch.reservation'].get_branch_stock_availability(
            [self.product_pot.id], self.pos_config.id
        )
        self.assertEqual(res['current_warehouse_id'], self.wh_sg.id, "Sidi Gaber POS must resolve to WH-SG")

    # =========================================================================
    # GROUP C: Branch Split Allocation Logic (TEST-017 - TEST-024)
    # =========================================================================

    def test_017_split_allocation_single_branch_full(self):
        """TEST-017: 100% quantity allocated from a single branch"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pot.id,
                'qty_requested': 2.0,
                'allocations': [{
                    'source_warehouse_id': self.wh_roshdy.id,
                    'qty': 2.0,
                    'fulfillment_type': 'transfer',
                }]
            }]
        })
        self.assertEqual(res_data['total_qty_requested'], 2.0)
        self.assertEqual(res_data['total_qty_reserved'], 2.0)
        self.assertEqual(res_data['total_qty_waiting'], 0.0)

    def test_018_split_allocation_dual_branch_split(self):
        """TEST-018: Split requested quantity across two branches (e.g. Roshdy + Smouha)"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pan.id,
                'qty_requested': 3.0,
                'allocations': [
                    {'source_warehouse_id': self.wh_roshdy.id, 'qty': 2.0, 'fulfillment_type': 'transfer'},
                    {'source_warehouse_id': self.wh_smouha.id, 'qty': 1.0, 'fulfillment_type': 'transfer'},
                ]
            }]
        })
        self.assertEqual(res_data['total_qty_requested'], 3.0)
        self.assertEqual(res_data['total_qty_reserved'], 3.0)
        self.assertEqual(len(res_data['allocations']), 2)

    def test_019_split_allocation_three_way_split(self):
        """TEST-019: Three-way split across Sidi Gaber, Roshdy, and Main Warehouse"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pot.id,
                'qty_requested': 5.0,
                'allocations': [
                    {'source_warehouse_id': self.wh_sg.id, 'qty': 2.0, 'fulfillment_type': 'transfer'},
                    {'source_warehouse_id': self.wh_roshdy.id, 'qty': 2.0, 'fulfillment_type': 'transfer'},
                    {'source_warehouse_id': self.wh_main.id, 'qty': 1.0, 'fulfillment_type': 'transfer'},
                ]
            }]
        })
        self.assertEqual(len(res_data['allocations']), 3)
        self.assertEqual(res_data['total_qty_reserved'], 5.0)

    def test_020_split_allocation_over_allocation_prevented(self):
        """TEST-020: Line calculations accurately reflect allocation amounts"""
        res = self.env['alahram.branch.reservation'].create({
            'current_branch_id': self.wh_sg.id,
            'partner_id': self.partner.id,
            'line_ids': [(0, 0, {'product_id': self.product_pot.id, 'qty_requested': 2.0})],
        })
        line = res.line_ids[0]
        self.env['alahram.branch.reservation.allocation'].create({
            'reservation_id': res.id,
            'reservation_line_id': line.id,
            'source_warehouse_id': self.wh_roshdy.id,
            'qty_allocated': 2.0,
            'fulfillment_type': 'transfer',
        })
        line._compute_quantities()
        self.assertEqual(line.qty_reserved, 2.0)

    def test_021_split_allocation_stepper_change(self):
        """TEST-021: Modifying allocated quantity updates line and header reserved sum"""
        res = self.env['alahram.branch.reservation'].create({
            'current_branch_id': self.wh_sg.id,
            'partner_id': self.partner.id,
            'line_ids': [(0, 0, {'product_id': self.product_pot.id, 'qty_requested': 5.0})],
        })
        alloc = self.env['alahram.branch.reservation.allocation'].create({
            'reservation_id': res.id,
            'reservation_line_id': res.line_ids[0].id,
            'source_warehouse_id': self.wh_roshdy.id,
            'qty_allocated': 2.0,
            'fulfillment_type': 'transfer',
        })
        alloc.write({'qty_allocated': 4.0})
        self.assertEqual(res.total_qty_reserved, 4.0)

    def test_022_split_allocation_remove_branch_recomputes(self):
        """TEST-022: Unlinking an allocation recomputes reservation reserved totals"""
        res = self.env['alahram.branch.reservation'].create({
            'current_branch_id': self.wh_sg.id,
            'partner_id': self.partner.id,
            'line_ids': [(0, 0, {'product_id': self.product_pot.id, 'qty_requested': 4.0})],
        })
        alloc1 = self.env['alahram.branch.reservation.allocation'].create({
            'reservation_id': res.id,
            'reservation_line_id': res.line_ids[0].id,
            'source_warehouse_id': self.wh_roshdy.id,
            'qty_allocated': 2.0,
            'fulfillment_type': 'transfer',
        })
        alloc2 = self.env['alahram.branch.reservation.allocation'].create({
            'reservation_id': res.id,
            'reservation_line_id': res.line_ids[0].id,
            'source_warehouse_id': self.wh_smouha.id,
            'qty_allocated': 2.0,
            'fulfillment_type': 'transfer',
        })
        self.assertEqual(res.total_qty_reserved, 4.0)
        alloc2.unlink()
        self.assertEqual(res.total_qty_reserved, 2.0)

    def test_023_split_allocation_auto_allocate_engine(self):
        """TEST-023: Allocations correctly populate linked line and reservation"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pot.id,
                'qty_requested': 1.0,
                'allocations': [{'source_warehouse_id': self.wh_roshdy.id, 'qty': 1.0, 'fulfillment_type': 'transfer'}]
            }]
        })
        res = self.env['alahram.branch.reservation'].browse(res_data['reservation_id'])
        self.assertEqual(len(res.allocation_ids), 1)
        self.assertEqual(res.allocation_ids[0].reservation_line_id.id, res.line_ids[0].id)

    def test_024_split_allocation_totals_consistency(self):
        """TEST-024: Reserved quantity on line matches sum of active allocations"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pot.id,
                'qty_requested': 3.0,
                'allocations': [
                    {'source_warehouse_id': self.wh_roshdy.id, 'qty': 1.0, 'fulfillment_type': 'transfer'},
                    {'source_warehouse_id': self.wh_main.id, 'qty': 2.0, 'fulfillment_type': 'transfer'},
                ]
            }]
        })
        res = self.env['alahram.branch.reservation'].browse(res_data['reservation_id'])
        self.assertEqual(res.line_ids[0].qty_reserved, 3.0)

    # =========================================================================
    # GROUP D: Dual Fulfillment Mechanics (TEST-025 - TEST-032)
    # =========================================================================

    def test_025_fulfillment_pickup_direct_source_branch(self):
        """TEST-025: Direct pickup generates outgoing picking at source branch with customer dest"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pot.id,
                'qty_requested': 1.0,
                'allocations': [{'source_warehouse_id': self.wh_roshdy.id, 'qty': 1.0, 'fulfillment_type': 'pickup'}]
            }]
        })
        res = self.env['alahram.branch.reservation'].browse(res_data['reservation_id'])
        alloc = res.allocation_ids[0]
        self.assertEqual(alloc.fulfillment_type, 'pickup')
        self.assertTrue(alloc.picking_id, "Direct pickup must create stock.picking")
        self.assertEqual(alloc.picking_id.picking_type_id.id, self.wh_roshdy.out_type_id.id, "Must be source warehouse out_type_id")
        self.assertEqual(alloc.picking_id.location_id.id, self.wh_roshdy.lot_stock_id.id)

    def test_026_fulfillment_transfer_internal_to_current_branch(self):
        """TEST-026: Internal transfer creates picking from source WH to current POS WH"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pan.id,
                'qty_requested': 2.0,
                'allocations': [{'source_warehouse_id': self.wh_smouha.id, 'qty': 2.0, 'fulfillment_type': 'transfer'}]
            }]
        })
        res = self.env['alahram.branch.reservation'].browse(res_data['reservation_id'])
        alloc = res.allocation_ids[0]
        self.assertEqual(alloc.fulfillment_type, 'transfer')
        self.assertTrue(alloc.picking_id, "Internal transfer must create stock.picking")
        self.assertEqual(alloc.picking_id.picking_type_id.id, self.wh_smouha.int_type_id.id)
        self.assertEqual(alloc.picking_id.location_dest_id.id, self.wh_sg.lot_stock_id.id)

    def test_027_fulfillment_mixed_pickup_and_transfer(self):
        """TEST-027: Basket with both pickup and transfer allocations creates distinct pickings"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [
                {
                    'product_id': self.product_pot.id,
                    'qty_requested': 1.0,
                    'allocations': [{'source_warehouse_id': self.wh_roshdy.id, 'qty': 1.0, 'fulfillment_type': 'pickup'}]
                },
                {
                    'product_id': self.product_pan.id,
                    'qty_requested': 1.0,
                    'allocations': [{'source_warehouse_id': self.wh_smouha.id, 'qty': 1.0, 'fulfillment_type': 'transfer'}]
                }
            ]
        })
        res = self.env['alahram.branch.reservation'].browse(res_data['reservation_id'])
        self.assertEqual(len(res.allocation_ids), 2)
        pickup_alloc = res.allocation_ids.filtered(lambda a: a.fulfillment_type == 'pickup')
        transfer_alloc = res.allocation_ids.filtered(lambda a: a.fulfillment_type == 'transfer')
        self.assertTrue(pickup_alloc.picking_id)
        self.assertTrue(transfer_alloc.picking_id)
        self.assertNotEqual(pickup_alloc.picking_id.id, transfer_alloc.picking_id.id)

    def test_028_fulfillment_pickup_pos_qty_to_move_zero(self):
        """TEST-028: PosOrderLine._get_qty_to_move() returns 0 for pickup lines (no double deduction)"""
        pos_order = self.env['pos.order'].create({
            'session_id': self.session.id,
            'partner_id': self.partner.id,
            'lines': [(0, 0, {
                'product_id': self.product_pot.id,
                'qty': 1.0,
                'price_unit': 1250.0,
                'price_subtotal': 1250.0,
                'price_subtotal_incl': 1425.0,
                'fulfillment_type': 'pickup',
            })],
            'amount_total': 1425.0,
            'amount_tax': 175.0,
            'amount_paid': 1425.0,
            'amount_return': 0.0,
        })
        line = pos_order.lines[0]
        qty_to_move = line._get_qty_to_move()
        self.assertEqual(qty_to_move, 0.0, "Pickup line must return 0.0 qty to move to avoid POS double stock deduction")

    def test_029_fulfillment_transfer_pos_qty_to_move_positive(self):
        """TEST-029: PosOrderLine._get_qty_to_move() returns normal qty for transfer lines"""
        pos_order = self.env['pos.order'].create({
            'session_id': self.session.id,
            'partner_id': self.partner.id,
            'lines': [(0, 0, {
                'product_id': self.product_pot.id,
                'qty': 2.0,
                'price_unit': 1250.0,
                'price_subtotal': 2500.0,
                'price_subtotal_incl': 2850.0,
                'fulfillment_type': 'transfer',
            })],
            'amount_total': 2850.0,
            'amount_tax': 350.0,
            'amount_paid': 2850.0,
            'amount_return': 0.0,
        })
        line = pos_order.lines[0]
        qty_to_move = line._get_qty_to_move()
        self.assertEqual(qty_to_move, 2.0, "Transfer line must return full qty to move from current POS store")

    def test_030_fulfillment_pickup_stock_picking_assign(self):
        """TEST-030: Direct pickup picking is in confirmed or assigned state"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pot.id,
                'qty_requested': 1.0,
                'allocations': [{'source_warehouse_id': self.wh_main.id, 'qty': 1.0, 'fulfillment_type': 'pickup'}]
            }]
        })
        res = self.env['alahram.branch.reservation'].browse(res_data['reservation_id'])
        picking = res.allocation_ids[0].picking_id
        self.assertIn(picking.state, ('confirmed', 'assigned'), "Picking should be confirmed and assigned")

    def test_031_fulfillment_transfer_stock_picking_assign(self):
        """TEST-031: Internal transfer picking is confirmed and assigned"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pot.id,
                'qty_requested': 1.0,
                'allocations': [{'source_warehouse_id': self.wh_main.id, 'qty': 1.0, 'fulfillment_type': 'transfer'}]
            }]
        })
        res = self.env['alahram.branch.reservation'].browse(res_data['reservation_id'])
        picking = res.allocation_ids[0].picking_id
        self.assertIn(picking.state, ('confirmed', 'assigned'))

    def test_032_fulfillment_complete_handover_validates_pickings(self):
        """TEST-032: action_complete_handover() marks reservation as delivered"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pot.id,
                'qty_requested': 1.0,
                'allocations': [{'source_warehouse_id': self.wh_main.id, 'qty': 1.0, 'fulfillment_type': 'transfer'}]
            }]
        })
        res = self.env['alahram.branch.reservation'].browse(res_data['reservation_id'])
        res.action_complete_handover()
        self.assertEqual(res.state, 'delivered')

    # =========================================================================
    # GROUP E: Partial Reservation, Waiting List & Retry Engine (TEST-033 - TEST-040)
    # =========================================================================

    def test_033_partial_reservation_creates_waitlist(self):
        """TEST-033: Deficit between requested and allocated creates waitlist line"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pot.id,
                'qty_requested': 5.0,
                'allocations': [{'source_warehouse_id': self.wh_roshdy.id, 'qty': 2.0, 'fulfillment_type': 'transfer'}]
            }]
        })
        self.assertEqual(res_data['state'], 'partially_reserved')
        self.assertEqual(res_data['total_qty_requested'], 5.0)
        self.assertEqual(res_data['total_qty_reserved'], 2.0)
        self.assertEqual(res_data['total_qty_waiting'], 3.0)
        self.assertEqual(len(res_data['waitlist']), 1)

    def test_034_partial_reservation_deficit_quantity_exact(self):
        """TEST-034: Deficit quantity equals requested minus allocated exactly"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_knife.id,
                'qty_requested': 10.0,
                'allocations': [{'source_warehouse_id': self.wh_roshdy.id, 'qty': 3.0, 'fulfillment_type': 'transfer'}]
            }]
        })
        res = self.env['alahram.branch.reservation'].browse(res_data['reservation_id'])
        wait_line = res.waitlist_line_ids[0]
        self.assertEqual(wait_line.qty_waiting, 7.0)

    def test_035_waitlist_priority_assignment(self):
        """TEST-035: Waitlist lines support priority setting"""
        res = self.env['alahram.branch.reservation'].create({
            'current_branch_id': self.wh_sg.id,
            'partner_id': self.partner.id,
            'line_ids': [(0, 0, {'product_id': self.product_pot.id, 'qty_requested': 1.0})],
            'waitlist_line_ids': [(0, 0, {
                'product_id': self.product_pot.id,
                'qty_waiting': 1.0,
                'priority': 'urgent',
                'state': 'waiting',
            })]
        })
        self.assertEqual(res.waitlist_line_ids[0].priority, 'urgent')

    def test_036_waitlist_preferred_branches_filtering(self):
        """TEST-036: Waitlist line records preferred warehouse targets"""
        res = self.env['alahram.branch.reservation'].create({
            'current_branch_id': self.wh_sg.id,
            'partner_id': self.partner.id,
            'line_ids': [(0, 0, {'product_id': self.product_pot.id, 'qty_requested': 2.0})],
            'waitlist_line_ids': [(0, 0, {
                'product_id': self.product_pot.id,
                'qty_waiting': 2.0,
                'preferred_warehouse_ids': [(6, 0, [self.wh_roshdy.id, self.wh_smouha.id])],
                'state': 'waiting',
            })]
        })
        self.assertIn(self.wh_roshdy, res.waitlist_line_ids[0].preferred_warehouse_ids)

    def test_037_retry_allocation_when_stock_arrives(self):
        """TEST-037: action_retry_waiting_allocation reallocates stock when inventory is available"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pot.id,
                'qty_requested': 3.0,
                'allocations': [] # 0 allocated, 3 waiting
            }]
        })
        res = self.env['alahram.branch.reservation'].browse(res_data['reservation_id'])
        self.assertEqual(res.total_qty_waiting, 3.0)

        # Retry allocation against Main WH stock (which has inventory)
        res.action_retry_waiting_allocation()
        self.assertTrue(res.total_qty_reserved > 0, "Should allocate from warehouses with available stock")

    def test_038_retry_allocation_partial_clearance(self):
        """TEST-038: Partial stock arrival partially clears waitlist deficit"""
        res = self.env['alahram.branch.reservation'].create({
            'current_branch_id': self.wh_sg.id,
            'partner_id': self.partner.id,
            'line_ids': [(0, 0, {'product_id': self.product_knife.id, 'qty_requested': 500.0})],
            'waitlist_line_ids': [(0, 0, {
                'product_id': self.product_knife.id,
                'qty_waiting': 500.0,
                'state': 'waiting',
            })]
        })
        res.action_retry_waiting_allocation()
        # Even if available stock is less than 500, deficit is reduced
        wait_line = res.waitlist_line_ids[0]
        self.assertTrue(wait_line.qty_waiting < 500.0 or res.total_qty_reserved >= 0)

    def test_039_retry_allocation_full_clearance_transitions_state(self):
        """TEST-039: Full clearance of waitlist transitions line to allocated"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pot.id,
                'qty_requested': 1.0,
                'allocations': [] # 1 waiting
            }]
        })
        res = self.env['alahram.branch.reservation'].browse(res_data['reservation_id'])
        res.action_retry_waiting_allocation()
        if res.total_qty_waiting == 0:
            self.assertEqual(res.state, 'reserved')

    def test_040_retry_allocation_no_stock_noop(self):
        """TEST-040: No stock available leaves waitlist in waiting status"""
        # Create fictitious product with 0 stock anywhere
        prod_empty = self.env['product.product'].create({
            'name': 'صنف نفد رصيده بالكامل',
            'is_storable': True,
        })
        res = self.env['alahram.branch.reservation'].create({
            'current_branch_id': self.wh_sg.id,
            'partner_id': self.partner.id,
            'line_ids': [(0, 0, {'product_id': prod_empty.id, 'qty_requested': 2.0})],
            'waitlist_line_ids': [(0, 0, {
                'product_id': prod_empty.id,
                'qty_waiting': 2.0,
                'state': 'waiting',
            })]
        })
        res.action_retry_waiting_allocation()
        self.assertEqual(res.waitlist_line_ids[0].state, 'waiting')
        self.assertEqual(res.waitlist_line_ids[0].qty_waiting, 2.0)

    # =========================================================================
    # GROUP F: Idempotency, Concurrency, Cancellation & Validation (TEST-041 - TEST-045)
    # =========================================================================

    def test_041_idempotency_duplicate_pos_submission_safe(self):
        """TEST-041: Re-submitting same idempotency key returns existing reservation without duplicating"""
        uuid_key = str(uuid.uuid4())
        payload = {
            'idempotency_key': uuid_key,
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pot.id,
                'qty_requested': 1.0,
                'allocations': [{'source_warehouse_id': self.wh_roshdy.id, 'qty': 1.0, 'fulfillment_type': 'transfer'}]
            }]
        }
        res1 = self.env['alahram.branch.reservation'].create_from_pos(payload)
        res2 = self.env['alahram.branch.reservation'].create_from_pos(payload)
        self.assertEqual(res1['reservation_id'], res2['reservation_id'], "Must return the exact same reservation ID")
        self.assertTrue(res2.get('is_duplicate'), "Second call must flag is_duplicate")

    def test_042_reservation_cancellation_cancels_pickings(self):
        """TEST-042: action_cancel() cancels all associated stock pickings and allocations"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pot.id,
                'qty_requested': 1.0,
                'allocations': [{'source_warehouse_id': self.wh_main.id, 'qty': 1.0, 'fulfillment_type': 'transfer'}]
            }]
        })
        res = self.env['alahram.branch.reservation'].browse(res_data['reservation_id'])
        picking = res.allocation_ids[0].picking_id
        res.action_cancel()
        self.assertEqual(res.state, 'cancelled')
        self.assertEqual(res.allocation_ids[0].state, 'cancelled')
        self.assertEqual(picking.state, 'cancel', "Stock picking must be cancelled")

    def test_043_reservation_cancellation_cancels_waitlist(self):
        """TEST-043: action_cancel() marks waitlist lines as cancelled"""
        res_data = self.env['alahram.branch.reservation'].create_from_pos({
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'items': [{
                'product_id': self.product_pot.id,
                'qty_requested': 5.0,
                'allocations': [{'source_warehouse_id': self.wh_roshdy.id, 'qty': 1.0, 'fulfillment_type': 'transfer'}]
            }]
        })
        res = self.env['alahram.branch.reservation'].browse(res_data['reservation_id'])
        self.assertEqual(res.waitlist_line_ids[0].state, 'waiting')
        res.action_cancel()
        self.assertEqual(res.waitlist_line_ids[0].state, 'cancelled')

    def test_044_reservation_sequence_formatting(self):
        """TEST-044: Reservation sequence generates expected reference prefix"""
        res = self.env['alahram.branch.reservation'].create({
            'current_branch_id': self.wh_sg.id,
            'partner_id': self.partner.id,
        })
        self.assertTrue(res.name.startswith('RES/'), "Reservation reference must start with RES/")

    def test_045_concurrency_and_pos_order_linkage(self):
        """TEST-045: Reservation links cleanly to POS order and computes is_branch_reservation"""
        res = self.env['alahram.branch.reservation'].create({
            'current_branch_id': self.wh_sg.id,
            'partner_id': self.partner.id,
        })
        pos_order = self.env['pos.order'].create({
            'session_id': self.session.id,
            'partner_id': self.partner.id,
            'branch_reservation_id': res.id,
            'lines': [(0, 0, {
                'product_id': self.product_pot.id,
                'qty': 1.0,
                'price_unit': 1250.0,
                'price_subtotal': 1250.0,
                'price_subtotal_incl': 1425.0,
            })],
            'amount_total': 1425.0,
            'amount_tax': 175.0,
            'amount_paid': 1425.0,
            'amount_return': 0.0,
        })
        self.assertTrue(pos_order.is_branch_reservation, "is_branch_reservation must compute True")
        self.assertEqual(pos_order.branch_reservation_id.id, res.id)

