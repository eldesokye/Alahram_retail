# Al Ahram Odoo 20 Enterprise - Bridal Package & Cross-Branch Architecture Audit

## 1. Executive Summary

This architecture audit analyzes the existing technical implementation of two core systems in the `alahram_retail_demo` module:
1. **The Smart Bridal Package System (`alahram.bridal.configurator`)**:
   Currently implemented as a backend configurator and wizard with sector selections, manual discount request governance, price variance tracking, and sales/POS order dispatch.
2. **The Cross-Branch Stock Availability and Reservation System (`alahram.branch.reservation`)**:
   Implemented as an atomic multi-branch reservation engine with POS OWL dialog components, real-time multi-warehouse availability lookup, internal transfer creation, customer direct pickup handling, and deficit waitlisting.

The primary engineering goal is to seamlessly integrate the Bridal Package experience directly into Odoo 20 POS for touchscreen tablets, completely reusing the existing cross-branch availability and reservation engine without creating redundant models or conflicting inventory logic.

---

## 2. Technical Audit of Existing Bridal Package Addon

- **Technical Addon Name**: `alahram_retail_demo`
- **Main Model**: `alahram.bridal.configurator`
- **Line Model**: `alahram.bridal.configurator.line`
- **Wizard Model**: `alahram.bridal.package.wizard`
- **Current Location**: `ALAhram/alahram_retail_demo/models/alahram_bridal_configurator.py`
- **Current POS Integration Status**:
  - The model currently contains an action `action_send_to_pos` which creates a backend `pos.order` draft and links it to an open POS session.
  - However, there is no direct, native, touch-friendly POS OWL interface on the tablet allowing salespeople to configure, customize, check stock across branches, substitute products, or request discounts inside the active POS session.

### Main Model Fields and Logic
- **Header (`alahram.bridal.configurator`)**:
  - `name`: Sequence `BRIDAL-XXXX`.
  - `partner_id`: Customer / Bride (`res.partner`).
  - `target_budget`: Target financial budget.
  - `package_tier`: Selection (`silver_15k`, `gold_20k`, `platinum_30k`, `royal_45k`, `custom`).
  - **Sectors (9 Booleans)**:
    - `sector_granite`: Granite cookware.
    - `sector_stainless`: Stainless steel 18/10.
    - `sector_aluminum`: Classic aluminum.
    - `sector_bakeware`: Oven trays and bakeware.
    - `sector_frypans`: Frying pans, crepe pans, grills.
    - `sector_appliances`: Small electric appliances and blenders.
    - `sector_cutlery`: Cutlery, knives, kitchen scissors.
    - `sector_serveware`: Serving trays, tea and coffee sets.
    - `sector_accessories`: Silicone tools and kitchen accessories.
  - **Financial & Discount Governance**:
    - `total_original_price`: Sum of line prices before discounts.
    - `budget_variance`: Variance between original price and target budget.
    - `budget_feedback_message`: Feedback notification regarding budget matching.
    - `requested_discount_pct`: Discretionary discount percentage requested by seller.
    - `requested_discount_amount`: Computed currency amount of requested discount.
    - `discount_state`: Selection (`no_discount`, `pending_bm`, `pending_ops`, `approved`, `refused`).
    - `discount_approver_id`: Manager who approved/refused (`res.users`).
    - `discount_approval_date`: Timestamp of approval.
    - `package_discount_amount`: Approved discount amount in EGP.
    - `final_package_price`: Net price to charge customer.
    - `state`: Selection (`draft`, `calculated`, `order_created`, `sent_to_pos`).
  - **Constraints**:
    - `@api.constrains('requested_discount_pct')`: Hard ceiling of 7.0%. Any discount greater than 7.0% triggers `ValidationError`. Negative discounts are blocked.

### Lines (`alahram.bridal.configurator.line`)
- `configurator_id`: Many2one reference.
- `product_id`: Product variant (`product.product`).
- `product_barcode`: Barcode.
- `category_name`: Family category name.
- `quantity`: Quantity requested.
- `unit_price`: Unit list price.
- `price_subtotal`: Subtotal in EGP.

---

## 3. Technical Audit of Existing Cross-Branch Availability & Reservation System

- **Technical Addon Name**: `alahram_retail_demo`
- **Main Models**:
  - `alahram.branch.reservation`: Header tracking multi-branch reservation.
  - `alahram.branch.reservation.line`: Requested product lines.
  - `alahram.branch.reservation.allocation`: Per-branch allocations linked to real `stock.picking`.
  - `alahram.branch.waitlist.line`: Deficit waiting list.
- **Current Location**: `ALAhram/alahram_retail_demo/models/branch_reservation.py`
- **POS OWL Components**:
  - `BranchReservationDialog`: Dialog component in `static/src/app/branch_reservation/branch_reservation_dialog.js`.
  - `control_buttons_patch.js` / `control_buttons_patch.xml`: UI entry buttons in Navbar, Burger Menu, Actionpad, and ControlButtons.

### Key Service Methods to Reuse
1. `get_branch_stock_availability(product_ids, pos_config_id)`:
   - Takes list of product IDs and POS configuration ID.
   - Calculates on-hand and free-to-use quantities across all 15 company warehouses (prioritizing current selling branch, then `WH-SG`, `WH-ROSHDY`, `WH-SMOUHA`, `WH-MAIN`).
   - Returns structured JSON containing branch metadata and per-product stock balances.
2. `create_from_pos(reservation_vals)`:
   - Atomic backend entry point accepting JSON reservation payload.
   - Idempotency protection via `idempotency_key`.
   - Automatically determines fulfillment types (`transfer` for internal transit to selling branch, `pickup` for customer collection at source warehouse).
   - Automatically generates, confirms, and reserves real Odoo `stock.picking` records (`stock.move`).
   - Records deficits into `alahram.branch.waitlist.line`.
3. `action_confirm()`: Validates and assigns stock pickings.
4. `action_cancel()`: Reverses/cancels open pickings, releases reserved inventory.
5. `action_retry_waiting_allocation()`: Re-checks incoming stock for waitlisted quantities.

---

## 4. Integration Gap Analysis

| Requirement | Existing State in Addon | Gap / Required Enhancement |
| :--- | :--- | :--- |
| **POS Touchscreen Entry** | Only "حجز وتوافر الفروع" dialog exists in POS. | Add "باكدج العروسة الذكي" entry button in POS Navbar, Actionpad, and Control Buttons. |
| **POS Bridal Package Dialog** | Bridal configurator is only a backend form view (`alahram.bridal.configurator`). | Build dedicated POS OWL Component (`BridalPackageDialog`) for touchscreen tablets. |
| **Sector & Category Selection** | Backend booleans exist on model. | Provide touch-friendly Sector cards and Category browsing in the POS dialog. |
| **Real Product Selection** | Hardcoded heuristics in backend method. | Allow live searching, filtering, and variant selection from real Odoo catalog. |
| **Alternative Products Engine** | Not implemented in bridal configurator. | Provide automatic similar/alternative product suggestions when stock is zero. |
| **Multi-Branch Stock Lookup** | Implemented in `branch_reservation.py`. | Call `get_branch_stock_availability` directly for all selected package lines. |
| **Reservation Execution** | Handled by `branch_reservation.py`. | Connect package lines to `create_from_pos` without duplicating stock logic. |
| **Line-Level Sourcing & Status** | Lines in configurator lack fulfillment status. | Add sourcing method (`local`, `transfer`, `pickup`, `waitlist`) and status to lines. |
| **Direct Delivery Option** | `branch_reservation` has `transfer` and `pickup`. | Add `direct_delivery` fulfillment type linked to customer delivery picking. |
| **Package Discount Governance** | Implemented in backend model methods. | Add RPC endpoints for POS to submit discount requests and manager PIN/session approval. |
| **POS Order Integration** | Backend creates standalone draft `pos.order`. | Add capability to load confirmed package items and approved discounts directly into active POS cart. |

---

## 5. Architectural Design Principles

1. **Zero Redundancy**:
   `alahram.bridal.configurator` will directly store references to `alahram.branch.reservation` records. It will never create independent stock move tables or duplicate availability algorithms.
2. **Strict Concurrency and Idempotency**:
   All reservation calls from the POS tablet will generate and pass an idempotency key combining package reference and timestamp to prevent duplicate transfers.
3. **Multi-Tier Discount Enforcement**:
   - 0.0%: No approval needed.
   - 0.01% - 5.0%: Branch Manager approval.
   - 5.01% - 7.0%: Operations Manager approval.
   - > 7.0%: Enforced failure at backend level.
   - Invalidation: Any change in line items or price base automatically resets approval state.
4. **Offline and Stale Data Prevention**:
   Availability displayed on the tablet is treated as advisory. When the salesperson clicks "Reserve" or "Confirm", backend transaction boundaries lock and re-validate real stock balances before issuing pickings.

