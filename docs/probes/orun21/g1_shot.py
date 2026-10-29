"""orun21 G1: a go-to-point episode as the dashboard plays it, shot and filmed on 127.0.0.1.

    pixi run python docs/probes/orun21/g1_shot.py PROJECT RUN OUT_PREFIX \\
        --at 0 9.6 13.0 [--film --step 0.2 --fps 10]

Serves PROJECT read-only on a loopback port, opens the page in headless
Chromium, picks RUN, waits for its playback, and for each time in --at writes
OUT_PREFIX-<t>s.png with the follow camera (`-course.png`: every point framed
from above, at the first --at time). With --film it seeks the episode every
--step seconds with the follow camera and encodes OUT_PREFIX.mp4 at --fps
(so --step 0.2 at 10 fps plays at twice real time). Prints what the page said
of the lit point at each shot.
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "cli"))

from cadex_cli.browser import HeadlessBrowser, find_browser  # noqa: E402
from cadex_cli.review_server import serve  # noqa: E402
from cadex_cli.video import ffmpeg  # noqa: E402

LAYOUT = {"dir": "col", "sizes": [0.9, 0.1], "children": [
    {"dir": "row", "sizes": [0.72, 0.28], "children": [{"editor": "view3d"}, {"editor": "training"}]},
    {"editor": "version"}]}
#: The follow camera: three-quarter on, high enough to see the points round the robot.
FOLLOW = {"yaw": 0.8, "pitch": 0.62, "distance": 4200}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("run")
    parser.add_argument("out")
    parser.add_argument("--size", default="1280x720")
    parser.add_argument("--at", type=float, nargs="*", default=[])
    parser.add_argument("--film", action="store_true")
    parser.add_argument("--step", type=float, default=0.2)
    parser.add_argument("--fps", type=float, default=10.0)
    options = parser.parse_args()
    width, height = (int(v) for v in options.size.split("x"))
    server, _thread = serve(Path(options.project).expanduser(), "127.0.0.1", 0)
    said = []
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
            page.wait_for("(function(p){return !!p && !!p.goto})(window.cadexReview.playback())", timeout=120)

            def capture(path: Path) -> None:
                shot = page.send("Page.captureScreenshot", {"format": "png"}, timeout=120)
                path.write_bytes(base64.b64decode(shot["data"]))

            def look(t: float, course: bool) -> dict:
                page.evaluate("window.cadexReview.setFollow(false)")
                page.evaluate(f"window.cadexReview.seek({t})")
                if course:
                    page.evaluate("window.cadexReview.viewer().frameTargets()")
                else:
                    page.evaluate("window.cadexReview.setFollow(true)")
                    page.evaluate(f"window.cadexReview.seek({t})")
                    page.evaluate("(function(v){var c=v.camera(); c.yaw=%f; c.pitch=%f; c.distance=%f; v.setCamera(c);})"
                                  "(window.cadexReview.viewer())" % (FOLLOW["yaw"], FOLLOW["pitch"], FOLLOW["distance"]))
                return json.loads(page.evaluate("JSON.stringify({t:window.cadexReview.playback().t,"
                                                " goto:window.cadexReview.playback().goto,"
                                                " targets:window.cadexReview.viewer().targets()})"))

            for k, t in enumerate(options.at):
                for course in ((True, False) if k == 0 else (False,)):
                    seen = look(t, course)
                    time.sleep(1.0)
                    name = f"{options.out}-course.png" if course else f"{options.out}-{t:g}s.png"
                    capture(Path(name))
                    said.append({"shot": name, **seen})
            if options.film:
                duration = page.evaluate("(function(p){return p.times_s[p.times_s.length-1]})"
                                         "(window.cadexReview.playback())")
                with tempfile.TemporaryDirectory() as work:
                    count, t = 0, 0.0
                    look(0.0, False)
                    while t <= duration + 1e-9:
                        page.evaluate(f"window.cadexReview.seek({t})")
                        capture(Path(work) / f"{count:05d}.png")
                        count, t = count + 1, t + options.step
                    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-framerate", str(options.fps),
                                    "-i", str(Path(work) / "%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                    "-crf", "28", f"{options.out}.mp4"], check=True)
                    said.append({"film": f"{options.out}.mp4", "frames": count, "episode_s": duration})
    finally:
        server.shutdown()
        server.server_close()
    print(json.dumps(said, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
