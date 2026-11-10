# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class AlahramExecutiveDashboard(models.TransientModel):
    _name = 'alahram.executive.dashboard'
    _description = 'لوحة التحكم والتحليلات التنفيذية للأهرام'

    @api.model
    def get_dashboard_data(self, filters=None):
        """
        Aggregate executive KPIs dynamically from REAL Odoo database tables:
        - alahram.branch.analytics (10 branches sales, profits, cogs, returns)
        - pos.order & pos.order.line (live retail transactions)
        - stock.quant & stock.warehouse (real inventory stock and valuation)
        - account.move & account.move.line (posted financial accounting)
        - product.template & product.product (product catalog, dead stock)
        - alahram.stock.recommendation (inter-branch replenishment alerts)
        """
        filters = filters or {}
        selected_branch = filters.get('branch_code')  # e.g. 'WH-SG' or None for all
        selected_wh_id = filters.get('warehouse_id')
        if selected_wh_id:
            try:
                selected_wh_id = int(selected_wh_id)
            except (ValueError, TypeError):
                selected_wh_id = None

        company_id = self.env.company.id

        # ---------------------------------------------------------
        # 1. BRANCH ANALYTICS (October 2026 Baseline & Live)
        # ---------------------------------------------------------
        analytics_domain = []
        if selected_branch:
            analytics_domain.append(('warehouse_code', '=', selected_branch))

        analytics_records = self.env['alahram.branch.analytics'].search(analytics_domain, order='net_sales_inc_vat desc')
        
        branch_rows = []
        for rec in analytics_records:
            gross = float(rec.gross_sales or 0.0)
            disc = float(rec.discount_given or 0.0)
            net_inc = float(rec.net_sales_inc_vat or 0.0)
            net_exc = float(rec.net_sales_exc_vat or 0.0)
            cogs = float(rec.cogs_cost or 0.0)
            profit = float(rec.net_profit or 0.0)
            ret_val = float(rec.return_value or 0.0)
            ret_rate = float(rec.return_rate or 0.0)
            
            disc_pct = (disc / gross * 100.0) if gross > 0 else 0.0
            margin_pct = (profit / net_exc * 100.0) if net_exc > 0 else 0.0

            badge = 'normal'
            if ret_rate > 20.0:
                badge = 'high_return'
            elif rec.warehouse_code == 'WH-SG':
                badge = 'top'

            branch_rows.append({
                'id': rec.id,
                'name': rec.branch_name,
                'code': rec.warehouse_code or '',
                'net_sold_qty': rec.net_sold_qty or 0,
                'gross_sales': round(gross, 2),
                'discount_given': round(disc, 2),
                'discount_pct': round(disc_pct, 1),
                'vat_14': round(float(rec.vat_14_amount or 0.0), 2),
                'return_qty': rec.return_qty or 0,
                'return_value': round(ret_val, 2),
                'return_rate': round(ret_rate, 2),
                'net_sales_inc_vat': round(net_inc, 2),
                'net_sales_exc_vat': round(net_exc, 2),
                'cogs': round(cogs, 2),
                'profit': round(profit, 2),
                'margin_pct': round(margin_pct, 1),
                'target_status': 'غير محدد (Not Configured)',
                'badge': badge,
            })

        # Aggregated totals
        total_gross = sum(b['gross_sales'] for b in branch_rows)
        total_discount = sum(b['discount_given'] for b in branch_rows)
        total_vat = sum(b['vat_14'] for b in branch_rows)
        total_return_val = sum(b['return_value'] for b in branch_rows)
        total_return_qty = sum(b['return_qty'] for b in branch_rows)
        total_net_inc = sum(b['net_sales_inc_vat'] for b in branch_rows)
        total_net_exc = sum(b['net_sales_exc_vat'] for b in branch_rows)
        total_cogs = sum(b['cogs'] for b in branch_rows)
        total_profit = sum(b['profit'] for b in branch_rows)

        overall_margin_pct = (total_profit / total_net_exc * 100.0) if total_net_exc > 0 else 0.0
        overall_disc_pct = (total_discount / total_gross * 100.0) if total_gross > 0 else 0.0
        overall_return_rate = (abs(total_return_val) / (total_gross or 1.0) * 100.0) if total_gross > 0 else 0.0

        # Best / Lowest branches
        top_branch = branch_rows[0] if branch_rows else None
        lowest_branch = branch_rows[-1] if branch_rows else None

        # ---------------------------------------------------------
        # 2. LIVE POS ORDERS & AOV
        # ---------------------------------------------------------
        pos_domain = [('state', 'in', ['paid', 'done', 'invoiced'])]
        if selected_branch == 'WH-SG':
            pos_domain.append(('config_id.name', 'ilike', 'سيدي جابر'))
        
        pos_orders = self.env['pos.order'].search(pos_domain)
        pos_orders_count = len(pos_orders)
        pos_sales_total = sum(pos_orders.mapped('amount_total'))
        pos_tax_total = sum(pos_orders.mapped('amount_tax'))
        aov = (pos_sales_total / pos_orders_count) if pos_orders_count > 0 else 0.0

        # ---------------------------------------------------------
        # 3. OPERATING EXPENSES (Posted Accounting Entries)
        # ---------------------------------------------------------
        expense_lines = self.env['account.move.line'].search([
            ('move_id.state', '=', 'posted'),
            ('account_id.account_type', '=', 'expense'),
            ('company_id', '=', company_id)
        ], order='date desc')

        total_expenses = sum(expense_lines.mapped('debit')) - sum(expense_lines.mapped('credit'))
        total_expenses = max(0.0, total_expenses)

        expense_items = []
        for l in expense_lines[:15]:
            expense_items.append({
                'id': l.id,
                'move_id': l.move_id.id,
                'move_name': l.move_id.name or 'قيد محاسبي',
                'date': str(l.date or ''),
                'partner_name': l.partner_id.name or 'مصروف عام',
                'account_name': l.account_id.name or 'مصروفات',
                'description': l.name or l.move_id.ref or '',
                'debit': round(l.debit, 2),
                'credit': round(l.credit, 2),
                'amount': round(l.debit - l.credit, 2),
            })

        expense_to_sales_pct = (total_expenses / total_net_exc * 100.0) if total_net_exc > 0 else 0.0
        branch_contribution = total_profit - total_expenses

        # ---------------------------------------------------------
        # 4. INVENTORY VALUATION & WAREHOUSE INTELLIGENCE
        # ---------------------------------------------------------
        wh_domain = [('company_id', '=', company_id)]
        if selected_wh_id:
            wh_domain.append(('id', '=', selected_wh_id))
        elif selected_branch:
            wh_domain.append(('code', '=', selected_branch))

        warehouses = self.env['stock.warehouse'].search(wh_domain, order='name')

        warehouse_breakdown = []
        total_stock_qty = 0.0
        total_stock_reserved = 0.0
        total_stock_valuation = 0.0

        for wh in warehouses:
            quants = self.env['stock.quant'].search([
                ('location_id.usage', '=', 'internal'),
                ('location_id.warehouse_id', '=', wh.id),
                ('quantity', '>', 0)
            ])
            
            wh_qty = sum(quants.mapped('quantity'))
            wh_reserved = sum(quants.mapped('reserved_quantity'))
            wh_products = len(set(quants.mapped('product_id.id')))
            
            # Calculate cost valuation
            wh_val = 0.0
            for q in quants:
                cost = q.product_id.standard_price or (q.product_id.list_price * 0.7)
                wh_val += (q.quantity * cost)

            if wh_qty > 0 or wh.code in ['WH-MAIN', 'WH-SG', 'WH-ROSHDY']:
                warehouse_breakdown.append({
                    'id': wh.id,
                    'name': wh.name,
                    'code': wh.code or '',
                    'products_count': wh_products,
                    'on_hand_qty': round(wh_qty, 0),
                    'reserved_qty': round(wh_reserved, 0),
                    'available_qty': round(wh_qty - wh_reserved, 0),
                    'valuation': round(wh_val, 2),
                })
                total_stock_qty += wh_qty
                total_stock_reserved += wh_reserved
                total_stock_valuation += wh_val

        warehouse_breakdown.sort(key=lambda x: x['valuation'], reverse=True)

        # Dead Stock
        dead_stock_products = self.env['product.template'].search([('is_dead_stock', '=', True)], order='list_price desc')
        dead_stock_items = []
        dead_stock_value = 0.0
        dead_stock_qty = 0.0

        for pt in dead_stock_products:
            p_quants = self.env['stock.quant'].search([
                ('product_id.product_tmpl_id', '=', pt.id),
                ('location_id.usage', '=', 'internal')
            ])
            qty = sum(p_quants.mapped('quantity'))
            unit_cost = pt.product_variant_id.standard_price or (pt.list_price * 0.7)
            val = qty * unit_cost

            dead_stock_value += val
            dead_stock_qty += qty

            dead_stock_items.append({
                'id': pt.id,
                'name': pt.name,
                'code': pt.default_code or pt.barcode or 'بدون كود',
                'list_price': round(pt.list_price, 2),
                'unit_cost': round(unit_cost, 2),
                'qty': round(qty, 0),
                'total_val': round(val, 2),
                'recommendation': 'تسييل عبر باكدجات العرائس وتخفيضات 25%'
            })

        # Stock recommendations
        rec_domain = []
        if selected_branch:
            rec_domain.append('|')
            rec_domain.append(('src_warehouse_id.code', '=', selected_branch))
            rec_domain.append(('dest_warehouse_id.code', '=', selected_branch))

        recommendations = self.env['alahram.stock.recommendation'].search(rec_domain, order='priority_score desc, id desc', limit=8)
        recommendation_rows = []
        for r in recommendations:
            recommendation_rows.append({
                'id': r.id,
                'name': r.name,
                'product_name': r.product_id.display_name,
                'src_warehouse': r.src_warehouse_id.name or 'مخزن غير محدد',
                'dest_warehouse': r.dest_warehouse_id.name or 'صالة العرض',
                'suggested_qty': r.suggested_qty or 0,
                'dead_stock_cost': round(float(r.dead_stock_cost or 0.0), 2),
                'priority': r.priority or 'medium',
                'state': r.state or 'draft',
                'reason': r.reason or '',
            })

        # ---------------------------------------------------------
        # 5. STRATEGIC BUSINESS ALERTS (Red / Amber / Green)
        # ---------------------------------------------------------
        alerts = []
        
        # High Returns Alert (Red)
        high_return_branches = [b for b in branch_rows if b['return_rate'] > 20.0]
        if high_return_branches:
            names = '، '.join(f"{b['name']} ({b['return_rate']}%)" for b in high_return_branches)
            alerts.append({
                'type': 'danger',
                'title': '🚨 نسبة مرتجعات مرتفعة تتجاوز الحدود الآمنة (> 20%)',
                'description': f"تم رصد ارتفاع غير طبيعي في نسب المرتجعات في الفروع التالية: {names}. يتطلب تدقيق جودة المنتجات أو أسباب استرجاع العملاء فوراً.",
                'action_model': 'alahram.branch.analytics',
                'action_label': 'فحص تقرير المرتجعات',
            })

        # Dead Stock Capital Lockup (Amber)
        if dead_stock_value > 0:
            alerts.append({
                'type': 'warning',
                'title': '⚠️ رأس مال مجمد في بضاعة راكدة (Dead Stock)',
                'description': f"يوجد عدد {len(dead_stock_items)} أصناف راكدة بعدد {int(dead_stock_qty):,} قطعة بإجمالي تكلفة {dead_stock_value:,.2f} ج.م بدون مبيعات في الفترة الأخيرة. التوصية: إدراجها ضمن باكدجات العروسة المخفضة.",
                'action_model': 'product.template',
                'action_domain': "[('is_dead_stock', '=', True)]",
                'action_label': 'عرض الأصناف الراكدة',
            })

        # Excessive Discounts (Amber)
        high_discount_branches = [b for b in branch_rows if b['discount_given'] > 300000.0]
        if high_discount_branches:
            names = '، '.join(f"{b['name']} ({b['discount_given']:,.0f} ج.م)" for b in high_discount_branches)
            alerts.append({
                'type': 'warning',
                'title': '🏷️ إجمالي خصومات ممنوحة مرتفع',
                'description': f"بلغت الخصومات الممنوحة في {names} مستويات تتطلب تفعيل صلاحيات اعتماد الخصومات فوق 5% من مدير الفرع لضبط هوامش الربحية.",
                'action_model': 'pos.order',
                'action_label': 'مراجعة طلبات الخصم',
            })

        # Top Sales Star (Green)
        if top_branch:
            alerts.append({
                'type': 'success',
                'title': '🌟 أعلى الفروع أداءً ومبيعات',
                'description': f"يتصدر {top_branch['name']} المبيعات بإجمالي {top_branch['net_sales_inc_vat']:,.2f} ج.م وصافي ربح {top_branch['profit']:,.2f} ج.م مع نسبة مرتجعات منضبطة ({top_branch['return_rate']}%).",
                'action_model': 'alahram.branch.analytics',
                'action_res_id': top_branch['id'],
                'action_label': 'بيان أداء الفرع',
            })

        # Inter-branch transfer recommendations (Actionable)
        if recommendation_rows:
            alerts.append({
                'type': 'info',
                'title': '🔄 توصيات ذكية لنقل وتدوير المخزون بين الفروع',
                'description': f"تم توليد عدد {len(recommendation_rows)} توصية نقل عاجلة لتغطية نواقص صالات العرض من مخزن الإدارة والفروع القريبة لمنع ضياع المبيعات.",
                'action_model': 'alahram.stock.recommendation',
                'action_label': 'مراجعة واعتماد التوصيات',
            })

        # Target Configuration Note
        alerts.append({
            'type': 'secondary',
            'title': 'ℹ️ حالة المستهدفات البيعية (Sales Targets)',
            'description': 'لم يتم تحديد مستهدفات مبيعات شهرية مسبقة للفروع في إعدادات النظام الحالية. يتم احتساب الأداء استناداً إلى المبيعات الفعلية والتكلفة وهوامش الربح.',
            'action_model': False,
            'action_label': '',
        })

        # ---------------------------------------------------------
        # 6. FILTERS METADATA
        # ---------------------------------------------------------
        all_warehouses = self.env['stock.warehouse'].search([('company_id', '=', company_id)], order='name')
        warehouse_options = [{'id': w.id, 'name': w.name, 'code': w.code} for w in all_warehouses]
        
        all_branches = self.env['alahram.branch.analytics'].search([], order='net_sales_inc_vat desc')
        branch_options = [{'code': b.warehouse_code, 'name': b.branch_name} for b in all_branches if b.warehouse_code]

        return {
            'overview': {
                'gross_sales': round(total_gross, 2),
                'discount_given': round(total_discount, 2),
                'discount_pct': round(overall_disc_pct, 1),
                'vat_14': round(total_vat, 2),
                'return_value': round(total_return_val, 2),
                'return_qty': total_return_qty,
                'return_rate_pct': round(overall_return_rate, 2),
                'net_sales_inc_vat': round(total_net_inc, 2),
                'net_sales_exc_vat': round(total_net_exc, 2),
                'cogs': round(total_cogs, 2),
                'gross_profit': round(total_profit, 2),
                'gross_margin_pct': round(overall_margin_pct, 1),
                'operating_expenses': round(total_expenses, 2),
                'branch_contribution': round(branch_contribution, 2),
                'expense_to_sales_pct': round(expense_to_sales_pct, 2),
                'target_achievement': {
                    'is_configured': False,
                    'label': 'غير محدد في النظام',
                    'note': 'Not Configured'
                },
                'inventory_valuation': round(total_stock_valuation, 2),
                'total_stock_qty': round(total_stock_qty, 0),
                'dead_stock_value': round(dead_stock_value, 2),
                'dead_stock_qty': round(dead_stock_qty, 0),
                'critical_alerts_count': len([a for a in alerts if a['type'] in ['danger', 'warning']]),
                'live_pos_orders_count': pos_orders_count,
                'live_pos_sales_total': round(pos_sales_total, 2),
                'aov': round(aov, 2),
            },
            'branch_performance': {
                'rows': branch_rows,
                'top_branch': top_branch,
                'lowest_branch': lowest_branch,
            },
            'inventory_intelligence': {
                'warehouses': warehouse_breakdown,
                'dead_stock_items': dead_stock_items,
                'recommendations': recommendation_rows,
            },
            'financial_performance': {
                'total_expenses': round(total_expenses, 2),
                'expense_to_sales_pct': round(expense_to_sales_pct, 2),
                'branch_contribution': round(branch_contribution, 2),
                'expense_items': expense_items,
                'is_allocated_by_branch': False,
                'allocation_note': 'جميع المصروفات المسجلة حالياً مقيدة كمصروفات مركزية عامة لعدم وجود مراكز تكلفة تحليلية مخصصة للفروع.',
            },
            'business_alerts': alerts,
            'filters_metadata': {
                'branches': branch_options,
                'warehouses': warehouse_options,
                'selected_branch': selected_branch,
                'selected_warehouse_id': selected_wh_id,
            }
        }
