"""orun21 D1: a dashboard screenshot of one run, served on 127.0.0.1 only.

    pixi run python docs/probes/orun21/d1_shot.py PROJECT RUN OUT.png [--gpu]

Serves PROJECT read-only on a loopback port, opens the page in headless
Chromium, picks RUN in the viewport, waits for its model, and writes the
viewport-and-status layout to OUT.png. Prints what the page said of the model.
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "cli"))

from cadex_cli.browser import HeadlessBrowser, find_browser  # noqa: E402
from cadex_cli.review_server import serve  # noqa: E402

LAYOUT = {"dir": "row", "sizes": [0.6, 0.4], "children": [{"editor": "view3d"}, {"editor": "training"}]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("run")
    parser.add_argument("out")
    parser.add_argument("--size", default="1440x810")
    parser.add_argument("--settle", type=float, default=4.0, help="seconds to let playback run")
    options = parser.parse_args()
    width, height = (int(v) for v in options.size.split("x"))
    server, _thread = serve(Path(options.project).expanduser(), "127.0.0.1", 0)
    try:
        with HeadlessBrowser(find_browser(), width=width, height=height) as browser:
            page = browser.page("about:blank")
            page.send("Emulation.setDeviceMetricsOverride",
                      {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})
            page.send("Page.enable")
            page.send("Page.addScriptToEvaluateOnNewDocument", {
                "source": "try { localStorage.setItem('cadex.layout.v7', %s); } catch (e) {}"
                          % json.dumps(json.dumps(LAYOUT))})
            page.send("Page.navigate", {"url": server.url})
            page.wait_for("document.readyState === 'complete' && !!window.cadexReview", timeout=120)
            page.evaluate("window.cadexReview.ready", await_promise=True, timeout=300)
            page.evaluate(f"window.cadexReview.setSource('run:' + {json.dumps(options.run)})")
            page.wait_for("['loaded','missing','error'].includes("
                          "document.getElementById('model-status').dataset.state)", timeout=300)
            page.evaluate("window.cadexReview.viewer().fit()")
            time.sleep(options.settle)
            shot = page.send("Page.captureScreenshot", {"format": "png"}, timeout=120)
            Path(options.out).write_bytes(base64.b64decode(shot["data"]))
            status = page.evaluate("(function(s){return {state:s.dataset.state, tier:s.dataset.tier||'',"
                                   " text:s.textContent}})(document.getElementById('model-status'))")
            stats = page.evaluate("JSON.stringify(window.cadexReview.viewer().stats())")
            print(json.dumps({"status": status, "stats": json.loads(stats)}, indent=1)[:1500])
    finally:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
