# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""orun2 W1, steps 7-8: a short training run and `evaluate`, seen in the dashboard.

Run after `cadex walk` and `cadex evaluate` have landed on a copy of a robot
project. Serves the dashboard over the projects directory on 127.0.0.1,
drives it in headless Chromium, and writes what the page showed to
``--out/walk-train-steps.json`` with a screenshot per step (PNG). It writes
nothing: training stays on the CLI, and the page only shows it.

    PYTHONPATH=cli pixi run python docs/probes/orun2/w1/walk_train_dashboard.py \
        --projects ~/cadex-projects --project orun2-w1-robin --run w1-gpu-1 \
        --out /tmp/w1/evidence
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import time

from cadex_cli.browser import HeadlessBrowser, find_browser
from cadex_cli.review_server import serve_projects


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects", type=Path, required=True)
    ap.add_argument("--project", required=True)
    ap.add_argument("--run", required=True, help="the walk's run directory name under runs/")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    root = (args.projects / args.project).resolve()
    steps: dict[str, dict] = {}
    server, _thread = serve_projects(args.projects, "127.0.0.1", 0)
    try:
        with HeadlessBrowser(find_browser(), width=1440, height=900) as browser:
            page = browser.page(server.url + "p/%s/" % args.project)
            page.evaluate("window.cadexReview.ready", await_promise=True)
            runs = page.evaluate("window.cadexReview.state().runs")

            # 7. The training run: its curves and its training/rollout record.
            page.evaluate("window.cadexReview.select(%s)" % json.dumps(args.run), await_promise=True)
            page.evaluate("window.cadexFrame && window.cadexFrame.show('curves')")
            page.wait_for("!!document.querySelector('#telemetry [data-metric=iteration]')"
                          " && !document.querySelector('#telemetry .histories p').textContent.includes('loading')",
                          timeout=120)
            time.sleep(0.5)
            page.screenshot(args.out / "w1-7-training.png")
            steps["7_training"] = {
                "runs_listed": runs,
                "selected": page.evaluate("window.cadexReview.state().selected"),
                "metrics": page.evaluate("Object.fromEntries(Array.from(document.querySelectorAll("
                                         "'#telemetry [data-metric]')).map(e => [e.dataset.metric, e.textContent]))"),
                "histories": page.evaluate("Object.fromEntries(Array.from(document.querySelectorAll("
                                           "'#telemetry [data-history]')).map(e => [e.dataset.history, +e.dataset.points]))"),
                "checkpoint_source": page.text("#checkpoint-source"),
                "training_record": page.evaluate("Array.from(document.querySelectorAll('#training tr'))"
                                                 ".map(r => r.textContent)"),
            }

            # 8. The evaluation: the verdict, the per-seed table and the film.
            page.evaluate("window.cadexReview.select('accepted')", await_promise=True)
            page.evaluate("window.cadexFrame && window.cadexFrame.show('evaluation')")
            page.wait_for("['pass','fail'].includes(document.getElementById('evaluation-status').dataset.state)"
                          " && !document.getElementById('evaluation-body').hidden", timeout=120)
            page.wait_for("document.querySelectorAll('#evaluation-film img').length > 0", timeout=60)
            time.sleep(1.0)
            page.screenshot(args.out / "w1-8-evaluate.png")
            steps["8_evaluate"] = {
                "status": page.text("#evaluation-status"),
                "verdict": page.attribute("#evaluation-status", "data-state"),
                "shown": page.evaluate("window.cadexReview.state().evaluation"),
                "predicates": page.evaluate("Array.from(document.querySelectorAll('#evaluation-predicates tbody tr'))"
                                            ".map(r => r.textContent)"),
                "film_images": page.evaluate("document.querySelectorAll('#evaluation-film img').length"),
                "film_video": page.evaluate("document.querySelectorAll('#evaluation-film video').length"),
            }
            steps["progress_tail"] = [line for line in (root / "PROGRESS.md").read_text().splitlines()
                                      if re.match(r"^\| 20", line)][-4:]
    finally:
        server.shutdown()
        server.server_close()
    # No machine paths in what is committed.
    text = json.dumps(steps, indent=1).replace(str(Path.home()) + "/", "~/")
    (args.out / "walk-train-steps.json").write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
