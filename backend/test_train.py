"""
Test the /ml/train SSE endpoint — reads the event stream and prints progress.
"""
import httpx, json, os, time

BASE  = "http://localhost:8000/api"
client = httpx.Client(timeout=120.0)
admin_username = os.environ.get("TEST_ADMIN_USERNAME")
admin_password = os.environ.get("TEST_ADMIN_PASSWORD")
if not admin_username or not admin_password:
    raise SystemExit("Set TEST_ADMIN_USERNAME and TEST_ADMIN_PASSWORD for an existing admin account.")

r = client.post(f"{BASE}/auth/login", data={"username": admin_username, "password": admin_password})
assert r.status_code == 200, f"Login failed: {r.text}"
token = r.json()["access_token"]
AH = {"Authorization": f"Bearer {token}"}

print("Calling /api/admin/ml/train (SSE stream)...\n")
t0 = time.time()

with client.stream("POST", f"{BASE}/admin/ml/train", headers={**AH, "Accept": "text/event-stream"}) as resp:
    assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text}"
    buf = ""
    for chunk in resp.iter_text():
        buf += chunk
        lines = buf.split("\n")
        buf = lines.pop()
        for line in lines:
            if not line.startswith("data: "):
                continue
            evt = json.loads(line[6:])
            pct  = evt.get("progress", 0)
            msg  = evt.get("message", "")
            err  = evt.get("error", False)
            done = evt.get("done", False)
            bar  = "█" * (pct // 5) + "░" * (20 - pct // 5)
            flag = "❌" if err else ("✅" if done else "  ")
            print(f"  {flag} [{bar}] {pct:3d}%  {msg}")
            if done:
                break

elapsed = time.time() - t0
print(f"\nDone in {elapsed:.1f}s")

# Check ML status
r = client.get(f"{BASE}/admin/ml/status", headers=AH)
print("ML status:", json.dumps(r.json(), indent=2))
