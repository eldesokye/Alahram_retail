# Al Ahram Retail POS - Bridal Package Budget Recommendation User Guide

Document Reference: [BRIDAL_BUDGET_RECOMMENDATION_USER_GUIDE.md](file:///d:/WORK/Odoo20-interbrise/docs/BRIDAL_BUDGET_RECOMMENDATION_USER_GUIDE.md)
Module: [alahram_retail_demo](file:///d:/WORK/Odoo20-interbrise/ALAhram/alahram_retail_demo)
Platform: Odoo 20 Enterprise

---

## 1. Introduction

The Al Ahram Smart Bridal Package Builder is designed to help retail salespeople configure, price, and reserve complete cookware packages for brides in accordance with declared customer budgets.

This guide provides operational workflows for Salespeople, Branch Managers, and System Administrators.

---

## 2. Salesperson Workflow (POS Tablet)

### 2.1 Opening the Bridal Package Dialog
1. In the active POS session (e.g., Sidi Gaber branch), tap the **Bridal Package Builder** button on the action bar.
2. The modal dialog opens, displaying the customer selection, target budget input, cookware sectors, and summary panel.

### 2.2 Entering Customer Information and Target Budget
1. Select the bride / customer from the dropdown list.
2. Enter the customer's declared budget in the **Target Budget (EGP)** field (e.g., `20,000`).
3. Observe the dynamic budget indicators in the summary widget:
   - Target Budget: `20,000.00 EGP`
   - Lower Bound: `18,000.00 EGP` (-2,000 tolerance)
   - Preferred Upper Bound: `22,500.00 EGP` (+2,500 tolerance)
   - Absolute Upper Bound: `23,000.00 EGP` (+3,000 tolerance)

### 2.3 Selecting Cookware Sectors and Suggesting Packages
1. Toggle the required sectors:
   - Cookware Sets (Granite, Stainless Steel, Aluminum)
   - Bakeware & Oven Trays
   - Frypans & Grills
   - Cutlery & Tableware
   - Kitchen Appliances & Accessories
2. Tap **Suggest Smart Package**.
3. The recommendation engine executes in real time and presents up to three distinct cards:
   - **Economy Package**: Focused on savings below or near budget.
   - **Best Match Package**: The optimal combination closest to the target budget.
   - **Premium Package**: Enhanced cookware sets within preferred tolerance.
4. Tap any card to review its items, pricing breakdown, and branch stock locations.

### 2.4 Handling No-Solution Scenarios
If the declared budget is too low to satisfy all selected sectors:
1. An alert banner appears detailing why no combination could be formed.
2. Read the diagnostic breakdown showing the minimum possible cost for the selected sectors.
3. Apply the suggestions:
   - Uncheck non-essential sectors.
   - Or increase the declared budget to match the minimum requirement.

### 2.5 Reserving the Package
1. Review the stock badges for each line item (Local Available, Remote Transfer, Waitlist).
2. Tap **Save & Reserve Package**.
3. Internal stock allocations and delivery reservations are confirmed automatically across branches.

---

## 3. Branch Manager Workflow

### 3.1 Reviewing Packages in Backend Dashboard
1. Navigate to: **Point of Sale > Al Ahram Retail > Bridal Packages**.
2. Open any package to view:
   - Budget Match Status badge (Matches Budget, Within Preferred, Slightly Above Preferred, Out of Bounds).
   - Recommendation Type (Economy, Best Match, Premium, Extended, Custom).
   - Tax amount (14% VAT) and Tax Included Total.
   - Administrative bounds (Lower, Preferred, Absolute).

### 3.2 Authorizing Discounts
1. If a salesperson requests a discount:
   - **0% to 5%**: Branch Manager enters PIN or clicks **Approve Discount**.
   - **5.01% to 7%**: Status changes to **Pending Operations Manager Approval**.
   - **Above 7%**: Prohibited by company policy.

---

## 4. System Administrator Workflow

### 4.1 Configuring Budget Tolerances
1. Navigate to: **Point of Sale > Settings > Al Ahram Bridal Budget Recommendation Tolerances**.
2. Or use the menu shortcut: **Point of Sale > Configuration > Bridal Budget Tolerances**.
3. Configure the parameters:
   - **Lower Budget Tolerance (EGP)**: Default `2,000.00`
   - **Preferred Upper Tolerance (EGP)**: Default `2,500.00`
   - **Absolute Upper Tolerance (EGP)**: Default `3,000.00`
   - **Max Recommended Packages**: Default `3`
   - **Enable Extended Range**: Default `True`
   - **Consider Cross-Branch Stock**: Default `True`
4. Click **Save**. All active POS tablets adopt the updated parameters immediately without restart.
