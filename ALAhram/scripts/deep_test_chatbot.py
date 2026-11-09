# -*- coding: utf-8 -*-
"""
Al Ahram Cookware — Deep Chatbot Test Suite & Scenario Verification
===================================================================
Runs end-to-end tests across 6 major operational scenarios:
1. Executive BI & Sales Analytics (Lowest Branches & Dead Stock)
2. Bridal Package & Custom Budget Inquiries (15k, 25k, Custom)
3. Supply Chain & Showroom Replenishment (Sidi Gaber Stockouts)
4. Multi-Turn Contextual Conversation
5. Multi-Channel & Interface Verification (REST POST/GET, Web UI, Discuss)
6. Edge Cases & Resilience (Empty inputs, Error handling, Zero 429 failures)
"""

import urllib.request
import urllib.parse
import json
import time
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8070"
CHAT_API = f"{BASE_URL}/api/alahram/chat"
CHAT_UI = f"{BASE_URL}/alahram/chat"

test_results = []

def run_test(scenario_name, query, expected_keywords, method="POST", history=None, expected_status="success", expected_code=200):
    start_time = time.time()
    result = {
        'scenario': scenario_name,
        'query': query,
        'method': method,
        'status': 'FAILED',
        'latency_s': 0,
        'details': ''
    }

    try:
        if method == "POST":
            payload = {"question": query}
            if history:
                payload["history"] = history
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                CHAT_API,
                data=data_bytes,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
        elif method == "GET":
            q_enc = urllib.parse.quote(query)
            req = urllib.request.Request(f"{CHAT_API}?question={q_enc}", method="GET")
        elif method == "UI":
            req = urllib.request.Request(CHAT_UI, method="GET")

        with urllib.request.urlopen(req, timeout=30) as resp:
            latency = round(time.time() - start_time, 2)
            result['latency_s'] = latency
            status_code = resp.status

            if method == "UI":
                content = resp.read().decode("utf-8")
                if status_code == 200 and "شات بوت الأهرام الذكي" in content and "/api/alahram/chat" in content:
                    result['status'] = 'PASSED'
                    result['details'] = f"UI rendered HTTP 200 with full branding & scripts ({len(content)} bytes)"
                else:
                    result['details'] = f"UI check failed: status {status_code}"
                test_results.append(result)
                return result, None

            res_json = json.loads(resp.read().decode("utf-8"))
            api_status = res_json.get("status")

            if status_code != expected_code or api_status != expected_status:
                result['details'] = f"Status mismatch: HTTP {status_code}, API {api_status}"
                test_results.append(result)
                return result, res_json

            reply = res_json.get("reply", "")
            html = res_json.get("html", "")
            full_text = reply + " " + html

            missing = [kw for kw in expected_keywords if kw not in full_text]
            if missing:
                result['details'] = f"Missing expected keywords: {missing}. Reply preview: {reply[:120]}..."
            else:
                result['status'] = 'PASSED'
                result['details'] = f"All {len(expected_keywords)} keywords matched. Latency: {latency}s. Reply: {reply[:100]}..."

            test_results.append(result)
            return result, res_json

    except urllib.error.HTTPError as e:
        latency = round(time.time() - start_time, 2)
        result['latency_s'] = latency
        if e.code == expected_code:
            try:
                err_json = json.loads(e.read().decode("utf-8"))
                result['status'] = 'PASSED'
                result['details'] = f"Expected HTTP error caught: {e.code} - {err_json.get('message')}"
            except Exception:
                result['status'] = 'PASSED'
                result['details'] = f"Expected HTTP error code: {e.code}"
        else:
            result['details'] = f"Unexpected HTTP Error {e.code}: {e.read().decode('utf-8', errors='ignore')[:150]}"
        test_results.append(result)
        return result, None
    except Exception as e:
        latency = round(time.time() - start_time, 2)
        result['latency_s'] = latency
        result['details'] = f"Exception: {str(e)}"
        test_results.append(result)
        return result, None


print("================================================================================")
print("🚀 STARTING DEEP TEST SUITE: AL AHRAM AI CHATBOT & DATABASE RAG ENGINE")
print(f"Target Server: {BASE_URL}")
print("================================================================================\n")

# ------------------------------------------------------------------------------
# SCENARIO 1: Executive Management & Sales BI
# ------------------------------------------------------------------------------
print("▶ SCENARIO 1: Executive Management & Sales BI Analytics")
run_test(
    scenario_name="1.1 Lowest 5 Branches Ranking",
    query="إيه أقل 5 فروع في المبيعات لشهر أكتوبر حسب بيانات النظام؟",
    expected_keywords=["الإدارة", "فيصل", "سموحة", "مبيعات", "أكتوبر"]
)

run_test(
    scenario_name="1.2 High Dead Stock Items",
    query="إيه الأصناف اللي عندي منها مخزون كبير ومش بتتباع؟",
    expected_keywords=["جرانيت", "Bio trade grip", "قطعة", "مخزون"]
)

run_test(
    scenario_name="1.3 Abnormal Return Rates",
    query="إيه الفروع اللي زادت فيها المرتجعات بنسبة غير طبيعية؟",
    expected_keywords=["مرتجع", "فرع"]
)

# ------------------------------------------------------------------------------
# SCENARIO 2: Bridal Package & Custom Budget Inquiries
# ------------------------------------------------------------------------------
print("\n▶ SCENARIO 2: Bridal Package & Custom Budget Inquiries")
run_test(
    scenario_name="2.1 Bridal Package 25k (Gold Tier)",
    query="عايز أجهز باكدج عروسة متكامل بميزانية 25,000 ج.م إيه الأصناف والخصم؟",
    expected_keywords=["جرانيت", "صواني", "تيفال", "25,000"]
)

run_test(
    scenario_name="2.2 Bridal Package 15k (Silver Economy)",
    query="عايز باكدج عروسة اقتصادي بميزانية 15000 جنيه",
    expected_keywords=["جرانيت", "15,000"]
)

run_test(
    scenario_name="2.3 Granite Cookware Value Proposition",
    query="ما هي مميزات أطقم الجرانيت الصحي 4 مم مقارنة بالأواني العادية؟",
    expected_keywords=["جرانيت", "صحي", "الأهرام"]
)

# ------------------------------------------------------------------------------
# SCENARIO 3: Supply Chain & Showroom Replenishment
# ------------------------------------------------------------------------------
print("\n▶ SCENARIO 3: Supply Chain & Showroom Replenishment")
run_test(
    scenario_name="3.1 Sidi Gaber Stockout & Transit Transfer",
    query="إيه المنتجات اللي ناقصة في فرع سيدي جابر ومحتاجة تحويل فوري من مخزن الإدارة؟",
    expected_keywords=["سيدي جابر", "الإدارة", "طقم"]
)

run_test(
    scenario_name="3.2 Promotional Discount Candidates",
    query="إيه الأصناف اللي نقدر نعمل عليها عروض وتخفيضات لتنشيط المبيعات؟",
    expected_keywords=["أصناف", "الأهرام"]
)

# ------------------------------------------------------------------------------
# SCENARIO 4: Multi-Turn Contextual Conversation
# ------------------------------------------------------------------------------
print("\n▶ SCENARIO 4: Multi-Turn Contextual Conversation")
history = []
_, r1 = run_test(
    scenario_name="4.1 Multi-Turn Step 1 (Inquire Cookware)",
    query="إيه أفضل أطقم الأواني المتوفرة لديكم حالياً؟",
    expected_keywords=["الأهرام", "جرانيت"]
)
if r1:
    history.append({"role": "user", "text": "إيه أفضل أطقم الأواني المتوفرة لديكم حالياً؟"})
    history.append({"role": "model", "text": r1.get("reply", "")})

run_test(
    scenario_name="4.2 Multi-Turn Step 2 (Follow-up Budget Order)",
    query="تمام، رتبلي منهم باكدج عروسة بالميزانية المتاحة 20000 جنيه مع صواني فرن",
    expected_keywords=["باكدج", "20,000"],
    history=history
)

# ------------------------------------------------------------------------------
# SCENARIO 5: Multi-Channel & Protocol Verification
# ------------------------------------------------------------------------------
print("\n▶ SCENARIO 5: Multi-Channel & Protocol Verification")
run_test(
    scenario_name="5.1 REST API GET Method",
    query="قائمة المنتجات والأسعار الرسمية",
    expected_keywords=["الأهرام"],
    method="GET"
)

run_test(
    scenario_name="5.2 Web Chatbot UI Page",
    query="",
    expected_keywords=[],
    method="UI"
)

# ------------------------------------------------------------------------------
# SCENARIO 6: Edge Cases & Resilience
# ------------------------------------------------------------------------------
print("\n▶ SCENARIO 6: Edge Cases & Resilience")
run_test(
    scenario_name="6.1 Empty Query Validation",
    query="",
    expected_keywords=[],
    method="POST",
    expected_status="error",
    expected_code=400
)

run_test(
    scenario_name="6.2 Whitespace Query Validation",
    query="     ",
    expected_keywords=[],
    method="POST",
    expected_status="error",
    expected_code=400
)

run_test(
    scenario_name="6.3 English Language Query",
    query="What are the lowest selling branches for October?",
    expected_keywords=["branches", "WH-MAIN"] or ["WH-MAIN", "الإدارة"]
)

# ------------------------------------------------------------------------------
# SUMMARY REPORT
# ------------------------------------------------------------------------------
print("\n================================================================================")
print("📊 DEEP TEST EXECUTION SUMMARY REPORT")
print("================================================================================")
total_tests = len(test_results)
passed_tests = sum(1 for t in test_results if t['status'] == 'PASSED')
failed_tests = total_tests - passed_tests
success_rate = (passed_tests / total_tests) * 100

for idx, t in enumerate(test_results, 1):
    symbol = "✅" if t['status'] == 'PASSED' else "❌"
    print(f"{idx:02d}. {symbol} [{t['status']}] {t['scenario']} ({t['latency_s']}s)")
    if t['status'] != 'PASSED':
        print(f"    ⚠️  Reason: {t['details']}")

print("\n--------------------------------------------------------------------------------")
print(f"TOTAL TESTS : {total_tests}")
print(f"PASSED      : {passed_tests}")
print(f"FAILED      : {failed_tests}")
print(f"SUCCESS RATE: {success_rate:.1f}%")
print("================================================================================")

