# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError, AccessError

class TestAlahramE2EScenarios(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].search([('name', 'ilike', 'الأهرام')], limit=1) or cls.env.company
        cls.wh_main = cls.env['stock.warehouse'].search([('code', '=', 'WH-MAIN')], limit=1)
        cls.wh_sg = cls.env['stock.warehouse'].search([('code', '=', 'WH-SG')], limit=1)
        cls.wh_roshdy = cls.env['stock.warehouse'].search([('code', '=', 'WH-ROSHDY')], limit=1)
        cls.wh_transit_loc = cls.env['stock.location'].search([('company_id', '=', cls.company.id), ('name', 'ilike', 'Transfer Store')], limit=1)
        cls.bm_user = cls.env['res.users'].search([('login', '=', 'bm.sidigaber@alahram.com')], limit=1)
        if not cls.bm_user:
            group_bm = cls.env.ref('alahram_retail_demo.group_alahram_branch_manager')
            cls.bm_user = cls.env['res.users'].create({
                'name': 'مدير فرع سيدي جابر (اختبار)',
                'login': 'test_bm_e2e@alahram.com',
                'group_ids': [(6, 0, [cls.env.ref('base.group_user').id, group_bm.id])],
            })
        cls.sales_user = cls.env['res.users'].search([('login', '=', 'sales.sidigaber@alahram.com')], limit=1)
        if not cls.sales_user:
            cls.sales_user = cls.bm_user

    def test_01_product_code_uniqueness_guard(self):
        """Prevent legacy Fox/RM duplicate coding chaos"""
        existing_prod = self.env['product.product'].search([('barcode', '=', '6221049011701')], limit=1)
        self.assertTrue(existing_prod, "Product 6221049011701 must exist")

        # Creating another product with the same barcode or default_code should be prevented
        with self.assertRaises((ValidationError, UserError)):
            self.env['product.template'].create({
                'name': 'صنف مكرر غير شرعي',
                'barcode': '6221049011701',
                'company_id': self.company.id,
            })

    def test_02_pos_discount_approval_thresholds(self):
        """Verify <= 5% auto-approval vs > 5% Branch Manager approval requirement"""
        pos_config = self.env['pos.config'].search([('name', 'ilike', 'كاشير 1')], limit=1)
        session = pos_config.current_session_id
        if not session or session.state != 'opened':
            cashier_user = self.env['res.users'].search([('login', '=', 'cashier1.sidigaber@alahram.com')], limit=1)
            session = self.env['pos.session'].sudo().create({
                'user_id': cashier_user.id if cashier_user else self.env.user.id,
                'config_id': pos_config.id,
            })
            session.sudo().write({'state': 'opened'})

        product = self.env['product.product'].search([('barcode', '=', '6221049430762')], limit=1)
        customer = self.env['res.partner'].search([('name', 'ilike', 'منال عبد الرحمن')], limit=1)

        # 1. 3% Discount should be auto-approved
        sub3 = round(product.list_price * 0.97, 2)
        order_3pct = self.env['pos.order'].create({
            'session_id': session.id,
            'partner_id': customer.id,
            'lines': [(0, 0, {
                'product_id': product.id,
                'qty': 1.0,
                'price_unit': product.list_price,
                'discount': 3.0,
                'price_subtotal': sub3,
                'price_subtotal_incl': sub3,
            })],
            'amount_tax': 0.0,
            'amount_total': sub3,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })
        self.assertEqual(order_3pct.discount_approval_status, 'auto_approved')

        # 2. 7% Discount should be pending approval
        sub7 = round(product.list_price * 0.93, 2)
        order_7pct = self.env['pos.order'].create({
            'session_id': session.id,
            'partner_id': customer.id,
            'lines': [(0, 0, {
                'product_id': product.id,
                'qty': 1.0,
                'price_unit': product.list_price,
                'discount': 7.0,
                'price_subtotal': sub7,
                'price_subtotal_incl': sub7,
            })],
            'amount_tax': 0.0,
            'amount_total': sub7,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })
        self.assertEqual(order_7pct.discount_approval_status, 'pending')

        # 3. Branch manager approves discount
        order_7pct.with_user(self.bm_user).action_approve_special_discount()
        self.assertEqual(order_7pct.discount_approval_status, 'approved')
        self.assertEqual(order_7pct.discount_approver_id, self.bm_user)

    def test_03_cross_branch_stock_reservation_and_transit(self):
        """Verify 2-step inter-branch transfer workflow: Roshdy -> Transit -> Sidi Gaber"""
        product = self.env['product.product'].search([('barcode', '=', '6221049011701')], limit=1)
        
        reserve = self.env['alahram.cross.branch.reserve'].create({
            'product_id': product.id,
            'quantity': 1.0,
            'src_warehouse_id': self.wh_roshdy.id,
            'dest_warehouse_id': self.wh_sg.id,
            'transit_location_id': self.wh_transit_loc.id if self.wh_transit_loc else False,
        })
        self.assertEqual(reserve.state, 'draft')

        # Confirm reservation
        reserve.action_confirm_reservation()
        self.assertEqual(reserve.state, 'reserved')

        # Ship to transit
        reserve.action_ship_to_transit()
        self.assertEqual(reserve.state, 'shipped')
        self.assertTrue(reserve.picking_out_id)

        # Receive at destination
        reserve.action_receive_at_branch()
        self.assertEqual(reserve.state, 'received')
        self.assertTrue(reserve.picking_in_id)

    def test_04_bridal_package_configurator(self):
        """Verify smart bridal package spans 5 categories with target budget deduction"""
        customer = self.env['res.partner'].search([('name', 'ilike', 'منال عبد الرحمن')], limit=1)
        if not customer:
            customer = self.env['res.partner'].search([('customer_rank', '>', 0)], limit=1) or self.env['res.partner'].search([], limit=1)
        configurator = self.env['alahram.bridal.configurator'].create({
            'partner_id': customer.id,
            'target_budget': 15000.0,
            'package_tier': 'silver_15k',
        })
        configurator.action_auto_generate_balanced_package()
        self.assertGreaterEqual(len(configurator.line_ids), 4)
        self.assertEqual(configurator.state, 'calculated')

        # Generate Sale Order
        configurator.action_create_sale_order()
        self.assertEqual(configurator.state, 'order_created')
        self.assertTrue(configurator.sale_order_id)
        self.assertAlmostEqual(configurator.final_package_price, 15000.0, delta=2000.0)

    def test_05_ai_assistant_queries(self):
        """Verify all 6 AI Assistant queries execute and produce data-backed insights"""
        queries = [
            'q1_lowest_branches',
            'q2_dead_stock',
            'q3_stockout_sidigaber',
            'q4_promo_candidates',
            'q5_high_returns',
            'q6_budget_order',
        ]
        for q in queries:
            ai = self.env['alahram.ai.assistant'].create({
                'name': f"Test AI Query {q}",
                'user_query': q,
                'target_budget': 15000.0,
            })
            ai.action_execute_ai_query()
            self.assertTrue(ai.ai_response_html, f"Query {q} must return HTML insight")
            self.assertTrue(ai.action_executed_summary, f"Query {q} must return summary")
            if q == 'q6_budget_order':
                self.assertTrue(ai.generated_sale_order_id, "Q6 must create sale order")
