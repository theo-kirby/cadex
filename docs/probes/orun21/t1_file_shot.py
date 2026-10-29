"""orun21 T1: a course sampled from a mesh asset (ADR-855), as the dashboard draws it.

    pixi run python docs/probes/orun21/t1_file_shot.py PROJECT ASSET.stl OUT.png

Serves PROJECT read-only on a loopback port, opens it in headless Chromium,
and lets the viewer draw the accepted export's course on its own (the
heightfield `mjcf_terrain` reads back out of the MJCF). It writes OUT.png and
prints the worst gap between the drawn ground (`viewer.groundAt`) and the
engine's (`CadexDynamics.course_ground` of the descriptor `terrain_grid`
samples from the same binary STL) at 2,000 random points, where the two
interpolate a cell differently (bilinear against two triangles), and at the
grid's own vertices, where any gap is a misdrawn course.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
import random
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "cli"))
sys.path.insert(0, str(ROOT / "src" / "Mod" / "cadex"))

import CadexDynamics  # noqa: E402
from cadex_cli.browser import HeadlessBrowser, find_browser  # noqa: E402
from cadex_cli.review_server import serve  # noqa: E402

LAYOUT = {"dir": "col", "sizes": [0.92, 0.08], "children": [
    {"dir": "row", "sizes": [0.8, 0.2], "children": [{"editor": "view3d"}, {"editor": "training"}]},
    {"editor": "version"}]}
COURSE = {"x_range_mm": [-1000.0, 6000.0], "y_range_mm": [-2500.0, 2500.0], "cell_mm": 100.0}
CAMERA = {"target": [3000.0, 0.0, 0.0], "yaw": -2.75, "pitch": 0.32, "distance": 5200.0}


def stl_triangles(path: Path) -> list[tuple]:
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    rows = (struct.unpack_from("<12f", data, 84 + 50 * k) for k in range(count))
    return [(row[3:6], row[6:9], row[9:12]) for row in rows]


def main() -> int:
    project, asset, out = (Path(arg).expanduser() for arg in sys.argv[1:4])
    course = CadexDynamics.terrain_grid({**COURSE, "mesh": {
        "asset": asset.name, "sha256": "", "triangles": stl_triangles(asset)}})["descriptor"]
    ground = CadexDynamics.course_ground(course)
    server, _thread = serve(project, "127.0.0.1", 0)
    try:
        with HeadlessBrowser(find_browser(), width=1200, height=680) as browser:
            page = browser.page("about:blank")
            page.send("Emulation.setDeviceMetricsOverride",
                      {"width": 1200, "height": 680, "deviceScaleFactor": 1, "mobile": False})
            page.send("Page.enable")
            page.send("Page.addScriptToEvaluateOnNewDocument", {
                "source": "try { localStorage.setItem('cadex.layout.v7', %s); } catch (e) {}"
                          % json.dumps(json.dumps(LAYOUT))})
            page.send("Page.navigate", {"url": server.url})
            page.wait_for("document.readyState === 'complete' && !!window.cadexReview", timeout=120)
            page.evaluate("window.cadexReview.ready", await_promise=True, timeout=300)
            page.wait_for("['loaded','missing','error'].includes("
                          "document.getElementById('model-status').dataset.state)", timeout=300)
            page.wait_for("window.cadexReview.viewer().groundAt(3200, 0) !== null", timeout=120)
            rng = random.Random(855)
            (x0, x1), (y0, y1) = course["x_range_mm"], course["y_range_mm"]
            points = [(rng.uniform(x0, x1), rng.uniform(y0, y1)) for _ in range(2000)]
            heights = page.evaluate(
                "(function (p) { var v = window.cadexReview.viewer(); "
                "return p.map(function (q) { return v.groundAt(q[0], q[1]); }); })(%s)"
                % json.dumps(points))
            gaps = [abs(h - ground(x, y)) for (x, y), h in zip(points, heights) if h is not None]
            vertices = [(x0 + c * course["cell_mm"], y0 + r * course["cell_mm"])
                        for r in range(1, course["nrow"] - 1) for c in range(1, course["ncol"] - 1)]
            drawn = page.evaluate(
                "(function (p) { var v = window.cadexReview.viewer(); "
                "return p.map(function (q) { return v.groundAt(q[0], q[1]); }); })(%s)"
                % json.dumps(vertices))
            vertex_gaps = [abs(h - ground(x, y)) for (x, y), h in zip(vertices, drawn)]
            page.evaluate("(function(v){v.setCamera(%s);})(window.cadexReview.viewer())"
                          % json.dumps(CAMERA))
            time.sleep(1.5)
            shot = page.send("Page.captureScreenshot", {"format": "png"}, timeout=120)
            out.write_bytes(base64.b64decode(shot["data"]))
    finally:
        server.shutdown()
        server.server_close()
    print(json.dumps({"shot": str(out), "grid": [course["ncol"], course["nrow"]],
                      "relief_mm": [course["lowest_mm"], course["highest_mm"]],
                      "compared": len(gaps), "worst_gap_mm": max(gaps),
                      "vertices": len(vertex_gaps), "worst_vertex_gap_mm": max(vertex_gaps)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
