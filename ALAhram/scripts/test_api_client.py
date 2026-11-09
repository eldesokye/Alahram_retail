import urllib.request
import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

payload = {"question": "إيه أقل 5 فروع في المبيعات لشهر أكتوبر حسب بيانات النظام؟"}
req = urllib.request.Request(
    "http://localhost:8070/api/alahram/chat",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print("Status:", res.get("status"))
        print("\n--- Question ---")
        print(res.get("question"))
        print("\n--- Reply ---")
        print(res.get("reply"))
        print("\n--- HTML Preview (First 200 chars) ---")
        print(res.get("html")[:200])
except Exception as e:
    print("Error:", e)
