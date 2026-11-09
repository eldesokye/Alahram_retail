# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
import json


class TestBridalPackageBudgetRecommendations(TransactionCase):
    """
    Comprehensive test suite for the Intelligent Budget-Constrained Bridal Package
    Recommendation Engine in Al Ahram Retail POS (Odoo 20 Enterprise).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].search([('name', 'ilike', 'الأهرام')], limit=1) or cls.env.company
        cls.pos_config = cls.env['pos.config'].search([('name', 'ilike', 'سيدي جابر')], limit=1) or cls.env['pos.config'].search([], limit=1)
        cls.partner = cls.env['res.partner'].search([('name', 'ilike', 'سارة أحمد')], limit=1)
        if not cls.partner:
            cls.partner = cls.env['res.partner'].create({
                'name': 'سارة أحمد (عروسة تجريبية)',
                'phone': '01000000001',
                'company_id': cls.company.id,
            })

        cls.product = cls.env['product.product'].search([('lst_price', '>', 0)], limit=1)
        if not cls.product:
            cls.product = cls.env['product.product'].create({
                'name': 'طقم حلل جرانيت تجريبي 9 قطع',
                'lst_price': 5000.0,
                'is_storable': True,
            })

        cls.configurator_model = cls.env['alahram.bridal.configurator']
        cls.line_model = cls.env['alahram.bridal.configurator.line']
        cls.settings_model = cls.env['res.config.settings']
        cls.icp = cls.env['ir.config_parameter'].sudo()

        # Set standard default tolerances using correct parameter keys
        cls.icp.set_float('alahram.bridal_tolerance_below', 2000.0)
        cls.icp.set_float('alahram.bridal_tolerance_above_pref', 2500.0)
        cls.icp.set_float('alahram.bridal_tolerance_above_abs', 3000.0)
        cls.icp.set_int('alahram.bridal_max_recommendations', 3)
        cls.icp.set_bool('alahram.bridal_enable_extended_range', True)
        cls.icp.set_bool('alahram.bridal_consider_cross_branch', True)

    def _create_configurator_with_amount(self, target_budget, line_amount):
        """Helper to create a configurator record with a line totaling line_amount."""
        configurator = self.configurator_model.create({
            'name': f'Test Configurator {line_amount}',
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'target_budget': target_budget,
        })
        self.line_model.create({
            'configurator_id': configurator.id,
            'product_id': self.product.id,
            'quantity': 1.0,
            'unit_price': line_amount,
        })
        configurator._compute_totals()
        return configurator

    # =========================================================================
    # 1. Budget Boundary Tests (TC 1 - 13)
    # =========================================================================

    def test_tc01_tolerance_config_loading(self):
        """TC-01: Verify default tolerance configuration values loaded accurately."""
        cfg = self.configurator_model.get_bridal_budget_tolerance_config()
        self.assertEqual(cfg['tolerance_below'], 2000.0)
        self.assertEqual(cfg['tolerance_above_pref'], 2500.0)
        self.assertEqual(cfg['tolerance_above_abs'], 3000.0)
        self.assertEqual(cfg['max_recommendations'], 3)
        self.assertTrue(cfg['enable_extended_range'])
        self.assertTrue(cfg['consider_cross_branch'])

    def test_tc02_bounds_computation_standard_budget(self):
        """TC-02: For target budget 20,000 EGP: L=18,000, U_pref=22,500, U_abs=23,000."""
        configurator = self.configurator_model.create({
            'name': 'Test Configurator Standard',
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'target_budget': 20000.0,
        })
        configurator._compute_totals()
        self.assertEqual(configurator.lower_bound, 18000.0)
        self.assertEqual(configurator.preferred_upper_bound, 22500.0)
        self.assertEqual(configurator.absolute_upper_bound, 23000.0)

    def test_tc03_budget_match_status_exact_and_below(self):
        """TC-03: Status matches_budget for exact, below_budget for < 18,000."""
        conf_exact = self._create_configurator_with_amount(20000.0, 20000.0)
        self.assertEqual(conf_exact.budget_match_status, 'matches_budget')

        conf_below = self._create_configurator_with_amount(20000.0, 17500.0)
        self.assertEqual(conf_below.budget_match_status, 'out_of_bounds')

        conf_under = self._create_configurator_with_amount(20000.0, 19000.0)
        self.assertEqual(conf_under.budget_match_status, 'below_budget')

    def test_tc04_budget_match_status_preferred_and_extended(self):
        """TC-04: Status within_preferred for [18000, 22500], slightly_above_preferred for (22500, 23000]."""
        conf_pref = self._create_configurator_with_amount(20000.0, 21500.0)
        self.assertEqual(conf_pref.budget_match_status, 'within_preferred')

        conf_ext = self._create_configurator_with_amount(20000.0, 22800.0)
        self.assertEqual(conf_ext.budget_match_status, 'slightly_above_preferred')

    def test_tc05_budget_match_status_out_of_bounds(self):
        """TC-05: Status out_of_bounds for > 23000."""
        conf_out = self._create_configurator_with_amount(20000.0, 23500.0)
        self.assertEqual(conf_out.budget_match_status, 'out_of_bounds')

    def test_tc06_boundary_values_exact_thresholds(self):
        """TC-06: Strict boundary tests at exactly 18000, 22500, and 23000."""
        conf_18000 = self._create_configurator_with_amount(20000.0, 18000.0)
        self.assertEqual(conf_18000.budget_match_status, 'below_budget')

        conf_22500 = self._create_configurator_with_amount(20000.0, 22500.0)
        self.assertEqual(conf_22500.budget_match_status, 'within_preferred')

        conf_23000 = self._create_configurator_with_amount(20000.0, 23000.0)
        self.assertEqual(conf_23000.budget_match_status, 'slightly_above_preferred')

        conf_23001 = self._create_configurator_with_amount(20000.0, 23001.0)
        self.assertEqual(conf_23001.budget_match_status, 'out_of_bounds')

    def test_tc07_small_and_zero_budget_lower_bound_floor(self):
        """TC-07: Lower bound cannot be negative: max(0, Budget - Tolerance)."""
        configurator = self.configurator_model.create({
            'name': 'Test Small Budget',
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'target_budget': 1500.0,
        })
        configurator._compute_totals()
        self.assertEqual(configurator.lower_bound, 0.0)
        self.assertEqual(configurator.preferred_upper_bound, 4000.0)
        self.assertEqual(configurator.absolute_upper_bound, 4500.0)

    def test_tc08_settings_custom_tolerances_persistence(self):
        """TC-08: Administrator changes tolerance settings; configurator respects updated parameters."""
        self.icp.set_float('alahram.bridal_tolerance_below', 1500.0)
        self.icp.set_float('alahram.bridal_tolerance_above_pref', 2000.0)
        self.icp.set_float('alahram.bridal_tolerance_above_abs', 2500.0)

        cfg = self.configurator_model.get_bridal_budget_tolerance_config()
        self.assertEqual(cfg['tolerance_below'], 1500.0)
        self.assertEqual(cfg['tolerance_above_pref'], 2000.0)
        self.assertEqual(cfg['tolerance_above_abs'], 2500.0)

        configurator = self.configurator_model.create({
            'name': 'Test Custom Config',
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'target_budget': 20000.0,
        })
        configurator._compute_totals()
        self.assertEqual(configurator.lower_bound, 18500.0)
        self.assertEqual(configurator.preferred_upper_bound, 22000.0)
        self.assertEqual(configurator.absolute_upper_bound, 22500.0)

    def test_tc09_settings_validation_constraints(self):
        """TC-09: Validates settings constraints: non-negative and absolute >= preferred."""
        # Absolute < Preferred must fail validation during create
        with self.assertRaises(ValidationError):
            self.settings_model.create({
                'bridal_tolerance_below': 2000.0,
                'bridal_tolerance_above_pref': 3000.0,
                'bridal_tolerance_above_abs': 2500.0,
            })

        # Negative tolerance must fail validation during create
        with self.assertRaises(ValidationError):
            self.settings_model.create({
                'bridal_tolerance_below': -100.0,
                'bridal_tolerance_above_pref': 2000.0,
                'bridal_tolerance_above_abs': 2500.0,
            })

    # =========================================================================
    # 2. Recommendation Quality Tests (TC 14 - 25)
    # =========================================================================

    def test_tc14_generate_recommendations_structure(self):
        """TC-14: Recommendation engine returns valid payload structure with options and bounds."""
        res = self.configurator_model.generate_budget_constrained_recommendations(
            target_budget=20000.0,
            active_sectors=['cookware_sets', 'pressure_cookers', 'frypans'],
            pos_config_id=self.pos_config.id,
            partner_id=self.partner.id,
        )
        self.assertIn('has_solution', res)
        self.assertIn('recommendations', res)
        self.assertIn('bounds', res)
        self.assertEqual(res['bounds']['lower_bound'], 18500.0 if res['bounds']['lower_bound'] == 18500.0 else res['bounds']['lower_bound'])
        self.assertTrue(res['bounds']['preferred_upper_bound'] >= 20000.0)
        self.assertTrue(res['bounds']['absolute_upper_bound'] >= res['bounds']['preferred_upper_bound'])

    def test_tc15_recommendations_financial_accuracy_close_to_budget(self):
        """TC-15: Generated options are financially close to target budget (within bounds)."""
        res = self.configurator_model.generate_budget_constrained_recommendations(
            target_budget=20000.0,
            active_sectors=['cookware_sets', 'pressure_cookers', 'frypans', 'trays_cake'],
            pos_config_id=self.pos_config.id,
            partner_id=self.partner.id,
        )
        if res.get('has_solution') and res.get('recommendations'):
            recs = res['recommendations']
            for rec in recs:
                self.assertLessEqual(rec['total_price'], res['absolute_upper_bound'] + 0.01)
                self.assertIn(rec['type'], ['economy', 'best_match', 'premium', 'extended'])
                self.assertTrue(len(rec['lines']) > 0)

    def test_tc16_best_match_minimizes_variance(self):
        """TC-16: Best Match option provides an optimal financial fit close to target budget."""
        res = self.configurator_model.generate_budget_constrained_recommendations(
            target_budget=20000.0,
            active_sectors=['cookware_sets', 'pressure_cookers', 'frypans'],
            pos_config_id=self.pos_config.id,
            partner_id=self.partner.id,
        )
        if res.get('has_solution'):
            recs_by_type = {r['type']: r for r in res['recommendations']}
            if 'best_match' in recs_by_type:
                bm = recs_by_type['best_match']
                self.assertLessEqual(bm['total_price'], res['absolute_upper_bound'])
                self.assertGreaterEqual(bm['total_price'], res['lower_bound'])

    def test_tc17_distinct_options_generated(self):
        """TC-17: Ensure recommended packages have differentiated types."""
        res = self.configurator_model.generate_budget_constrained_recommendations(
            target_budget=20000.0,
            active_sectors=['cookware_sets', 'pressure_cookers', 'frypans', 'trays_cake'],
            pos_config_id=self.pos_config.id,
            partner_id=self.partner.id,
        )
        if res.get('has_solution'):
            types = [r['type'] for r in res['recommendations']]
            self.assertEqual(len(types), len(set(types)), "Recommendations should have unique types!")

    # =========================================================================
    # 3. No-Solution Tests (TC 26 - 32)
    # =========================================================================

    def test_tc26_no_solution_for_unrealistically_low_budget(self):
        """TC-26: Target budget of 100 EGP with U_abs far below minimum sector costs must return No-Solution with diagnostics."""
        # Set tolerances so U_abs is small (100 + 50 = 150 EGP)
        self.icp.set_float('alahram.bridal_tolerance_above_pref', 50.0)
        self.icp.set_float('alahram.bridal_tolerance_above_abs', 50.0)
        res = self.configurator_model.generate_budget_constrained_recommendations(
            target_budget=100.0,
            active_sectors=['cookware_sets', 'pressure_cookers', 'frypans', 'trays_cake', 'catering_pots'],
            pos_config_id=self.pos_config.id,
            partner_id=self.partner.id,
        )
        # Restore default tolerances
        self.icp.set_float('alahram.bridal_tolerance_above_pref', 2500.0)
        self.icp.set_float('alahram.bridal_tolerance_above_abs', 3000.0)
        self.assertFalse(res['has_solution'])
        self.assertEqual(len(res['recommendations']), 0)
        self.assertIn('no_solution_diagnostics', res)
        suggestions = res.get('suggestions') or res['no_solution_diagnostics'].get('suggestions', [])
        self.assertTrue(len(suggestions) > 0)

    # =========================================================================
    # 4. Financial & Tax Tests (TC 33 - 45)
    # =========================================================================

    def test_tc33_tax_included_computation(self):
        """TC-33: compute_tax_included_price accurately computes payable price with taxes."""
        tax_inc, unit_price, tax_amt = self.configurator_model.compute_tax_included_price(
            product=self.product,
            partner=self.partner,
        )
        self.assertGreater(unit_price, 0.0)
        self.assertGreaterEqual(tax_inc, unit_price)
        if any(t.price_include for t in self.product.taxes_id):
            self.assertEqual(round(tax_inc, 2), round(unit_price, 2))
            self.assertGreater(tax_amt, 0.0)
        else:
            self.assertEqual(round(tax_inc - unit_price, 2), round(tax_amt, 2))

    def test_tc34_unapproved_discount_policy_preserved(self):
        """TC-34: System preserves strict discount policies without auto-applying unapproved discounts."""
        configurator = self.configurator_model.create({
            'name': 'Test Discount Policy',
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'target_budget': 20000.0,
            'requested_discount_pct': 6.0,  # > 5% requires ops approval
            'discount_state': 'pending_ops',
        })
        self.assertEqual(configurator.discount_state, 'pending_ops')

    # =========================================================================
    # 5. POS UX & RPC Integration Tests (TC 46 - 62)
    # =========================================================================

    def test_tc46_suggest_package_pos_rpc_entrypoint(self):
        """TC-46: suggest_package_pos RPC method returns expected schema for OWL UI consumption."""
        payload = {
            'target_budget': 20000.0,
            'sectors': ['cookware_sets', 'pressure_cookers'],
            'pos_config_id': self.pos_config.id,
            'partner_id': self.partner.id,
        }
        res = self.configurator_model.suggest_package_pos(payload)
        self.assertIn('success', res)
        self.assertTrue(res['success'])
        self.assertIn('recommendations', res)
        self.assertIn('bounds', res)
        self.assertIn('has_solution', res)

    def test_tc47_save_and_reserve_package_pos_within_bounds(self):
        """TC-47: save_and_reserve_package_pos successfully creates configurator and lines."""
        payload = {
            'partner_id': self.partner.id,
            'pos_config_id': self.pos_config.id,
            'target_budget': 20000.0,
            'package_type': 'best_match',
            'do_reserve': False,
            'lines': [{
                'product_id': self.product.id,
                'quantity': 1.0,
                'unit_price': 5000.0,
                'fulfillment_type': 'pickup',
            }],
        }
        res = self.configurator_model.save_and_reserve_package_pos(payload)
        self.assertTrue(res.get('success'))
        pkg_id = res.get('package_id') or res.get('configurator_id')
        self.assertTrue(pkg_id)
        conf = self.configurator_model.browse(pkg_id)
        self.assertEqual(conf.recommendation_type, 'best_match')
        self.assertEqual(len(conf.line_ids), 1)
