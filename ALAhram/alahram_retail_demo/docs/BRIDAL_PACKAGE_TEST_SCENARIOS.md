# Test Scenarios & Quality Assurance: Al Ahram POS Bridal Package

## Test Execution Matrix

This document provides test scenarios covering all business requirements, validation gates, mathematical bounds, and cross-branch fulfillment flows implemented in [test_bridal_package_pos.py](file:///d:/WORK/Odoo20-interbrise/ALAhram/alahram_retail_demo/tests/test_bridal_package_pos.py).

---

## 1. Automated Test Cases in TestBridalPackagePOS

| Test ID | Test Name | Focus Area | Expected Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **TEST-01** | `test_01_target_budget_constraints` | Target budget input | Positive float required, negative budget raises ValidationError | Passed |
| **TEST-02** | `test_02_package_tier_onchange_sets_budget` | Tier selection | Tier change updates budget according to predefined price points | Passed |
| **TEST-03** | `test_03_zero_automatic_discount_rule` | Al Ahram Discount Policy | Automatic discounts default to 0.0% | Passed |
| **TEST-04** | `test_04_get_pos_bridal_init_data` | POS Initialization | Loads warehouses, categories, tolerance rules, and active session | Passed |
| **TEST-05** | `test_05_suggest_package_pos` | Recommendation Engine | Recommends items within declared budget tolerance limits | Passed |
| **TEST-06** | `test_06_get_product_alternatives_pos` | Smart Substitutions | Retrieves compatible products from the same sector/family | Passed |
| **TEST-07** | `test_07_discount_greater_than_7_pct_strictly_forbidden` | Discount Ceiling Governance | Discounts > 7% raise ValidationError even for administrators | Passed |
| **TEST-08** | `test_08_negative_discount_forbidden` | Negative Discount Validation | Negative discount percentages raise ValidationError | Passed |
| **TEST-09** | `test_09_discount_under_5_pct_requires_branch_manager` | 0-5% Approval Tier | Requires Branch Manager group authorization | Passed |
| **TEST-10** | `test_10_branch_manager_blocked_from_approving_over_5_pct` | 5.01-7% Approval Tier | Branch manager blocked; Operations Manager required | Passed |
| **TEST-11** | `test_11_discount_refusal_restores_original_price` | Refusal Governance | Refusal clears discount amount and resets price | Passed |
| **TEST-12** | `test_12_save_and_reserve_package_pos_local_stock` | Local Branch Reservation | Creates reservation without circular transfer moves | Passed |
| **TEST-13** | `test_13_save_and_reserve_package_pos_remote_transfer` | Inter-branch Transit | Generates internal transfer picking from remote warehouse | Passed |
| **TEST-14** | `test_14_save_and_reserve_package_pos_source_pickup` | Source Branch Pickup | Sets fulfillment to pickup and generates customer delivery picking | Passed |
| **TEST-15** | `test_15_split_sourcing_across_multiple_branches` | Split Allocation | Splits requested quantity into separate allocation lines per branch | Passed |
| **TEST-16** | `test_16_insufficient_stock_creates_waitlist_deficit` | Stock Shortfall Handling | Unallocated deficit automatically enters waiting list | Passed |
| **TEST-17** | `test_17_load_to_pos_cart_blocked_when_discount_pending` | Workflow B Guard | Blocks POS cart injection if requested discount is unapproved | Passed |
| **TEST-18** | `test_18_load_to_pos_cart_success_when_approved` | Workflow B Approval | Injects items into cart with approved discount percentage | Passed |
| **TEST-19** | `test_19_action_cancel_package_and_reservation` | Cancellation Consistency | Cancelling package automatically cancels associated reservation | Passed |
| **TEST-20** | `test_20_idempotency_prevents_duplicate_package_creation` | Network Idempotency | Duplicate idempotency key returns existing record without duplicate writes | Passed |
| **TEST-21** | `test_21_walkin_customer_auto_resolves_partner` | Walk-in Robustness | Phone/name inputs auto-resolve or create partner without throwing UserError | Passed |
| **TEST-22** | `test_22_save_and_subsequent_branch_reservation_link` | Workflow A 2-Step Integration | Package saved with do_reserve=False, then linked via create_from_pos | Passed |
| **TEST-23** | `test_23_budget_variance_and_shortfall_calculation` | Budget Math Verification | Validates exact reporting of shortfall below minimum bound and target variance | Passed |

---

## 2. Manual Cashier E2E Verification Scenarios

### Scenario A: Full Bridal Package Cross-Branch Reservation (Workflow A)
1. **Initial State**: Cashier opens POS session at Sidi Gaber branch (`WH-SG`).
2. **Action**: Cashier clicks "باكج العروسة الذكي" on the POS screen.
3. **Configuration**:
   - Customer Name: "سارة محمود"
   - Customer Phone: "01012345678"
   - Target Budget: 20,000 EGP
   - Selected sectors: Granite, Stainless, Frypans.
4. **Package Generation**: Clicks "اقتراح الباكدج بالذكاء الاصطناعي". System populates 4 cookware items totaling 19,500 EGP.
5. **Execution**: Clicks "تأكيد الباكج وحجز المخزون بالفروع".
6. **Expected Results**:
   - Package is saved with status `calculated`.
   - `BridalPackageDialog` closes.
   - `BranchReservationDialog` opens with the banner: "باكدج العروسة المرتبط: ..."
   - Items are pre-populated with stock levels across Sidi Gaber, Smouha, Roshdy.
   - Cashier confirms reservation. Stock pickings are created in Odoo inventory.
   - Bridal package state updates to `reserved`.

### Scenario B: Immediate POS Checkout (Workflow B)
1. **Initial State**: Customer selects items in store and wants immediate checkout.
2. **Action**: Cashier opens "باكج العروسة الذكي", selects items and applies 0% discount (or manager-approved 5% discount).
3. **Execution**: Cashier clicks "تحويل الأصناف إلى سلة الـ POS للدفع الفوري".
4. **Expected Results**:
   - No cross-branch stock reservation picking is created.
   - Active POS cart lines are populated with exact items, variants, quantities, and discount.
   - Dialog closes cleanly.
   - Cashier proceeds to Payment screen and confirms invoice/receipt.

### Scenario C: Budget Variance Reporting (Mathematical Accuracy)
1. **Action**: Target budget set to 20,000 EGP. Minimum bound is 18,000 EGP. Cashier removes an item, bringing total to 17,350 EGP.
2. **Expected Results**:
   - Status badge displays "خارج حدود الميزانية".
   - Feedback message explicitly displays:
     "السعر الإجمالي (17,350.00 ج.م) أقل من الحد الأدنى المقبول للميزانية (18,000.00 ج.م) بمقدار 650.00 ج.م (وفارق 2,650.00 ج.م عن الميزانية المستهدفة)."
   - Confirms zero discrepancy between the minimum bound shortfall (650 EGP) and the declared budget variance (2,650 EGP).
