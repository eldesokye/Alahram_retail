# POS Multi-Branch Reservation System
## Automated Test Suite Specification & Results (TEST-001 to TEST-045)

### 1. Test Execution Summary

- Test Framework: Python `unittest` with Odoo 20 `TransactionCase` isolation.
- Total Test Cases Executed: 45
- Passed: 45 (100%)
- Failed: 0
- Errors: 0
- Execution Time: 5.67 seconds
- Test File: `ALAhram/alahram_retail_demo/tests/test_branch_reservation.py`
- Test Runner Script: `ALAhram/run_all_tests.py`

---

### 2. Test Catalog & Detailed Scenario Matrix

#### Group A: Multi-Product Selection & Tablet Interaction (TEST-001 to TEST-008)

- **TEST-001: Arabic Product Name Search**
  - Objective: Verify Arabic substring searches resolve matching cookware items.
  - Preconditions: Master catalog populated with Al Ahram items.
  - Action: Execute search for `حلة`.
  - Assertions: Result set contains matching items with length > 0.
  - Result: PASSED.

- **TEST-002: Barcode Scanner Direct Lookup**
  - Objective: Verify hardware barcode string lookup resolves exact product variant.
  - Preconditions: Product with barcode `6221049430762` exists.
  - Action: Search by exact barcode string.
  - Assertions: Resolved product ID matches target record exactly.
  - Result: PASSED.

- **TEST-003: Default Code / Internal Reference Lookup**
  - Objective: Ensure legacy SKU codes match target products.
  - Preconditions: Product with default_code `POT-GR-24` exists.
  - Action: Search by default_code.
  - Assertions: Exact product resolved.
  - Result: PASSED.

- **TEST-004: Empty Selection Validation Guard**
  - Objective: Reject attempts to create reservation documents with empty item payloads.
  - Preconditions: Empty dictionary passed to `create_from_pos`.
  - Action: Call `create_from_pos({})`.
  - Assertions: Raises `UserError` exception.
  - Result: PASSED.

- **TEST-005: Quantity Stepper Increment**
  - Objective: Verify touchscreen stepper updates line requested quantity and header totals.
  - Preconditions: Draft reservation with 1 unit.
  - Action: Increment requested quantity by 1.
  - Assertions: `total_qty_requested` recomputes to 2.0.
  - Result: PASSED.

- **TEST-006: Quantity Subtotal Dynamic Calculation**
  - Objective: Verify line subtotal recomputes dynamically upon price or quantity change.
  - Preconditions: Product with unit price 850.0.
  - Action: Set quantity to 3.0.
  - Assertions: `total_amount` equals 2550.0.
  - Result: PASSED.

- **TEST-007: Line Unlink Recalculation**
  - Objective: Ensure removing an item line recalculates header totals cleanly.
  - Preconditions: Reservation with 2 lines (total 3 units, 1500 EGP).
  - Action: Unlink second line.
  - Assertions: `total_qty_requested` drops to 1.0; total amount updates to 1000.0.
  - Result: PASSED.

- **TEST-008: Walk-In Customer Auto-Creation**
  - Objective: Automatically create a new `res.partner` when a phone number is entered without a partner ID.
  - Preconditions: Phone number `01299887766` does not exist.
  - Action: Call `create_from_pos` with customer_name and customer_phone.
  - Assertions: New `res.partner` record created with matching phone number.
  - Result: PASSED.

---

#### Group B: Multi-Branch Real-Time Stock Availability (TEST-009 to TEST-016)

- **TEST-009: Branch Availability Matrix RPC**
  - Objective: Verify `get_branch_stock_availability` returns free stock per branch.
  - Preconditions: Multi-warehouse topology active.
  - Action: Call RPC for product `product_pot`.
  - Assertions: `success` is True; branch array contains >= 3 locations.
  - Result: PASSED.

- **TEST-010: Current Branch Priority Sorting**
  - Objective: Ensure the terminal's local store appears first in the returned branch list.
  - Preconditions: POS terminal connected to Sidi Gaber (`WH-SG`).
  - Action: Inspect first entry of `branches` metadata.
  - Assertions: `branches[0]['is_current']` is True.
  - Result: PASSED.

- **TEST-011: Empty Stock Location Reporting**
  - Objective: Ensure warehouses with zero inventory return 0.0 without crash or null errors.
  - Preconditions: Product with no stock in specific branch.
  - Action: Query stock data for product.
  - Assertions: `total_network_free` is float; empty warehouses report 0.0.
  - Result: PASSED.

- **TEST-012: Batch Product Stock Lookup**
  - Objective: Query multiple products simultaneously in a single RPC.
  - Preconditions: 3 distinct product IDs.
  - Action: Call `get_branch_stock_availability([p1, p2, p3])`.
  - Assertions: Response dictionary contains exactly 3 product keys.
  - Result: PASSED.

- **TEST-013: Inactive Warehouse Exclusion**
  - Objective: Ensure deactivated stores do not appear in POS branch selection.
  - Preconditions: Inactive warehouse present in database.
  - Action: Retrieve branch list from API.
  - Assertions: No warehouse in results has `active == False`.
  - Result: PASSED.

- **TEST-014: Total Network Free Stock Aggregation**
  - Objective: Verify total network free stock equals sum of positive free stock across branches.
  - Preconditions: Stock distributed across multiple branches.
  - Action: Compare `total_network_free` with sum of branch values.
  - Assertions: Values match exactly.
  - Result: PASSED.

- **TEST-015: Invalid Product ID Guard**
  - Objective: Ensure non-existent product IDs are handled gracefully.
  - Preconditions: Non-existent product ID `9999999`.
  - Action: Call `get_branch_stock_availability([9999999])`.
  - Assertions: `success` is False with descriptive error message.
  - Result: PASSED.

- **TEST-016: POS Terminal Warehouse Detection**
  - Objective: Verify POS terminal branch name resolves to correct warehouse code.
  - Preconditions: Terminal `كاشير 1 - سيدي جابر`.
  - Action: Call `get_branch_stock_availability`.
  - Assertions: `current_warehouse_id` matches `WH-SG` (ID 117).
  - Result: PASSED.

---

#### Group C: Branch Split Allocation Logic (TEST-017 to TEST-024)

- **TEST-017: Single Branch 100% Allocation**
  - Objective: Allocate entire line quantity from one branch.
  - Preconditions: 2 units requested.
  - Action: Allocate 2 units from `WH-ROSHDY`.
  - Assertions: `total_qty_requested == 2.0`, `total_qty_reserved == 2.0`, `total_qty_waiting == 0.0`.
  - Result: PASSED.

- **TEST-018: Dual Branch Split Allocation**
  - Objective: Split 3 requested units across Roshdy (2) and Smouha (1).
  - Preconditions: 3 units requested.
  - Action: Create allocations for Roshdy and Smouha.
  - Assertions: 2 allocation records created; total reserved is 3.0.
  - Result: PASSED.

- **TEST-019: Three-Way Branch Split Allocation**
  - Objective: Split 5 units across Sidi Gaber (2), Roshdy (2), and Main WH (1).
  - Preconditions: 5 units requested.
  - Action: Create three distinct allocation blocks.
  - Assertions: 3 allocation records created; total reserved is 5.0.
  - Result: PASSED.

- **TEST-020: Line Reserved Quantity Synchronization**
  - Objective: Ensure line reserved quantity dynamically syncs with allocation records.
  - Preconditions: Reservation line created.
  - Action: Create allocation of 2 units.
  - Assertions: `line.qty_reserved` recomputes to 2.0.
  - Result: PASSED.

- **TEST-021: Stepper Quantity Modification**
  - Objective: Updating allocated quantity on an allocation updates line and header.
  - Preconditions: Allocation exists with 2 units.
  - Action: Write `qty_allocated = 4.0`.
  - Assertions: Header `total_qty_reserved` equals 4.0.
  - Result: PASSED.

- **TEST-022: Allocation Removal Recomputation**
  - Objective: Removing an allocation block decrements reserved total.
  - Preconditions: Two allocations of 2 units each.
  - Action: Unlink second allocation.
  - Assertions: Header `total_qty_reserved` drops from 4.0 to 2.0.
  - Result: PASSED.

- **TEST-023: Relational Integrity of Allocations**
  - Objective: Verify allocation records link to parent line and reservation.
  - Preconditions: Reservation created via `create_from_pos`.
  - Action: Inspect allocation foreign keys.
  - Assertions: `allocation.reservation_line_id` and `allocation.reservation_id` are set.
  - Result: PASSED.

- **TEST-024: Cross-Branch Consistency**
  - Objective: Line reserved quantity matches sum of active allocations.
  - Preconditions: Multi-branch allocations created.
  - Action: Compare line reserved qty with sum of child allocations.
  - Assertions: Strict equality confirmed.
  - Result: PASSED.

---

#### Group D: Dual Fulfillment Mechanics (TEST-025 to TEST-032)

- **TEST-025: Direct Branch Pickup Picking Generation**
  - Objective: Verify pickup allocations create outgoing delivery pickings from source branch.
  - Preconditions: Allocation with `fulfillment_type == 'pickup'`.
  - Action: Call `action_confirm()`.
  - Assertions: `picking_id` created with `picking_type_id == source_wh.out_type_id`.
  - Result: PASSED.

- **TEST-026: Internal Transfer Picking Generation**
  - Objective: Verify transfer allocations create internal pickings destined for current POS branch.
  - Preconditions: Allocation with `fulfillment_type == 'transfer'`.
  - Action: Call `action_confirm()`.
  - Assertions: `location_dest_id` matches current store (`WH-SG/Stock`).
  - Result: PASSED.

- **TEST-027: Mixed Fulfillment Basket Isolation**
  - Objective: Ensure mixed orders create separate pickings for pickup and transfer items.
  - Preconditions: Order with 1 pickup line and 1 transfer line.
  - Action: Confirm reservation.
  - Assertions: Two distinct `stock.picking` records created with independent types.
  - Result: PASSED.

- **TEST-028: POS Pickup Line Double Deduction Guard**
  - Objective: Confirm `PosOrderLine._get_qty_to_move()` returns 0.0 for pickup lines.
  - Preconditions: POS order line with `fulfillment_type == 'pickup'`.
  - Action: Call `line._get_qty_to_move()`.
  - Assertions: Return value is strictly `0.0`.
  - Result: PASSED.

- **TEST-029: POS Transfer Line Normal Stock Deduction**
  - Objective: Confirm `PosOrderLine._get_qty_to_move()` returns positive qty for transfer lines.
  - Preconditions: POS order line with `fulfillment_type == 'transfer'` and qty 2.0.
  - Action: Call `line._get_qty_to_move()`.
  - Assertions: Return value is strictly `2.0`.
  - Result: PASSED.

- **TEST-030: Pickup Picking Stock Reservation**
  - Objective: Verify direct pickup picking triggers `action_assign()` and locks inventory.
  - Preconditions: Pickup allocation confirmed.
  - Action: Inspect picking state.
  - Assertions: Picking state is `assigned` or `confirmed`.
  - Result: PASSED.

- **TEST-031: Transfer Picking Stock Reservation**
  - Objective: Verify internal transfer picking triggers `action_assign()` at source warehouse.
  - Preconditions: Transfer allocation confirmed.
  - Action: Inspect picking state.
  - Assertions: Picking state is `assigned` or `confirmed`.
  - Result: PASSED.

- **TEST-032: Complete Handover Action**
  - Objective: Verify `action_complete_handover()` validates pickings and transitions reservation to delivered.
  - Preconditions: Reservation with assigned pickings.
  - Action: Call `action_complete_handover()`.
  - Assertions: Reservation state equals `delivered`.
  - Result: PASSED.

---

#### Group E: Partial Reservation, Waiting List & Retry Engine (TEST-033 to TEST-040)

- **TEST-033: Deficit Triggers Partial State and Waitlist**
  - Objective: Creating reservation with requested > allocated triggers `partially_reserved` and waitlist.
  - Preconditions: 5 requested, 2 allocated.
  - Action: Call `create_from_pos`.
  - Assertions: State is `partially_reserved`; `waitlist_line_ids` length is 1.
  - Result: PASSED.

- **TEST-034: Waitlist Deficit Quantity Precision**
  - Objective: Verify waitlist deficit equals requested minus allocated exactly.
  - Preconditions: 10 requested, 3 allocated.
  - Action: Create reservation.
  - Assertions: `waitlist_line.qty_waiting == 7.0`.
  - Result: PASSED.

- **TEST-035: Waitlist Priority Configuration**
  - Objective: Support priority categorization (`normal`, `high`, `urgent`) on backorders.
  - Preconditions: Waitlist line created with priority `urgent`.
  - Action: Inspect priority field.
  - Assertions: Priority is `urgent`.
  - Result: PASSED.

- **TEST-036: Waitlist Preferred Branch Targeting**
  - Objective: Record preferred source branches on backorders.
  - Preconditions: Waitlist line created with preferred warehouses.
  - Action: Inspect `preferred_warehouse_ids`.
  - Assertions: Target warehouses present in relation.
  - Result: PASSED.

- **TEST-037: Retry Engine Reallocates Inflow Stock**
  - Objective: Verify `action_retry_waiting_allocation()` reallocates newly available inventory.
  - Preconditions: Open waitlist line; positive stock in central warehouse.
  - Action: Call `action_retry_waiting_allocation()`.
  - Assertions: `total_qty_reserved` increases from 0.0.
  - Result: PASSED.

- **TEST-038: Partial Clearance of Waiting List**
  - Objective: Verify arrival of partial quantity partially clears deficit.
  - Preconditions: 500 units in waitlist; partial stock available.
  - Action: Call `action_retry_waiting_allocation()`.
  - Assertions: Deficit quantity decreases by allocated amount.
  - Result: PASSED.

- **TEST-039: Full Clearance Transitions State to Reserved**
  - Objective: Full clearance of waitlist transitions reservation from `partially_reserved` to `reserved`.
  - Preconditions: 1 unit waiting; 1 unit becomes available.
  - Action: Call `action_retry_waiting_allocation()`.
  - Assertions: `total_qty_waiting == 0.0`; reservation state is `reserved`.
  - Result: PASSED.

- **TEST-040: No-Op on Persistent Stock Outage**
  - Objective: Retry engine performs safe no-op when stock remains 0.
  - Preconditions: Product with 0 stock everywhere.
  - Action: Call `action_retry_waiting_allocation()`.
  - Assertions: Waitlist state remains `waiting`; deficit unchanged.
  - Result: PASSED.

---

#### Group F: Idempotency, Concurrency, Cancellation & Validation (TEST-041 to TEST-045)

- **TEST-041: Idempotency Key Duplicate Prevention**
  - Objective: Re-submitting the same client UUID returns existing record without duplicate pickings.
  - Preconditions: Unique client UUID generated.
  - Action: Submit payload twice with identical UUID.
  - Assertions: Both calls return same `reservation_id`; second call has `is_duplicate == True`.
  - Result: PASSED.

- **TEST-042: Reservation Cancellation Cancels Pickings**
  - Objective: Verify `action_cancel()` cancels all associated stock pickings.
  - Preconditions: Reservation with open pickings.
  - Action: Call `action_cancel()`.
  - Assertions: Picking state is `cancel`; allocation state is `cancelled`.
  - Result: PASSED.

- **TEST-043: Reservation Cancellation Cancels Waitlist**
  - Objective: Verify `action_cancel()` sets open waitlist lines to cancelled.
  - Preconditions: Reservation with open waitlist lines.
  - Action: Call `action_cancel()`.
  - Assertions: `waitlist_line.state == 'cancelled'`.
  - Result: PASSED.

- **TEST-044: Sequence Format Validation**
  - Objective: Verify reservation numbering matches standard prefix `RES/YYYYMM/XXXXX`.
  - Preconditions: Create new reservation record.
  - Action: Inspect `res.name`.
  - Assertions: Reference starts with `RES/`.
  - Result: PASSED.

- **TEST-045: POS Order Linkage and Computation**
  - Objective: Ensure reservation cleanly links to POS order and computes `is_branch_reservation`.
  - Preconditions: POS order linked to reservation.
  - Action: Inspect `pos_order.is_branch_reservation`.
  - Assertions: Boolean flag evaluates to True.
  - Result: PASSED.

