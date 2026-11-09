# Al Ahram Retail POS - Bridal Package Budget Recommendation Business Rules

Document Reference: [BRIDAL_BUDGET_RECOMMENDATION_BUSINESS_RULES.md](file:///d:/WORK/Odoo20-interbrise/docs/BRIDAL_BUDGET_RECOMMENDATION_BUSINESS_RULES.md)
Module: [alahram_retail_demo](file:///d:/WORK/Odoo20-interbrise/ALAhram/alahram_retail_demo)
Platform: Odoo 20 Enterprise

---

## 1. Executive Summary and Problem Statement

### 1.1 Background
Al Ahram Home and Cookware is an Egyptian retail leader specializing in premium cookware sets (Granite, Stainless Steel 18/10, Classic Aluminum), pressure cookers, bakeware, frypans, and home accessories. The Bridal Package Builder is one of the core sales tools used on Point of Sale (POS) tablets across Al Ahram branches (including Sidi Gaber, Roshdy, and Smouha).

### 1.2 Identified Problem
Prior to this enhancement, when a bride or family entered a target budget (e.g. 20,000 EGP), the POS package builder would assemble combinations totaling 35,000 to 70,000 EGP—often more than double or triple the customer's stated budget. This resulted in:
1. Significant customer sticker shock and lost retail sales.
2. Salespeople having to manually dismantle and reassemble packages item by item.
3. Inaccurate inventory forecasts and abandoned reservations.

### 1.3 Business Objective
Enforce strict budget governance where recommended bridal packages strictly align with declared customer purchasing capacity, using mathematical combinatorial optimization bounded by administrative tolerances.

---

## 2. Core Business Rules and Mathematical Formulation

### 2.1 Target Budget Variable Definition
Let:
- $B$ denote the customer's declared target budget in Egyptian Pounds (EGP).
- $T_{below}$ denote the allowable tolerance below target budget (Default: 2,000.00 EGP).
- $T_{pref}$ denote the preferred upper tolerance above target budget (Default: 2,500.00 EGP).
- $T_{abs}$ denote the absolute upper tolerance above target budget (Default: 3,000.00 EGP).

### 2.2 Boundary Formulas
1. **Lower Bound ($L$)**:
   $$L = \max(0, B - T_{below})$$
2. **Preferred Upper Bound ($U_{pref}$)**:
   $$U_{pref} = B + T_{pref}$$
3. **Absolute Upper Bound ($U_{abs}$)**:
   $$U_{abs} = B + T_{abs}$$

### 2.3 Mathematical Invariants and Administrative Constraints
1. **Non-negativity**: $T_{below} \ge 0, T_{pref} \ge 0, T_{abs} \ge 0$.
2. **Monotonicity**: $U_{abs} \ge U_{pref} \ge B \ge L \ge 0$.
3. **Primary Acceptance Range**: $[L, U_{pref}]$. Any combination whose tax-inclusive payable total price $P$ falls within $[L, U_{pref}]$ is an acceptable primary recommendation.
4. **Extended Acceptance Range**: $(U_{pref}, U_{abs}]$. Combinations falling in this range are only presented if no primary solution exists and the administrator has enabled extended recommendations.
5. **Rejection Boundary**: Any package with $P > U_{abs}$ or $P < L$ is rejected and must never be presented as an automatic recommendation.

---

## 3. Recommendation Packages and Classification

The engine produces up to three differentiated recommendation options to empower customer decision-making:

### 3.1 Option A: Economy Package (`economy`)
- **Intent**: Provides the highest savings while fulfilling all mandatory customer sectors.
- **Price Target**: Strictly below target budget ($P \le B$) or as close to the lower bound as possible.
- **Selection Criteria**: Selects high-value, durable products (such as Al Ahram Classic Aluminum or essential Granite sets) that minimize total investment without sacrificing quality.

### 3.2 Option B: Best Budget Match (`best_match`)
- **Intent**: The primary recommendation that maximizes alignment with the customer's declared budget.
- **Optimization Objective**: Minimizes absolute budget variance:
  $$\min | P - B | \quad \text{subject to } L \le P \le U_{pref}$$
- **Selection Criteria**: Balanced mix of premium cookware and essential kitchenware closest to target budget. In case of ties, local branch availability is prioritized.

### 3.3 Option C: Premium Package (`premium`)
- **Intent**: Upselling tier within safe financial boundaries.
- **Price Target**: Higher price tier up to the preferred upper bound ($B \le P \le U_{pref}$).
- **Selection Criteria**: Upgrades core pieces (e.g., Signature 18/10 Stainless Steel, Master Granite with induction bases) while remaining within the customer's comfort range.

### 3.4 Extended Option (`extended`)
- **Condition**: Only generated when zero combinations exist in $[L, U_{pref}]$, but valid combinations exist in $(U_{pref}, U_{abs}]$.
- **User Notice**: Clearly labeled with an advisory badge indicating it is slightly above preferred budget.

---

## 4. No-Solution Diagnostics and Exception Handling

When customer sector selections cannot be satisfied within $[L, U_{abs}]$ (e.g. budget is 1,000 EGP but customer requested Granite Set, Stainless Set, and Pressure Cooker), the system:
1. Sets `has_solution = False`.
2. Generates an informative diagnostic explanation detailing:
   - Sum of the absolute cheapest items across selected sectors ($\sum \min(S_i)$).
   - The exact financial deficit ($D = \sum \min(S_i) - U_{abs}$).
3. Delivers actionable suggestions:
   - Unchecking non-essential sectors (e.g. appliances or cutlery).
   - Increasing the budget to meet the required minimum.

---

## 5. Financial, Tax, and Discount Governance

1. **Tax Inclusive Pricing**: All pricing displayed to the customer and evaluated by the recommendation engine includes Egypt's native 14% Value Added Tax (VAT) using Odoo's native `taxes_id.compute_all()`.
2. **Zero Automatic Phantom Discounts**: The recommendation engine is strictly forbidden from applying unapproved discounts to artificially force-fit a package into budget.
3. **Discount Approval Policy**:
   - 0.00% to 5.00%: Requires Branch Manager authorization (PIN or login).
   - 5.01% to 7.00%: Strictly requires Operations Manager authorization.
   - Over 7.00%: Prohibited by system validation constraints.

---

## 6. Sourcing and Multi-Branch Stock Coordination

Recommendations evaluate inventory across the entire Al Ahram branch network:
- **Local Branch Available**: Stock available at the POS register's physical warehouse (immediate fulfillment).
- **Remote Branch Available**: Stock available at other branches (automated internal transfer created via [alahram.branch.reservation](file:///d:/WORK/Odoo20-interbrise/ALAhram/alahram_retail_demo/models/alahram_branch_reservation.py)).
- **Waitlisted**: Production backorder created with factory tracking.
