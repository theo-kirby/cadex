# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The review dashboard shows an evaluation (ADR-459, DASHBOARD.md §17).

The failing fixture is the real thing: ot10's ``w2-2`` shuffle as ``cadex
evaluate`` measured it on the frozen walk contract, from the receipt
committed under ``docs/probes/ot11/retained/``. The passing one is written
here. The server half needs nothing; the page half needs a Chromium and
skips without one.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from cadex_cli import review_server
from cadex_cli.studio import STUDIO

from test_review_design import SIZES, _rendered
from test_review_server import (  # noqa: F401 - fixtures
    REVISION_A, REVISION_B, _get, _json, browser, needs_browser, served)

REPO = Path(__file__).resolve().parents[2]
W2_RECEIPT = REPO / "docs" / "probes" / "ot11" / "retained" / "p2-w2-2-evaluation.json"
SHEET = (1036, 776)
WEBM = b"\x1a\x45\xdf\xa3 not a real clip, only bytes to serve"


def _film(directory: Path, seeds=(1101,), *, video: bool = True) -> dict:
    rows = []
    for position, seed in enumerate(seeds):
        row = {"seed": seed, "trace_sha256": "t" * 64, "video": None}
        for key in ("overview", "detail"):
            name = f"seed-{seed}-{key}.png"
            (directory / name).write_bytes(STUDIO.png(bytes(STUDIO.PALETTE["bg"]) * (SHEET[0] * SHEET[1]), *SHEET))
            row[key] = {"file": name, "sha256": "c" * 64, "bytes": (directory / name).stat().st_size,
                        "width": SHEET[0], "height": SHEET[1], "frames": 12,
                        "times_s": [0.5 * k for k in range(12)], "view": f"the {key} view"}
        if video and position == 0:
            name = f"seed-{seed}-rollout.webm"
            (directory / name).write_bytes(WEBM)
            row["video"] = {"file": name, "sha256": "e" * 64, "bytes": len(WEBM), "frames": 101,
                            "fps": 10, "sim_seconds": 10.0}
        rows.append(row)
    return {"schema": "cadex-evaluation-film-v1", "state": "ready", "error": None,
            "materials": {"source": "the accepted assembly's inventory", "declared": True},
            "seeds": rows}


def _w2_shuffle(root: Path, name: str = "w2-shuffle", *, revision: str = REVISION_B,
                film: bool = True) -> Path:
    """The w2-2 shuffle's evaluation, as if of this project's accepted revision."""

    directory = root / "evaluations" / name
    directory.mkdir(parents=True)
    report = json.loads(W2_RECEIPT.read_text(encoding="utf-8"))
    report["accepted_revision"] = revision
    # The receipt carries the real film block; its sheets are not all committed,
    # so the fixture states its own, or none.
    del report["film"]
    if film:
        report["film"] = _film(directory, (1101, 1105))
    (directory / "seed-1101-trace.json").write_text("{}")
    (directory / "evaluation.json").write_text(json.dumps(report))
    return directory


def _passing(root: Path, name: str = "steady", *, revision: str = REVISION_A) -> Path:
    directory = root / "evaluations" / name
    directory.mkdir(parents=True)
    seeds = []
    for seed, tilt in ((11, 3.5), (12, 4.25)):
        seeds.append({
            "seed": seed, "pass": True, "void": "", "failing": [],
            "predicates": [{"id": "upright", "metric": "max_tilt_deg", "value": tilt, "min": None,
                            "max": 30.0, "pass": True, "why": ""}],
            "metrics": {"completed": 1.0, "max_tilt_deg": tilt},
            "episode": {"steps": 200, "duration_s": 4.0, "termination": "", "truncated": True},
            "reward": {"total": 8.0, "terms": [{"label": "alive", "per_step": 0.04, "total": 8.0}]},
            "drawn": {"disturbance": []}, "trace": {"file": f"seed-{seed}-trace.json"}})
    (directory / "evaluation.json").write_text(json.dumps({
        "schema": "cadex-evaluation-v1", "verdict": "pass", "accepted_revision": revision,
        "policy_output": "hold", "policy_sha256": "9" * 64, "task_output": "stand", "task_label": "stand",
        "seeds": seeds,
        "summary": {"pass": True, "seeds": 2, "passed": [11, 12], "failed": [], "void": [],
                    "terminations": {"horizon": 2},
                    "predicates": [{"id": "upright", "metric": "max_tilt_deg", "min": None, "max": 30.0,
                                    "passed": 2, "failed_seeds": [],
                                    "value": {"min": 3.5, "median": 3.875, "max": 4.25}}]}}))
    # Older than the shuffle's, whatever order the fixtures were written in.
    os.utime(directory / "evaluation.json", (1_000_000_000, 1_000_000_000))
    return directory


# -- the server ------------------------------------------------------------------

def test_the_project_lists_each_evaluation_as_a_bounded_summary(served) -> None:
    root, server = served
    assert _json(server.url + "api/project")["evaluations"] == []

    _w2_shuffle(root)
    _passing(root)
    old, new = _json(server.url + "api/project")["evaluations"]
    assert (old["name"], old["verdict"], old["passed"], old["seeds"], old["relation"]) == (
        "steady", "pass", 2, 2, "historical")
    assert old["failing"] == [] and old["film"] == {"state": "none", "seeds": []}
    assert old["evaluated_at"] == "2001-09-09T01:46:40Z"
    assert (new["name"], new["verdict"], new["passed"], new["seeds"], new["relation"]) == (
        "w2-shuffle", "fail", 0, 10, "current")
    assert new["policy_output"] == "walk_policy" and new["policy_sha256"].startswith("7a4e8c23")
    assert new["task_output"] == "walk_task" and new["terminations"] == {"horizon": 8, "tipped": 2}
    # What failed, worst first: stepping and slip on every seed.
    assert new["failing"][:3] == ["W5-steps (10 of 10)", "W5-share (10 of 10)", "W7 (10 of 10)"]
    assert new["film"] == {"state": "ready", "seeds": [1101, 1105]}
    # A summary: no per-seed row travels in the list a poll fetches.
    assert not any(isinstance(value, (list, dict)) and "metrics" in json.dumps(value)
                   for value in new.values())
    assert len(json.dumps(new)) < 2000


def test_a_rewritten_report_is_read_again_and_an_invalid_one_is_not_listed(served) -> None:
    root, server = served
    directory = _w2_shuffle(root, film=False)
    (row,) = _json(server.url + "api/project")["evaluations"]
    assert row["film"]["state"] == "none"

    report = json.loads((directory / "evaluation.json").read_text())
    report["film"] = _film(directory, (1110,))
    (directory / "evaluation.json").write_text(json.dumps(report))
    (again,) = _json(server.url + "api/project")["evaluations"]
    assert again["film"] == {"state": "ready", "seeds": [1110]} and again["stamp"] != row["stamp"]

    other = root / "evaluations" / "junk"
    other.mkdir()
    (other / "evaluation.json").write_text(json.dumps({"schema": "something-else", "summary": {}}))
    (root / "evaluations" / "empty").mkdir()
    assert [r["name"] for r in _json(server.url + "api/project")["evaluations"]] == ["w2-shuffle"]


def test_one_evaluation_is_served_whole_with_what_of_its_film_is_on_disk(served) -> None:
    root, server = served
    directory = _w2_shuffle(root)
    (directory / "seed-1105-detail.png").unlink()
    detail = _json(server.url + "api/evaluation/w2-shuffle")

    assert detail["name"] == "w2-shuffle" and detail["relation"] == "current"
    assert detail["report"] == json.loads((directory / "evaluation.json").read_text())
    assert len(detail["report"]["seeds"]) == 10
    assert detail["files"]["seed-1101-overview.png"]["exists"] is True
    assert detail["files"]["seed-1101-rollout.webm"] == {"exists": True, "error": None, "bytes": len(WEBM)}
    assert detail["files"]["seed-1105-detail.png"] == {"exists": False, "error": None, "bytes": None}

    for missing in ("api/evaluation/nothing", "api/evaluation/..", "api/evaluation/w2-shuffle%2F..",
                    "api/evaluation/w2%20shuffle"):
        assert _get(server.url + missing)[0] == 404, missing


def test_only_the_report_and_the_film_it_names_are_served(served) -> None:
    root, server = served
    directory = _w2_shuffle(root)

    status, headers, body = _get(server.url + "evaluation/w2-shuffle/seed-1101-overview.png")
    assert status == 200 and headers["content-type"] == "image/png"
    assert body == (directory / "seed-1101-overview.png").read_bytes()
    status, headers, body = _get(server.url + "evaluation/w2-shuffle/seed-1101-rollout.webm")
    assert (status, headers["content-type"], body) == (200, "video/webm", WEBM)
    status, headers, body = _get(server.url + "evaluation/w2-shuffle/evaluation.json?download=1")
    assert status == 200 and "attachment" in headers["content-disposition"]
    assert json.loads(body)["verdict"] == "fail"

    # The trace is in the directory and is not part of the film; nor is anything unnamed.
    assert (directory / "seed-1101-trace.json").is_file()
    (directory / "notes.png").write_bytes(b"x")
    for refused in ("seed-1101-trace.json", "notes.png", "seed-1110-overview.png", "..%2F..%2Fscript.json"):
        assert _get(server.url + "evaluation/w2-shuffle/" + refused)[0] == 404, refused
    assert _get(server.url + "evaluation/nothing/evaluation.json")[0] == 404


def test_a_film_file_that_points_outside_the_evaluation_is_never_served(served) -> None:
    root, server = served
    directory = _w2_shuffle(root)
    secret = root / "secret.png"
    secret.write_bytes(b"outside")
    (directory / "seed-1101-detail.png").unlink()
    (directory / "seed-1101-detail.png").symlink_to(secret)
    report = json.loads((directory / "evaluation.json").read_text())
    report["film"]["seeds"][0]["overview"]["file"] = "../../secret.png"
    (directory / "evaluation.json").write_text(json.dumps(report))

    files = _json(server.url + "api/evaluation/w2-shuffle")["files"]
    assert "../../secret.png" not in files
    assert files["seed-1101-detail.png"]["exists"] is False
    assert _get(server.url + "evaluation/w2-shuffle/seed-1101-detail.png")[0] == 404


def test_an_idle_poll_parses_no_report_twice(served, monkeypatch) -> None:
    root, server = served
    _w2_shuffle(root)
    _passing(root)
    review_server._evaluation_cache.clear()
    parsed = []
    real = review_server._evaluation_report
    monkeypatch.setattr(review_server, "_evaluation_report",
                        lambda directory: parsed.append(directory.name) or real(directory))
    for _ in range(3):
        assert len(_json(server.url + "api/project")["evaluations"]) == 2
    assert sorted(parsed) == ["steady", "w2-shuffle"]


# -- the page ----------------------------------------------------------------------

def _shown(page, name: str) -> None:
    page.wait_for("window.cadexReview.state().evaluation"
                  f" && window.cadexReview.state().evaluation.name === {json.dumps(name)}")


@needs_browser
@pytest.mark.parametrize("size", sorted(SIZES))
def test_the_page_shows_the_shuffle_failing_for_its_steps_and_its_slip(served, browser, size) -> None:
    root, server = served
    _w2_shuffle(root)
    _passing(root)
    page = _rendered(browser, server.url, size)
    _shown(page, "w2-shuffle")

    assert page.attribute("#evaluation-status", "data-state") == "fail"
    status = page.text("#evaluation-status")
    assert status.startswith("fail: 0 of 10 seeds pass · policy walk_policy (7a4e8c233214) on task walk_task")
    assert "the accepted design" in status and "failing W5-steps (10 of 10)" in status
    assert page.evaluate("window.cadexReview.state().evaluation") == {
        "name": "w2-shuffle", "verdict": "fail", "seeds": 10, "film": "ready", "filmed": [1101, 1105]}

    # Per predicate: the bound, the tally and the spread.
    rows = page.evaluate(
        "Array.from(document.querySelectorAll('#evaluation-predicates tbody tr')).map("
        "r => [r.dataset.predicate].concat(Array.from(r.cells).slice(1, 4).map(c => c.textContent),"
        " r.cells[3].dataset.pass))")
    assert len(rows) == 11
    by_id = {row[0]: row[1:] for row in rows}
    assert by_id["W5-steps"] == ["steps_min", "≥ 4", "0 of 10", "false"]
    assert by_id["W7"] == ["slip_share_max", "≤ 0.15", "0 of 10", "false"]
    assert by_id["W1"][2:] == ["8 of 10", "false"] and by_id["W6"][2:] == ["6 of 10", "false"]

    # Per seed and per predicate: the verdict, how it ended, each value against its bound.
    seeds = page.evaluate(
        "Array.from(document.querySelectorAll('#evaluation-seeds tbody tr')).map("
        "r => [r.dataset.seed, r.cells[1].textContent, r.cells[2].textContent, r.dataset.filmed])")
    assert [row[0] for row in seeds] == [str(seed) for seed in range(1101, 1111)]
    assert all(row[1] == "fail" for row in seeds)
    assert seeds[6][2] == "tipped at 6.26 s" and seeds[0][2] == "horizon at 10 s"
    assert [row[0] for row in seeds if row[3] == "true"] == ["1101", "1105"]
    head = page.evaluate("Array.from(document.querySelectorAll('#evaluation-seeds thead th')).map(n => n.textContent)")
    assert head[:3] == ["seed", "verdict", "ended"] and head[3:] == [row[0] for row in rows]
    report = json.loads(W2_RECEIPT.read_text())
    best = next(row for row in report["seeds"] if row["seed"] == 1109)
    steps = next(item for item in best["predicates"] if item["id"] == "W5-steps")
    at = head.index("W5-steps") + 1
    cell = page.evaluate(
        f"(c => [c.textContent, c.dataset.pass, c.title])(document.querySelector("
        f"'#evaluation-seeds tr[data-seed=\"1109\"] td:nth-child({at})'))")
    assert cell == ["1", "false", steps["why"]] and steps["value"] == 1

    # The behaviour metrics and the reward, term by term, a column a seed.
    metrics = page.evaluate(
        "Array.from(document.querySelectorAll('#evaluation-metrics tbody tr')).map(r => r.dataset.metricRow)")
    assert {"steps_min", "step_share_min", "slip_share_max", "duty_factor_min",
            "step_clearance_hip_heights_min", "mean_forward_speed_mm_s", "max_tilt_deg",
            "max_drift_mm", "max_heading_deg"} <= set(metrics)
    assert page.evaluate("document.querySelectorAll('#evaluation-metrics thead th').length") == 11
    terms = page.evaluate(
        "Array.from(document.querySelectorAll('#evaluation-reward tbody tr')).map("
        "r => [r.dataset.term, r.cells[9].textContent])")
    assert [row[0] for row in terms] == ["alive", "upright", "speed_error", "sideways", "yaw_rate", "total"]
    assert terms[-1][1] == "835.98"            # seed 1109, the best paid, barely stepped

    # The film: both sheets of each filmed seed, and the first seed's video.
    page.wait_for("Array.from(document.querySelectorAll('#evaluation-film img')).every("
                  "n => n.complete && n.naturalWidth > 0) || true")
    film = page.evaluate(
        "Array.from(document.querySelectorAll('#evaluation-film li')).map(li => [li.dataset.filmSeed,"
        " Array.from(li.querySelectorAll('[data-film]')).map(n => n.dataset.film + ':' + n.tagName)])")
    assert film == [["1101", ["overview:IMG", "detail:IMG", "video:VIDEO"]],
                    ["1105", ["overview:IMG", "detail:IMG"]]]
    assert page.evaluate("document.querySelector('#evaluation-film img').getAttribute('src')").startswith(
        "/evaluation/w2-shuffle/seed-1101-overview.png?v=")
    assert page.attribute("#evaluation-download", "href").endswith("/evaluation/w2-shuffle/evaluation.json?download=1")
    assert "dark prototype floor" in page.text("#evaluation-film-note")

    if size == "desk":
        # A tab on the stage, its dot the verdict; the page itself never scrolls.
        assert page.attribute("#evaluation-dot", "data-state") == "fail"
        page.click("#stage-tabs [data-stage='evaluation']")
        assert page.evaluate("document.getElementById('stage').dataset.active") == "evaluation"
        assert page.evaluate("document.getElementById('evaluation').checkVisibility({visibilityProperty: true})")
        assert page.evaluate("document.documentElement.scrollHeight <= innerHeight")
        page.wait_for("(n => n.complete && n.naturalWidth === %d)(document.querySelector('#evaluation-film img'))"
                      % SHEET[0])
    else:
        # In the column after the videos, and its wide tables scroll inside the card.
        assert page.rect("#videos-region")["y"] < page.rect("#evaluation")["y"] < page.rect("#record")["y"]
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.evaluate("(n => n.scrollWidth > n.clientWidth)("
                             "document.getElementById('evaluation-seeds').parentElement)")
    assert page.evaluate("Array.from(document.querySelectorAll('#evaluation *')).every("
                         "n => parseFloat(getComputedStyle(n).fontSize) >= 12)")


@needs_browser
def test_the_reader_picks_another_evaluation_and_a_historical_one_never_reads_as_current(served, browser) -> None:
    root, server = served
    _w2_shuffle(root)
    _passing(root)
    page = _rendered(browser, server.url, "desk")
    _shown(page, "w2-shuffle")
    buttons = page.evaluate(
        "Array.from(document.querySelectorAll('#evaluation-list button')).map("
        "b => [b.dataset.evaluation, b.getAttribute('aria-pressed'), b.textContent])")
    assert [row[:2] for row in buttons] == [["w2-shuffle", "true"], ["steady", "false"]]
    assert buttons[1][2].endswith("pass 2/2 · historical")

    page.click("#stage-tabs [data-stage='evaluation']")
    page.click("#evaluation-list button[data-evaluation='steady']")
    _shown(page, "steady")
    assert page.attribute("#evaluation-status", "data-state") == "pass"
    status = page.text("#evaluation-status")
    assert status.startswith("pass: 2 of 2 seeds pass") and "historical: not the accepted design" in status
    assert page.attribute("#evaluation-dot", "data-state") == "pass"
    assert page.evaluate("document.querySelectorAll('#evaluation-seeds tbody tr').length") == 2
    assert page.text("#evaluation-seeds tbody tr td:nth-child(2)") == "pass"
    assert page.evaluate("(c => [c.textContent, c.dataset.pass])(document.querySelector("
                         "'#evaluation-predicates tbody tr td:nth-child(4)'))") == ["2 of 2", "true"]
    assert "no film" in page.text("#evaluation-film-note")
    assert page.evaluate("document.querySelectorAll('#evaluation-film li').length") == 0
    # The pick holds across a poll.
    page.evaluate("window.cadexReview.refresh()", await_promise=True)
    assert page.evaluate("window.cadexReview.state().evaluation.name") == "steady"


@needs_browser
def test_a_project_with_no_evaluation_says_what_makes_one(served, browser) -> None:
    root, server = served
    page = _rendered(browser, server.url, "desk")
    assert page.attribute("#evaluation-status", "data-state") == "empty"
    assert "cadex evaluate" in page.text("#evaluation-status")
    assert page.evaluate("document.getElementById('evaluation-body').hidden")
    assert page.evaluate("!('state' in document.getElementById('evaluation-dot').dataset)")
    assert page.evaluate("window.cadexReview.state().evaluation") is None

    # One landing while the page is open is on the next poll.
    _w2_shuffle(root)
    page.evaluate("window.cadexReview.refresh()", await_promise=True)
    _shown(page, "w2-shuffle")
    assert page.attribute("#evaluation-status", "data-state") == "fail"
