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


HERO = (64, 48)


def _heroes(directory: Path) -> Path:
    """Give a passed evaluation its two heroes (ADR-570), as ``add_heroes`` writes them."""

    report = json.loads((directory / "evaluation.json").read_text(encoding="utf-8"))
    block = {"schema": "cadex-heroes-v1", "state": "ready", "revision": report["accepted_revision"],
             "errors": {}}
    for key, name in (("hero", "hero.png"), ("print_bed", "print-bed.png")):
        (directory / name).write_bytes(STUDIO.png(bytes(STUDIO.PALETTE["bg"]) * (HERO[0] * HERO[1]), *HERO))
        block[key] = {"file": name, "bytes": (directory / name).stat().st_size}
    report["heroes"] = block
    stamp = (directory / "evaluation.json").stat()
    (directory / "evaluation.json").write_text(json.dumps(report))
    os.utime(directory / "evaluation.json", ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    return directory


CAPTION = ("seed 1101 · push 1: 0.84 N at 2.53 s, recovered in 0.62 s · "
           "push 2: 1.31 N at 4.40 s, not settled · fell: tipped at 5.10 s")


def _shove(directory: Path) -> Path:
    """Give a passed evaluation its shove video (ADR-571), as ``add_shove`` writes it."""

    report = json.loads((directory / "evaluation.json").read_text(encoding="utf-8"))
    (directory / "shove.webm").write_bytes(WEBM)
    report["shove"] = {"schema": "cadex-shove-film-v1", "state": "ready", "error": None, "seed": 1101,
                       "caption": CAPTION, "video": {"file": "shove.webm", "bytes": len(WEBM)}}
    stamp = (directory / "evaluation.json").stat()
    (directory / "evaluation.json").write_text(json.dumps(report))
    os.utime(directory / "evaluation.json", ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
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
    assert old["failing"] == [] and old["film"] == {"state": "none", "seeds": [], "sheets": []}
    assert old["evaluated_at"] == "2001-09-09T01:46:40Z"
    assert (new["name"], new["verdict"], new["passed"], new["seeds"], new["relation"]) == (
        "w2-shuffle", "fail", 0, 10, "current")
    assert new["policy_output"] == "walk_policy" and new["policy_sha256"].startswith("7a4e8c23")
    assert new["task_output"] == "walk_task" and new["terminations"] == {"horizon": 8, "tipped": 2}
    # What failed, worst first: stepping and slip on every seed.
    assert new["failing"][:3] == ["W5-steps (10 of 10)", "W5-share (10 of 10)", "W7 (10 of 10)"]
    assert new["film"] == {"state": "ready", "seeds": [1101, 1105], "sheets": [
        {"seed": 1101, "overview": "seed-1101-overview.png", "detail": "seed-1101-detail.png",
         "video": "seed-1101-rollout.webm"},
        {"seed": 1105, "overview": "seed-1105-overview.png", "detail": "seed-1105-detail.png",
         "video": None}]}
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
    assert again["film"] == {"state": "ready", "seeds": [1110], "sheets": [
        {"seed": 1110, "overview": "seed-1110-overview.png", "detail": "seed-1110-detail.png",
         "video": "seed-1110-rollout.webm"}]} and again["stamp"] != row["stamp"]

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


def test_a_passs_heroes_are_listed_and_served_and_a_fail_has_none(served) -> None:
    """ADR-570: the row names the heroes the report names, and only those are served."""

    root, server = served
    directory = _heroes(_passing(root))
    _w2_shuffle(root)
    passed, failed = _json(server.url + "api/project")["evaluations"]
    assert passed["heroes"] == {"hero": "hero.png", "print_bed": "print-bed.png"}
    assert failed["heroes"] == {"hero": None, "print_bed": None}
    for name in ("hero.png", "print-bed.png"):
        status, headers, body = _get(server.url + "evaluation/steady/" + name)
        assert status == 200 and headers["content-type"] == "image/png"
        assert body == (directory / name).read_bytes()
        assert _json(server.url + "api/evaluation/steady")["files"][name]["exists"] is True
        # A hero the failing report does not name is not served from it.
        (root / "evaluations" / "w2-shuffle" / name).write_bytes(body)
        assert _get(server.url + "evaluation/w2-shuffle/" + name)[0] == 404


def test_a_passs_shove_video_is_listed_with_its_caption_and_served(served) -> None:
    """ADR-571: the row names the shove video and the caption the report wrote; nothing else is served."""

    root, server = served
    _shove(_passing(root))
    _w2_shuffle(root)
    passed, failed = _json(server.url + "api/project")["evaluations"]
    assert passed["shove"] == {"state": "ready", "video": "shove.webm", "caption": CAPTION}
    assert failed["shove"] == {"state": "none", "video": None, "caption": None}
    status, headers, body = _get(server.url + "evaluation/steady/shove.webm")
    assert (status, headers["content-type"], body) == (200, "video/webm", WEBM)
    (root / "evaluations" / "w2-shuffle" / "shove.webm").write_bytes(WEBM)
    assert _get(server.url + "evaluation/w2-shuffle/shove.webm")[0] == 404


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
def test_the_2d_viewport_lists_and_plays_each_evaluation_film(tmp_path, browser) -> None:
    """ADR-541: a filmed seed's video and sheets are 2D-viewport sources."""

    from test_review_server import _open, _review_project, serve
    root = _review_project(tmp_path)
    _w2_shuffle(root)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        films = [s for s in page.evaluate("window.cadexReview.sheets()") if s["group"] == "Evaluations"]
        assert [(s["kind"], s["label"].rsplit(" · ", 2)[1:]) for s in films] == [
            ("video", ["seed 1101", "video"]), ("image", ["seed 1101", "filmstrip"]),
            ("image", ["seed 1101", "detail"]), ("image", ["seed 1105", "filmstrip"]),
            ("image", ["seed 1105", "detail"])]
        page.evaluate(f"window.cadexReview.setSheet({json.dumps(films[0]['key'])})", await_promise=True)
        video = page.evaluate("""(function () { var v = document.getElementById('sheet-video');
            return v && {src: v.src, controls: v.controls, muted: v.muted,
                         kind: document.getElementById('sheet-stage').dataset.kind}; })()""")
        assert video["kind"] == "video" and video["controls"] and video["muted"], video
        assert "/evaluation/w2-shuffle/seed-1101-rollout.webm?v=" in video["src"]
        status, headers, body = _get(video["src"])
        assert status == 200 and headers["content-type"] == "video/webm" and body == WEBM
        page.evaluate(f"window.cadexReview.setSheet({json.dumps(films[1]['key'])})", await_promise=True)
        assert page.wait_for("(function(){var i=document.getElementById('sheet-image');"
                             "return i && i.complete && i.naturalWidth})()") == SHEET[0]
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_the_2d_viewport_shows_a_passs_two_heroes_before_its_film(tmp_path, browser) -> None:
    """ADR-570: a passed evaluation's hero and print bed are 2D-viewport images; a fail adds none.
    ADR-571: its shove video follows them, captioned."""

    from test_review_server import _open, _review_project, serve
    root = _review_project(tmp_path)
    _w2_shuffle(root)
    passed = _shove(_heroes(_passing(root)))
    report = json.loads((passed / "evaluation.json").read_text())
    report["film"] = _film(passed, (11,), video=False)
    (passed / "evaluation.json").write_text(json.dumps(report))
    os.utime(passed / "evaluation.json", (1_000_000_000, 1_000_000_000))
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        listed = [(s["kind"], s["label"]) for s in page.evaluate("window.cadexReview.sheets()")
                  if s["group"] == "Evaluations"]
        steady = [label.split(" · ", 1)[1] for kind, label in listed if label.startswith("stand pass")]
        assert steady == ["hero", "print bed", "shoves", "seed 11 · filmstrip", "seed 11 · detail"], listed
        # The shove video plays with the pushes and the ending beside it (ADR-571).
        (shoves,) = [s["key"] for s in page.evaluate("window.cadexReview.sheets()") if s["key"].startswith("shove:")]
        page.evaluate(f"window.cadexReview.setSheet({json.dumps(shoves)})", await_promise=True)
        shown = page.evaluate("""(function () { var v = document.getElementById('sheet-video'),
            c = document.getElementById('sheet-caption');
            return {src: v && v.src, caption: c && c.textContent,
                    below: !!(v && c && c.getBoundingClientRect().top >= v.getBoundingClientRect().bottom - 1)}; })()""")
        assert "/evaluation/steady/shove.webm?v=" in shown["src"] and shown["caption"] == CAPTION, shown
        assert shown["below"], shown
        assert not [label for _kind, label in listed if label.startswith("walk") and "hero" in label]
        assert not [label for _kind, label in listed if "print bed" in label and "pass" not in label]
        for key in [s["key"] for s in page.evaluate("window.cadexReview.sheets()") if s["key"].startswith("hero:")]:
            page.evaluate(f"window.cadexReview.setSheet({json.dumps(key)})", await_promise=True)
            assert page.wait_for("(function(){var i=document.getElementById('sheet-image');"
                                 "return i && i.complete && i.naturalWidth})()") == HERO[0]
            assert "/evaluation/steady/" in page.evaluate("document.getElementById('sheet-image').src")
    finally:
        server.shutdown()
        server.server_close()
