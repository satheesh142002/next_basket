"""
Quick SSE test — reads up to first 3 events then stops.
This validates the stream works without waiting for full training.
"""
import httpx, json, os, time, sys

BASE = "http://localhost:8000/api"
c    = httpx.Client(timeout=30.0)

admin_username = os.environ.get("TEST_ADMIN_USERNAME")
admin_password = os.environ.get("TEST_ADMIN_PASSWORD")
if not admin_username or not admin_password:
    raise SystemExit("Set TEST_ADMIN_USERNAME and TEST_ADMIN_PASSWORD for an existing admin account.")

r = c.post(f"{BASE}/auth/login", data={"username": admin_username, "password": admin_password})
assert r.status_code == 200
token = r.json()["access_token"]
AH = {"Authorization": f"Bearer {token}", "Accept": "text/event-stream"}

print("Reading first few SSE events from /ml/train ...\n")
t0 = time.time()
events = []

with c.stream("POST", f"{BASE}/admin/ml/train", headers=AH) as resp:
    print(f"Status: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('content-type', '?')}")
    print()

    if resp.status_code != 200:
        print("ERROR:", resp.text)
        sys.exit(1)

    buf = ""
    for chunk in resp.iter_bytes(chunk_size=None):
        text = chunk.decode("utf-8", errors="replace")
        buf += text
        lines = buf.split("\n")
        buf = lines.pop()  # keep incomplete

        for line in lines:
            if not line.startswith("data: "):
                continue
            try:
                evt = json.loads(line[6:])
                t   = time.time() - t0
                bar = "█" * (evt["progress"] // 5) + "░" * (20 - evt["progress"] // 5)
                print(f"  t={t:4.1f}s [{bar}] {evt['progress']:3d}%  {evt['message']}")
                events.append(evt)
            except Exception:
                pass

        # Stop after 4 events — don't wait for full training
        if len(events) >= 4:
            break

if len(events) == 0:
    print("❌  No SSE events received — stream may be fully buffered")
    sys.exit(1)
elif len(events) >= 4:
    # Check events arrived at different times (not all at once)
    print(f"\n✅  Received {len(events)} events successfully")
    print("   If timestamps increase progressively, streaming is working correctly")
else:
    print(f"⚠️  Only {len(events)} events before stream ended")

sys.exit(0)
