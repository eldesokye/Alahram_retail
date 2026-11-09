# POS Multi-Branch Reservation System
## System Administration & Operations Guide

### 1. Introduction

This guide provides operational and configuration instructions for System Administrators, ERP Managers, and Branch Supervisors responsible for maintaining the Multi-Branch POS Reservation and Stock Transfer subsystem in Odoo 20 Enterprise.

---

### 2. Configuration & Prerequisites

#### 2.1 Warehouse Setup
Ensure that every physical store in the Al Ahram network has a configured warehouse record (`stock.warehouse`):
- Alexandria Branches:
  - `WH-SG`: Sidi Gaber Showroom & Backroom (Primary retail branch).
  - `WH-ROSHDY`: Roshdy / Loran retail store.
  - `WH-SMOUHA`: Smouha / Baccous retail store.
- Central Depot:
  - `WH-MAIN`: Central Administration & Logistics Warehouse.
- Operation Types:
  - Internal Transfer (`int_type_id`): Required for executing inter-branch transfers (Option B).
  - Delivery Orders (`out_type_id`): Required for direct customer pickups at the source branch (Option A).
- Transit Location:
  - Ensure the internal transit location `Transfer Store (بضاعة بالطريق)` (`usage == 'transit'`) is active and accessible.

#### 2.2 Point of Sale Terminal Setup
1. Navigate to `Point of Sale > Configuration > Settings`.
2. Select the relevant POS terminal (e.g., `كاشير 1 - سيدي جابر`).
3. Verify that the terminal is linked to its physical store warehouse.
4. If a terminal name contains the Arabic branch name (e.g., `سيدي جابر`), the system automatically resolves the corresponding warehouse.
5. In POS settings, ensure `Inventory Management` is active so that real stock quants are tracked.

---

### 3. User Roles and Security Groups

| Role | Access Level | Responsibilities |
| :--- | :--- | :--- |
| Showroom Salesperson | Read & Create | Search products, inspect branch availability, create draft reservations |
| Cashier | Full POS Access | Finalize reservations, add items to POS cart, collect payments |
| Branch Manager | Management Access | Review branch reservations, approve transfers, reallocate stock |
| Inventory Controller | Warehouse Full | Validate transfer receipts, dispatch branch delivery pickings |

Access permissions are enforced through standard Odoo security records in `security/ir.access.csv`.

---

### 4. Operational Maintenance & Routine Tasks

#### 4.1 Monitoring Open Reservations
1. Navigate to `Point of Sale > حجوزات الفروع` (or `مركز العمليات > حجوزات وتوافر الفروع`).
2. Filter by status:
   - `Partially Reserved (حجز جزئي)`: Orders awaiting complete stock allocation.
   - `In Transit (قيد التحويل)`: Items currently moving through transit between warehouses.
   - `Reserved (محجوز بالكامل)`: Items ready for customer collection.
3. Open any reservation record to inspect linked pickings, destination branches, and tracking notes.

#### 4.2 Processing the Waiting List (Backorders)
When requested quantities exceed network inventory, items are automatically placed in `قائمة انتظار العجز المخزني`:
1. Navigate to `Point of Sale > قائمة انتظار العجز المخزني`.
2. Inspect entries filtered by status `Waiting for Stock (بانتظار رصيد)`.
3. To trigger automatic reallocation after receiving a purchase order at `WH-MAIN`:
   - Open the reservation form and click `إعادة فحص قائمة الانتظار`.
   - The retry engine scans free stock across candidate warehouses, allocates available quantities, updates pickings, and decrements the waiting list deficit.

#### 4.3 Handling Order Handover & Delivery
1. When a customer arrives to collect a Direct Pickup order at `WH-ROSHDY`:
   - Open the reservation in Odoo backend.
   - Click `تسليم للعميل (Complete Handover)`.
   - The system automatically marks associated pickings as done and updates the reservation state to `Delivered (تم التسليم)`.

#### 4.4 Handling Cancellations
1. If a customer cancels an unfulfilled reservation:
   - Open the reservation form and click `إلغاء الحجز (Cancel Reservation)`.
   - The system immediately cancels all associated draft or assigned stock pickings, releases locked inventory quants, and sets waitlist lines to `Cancelled`.

---

### 5. Troubleshooting & FAQ

#### Q1: A cashier reports that a branch is missing from the availability matrix.
- Ensure the warehouse record in `Inventory > Configuration > Warehouses` has `active = True`.
- Inactive warehouses are automatically excluded from the API response.

#### Q2: Direct pickup items are not showing on the POS cashier receipt picking.
- This is by design. Overriding `_get_qty_to_move()` prevents POS cashiers from deducting stock for items that the customer picks up at another branch. The stock reduction is handled exclusively by the source branch outgoing picking.

#### Q3: How to test the subsystem on a fresh database?
- Execute the standalone automated test harness:
  ```bash
  docker exec odoo20_enterprise_app python3 /mnt/ALAhram/run_all_tests.py
  ```
- All 45 unit and integration tests will execute in isolated transactions and report results in standard format.

