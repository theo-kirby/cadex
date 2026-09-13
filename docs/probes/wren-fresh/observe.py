"""Observe the PERSISTENT operator dashboard during real GPU training (D3, D10).

Opens the already-running private-network server (URL from the environment;
never starts or stops one), checks that a fresh visit selects the run that is
training right now, exercises orbit/zoom on its retained model, and records for
a bounded window the trainer's committed progress.json iteration beside the
iteration the page shows. Writes <RUN>-observe.json and a screenshot beside
itself. Assertion failures never touch the trainer.
"""
import json, os, time
from pathlib import Path
from cdp_browser import HeadlessBrowser, find_browser

root = Path(os.environ["PROJECT"]).resolve()
run = os.environ["RUN"]
url = os.environ["URL"]
progress = root / "runs" / run / "train" / "progress.json"
window_s = float(os.environ.get("WINDOW_S", "240"))
want_updates = int(os.environ.get("UPDATES", "6"))

def file_iteration():
    try:
        d = json.loads(progress.read_text())
        return d.get("state"), int(d.get("iteration")), float(d.get("updated_at"))
    except (OSError, ValueError, TypeError):
        return None, None, None

result = {"url": url, "run": run, "persistent_server": True, "samples": [], "first_seen": {}}
try:
    with HeadlessBrowser(find_browser()) as browser:
        page = browser.page(url)
        page.evaluate("window.cadexReview.ready", await_promise=True)
        page.wait_for("['loaded','missing','error'].includes(document.getElementById('model-status').dataset.state)", timeout=60)
        result["project_name"] = page.text("#project-name")
        result["accepted"] = page.text("#accepted-line")
        result["runs"] = page.evaluate("window.cadexReview.state().runs")
        # D10: a fresh visit must land on the active training run without a click.
        result["default_view_kind"] = page.text("#view-kind")
        result["current_run_label"] = page.text("#current-run")
        assert result["default_view_kind"] == "RUN " + run, result["default_view_kind"]
        page.wait_for("document.getElementById('telemetry').dataset.state === 'training'", timeout=30)
        result["view_revision"] = page.text("#view-revision")
        result["view_relation"] = page.text("#view-relation")
        result["model_state"] = page.attribute("#model-status", "data-state")
        result["model_components"] = page.text("#model-components")
        result["params"] = page.text("#params")
        record = json.loads((root / "runs" / run / "run.json").read_text())
        assert result["view_revision"] == record["model"]["accepted_revision"]
        page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
        assert page.evaluate("window.cadexReview.viewer().nonBackgroundPixels()") > 1000
        page.scroll_into_view("#viewer")
        rect = page.rect("#viewer"); cx = rect["x"] + rect["width"] / 2; cy = rect["y"] + rect["height"] / 2
        before = page.evaluate("window.cadexReview.viewer().camera()")
        page.drag(cx, cy, cx + 100, cy + 40)
        orbit = page.evaluate("window.cadexReview.viewer().camera()")
        page.wait_for(f"window.cadexReview.viewer().camera().yaw !== {before['yaw']}")
        page.wheel(cx, cy, -240)
        page.wait_for("window.cadexReview.viewer().camera().distance < %s" % orbit["distance"])
        result["orbit_zoom"] = True
        start = time.time(); file_seen = {}; page_seen = {}
        while time.time() - start < window_s and len(page_seen) < want_updates + 1:
            state, fit, fat = file_iteration()
            shown = page.text("[data-metric=iteration]").split(": ")[1]
            pit = int(shown) if shown.lstrip("-").isdigit() else None
            now = time.time()
            if fit is not None and fit not in file_seen:
                file_seen[fit] = {"committed_at": fat, "polled_at": now}
            if pit is not None and pit not in page_seen:
                page_seen[pit] = now
                result["samples"].append({
                    "t": round(now - start, 2), "file_state": state, "file_iteration": fit, "page_iteration": pit,
                    "telemetry_state": page.attribute("#telemetry", "data-state"),
                    "freshness": page.attribute("#freshness", "data-state"),
                    "reward": page.text("[data-metric=reward_per_step]"), "loss": page.text("[data-metric=loss]"),
                    "episode_steps": page.text("[data-metric=episode_steps]"),
                    "curve_points": page.attribute("[data-history=curve]", "data-points"),
                    "loss_points": page.attribute("[data-history=loss_curve]", "data-points"),
                    "checkpoints": page.evaluate("document.querySelectorAll('#checkpoints li').length"),
                })
            time.sleep(0.25)
        for it, seen in page_seen.items():
            if it in file_seen:
                result["first_seen"][str(it)] = {
                    "committed_to_page_s": round(seen - file_seen[it]["committed_at"], 2),
                    "polled_to_page_s": round(seen - file_seen[it]["polled_at"], 2)}
        result["page_iterations"] = sorted(page_seen)
        result["file_iterations"] = sorted(file_seen)
        result["reload_count"] = page.evaluate("performance.getEntriesByType('navigation').length")
        page.screenshot(root / "evidence" / (run + "-observe.png"))
        assert len(page_seen) >= 7
        assert result["reload_count"] == 1
        assert all(0 <= x["committed_to_page_s"] < 5 for x in result["first_seen"].values())
        result["ok"] = True
finally:
    (root / "evidence" / (run + "-observe.json")).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k not in ("samples", "params", "runs")}, indent=2))
print("samples:", len(result["samples"]))
