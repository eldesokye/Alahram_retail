# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError, AccessError
import uuid

class TestBridalPackagePOS(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].search([('name', 'ilike', 'الأهرام')], limit=1) or cls.env.company
        cls.wh_main = cls.env['stock.warehouse'].search([('code', '=', 'WH-MAIN')], limit=1)
        cls.wh_sg = cls.env['stock.warehouse'].search([('code', '=', 'WH-SG')], limit=1)
        cls.wh_roshdy = cls.env['stock.warehouse'].search([('code', '=', 'WH-ROSHDY')], limit=1)
        cls.wh_smouha = cls.env['stock.warehouse'].search([('code', '=', 'WH-SMOUHA')], limit=1)

        # Users with specific security groups
        cls.user_bm = cls.env['res.users'].search([('login', '=', 'bm.sidigaber@alahram.com')], limit=1)
        if not cls.user_bm:
            group_bm = cls.env.ref('alahram_retail_demo.group_alahram_branch_manager')
            cls.user_bm = cls.env['res.users'].create({
                'name': 'مدير فرع سيدي جابر (اختبار)',
                'login': 'test_bm_sidigaber@alahram.com',
                'group_ids': [(6, 0, [cls.env.ref('base.group_user').id, group_bm.id])],
            })

        cls.user_ops = cls.env['res.users'].search([('login', '=', 'ops.manager@alahram.com')], limit=1)
        if not cls.user_ops:
            group_ops = cls.env.ref('alahram_retail_demo.group_alahram_ops_manager')
            cls.user_ops = cls.env['res.users'].create({
                'name': 'مدير العمليات والتوسع (اختبار)',
                'login': 'test_ops_manager@alahram.com',
                'group_ids': [(6, 0, [cls.env.ref('base.group_user').id, group_ops.id])],
            })

        cls.user_seller = cls.env['res.users'].search([('login', '=', 'seller.sidigaber@alahram.com')], limit=1)
        if not cls.user_seller:
            group_seller = cls.env.ref('alahram_retail_demo.group_alahram_salesperson')
            cls.user_seller = cls.env['res.users'].create({
                'name': 'بائع صالة سيدي جابر (اختبار)',
                'login': 'test_seller_sidigaber@alahram.com',
                'group_ids': [(6, 0, [cls.env.ref('base.group_user').id, group_seller.id])],
            })

        cls.partner = cls.env['res.partner'].search([('name', 'ilike', 'سارة أحمد')], limit=1)
        if not cls.partner:
            cls.partner = cls.env['res.partner'].create({
                'name': 'سارة أحمد (عروسة تجريبية)',
                'phone': '01234567890',
                'company_id': cls.company.id,
            })

        cls.pos_config = cls.env['pos.config'].search([('name', 'ilike', 'سيدي جابر')], limit=1)
        if not cls.pos_config:
            cls.pos_config = cls.env['pos.config'].search([], limit=1)

        # Products for testing
        cls.prod_granite = cls.env['product.product'].search([('name', 'ilike', 'جرانيت')], limit=1)
        if not cls.prod_granite:
            cls.prod_granite = cls.env['product.product'].create({
                'name': 'طقم حلل جرانيت 9 قطع كحلي',
                'default_code': 'TEST-GR-09',
                'barcode': '622111111001',
                'lst_price': 5000.0,
                'is_storable': True,
            })

        cls.prod_granite_alt = cls.env['product.product'].search([('id', '!=', cls.prod_granite.id), ('name', 'ilike', 'جرانيت')], limit=1)
        if not cls.prod_granite_alt:
            cls.prod_granite_alt = cls.env['product.product'].create({
                'name': 'طقم حلل جرانيت 10 قطع رمادي بديل',
                'default_code': 'TEST-GR-10-ALT',
                'barcode': '622111111002',
                'lst_price': 5200.0,
                'is_storable': True,
            })

        cls.prod_stainless = cls.env['product.product'].search([('name', 'ilike', 'ستانلس')], limit=1)
        if not cls.prod_stainless:
            cls.prod_stainless = cls.env['product.product'].create({
                'name': 'طقم حلل ستانلس ستيل 18/10 سيجنتشر 8 قطع',
                'default_code': 'TEST-ST-08',
                'barcode': '622111111003',
                'lst_price': 4000.0,
                'is_storable': True,
            })

        cls.prod_tray = cls.env['product.product'].search([('name', 'ilike', 'صواني')], limit=1)
        if not cls.prod_tray:
            cls.prod_tray = cls.env['product.product'].create({
                'name': 'طقم صواني فرن بسبوسة وكيك 3 قطع',
                'default_code': 'TEST-TRY-03',
                'barcode': '622111111004',
                'lst_price': 1500.0,
                'is_storable': True,
            })

    def _set_stock_quant(self, product, location, qty):
        """Helper to safely set stock quant in test environment."""
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product.id,
            'location_id': location.id,
            'inventory_quantity': qty,
        }).action_apply_inventory()

    # =========================================================================
    # GROUP A: Basic Package Setup & Calculation Tests
    # =========================================================================

    def test_01_create_bridal_package_backend(self):
        """TEST-01: Create bridal package record and verify defaults."""
        pkg = self.env['alahram.bridal.configurator'].create({
            'partner_id': self.partner.id,
            'target_budget': 20000.0,
            'package_tier': 'gold_20k',
            'sector_granite': True,
            'sector_stainless': True,
            'sector_bakeware': True,
            'sector_frypans': True,
        })
        self.assertTrue(pkg.name.startswith('BRIDAL-') or pkg.name != 'جديد')
        self.assertEqual(pkg.target_budget, 20000.0)
        self.assertEqual(pkg.discount_state, 'no_discount')

    def test_02_package_tier_onchange_sets_budget(self):
        """TEST-02: Onchange of tier updates target budget."""
        pkg = self.env['alahram.bridal.configurator'].new({'package_tier': 'platinum_30k'})
        pkg._onchange_package_tier()
        self.assertEqual(pkg.target_budget, 30000.0)

        pkg.package_tier = 'royal_45k'
        pkg._onchange_package_tier()
        self.assertEqual(pkg.target_budget, 45000.0)

    def test_03_zero_automatic_discount_rule(self):
        """TEST-03: System must NOT deduct arbitrary variance as an automatic discount."""
        pkg = self.env['alahram.bridal.configurator'].create({
            'partner_id': self.partner.id,
            'target_budget': 10000.0,
            'line_ids': [
                (0, 0, {'product_id': self.prod_granite.id, 'quantity': 1.0, 'unit_price': 5000.0}),
                (0, 0, {'product_id': self.prod_stainless.id, 'quantity': 1.0, 'unit_price': 4000.0}),
                (0, 0, {'product_id': self.prod_tray.id, 'quantity': 2.0, 'unit_price': 1500.0}),
            ]
        })
        # Total is 5000 + 4000 + 3000 = 12000.0 (Variance is +2000)
        self.assertEqual(pkg.total_original_price, 12000.0)
        self.assertEqual(pkg.budget_variance, 2000.0)
        self.assertEqual(pkg.package_discount_amount, 0.0, "Automatic discount must remain zero!")
        self.assertEqual(pkg.final_package_price, 12000.0, "Final price must equal original price before approved discount!")

    # =========================================================================
    # GROUP B: POS Init Data, Suggestion & Alternatives
    # =========================================================================

    def test_04_get_pos_bridal_init_data(self):
        """TEST-04: RPC service returns initial metadata for POS dialog."""
        data = self.env['alahram.bridal.configurator'].get_pos_bridal_init_data(self.pos_config.id)
        self.assertTrue(data.get('success'))
        self.assertTrue(len(data.get('sectors', [])) == 9)
        self.assertTrue(len(data.get('tiers', [])) == 5)
        self.assertTrue(len(data.get('products', [])) > 0)
        self.assertIn('user_permissions', data)

    def test_05_suggest_package_pos(self):
        """TEST-05: POS suggestion returns intelligent line items with live stock."""
        res = self.env['alahram.bridal.configurator'].suggest_package_pos({
            'target_budget': 20000.0,
            'sectors': {'granite': True, 'stainless': True, 'bakeware': True},
            'pos_config_id': self.pos_config.id,
        })
        self.assertTrue(res.get('success'))
        self.assertTrue(len(res.get('lines', [])) >= 2)
        self.assertIn('total_original_price', res)
        self.assertIn('budget_variance', res)

    def test_06_get_product_alternatives_pos(self):
        """TEST-06: Fetches eligible product alternatives with multi-branch availability."""
        res = self.env['alahram.bridal.configurator'].get_product_alternatives_pos(
            self.prod_granite.id, self.pos_config.id
        )
        self.assertTrue(res.get('success'))
        self.assertEqual(res.get('original_product_id'), self.prod_granite.id)
        self.assertIn('alternatives', res)

    # =========================================================================
    # GROUP C: Multi-Tier Discount Governance Tests
    # =========================================================================

    def test_07_discount_greater_than_7_pct_strictly_forbidden(self):
        """TEST-07: Discount exceeding 7% triggers ValidationError."""
        pkg = self.env['alahram.bridal.configurator'].create({
            'partner_id': self.partner.id,
            'target_budget': 20000.0,
        })
        with self.assertRaises(ValidationError):
            pkg.write({'requested_discount_pct': 7.5})

    def test_08_negative_discount_forbidden(self):
        """TEST-08: Negative discount raises ValidationError."""
        pkg = self.env['alahram.bridal.configurator'].create({
            'partner_id': self.partner.id,
            'target_budget': 20000.0,
        })
        with self.assertRaises(ValidationError):
            pkg.write({'requested_discount_pct': -2.0})

    def test_09_discount_under_5_pct_requires_branch_manager(self):
        """TEST-09: Discount <= 5% sets state to pending_bm and branch manager can approve."""
        pkg = self.env['alahram.bridal.configurator'].create({
            'partner_id': self.partner.id,
            'target_budget': 20000.0,
            'requested_discount_pct': 4.0,
            'line_ids': [(0, 0, {'product_id': self.prod_granite.id, 'quantity': 1.0, 'unit_price': 5000.0})],
        })
        pkg.action_request_discount()
        self.assertEqual(pkg.discount_state, 'pending_bm')

        # Branch manager approves
        pkg.with_user(self.user_bm).action_approve_discount_branch_manager()
        self.assertEqual(pkg.discount_state, 'approved')
        self.assertEqual(pkg.package_discount_amount, 200.0) # 4% of 5000
        self.assertEqual(pkg.final_package_price, 4800.0)

    def test_10_branch_manager_blocked_from_approving_over_5_pct(self):
        """TEST-10: Branch manager cannot approve discount > 5%."""
        pkg = self.env['alahram.bridal.configurator'].create({
            'partner_id': self.partner.id,
            'target_budget': 20000.0,
            'requested_discount_pct': 6.0,
            'line_ids': [(0, 0, {'product_id': self.prod_granite.id, 'quantity': 1.0, 'unit_price': 5000.0})],
        })
        pkg.action_request_discount()
        self.assertEqual(pkg.discount_state, 'pending_ops')

        # Branch Manager attempts approval -> AccessError
        with self.assertRaises(AccessError):
            pkg.with_user(self.user_bm).action_approve_discount_branch_manager()

        # Operations Manager can approve
        pkg.with_user(self.user_ops).action_approve_discount_ops_manager()
        self.assertEqual(pkg.discount_state, 'approved')
        self.assertEqual(pkg.package_discount_amount, 300.0) # 6% of 5000
        self.assertEqual(pkg.final_package_price, 4700.0)

    def test_11_discount_refusal_restores_original_price(self):
        """TEST-11: Refusal resets discount to 0% and restores full original price."""
        pkg = self.env['alahram.bridal.configurator'].create({
            'partner_id': self.partner.id,
            'target_budget': 20000.0,
            'requested_discount_pct': 4.5,
            'line_ids': [(0, 0, {'product_id': self.prod_granite.id, 'quantity': 1.0, 'unit_price': 5000.0})],
        })
        pkg.action_request_discount()
        pkg.with_user(self.user_bm).action_refuse_discount()
        self.assertEqual(pkg.discount_state, 'refused')
        self.assertEqual(pkg.requested_discount_pct, 0.0)
        self.assertEqual(pkg.package_discount_amount, 0.0)
        self.assertEqual(pkg.final_package_price, 5000.0)

    # =========================================================================
    # GROUP D: Cross-Branch Reservation & Stock Operations Integration
    # =========================================================================

    def test_12_save_and_reserve_package_pos_local_stock(self):
        """TEST-12: Full atomic reservation from POS tablet with local stock."""
        # Set stock in Sidi Gaber warehouse
        if self.wh_sg:
            self._set_stock_quant(self.prod_granite, self.wh_sg.lot_stock_id, 10.0)

        idempotency_key = f"TEST-BRIDAL-{uuid.uuid4().hex[:8]}"
        payload = {
            'partner_id': self.partner.id,
            'customer_name': self.partner.name,
            'customer_phone': self.partner.phone,
            'target_budget': 10000.0,
            'requested_discount_pct': 0.0,
            'pos_config_id': self.pos_config.id,
            'idempotency_key': idempotency_key,
            'do_reserve': True,
            'lines': [{
                'product_id': self.prod_granite.id,
                'quantity': 2.0,
                'unit_price': self.prod_granite.lst_price,
                'fulfillment_type': 'transfer',
                'source_warehouse_id': self.wh_sg.id if self.wh_sg else False,
            }]
        }

        res = self.env['alahram.bridal.configurator'].save_and_reserve_package_pos(payload)
        self.assertTrue(res.get('success'))
        self.assertIsNotNone(res.get('package_id'))
        self.assertIsNotNone(res.get('reservation_id'))

        pkg = self.env['alahram.bridal.configurator'].browse(res['package_id'])
        self.assertEqual(pkg.reservation_id.id, res['reservation_id'])
        self.assertTrue(len(pkg.line_ids) == 1)

    def test_13_save_and_reserve_package_pos_remote_transfer(self):
        """TEST-13: Reservation generates real internal transfer picking from remote warehouse."""
        if self.wh_roshdy:
            self._set_stock_quant(self.prod_stainless, self.wh_roshdy.lot_stock_id, 5.0)

        idempotency_key = f"TEST-REMOTE-{uuid.uuid4().hex[:8]}"
        payload = {
            'partner_id': self.partner.id,
            'customer_name': self.partner.name,
            'target_budget': 15000.0,
            'pos_config_id': self.pos_config.id,
            'idempotency_key': idempotency_key,
            'do_reserve': True,
            'lines': [{
                'product_id': self.prod_stainless.id,
                'quantity': 1.0,
                'unit_price': self.prod_stainless.lst_price,
                'fulfillment_type': 'transfer',
                'source_warehouse_id': self.wh_roshdy.id if self.wh_roshdy else False,
            }]
        }

        res = self.env['alahram.bridal.configurator'].save_and_reserve_package_pos(payload)
        self.assertTrue(res.get('success'))
        pkg = self.env['alahram.bridal.configurator'].browse(res['package_id'])
        line = pkg.line_ids[0]
        self.assertEqual(line.sourcing_status, 'transfer_requested')
        self.assertTrue(line.picking_id, "Must link to real stock picking!")

    def test_14_save_and_reserve_package_pos_source_pickup(self):
        """TEST-14: Reservation with customer pickup at source warehouse."""
        if self.wh_roshdy:
            self._set_stock_quant(self.prod_tray, self.wh_roshdy.lot_stock_id, 8.0)

        payload = {
            'partner_id': self.partner.id,
            'target_budget': 5000.0,
            'pos_config_id': self.pos_config.id,
            'idempotency_key': f"TEST-PICKUP-{uuid.uuid4().hex[:8]}",
            'do_reserve': True,
            'lines': [{
                'product_id': self.prod_tray.id,
                'quantity': 2.0,
                'unit_price': self.prod_tray.lst_price,
                'fulfillment_type': 'pickup',
                'source_warehouse_id': self.wh_roshdy.id if self.wh_roshdy else False,
            }]
        }

        res = self.env['alahram.bridal.configurator'].save_and_reserve_package_pos(payload)
        self.assertTrue(res.get('success'))
        pkg = self.env['alahram.bridal.configurator'].browse(res['package_id'])
        line = pkg.line_ids[0]
        self.assertEqual(line.sourcing_status, 'source_pickup_ready')

    def test_15_split_sourcing_across_multiple_branches(self):
        """TEST-15: Sourcing requested quantity split across two warehouses."""
        if self.wh_sg and self.wh_roshdy:
            self._set_stock_quant(self.prod_granite, self.wh_sg.lot_stock_id, 2.0)
            self._set_stock_quant(self.prod_granite, self.wh_roshdy.lot_stock_id, 3.0)

        payload = {
            'partner_id': self.partner.id,
            'target_budget': 25000.0,
            'pos_config_id': self.pos_config.id,
            'idempotency_key': f"TEST-SPLIT-{uuid.uuid4().hex[:8]}",
            'do_reserve': True,
            'lines': [{
                'product_id': self.prod_granite.id,
                'quantity': 5.0,
                'unit_price': self.prod_granite.lst_price,
                'allocations': [
                    {'source_warehouse_id': self.wh_sg.id if self.wh_sg else False, 'qty': 2.0, 'fulfillment_type': 'transfer'},
                    {'source_warehouse_id': self.wh_roshdy.id if self.wh_roshdy else False, 'qty': 3.0, 'fulfillment_type': 'transfer'},
                ]
            }]
        }

        res = self.env['alahram.bridal.configurator'].save_and_reserve_package_pos(payload)
        self.assertTrue(res.get('success'))
        pkg = self.env['alahram.bridal.configurator'].browse(res['package_id'])
        reservation = pkg.reservation_id
        self.assertEqual(len(reservation.allocation_ids), 2, "Must create 2 separate allocations for the split")
        self.assertEqual(sum(reservation.allocation_ids.mapped('qty_allocated')), 5.0)

    def test_16_insufficient_stock_creates_waitlist_deficit(self):
        """TEST-16: Stock deficit automatically enters waiting list without failure."""
        if self.wh_sg:
            self._set_stock_quant(self.prod_stainless, self.wh_sg.lot_stock_id, 1.0)

        payload = {
            'partner_id': self.partner.id,
            'target_budget': 20000.0,
            'pos_config_id': self.pos_config.id,
            'idempotency_key': f"TEST-DEFICIT-{uuid.uuid4().hex[:8]}",
            'do_reserve': True,
            'lines': [{
                'product_id': self.prod_stainless.id,
                'quantity': 3.0,
                'unit_price': self.prod_stainless.lst_price,
                'allocations': [
                    {'source_warehouse_id': self.wh_sg.id if self.wh_sg else False, 'qty': 1.0, 'fulfillment_type': 'transfer'},
                ]
            }]
        }

        res = self.env['alahram.bridal.configurator'].save_and_reserve_package_pos(payload)
        self.assertTrue(res.get('success'))
        pkg = self.env['alahram.bridal.configurator'].browse(res['package_id'])
        self.assertTrue(len(pkg.reservation_id.waitlist_line_ids) > 0)
        self.assertEqual(pkg.reservation_id.waitlist_line_ids[0].qty_waiting, 2.0)

    # =========================================================================
    # GROUP E: POS Cart Loading & Cancellation Tests
    # =========================================================================

    def test_17_load_to_pos_cart_blocked_when_discount_pending(self):
        """TEST-17: Cart injection blocked if package has an unapproved pending discount."""
        pkg = self.env['alahram.bridal.configurator'].create({
            'partner_id': self.partner.id,
            'target_budget': 10000.0,
            'requested_discount_pct': 4.0,
            'discount_state': 'pending_bm',
            'line_ids': [(0, 0, {'product_id': self.prod_granite.id, 'quantity': 1.0, 'unit_price': 5000.0})],
        })
        res = self.env['alahram.bridal.configurator'].load_package_to_pos_cart(pkg.id)
        self.assertFalse(res.get('success'))
        self.assertIn('لا يمكن تحصيل', res.get('error', ''))

    def test_18_load_to_pos_cart_success_when_approved(self):
        """TEST-18: Cart injection succeeds when discount is approved."""
        pkg = self.env['alahram.bridal.configurator'].create({
            'partner_id': self.partner.id,
            'target_budget': 10000.0,
            'requested_discount_pct': 5.0,
            'discount_state': 'approved',
            'line_ids': [(0, 0, {'product_id': self.prod_granite.id, 'quantity': 1.0, 'unit_price': 5000.0})],
        })
        res = self.env['alahram.bridal.configurator'].load_package_to_pos_cart(pkg.id)
        self.assertTrue(res.get('success'))
        self.assertEqual(res.get('discount'), 5.0)
        self.assertEqual(len(res.get('items', [])), 1)

    def test_19_action_cancel_package_and_reservation(self):
        """TEST-19: Cancelling bridal package atomically cancels reservation and releases pickings."""
        pkg = self.env['alahram.bridal.configurator'].create({
            'partner_id': self.partner.id,
            'target_budget': 10000.0,
            'line_ids': [(0, 0, {'product_id': self.prod_granite.id, 'quantity': 1.0, 'unit_price': 5000.0})],
        })
        # Mock reservation
        res_header = self.env['alahram.branch.reservation'].create({
            'partner_id': self.partner.id,
            'customer_name': self.partner.name,
            'state': 'reserved',
        })
        pkg.reservation_id = res_header.id
        pkg.action_cancel_package_and_reservation()
        self.assertEqual(pkg.state, 'draft')
        self.assertEqual(res_header.state, 'cancelled')

    # =========================================================================
    # GROUP F: Idempotency Protection Test
    # =========================================================================

    def test_20_idempotency_prevents_duplicate_package_creation(self):
        """TEST-20: Repeated POS requests with identical idempotency key do not duplicate packages."""
        key = f"IDEMPOTENT-KEY-{uuid.uuid4().hex[:8]}"
        payload = {
            'partner_id': self.partner.id,
            'target_budget': 10000.0,
            'pos_config_id': self.pos_config.id,
            'idempotency_key': key,
            'do_reserve': False,
            'lines': [{'product_id': self.prod_granite.id, 'quantity': 1.0, 'unit_price': 5000.0}]
        }
        res1 = self.env['alahram.bridal.configurator'].save_and_reserve_package_pos(payload)
        res2 = self.env['alahram.bridal.configurator'].save_and_reserve_package_pos(payload)
        self.assertEqual(res1['package_id'], res2['package_id'])
        self.assertTrue(res2.get('is_duplicate', False))

    def test_21_walkin_customer_auto_resolves_partner(self):
        """TEST-21: Walk-in POS customer without partner_id resolves customer by phone or name without crashing."""
        test_phone = f"010{uuid.uuid4().hex[:8]}"
        payload = {
            'partner_id': False,
            'customer_name': 'عروسة جديدة للمحل',
            'customer_phone': test_phone,
            'target_budget': 10000.0,
            'pos_config_id': self.pos_config.id,
            'idempotency_key': f"TEST-WALKIN-{uuid.uuid4().hex[:8]}",
            'do_reserve': False,
            'lines': [{'product_id': self.prod_granite.id, 'quantity': 1.0, 'unit_price': 5000.0}]
        }
        res = self.env['alahram.bridal.configurator'].save_and_reserve_package_pos(payload)
        self.assertTrue(res.get('success'))
        pkg = self.env['alahram.bridal.configurator'].browse(res['package_id'])
        self.assertTrue(pkg.partner_id)
        self.assertEqual(pkg.partner_id.phone, test_phone)

    def test_22_save_and_subsequent_branch_reservation_link(self):
        """TEST-22: Workflow A 2-step link: package saved with do_reserve=False, then linked via create_from_pos."""
        payload = {
            'partner_id': self.partner.id,
            'target_budget': 15000.0,
            'pos_config_id': self.pos_config.id,
            'idempotency_key': f"TEST-2STEP-{uuid.uuid4().hex[:8]}",
            'do_reserve': False,
            'lines': [{'product_id': self.prod_granite.id, 'quantity': 1.0, 'unit_price': 5000.0}]
        }
        res = self.env['alahram.bridal.configurator'].save_and_reserve_package_pos(payload)
        self.assertTrue(res.get('success'))
        pkg_id = res['package_id']
        pkg = self.env['alahram.bridal.configurator'].browse(pkg_id)
        self.assertFalse(pkg.reservation_id)

        # Cashier confirms from BranchReservationDialog
        res_payload = {
            'partner_id': self.partner.id,
            'customer_name': self.partner.name,
            'customer_phone': self.partner.phone or '01000000000',
            'pos_config_id': self.pos_config.id,
            'bridal_configurator_id': pkg_id,
            'items': [{
                'product_id': self.prod_granite.id,
                'qty_requested': 1.0,
                'price_unit': 5000.0,
                'allocations': [{
                    'source_warehouse_id': self.wh_sg.id if self.wh_sg else False,
                    'qty': 1.0,
                    'fulfillment_type': 'transfer',
                }]
            }]
        }
        res_result = self.env['alahram.branch.reservation'].create_from_pos(res_payload)
        self.assertTrue(res_result.get('success'))
        self.assertEqual(pkg.reservation_id.id, res_result['reservation_id'])
        self.assertEqual(pkg.state, 'reserved')

    def test_23_budget_variance_and_shortfall_calculation(self):
        """TEST-23: Mathematical consistency between target difference and minimum shortfall."""
        # Target: 20000, Min bound: 18000, Total price: 17350
        pkg = self.env['alahram.bridal.configurator'].create({
            'partner_id': self.partner.id,
            'target_budget': 20000.0,
            'package_tier': 'gold_20k',
            'line_ids': [
                (0, 0, {'product_id': self.prod_granite.id, 'quantity': 1.0, 'unit_price': 17350.0}),
            ],
        })
        pkg._compute_totals()
        self.assertEqual(pkg.budget_match_status, 'out_of_bounds')
        self.assertEqual(pkg.lower_bound, 18000.0)
        # Difference from minimum bound (18000 - 17350 = 650)
        self.assertIn("650.00", pkg.budget_feedback_message)
        # Difference from target budget (20000 - 17350 = 2650)
        self.assertIn("2650.00", pkg.budget_feedback_message)
