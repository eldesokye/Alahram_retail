import urllib.request
import json

# 1. Login to get session cookie
login_url = "http://localhost:8070/web/session/authenticate"
login_payload = {
    "jsonrpc": "2.0",
    "params": {
        "db": "odoo20",
        "login": "ops.manager@alahram.com",
        "password": "operations"
    }
}

req = urllib.request.Request(login_url, data=json.dumps(login_payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
cookie = resp.headers.get('Set-Cookie')
res_data = json.loads(resp.read().decode('utf-8'))
uid = res_data.get('result', {}).get('uid')
print(f"Logged in via HTTP as ops.manager (UID: {uid})")

# 2. Search for pending recommendation
search_url = "http://localhost:8070/web/dataset/call_kw"
search_payload = {
    "jsonrpc": "2.0",
    "params": {
        "model": "alahram.stock.recommendation",
        "method": "search_read",
        "args": [[["state", "=", "pending"]]],
        "kwargs": {
            "fields": ["id", "name", "priority"],
            "limit": 1
        }
    }
}
req = urllib.request.Request(search_url, data=json.dumps(search_payload).encode('utf-8'), headers={'Content-Type': 'application/json', 'Cookie': cookie})
resp = urllib.request.urlopen(req)
recs = json.loads(resp.read().decode('utf-8')).get('result', [])
if not recs:
    print("No pending recommendations found via HTTP!")
else:
    target_rec = recs[0]
    rec_id = target_rec['id']
    rec_name = target_rec['name']
    rec_priority = target_rec['priority']
    print(f"Found pending recommendation via HTTP: ID {rec_id} ({rec_name}, priority: {rec_priority})")

    # 3. Call action_approve_recommendation via HTTP with simulated Kanban context (default_priority='urgent')!
    call_payload = {
        "jsonrpc": "2.0",
        "params": {
            "model": "alahram.stock.recommendation",
            "method": "action_approve_recommendation",
            "args": [[rec_id]],
            "kwargs": {
                "context": {
                    "tz": "Africa/Cairo",
                    "uid": uid,
                    "default_priority": "urgent",
                    "group_by": "priority"
                }
            }
        }
    }
    req = urllib.request.Request(search_url, data=json.dumps(call_payload).encode('utf-8'), headers={'Content-Type': 'application/json', 'Cookie': cookie})
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read().decode('utf-8'))
    
    if "error" in result:
        print("❌ HTTP Call Button Error:", json.dumps(result['error'], indent=2))
    else:
        print("🎉 SUCCESS! HTTP Call Button returned:", result.get('result'))
