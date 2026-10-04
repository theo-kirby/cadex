# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""orun2 W1, steps 1-6: the headless walk, each step seen in the dashboard.

Run after a design turn (`cadex -p`) has landed on a copy of a robot
project. Serves the dashboard over the projects directory on 127.0.0.1,
drives it in headless Chromium, and writes what each step measured to
``--out/walk-steps.json`` with a screenshot per step (PNG). The writes it
makes are the dashboard's own: the owner's Accept verdict, slider moves,
and the Export button; ``cadex render`` is run as the CLI, since the
dashboard has no render button and shows what render drew.

    PYTHONPATH=cli pixi run python docs/probes/orun2/w1/walk_dashboard.py \
        --projects ~/cadex-projects --project orun2-w1-quad \
        --param shin=52,58,55 --out /tmp/w1/evidence
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

from cadex_cli.browser import HeadlessBrowser, find_browser
from cadex_cli.review_server import serve_projects

REPO = Path(__file__).resolve().parents[4]


def get_json(url: str):
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.loads(response.read())


def git_count(root: Path) -> int:
    return int(subprocess.run(["git", "-C", str(root), "rev-list", "--count", "HEAD"],
                              capture_output=True, text=True, check=True).stdout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects", type=Path, required=True)
    ap.add_argument("--project", required=True)
    ap.add_argument("--param", required=True, help="NAME=v1,v2,... moved on the slider in order")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    root = (args.projects / args.project).resolve()
    name, values = args.param.split("=", 1)
    sweep = [float(v) for v in values.split(",")]
    steps: dict[str, dict] = {}
    server, _thread = serve_projects(args.projects, "127.0.0.1", 0)
    base = server.url
    try:
        with HeadlessBrowser(find_browser(), width=1440, height=900) as browser:
            # 1. The prompt turn: the index lists the project at the revision
            #    the turn left, and the turn among the CLI agent turns.
            listing = get_json(base + "api/projects")
            row = next(p for p in listing["projects"] if p["name"] == args.project)
            turns = [t for t in get_json(base + "api/turns")["turns"] if t.get("project") == args.project]
            index = browser.page(base)
            index.wait_for("document.querySelectorAll('[data-project]').length > 0", timeout=60)
            index.screenshot(args.out / "w1-1-index.png")
            steps["1_prompt"] = {"index_row": row, "cli_turns": turns[:3],
                                 "listed_on_index": index.evaluate(
                                     "!!document.querySelector('[data-project=%s]')" % json.dumps(args.project))}

            # 2. The accepted design, and the owner's Accept verdict on it.
            page = browser.page(base + "p/%s/" % args.project)
            page.evaluate("window.cadexReview.ready", await_promise=True)
            page.evaluate("window.cadexReview.select('accepted')", await_promise=True)
            page.wait_for("['loaded','missing','error'].includes("
                          "document.getElementById('model-status').dataset.state)", timeout=300)
            revision = page.evaluate("window.cadexReview.state().revision")
            model_state = page.attribute("#model-status", "data-state")
            stats = page.evaluate("window.cadexReview.viewer().stats()")
            page.wait_for("document.querySelectorAll('#revision-list li').length > 0", timeout=60)
            if page.attribute("#revision-list li", "data-verdict") != "accepted":
                page.wait_for("!document.getElementById('revision-accept').disabled", timeout=60)
                page.click("#revision-accept")
            page.wait_for("document.querySelector('#revision-list li').dataset.verdict === 'accepted'",
                          timeout=120)
            page.screenshot(args.out / "w1-2-accepted.png")
            steps["2_accepted"] = {"revision": revision, "index_revision": (row.get("accepted") or {}).get("revision"),
                                   "model_state": model_state, "components": stats.get("components"),
                                   "verdict": page.attribute("#revision-list li", "data-verdict"),
                                   "last_revision_write": page.evaluate("window.cadexReview.lastRevision()")}

            # 3. A params sweep on the slider: each move is `cadex params`.
            slider = "#params input[type=range][data-param=%s]" % name
            page.wait_for("!!document.querySelector(%s)" % json.dumps(slider), timeout=60)
            commits = git_count(root)
            moves = []
            for value in sweep:
                before = page.evaluate("window.cadexReview.state().revision")
                started = time.monotonic()
                page.evaluate("(() => { const s = document.querySelector(%s); s.value = %s;"
                              " s.dispatchEvent(new Event('input')); s.dispatchEvent(new Event('change')); })()"
                              % (json.dumps(slider), json.dumps(str(value))))
                page.wait_for("(window.cadexReview.lastWrite() || {}).value === %s" % json.dumps(value),
                              timeout=1800, interval=0.5)
                write = page.evaluate("window.cadexReview.lastWrite()")
                page.wait_for("['loaded','missing','error'].includes("
                              "document.getElementById('model-status').dataset.state)"
                              " && window.cadexReview.state().model"
                              " && window.cadexReview.state().model.revision === window.cadexReview.state().revision",
                              timeout=300)
                moves.append({"value": value, "ok": write.get("ok"), "error": write.get("error"),
                              "seconds": round(time.monotonic() - started, 2),
                              "revision_before": before, "revision_after": write.get("revision"),
                              "model_state": page.attribute("#model-status", "data-state")})
            page.screenshot(args.out / "w1-3-sweep.png")
            steps["3_params_sweep"] = {"param": name, "moves": moves,
                                       "commits_added": git_count(root) - commits}

            # 4. Render: `cadex render`, then the concept sheet on the page.
            started = time.monotonic()
            render = subprocess.run([str(REPO / "cadex"), "render", "--project", str(root), "--json"],
                                    capture_output=True, text=True, timeout=3600)
            render_s = round(time.monotonic() - started, 1)
            envelope = json.loads(render.stdout or "{}")
            page.evaluate("window.cadexReview.refresh()", await_promise=True)
            page.wait_for("(window.cadexReview.state().concept || {}).available === true", timeout=120)
            page.evaluate("window.cadexFrame && window.cadexFrame.show('concept')")
            time.sleep(1.0)
            page.screenshot(args.out / "w1-4-render.png")
            steps["4_render"] = {"exit": render.returncode, "seconds": render_s,
                                 "envelope_ok": envelope.get("ok"),
                                 "concept": page.evaluate("window.cadexReview.state().concept"),
                                 "status": page.text("#concept-status")}

            # 5 and 6. Export: STEP and STL, and the MJCF staged beside them.
            page.evaluate("window.cadexFrame && window.cadexFrame.show('model')")
            page.wait_for("!document.getElementById('export-run').disabled", timeout=60)
            started = time.monotonic()
            page.click("#export-run")
            page.wait_for("['done','error'].includes(document.getElementById('export-status').dataset.state)",
                          timeout=3600, interval=0.5)
            export_s = round(time.monotonic() - started, 1)
            files = page.evaluate("Array.from(document.querySelectorAll('#export-list li[data-name]'))"
                                  ".map(li => li.dataset.name)")
            downloads = {}
            for suffix in (".step", ".stl", ".xml"):
                pick = next((f for f in files if f.endswith(suffix)), None)
                if pick is None:
                    continue
                got = page.download('#export-list li[data-name=%s] a' % json.dumps(pick), timeout=120)
                head = got.path.read_bytes()[:400]
                downloads[suffix] = {"name": pick, "bytes": got.received_bytes,
                                     "head_ok": {".step": head.startswith(b"ISO-10303-21;"),
                                                 ".stl": head.lstrip().startswith(b"solid") or len(head) > 84,
                                                 ".xml": b"<mujoco" in head}[suffix]}
            page.scroll_into_view("#export-panel")
            page.screenshot(args.out / "w1-5-export.png")
            steps["5_6_export"] = {"state": page.attribute("#export-status", "data-state"),
                                   "status": page.text("#export-status"), "seconds": export_s,
                                   "files": files, "downloads": downloads,
                                   "step": sum(f.endswith(".step") for f in files),
                                   "stl": sum(f.endswith(".stl") for f in files),
                                   "mjcf": [f for f in files if f.endswith(".xml")]}
            steps["progress_tail"] = [line for line in (root / "PROGRESS.md").read_text().splitlines()
                                      if re.match(r"^\| 20", line)][-8:]
    finally:
        server.shutdown()
        server.server_close()
    # No machine paths in what is committed.
    text = json.dumps(steps, indent=1).replace(str(Path.home()) + "/", "~/")
    (args.out / "walk-steps.json").write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
