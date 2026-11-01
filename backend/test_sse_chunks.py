"""Verify SSE events arrive as separate chunks (not one big blob)."""
import httpx, time, json

BASE  = "http://localhost:8000/api"
c     = httpx.Client(timeout=120.0)

r = c.post(f"{BASE}/auth/login", data={"username": "admin", "password": "admin123"})
token = r.json()["access_token"]
AH = {"Authorization": f"Bearer {token}", "Accept": "text/event-stream"}

print("Reading raw SSE chunks from /ml/train ...\n")
t0 = time.time()
chunk_times = []

with c.stream("POST", f"{BASE}/admin/ml/train", headers=AH) as resp:
    print(f"Status: {resp.status_code}  Content-Type: {resp.headers.get('content-type')}\n")
    buf = ""
    for raw_chunk in resp.iter_bytes(chunk_size=None):
        elapsed = time.time() - t0
        chunk_times.append(elapsed)
        text = raw_chunk.decode("utf-8", errors="replace")
        buf += text
        for line in text.split("\n"):
            if line.startswith("data: "):
                try:
                    evt = json.loads(line[6:])
                    bar = "█" * (evt["progress"] // 5) + "░" * (20 - evt["progress"] // 5)
                    done_flag = "✅ " if evt.get("done") else "   "
                    print(f"  t={elapsed:5.1f}s  [{bar}] {evt['progress']:3d}%  {done_flag}{evt['message']}")
                except Exception:
                    pass
        if "\"done\": true" in text or '"done":true' in text:
            break

elapsed_total = time.time() - t0
print(f"\nTotal time: {elapsed_total:.1f}s")
print(f"Chunks received: {len(chunk_times)}")
if len(chunk_times) > 1:
    spreads = [chunk_times[i+1] - chunk_times[i] for i in range(len(chunk_times)-1)]
    print(f"Inter-chunk gaps: min={min(spreads):.2f}s  max={max(spreads):.2f}s  avg={sum(spreads)/len(spreads):.2f}s")
    if max(spreads) > 2:
        print("⚠️  Large gap detected — some events may be buffered together")
    else:
        print("✅  Events arrive as separate chunks — progress bar will work")
