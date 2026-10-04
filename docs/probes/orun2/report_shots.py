# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""orun2 C1: the closing report's dashboard screenshots, and its defects re-checked.

Read-only. Serves `cadex app` over a projects directory on 127.0.0.1, opens
the index and one project page in headless Chromium
(`cli/cadex_cli/browser.py`), and writes a PNG per view plus
``report-shots.json`` with what each defect check measured:

- **speck**: the model's pixel coverage of the canvas as the Model tab first
  draws it, against the same after pressing **Fit**, and the bounds Fit
  frames (a task floor the engine calls world geometry sizes nothing, ADR-525);
- **colours**: whether the parts are painted by appearance role (ADR-522) or
  by the per-index debug palette;
- **CLI transcript**: whether the latest CLI agent turn's text, or a `look`
  image of it, appears anywhere on the project page.

    PYTHONPATH=cli pixi run python docs/probes/orun2/report_shots.py \
        --projects ~/cadex-projects --project orun2-w1-quad --out docs/probes/orun2
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import urllib.request

from cadex_cli.browser import HeadlessBrowser, find_browser
from cadex_cli.review_server import serve_projects


def get_json(url: str):
    with urllib.request.urlopen(url, timeout=120) as response:
        return json.loads(response.read())


def shrink(path: Path, limit: int = 300_000) -> None:
    """Hold a committed PNG to the charter's 300 KB by a 256-colour palette."""
    if path.stat().st_size > limit:
        from PIL import Image
        Image.open(path).convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(
            path, optimize=True)


def coverage(page) -> dict:
    px = page.evaluate("window.cadexReview.viewer().modelPixels()")
    px["fraction"] = round(px["count"] / float(px["width"] * px["height"]), 4)
    return px


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects", type=Path, required=True)
    ap.add_argument("--project", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    found: dict[str, object] = {}
    server, _thread = serve_projects(args.projects, "127.0.0.1", 0)
    base = server.url
    try:
        with HeadlessBrowser(find_browser(), width=1440, height=900) as browser:
            index = browser.page(base)
            index.wait_for("document.querySelectorAll('[data-project]').length > 0", timeout=60)
            time.sleep(1.0)
            index.screenshot(args.out / "dashboard-index.png")
            found["index_projects"] = index.evaluate("document.querySelectorAll('[data-project]').length")

            page = browser.page(base + "p/%s/" % args.project)
            page.evaluate("window.cadexReview.ready", await_promise=True)
            page.evaluate("window.cadexReview.select('accepted')", await_promise=True)
            page.wait_for("['loaded','missing','error'].includes("
                          "document.getElementById('model-status').dataset.state)", timeout=300)
            found["model_state"] = page.attribute("#model-status", "data-state")
            found["first_tab"] = page.attribute("#stage", "data-active")
            page.screenshot(args.out / "dashboard-concept.png")
            page.click("#stage-tabs [data-stage=model]")
            time.sleep(1.0)
            found["speck_as_opened"] = coverage(page)
            page.click("#model-fit")
            time.sleep(0.5)
            found["speck_after_fit"] = coverage(page)
            # What Fit frames: the bounds of every drawn component but world geometry.
            found["viewer_bounds"] = page.evaluate("window.cadexReview.viewer().stats().bounds")
            found["viewer_components"] = page.evaluate(
                "Object.keys(window.cadexReview.viewer().stats().poses || {}).slice(0, 4)")
            page.screenshot(args.out / "dashboard-model.png")

            found["parts_summary"] = page.evaluate(
                "(() => { const s = document.getElementById('parts-summary');"
                " return s ? {appearance: s.dataset.appearance, text: s.textContent} : null; })()")

            turns = [t for t in get_json(base + "api/turns")["turns"] if t.get("project") == args.project]
            found["cli_turns_listed"] = len(turns)
            body = page.evaluate("document.body.innerText")
            # A CLI turn's own words: its PROGRESS.md summary is listed on the
            # index; the question is whether the page carries the agent's text.
            found["turn_transcript_shown"] = page.evaluate(
                "!document.getElementById('turn-transcript').hidden")
            found["look_images_on_page"] = page.evaluate(
                "Array.from(document.images).filter(i => /look/.test(i.src)).length")
            found["latest_turn"] = turns[0] if turns else None
            found["page_text_chars"] = len(body)

            page.click("#stage-tabs [data-stage=evaluation]")
            time.sleep(1.0)
            page.screenshot(args.out / "dashboard-evaluation.png")
    finally:
        server.shutdown()
        server.server_close()
    for png in args.out.glob("dashboard-*.png"):
        shrink(png)
    text = json.dumps(found, indent=1).replace(str(Path.home()) + "/", "~/")
    (args.out / "report-shots.json").write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
