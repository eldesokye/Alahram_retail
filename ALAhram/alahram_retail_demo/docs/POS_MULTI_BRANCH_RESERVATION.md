# POS Multi-Branch, Multi-Product Reservation & Stock Transfer System
## Technical Specification & Operational Manual

### 1. Architectural Overview

The Multi-Branch POS Reservation and Stock Transfer Subsystem provides an integrated, real-time inventory reservation and inter-branch fulfillment engine within Odoo 20 Enterprise Point of Sale. It enables showroom sales staff and cashiers to look up live network-wide stock across all retail branches and central warehouses, allocate customer orders from multiple source locations, execute split fulfillments, and automatically queue shortages into an active waiting list.

The subsystem operates directly inside the Point of Sale touchscreen interface using Odoo 20 OWL components and communicates with the backend via atomic, concurrency-safe RPC transactions.

---

### 2. Core Functional Requirements

1. **Multi-Product Selection**:
   - Cashiers or showroom salespersons can select multiple products within a single reservation session.
   - Real-time product search supports Arabic and English name substrings, barcode scanner inputs, and internal reference codes.
   - Responsive quantity steppers allow touch-friendly adjustments on mobile tablets.

2. **Network-Wide Live Stock Availability**:
   - Queries real-time on-hand and free-to-use quantities across all 15 warehouses and retail stores (Sidi Gaber, Roshdy, Smouha, Main Warehouse, etc.).
   - Visual branch availability badges dynamically indicate stock levels at each location.
   - The current branch POS terminal warehouse is automatically detected and placed first in the availability matrix.

3. **Per-Product Branch Split Allocation**:
   - Orders can be fulfilled from a single branch or split across multiple locations (e.g., 2 units from Roshdy and 1 unit from Smouha).
   - An intelligent auto-allocation algorithm greedily pre-allocates requested items from locations with verified positive free stock.
   - Steppers allow cashiers to customize branch quantities or add additional branches on the fly.

4. **Dual Fulfillment Modes**:
   - **Fulfillment Option A (Direct Branch Pickup - استلام مباشر من الفرع المصدري)**:
     The customer collects goods directly at the source warehouse. The system generates an outgoing delivery picking (`out_type_id`) at the source warehouse reserved specifically for the customer.
   - **Fulfillment Option B (Internal Transfer to Current Branch - شحن وتحويل لفرع البيع)**:
     Goods are transferred from the source branch warehouse to the current POS branch showroom (`WH-SG/Stock`). The system creates an internal transfer picking (`int_type_id`).
   - **Mixed Fulfillment**:
     Items within the same order can use different fulfillment methods simultaneously.

5. **Double Stock Deduction Prevention**:
   - In native Odoo POS, validating a POS order triggers a delivery move from the current branch warehouse (`WH-SG/Stock`).
   - For items marked as **Direct Branch Pickup**, deducting inventory at Sidi Gaber would cause duplicate stock reduction.
   - Resolution: `PosOrderLine._get_qty_to_move()` is overridden to return `0.0` for pickup lines. The inventory deduction is exclusively managed by the source branch picking (`WH-ROSHDY/Stock` -> `Customer`).
   - For transfer lines, `_get_qty_to_move()` returns standard positive quantity, allowing the current store inventory to be reduced once the incoming transfer is received.

6. **Partial Reservation & Automatic Waiting List Engine**:
   - When requested quantities exceed network-wide free stock, the system never turns the customer away.
   - Available quantities are reserved immediately, and the remaining deficit is automatically queued in `alahram.branch.waitlist.line`.
   - The reservation document assumes state `partially_reserved`.
   - The retry engine (`action_retry_waiting_allocation`) continuously matches newly received stock from supplier receipts or customer returns against open waitlist lines.

---

### 3. Backend Data Models

#### 3.1 `alahram.branch.reservation` (Header)
- `name`: Unique reference string (`RES/YYYYMM/00001`).
- `partner_id`: Customer partner reference (`res.partner`).
- `customer_name`: Walk-in customer name.
- `customer_phone`: Customer phone number for SMS and delivery tracking.
- `pos_order_id`: Linked POS order (`pos.order`).
- `pos_session_id`: Originating POS session (`pos.session`).
- `pos_config_id`: Originating POS terminal (`pos.config`).
- `salesperson_id`: Responsible salesperson or cashier (`res.users`).
- `current_branch_id`: Originating store warehouse (`stock.warehouse`).
- `state`: Status workflow: `draft` -> `reserved` / `partially_reserved` -> `transferred` -> `delivered` / `cancelled`.
- `date_reservation`: Datetime of creation.
- `line_ids`: Requested items (`alahram.branch.reservation.line`).
- `allocation_ids`: Branch fulfillments (`alahram.branch.reservation.allocation`).
- `waitlist_line_ids`: Deficit backorders (`alahram.branch.waitlist.line`).
- `picking_ids`: Associated stock pickings (`stock.picking`).
- `idempotency_key`: Client-generated UUID preventing duplicate creation.
- `total_qty_requested`, `total_qty_reserved`, `total_qty_waiting`, `total_amount`.

#### 3.2 `alahram.branch.reservation.line`
- `reservation_id`: Parent reservation reference.
- `product_id`: Storable product record (`product.product`).
- `qty_requested`: Requested quantity.
- `qty_reserved`: Total allocated across active branch allocations.
- `qty_waiting`: Remaining deficit queued in waiting list.
- `price_unit`: Base unit sale price.
- `price_subtotal`: Computed subtotal (`qty_requested * price_unit`).
- `allocation_ids`: Detailed allocations per source branch.
- `waitlist_line_ids`: Linked waitlist lines.

#### 3.3 `alahram.branch.reservation.allocation`
- `reservation_id`: Parent reservation reference.
- `reservation_line_id`: Line reference.
- `product_id`: Product reference.
- `source_warehouse_id`: Warehouse fulfilling the quantity (`stock.warehouse`).
- `destination_warehouse_id`: Destination warehouse (current branch for transfers, customer for pickup).
- `fulfillment_type`: `pickup` (Direct Branch Pickup) or `transfer` (Internal Stock Transfer).
- `qty_allocated`: Quantity assigned to this fulfillment.
- `state`: `draft`, `reserved`, `transit`, `received`, `handed_over`, `cancelled`.
- `picking_id`: Concrete Odoo `stock.picking` record.

#### 3.4 `alahram.branch.waitlist.line`
- `reservation_id`: Parent reservation reference.
- `reservation_line_id`: Line reference.
- `product_id`: Product in deficit.
- `partner_id`: Customer awaiting stock.
- `qty_waiting`: Unfulfilled deficit quantity.
- `preferred_warehouse_ids`: Priority warehouses for fulfillment.
- `priority`: `normal`, `high`, `urgent`.
- `state`: `waiting`, `allocated`, `cancelled`.
- `date_added`: Datetime of backorder registration.
- `notification_notes`: Operational notes for cashier and inventory managers.

---

### 4. POS Frontend Touchscreen Integration

1. **Control Button Extension**:
   - The button `حجز وتوافر الفروع` is injected into `point_of_sale.ControlButtons`.
   - On desktop and tablet, it is permanently displayed on the action bar next to partner selection.
   - It is also accessible within the `More Actions` popup dialog.

2. **Interactive Dialog (`BranchReservationDialog`)**:
   - Customer Information Bar: Captures name, phone number, and a toggle to automatically insert reserved lines into the active POS cart.
   - Real-time Product Search & Scanner: Instant search with debounced typing and integrated hardware barcode listener (`barcode_reader` service).
   - Branch Allocation Matrix: Visual breakdown of stock across branches with increment/decrement steppers for intuitive quantity assignment.
   - Live Fulfillment Dropdowns: Select between Direct Pickup and Internal Transfer per allocation block.
   - Dynamic Deficit & Summary Counter: Visual badge indicating waiting list deficit before confirming the transaction.

---

### 5. Standard Operating Procedures (SOP)

#### 5.1 Cashier Reservation Workflow
1. In the POS screen, tap `حجز وتوافر الفروع`.
2. Enter the customer's phone number and name (or select an existing customer).
3. Scan product barcodes or search for cookware items by name.
4. Review branch stock availability in Alexandria and central depots.
5. Choose source branches and fulfillment methods (Direct Pickup or Internal Transfer).
6. Tap `تأكيد الحجز وتخصيص الفروع`.
7. The system creates the reservation, locks real inventory via stock moves, and adds the items to the customer POS cart.

#### 5.2 Warehouse Handover Workflow
1. For pickup orders: When the customer visits the source branch (e.g., Roshdy), the store clerk opens `Point of Sale > حجوزات الفروع`.
2. Search by customer phone or reservation reference.
3. Validate the customer identity and tap `تسليم للعميل`.
4. The system automatically validates the delivery picking and updates state to `delivered`.

