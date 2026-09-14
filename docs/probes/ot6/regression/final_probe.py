"""D9's final regression receipt: the suites, and the persistent dashboard
at both charter widths with the arm's final run selected.

Usage:
  PYTHONPATH=cli pixi run python docs/probes/ot6/regression/final_probe.py URL LOGS OUT

URL is the operator address (read from the environment by the caller, never
from this file). LOGS holds engine.{log,exit,started,finished} and
cli.{log,exit,started,finished} from `pixi run test-engine` and
`pixi run python -m pytest cli/tests`. Writes OUT/final.json and
OUT/final-{1400,400}.png (the #model region, quantised under the image cap).

At each width a fresh visit must select the retained final run by itself,
load its real tessellation showing solids, have no horizontal overflow, poll
the project with no gap over five seconds, play the retained video and
download it with the recorded digest; at 400 px one finger must orbit the
model without scrolling the page.
"""
import datetime
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image
from cadex_cli.browser import HeadlessBrowser, find_browser

RUN = "heron1-final"
url, logs, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()


def suite(name, command, per_file):
    log = (logs / f"{name}.log").read_text(errors="replace")
    tail = re.search(r"=+ (.*?) in ([\d.]+)s", log.splitlines()[-1])
    counts = {k: int(v) for v, k in re.findall(r"(\d+) (passed|skipped|failed|error|xfailed)", tail[1])}
    files = {}  # path -> [passed, skipped, failed]; the CLI suite only, to stay under the receipt cap
    path = None
    for line in log.splitlines():  # a file's marks wrap onto bare continuation lines
        head = re.match(r"^(\S+\.py) ([.sFxXE]+)", line) or (path and re.match(r"^()([.sFxXE]+)\s+\[", line))
        if not head:
            continue
        path = head[1] or path
        row = files.setdefault(path, [0, 0, 0])
        marks = head[2]
        row[0] += marks.count("."); row[1] += marks.count("s"); row[2] += marks.count("F") + marks.count("E")
    return {"command": command, "exit_code": int((logs / f"{name}.exit").read_text()),
            **({"files": files} if per_file else {}),
            "started": (logs / f"{name}.started").read_text().strip(),
            "finished": (logs / f"{name}.finished").read_text().strip(),
            "seconds": float(tail[2]), "log_sha256": hashlib.sha256(log.encode()).hexdigest(),
            "log_bytes": len(log.encode()), **{k: counts.get(k, 0) for k in ("passed", "skipped", "failed", "error")}}


receipt = {
    "schema": "ot6-d9-final-regression-v1",
    "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "suites": [suite("engine", "pixi run test-engine", per_file=False),
               suite("cli", "pixi run python -m pytest cli/tests", per_file=True)],
    "operator_url": "http://<private-address>:8765/", "run": RUN, "visits": []}
project = json.load(urllib.request.urlopen(url + "api/project"))
receipt["project"] = project["project"]
receipt["accepted_revision"] = project["accepted"]["revision"]
receipt["runs"] = [{"run": r["run"], "relation": r["relation"], "outcome": r.get("outcome"),
                    "videos": len(r.get("videos") or [])} for r in project["runs"]]
retained = json.load(urllib.request.urlopen(url + f"api/run/{RUN}"))
video = retained["videos"][0]
receipt["retained_video"] = {"sha256": video["sha256"], "style": video["style"], "showing": video["showing"]}

for width, height in [(1400, 900), (400, 850)]:
    mobile = width == 400
    with HeadlessBrowser(find_browser(), width=width, height=height) as browser:
        page = browser.page("about:blank")
        page.send("Emulation.setDeviceMetricsOverride",
                  {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": mobile})
        if mobile:
            page.send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})
        page.send("Page.navigate", {"url": url})
        page.wait_for("document.readyState === 'complete' && !!window.cadexReview")
        page.evaluate("window.cadexReview.ready", await_promise=True)
        page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
        page.wait_for("document.getElementById('model-status').dataset.showing === 'solids'")
        page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
        state = page.evaluate("window.cadexReview.state()")
        visit = {"at": now(), "width": width, "height": height, "touch": mobile,
                 "selected": state["selected"], "relation": state["relation"], "stale": state["stale"],
                 "model_revision": state["model"]["revision"], "status": page.text("#model-status"),
                 "overflow_px": page.evaluate(
                     "Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)"),
                 "drawn_pixels": page.evaluate("window.cadexReview.viewer().nonBackgroundPixels()")}
        assert visit["selected"] == RUN and visit["overflow_px"] == 0 and visit["drawn_pixels"] > 1000
        assert visit["model_revision"] == video["accepted_revision"]
        # Live polling: the page keeps fetching the project on its own; no gap over five seconds.
        page.evaluate("performance.clearResourceTimings()")
        time.sleep(10.5)
        stamps = page.evaluate("performance.getEntriesByType('resource')"
                               ".filter(function (e) { return e.name.indexOf('/api/project') >= 0; })"
                               ".map(function (e) { return e.responseEnd; })")
        gaps = [b - a for a, b in zip(stamps, stamps[1:])]
        visit["polling"] = {"window_s": 10.5, "project_fetches": len(stamps),
                            "max_gap_s": round(max(gaps) / 1000, 3) if gaps else None,
                            "last_poll_ms": page.evaluate("window.cadexReview.lastPoll()")["ms"]}
        assert len(stamps) >= 3 and visit["polling"]["max_gap_s"] < 5
        if mobile:
            page.scroll_into_view("#model")
            box = page.rect("#viewer")
            cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            before = page.evaluate("window.cadexReview.viewer().camera()")
            scroll = page.evaluate("scrollY")
            page.touch_drag(cx, cy, cx + 120, cy + 50)
            after = page.wait_for("(function(){var c=window.cadexReview.viewer().camera();"
                                  f"return (c.yaw !== {before['yaw']} && c.pitch !== {before['pitch']}) && c}})()")
            visit["touch_orbit"] = {"camera_before": before, "camera_after": after,
                                    "page_scrolled_px": page.evaluate("scrollY") - scroll}
            assert after["distance"] == before["distance"] and visit["touch_orbit"]["page_scrolled_px"] == 0
        page.scroll_into_view("#model")
        png = out / f"final-{width}.png"
        page.screenshot(png, clip=page.rect("#model"))
        Image.open(png).convert("RGB").quantize(256).save(png, optimize=True)
        visit["png"] = png.name
        visit["png_bytes"] = png.stat().st_size
        visit["png_sha256"] = hashlib.sha256(png.read_bytes()).hexdigest()
        page.evaluate("window.checkedVideo = document.querySelector('#videos video');"
                      "checkedVideo.muted = true; checkedVideo.play()", await_promise=True)
        page.wait_for("checkedVideo.currentTime > 0.1")
        visit["playback_seconds"] = page.evaluate("checkedVideo.currentTime")
        page.evaluate("checkedVideo.pause()")
        download = page.download("#videos a", by_touch=mobile)
        visit["download"] = {"bytes": download.path.stat().st_size,
                             "sha256": hashlib.sha256(download.path.read_bytes()).hexdigest(),
                             "by_touch": mobile}
        assert visit["download"]["sha256"] == video["sha256"]
        receipt["visits"].append(visit)

receipt["service"] = subprocess.run(
    ["systemctl", "--user", "show", "cadex-operator-review", "-p", "ActiveState", "-p", "ActiveEnterTimestamp"],
    text=True, capture_output=True).stdout.strip().splitlines()
(out / "final.json").write_text(json.dumps(receipt, indent=1, separators=(",", ": ")) + "\n")
print(json.dumps(receipt, indent=1))
