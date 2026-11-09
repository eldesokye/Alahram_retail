# POS Multi-Branch, Multi-Product Reservation & Stock Transfer System
## Architectural Audit & Gap Analysis Report

### 1. Executive Summary

This audit establishes the baseline architectural state of the Odoo 20 Enterprise deployment for Al Ahram Homeware / Cookware Retail. The objective is to design and implement an enterprise-grade, touchscreen-optimized Multi-Branch POS Reservation and Stock Transfer subsystem within the custom module `alahram_retail_demo`.

The audited environment consists of:
- Platform: Odoo 20.0 Enterprise (Python 3.12, PostgreSQL 16, OWL JavaScript Framework).
- Active Database: `odoo20`.
- Warehouse Topology: 15 physical and logical warehouses, including Alexandria retail network (`WH-SG` Sidi Gaber Showroom & Backroom, `WH-ROSHDY` Roshdy, `WH-SMOUHA` Smouha) and `WH-MAIN` Central Management Warehouse.
- Custom Addon: `/mnt/extra-addons/alahram_retail_demo` (mounted from `ALAhram/alahram_retail_demo`).

---

### 2. Current Architecture & Data Model Inventory

#### 2.1 Warehouse & Location Structure
The audited warehouse topology in database `odoo20`:
1. `WH-MAIN` (ID: 115, Stock Location: 719): Central Administration Warehouse.
2. `WH-LOC` (ID: 116, Stock Location: 725): Local Supply Depot.
3. `WH-SG` (ID: 117, Stock Location: 731): Sidi Gaber Showroom & Backroom (Primary retail POS branch).
4. `WH-ROSHDY` (ID: 118, Stock Location: 737): Roshdy / Loran retail branch.
5. `WH-SMOUHA` (ID: 119, Stock Location: 743): Smouha / Baccous retail branch.
6. `WH-SEKKA`, `WH-SK-ECO`, `WH-HANOVIL`, `WH-SHOBRA`, `WH-NASR`, `WH-FAISAL`, `WH-ONLINE`, `WH-SPIN`, `WH-TAG`, `WH-TAN`, `WH-RML`.
7. Inter-branch Transit Location: `loc_transit_transfer_store` (Physical Location / Transit).

#### 2.2 Point of Sale Configurations
Audited POS terminals:
- `pos_config_cashier1`: Cashier 1 Desk (Sidi Gaber, connected to `WH-SG/Stock`).
- `pos_config_cashier2`: Cashier 2 Desk (Sidi Gaber, connected to `WH-SG/Stock`).
- `pos_config_tablet_sales`: Showroom Salesperson Tablet (Sidi Gaber floor staff).

#### 2.3 Existing Cross-Branch Implementation (Scene 3 Baseline)
Scene 3 previously introduced a desktop wizard-based mechanism:
- Model `alahram.cross.branch.reserve`: Standalone cross-branch reservation document.
- Model `alahram.cross.branch.reserve.wizard`: Backend wizard for creating transfers.
- Fields on `product.template`: `qty_sidi_gaber`, `qty_roshdy`, `qty_smouha`, `qty_main_wh`.

Preservation Mandate:
The new POS-native subsystem must strictly preserve the existing Scene 3 models and views so that backend desktop operations and existing dashboards remain 100% operational with zero regression.

---

### 3. Gap Analysis & Architectural Challenges

#### 3.1 Gap 1: Point of Sale Frontend Integration
- Current State: Scene 3 reservation is only accessible via backend desktop views (`alahram_retail_demo.action_cross_branch_reserve`). POS cashiers and floor tablet salespersons cannot initiate reservations directly from the POS interface.
- Required State: A dedicated OWL component embedded in `point_of_sale.ControlButtons`, opening an intuitive, touchscreen-first modal supporting multi-product selection, barcode lookups, branch availability breakdown, quantity split allocation, and fulfillment selection.

#### 3.2 Gap 2: Multi-Product & Split Branch Allocation
- Current State: Scene 3 handles one product per reservation record.
- Required State: A customer basket containing multiple products must be reservable in a single atomic transaction. Each product can be fulfilled from one branch or split across multiple branches (e.g., 2 units from Roshdy, 1 unit from Smouha).

#### 3.3 Gap 3: Dual Fulfillment Logic (Pickup vs Transfer)
- Current State: Only 2-step internal transit transfers were modeled.
- Required State:
  - Fulfillment Option A: Direct Pickup at Source Branch (الاستلام من الفرع المصدري). The customer receives a reservation voucher to collect the item directly from Roshdy or Smouha.
  - Fulfillment Option B: Internal Stock Transfer to POS Branch (تحويل وشحن لفرع البيع الحالي). Stock moves from source warehouse via transit to Sidi Gaber.
  - Fulfillment Option C: Mixed Fulfillment within the same customer order.

#### 3.4 Gap 4: Double Stock Deduction Hazard (Odoo POS Stock Mechanics)
- Root Hazard:
  In native Odoo 20 POS, when a POS order is validated, Odoo automatically generates a delivery stock picking (`stock.picking` with `picking_type_id = pos.config.picking_type_id`) from the POS warehouse (`WH-SG/Stock`) to `Partner Locations/Customers`.
  If an order contains an item marked for Direct Pickup at Roshdy (`WH-ROSHDY`), native Odoo POS would attempt to deduct stock from `WH-SG/Stock` as well! This causes phantom negative inventory and duplicate stock reductions.
- Architectural Resolution:
  Odoo 20 provides `pos.order.line._get_qty_to_move()`. By overriding `_get_qty_to_move()` to return `0.0` for order lines fulfilled via external branch pickup, the POS delivery picking skips those lines. The stock deduction for the pickup item is exclusively handled by the dedicated reservation picking originating at `WH-ROSHDY/Stock`.

#### 3.5 Gap 5: Partial Reservations and Waiting List Engine
- Current State: Lack of formal backorder / waiting list queue when inventory across all branches is insufficient.
- Required State: The customer must never be turned away. When requested quantity exceeds total network free stock, the available quantity is reserved immediately, and the deficit is automatically queued in an active Waiting List model (`alahram.branch.waitlist.line`). A retry engine (`action_retry_waiting_allocation`) automatically matches incoming receipts against open waitlists.

---

### 4. Technical Architecture & Component Design

#### 4.1 Relational Architecture
```
+-------------------------------------------------------------------+
|                  alahram.branch.reservation                       |
| (Header: name, partner_id, pos_session_id, current_branch_id,    |
|  state, total_qty_requested, total_qty_reserved, total_waiting)   |
+---------------------------------+---------------------------------+
                                  | 1:N
        +-------------------------+-------------------------+
        | 1:N                                               | 1:N
+-------v-------------------------+       +-----------------v---------------+
|  alahram.branch.reservation.line|       |   alahram.branch.waitlist.line  |
|  (Product, Requested, Reserved, |       |   (Product, Customer, Deficit,  |
|   Waiting Deficit, Price, UoM)  |       |    Priority, Target Branches)   |
+-------+-------------------------+       +---------------------------------+
        | 1:N
+-------v-------------------------------+
| alahram.branch.reservation.allocation |
| (Source Branch, Dest Branch, Qty,     |
|  Fulfillment Type: Pickup/Transfer,   |
|  Stock Picking Link, State)           |
+---------------------------------------+
```

#### 4.2 Concurrency & Idempotency Safeguards
1. Real Stock Reservation: Reservations create real `stock.picking` records in `draft` or `confirmed` state and trigger `action_assign()` (`stock.move._action_assign()`), locking actual quants rather than using volatile virtual counters.
2. Row Locking: `SELECT FOR UPDATE` is applied on `stock.quant` and reservation lines during allocation to eliminate race conditions between multiple concurrent tablet sessions.
3. Idempotency Keys: Client-generated UUIDs are validated in `create_from_pos` to prevent duplicate reservations on flaky network connections or double touchscreen taps.

---

### 5. Implementation Roadmap

1. Implement Backend Models:
   - `alahram.branch.reservation`
   - `alahram.branch.reservation.line`
   - `alahram.branch.reservation.allocation`
   - `alahram.branch.waitlist.line`
   - Override `pos.order` and `pos.order.line` (`_get_qty_to_move`).
2. Implement Security, Sequences, and Access Rules.
3. Implement POS OWL Touchscreen Frontend:
   - Control button in POS.
   - Comprehensive multi-product, multi-branch dialog with live scanner support.
4. Build Backend Views and Management Menus.
5. Create Comprehensive Automated Test Suite (TEST-001 through TEST-045).
6. Verify and document system operation.

