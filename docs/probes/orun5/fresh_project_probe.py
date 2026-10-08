"""Measure when a fresh project becomes readable on `cadex app` (REPORT §10.3).

Starts `cadex app` over a temporary projects directory and `cadex mcp` on a
project that does not exist yet, then probes `/api/projects` and
`/p/<name>/api/project` before the server starts, after `initialize`, after
`tools/list`, after the first tool call and after the server exits. No script
is ever written. Usage: pixi run python fresh_project_probe.py <repo root>
"""
import json, os, re, subprocess, sys, tempfile, time, urllib.error, urllib.request
repo = sys.argv[1]
projects = tempfile.mkdtemp(prefix="o5nf-projects-")
proj = os.path.join(projects, "orun5-fresh")
app = subprocess.Popen([repo + "/cadex", "app", "--projects", projects, "--port", "0", "--json"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=repo)
port = None
t0 = time.time()
lines = []
while time.time() - t0 < 60 and port is None:
    line = app.stdout.readline()
    lines.append(line)
    m = re.search(r"127\.0\.0\.1:(\d+)", line)
    if m: port = int(m.group(1))
if port is None:
    print("no port", lines); app.kill(); sys.exit(1)
def get(path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")
def probe(stage):
    s1, idx = get("/api/projects")
    names = [p.get("name") for p in (idx.get("projects") if isinstance(idx, dict) else idx) or []] if s1 == 200 else idx
    s2, body = get("/p/orun5-fresh/api/project")
    summary = body if s2 != 200 else {"accepted.available": (body.get("accepted") or {}).get("available"),
                                      "accepted.reason": (body.get("accepted") or {}).get("reason")}
    print(json.dumps({"stage": stage, "t_s": round(time.time() - T, 2),
                      "index": s1, "listed": "orun5-fresh" in (names or []),
                      "project": s2, "body": summary,
                      "files": sorted(os.path.relpath(os.path.join(d, f), proj) for d, _, fs in os.walk(proj) for f in fs) if os.path.isdir(proj) else None}))
T = time.time()
probe("before mcp starts")
mcp = subprocess.Popen([repo + "/cadex", "mcp", "--project", proj], stdin=subprocess.PIPE,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=repo)
def rpc(i, method, params):
    mcp.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": method, "params": params}) + "\n"); mcp.stdin.flush()
    while True:
        msg = json.loads(mcp.stdout.readline())
        if msg.get("id") == i: return msg
r = rpc(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "probe", "version": "0"}})
mcp.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"); mcp.stdin.flush()
probe("after initialize")
tools = rpc(2, "tools/list", {})["result"]["tools"]
names = [t["name"] for t in tools]
print("tools:", names)
probe("after tools/list")
first = "describe_api" if "describe_api" in names else names[0]
t = time.time(); r = rpc(3, "tools/call", {"name": first, "arguments": {}})
print("first tool call:", first, "error" if r.get("error") or r.get("result", {}).get("isError") else "ok", round(time.time()-t, 2), "s")
probe("after first tool call (no script)")
mcp.stdin.close(); mcp.wait(timeout=60)
probe("after mcp exits (no script)")
app.terminate(); app.wait(timeout=10)
