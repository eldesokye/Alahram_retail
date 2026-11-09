# -*- coding: utf-8 -*-
"""
Al Ahram Cookware — End-to-End Five Scenes & AI Engine Comprehensive Verification Test Suite
"""
import sys

def run_tests(env):
    results = {}
    print("=" * 70)
    print("🚀 STARTING AL AHRAM 5 SCENES & AI ENGINE FULL VERIFICATION SUITE")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. TEST SCENE 11 SEED & SMART STOCK TRANSFER RECOMMENDATIONS
    # -------------------------------------------------------------
    print("\n[SCENE 11] Testing Smart Stock Transfer Recommendations...")
    RecModel = env['alahram.stock.recommendation']
    RecModel.action_seed_demo_recommendations()
    recs = RecModel.search([('state', '=', 'pending')])
    print(f"  -> Found {len(recs)} active pending recommendations:")
    for r in recs:
        print(f"     * [{r.name}] {r.product_id.name} | أولوية: {r.priority} | كمية مقترحة: {r.suggested_qty} | رصيد راكد: {r.dead_stock_qty}")
    assert len(recs) >= 3, "Expected at least 3 seeded recommendations!"

    # Approve one recommendation to verify stock.picking creation
    test_rec = recs[0]
    app_res = test_rec.action_approve_recommendation()
    assert test_rec.state == 'approved', "Recommendation state should be 'approved'!"
    assert test_rec.picking_id, "Recommendation must have linked stock.picking!"
    print(f"  ✅ [PASS] Approved recommendation {test_rec.name} -> Created real Picking: {test_rec.picking_id.name} (State: {test_rec.picking_id.state})")
    results['Scene 11'] = f"PASSED ({len(recs)} recommendations, Picking: {test_rec.picking_id.name})"

    # -------------------------------------------------------------
    # 2. TEST SCENE 3: BRANCH AVAILABILITY & BACKROOM PULL & RESERVATION
    # -------------------------------------------------------------
    print("\n[SCENE 3] Testing Branch Availability & Backroom Pull...")
    ProdTmpl = env['product.template']
    p_backroom = ProdTmpl.search([('barcode', '=', '6221049430762')], limit=1)
    if not p_backroom:
        p_backroom = ProdTmpl.search([('default_code', '=', '6221049430762')], limit=1)
    assert p_backroom, "Product 6221049430762 must exist in catalog!"

    pull_res = p_backroom.action_pull_from_backroom()
    pull_picking = env['stock.picking'].browse(pull_res['res_id'])
    assert pull_picking.exists(), "Backroom pull picking must be created!"
    print(f"  ✅ [PASS] Backroom Pull (6221049430762): Created Picking {pull_picking.name} from {pull_picking.location_id.name} to {pull_picking.location_dest_id.name}")

    # Cross Branch Reservation (6221049011701)
    p_cross = env['product.product'].search([('barcode', '=', '6221049011701')], limit=1)
    wh_roshdy = env['stock.warehouse'].search([('code', '=', 'WH-ROSHDY')], limit=1) or env['stock.warehouse'].search([], limit=1)
    wh_sg = env['stock.warehouse'].search([('code', '=', 'WH-SG')], limit=1) or env['stock.warehouse'].search([], limit=1)
    reserve = env['alahram.cross.branch.reserve'].create({
        'product_id': p_cross.id if p_cross else p_backroom.product_variant_id.id,
        'quantity': 2.0,
        'src_warehouse_id': wh_roshdy.id,
        'dest_warehouse_id': wh_sg.id,
    })
    reserve.action_confirm_reservation()
    reserve.action_ship_to_transit()
    assert reserve.state == 'shipped', "Reservation should be in shipped state!"
    assert reserve.picking_out_id, "Reservation must have linked transit picking out!"
    print(f"  ✅ [PASS] Cross-Branch Reservation: Created 2-step transit transfer {reserve.name} -> Picking: {reserve.picking_out_id.name}")
    results['Scene 3'] = f"PASSED (Pull Picking: {pull_picking.name}, Transit Picking: {reserve.picking_out_id.name})"

    # -------------------------------------------------------------
    # 3. TEST SCENE 4: SMART BRIDAL PACKAGE CONFIGURATOR
    # -------------------------------------------------------------
    print("\n[SCENE 4] Testing Bridal Package Configurator (15,000 EGP Scenario)...")
    customer = env['res.partner'].search([('customer_rank', '>', 0)], limit=1) or env['res.partner'].search([], limit=1)
    bridal = env['alahram.bridal.configurator'].create({
        'partner_id': customer.id,
        'target_budget': 15000.0,
        'package_tier': 'silver_15k',
    })
    bridal.action_auto_generate_balanced_package()
    print(f"  -> Generated lines: {len(bridal.line_ids)}")
    print(f"  -> Original Total: {bridal.total_original_price:,.2f} EGP")
    print(f"  -> Package Discount: {bridal.package_discount_amount:,.2f} EGP")
    print(f"  -> Final Price: {bridal.final_package_price:,.2f} EGP")
    assert len(bridal.line_ids) >= 4, "Expected at least 4 lines across categories!"
    assert abs(bridal.final_package_price - 15000.0) <= 2000.0, "Final price must be within budget tolerance!"

    so_res = bridal.action_create_sale_order()
    sale_order = bridal.sale_order_id
    assert sale_order.exists(), "Real sale.order must be created!"
    print(f"  ✅ [PASS] Created Real Sale Order: {sale_order.name} with {len(sale_order.order_line)} lines. Total: {sale_order.amount_total:,.2f} EGP")
    results['Scene 4'] = f"PASSED (Sale Order: {sale_order.name}, Amount: {sale_order.amount_total:,.2f} EGP)"

    # -------------------------------------------------------------
    # 4. TEST SCENE 6: POS DISCOUNT APPROVAL DASHBOARD
    # -------------------------------------------------------------
    print("\n[SCENE 6] Testing POS Discount Approvals...")
    pos_config = env['pos.config'].search([], limit=1)
    pos_session = env['pos.session'].search([('config_id', '=', pos_config.id)], limit=1)
    
    # Test Auto-approval <= 5%
    test_prod = env['product.product'].search([('sale_ok', '=', True)], limit=1)
    pos_order_3pct = env['pos.order'].create({
        'session_id': pos_session.id if pos_session else 1,
        'partner_id': customer.id,
        'amount_tax': 0.0,
        'amount_total': 970.0,
        'amount_paid': 0.0,
        'amount_return': 0.0,
        'lines': [(0, 0, {
            'product_id': test_prod.id,
            'qty': 1,
            'price_unit': 1000.0,
            'discount': 3.0,
            'price_subtotal': 970.0,
            'price_subtotal_incl': 970.0,
        })],
    })
    assert pos_order_3pct.discount_approval_status == 'auto_approved', "Discount <= 5% must be auto_approved!"
    print(f"  ✅ [PASS] 3% Discount: State is '{pos_order_3pct.discount_approval_status}'")

    # Test Pending & Branch Manager Approval > 5%
    pos_order_7pct = env['pos.order'].create({
        'session_id': pos_session.id if pos_session else 1,
        'partner_id': customer.id,
        'amount_tax': 0.0,
        'amount_total': 930.0,
        'amount_paid': 0.0,
        'amount_return': 0.0,
        'lines': [(0, 0, {
            'product_id': test_prod.id,
            'qty': 1,
            'price_unit': 1000.0,
            'discount': 7.0,
            'price_subtotal': 930.0,
            'price_subtotal_incl': 930.0,
        })],
    })
    assert pos_order_7pct.discount_approval_status == 'pending', "Discount > 5% must be pending!"
    print(f"  ✅ [PASS] 7% Discount: State is '{pos_order_7pct.discount_approval_status}'")

    # Manager approves
    pos_order_7pct.action_approve_special_discount()
    assert pos_order_7pct.discount_approval_status == 'approved', "Discount must transition to 'approved'!"
    assert pos_order_7pct.discount_approver_id, "Approver must be recorded!"
    print(f"  ✅ [PASS] Manager Approval: Order {pos_order_7pct.name} approved by {pos_order_7pct.discount_approver_id.name}")
    results['Scene 6'] = f"PASSED (3% Auto-approved, 7% Manager approved)"

    # -------------------------------------------------------------
    # 5. TEST SCENE 13: AI EXECUTIVE ASSISTANT (ALL 6 QUESTIONS)
    # -------------------------------------------------------------
    print("\n[SCENE 13] Testing AI Executive Assistant (All 6 Business Questions)...")
    assistant = env['alahram.ai.assistant'].create({
        'name': 'اختبار التحقق الشامل لمساعد الذكاء الاصطناعي',
        'customer_id': customer.id,
        'target_budget': 15000.0,
    })

    for q_idx in range(1, 7):
        getattr(assistant, f"action_run_q{q_idx}")()
        assert assistant.ai_response_html, f"Question {q_idx} must produce HTML response!"
        assert assistant.action_executed_summary, f"Question {q_idx} must produce summary!"
        print(f"  ✅ [PASS] Question {q_idx}: {assistant.action_executed_summary[:80]}...")
    
    assert assistant.generated_sale_order_id, "Question 6 must have generated a Sale Order!"
    print(f"  ✅ [PASS] Question 6 generated real Sales Order: {assistant.generated_sale_order_id.name}")
    results['Scene 13'] = f"PASSED (All 6 Executive Questions verified, SO: {assistant.generated_sale_order_id.name})"

    # -------------------------------------------------------------
    # 6. TEST CHATBOT SERVICE INTENTS & DISCUSS ENGINE
    # -------------------------------------------------------------
    print("\n[AI CHATBOT ENGINE] Testing Chatbot Intents & Discuss Auto-responder Fallback...")
    Chatbot = env['alahram.chatbot.service']

    test_queries = [
        ("Top 5 sales reps by revenue", "أحمد محمود"),
        ("Show sales by product category this month", "أطقم حلل وتجهيز عرائس"),
        ("Display the profit margins by product category", "هامش الربح"),
        ("Show me the current cash flow status", "4,820,500"),
        ("say to me what the best product in alahram company", "Bio Trade Grip"),
        ("تجهيز باكج العروسه بسعر 15000", "15,000"),
        ("إيه أقل 5 فروع في المبيعات لشهر أكتوبر؟", "مخزن الإدارة"),
        ("أريد قائمة المنتجات المتاحة والأسعار", "الأهرام"),
    ]

    for query, expected_snippet in test_queries:
        # Test local deterministic database RAG engine
        text_fb, html_fb = Chatbot._fallback_database_rag(query)
        assert expected_snippet in html_fb or expected_snippet in text_fb, f"Expected '{expected_snippet}' in fallback for query: '{query}'"

        # Test ask_ai end-to-end Discuss/Webchat pipeline
        res = Chatbot.ask_ai(question=query, channel='discuss')
        assert res and res.get('status') == 'success', f"Query failed for: {query}"
        html_body = res.get('html', '')
        
        # Verify no demo products leaked
        for demo_food in ['Apple Pie', 'Bagel', 'Acoustic Bloc Screens']:
            assert demo_food not in html_body, f"Forbidden demo item '{demo_food}' found in response!"
        print(f"  ✅ [PASS] Query: '{query[:40]}...' -> Verified RAG Engine & Discuss pipeline (0 demo items leaked)")

    results['AI Chatbot'] = f"PASSED (All {len(test_queries)} intent queries verified, 0 demo items leaked)"

    print("\n" + "=" * 70)
    print("🎉 ALL 5 SCENES & AI ENGINE FULLY VERIFIED WITH 100% SUCCESS RATE!")
    print("=" * 70)
    for k, v in results.items():
        print(f"  - {k}: {v}")
    return results

if __name__ == '__main__':
    import os
    import odoo
    from odoo.modules.registry import Registry
    from odoo import api, SUPERUSER_ID

    db_name = os.environ.get('TARGET_DB', 'Demo2')
    conf_path = os.environ.get('ODOO_RC', '/etc/odoo/odoo.conf')
    odoo.tools.config.parse_config(['-c', conf_path, '-d', db_name])
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        run_tests(env)
        cr.rollback()
