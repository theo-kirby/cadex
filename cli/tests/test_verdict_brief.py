# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The verdict brief every build path carries, and panel rows that say their verdict (ADR-689).

panel-cat-3 (2026-10-13) built from the shell with ``cadex script --set
--json``, whose envelope carried no fit, and ran seven MCP ``rebuild``\\ s
(about 57 minutes) only to read which panels failed; ``inspect
scope=clearance path=/panels/N`` had the measurements and not the verdict.
After a shell build, the MCP ``look`` reopened the engine with a restore and
then rebuilt, once for 11 minutes. These pin the three fixes.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path

from cadex_cli import __main__ as cli
from cadex_cli.bridge import Bridge
from cadex_cli.clearance import (
    VERDICT_BRIEF_LIMIT, fit_summary, judge_panel_rows, verdict_brief, verdict_lines,
)

from fake_cadexd import FakeCadexd, accepted_reply, inspect_reply

REVISION = "a" * 64


def _component(name, *, role=None, family=None):
    row = {"component": name, "source_output": name}
    if role:
        row["role"] = role
    if family:
        row["catalog"] = {"family": family, "part_number": "x"}
        row["mount_axes"] = []
    return row


def _measured(name, p90, **extra):
    row = {"component": name, "covers": ["board"], "samples": 400, "inner_samples": 180,
           "gap_p10_mm": p90 / 3, "gap_median_mm": p90 / 2, "gap_p90_mm": p90,
           "gap_max_mm": p90 * 1.2, "hug_fraction": 0.0, "egg_ratio": 1.3, "coverage": 0.8,
           "wall_p10_mm": 1.9, "wall_median_mm": 2.0, "wall_p90_mm": 2.4,
           "size_mm": [120.0, 80.0, 30.0], "points": [[0.0, 0.0, 10.0]]}
    row.update(extra)
    return row


def _value(extra_panels=0):
    """A clearance value with a floating, a struck and an unmounted panel, an
    overlapping pair, an unswept joint and a loose purchased part."""

    panels = ["egg", "rub", "loose"] + [f"p{k}" for k in range(extra_panels)]
    return {
        "revision": REVISION, "assembly": "asm", "available": True,
        "pose": "initial solved pose (not swept motion)",
        "components": [_component("deck", role="frame"), _component("board"), _component("leg"),
                       _component("motor", family="bldc")]
                      + [_component(name, role="panel") for name in panels],
        "pairs": [{"first": "board", "second": "rub", "distance_mm": 0.0,
                   "common_volume_mm3": 12.0},
                  {"first": "deck", "second": "egg", "distance_mm": 0.0,
                   "common_volume_mm3": 0.0, "intent": {"kind": "attached", "minimum_mm": 0.0}}],
        "attachments": [{"first": "deck", "second": "egg", "status": "touching"},
                        {"first": "deck", "second": "rub", "status": "touching"}],
        "clearance_sweep": {"status": "incomplete", "joints": [
            {"joint": "hip", "status": "complete", "pairs": [
                {"first": "leg", "second": "rub", "minimum_distance_mm": 0.0,
                 "maximum_common_volume_mm3": 40.0, "relative_motion": True}]},
            {"joint": "knee", "status": "incomplete", "reason": "runtime budget exceeded",
             "pairs": []}]},
        "panels": [_measured("egg", 31.3), _measured("rub", 2.0), _measured("loose", 2.0)]
                  + [_measured(f"p{k}", 2.0) for k in range(extra_panels)],
    }


def test_the_brief_names_every_verdict_and_the_worst_rows_in_a_few_lines():
    fit = fit_summary(_value())
    brief = verdict_brief(fit)
    assert brief["fit"] == "fail" and brief["revision"] == REVISION[:12]
    assert brief["failing_pairs"] == 1 and brief["pairs"] == ["board ∩ rub: intersection 12 mm³"]
    assert brief["sweep"]["verdict"] == "fail"
    assert brief["sweep"]["pairs"] == ["leg ∩ rub through hip: intersection 40 mm³"]
    assert brief["sweep"]["unswept"] == ["knee: incomplete, runtime budget exceeded"]
    panels = brief["panels"]
    assert (panels["verdict"], panels["failing"], panels["panel_count"]) == ("fail", 3, 3)
    by = {line.split(":")[0]: line for line in panels["failing_panels"]}
    assert by["egg"].startswith("egg: floating -- its inner face's p90 gap is 31.3 mm")
    assert by["rub"].startswith("rub: colliding, colliding in motion -- it overlaps board")
    assert "leg (hip)" in by["rub"]
    assert by["loose"].startswith("loose: unmounted")
    assert brief["mounting"]["verdict"] == "unknown"
    assert brief["mounting"]["not_held"][0].startswith("motor: unknown -- No solved placement")
    assert "inspect scope=clearance" in brief["rest"]
    # One string per row: the brief is small whatever the block's size.
    assert len(json.dumps(brief)) < 2500
    text = "\n".join(verdict_lines(brief))
    assert "panels fail  3 of 3 failing" in text and "  egg: floating" in text
    assert "sweep  fail  1 of 2 joint(s) swept, 1 failing pair(s)" in text
    assert "\nwelds " not in text  # every weld touches: nothing to say


def test_the_brief_cuts_long_lists_and_counts_the_rest():
    value = _value(extra_panels=20)
    for row in value["panels"][3:]:
        row["inner_samples"] = 0  # no part faces what it covers: floating
    brief = verdict_brief(fit_summary(value))
    panels = brief["panels"]
    assert panels["failing"] == 23
    assert len(panels["failing_panels"]) == VERDICT_BRIEF_LIMIT
    assert panels["failing_panels_more"] == 23 - VERDICT_BRIEF_LIMIT
    assert f"... and {23 - VERDICT_BRIEF_LIMIT} more" in "\n".join(verdict_lines(brief))


def test_an_unavailable_fit_is_said_and_never_a_pass():
    brief = verdict_brief({"verdict": "unavailable", "error": "fit measurements could not be read: x"})
    assert brief == {"revision": "", "fit": "unavailable",
                     "reason": "fit measurements could not be read: x"}
    assert verdict_lines(brief) == ["fit    unavailable: fit measurements could not be read: x"]
    assert verdict_brief(None)["fit"] == "unavailable"


def test_a_panel_row_carries_its_verdict_and_findings():
    fit = fit_summary(_value())
    rows = judge_panel_rows(_value()["panels"], fit)
    by = {row["component"]: row for row in rows}
    assert by["egg"]["verdict"] == "fail" and by["egg"]["findings"] == ["floating"]
    assert "31.3 mm" in by["egg"]["detail"]
    assert by["rub"]["colliding_in_motion"][0]["joint"] == "hip"
    # The measurements stay as published.
    assert by["egg"]["gap_p90_mm"] == 31.3
    one = judge_panel_rows(_value()["panels"][2], fit)
    assert one["verdict"] == "fail" and one["findings"] == ["unmounted"]
    # A row the block does not name, or no block, is left alone.
    assert judge_panel_rows({"component": "ghost"}, fit) == {"component": "ghost"}
    assert judge_panel_rows([{"component": "egg"}], None) == [{"component": "egg"}]


def _fake(value):
    def inspect(args):
        if args.get("scope") == "clearance":
            path = str(args.get("path") or "")
            if path.startswith("/panels/"):
                return inspect_reply(args, value["panels"][int(path.rsplit("/", 1)[1])])
            if path == "/panels":
                return inspect_reply(args, value["panels"])
            return inspect_reply(args, value)
        if args.get("scope") == "script":
            path = str(args.get("path") or "")
            found = {"/revisions": {"working_revision": REVISION},
                     "/params/specs": [], "/params/values": {}}.get(path, "")
            return inspect_reply(args, found)
        return inspect_reply(args, {"revision": REVISION, "assembly": "", "components": [],
                                    "component_count": 0, "catalog_counts": {},
                                    "uncatalogued_sources": [], "derived_catalog_sources": [],
                                    "verdict": "undeclared", "regions": [],
                                    "rigid_appendages": []})
    return FakeCadexd(replies={"inspect": inspect,
                               "write_script": lambda _a: accepted_reply("write_script", REVISION)})


def test_the_mcp_build_reply_carries_the_same_brief():
    client = _fake(_value())
    with Bridge(client) as bridge:
        result = bridge.call("write_script", {"source": "result = {}"})
    view = json.loads(result["content"][0]["text"])
    assert view["verdicts"] == verdict_brief(fit_summary(_value()))
    assert view["verdicts"]["panels"]["failing"] == 3


def test_an_mcp_inspect_of_a_panel_row_says_its_verdict_without_a_build():
    """A session opened after a shell build has no build reply: the fit is
    read once, for the stored accepted revision, and kept."""

    client = _fake(_value())
    with Bridge(client) as bridge:
        result = bridge.call("inspect", {"scope": "clearance", "path": "/panels/0"})
        row = json.loads(result["content"][0]["text"])["value"]
        assert row["component"] == "egg" and row["verdict"] == "fail"
        assert row["findings"] == ["floating"] and "31.3 mm" in row["detail"]
        rows = json.loads(bridge.call("inspect", {"scope": "clearance", "path": "/panels"})
                          ["content"][0]["text"])["value"]
        assert [r["verdict"] for r in rows] == ["fail", "fail", "fail"]
    assert not client.args_for("rebuild")
    # Read once (every page of the scope), then served from the kept block.
    whole = [a for a in client.args_for("inspect") if a.get("scope") == "clearance"
             and not str(a.get("path") or "").startswith("/panels")]
    assert len(whole) == 1


def test_cadex_script_json_carries_the_brief(tmp_path, monkeypatch, capsys):
    client = _fake(_value())

    @contextmanager
    def session(args, report, *, restore=True):
        report.project_root = str(tmp_path)
        yield client.engine, client

    monkeypatch.setattr(cli, "_engine_session", session)
    monkeypatch.setattr(cli, "_record_progress", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_commit_run", lambda *a, **k: None)
    source = tmp_path / "s.py"
    source.write_text("result = {}\n", encoding="utf-8")
    assert cli.main(["script", "--set", str(source), "--project", str(tmp_path), "--json"]) == 0
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["verdicts"] == verdict_brief(fit_summary(_value()))
    assert "fit" not in envelope  # the whole block is `cadex clearance` away
    # ...and the prose report prints the same brief.
    assert cli.main(["script", "--set", str(source), "--project", str(tmp_path)]) == 0
    text = capsys.readouterr().out
    assert "panels fail  3 of 3 failing, 0 advisory" in text
    assert "  loose: unmounted" in text


def _retained_project(tmp_path, display_reply):
    """A project store whose accepted attempt retained ``display_reply``'s tessellation."""

    root = tmp_path / "project"
    staging = root / "script_artifacts" / REVISION / "attempts" / "1"
    staging.mkdir(parents=True)
    outputs = []
    for name, entry in display_reply["display"].items():
        item = {"name": name, "artifact_kind": entry["artifact_kind"],
                "solved_placement_matrix": entry["placement"]}
        if entry.get("source_output"):
            item["source_output"] = entry["source_output"]
        tess = entry.get("tessellation")
        if tess:
            for key in ("artifact_path", "sidecar_path"):
                target = staging / Path(tess[key]).name
                target.write_bytes(Path(tess[key]).read_bytes())
            item["display"] = {**tess, "artifact_path": Path(tess["artifact_path"]).name,
                               "sidecar_path": Path(tess["sidecar_path"]).name}
        outputs.append(item)
    (staging / "result.json").write_text(json.dumps(
        {"ok": True, "digest": "d" * 64, "outputs": outputs}), encoding="utf-8")
    (root / "script.json").write_text(json.dumps({
        "schema": "cadex-project-script-v1", "accepted_revision": REVISION,
        "accepted_digest": "d" * 64,
        "accepted_attempt": {"revision": REVISION,
                             "staging": str(staging.relative_to(root))}}), encoding="utf-8")
    return root


def test_look_after_a_shell_build_draws_the_retained_attempt_and_rebuilds_nothing(tmp_path):
    from test_look import _reply

    (tmp_path / "mesh").mkdir()
    root = _retained_project(tmp_path, _reply(tmp_path / "mesh"))
    client = FakeCadexd()
    with Bridge(client, project_root=root) as bridge:
        result = bridge.call("look", {"views": ["top"]})
        assert result["is_error"] is False, result["content"][0]["text"]
        assert json.loads(result["content"][0]["text"])["revision"] == REVISION
        bridge.call("look", {"views": ["front"]})
    assert not client.args_for("rebuild")
    scopes = {args.get("scope") for op, args in client.calls if op == "inspect"}
    assert {"clearance", "inventory"} <= scopes
    # Nothing was built, so the session lands no row of its own.
    assert bridge.state.last_accepted is None


def test_mcp_opens_unrestored_and_restores_only_for_the_live_document(monkeypatch, tmp_path):
    opens = []

    @contextmanager
    def session(args, report, *, restore=True):
        opens.append(restore)
        report.project_root = str(tmp_path)
        yield client.engine, client

    client = _fake(_value())
    monkeypatch.setattr(cli, "_engine_session", session)
    monkeypatch.setattr(cli, "begin_activity", lambda *a, **k: "")
    monkeypatch.setattr(cli, "append_activity", lambda *a, **k: None)
    mcp = cli.McpSession.__new__(cli.McpSession)
    mcp.args = type("Args", (), {"project": str(tmp_path), "engine": "", "wait": False})()
    mcp.engine = client.engine
    mcp._stack = mcp._bridge = mcp._client = mcp._report = None
    mcp._open_seconds, mcp._restored = 0.0, False
    mcp.call("inspect", {"scope": "clearance", "path": "/panels/0"})
    assert opens == [False]
    mcp.call("inspect", {"scope": "document"})
    assert opens == [False, True]
    mcp.call("inspect", {"scope": "object", "target": "Box"})
    assert opens == [False, True]
    mcp.close()
