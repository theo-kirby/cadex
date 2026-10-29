"""orun21 T1: the tile patch, the maze and the corridor (ADR-853) as the dashboard draws them.

    pixi run python docs/probes/orun21/t1_shot.py PROJECT OUT_PREFIX

Serves PROJECT read-only on a loopback port and opens it in headless Chromium.
It hands the viewer the engine's own drawing (`CadexDynamics.terrain_drawing`)
of two courses: a listed one with a tile patch, a 3 x 3 maze and a 4 x 1
corridor, and course 2 of a drawn pool of tile patches and mazes. It writes
OUT_PREFIX-<shot>.png for each of SHOTS, and prints the worst gap between the
drawn ground (`viewer.groundAt`) and the engine's (`terrain_box_ground_mm`) at
2,000 points over the course, a millimetre clear of any wall face.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "cli"))
sys.path.insert(0, str(ROOT / "src" / "Mod" / "cadex"))

import CadexDynamics  # noqa: E402
from cadex_cli.browser import HeadlessBrowser, find_browser  # noqa: E402
from cadex_cli.review_server import serve, terrain_block  # noqa: E402

LAYOUT = {"dir": "col", "sizes": [0.92, 0.08], "children": [
    {"dir": "row", "sizes": [0.8, 0.2], "children": [{"editor": "view3d"}, {"editor": "training"}]},
    {"editor": "version"}]}

LISTED = {"form": "boxes", "x_range_mm": [-1000.0, 8000.0], "y_range_mm": [-2500.0, 2500.0],
          "features": [
              {"kind": "tiles", "x_mm": 2200.0, "y_mm": -1300.0, "length_mm": 1800.0,
               "width_mm": 1500.0, "cell_mm": 300.0, "height_mm": 150.0},
              {"kind": "maze", "x_mm": 5600.0, "y_mm": 0.0, "cells_x": 3, "cells_y": 3,
               "cell_mm": 900.0, "height_mm": 450.0, "thickness_mm": 60.0},
              {"kind": "maze", "x_mm": 2200.0, "y_mm": 1300.0, "cells_x": 4, "cells_y": 1,
               "cell_mm": 700.0, "height_mm": 350.0, "thickness_mm": 60.0}]}
DRAWN = {"form": "boxes", "x_range_mm": [-2000.0, 9000.0], "y_range_mm": [-2000.0, 2000.0],
         "random": {"seed": 10, "courses": 6, "tile_mm": [40.0, 120.0], "tiles": 2,
                    "wall_mm": [300.0, 500.0], "maze_cells": [1, 3]}}

#: Each shot: the course, and a camera three-quarter on and above what it shows.
SHOTS = [
    ("maze", "listed", {"target": [5600.0, 0.0, 0.0], "yaw": -2.3, "pitch": 0.95, "distance": 5200.0}),
    ("tiles-corridor", "listed", {"target": [2200.0, 0.0, 0.0], "yaw": -2.0, "pitch": 0.7,
                                  "distance": 5000.0}),
    ("drawn-course2", "drawn", {"target": [3000.0, 300.0, 0.0], "yaw": -2.2, "pitch": 0.8,
                                "distance": 4800.0}),
]


def main() -> int:
    project, out = Path(sys.argv[1]).expanduser(), sys.argv[2]
    listed = CadexDynamics.terrain_grid(LISTED)["descriptor"]
    drawn = CadexDynamics.terrain_grid(DRAWN)["descriptor"]
    pooled = {key: value for key, value in drawn.items() if key != "pool"}
    pooled.update(drawn["pool"][2])
    courses = {"listed": listed, "drawn": pooled}
    server, _thread = serve(project, "127.0.0.1", 0)
    said = []
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
            rng = random.Random(853)
            for name, which, camera in SHOTS:
                course = courses[which]
                block = terrain_block(json.loads(json.dumps(CadexDynamics.terrain_drawing(course))))
                count = page.evaluate("window.cadexReview.viewer().setTerrain(%s)" % json.dumps(block))
                (x0, x1), (y0, y1) = course["x_range_mm"], course["y_range_mm"]
                points = [(rng.uniform(x0, x1), rng.uniform(y0, y1)) for _ in range(2000)]
                heights = page.evaluate(
                    "(function (p) { var v = window.cadexReview.viewer(); "
                    "return p.map(function (q) { return v.groundAt(q[0], q[1]); }); })(%s)"
                    % json.dumps(points))
                gaps = []
                for (x, y), height in zip(points, heights):
                    engine = CadexDynamics.terrain_box_ground_mm(course, x, y)
                    near_wall = any(min(abs(x - xa), abs(x - xb), abs(y - ya), abs(y - yb)) < 1.0
                                    for box in course["boxes"]
                                    for (xa, xb), (ya, yb) in [(box["x_range_mm"], box["y_range_mm"])])
                    if height is not None and not near_wall:
                        gaps.append(abs(height - engine))
                page.evaluate("(function(v){v.setCamera(%s);})(window.cadexReview.viewer())"
                              % json.dumps(camera))
                time.sleep(1.5)
                shot = page.send("Page.captureScreenshot", {"format": "png"}, timeout=120)
                path = Path(f"{out}-{name}.png")
                path.write_bytes(base64.b64decode(shot["data"]))
                said.append({"shot": str(path), "drawn_records": count,
                             "kinds": sorted({f["kind"] for f in course["features"]}),
                             "boxes": len(course["boxes"]), "compared": len(gaps),
                             "worst_gap_mm": max(gaps)})
    finally:
        server.shutdown()
        server.server_close()
    print(json.dumps(said, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
