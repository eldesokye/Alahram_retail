import urllib.request
import json

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

search_url = "http://localhost:8070/web/dataset/call_kw"
search_payload = {
    "jsonrpc": "2.0",
    "params": {
        "model": "alahram.stock.recommendation",
        "method": "search_read",
        "args": [[["state", "=", "pending"], ["priority", "=", "urgent"]]],
        "kwargs": {
            "fields": ["id", "name", "priority"],
            "limit": 1
        }
    }
}
req = urllib.request.Request(search_url, data=json.dumps(search_payload).encode('utf-8'), headers={'Content-Type': 'application/json', 'Cookie': cookie})
resp = urllib.request.urlopen(req)
recs = json.loads(resp.read().decode('utf-8')).get('result', [])

if recs:
    target = recs[0]
    print(f"Testing URGENT recommendation: {target['name']} (ID: {target['id']})")
    call_payload = {
        "jsonrpc": "2.0",
        "params": {
            "model": "alahram.stock.recommendation",
            "method": "action_approve_recommendation",
            "args": [[target['id']]],
            "kwargs": {
                "context": {
                    "default_priority": "urgent",
                    "group_by": "priority"
                }
            }
        }
    }
    req = urllib.request.Request(search_url, data=json.dumps(call_payload).encode('utf-8'), headers={'Content-Type': 'application/json', 'Cookie': cookie})
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read().decode('utf-8'))
    print("Result for URGENT:", result)
else:
    print("No pending urgent recommendations, let's seed demo recommendations...")
    seed_payload = {
        "jsonrpc": "2.0",
        "params": {
            "model": "alahram.stock.recommendation",
            "method": "action_seed_demo_recommendations",
            "args": [],
            "kwargs": {}
        }
    }
    req = urllib.request.Request(search_url, data=json.dumps(seed_payload).encode('utf-8'), headers={'Content-Type': 'application/json', 'Cookie': cookie})
    urllib.request.urlopen(req)
    print("Seeded new demo recommendations!")

