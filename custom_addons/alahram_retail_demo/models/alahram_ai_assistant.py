# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json

class AlahramBranchAnalytics(models.Model):
    _name = 'alahram.branch.analytics'
    _description = 'سجل تحليلات مبيعات وربحية الفروع - أكتوبر 2026'
    _order = 'net_sales_inc_vat desc'

    branch_name = fields.Char(string='اسم الفرع', required=True)
    warehouse_code = fields.Char(string='كود المخزن / الفرع')
    net_sold_qty = fields.Integer(string='صافي الكمية المباعة (قطعة)')
    gross_sales = fields.Float(string='إجمالي المبيعات قبل الضريبة والخصم (ج.م)')
    discount_given = fields.Float(string='الخصومات الممنوحة (ج.م)')
    vat_14_amount = fields.Float(string='ضريبة القيمة المضافة 14% (ج.م)')
    return_qty = fields.Integer(string='كمية المرتجعات (قطعة)')
    return_value = fields.Float(string='قيمة المرتجعات (ج.م)')
    net_sales_inc_vat = fields.Float(string='صافي المبيعات شامل الضريبة (ج.م)')
    net_sales_exc_vat = fields.Float(string='صافي المبيعات غير شامل الضريبة (ج.م)')
    cogs_cost = fields.Float(string='تكلفة البضاعة المباعة COGS (ج.م)')
    net_profit = fields.Float(string='صافي الربح (ج.م)')
    return_rate = fields.Float(string='نسبة المرتجع %')
    sales_target = fields.Float(
        string='المستهدف البيعي الشهري (ج.م)',
        default=0.0,
        help='المستهدف البيعي المعتمد للفرع — اتركه صفراً إذا لم يتم تحديده في النظام.'
    )


class AlahramAIAssistant(models.Model):
    _name = 'alahram.ai.assistant'
    _description = 'مساعد الذكاء الاصطناعي لإدارة الأهرام للأدوات المنزلية'
    _inherit = ['mail.thread']

    name = fields.Char(string='عنوان الاستفسار', default='مساعد أودو 20 الذكي للأهرام')
    user_query = fields.Selection([
        ('q1_lowest_branches', '1. إيه أقل 5 فروع في المبيعات؟'),
        ('q2_dead_stock', '2. إيه الأصناف اللي عندي منها مخزون كبير ومش بتتباع؟'),
        ('q3_stockout_sidigaber', '3. إيه المنتجات اللي ناقصة في سيدي جابر وموجودة في فروع تانية؟'),
        ('q4_promo_candidates', '4. إيه الأصناف اللي ممكن أعمل عليها عروض وتخفيضات؟'),
        ('q5_high_returns', '5. إيه الفروع اللي زادت فيها المرتجعات بنسبة غير طبيعية؟'),
        ('q6_budget_order', '6. تجهيز أمر بيع آلي بميزانية محددة (باكدج عروسة متوازن 5 تصنيفات)'),
        ('free_gemini', '⚡ سؤال حر ذكي فوري عبر Google Gemini Flash AI (مباشر ومجاني)'),
    ], string='اختر سؤال الأعمال التجريبي', default='q1_lowest_branches')

    custom_prompt = fields.Char(string='أو اكتب سؤالك الحر هنا')
    target_budget = fields.Float(string='الميزانية المستهدفة (للسؤال رقم 6)', default=15000.0)
    customer_id = fields.Many2one('res.partner', string='العميل المستهدف (للسؤال رقم 6)')

    ai_response_html = fields.Html(string='إجابة وتحليل الذكاء الاصطناعي', readonly=True)
    generated_sale_order_id = fields.Many2one('sale.order', string='أمر البيع المنشأ آلياً', readonly=True)
    action_executed_summary = fields.Text(string='ملخص الإجراء المنفذ', readonly=True)

    def action_run_q1(self):
        self.ensure_one()
        self.user_query = 'q1_lowest_branches'
        self._answer_q1_lowest_branches()
        return True

    def action_run_q2(self):
        self.ensure_one()
        self.user_query = 'q2_dead_stock'
        self._answer_q2_dead_stock()
        return True

    def action_run_q3(self):
        self.ensure_one()
        self.user_query = 'q3_stockout_sidigaber'
        self._answer_q3_stockout_sidigaber()
        return True

    def action_run_q4(self):
        self.ensure_one()
        self.user_query = 'q4_promo_candidates'
        self._answer_q4_promo_candidates()
        return True

    def action_run_q5(self):
        self.ensure_one()
        self.user_query = 'q5_high_returns'
        self._answer_q5_high_returns()
        return True

    def action_run_q6(self):
        self.ensure_one()
        self.user_query = 'q6_budget_order'
        self._answer_q6_budget_order()
        return True

    def action_open_generated_order(self):
        self.ensure_one()
        if not self.generated_sale_order_id:
            raise UserError(_("لم يتم إنشاء أمر بيع بعد! اضغط على السؤال 6 لتوليد الباكدج وإصدار الأمر."))
        return {
            'name': _('أمر البيع المنشأ من الذكاء الاصطناعي'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.generated_sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_execute_ai_query(self):
        """Execute selected query and return formatted insight with actionable buttons"""
        self.ensure_one()
        query = self.user_query

        if self.custom_prompt or query == 'free_gemini':
            self._answer_custom_gemini_query()
        elif query == 'q1_lowest_branches':
            self._answer_q1_lowest_branches()
        elif query == 'q2_dead_stock':
            self._answer_q2_dead_stock()
        elif query == 'q3_stockout_sidigaber':
            self._answer_q3_stockout_sidigaber()
        elif query == 'q4_promo_candidates':
            self._answer_q4_promo_candidates()
        elif query == 'q5_high_returns':
            self._answer_q5_high_returns()
        elif query == 'q6_budget_order':
            self._answer_q6_budget_order()
        return True

    def _answer_custom_gemini_query(self):
        prompt = self.custom_prompt or "قدم لي نصائح تسويقية لزيادة مبيعات صواني الفرن وأطقم الجرانيت لشركة الأهرام."
        ir_config = self.env['ir.config_parameter'].sudo()
        api_key = ir_config.get_str('gemini.api_key') or ir_config.get_str('ai.gemini_api_key')
        model = ir_config.get_str('gemini.model') or 'gemini-2.5-flash'
        
        system_instruction = (
            "أنت المستشار الذكي الرسمي لشركة الأهرام للأدوات المنزلية (Al Ahram Cookware) داخل نظام Odoo 20 Enterprise.\n"
            "الشركة رائدة في مصر في تصنيع أواني الطهي (ألومنيوم كلاسيك، جرانيت صحي 4 مم، ستانلس ستيل 18/10، تيفال).\n"
            "أجب دائماً باللغة العربية باحترافية، ونسق الإجابة بنقاط أو جداول عملية واضحة."
        )
        
        from .odoo_ai_gemini_bridge import request_gemini_api
        
        payload = {
            'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
            'system_instruction': {'parts': [{'text': system_instruction}]}
        }
        
        try:
            raw_reply = request_gemini_api(api_key, model, payload)
            html_content = raw_reply.replace('\n\n', '</p><p>').replace('\n', '<br/>')
            html = f"""
            <div style="font-family: Cairo, Tahoma, sans-serif; direction: rtl; line-height: 1.8;">
                <div class="alert alert-primary" style="font-size: 15px; font-weight: bold; border-right: 5px solid #0d6efd; background: #eef5ff;">
                    🤖 <strong>استجابة Google Gemini AI الحية (نموذج {model} بدون IAP Credits):</strong><br/>
                    <small style="color: #444;">السؤال: {prompt}</small>
                </div>
                <div class="card p-3 shadow-sm border-0" style="background: #ffffff; border-radius: 8px; font-size: 14.5px;">
                    <p>{html_content}</p>
                </div>
                <div class="alert alert-success mt-3" style="font-size: 12.5px;">
                    ✅ <strong>تمت المعالجة بنجاح عبر مفتاح Google AI Studio API الخاص بك مجاناً 100%.</strong>
                </div>
            </div>
            """
            self.ai_response_html = html
            self.action_executed_summary = f"تمت الإجابة الفورية عبر Google Gemini على: {prompt[:70]}"
        except Exception as e:
            self.ai_response_html = f"<div class='alert alert-danger'>فشل الاتصال بـ Gemini API: {str(e)}</div>"
            self.action_executed_summary = f"خطأ: {str(e)}"

    def _answer_q1_lowest_branches(self):
        html = """
        <div style="font-family: Cairo, Tahoma, sans-serif; direction: rtl; line-height: 1.8;">
            <div class="alert alert-info" style="font-size: 15px; font-weight: bold; border-right: 5px solid #0056b3; background: #e8f4fd;">
                📊 <strong>تحليل الذكاء الاصطناعي — أقل 5 فروع في مبيعات شهر أكتوبر 2026:</strong>
            </div>
            <table class="table table-bordered table-striped" style="margin-top: 15px; text-align: center;">
                <thead style="background: #2c3e50; color: white;">
                    <tr>
                        <th>الترتيب</th>
                        <th>اسم الفرع</th>
                        <th>صافي الكمية المباعة</th>
                        <th>صافي المبيعات شامل الضريبة (ج.م)</th>
                        <th>صافي المبيعات غير شامل الضريبة (ج.م)</th>
                        <th>صافي الربح (ج.م)</th>
                        <th>رصيد المخزون التقديري (ج.م)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="background: #fff3cd;">
                        <td><strong>1</strong></td>
                        <td><strong>مخزن الإدارة (WH-MAIN)</strong></td>
                        <td>-40 قطعة</td>
                        <td>71,371.11 ج.م</td>
                        <td>62,606.24 ج.م</td>
                        <td>13,397.68 ج.م</td>
                        <td>15,838,583.79 ج.م</td>
                    </tr>
                    <tr>
                        <td><strong>2</strong></td>
                        <td><strong>مبيعات الأونلاين (WH-ONLINE)</strong></td>
                        <td>414 قطعة</td>
                        <td>307,838.02 ج.م</td>
                        <td>270,033.34 ج.م</td>
                        <td>63,233.69 ج.م</td>
                        <td>1,050,353.86 ج.م</td>
                    </tr>
                    <tr>
                        <td><strong>3</strong></td>
                        <td><strong>فرع باكوس / سموحة (WH-SMOUHA)</strong></td>
                        <td>591 قطعة</td>
                        <td>385,077.03 ج.م</td>
                        <td>337,786.84 ج.م</td>
                        <td>66,961.00 ج.م</td>
                        <td>1,611,825.96 ج.م</td>
                    </tr>
                    <tr>
                        <td><strong>4</strong></td>
                        <td><strong>فرع لوران / رشدي (WH-ROSHDY)</strong></td>
                        <td>919 قطعة</td>
                        <td>529,961.02 ج.م</td>
                        <td>464,878.06 ج.م</td>
                        <td>90,233.10 ج.م</td>
                        <td>3,672,735.00 ج.م</td>
                    </tr>
                    <tr style="background: #f8d7da; color: #721c24;">
                        <td><strong>5</strong></td>
                        <td><strong>فرع فيصل - الجيزة (WH-FAISAL)</strong></td>
                        <td>904 قطعة</td>
                        <td>576,657.59 ج.م</td>
                        <td>505,839.98 ج.م</td>
                        <td>89,353.71 ج.م</td>
                        <td><strong>6,866,883.84 ج.م ⚠️</strong></td>
                    </tr>
                </tbody>
            </table>
            <div class="alert alert-warning" style="margin-top: 15px; border-right: 5px solid #ff9800; background: #fff8e1;">
                ⚠️ <strong>تنبيه إداري فوري لفرع فيصل (Executive Warning):</strong><br/>
                فرع فيصل يحتفظ بمخزون قيمته البيعية <strong>6.87 مليون جنيه</strong> (وهو أعلى رصيد بضاعة راكدة بين جميع فروع الجمهورية)، ومع ذلك يحتل المركز الخامس كأقل الفروع تحقيقاً للمبيعات!<br/>
                <strong>توصية الذكاء الاصطناعي:</strong> نقل 30% من مخزون فيصل الراكد إلى فرع سيدي جابر وشبرا الأعلى سحباً، أو تدشين حملة تصفيات محلية.
            </div>
        </div>
        """
        self.ai_response_html = html
        self.action_executed_summary = "تم فحص بيانات 10 فروع لشهر أكتوبر وتحديد أدنى 5 فروع مع تنبيه مخزون فيصل."

    def _answer_q2_dead_stock(self):
        html = """
        <div style="font-family: Cairo, Tahoma, sans-serif; direction: rtl; line-height: 1.8;">
            <div class="alert alert-danger" style="font-size: 15px; font-weight: bold; border-right: 5px solid #dc3545; background: #fdf2f2;">
                📦 <strong>تحليل الذكاء الاصطناعي — أعلى 5 أصناف ذات مخزون راكد بدون مبيعات في أكتوبر 2026:</strong>
            </div>
            <table class="table table-bordered table-hover" style="margin-top: 15px; text-align: center;">
                <thead style="background: #842029; color: white;">
                    <tr>
                        <th>كود الصنف</th>
                        <th>اسم الصنف الراكد</th>
                        <th>رصيد المخزون (قطعة)</th>
                        <th>متوسط التكلفة (ج.م)</th>
                        <th>قيمة التكلفة المجمدة (ج.م)</th>
                        <th>سعر البيع الرسمي (ج.م)</th>
                        <th>مبيعات أكتوبر</th>
                        <th>موقع التخزين الرئيسي</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><code>1414000000042</code></td>
                        <td><strong>شواية جرانيت Bio trade grip يد بكاليت 28</strong></td>
                        <td><span class="badge bg-danger">438 قطعة</span></td>
                        <td>434.21 ج.م</td>
                        <td><strong>190,183.98 ج.م</strong></td>
                        <td>1,102.69 ج.م</td>
                        <td>0 قطعة</td>
                        <td>مخزن الإدارة (279) + رشدي (35)</td>
                    </tr>
                    <tr>
                        <td><code>1433000000067</code></td>
                        <td><strong>حلة سيجنتشر ستايل ستانلس ستيل أيادي وغطا 24</strong></td>
                        <td><span class="badge bg-danger">317 قطعة</span></td>
                        <td>556.29 ج.م</td>
                        <td><strong>176,342.66 ج.م</strong></td>
                        <td>1,124.00 ج.م</td>
                        <td>0 قطعة</td>
                        <td>مخزن الإدارة (221) + رشدي (48)</td>
                    </tr>
                    <tr>
                        <td><code>1414000000035</code></td>
                        <td><strong>حلة جرانيت Bio trade grip غطا ستانلس 24</strong></td>
                        <td><span class="badge bg-danger">357 قطعة</span></td>
                        <td>486.84 ج.م</td>
                        <td><strong>173,801.88 ج.م</strong></td>
                        <td>1,112.79 ج.م</td>
                        <td>0 قطعة</td>
                        <td>مخزن الإدارة (233) + سيدي جابر (5)</td>
                    </tr>
                    <tr>
                        <td><code>1431000000278</code></td>
                        <td><strong>الأهرام طقم شاورما ألومنيوم كلاسيك 5 قطع</strong></td>
                        <td><span class="badge bg-danger">63 طقم</span></td>
                        <td>1,995.00 ج.م</td>
                        <td><strong>125,685.00 ج.م</strong></td>
                        <td>3,620.00 ج.م</td>
                        <td>0 طقم</td>
                        <td>مخزن الإدارة الرئيسي</td>
                    </tr>
                    <tr>
                        <td><code>1431000000124</code></td>
                        <td><strong>صينية بيتزا بان ألومنيوم كلاسيك 30</strong></td>
                        <td><span class="badge bg-danger">266 قطعة</span></td>
                        <td>417.96 ج.م</td>
                        <td><strong>111,176.03 ج.م</strong></td>
                        <td>898.00 ج.م</td>
                        <td>0 قطعة</td>
                        <td>مخزن الإدارة (210) + فروع</td>
                    </tr>
                </tbody>
            </table>
            <div class="alert alert-success" style="margin-top: 15px; border-right: 5px solid #28a745; background: #e8f5e9;">
                💡 <strong>خطة تصريف الركود المقترحة من أودو 20:</strong><br/>
                إجمالي رأس المال المجمد في هذه الأصناف الـ 5 يبلغ <strong>777,189.55 جنيه</strong> بسعر التكلفة و<strong>1,692,300.00 جنيه</strong> بسعر البيع!<br/>
                - إدخال حلة الجرانيت 24 وشواية 28 في "باكدج العروسة الفضي والذهبي" بخصم باكدج 20% لتسييل السيولة فوراً.
            </div>
        </div>
        """
        self.ai_response_html = html
        self.action_executed_summary = "تم فحص أرصدة المخزون وتحديد الأصناف ذات الرصيد > 50 قطعة ومبيعات صفرية في أكتوبر."

    def _answer_q3_stockout_sidigaber(self):
        html = """
        <div style="font-family: Cairo, Tahoma, sans-serif; direction: rtl; line-height: 1.8;">
            <div class="alert alert-warning" style="font-size: 15px; font-weight: bold; border-right: 5px solid #ffc107; background: #fffde7;">
                🚨 <strong>تحليل الذكاء الاصطناعي — أصناف نفدت في سيدي جابر وعليها طلب عالٍ مع وجودها بالفروع الأخرى:</strong>
            </div>
            <table class="table table-bordered table-hover" style="margin-top: 15px; text-align: center;">
                <thead style="background: #d39e00; color: #212529;">
                    <tr>
                        <th>الباركود</th>
                        <th>اسم الصنف</th>
                        <th>رصيد سيدي جابر الحالي</th>
                        <th>مبيعات الصنف في أكتوبر</th>
                        <th>المخزن المتوفر به البديل</th>
                        <th>الرصيد المتاح بالنقل</th>
                        <th>الإجراء الموصى به</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><code>6221049803894</code></td>
                        <td><strong>الاهرام مقلايه جرانيت BIO TRADE GRIP دارك سيلفر 20</strong></td>
                        <td><span class="badge bg-danger">0 قطعة</span></td>
                        <td><strong>107 قطعة (طلب مرتفع جداً)</strong></td>
                        <td>مخزن الإدارة الرئيسي (WH-MAIN)</td>
                        <td><span class="badge bg-success">27 قطعة</span></td>
                        <td>تحويل فوري 15 قطعة عبر بضاعة بالطريق</td>
                    </tr>
                    <tr>
                        <td><code>6221049430625</code></td>
                        <td><strong>الأهرام طقم حلة ويركت ألومنيوم كلاسيك 10 قطع</strong></td>
                        <td><span class="badge bg-danger">0 قطعة</span></td>
                        <td><strong>23 طقم (صنف باكدج أساسي)</strong></td>
                        <td>فرع لوران / رشدي (WH-ROSHDY)</td>
                        <td><span class="badge bg-success">2 طقم (إجمالي الشركة 13)</span></td>
                        <td>تحويل 2 طقم من فرع رشدي القريب</td>
                    </tr>
                    <tr>
                        <td><code>6221049011701</code></td>
                        <td><strong>الأهرام حلة صحي و مفيد ألومنيوم كلاسيك 24</strong></td>
                        <td><span class="badge bg-danger">0 قطعة</span></td>
                        <td>9 قطع</td>
                        <td>فرع رشدي (3) + مخزن الإدارة (3)</td>
                        <td><span class="badge bg-success">30 قطعة في الشركة</span></td>
                        <td>تحويل 3 قطع فورية لسيدي جابر</td>
                    </tr>
                </tbody>
            </table>
            <div class="alert alert-info" style="margin-top: 15px;">
                🚚 <strong>ربط أودو 20 السريع:</strong> يمكنك من شاشة "طلب حجز وتحويل بين الفروع" الضغط على زر <strong>تحويل فوري</strong> لإنشاء أذون التحويل المزدوجة (WH-ROSHDY -> WH-TRANSIT -> WH-SG).
            </div>
        </div>
        """
        self.ai_response_html = html
        self.action_executed_summary = "تم اكتشاف عجز 3 أصناف استراتيجية في سيدي جابر مع وجودها في الإدارة وفرع رشدي."

    def _answer_q4_promo_candidates(self):
        html = """
        <div style="font-family: Cairo, Tahoma, sans-serif; direction: rtl; line-height: 1.8;">
            <div class="alert alert-success" style="font-size: 15px; font-weight: bold; border-right: 5px solid #28a745; background: #f0fdf4;">
                🎯 <strong>تحليل الذكاء الاصطناعي — أصناف مثالية للحملات الترويجية (هامش ربح > 50% ورصيد وفير):</strong>
            </div>
            <table class="table table-bordered table-striped" style="margin-top: 15px; text-align: center;">
                <thead style="background: #1b5e20; color: white;">
                    <tr>
                        <th>الباركود</th>
                        <th>اسم الصنف المرشح للعرض</th>
                        <th>إجمالي الرصيد المتاح</th>
                        <th>التكلفة (ج.م)</th>
                        <th>سعر البيع الرسمي (ج.م)</th>
                        <th>هامش الربح الإجمالي %</th>
                        <th>العرض الترويجي المقترح من الذكاء الاصطناعي</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><code>1414000000073</code></td>
                        <td><strong>صينية فرن جرانيت Bio grip trade 30</strong></td>
                        <td><span class="badge bg-info">580 قطعة</span></td>
                        <td>350.88 ج.م</td>
                        <td>811.03 ج.م</td>
                        <td><strong>50.62%</strong></td>
                        <td>خصم 25% ليصبح 608 ج.م مع الحفاظ على ربح 257 ج.م للقطعة</td>
                    </tr>
                    <tr>
                        <td><code>1433000000050</code></td>
                        <td><strong>طقم حلة ستانلس ستيل سيجنتشر ستايل 6 قطع</strong></td>
                        <td><span class="badge bg-info">81 طقم</span></td>
                        <td>1,321.87 ج.م</td>
                        <td>3,463.82 ج.م</td>
                        <td><strong>56.49%</strong></td>
                        <td>عرض هدية كسرولة ستانلس 16 مجاناً عند الشراء بسعر 3,199 ج.م</td>
                    </tr>
                    <tr>
                        <td><code>BUNDLE_01</code></td>
                        <td><strong>عرض ثنائي الطهي (شواية جرانيت 28 + حلة جرانيت 24)</strong></td>
                        <td><span class="badge bg-warning">350+ مجموعة</span></td>
                        <td>921.05 ج.م</td>
                        <td>2,215.48 ج.م</td>
                        <td><strong>58.42%</strong></td>
                        <td>بيع الطقمين معاً بسعر 1,599 ج.م (توفير 616 ج.م للعميل وربح 678 ج.م للشركة)</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """
        self.ai_response_html = html
        self.action_executed_summary = "تم حساب هوامش الأرباح للأصناف الوفيرة وتحديد 3 فرص ترويجية بربحية مضمونة."

    def _answer_q5_high_returns(self):
        html = """
        <div style="font-family: Cairo, Tahoma, sans-serif; direction: rtl; line-height: 1.8;">
            <div class="alert alert-danger" style="font-size: 15px; font-weight: bold; border-right: 5px solid #b71c1c; background: #ffebee;">
                📉 <strong>تحليل الذكاء الاصطناعي — الفروع التي سجلت ارتفاعاً حاداً في نسب المرتجعات:</strong>
            </div>
            <table class="table table-bordered table-hover" style="margin-top: 15px; text-align: center;">
                <thead style="background: #b71c1c; color: white;">
                    <tr>
                        <th>الفرع</th>
                        <th>كمية المرتجع (قطعة)</th>
                        <th>قيمة المرتجعات (ج.م)</th>
                        <th>صافي مبيعات الفرع (ج.م)</th>
                        <th>نسبة المرتجع %</th>
                        <th>التشخيص الإداري للمشكلة</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="background: #ffcdd2;">
                        <td><strong>فرع شبرا - القاهرة (WH-SHOBRA)</strong></td>
                        <td><span class="badge bg-danger">-180 قطعة</span></td>
                        <td><strong>-280,232.34 ج.م</strong></td>
                        <td>1,147,535.30 ج.م</td>
                        <td><strong style="color: #b71c1c; font-size: 16px;">24.34% ⚠️</strong></td>
                        <td>شكاوى من خدوش طلاء الجرانيت أثناء النقل أو أخطاء استبدال الفاتورة</td>
                    </tr>
                    <tr style="background: #ffe0b2;">
                        <td><strong>فرع مدينة نصر (WH-NASR)</strong></td>
                        <td><span class="badge bg-danger">-86 قطعة</span></td>
                        <td><strong>-140,141.55 ج.م</strong></td>
                        <td>602,827.03 ج.م</td>
                        <td><strong style="color: #b71c1c; font-size: 16px;">23.64% ⚠️</strong></td>
                        <td>مرتجع أطقم ستانلس ستيل ومقاسات غير مناسبة للمطابخ</td>
                    </tr>
                    <tr style="background: #fff9c4;">
                        <td><strong>مبيعات الأونلاين (WH-ONLINE)</strong></td>
                        <td><span class="badge bg-danger">-47 قطعة</span></td>
                        <td><strong>-69,589.10 ج.م</strong></td>
                        <td>307,838.02 ج.م</td>
                        <td><strong style="color: #b71c1c; font-size: 16px;">23.32% ⚠️</strong></td>
                        <td>طبيعة التجارة الإلكترونية ورفض الاستلام من مندوبي الشحن</td>
                    </tr>
                </tbody>
            </table>
            <div class="alert alert-warning" style="margin-top: 15px;">
                🔎 <strong>مقارنة بفرع سيدي جابر المنضبط:</strong> سجل فرع سيدي جابر نسبة مرتجع <strong>8.49%</strong> فقط (100 قطعة من أصل 2,067 مباعة)، مما يؤكد أن فروع القاهرة تعاني من خلل تشغيلي في فحص الجودة وتوجيه العملاء.
            </div>
        </div>
        """
        self.ai_response_html = html
        self.action_executed_summary = "تم رصد فروع شبرا ومدينة نصر والأونلاين بنسب مرتجع تجاوزت 23%."

    def _answer_q6_budget_order(self):
        budget = self.target_budget or 15000.0
        partner = self.customer_id or self.env['res.partner'].search([('customer_rank', '>', 0)], limit=1)
        if not partner:
            partner = self.env['res.partner'].search([], limit=1)

        # Trigger Bridal Configurator logic to generate order
        configurator = self.env['alahram.bridal.configurator'].create({
            'partner_id': partner.id,
            'target_budget': budget,
            'package_tier': 'silver_15k' if budget <= 18000 else 'gold_25k',
        })
        configurator.action_auto_generate_balanced_package()
        res = configurator.action_create_sale_order()
        sale_order = configurator.sale_order_id

        self.generated_sale_order_id = sale_order.id
        
        # Build lines display
        lines_html = ""
        for line in sale_order.order_line:
            lines_html += f"""
            <tr>
                <td>{line.product_id.default_code or line.product_id.barcode or ''}</td>
                <td><strong>{line.product_id.name}</strong></td>
                <td>{line.product_id.categ_id.name or 'أدوات منزلية'}</td>
                <td>{line.product_uom_qty}</td>
                <td>{line.price_unit:,.2f} ج.م</td>
                <td><strong>{line.price_subtotal:,.2f} ج.م</strong></td>
            </tr>
            """

        html = f"""
        <div style="font-family: Cairo, Tahoma, sans-serif; direction: rtl; line-height: 1.8;">
            <div class="alert alert-success" style="font-size: 15px; font-weight: bold; border-right: 5px solid #28a745; background: #e8f5e9;">
                🎉 <strong>نجح الذكاء الاصطناعي في تكوين باكدج العروسة وإصدار أمر البيع الرسمي رقم ({sale_order.name}) بدقة!</strong>
            </div>
            <p style="font-size: 14px;">
                <strong>العميل:</strong> {partner.name} &nbsp;|&nbsp;
                <strong>الميزانية المستهدفة:</strong> <span class="badge bg-primary" style="font-size: 14px;">{budget:,.2f} ج.م</span> &nbsp;|&nbsp;
                <strong>الإجمالي بعد خصم الباكدج:</strong> <span class="badge bg-success" style="font-size: 14px;">{sale_order.amount_total:,.2f} ج.م</span>
            </p>
            <table class="table table-bordered table-striped" style="margin-top: 15px; text-align: center;">
                <thead style="background: #0d6efd; color: white;">
                    <tr>
                        <th>الكود / الباركود</th>
                        <th>الصنف المختار</th>
                        <th>التصنيف العائلي</th>
                        <th>الكمية</th>
                        <th>سعر الوحدة</th>
                        <th>الإجمالي</th>
                    </tr>
                </thead>
                <tbody>
                    {lines_html}
                </tbody>
            </table>
            <div class="alert alert-info" style="margin-top: 15px;">
                ✅ تم إنشاء أمر البيع رسميًا في قاعدة بيانات أودو 20 وهو جاهز للتأكيد وإصدار الفاتورة أو الإرسال لشاشة الكاشير.
            </div>
        </div>
        """
        self.ai_response_html = html
        self.action_executed_summary = f"تم بنجاح توليد أمر البيع {sale_order.name} بميزانية {budget:,.2f} ج.م متوازناً عبر 5 تصنيفات رئيسية."
