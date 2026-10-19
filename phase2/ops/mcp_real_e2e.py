"""Real end-to-end check: talk to the MCP server over stdio exactly like an MCP client and run real Antigravity jobs.
Usage: python mcp_real_e2e.py PROJECT"""
import json
import subprocess
import sys
import time
from pathlib import Path

P2 = Path(__file__).resolve().parent.parent
project = sys.argv[1]
p = subprocess.Popen([sys.executable, str(P2 / "assets_mcp/af_assets_server.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                     text=True, encoding="utf-8")
n = 0


def rpc(method, params=None):
    global n
    n += 1
    p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": n, "method": method, "params": params or {}}) + "\n")
    p.stdin.flush()
    while True:
        m = json.loads(p.stdout.readline())
        if m.get("id") == n:
            return m


def tool(name, args):
    r = rpc("tools/call", {"name": name, "arguments": args})["result"]
    return r["isError"], (r["content"][0]["text"] if r["isError"] else json.loads(r["content"][0]["text"]))


info = rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "e2e", "version": "1"}})["result"]
print("server:", info["serverInfo"], "| tools:", [t["name"] for t in rpc("tools/list")["result"]["tools"]])
ref = str(P2 / "approved/bi_v2.1/frames/frame01.png")
jobs = {}
for aid, kind, prompt, extra in (
        ("umbrella_ai", "prop", "a closed red umbrella with a simple curved handle (symbol of being prepared for emergencies)", {"reference_images": [ref], "display_width": 300}),
        ("calm_room_ai", "background", "a calm flat living room corner: a plain wall, a window, a small sofa and a floor lamp, soft cream and pale blue shapes", {"display_width": 1920})):
    err, j = tool("submit_asset_job", {"project": project, "asset_id": aid, "kind": kind, "prompt": prompt, **extra})
    print("submit", aid, "->", j["job_id"] if not err else j, j.get("state"))
    jobs[aid] = j["job_id"]
t0 = time.time()
done = {}
while len(done) < len(jobs) and time.time() - t0 < 900:
    for aid, jid in jobs.items():
        if aid in done:
            continue
        _, j = tool("check_asset_job", {"project": project, "job_id": jid})
        if j["state"] not in ("queued", "running"):
            done[aid] = j
            print(f"[{time.time() - t0:5.0f}s] {aid}: {j['state']}", json.dumps(j.get("result") or j.get("error"), ensure_ascii=False)[:400])
    time.sleep(3)
# repeat the same request: stored result, no new agy run
err, again = tool("submit_asset_job", {"project": project, "asset_id": "umbrella_ai", "kind": "prop",
                                       "prompt": "a closed red umbrella with a simple curved handle (symbol of being prepared for emergencies)", "reference_images": [ref], "display_width": 300})
print("repeat same request ->", again["job_id"], again.get("note"))
p.stdin.close()
p.wait(timeout=10)
