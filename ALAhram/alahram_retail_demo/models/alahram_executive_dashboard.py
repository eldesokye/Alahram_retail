# -*- coding: utf-8 -*-
import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta

import pytz
from odoo import _, api, fields, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

# Historical monthly summary dataset in alahram.branch.analytics covers 1-28 Oct 2026.
OCT_BASELINE_START = date(2026, 10, 1)
OCT_BASELINE_CORE_END = date(2026, 10, 28)
OCT_BASELINE_END = date(2026, 10, 31)

# Explicit showroom/branch keyword mapping for POS terminals / analytic accounts
# whose picking_type_id or code was left on the company's default generic warehouse.
BRANCH_NAME_PATTERNS = (
    ('WH-SG', ('سيدي جابر', 'sidi gaber', 'wh-sg')),
    ('WH-SHOBRA', ('شبرا', 'shobra', 'wh-shobra')),
    ('WH-SEKKA', ('السكة الجديدة', 'السكة', 'المنشية', 'sekka', 'wh-sekka')),
    ('WH-HANOVIL', ('هانوفيل', 'العجمي', 'hanovil', 'wh-hanovil')),
    ('WH-NASR', ('مدينة نصر', 'نصر', 'nasr', 'wh-nasr')),
    ('WH-FAISAL', ('فيصل', 'faisal', 'wh-faisal')),
    ('WH-ROSHDY', ('رشدي', 'لوران', 'roshdy', 'louran', 'wh-roshdy')),
    ('WH-SMOUHA', ('سموحة', 'باكوس', 'سموحه', 'smouha', 'baccous', 'wh-smouha')),
    ('WH-ONLINE', ('أونلاين', 'اونلاين', 'online', 'wh-online')),
    ('WH-MAIN', ('مخزن الإدارة', 'الادارة الرئيسي', 'الإدارة الرئيسي', 'wh-main')),
)


class AlahramExecutiveDashboard(models.TransientModel):
    _name = 'alahram.executive.dashboard'
    _description = 'لوحة التحكم والتحليلات التنفيذية للأهرام'

    # ------------------------------------------------------------------
    # Access & Filter Helpers
    # ------------------------------------------------------------------
    def _can_read(self, model_name):
        if model_name not in self.env:
            return False
        try:
            return bool(self.env[model_name].has_access('read'))
        except Exception:
            return False

    def _get_user_tz(self):
        tz_name = self.env.user.tz or self.env.company.partner_id.tz or 'Africa/Cairo'
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.timezone('Africa/Cairo')

    def _parse_date(self, val):
        if not val:
            return None
        if isinstance(val, date) and not isinstance(val, datetime):
            return val
        try:
            return fields.Date.to_date(str(val)[:10])
        except Exception:
            return None

    def _resolve_date_bounds(self, filters):
        user_tz = self._get_user_tz()
        now_local = datetime.now(pytz.UTC).astimezone(user_tz).date()
        preset = (filters.get('period_preset') or 'all').strip()

        raw_from = self._parse_date(filters.get('date_from'))
        raw_to = self._parse_date(filters.get('date_to'))

        if preset == 'oct_2026':
            d_from, d_to = date(2026, 10, 1), date(2026, 10, 31)
        elif preset == 'nov_2026':
            d_from, d_to = date(2026, 11, 1), date(2026, 11, 30)
        elif preset == 'current_month':
            d_from = now_local.replace(day=1)
            next_m = (d_from + timedelta(days=32)).replace(day=1)
            d_to = next_m - timedelta(days=1)
        elif preset == 'last_7_days':
            d_to = now_local
            d_from = now_local - timedelta(days=6)
        elif preset == 'last_30_days':
            d_to = now_local
            d_from = now_local - timedelta(days=29)
        elif preset == 'custom':
            d_from, d_to = raw_from, raw_to
        else:
            # 'all' or explicit dates passed directly
            if raw_from or raw_to:
                preset = 'custom'
                d_from, d_to = raw_from, raw_to
            else:
                preset = 'all'
                d_from, d_to = None, None

        if d_from and d_to and d_from > d_to:
            d_from, d_to = d_to, d_from

        dt_start_utc = None
        dt_end_utc = None
        if d_from:
            dt_start_utc = user_tz.localize(datetime.combine(d_from, time.min)).astimezone(pytz.UTC).replace(tzinfo=None)
        if d_to:
            dt_end_utc = user_tz.localize(datetime.combine(d_to, time.max)).astimezone(pytz.UTC).replace(tzinfo=None)

        # Include October 2026 historical baseline ONLY if no filter or range overlaps 1..28 Oct 2026
        include_oct_baseline = True
        if d_from or d_to:
            eff_from = d_from or date.min
            eff_to = d_to or date.max
            include_oct_baseline = (eff_from <= OCT_BASELINE_CORE_END and eff_to >= OCT_BASELINE_START)

        return {
            'preset': preset,
            'date_from': d_from,
            'date_to': d_to,
            'date_from_str': d_from.isoformat() if d_from else '',
            'date_to_str': d_to.isoformat() if d_to else '',
            'dt_start_utc': dt_start_utc,
            'dt_end_utc': dt_end_utc,
            'include_oct_baseline': include_oct_baseline,
            'user_tz': user_tz,
        }

    def _match_branch_code_from_text(self, text, valid_codes):
        if not text:
            return None
        low = text.lower()
        for code, patterns in BRANCH_NAME_PATTERNS:
            if code in valid_codes and any(pat in low for pat in patterns):
                return code
        return None

    def _resolve_pos_branch_code(self, pos_config, valid_branch_codes, wh_by_id):
        wh = pos_config.picking_type_id.warehouse_id if pos_config and pos_config.picking_type_id else False
        if wh and wh.code and wh.code in valid_branch_codes:
            return wh.code, wh.id, wh.name, 'warehouse'

        matched_code = self._match_branch_code_from_text(pos_config.name if pos_config else '', valid_branch_codes)
        if matched_code:
            matched_wh = next((w for w in wh_by_id.values() if w.code == matched_code), None)
            return (
                matched_code,
                matched_wh.id if matched_wh else (wh.id if wh else False),
                matched_wh.name if matched_wh else matched_code,
                'pos_config_name',
            )

        if wh:
            return wh.code or f'WH-{wh.id}', wh.id, wh.name, 'warehouse'
        return 'UNASSIGNED', False, 'عمليات غير مربوطة بمستودع', 'unassigned'

    # ------------------------------------------------------------------
    # Pillar C: Inventory Collection (Single Batched Pass, Zero N+1)
    # ------------------------------------------------------------------
    def _collect_inventory_data(self, company_id, all_warehouses, inv_wh_ids, selected_branch, selected_wh_id):
        wh_by_id = {w.id: w for w in all_warehouses}
        wh_stats = {
            w.id: {
                'id': w.id,
                'name': w.name,
                'code': w.code or '',
                'on_hand_qty': 0.0,
                'reserved_qty': 0.0,
                'available_qty': 0.0,
                'valuation': 0.0,
                'product_ids': set(),
                'quant_lines': 0,
                'zero_cost_product_ids': set(),
                'cost_gt_list_product_ids': set(),
            }
            for w in all_warehouses
        }

        has_quant_access = self._can_read('stock.quant')
        global_zero_cost_products = set()
        global_cost_gt_list_products = set()
        all_stocked_warehouse_ids = set()

        if has_quant_access:
            domain = [
                ('company_id', '=', company_id),
                ('location_id.usage', '=', 'internal'),
                '|',
                ('quantity', '!=', 0.0),
                ('reserved_quantity', '!=', 0.0),
            ]
            quants = self.env['stock.quant'].search(domain)
            if quants:
                # Prefetch related location, warehouse, owner, and product valuation metadata in batches
                quants.mapped('location_id.warehouse_id')
                quants.mapped('owner_id')
                products = quants.mapped('product_id')
                products.mapped('standard_price')
                products.mapped('list_price')
                products.mapped('categ_id.property_cost_method')
                products.mapped('lot_valuated')

                company_partner_id = self.env.company.partner_id.id
                loc_valued_cache = {}
                has_q_val_field = 'value' in quants._fields

                for q in quants:
                    loc = q.location_id
                    wh = loc.warehouse_id
                    if not wh:
                        continue
                    wh_id = wh.id
                    all_stocked_warehouse_ids.add(wh_id)
                    if wh_id not in wh_stats:
                        wh_stats[wh_id] = {
                            'id': wh.id,
                            'name': wh.name,
                            'code': wh.code or '',
                            'on_hand_qty': 0.0,
                            'reserved_qty': 0.0,
                            'available_qty': 0.0,
                            'valuation': 0.0,
                            'product_ids': set(),
                            'quant_lines': 0,
                            'zero_cost_product_ids': set(),
                            'cost_gt_list_product_ids': set(),
                        }
                    if inv_wh_ids is not None and wh_id not in inv_wh_ids:
                        continue

                    qty = float(q.quantity or 0.0)
                    res = float(q.reserved_quantity or 0.0)
                    prod = q.product_id
                    std_cost = float(prod.standard_price or 0.0)
                    list_price = float(prod.list_price or 0.0)

                    # Strict actual costing only (zero fallback to selling price).
                    # Fast batched calculation for standard/AVCO non-lot-valuated quants avoids 4,000+ _compute_value RPC queries.
                    if loc.id not in loc_valued_cache:
                        loc_valued_cache[loc.id] = loc._should_be_valued() if hasattr(loc, '_should_be_valued') else True
                    is_valued = loc_valued_cache[loc.id] and (not q.owner_id or q.owner_id.id == company_partner_id)

                    if not is_valued or abs(qty) < 1e-9:
                        quant_value = 0.0
                    elif not prod.lot_valuated and prod.cost_method != 'fifo':
                        quant_value = qty * std_cost if std_cost > 0 else 0.0
                    else:
                        quant_value = float(q.value or 0.0) if has_q_val_field else (qty * std_cost if std_cost > 0 else 0.0)

                    st = wh_stats[wh_id]
                    st['on_hand_qty'] += qty
                    st['reserved_qty'] += res
                    st['available_qty'] += (qty - res)
                    st['valuation'] += quant_value
                    st['quant_lines'] += 1
                    st['product_ids'].add(prod.id)

                    if std_cost <= 0.0 and qty > 0.0:
                        st['zero_cost_product_ids'].add(prod.id)
                        global_zero_cost_products.add(prod.id)
                    elif list_price > 0.0 and std_cost > list_price and qty > 0.0:
                        st['cost_gt_list_product_ids'].add(prod.id)
                        global_cost_gt_list_products.add(prod.id)

        target_wh_iter = [wh_stats[wid] for wid in wh_stats if (inv_wh_ids is None or wid in inv_wh_ids)]

        warehouse_breakdown = []
        total_on_hand = 0.0
        total_reserved = 0.0
        total_available = 0.0
        total_valuation = 0.0
        tracked_wh_count = 0

        for st in target_wh_iter:
            is_tracked = st['quant_lines'] > 0
            if is_tracked:
                tracked_wh_count += 1
            on_hand = round(st['on_hand_qty'], 2)
            reserved = round(st['reserved_qty'], 2)
            available = round(st['available_qty'], 2)
            valuation = round(st['valuation'], 2)
            total_on_hand += on_hand
            total_reserved += reserved
            total_available += available
            total_valuation += valuation

            # Show stocked warehouses or explicitly selected/core warehouses cleanly
            if is_tracked or selected_wh_id == st['id'] or (selected_branch and st['code'] == selected_branch) or st['code'] in ('WH-MAIN', 'WH-SG', 'WH-ROSHDY'):
                warehouse_breakdown.append({
                    'id': st['id'],
                    'name': st['name'],
                    'code': st['code'],
                    'products_count': len(st['product_ids']),
                    'on_hand_qty': round(on_hand, 0),
                    'reserved_qty': round(reserved, 0),
                    'available_qty': round(available, 0),
                    'valuation': valuation,
                    'is_tracked': is_tracked,
                    'zero_cost_skus': len(st['zero_cost_product_ids']),
                    'cost_gt_list_skus': len(st['cost_gt_list_product_ids']),
                })

        warehouse_breakdown.sort(key=lambda x: (x['valuation'], x['on_hand_qty']), reverse=True)

        # Dead Stock (Single batched read_group — zero N+1)
        dead_stock_items = []
        dead_stock_value = 0.0
        dead_stock_qty = 0.0
        dead_stock_templates = self.env['product.template'].search([('is_dead_stock', '=', True)], order='list_price desc')
        if dead_stock_templates and has_quant_access:
            variant_ids = dead_stock_templates.mapped('product_variant_ids').ids
            quant_domain = [
                ('company_id', '=', company_id),
                ('product_id', 'in', variant_ids),
                ('location_id.usage', '=', 'internal'),
            ]
            if inv_wh_ids is not None:
                quant_domain.append(('location_id.warehouse_id', 'in', list(inv_wh_ids)))
            grouped = self.env['stock.quant'].read_group(
                quant_domain,
                groupby=['product_id'],
                aggregates=['quantity:sum'],
            )
            qty_by_prod = {
                (prod.id if hasattr(prod, 'id') else prod): float(qty_sum or 0.0)
                for prod, qty_sum in grouped
                if prod
            }

            for pt in dead_stock_templates:
                variants = pt.product_variant_ids
                qty = sum(qty_by_prod.get(v.id, 0.0) for v in variants)
                unit_cost = float(pt.product_variant_id.standard_price or 0.0) if pt.product_variant_id else 0.0
                val = qty * unit_cost if unit_cost > 0 else 0.0
                dead_stock_qty += qty
                dead_stock_value += val
                dead_stock_items.append({
                    'id': pt.id,
                    'name': pt.name,
                    'code': pt.default_code or pt.barcode or 'بدون كود',
                    'list_price': round(float(pt.list_price or 0.0), 2),
                    'unit_cost': round(unit_cost, 2),
                    'has_cost': unit_cost > 0,
                    'qty': round(qty, 0),
                    'total_val': round(val, 2),
                    'recommendation': 'تسييل عبر باكدجات العرائس وتخفيضات مدروسة',
                })

        # Smart Replenishment Recommendations
        rec_domain = []
        if inv_wh_ids is not None:
            wh_list = list(inv_wh_ids)
            rec_domain = ['|', ('src_warehouse_id', 'in', wh_list), ('dest_warehouse_id', 'in', wh_list)]
        recommendations = self.env['alahram.stock.recommendation'].search(
            rec_domain, order='priority_score desc, id desc', limit=10
        ) if self._can_read('alahram.stock.recommendation') else self.env['alahram.stock.recommendation']
        recommendation_rows = [
            {
                'id': r.id,
                'name': r.name,
                'product_name': r.product_id.display_name,
                'src_warehouse': r.src_warehouse_id.name or 'مخزن غير محدد',
                'dest_warehouse': r.dest_warehouse_id.name or 'صالة العرض',
                'suggested_qty': r.suggested_qty or 0,
                'dead_stock_cost': round(float(r.dead_stock_cost or 0.0), 2),
                'priority': r.priority or 'medium',
                'state': r.state or 'pending',
                'reason': r.reason or '',
            }
            for r in recommendations
        ]

        return {
            'has_access': has_quant_access,
            'wh_stats_by_code': {wh_stats[wid]['code']: wh_stats[wid] for wid in wh_stats if wh_stats[wid]['code']},
            'warehouses': warehouse_breakdown,
            'total_on_hand_qty': round(total_on_hand, 0),
            'total_reserved_qty': round(total_reserved, 0),
            'total_available_qty': round(total_available, 0),
            'total_valuation': round(total_valuation, 2),
            'tracked_warehouses_count': tracked_wh_count,
            'total_warehouses_count': len(target_wh_iter),
            'stocked_warehouses_global_count': len(all_stocked_warehouse_ids),
            'dead_stock_items': dead_stock_items,
            'dead_stock_value': round(dead_stock_value, 2),
            'dead_stock_qty': round(dead_stock_qty, 0),
            'recommendations': recommendation_rows,
            'zero_cost_sku_count': len(global_zero_cost_products),
            'cost_gt_list_sku_count': len(global_cost_gt_list_products),
        }

    # ------------------------------------------------------------------
    # Pillars A & B: Branch Analytics, Live POS, Deduplicated Sales Orders, Targets
    # ------------------------------------------------------------------
    def _collect_sales_and_targets(
        self, company_id, date_ctx, all_branches, all_warehouses, selected_branch, selected_wh_code
    ):
        wh_by_id = {w.id: w for w in all_warehouses}
        wh_by_code = {w.code: w for w in all_warehouses if w.code}
        analytics_by_code = {b.warehouse_code: b for b in all_branches if b.warehouse_code}
        valid_branch_codes = set(analytics_by_code.keys())

        effective_code_filter = selected_branch or selected_wh_code

        # Also check optional Odoo Enterprise budget items if any exist in future/other DBs
        budget_targets_by_code = {}
        if 'account.report.budget.item' in self.env and self._can_read('account.report.budget.item'):
            budget_items = self.env['account.report.budget.item'].search([('budget_id.company_id', '=', company_id)])
            for item in budget_items:
                acct_name = (item.account_id.name or '') if hasattr(item, 'account_id') and item.account_id else ''
                code = self._match_branch_code_from_text(acct_name, valid_branch_codes)
                if code:
                    budget_targets_by_code[code] = budget_targets_by_code.get(code, 0.0) + float(item.amount or 0.0)

        # 1) Live POS Orders (Single query, prefetched lines & configs)
        has_pos_access = self._can_read('pos.order')
        pos_orders = self.env['pos.order']
        pos_settled_so_ids = set()
        if has_pos_access:
            # Globally collect any sale.order already paid/settled through POS to prevent double counting
            if 'pos.order.line' in self.env and self._can_read('pos.order.line'):
                settled_lines = self.env['pos.order.line'].search([
                    ('order_id.company_id', '=', company_id),
                    ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
                    ('sale_order_origin_id', '!=', False),
                ])
                pos_settled_so_ids = set(settled_lines.mapped('sale_order_origin_id').ids)

            pos_domain = [
                ('company_id', '=', company_id),
                ('state', 'in', ['paid', 'done', 'invoiced']),
            ]
            if date_ctx['dt_start_utc']:
                pos_domain.append(('date_order', '>=', fields.Datetime.to_string(date_ctx['dt_start_utc'])))
            if date_ctx['dt_end_utc']:
                pos_domain.append(('date_order', '<=', fields.Datetime.to_string(date_ctx['dt_end_utc'])))

            pos_orders = self.env['pos.order'].search(pos_domain, order='date_order asc')
            pos_orders.mapped('config_id.picking_type_id.warehouse_id')
            pos_orders.mapped('lines.discount')

        live_pos_by_code = defaultdict(lambda: {
            'orders_count': 0,
            'net_inc': 0.0,
            'net_exc': 0.0,
            'tax': 0.0,
            'discount': 0.0,
            'return_val': 0.0,
            'return_qty': 0,
            'sold_qty': 0,
            'unmapped_name': '',
            'warehouse_id': False,
        })
        daily_trend = defaultdict(lambda: {'pos': 0.0, 'so': 0.0, 'orders': 0})

        user_tz = date_ctx['user_tz']
        for o in pos_orders:
            b_code, wh_id, wh_label, _src = self._resolve_pos_branch_code(o.config_id, valid_branch_codes, wh_by_id)
            if effective_code_filter and b_code != effective_code_filter:
                continue

            amt_inc = float(o.amount_total or 0.0)
            amt_tax = float(o.amount_tax or 0.0)
            amt_exc = amt_inc - amt_tax

            bucket = live_pos_by_code[b_code]
            bucket['orders_count'] += 1
            bucket['net_inc'] += amt_inc
            bucket['net_exc'] += amt_exc
            bucket['tax'] += amt_tax
            bucket['unmapped_name'] = bucket['unmapped_name'] or wh_label
            bucket['warehouse_id'] = bucket['warehouse_id'] or wh_id

            if amt_inc < 0:
                bucket['return_val'] += amt_inc

            for line in o.lines:
                qty = float(line.qty or 0.0)
                if qty < 0:
                    bucket['return_qty'] += int(round(qty))
                else:
                    bucket['sold_qty'] += int(round(qty))
                if line.discount and line.price_unit and qty > 0:
                    bucket['discount'] += qty * float(line.price_unit) * (float(line.discount) / 100.0)

            if o.date_order:
                dt_local = pytz.UTC.localize(o.date_order).astimezone(user_tz).date().isoformat()
                daily_trend[dt_local]['pos'] += amt_inc
                daily_trend[dt_local]['orders'] += 1

        # 2) Direct Sale Orders (Confirmed, strictly deduplicated from POS-settled SOs)
        has_so_access = self._can_read('sale.order')
        live_so_by_code = defaultdict(lambda: {
            'orders_count': 0,
            'net_inc': 0.0,
            'net_exc': 0.0,
            'tax': 0.0,
            'warehouse_id': False,
            'warehouse_name': '',
        })
        dedup_excluded_so_count = 0
        if has_so_access:
            so_domain = [
                ('company_id', '=', company_id),
                ('state', 'in', ['sale', 'done']),
            ]
            if date_ctx['dt_start_utc']:
                so_domain.append(('date_order', '>=', fields.Datetime.to_string(date_ctx['dt_start_utc'])))
            if date_ctx['dt_end_utc']:
                so_domain.append(('date_order', '<=', fields.Datetime.to_string(date_ctx['dt_end_utc'])))

            sale_orders = self.env['sale.order'].search(so_domain, order='date_order asc')
            sale_orders.mapped('warehouse_id')
            for s in sale_orders:
                if s.id in pos_settled_so_ids:
                    dedup_excluded_so_count += 1
                    continue
                wh = s.warehouse_id
                code = wh.code if wh and wh.code else (f'WH-{wh.id}' if wh else 'UNASSIGNED')
                if effective_code_filter and code != effective_code_filter:
                    continue

                amt_inc = float(s.amount_total or 0.0)
                amt_exc = float(s.amount_untaxed or 0.0)
                amt_tax = float(s.amount_tax or (amt_inc - amt_exc))
                sb = live_so_by_code[code]
                sb['orders_count'] += 1
                sb['net_inc'] += amt_inc
                sb['net_exc'] += amt_exc
                sb['tax'] += amt_tax
                sb['warehouse_id'] = sb['warehouse_id'] or (wh.id if wh else False)
                sb['warehouse_name'] = sb['warehouse_name'] or (wh.name if wh else 'مبيعات مباشرة')

                if s.date_order:
                    dt_local = pytz.UTC.localize(s.date_order).astimezone(user_tz).date().isoformat()
                    daily_trend[dt_local]['so'] += amt_inc
                    daily_trend[dt_local]['orders'] += 1

        # 3) Combine Historical Baseline + Live Transactions cleanly per branch
        branch_entities = []
        seen_codes = set()
        for rec in all_branches:
            code = rec.warehouse_code or ''
            if effective_code_filter and code != effective_code_filter:
                continue
            seen_codes.add(code)

            if date_ctx['include_oct_baseline']:
                base_gross = float(rec.gross_sales or 0.0)
                base_disc = float(rec.discount_given or 0.0)
                base_vat = float(rec.vat_14_amount or 0.0)
                base_ret_qty = int(rec.return_qty or 0)
                base_ret_val = float(rec.return_value or 0.0)
                base_ret_rate = float(rec.return_rate or 0.0)
                base_inc = float(rec.net_sales_inc_vat or 0.0)
                base_exc = float(rec.net_sales_exc_vat or 0.0)
                base_cogs = float(rec.cogs_cost or 0.0)
                base_profit = float(rec.net_profit or 0.0)
                base_qty = int(rec.net_sold_qty or 0)
            else:
                base_gross = base_disc = base_vat = base_ret_val = base_ret_rate = 0.0
                base_inc = base_exc = base_cogs = base_profit = 0.0
                base_ret_qty = base_qty = 0

            pos_b = live_pos_by_code.get(code) or {}
            so_b = live_so_by_code.get(code) or {}

            live_pos_inc = float(pos_b.get('net_inc', 0.0))
            live_pos_exc = float(pos_b.get('net_exc', 0.0))
            live_so_inc = float(so_b.get('net_inc', 0.0))
            live_so_exc = float(so_b.get('net_exc', 0.0))

            actual_inc = base_inc + live_pos_inc + live_so_inc
            actual_exc = base_exc + live_pos_exc + live_so_exc
            total_disc = base_disc + float(pos_b.get('discount', 0.0))
            total_vat = base_vat + float(pos_b.get('tax', 0.0)) + float(so_b.get('tax', 0.0))
            total_ret_val = base_ret_val + float(pos_b.get('return_val', 0.0))
            total_ret_qty = base_ret_qty + int(pos_b.get('return_qty', 0))
            total_gross = base_gross + actual_exc if not date_ctx['include_oct_baseline'] else (base_gross + live_pos_exc + live_so_exc)

            # Effective return rate: use historical baseline rate if pure baseline, else compute dynamically
            if base_inc > 0 and live_pos_inc == 0 and live_so_inc == 0:
                eff_return_rate = base_ret_rate
            else:
                denom = abs(actual_inc) + abs(total_ret_val)
                eff_return_rate = (abs(total_ret_val) / denom * 100.0) if denom > 0 else 0.0

            # Margin only reflects verified historical COGS when baseline is active (never distorted by unverified product costs)
            has_verified_profit = base_exc > 0
            margin_pct = (base_profit / base_exc * 100.0) if has_verified_profit else None
            disc_pct = (total_disc / total_gross * 100.0) if total_gross > 0 else 0.0

            configured_target = float(getattr(rec, 'sales_target', 0.0) or 0.0)
            if configured_target <= 0.0 and code in budget_targets_by_code:
                configured_target = float(budget_targets_by_code[code])

            has_target = configured_target > 0.0
            achievement_pct = round((actual_inc / configured_target * 100.0), 1) if has_target else None
            remaining_target = round(max(0.0, configured_target - actual_inc), 2) if has_target else None

            wh = wh_by_code.get(code)
            branch_entities.append({
                'id': rec.id,
                'key': code,
                'name': rec.branch_name,
                'code': code,
                'row_type': 'branch',
                'warehouse_id': wh.id if wh else False,
                'warehouse_name': wh.name if wh else '',
                'net_sold_qty': base_qty + int(pos_b.get('sold_qty', 0)),
                'gross_sales': round(total_gross, 2),
                'discount_given': round(total_disc, 2),
                'discount_pct': round(disc_pct, 1),
                'vat_14': round(total_vat, 2),
                'return_qty': total_ret_qty,
                'return_value': round(total_ret_val, 2),
                'return_rate': round(eff_return_rate, 2),
                'baseline_sales_inc_vat': round(base_inc, 2),
                'baseline_sales_exc_vat': round(base_exc, 2),
                'live_pos_sales_inc_vat': round(live_pos_inc, 2),
                'live_so_sales_inc_vat': round(live_so_inc, 2),
                'actual_sales_inc_vat': round(actual_inc, 2),
                'actual_sales_exc_vat': round(actual_exc, 2),
                'net_sales_inc_vat': round(actual_inc, 2),
                'net_sales_exc_vat': round(actual_exc, 2),
                'live_orders_count': int(pos_b.get('orders_count', 0)) + int(so_b.get('orders_count', 0)),
                'cogs': round(base_cogs, 2),
                'profit': round(base_profit, 2),
                'has_verified_profit': has_verified_profit,
                'margin_pct': round(margin_pct, 1) if margin_pct is not None else None,
                'sales_target': round(configured_target, 2) if has_target else None,
                'has_target': has_target,
                'achievement_pct': achievement_pct,
                'remaining_target': remaining_target,
                'target_status': f'{achievement_pct:.1f}%' if has_target else 'غير محدد في النظام',
            })

        # Unmapped warehouse channels having live POS/SO sales (e.g. default WH 'YourCompany')
        unmapped_sales_codes = (set(live_pos_by_code.keys()) | set(live_so_by_code.keys())) - seen_codes
        unmapped_rows = []
        for ucode in sorted(unmapped_sales_codes):
            if effective_code_filter and ucode != effective_code_filter:
                continue
            pos_b = live_pos_by_code.get(ucode) or {}
            so_b = live_so_by_code.get(ucode) or {}
            live_pos_inc = float(pos_b.get('net_inc', 0.0))
            live_pos_exc = float(pos_b.get('net_exc', 0.0))
            live_so_inc = float(so_b.get('net_inc', 0.0))
            live_so_exc = float(so_b.get('net_exc', 0.0))
            actual_inc = live_pos_inc + live_so_inc
            actual_exc = live_pos_exc + live_so_exc
            if actual_inc == 0 and not pos_b and not so_b:
                continue
            wh = wh_by_code.get(ucode)
            ret_val = float(pos_b.get('return_val', 0.0))
            denom = abs(actual_inc) + abs(ret_val)
            ret_rate = (abs(ret_val) / denom * 100.0) if denom > 0 else 0.0
            disc = float(pos_b.get('discount', 0.0))
            disc_pct = (disc / actual_exc * 100.0) if actual_exc > 0 else 0.0
            label = wh.name if wh else (so_b.get('warehouse_name') or pos_b.get('unmapped_name') or ucode)
            unmapped_rows.append({
                'id': False,
                'key': ucode,
                'name': f'{label} (قناة عامة / غير مخصصة لفرع)',
                'code': ucode,
                'row_type': 'unmapped_channel',
                'warehouse_id': wh.id if wh else (pos_b.get('warehouse_id') or so_b.get('warehouse_id') or False),
                'warehouse_name': label,
                'net_sold_qty': int(pos_b.get('sold_qty', 0)),
                'gross_sales': round(actual_exc, 2),
                'discount_given': round(disc, 2),
                'discount_pct': round(disc_pct, 1),
                'vat_14': round(float(pos_b.get('tax', 0.0)) + float(so_b.get('tax', 0.0)), 2),
                'return_qty': int(pos_b.get('return_qty', 0)),
                'return_value': round(ret_val, 2),
                'return_rate': round(ret_rate, 2),
                'baseline_sales_inc_vat': 0.0,
                'baseline_sales_exc_vat': 0.0,
                'live_pos_sales_inc_vat': round(live_pos_inc, 2),
                'live_so_sales_inc_vat': round(live_so_inc, 2),
                'actual_sales_inc_vat': round(actual_inc, 2),
                'actual_sales_exc_vat': round(actual_exc, 2),
                'net_sales_inc_vat': round(actual_inc, 2),
                'net_sales_exc_vat': round(actual_exc, 2),
                'live_orders_count': int(pos_b.get('orders_count', 0)) + int(so_b.get('orders_count', 0)),
                'cogs': 0.0,
                'profit': 0.0,
                'has_verified_profit': False,
                'margin_pct': None,
                'sales_target': None,
                'has_target': False,
                'achievement_pct': None,
                'remaining_target': None,
                'target_status': 'غير محدد في النظام',
            })

        # Rank branches by Actual Sales descending
        branch_entities.sort(key=lambda r: r['actual_sales_inc_vat'], reverse=True)
        for idx, b in enumerate(branch_entities, start=1):
            b['rank'] = idx
            if b['return_rate'] > 20.0:
                b['badge'] = 'high_return'
            elif idx == 1 and b['actual_sales_inc_vat'] > 0:
                b['badge'] = 'top'
            else:
                b['badge'] = 'normal'

        for u in unmapped_rows:
            u['rank'] = None
            u['badge'] = 'unmapped'

        all_sales_rows = branch_entities + unmapped_rows

        daily_trend_list = [
            {
                'date': d_str,
                'pos_sales': round(vals['pos'], 2),
                'so_sales': round(vals['so'], 2),
                'total_sales': round(vals['pos'] + vals['so'], 2),
                'orders_count': vals['orders'],
            }
            for d_str, vals in sorted(daily_trend.items())
        ]

        return {
            'branch_rows': branch_entities,
            'unmapped_sales_rows': unmapped_rows,
            'all_sales_rows': all_sales_rows,
            'daily_trend': daily_trend_list,
            'dedup_excluded_so_count': dedup_excluded_so_count,
            'has_pos_access': has_pos_access,
            'has_so_access': has_so_access,
        }

    # ------------------------------------------------------------------
    # Pillar D: Operational Expenses & Strict Financial Audit
    # ------------------------------------------------------------------
    def _collect_expenses_data(self, company_id, date_ctx, valid_branch_codes, selected_branch):
        has_access = self._can_read('account.move.line')
        if not has_access:
            return {
                'has_access': False,
                'total_expenses': 0.0,
                'allocated_expenses': 0.0,
                'unallocated_expenses': 0.0,
                'expenses_by_branch': {},
                'expense_categories': [],
                'expense_items': [],
                'excluded_purchases_total': 0.0,
                'excluded_tax_total': 0.0,
                'excluded_cogs_total': 0.0,
                'is_allocated_by_branch': False,
                'allocation_note': 'ليس لديك صلاحية الوصول إلى القيود المحاسبية لقراءة المصروفات.',
                'previous_period': {'has_prev_data': False, 'prev_total': 0.0, 'change_pct': None},
                'hr_expense_installed': 'hr.expense' in self.env,
                'hr_expense_count': 0,
            }

        def query_aml(d_from, d_to):
            dom = [
                ('move_id.state', '=', 'posted'),
                ('company_id', '=', company_id),
                ('account_id.account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost']),
            ]
            if d_from:
                dom.append(('date', '>=', d_from))
            if d_to:
                dom.append(('date', '<=', d_to))
            return self.env['account.move.line'].search(dom, order='date desc, id desc')

        lines = query_aml(date_ctx['date_from'], date_ctx['date_to'])
        if lines:
            lines.mapped('move_id')
            lines.mapped('account_id')
            lines.mapped('product_id.product_tmpl_id')
            lines.mapped('partner_id')
            lines.mapped('tax_line_id')

        # Resolve analytic accounts across all lines in one batch query
        analytic_ids = set()
        for l in lines:
            if isinstance(l.analytic_distribution, dict):
                for key in l.analytic_distribution:
                    for part in str(key).split(','):
                        part = part.strip()
                        if part.isdigit():
                            analytic_ids.add(int(part))

        analytic_branch_map = {}
        if analytic_ids and self._can_read('account.analytic.account'):
            analytics = self.env['account.analytic.account'].browse(list(analytic_ids)).exists()
            for aa in analytics:
                matched = self._match_branch_code_from_text(f"{aa.code or ''} {aa.name or ''}", valid_branch_codes)
                if matched:
                    analytic_branch_map[str(aa.id)] = matched

        opex_total = 0.0
        allocated_total = 0.0
        unallocated_total = 0.0
        excluded_purchases_total = 0.0
        excluded_tax_total = 0.0
        excluded_cogs_total = 0.0

        expenses_by_branch = defaultdict(float)
        category_totals = defaultdict(lambda: {'name': '', 'code': '', 'amount': 0.0, 'lines_count': 0})
        expense_items = []
        excluded_items = []

        for l in lines:
            amt = float(l.debit or 0.0) - float(l.credit or 0.0)
            acc = l.account_id
            move = l.move_id

            # 1) Recoverable purchase VAT lines accidentally mapped to expense account
            if l.tax_line_id:
                excluded_tax_total += amt
                excluded_items.append({
                    'id': l.id,
                    'move_name': move.name,
                    'date': str(l.date or ''),
                    'reason': 'ضريبة قيمة مضافة على المشتريات (ليست مصروفاً تشغيلياً)',
                    'amount': round(amt, 2),
                })
                continue

            # 2) Direct COGS lines
            if acc.account_type == 'expense_direct_cost':
                excluded_cogs_total += amt
                continue

            # 3) Periodic inventory/merchandise purchase vendor bills (storable goods)
            if move.move_type in ('in_invoice', 'in_refund') and l.product_id and l.product_id.is_storable:
                excluded_purchases_total += amt
                excluded_items.append({
                    'id': l.id,
                    'move_name': move.name,
                    'date': str(l.date or ''),
                    'reason': f'فاتورة شراء مخزون / بضاعة ({l.product_id.display_name})',
                    'amount': round(amt, 2),
                })
                continue

            # 4) Verified Operating Expense Line
            branch_allocs = []
            if isinstance(l.analytic_distribution, dict):
                for key, pct in l.analytic_distribution.items():
                    pct_f = float(pct or 0.0) / 100.0
                    for part in str(key).split(','):
                        part = part.strip()
                        if part in analytic_branch_map and pct_f:
                            branch_allocs.append((analytic_branch_map[part], amt * pct_f))

            if branch_allocs:
                line_alloc_sum = 0.0
                for bcode, bamt in branch_allocs:
                    expenses_by_branch[bcode] += bamt
                    line_alloc_sum += bamt
                allocated_total += line_alloc_sum
                rem = amt - line_alloc_sum
                if abs(rem) > 0.01:
                    unallocated_total += rem
            else:
                unallocated_total += amt

            # When branch filter is set, count only expenses genuinely allocated to that branch
            include_in_filtered_total = True
            if selected_branch:
                branch_share = sum(bamt for bcode, bamt in branch_allocs if bcode == selected_branch)
                if not branch_allocs or branch_share == 0.0:
                    include_in_filtered_total = False
                else:
                    amt = branch_share

            if include_in_filtered_total:
                opex_total += amt
                cat_key = acc.id
                cat_bucket = category_totals[cat_key]
                cat_bucket['name'] = acc.name or 'مصروفات تشغيلية'
                cat_bucket['code'] = acc.code or ''
                cat_bucket['amount'] += amt
                cat_bucket['lines_count'] += 1

                expense_items.append({
                    'id': l.id,
                    'move_id': move.id,
                    'move_name': move.name or 'قيد محاسبي',
                    'move_type': move.move_type,
                    'date': str(l.date or ''),
                    'partner_name': l.partner_id.name or 'مصروف عام',
                    'account_code': acc.code or '',
                    'account_name': acc.name or 'مصروفات',
                    'description': l.name or move.ref or '',
                    'branch_allocated': ', '.join(b for b, _a in branch_allocs) if branch_allocs else 'غير مخصص لفرع (مركزي)',
                    'debit': round(float(l.debit or 0.0), 2),
                    'credit': round(float(l.credit or 0.0), 2),
                    'amount': round(amt, 2),
                })

        is_allocated_by_branch = abs(allocated_total) > 0.01
        company_total_opex = round(allocated_total + unallocated_total, 2)
        opex_total = round(max(0.0, opex_total), 2)

        expense_categories = sorted(
            [
                {
                    'code': c['code'],
                    'name': f"{c['code']} - {c['name']}" if c['code'] else c['name'],
                    'amount': round(c['amount'], 2),
                    'lines_count': c['lines_count'],
                }
                for c in category_totals.values()
                if abs(c['amount']) > 0.001
            ],
            key=lambda x: x['amount'],
            reverse=True,
        )

        # Previous Period Comparison when custom/bounded dates are selected
        prev_info = {'has_prev_data': False, 'prev_total': 0.0, 'change_pct': None, 'prev_label': ''}
        if date_ctx['date_from'] and date_ctx['date_to']:
            span_days = (date_ctx['date_to'] - date_ctx['date_from']).days + 1
            prev_to = date_ctx['date_from'] - timedelta(days=1)
            prev_from = prev_to - timedelta(days=span_days - 1)
            prev_lines = query_aml(prev_from, prev_to)
            prev_opex = 0.0
            for pl in prev_lines:
                if pl.tax_line_id or pl.account_id.account_type == 'expense_direct_cost':
                    continue
                if pl.move_id.move_type in ('in_invoice', 'in_refund') and pl.product_id and pl.product_id.is_storable:
                    continue
                prev_opex += float(pl.debit or 0.0) - float(pl.credit or 0.0)
            prev_opex = round(max(0.0, prev_opex), 2)
            prev_info['prev_label'] = f"{prev_from.isoformat()} → {prev_to.isoformat()}"
            prev_info['prev_total'] = prev_opex
            if prev_opex > 0:
                prev_info['has_prev_data'] = True
                prev_info['change_pct'] = round(((opex_total - prev_opex) / prev_opex) * 100.0, 1)

        if is_allocated_by_branch:
            alloc_note = f"تم توزيع {allocated_total:,.2f} ج.م على الفروع عبر الحسابات التحليلية، ويتبقى {unallocated_total:,.2f} ج.م مصروفات مركزية غير موزعة."
        else:
            alloc_note = (
                "لم يتم ربط قيود المصروفات التشغيلية بمراكز تكلفة تحليلية للفروع (Analytic Distribution = فارغ). "
                "تُعرض المصروفات التشغيلية المعتمدة على مستوى الشركة فقط دون توزيع تقديري مصطنع على الفروع."
            )

        hr_installed = 'hr.expense' in self.env
        hr_count = self.env['hr.expense'].search_count([]) if (hr_installed and self._can_read('hr.expense')) else 0

        return {
            'has_access': True,
            'total_expenses': opex_total,
            'company_total_expenses': company_total_opex,
            'allocated_expenses': round(allocated_total, 2),
            'unallocated_expenses': round(unallocated_total, 2),
            'expenses_by_branch': {k: round(v, 2) for k, v in expenses_by_branch.items()},
            'expense_categories': expense_categories,
            'expense_items': expense_items[:25],
            'excluded_purchases_total': round(excluded_purchases_total, 2),
            'excluded_tax_total': round(excluded_tax_total, 2),
            'excluded_cogs_total': round(excluded_cogs_total, 2),
            'excluded_items': excluded_items[:15],
            'is_allocated_by_branch': is_allocated_by_branch,
            'allocation_note': alloc_note,
            'previous_period': prev_info,
            'hr_expense_installed': hr_installed,
            'hr_expense_count': hr_count,
        }

    # ------------------------------------------------------------------
    # Chart Payloads (Chart.js v4.5.0 Direct Bindings)
    # ------------------------------------------------------------------
    def _build_charts_payload(self, sales_data, inv_data, exp_data, overview, selected_branch):
        branch_rows = sales_data['branch_rows']

        # Chart 1: Branch Sales vs Sales Targets (Grouped Bar)
        configured_target_branches = [b for b in branch_rows if b['has_target']]
        has_any_target = len(configured_target_branches) > 0
        sales_vs_target = {
            'labels': [b['name'] for b in branch_rows],
            'codes': [b['code'] for b in branch_rows],
            'actual_sales': [b['actual_sales_inc_vat'] for b in branch_rows],
            'baseline_sales': [b['baseline_sales_inc_vat'] for b in branch_rows],
            'live_sales': [round(b['live_pos_sales_inc_vat'] + b['live_so_sales_inc_vat'], 2) for b in branch_rows],
            'sales_targets': [b['sales_target'] if b['has_target'] else None for b in branch_rows],
            'achievement_pcts': [b['achievement_pct'] for b in branch_rows],
            'has_any_target': has_any_target,
            'configured_count': len(configured_target_branches),
            'total_branches_count': len(branch_rows),
        }

        # Chart 2: Warehouse Inventory Distribution (Stacked Bar: Available + Reserved, Valuation overlay)
        stocked_wh = [w for w in inv_data['warehouses'] if w['on_hand_qty'] > 0 or w['reserved_qty'] > 0]
        warehouse_inventory = {
            'labels': [w['name'] for w in stocked_wh],
            'codes': [w['code'] for w in stocked_wh],
            'available_qty': [w['available_qty'] for w in stocked_wh],
            'reserved_qty': [w['reserved_qty'] for w in stocked_wh],
            'on_hand_qty': [w['on_hand_qty'] for w in stocked_wh],
            'valuation': [w['valuation'] for w in stocked_wh],
            'products_count': [w['products_count'] for w in stocked_wh],
            'has_data': len(stocked_wh) > 0,
            'untracked_message': '' if stocked_wh else 'لا توجد أرصدة مخزنية مسجلة في stock.quant للمستودع / الفرع المحدد.',
        }

        # Chart 3: Operational Expenses (By Branch if allocated analytically, else by Account Category)
        if exp_data['is_allocated_by_branch']:
            exp_labels = [b['name'] for b in branch_rows if exp_data['expenses_by_branch'].get(b['code'], 0.0) > 0]
            exp_values = [exp_data['expenses_by_branch'][b['code']] for b in branch_rows if exp_data['expenses_by_branch'].get(b['code'], 0.0) > 0]
            if exp_data['unallocated_expenses'] > 0 and not selected_branch:
                exp_labels.append('مصروفات مركزية غير موزعة')
                exp_values.append(exp_data['unallocated_expenses'])
            exp_mode = 'by_branch'
        else:
            exp_labels = [c['name'] for c in exp_data['expense_categories']]
            exp_values = [c['amount'] for c in exp_data['expense_categories']]
            exp_mode = 'by_category'

        expenses_chart = {
            'mode': exp_mode,
            'labels': exp_labels,
            'values': exp_values,
            'has_data': len(exp_values) > 0 and any(v > 0 for v in exp_values),
            'is_allocated_by_branch': exp_data['is_allocated_by_branch'],
            'excluded_purchases_total': exp_data['excluded_purchases_total'],
        }

        # Chart 4: Branch Operational Performance Radar (4 verified KPI dimensions 0..100)
        # Compares Top 3 branches + High-return / Lowest branch (or Selected Branch vs Company Avg)
        radar_candidates = [b for b in branch_rows if b['actual_sales_inc_vat'] > 0]
        radar_series = []
        if radar_candidates:
            max_sales = max(b['actual_sales_inc_vat'] for b in radar_candidates) or 1.0

            def to_radar_scores(b):
                sales_idx = round((b['actual_sales_inc_vat'] / max_sales) * 100.0, 1)
                margin_score = round(max(0.0, min(100.0, b['margin_pct'] or 0.0)), 1)
                return_discipline = round(max(0.0, min(100.0, 100.0 - float(b['return_rate'] or 0.0))), 1)
                discount_control = round(max(0.0, min(100.0, 100.0 - float(b['discount_pct'] or 0.0))), 1)
                return [sales_idx, margin_score, return_discipline, discount_control]

            if len(radar_candidates) == 1:
                chosen = radar_candidates
            else:
                chosen_ids = set()
                chosen = []
                # Top 2 by sales, highest return branch, lowest sales branch
                for b in radar_candidates[:2]:
                    chosen.append(b)
                    chosen_ids.add(b['key'])
                highest_ret = max(radar_candidates, key=lambda x: x['return_rate'])
                if highest_ret['key'] not in chosen_ids:
                    chosen.append(highest_ret)
                    chosen_ids.add(highest_ret['key'])
                lowest = radar_candidates[-1]
                if lowest['key'] not in chosen_ids:
                    chosen.append(lowest)
                    chosen_ids.add(lowest['key'])

            for b in chosen[:4]:
                radar_series.append({
                    'label': b['name'],
                    'data': to_radar_scores(b),
                })

        performance_radar = {
            'axes': [
                'مؤشر حجم المبيعات %',
                'هامش الربح الإجمالي %',
                'انضباط المرتجعات (100 - % المرتجع)',
                'ضبط الخصومات (100 - % الخصم)',
            ],
            'datasets': radar_series,
            'has_data': len(radar_series) > 0,
        }

        # Chart 5: Daily Live Sales Trend (Strictly real dated orders, NO fake interpolation)
        trend_points = sales_data['daily_trend']
        sales_trend = {
            'labels': [p['date'] for p in trend_points],
            'pos_sales': [p['pos_sales'] for p in trend_points],
            'so_sales': [p['so_sales'] for p in trend_points],
            'total_sales': [p['total_sales'] for p in trend_points],
            'orders_count': [p['orders_count'] for p in trend_points],
            'has_data': len(trend_points) > 0,
        }

        return {
            'sales_vs_target': sales_vs_target,
            'warehouse_inventory': warehouse_inventory,
            'expenses': expenses_chart,
            'performance_radar': performance_radar,
            'sales_trend': sales_trend,
        }

    # ------------------------------------------------------------------
    # Main RPC Entrypoint
    # ------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self, filters=None):
        """
        Aggregate multi-pillar executive intelligence strictly from verified Odoo 20 tables:
        - Pillar A (Sales): alahram.branch.analytics (Oct 2026 baseline) + live pos.order + non-POS sale.order
        - Pillar B (Targets): alahram.branch.analytics.sales_target / account.report.budget.item (explicit unconfigured state if unset)
        - Pillar C (Inventory): stock.quant real internal balances & actual cost valuation (no selling-price fallback)
        - Pillar D (Expenses): posted account.move.line excluding purchase VAT, COGS & periodic storable stock purchases
        """
        filters = filters or {}
        company = self.env.company
        company_id = company.id

        selected_branch = (filters.get('branch_code') or '').strip() or None
        selected_wh_id = filters.get('warehouse_id')
        if selected_wh_id:
            try:
                selected_wh_id = int(selected_wh_id)
            except (ValueError, TypeError):
                selected_wh_id = None
        else:
            selected_wh_id = None

        date_ctx = self._resolve_date_bounds(filters)

        all_warehouses = self.env['stock.warehouse'].search([('company_id', '=', company_id)], order='name')
        wh_by_id = {w.id: w for w in all_warehouses}
        wh_by_code = {w.code: w for w in all_warehouses if w.code}

        all_branches = self.env['alahram.branch.analytics'].search([], order='net_sales_inc_vat desc')
        valid_branch_codes = {b.warehouse_code for b in all_branches if b.warehouse_code}

        # Synchronize warehouse filter -> inventory scope and branch scope consistently
        selected_wh_obj = wh_by_id.get(selected_wh_id) if selected_wh_id else None
        selected_wh_code = selected_wh_obj.code if selected_wh_obj else None

        if selected_wh_id:
            inv_wh_ids = {selected_wh_id}
        elif selected_branch and selected_branch in wh_by_code:
            inv_wh_ids = {wh_by_code[selected_branch].id}
        elif selected_branch:
            # Selected branch has no matching warehouse record
            inv_wh_ids = set()
        else:
            inv_wh_ids = None

        # Collect 4 Business Pillars
        sales_data = self._collect_sales_and_targets(
            company_id=company_id,
            date_ctx=date_ctx,
            all_branches=all_branches,
            all_warehouses=all_warehouses,
            selected_branch=selected_branch,
            selected_wh_code=selected_wh_code,
        )
        inv_data = self._collect_inventory_data(
            company_id=company_id,
            all_warehouses=all_warehouses,
            inv_wh_ids=inv_wh_ids,
            selected_branch=selected_branch,
            selected_wh_id=selected_wh_id,
        )
        effective_exp_code = selected_branch or selected_wh_code
        exp_data = self._collect_expenses_data(
            company_id=company_id,
            date_ctx=date_ctx,
            valid_branch_codes=valid_branch_codes,
            selected_branch=effective_exp_code,
        )

        all_sales_rows = sales_data['all_sales_rows']
        branch_rows = sales_data['branch_rows']

        # Build Unified Reconciliation Comparison Table
        wh_inv_by_code = inv_data['wh_stats_by_code']
        seen_wh_codes_in_table = set()
        comparison_rows = []

        for srow in all_sales_rows:
            code = srow['code']
            if code:
                seen_wh_codes_in_table.add(code)
            wh_stat = wh_inv_by_code.get(code)
            has_inv = bool(wh_stat and wh_stat['quant_lines'] > 0)
            on_hand = round(wh_stat['on_hand_qty'], 0) if wh_stat else 0.0
            reserved = round(wh_stat['reserved_qty'], 0) if wh_stat else 0.0
            available = round(wh_stat['available_qty'], 0) if wh_stat else 0.0
            valuation = round(wh_stat['valuation'], 2) if wh_stat else 0.0

            branch_opex = exp_data['expenses_by_branch'].get(code) if exp_data['is_allocated_by_branch'] else None
            exp_ratio = (
                round((branch_opex / srow['actual_sales_exc_vat']) * 100.0, 2)
                if (branch_opex is not None and srow['actual_sales_exc_vat'] > 0)
                else None
            )

            # Performance status strictly from verified indicators
            if srow['row_type'] == 'unmapped_channel':
                perf_status, status_label = 'unmapped', 'قناة مبيعات عامة'
            elif srow['return_rate'] > 20.0:
                perf_status, status_label = 'critical', 'مرتجعات مرتفعة'
            elif srow['has_target'] and srow['achievement_pct'] is not None:
                if srow['achievement_pct'] >= 100.0:
                    perf_status, status_label = 'excellent', 'حقق المستهدف'
                elif srow['achievement_pct'] >= 75.0:
                    perf_status, status_label = 'good', 'قريب من المستهدف'
                else:
                    perf_status, status_label = 'warning', 'دون المستهدف'
            elif srow.get('rank') == 1 and srow['actual_sales_inc_vat'] > 0:
                perf_status, status_label = 'excellent', 'المركز #1 مبيعات'
            elif srow['actual_sales_inc_vat'] > 0 and (srow['margin_pct'] or 0.0) >= 20.0:
                perf_status, status_label = 'good', 'أداء جيد'
            elif srow['actual_sales_inc_vat'] > 0:
                perf_status, status_label = 'normal', 'مستقر'
            else:
                perf_status, status_label = 'inactive', 'لا توجد مبيعات بالفترة'

            row_obj = dict(srow)
            row_obj.update({
                'on_hand_qty': on_hand,
                'reserved_qty': reserved,
                'available_qty': available,
                'inventory_valuation': valuation,
                'inventory_status': 'tracked' if has_inv else 'no_quants',
                'products_count': len(wh_stat['product_ids']) if wh_stat else 0,
                'operating_expenses': round(branch_opex, 2) if branch_opex is not None else None,
                'is_expense_allocated': exp_data['is_allocated_by_branch'] and branch_opex is not None,
                'expense_to_sales_pct': exp_ratio,
                'performance_status': perf_status,
                'status_label': status_label,
            })
            comparison_rows.append(row_obj)

        # Ensure any stocked warehouse with zero sales still appears in Comparison Table so Inventory Totals reconcile 100%
        for wh_item in inv_data['warehouses']:
            wcode = wh_item['code']
            if wcode and wcode not in seen_wh_codes_in_table and (wh_item['on_hand_qty'] != 0 or wh_item['reserved_qty'] != 0 or wh_item['valuation'] != 0):
                seen_wh_codes_in_table.add(wcode)
                comparison_rows.append({
                    'id': False,
                    'key': wcode,
                    'name': f"{wh_item['name']} (مستودع مخزني)",
                    'code': wcode,
                    'row_type': 'stock_only',
                    'warehouse_id': wh_item['id'],
                    'warehouse_name': wh_item['name'],
                    'net_sold_qty': 0,
                    'gross_sales': 0.0,
                    'discount_given': 0.0,
                    'discount_pct': 0.0,
                    'vat_14': 0.0,
                    'return_qty': 0,
                    'return_value': 0.0,
                    'return_rate': 0.0,
                    'baseline_sales_inc_vat': 0.0,
                    'baseline_sales_exc_vat': 0.0,
                    'live_pos_sales_inc_vat': 0.0,
                    'live_so_sales_inc_vat': 0.0,
                    'actual_sales_inc_vat': 0.0,
                    'actual_sales_exc_vat': 0.0,
                    'net_sales_inc_vat': 0.0,
                    'net_sales_exc_vat': 0.0,
                    'live_orders_count': 0,
                    'cogs': 0.0,
                    'profit': 0.0,
                    'has_verified_profit': False,
                    'margin_pct': None,
                    'sales_target': None,
                    'has_target': False,
                    'achievement_pct': None,
                    'remaining_target': None,
                    'target_status': 'مستودع فقط',
                    'rank': None,
                    'badge': 'normal',
                    'on_hand_qty': wh_item['on_hand_qty'],
                    'reserved_qty': wh_item['reserved_qty'],
                    'available_qty': wh_item['available_qty'],
                    'inventory_valuation': wh_item['valuation'],
                    'inventory_status': 'tracked' if wh_item['is_tracked'] else 'no_quants',
                    'products_count': wh_item['products_count'],
                    'operating_expenses': None,
                    'is_expense_allocated': False,
                    'expense_to_sales_pct': None,
                    'performance_status': 'stock_only',
                    'status_label': 'مخزني فقط',
                })

        # Consolidated Overview Totals (Strictly Reconciled to Comparison Rows)
        total_actual_inc = round(sum(r['actual_sales_inc_vat'] for r in comparison_rows), 2)
        total_actual_exc = round(sum(r['actual_sales_exc_vat'] for r in comparison_rows), 2)
        total_baseline_inc = round(sum(r['baseline_sales_inc_vat'] for r in comparison_rows), 2)
        total_live_pos_inc = round(sum(r['live_pos_sales_inc_vat'] for r in comparison_rows), 2)
        total_live_so_inc = round(sum(r['live_so_sales_inc_vat'] for r in comparison_rows), 2)
        total_gross = round(sum(r['gross_sales'] for r in comparison_rows), 2)
        total_discount = round(sum(r['discount_given'] for r in comparison_rows), 2)
        total_vat = round(sum(r['vat_14'] for r in comparison_rows), 2)
        total_ret_val = round(sum(r['return_value'] for r in comparison_rows), 2)
        total_ret_qty = sum(r['return_qty'] for r in comparison_rows)
        total_sold_qty = sum(r['net_sold_qty'] for r in comparison_rows)
        total_live_orders = sum(r['live_orders_count'] for r in comparison_rows)
        total_cogs = round(sum(r['cogs'] for r in comparison_rows), 2)
        total_profit = round(sum(r['profit'] for r in comparison_rows), 2)

        base_exc_sum = sum(r['baseline_sales_exc_vat'] for r in comparison_rows)
        overall_margin_pct = round((total_profit / base_exc_sum * 100.0), 1) if base_exc_sum > 0 else None
        overall_disc_pct = round((total_discount / total_gross * 100.0), 1) if total_gross > 0 else 0.0
        overall_ret_denom = abs(total_actual_inc) + abs(total_ret_val)
        overall_return_rate = round((abs(total_ret_val) / overall_ret_denom * 100.0), 2) if overall_ret_denom > 0 else 0.0

        # Targets Overview
        target_rows = [b for b in branch_rows if b['has_target']]
        configured_target_total = round(sum(b['sales_target'] for b in target_rows), 2) if target_rows else None
        actual_on_targeted_branches = sum(b['actual_sales_inc_vat'] for b in target_rows)
        if target_rows and configured_target_total:
            target_achievement_pct = round((total_actual_inc / configured_target_total * 100.0), 1)
            target_remaining = round(max(0.0, configured_target_total - total_actual_inc), 2)
            target_state = {
                'is_configured': True,
                'partial': len(target_rows) < len(branch_rows),
                'configured_count': len(target_rows),
                'total_branches': len(branch_rows),
                'total_target': configured_target_total,
                'achievement_pct': target_achievement_pct,
                'remaining_target': target_remaining,
                'targeted_actual_sales': round(actual_on_targeted_branches, 2),
                'label': f"{target_achievement_pct:.1f}%",
                'note': f"مهيأ لـ {len(target_rows)} من {len(branch_rows)} فرعاً",
            }
        else:
            target_state = {
                'is_configured': False,
                'partial': False,
                'configured_count': 0,
                'total_branches': len(branch_rows),
                'total_target': None,
                'achievement_pct': None,
                'remaining_target': None,
                'targeted_actual_sales': 0.0,
                'label': 'غير محدد في النظام',
                'note': 'Not Configured — لم يتم تسجيل مستهدفات شهرية للفروع في قاعدة البيانات',
            }

        total_expenses = exp_data['total_expenses']
        expense_to_sales_pct = round((total_expenses / total_actual_exc * 100.0), 2) if (total_actual_exc > 0 and total_expenses > 0) else 0.0
        branch_contribution = round(total_profit - total_expenses, 2) if base_exc_sum > 0 else None
        aov = round((total_live_pos_inc / total_live_orders), 2) if total_live_orders > 0 else 0.0

        top_branch = branch_rows[0] if branch_rows else None
        lowest_branch = branch_rows[-1] if branch_rows else None
        high_return_branches = [b for b in branch_rows if b['return_rate'] > 20.0]

        # Strategic Dynamic Alerts
        alerts = []
        if high_return_branches:
            names = '، '.join(f"{b['name']} ({b['return_rate']}%)" for b in high_return_branches)
            alerts.append({
                'type': 'danger',
                'title': 'نسبة مرتجعات مرتفعة تتجاوز الحدود الآمنة (> 20%)',
                'description': f"تم رصد ارتفاع غير طبيعي في نسب المرتجعات في: {names}. يتطلب مراجعة فورية لأسباب الاسترجاع وضبط الجودة.",
                'action_model': 'alahram.branch.analytics',
                'action_label': 'فحص تقرير المرتجعات',
            })

        if inv_data['dead_stock_value'] > 0:
            alerts.append({
                'type': 'warning',
                'title': 'رأس مال مجمد في بضاعة راكدة (Dead Stock)',
                'description': f"يوجد {len(inv_data['dead_stock_items'])} أصناف راكدة بكمية {int(inv_data['dead_stock_qty']):,} قطعة وتكلفة فعلية {inv_data['dead_stock_value']:,.2f} ج.م دون حركة مبيعات.",
                'action_model': 'product.template',
                'action_label': 'عرض الأصناف الراكدة',
            })

        if inv_data['cost_gt_list_sku_count'] > 0 or inv_data['zero_cost_sku_count'] > 0:
            alerts.append({
                'type': 'warning',
                'title': 'ملاحظة تدقيق تكلفة المخزون (Cost Integrity Audit)',
                'description': (
                    f"تم رصد {inv_data['cost_gt_list_sku_count']} صنفاً بالمخزون سعر تكلفته المسجل (standard_price) أعلى من سعر البيع الرسمي، "
                    f"و{inv_data['zero_cost_sku_count']} صنفاً بتكلفة صفرية. لم يتم استبدالها بسعر البيع حفظاً لدقة البيانات."
                ),
                'action_model': 'stock.quant',
                'action_label': 'مراجعة أرصدة وتكاليف المخزون',
            })

        high_discount_branches = [b for b in branch_rows if b['discount_given'] > 300000.0]
        if high_discount_branches:
            names = '، '.join(f"{b['name']} ({b['discount_given']:,.0f} ج.م)" for b in high_discount_branches)
            alerts.append({
                'type': 'warning',
                'title': 'ارتفاع قيمة الخصومات الممنوحة بالمعارض',
                'description': f"بلغت الخصومات الممنوحة في {names} مستويات تتطلب حوكمة ومراجعة صلاحيات الخصم فوق 5%.",
                'action_model': 'pos.order',
                'action_label': 'مراجعة طلبات نقاط البيع',
            })

        if top_branch and top_branch['actual_sales_inc_vat'] > 0:
            alerts.append({
                'type': 'success',
                'title': 'الفرع الأعلى أداءً ومبيعات',
                'description': f"يتصدر {top_branch['name']} المبيعات بإجمالي {top_branch['actual_sales_inc_vat']:,.2f} ج.م ونسبة مرتجع {top_branch['return_rate']}%.",
                'action_model': 'alahram.branch.analytics',
                'action_res_id': top_branch['id'],
                'action_label': 'بيان أداء الفرع',
            })

        if inv_data['recommendations']:
            alerts.append({
                'type': 'info',
                'title': 'توصيات نقل وتوازن المخزون بين الفروع',
                'description': f"تتوفر {len(inv_data['recommendations'])} توصية نقل مقترحة لتعويض النواقص وتدوير المخزون من المستودعات ذات الفائض.",
                'action_model': 'alahram.stock.recommendation',
                'action_label': 'مراجعة التوصيات',
            })

        if not target_state['is_configured']:
            alerts.append({
                'type': 'secondary',
                'title': 'مصدر بيانات مفقود: المستهدف البيعي للفروع (Sales Targets)',
                'description': 'لم يتم تحديد مستهدفات مبيعات في جدول تحليلات الفروع أو الموازنات. يمكنك إدخال المستهدف الشهري لكل فرع مباشرة من تقرير تحليلات الفروع.',
                'action_model': 'alahram.branch.analytics',
                'action_label': 'تحديد المستهدفات الآن',
            })

        if not exp_data['is_allocated_by_branch']:
            alerts.append({
                'type': 'secondary',
                'title': 'مصدر بيانات مفقود: مراكز التكلفة التحليلية للفروع (Analytic Allocation)',
                'description': exp_data['allocation_note'] + (
                    f" كما تم استبعاد {exp_data['excluded_purchases_total']:,.2f} ج.م فواتير مشتريات بضاعة/مخزون دورية من المصروفات التشغيلية."
                    if exp_data['excluded_purchases_total'] > 0 else ""
                ),
                'action_model': 'account.move',
                'action_label': 'مراجعة الفواتير والقيود',
            })

        overview = {
            'gross_sales': total_gross,
            'discount_given': total_discount,
            'discount_pct': overall_disc_pct,
            'vat_14': total_vat,
            'return_value': total_ret_val,
            'return_qty': total_ret_qty,
            'return_rate_pct': overall_return_rate,
            'sold_qty': total_sold_qty,
            'actual_sales_inc_vat': total_actual_inc,
            'actual_sales_exc_vat': total_actual_exc,
            'net_sales_inc_vat': total_actual_inc,
            'net_sales_exc_vat': total_actual_exc,
            'baseline_sales_inc_vat': total_baseline_inc,
            'live_pos_sales_inc_vat': total_live_pos_inc,
            'live_so_sales_inc_vat': total_live_so_inc,
            'cogs': total_cogs,
            'gross_profit': total_profit,
            'has_verified_profit': base_exc_sum > 0,
            'gross_margin_pct': overall_margin_pct,
            'operating_expenses': total_expenses,
            'company_operating_expenses': exp_data['company_total_expenses'],
            'branch_contribution': branch_contribution,
            'expense_to_sales_pct': expense_to_sales_pct,
            'target_achievement': target_state,
            'inventory_valuation': round(sum(r['inventory_valuation'] for r in comparison_rows), 2),
            'total_stock_qty': round(sum(r['on_hand_qty'] for r in comparison_rows), 0),
            'total_reserved_qty': round(sum(r['reserved_qty'] for r in comparison_rows), 0),
            'total_available_qty': round(sum(r['available_qty'] for r in comparison_rows), 0),
            'tracked_warehouses_count': inv_data['tracked_warehouses_count'],
            'total_warehouses_count': inv_data['total_warehouses_count'],
            'dead_stock_value': inv_data['dead_stock_value'],
            'dead_stock_qty': inv_data['dead_stock_qty'],
            'critical_alerts_count': len([a for a in alerts if a['type'] in ['danger', 'warning']]),
            'live_pos_orders_count': total_live_orders,
            'live_pos_sales_total': round(total_live_pos_inc, 2),
            'aov': aov,
        }

        charts = self._build_charts_payload(sales_data, inv_data, exp_data, overview, selected_branch)

        warehouse_options = [{'id': w.id, 'name': w.name, 'code': w.code} for w in all_warehouses]
        branch_options = [{'code': b.warehouse_code, 'name': b.branch_name} for b in all_branches if b.warehouse_code]

        now_local_str = datetime.now(pytz.UTC).astimezone(date_ctx['user_tz']).strftime('%Y-%m-%d %H:%M:%S')

        return {
            'overview': overview,
            'charts': charts,
            'comparison_rows': comparison_rows,
            'branch_performance': {
                'rows': branch_rows,
                'top_branch': top_branch,
                'lowest_branch': lowest_branch,
                'high_return_branches': [
                    {'code': b['code'], 'name': b['name'], 'return_rate': b['return_rate']}
                    for b in high_return_branches
                ],
            },
            'inventory_intelligence': {
                'warehouses': inv_data['warehouses'],
                'dead_stock_items': inv_data['dead_stock_items'],
                'recommendations': inv_data['recommendations'],
                'snapshot_note': 'أرصدة المخزون تعكس اللقطة اللحظية الفعلية الحالية (Real-time stock.quant Snapshot).',
            },
            'financial_performance': {
                'has_access': exp_data['has_access'],
                'total_expenses': exp_data['total_expenses'],
                'company_total_expenses': exp_data['company_total_expenses'],
                'allocated_expenses': exp_data['allocated_expenses'],
                'unallocated_expenses': exp_data['unallocated_expenses'],
                'expense_to_sales_pct': expense_to_sales_pct,
                'branch_contribution': branch_contribution,
                'expense_categories': exp_data['expense_categories'],
                'expense_items': exp_data['expense_items'],
                'excluded_purchases_total': exp_data['excluded_purchases_total'],
                'excluded_tax_total': exp_data['excluded_tax_total'],
                'excluded_items': exp_data['excluded_items'],
                'is_allocated_by_branch': exp_data['is_allocated_by_branch'],
                'allocation_note': exp_data['allocation_note'],
                'previous_period': exp_data['previous_period'],
                'hr_expense_installed': exp_data['hr_expense_installed'],
                'hr_expense_count': exp_data['hr_expense_count'],
            },
            'business_alerts': alerts,
            'data_integrity': {
                'last_updated_at': now_local_str,
                'company_name': company.name,
                'company_currency': company.currency_id.name,
                'display_currency': 'EGP',
                'baseline_included': date_ctx['include_oct_baseline'],
                'baseline_period_label': 'أكتوبر 2026 (1–28 أكتوبر)',
                'dedup_excluded_so_count': sales_data['dedup_excluded_so_count'],
                'zero_cost_sku_count': inv_data['zero_cost_sku_count'],
                'cost_gt_list_sku_count': inv_data['cost_gt_list_sku_count'],
                'untracked_branches_count': len([r for r in branch_rows if r['code'] not in inv_data['wh_stats_by_code'] or inv_data['wh_stats_by_code'][r['code']]['quant_lines'] == 0]),
                'missing_sources': [
                    m for m in [
                        None if target_state['is_configured'] else 'المستهدف البيعي للفروع (Sales Targets)',
                        None if exp_data['is_allocated_by_branch'] else 'توزيع المصروفات التحليلية للفروع (Analytic Allocation)',
                        None if inv_data['stocked_warehouses_global_count'] >= len(branch_rows) else f"أرصدة المخزون لـ {len(branch_rows) - len([b for b in branch_rows if b['code'] in inv_data['wh_stats_by_code'] and inv_data['wh_stats_by_code'][b['code']]['quant_lines'] > 0])} فروع لم تُحمَّل في stock.quant",
                    ] if m
                ],
            },
            'filters_metadata': {
                'branches': branch_options,
                'warehouses': warehouse_options,
                'selected_branch': selected_branch or '',
                'selected_warehouse_id': selected_wh_id or '',
                'period_preset': date_ctx['preset'],
                'date_from': date_ctx['date_from_str'],
                'date_to': date_ctx['date_to_str'],
            },
        }
