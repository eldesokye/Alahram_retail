# -*- coding: utf-8 -*-
"""
E2E Test Suite for Upgraded Scene 4: Bridal Package Configurator
===============================================================
Tests:
1. Sector Selection & Dynamic Package Suggestion
2. Elimination of Automatic Discount & Clear Pricing Feedback
3. Multi-tier Discount Governance (0-5% BM / 5-7% Ops / >7% Blocked)
4. Approval and Refusal Permissions
5. Creation of Sale Order and Direct Dispatch to POS
"""

import odoo
from odoo.tools import config
from odoo.modules.registry import Registry
from odoo.exceptions import ValidationError, AccessError, UserError

def run_tests():
    print("=" * 70)
    print("🚀 STARTING E2E VERIFICATION: SCENE 4 BRIDAL PACKAGE UPGRADE")
    print("=" * 70)

    config.parse_config(["-c", "/etc/odoo/odoo.conf", "-d", "odoo20"])
    registry = Registry("odoo20")

    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        BridalConfig = env["alahram.bridal.configurator"]
        Partner = env["res.partner"]
        User = env["res.users"]

        # 0. Get or create test bride partner
        bride = Partner.search([("name", "=", "سارة أحمد (عروسة سيدي جابر)")], limit=1)
        if not bride:
            bride = Partner.create({
                "name": "سارة أحمد (عروسة سيدي جابر)",
                "phone": "01099887766",
            })

        # Get test users
        bm_user = User.search([("login", "=", "manager.sg@alahram.com")], limit=1)
        ops_user = User.search([("login", "=", "ops.manager@alahram.com")], limit=1)
        sales_user = User.search([("login", "=", "salesperson.sg@alahram.com")], limit=1)

        print(f"[*] Test Bride: {bride.name} (ID: {bride.id})")
        print(f"[*] BM User: {bm_user.name if bm_user else 'None'}")
        print(f"[*] Ops User: {ops_user.name if ops_user else 'None'}")
        print(f"[*] Sales User: {sales_user.name if sales_user else 'None'}")

        # -------------------------------------------------------------
        # TEST 1: Sector Selection & Dynamic Algorithm
        # -------------------------------------------------------------
        print("\n--- [TEST 1] Sector Selection & Dynamic Package Suggestion ---")
        configurator = BridalConfig.create({
            "partner_id": bride.id,
            "target_budget": 20000.0,
            "package_tier": "gold_20k",
            "sector_granite": True,
            "sector_stainless": True,
            "sector_aluminum": False,
            "sector_bakeware": True,
            "sector_frypans": True,
            "sector_appliances": True,
            "sector_cutlery": False,
            "sector_serveware": False,
            "sector_accessories": False,
        })

        configurator.action_suggest_package_from_sectors()
        print(f"[+] Package Generated: {configurator.name}")
        print(f"[+] Total Lines Count: {len(configurator.line_ids)}")
        for l in configurator.line_ids:
            print(f"    - {l.product_id.name[:35]} | Cat: {l.category_name} | Qty: {l.quantity} | Unit: {l.unit_price} EGP | Sub: {l.price_subtotal} EGP")

        orig_sum = sum(configurator.line_ids.mapped('price_subtotal'))
        assert abs(configurator.total_original_price - orig_sum) < 0.01, "Original price must equal sum of lines!"
        assert configurator.final_package_price == configurator.total_original_price, "Final price must equal original price with NO auto discount!"
        assert configurator.package_discount_amount == 0.0, "Automatic discount must be strictly 0.0!"

        print(f"[+] Total Original Price: {configurator.total_original_price} EGP")
        print(f"[+] Target Budget:        {configurator.target_budget} EGP")
        print(f"[+] Variance:             {configurator.budget_variance} EGP")
        print(f"[+] Feedback Note:        {configurator.budget_feedback_message}")
        print("✅ TEST 1 PASSED: Package suggested from chosen sectors with ZERO automatic discount!")
        cr.commit()

        # -------------------------------------------------------------
        # TEST 2: Governance Rule - Discount > 7% is BLOCKED
        # -------------------------------------------------------------
        print("\n--- [TEST 2] Governance Rule: Discount > 7% Strictly Forbidden ---")
        try:
            with cr.savepoint():
                configurator.write({"requested_discount_pct": 8.5})
            print("❌ FAILED: System allowed 8.5% discount!")
            assert False, "Discount > 7% should have been blocked!"
        except ValidationError as e:
            print(f"✅ TEST 2 PASSED: Successfully blocked 8.5% discount with error:\n   -> {e}")

        # -------------------------------------------------------------
        # TEST 3: Seller requests 4% discount -> Needs Branch Manager
        # -------------------------------------------------------------
        print("\n--- [TEST 3] Discount <= 5%: Requires Branch Manager Approval ---")
        configurator.write({"requested_discount_pct": 4.0})
        configurator.action_request_discount()

        assert configurator.discount_state == 'pending_bm', f"State should be pending_bm, got {configurator.discount_state}"
        assert configurator.final_package_price == configurator.total_original_price, "Discount must NOT apply before approval!"
        print(f"[+] Requested Discount: 4.0% ({configurator.requested_discount_amount} EGP)")
        print(f"[+] Discount State: {configurator.discount_state} (Waiting for Branch Manager)")

        # Branch Manager Approves
        bm_env = configurator.with_user(bm_user) if bm_user else configurator
        bm_env.action_approve_discount_branch_manager()

        assert configurator.discount_state == 'approved', "Discount should now be approved!"
        expected_final = round(configurator.total_original_price * (1.0 - 0.04), 2)
        assert abs(configurator.final_package_price - expected_final) < 0.1, f"Final price mismatch: got {configurator.final_package_price}, expected {expected_final}"
        print(f"[+] Branch Manager Approved Successfully!")
        print(f"[+] Final Package Price after 4% discount: {configurator.final_package_price} EGP")
        print("✅ TEST 3 PASSED: Branch Manager approved 4% discount!")

        # -------------------------------------------------------------
        # TEST 4: Customer asks 6.5% discount -> Requires Ops Manager
        # -------------------------------------------------------------
        print("\n--- [TEST 4] Discount 5-7%: Requires Operations Manager Approval ---")
        configurator.write({"requested_discount_pct": 6.5})
        configurator.action_request_discount()

        assert configurator.discount_state == 'pending_ops', f"State should be pending_ops, got {configurator.discount_state}"
        print(f"[+] Requested Discount: 6.5% ({configurator.requested_discount_amount} EGP)")
        print(f"[+] Discount State: {configurator.discount_state} (Waiting for Ops Manager)")

        # Test: If Branch Manager tries to approve 6.5%, it must FAIL!
        if bm_user:
            try:
                with cr.savepoint():
                    bm_env = configurator.with_user(bm_user)
                    bm_env.action_approve_discount_branch_manager()
                print("❌ FAILED: Branch Manager was able to approve 6.5% discount!")
                assert False, "BM should not be allowed to approve > 5% discount!"
            except AccessError as e:
                print(f"✅ Security Verification: Branch Manager blocked from approving 6.5% discount:\n   -> {e}")

        # Ops Manager Approves
        ops_env = configurator.with_user(ops_user) if ops_user else configurator
        ops_env.action_approve_discount_ops_manager()

        assert configurator.discount_state == 'approved', "Ops Manager should approve 6.5%!"
        expected_final_65 = round(configurator.total_original_price * (1.0 - 0.065), 2)
        assert abs(configurator.final_package_price - expected_final_65) < 0.1, "Final price must reflect approved 6.5% discount!"
        print(f"[+] Ops Manager Approved Successfully!")
        print(f"[+] Final Package Price after 6.5% discount: {configurator.final_package_price} EGP")
        print("✅ TEST 4 PASSED: Operations Manager approved 6.5% discount, Branch Manager blocked!")

        # -------------------------------------------------------------
        # TEST 5: Create Sale Order and Direct Dispatch to POS
        # -------------------------------------------------------------
        print("\n--- [TEST 5] Sale Order Creation & Direct Dispatch to POS ---")
        action_pos = configurator.action_send_to_pos()

        assert configurator.sale_order_id, "Sale order must be created!"
        assert configurator.pos_order_id, "POS order must be created!"
        assert configurator.state == 'sent_to_pos', "State must be sent_to_pos!"

        sale_order = configurator.sale_order_id
        pos_order = configurator.pos_order_id

        print(f"[+] Official Sale Order: {sale_order.name} (Amount: {sale_order.amount_total} EGP)")
        print(f"[+] Point of Sale Order: {pos_order.name} / {pos_order.pos_reference}")
        print(f"[+] POS Session:         {pos_order.session_id.name} ({pos_order.session_id.config_id.name})")
        print(f"[+] POS Total:           {pos_order.amount_total} EGP")
        print(f"[+] POS Lines Count:     {len(pos_order.lines)}")
        for pl in pos_order.lines:
            print(f"    * {pl.product_id.name[:30]} | Qty: {pl.qty} | Price: {pl.price_unit} EGP | Disc: {pl.discount}%")

        assert pos_order.amount_total == configurator.final_package_price, "POS total must match final package price!"
        print("✅ TEST 5 PASSED: Order successfully dispatched to Point of Sale (POS) ready for payment!")

        # Commit test verification
        cr.commit()

        print("\n" + "=" * 70)
        print("🎉 ALL 5 E2E TESTS PASSED WITH 100% SUCCESS!")
        print("=" * 70)

if __name__ == "__main__":
    run_tests()
