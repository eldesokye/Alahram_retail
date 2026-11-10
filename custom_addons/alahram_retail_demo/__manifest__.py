# -*- coding: utf-8 -*-
{
    'name': 'شركة الأهرام للأدوات المنزلية (Al Ahram Cookware E2E Retail & AI Demo)',
    'version': '20.0.1.0.0',
    'category': 'Point of Sale / Retail',
    'summary': 'End-to-End Retail, Multi-Warehouse, Dual POS, Automated Accounting & AI Demo for Al Ahram Cookware',
    'description': """
شركة الأهرام للأدوات المنزلية — Al Ahram Cookware
=================================================
Complete production-grade E2E Retail, Multi-Warehouse, POS, Anglo-Saxon Perpetual Accounting and AI-Powered ERP System for Odoo 20 Enterprise.

Key Capabilities:
-----------------
1. Central Warehouse Purchasing, Receipt & Putaway rules.
2. 15 Real Warehouses + Sidi Gaber Showroom & Backroom Bin Location Hierarchy.
3. Showroom Salesperson Tablet pushing orders directly to Dual POS Cashiers.
4. Cashier <= 5% auto-discount vs > 5% Branch Manager Approval workflow.
5. 1-Click Cross-Branch Stock Reservation & 2-Step Transit Transfer.
6. Smart Bridal Package (تجهيز العرائس) & AI Budget Sales Order Generator.
7. Odoo 20 Enterprise AI Executive & Sales Assistant answering the 6 meeting business queries.
8. Real October 2026 Store & Item sales analytics dataset.
    """,
    'author': 'Antigravity AI / Al Ahram Cookware ERP Implementation Team',
    'website': 'https://alahramcookware.com',
    'license': 'OEEL-1',
    'depends': [
        'base',
        'web',
        'mail',
        'product',
        'stock',
        'purchase',
        'sale_management',
        'point_of_sale',
        'pos_sale',
        'account',
    ],
    'data': [
        'security/alahram_security.xml',
        'security/ir.access.csv',
        'data/01_company_and_tax_14vat.xml',
        'data/branch_reservation_sequence.xml',
        'data/02_warehouses_and_bins.xml',
        'data/03_users_and_roles.xml',
        'data/04_products_master_data.xml',
        'data/05_pos_configs_and_pricelists.xml',
        'data/06_october_historical_analytics.xml',
        'views/ai_assistant_views.xml',
        'views/branch_manager_dashboard.xml',
        'views/owner_bi_reports.xml',
        'views/pos_views.xml',
        'views/product_views.xml',
        'wizards/bridal_package_wizard_views.xml',
        'wizards/cross_branch_reserve_wizard_views.xml',
        'views/chatbot_views.xml',
        'views/stock_recommendation_views.xml',
        'views/branch_reservation_views.xml',
        'views/res_config_settings_views.xml',
        'views/executive_dashboard_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'alahram_retail_demo/static/src/app/**/*',
        ],
        'web.assets_backend': [
            'alahram_retail_demo/static/src/dashboard/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
