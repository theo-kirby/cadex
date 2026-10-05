# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Each accepted revision's model is kept by content hash per part (orun3 V3, ADR-546).

The engine prunes an old revision's attempt, so the CLI keeps each accepted
model in ``review/revisions/``: a part that did not change between two
revisions is the same blob, and a revision accepted before the store
existed says so instead of borrowing another revision's geometry.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from cadex_cli.__main__ import main
from cadex_cli.bridge import Bridge
from cadex_cli.client import CadexdClient, open_project
from cadex_cli.report import EXIT_OK
from cadex_cli.revision_meshes import (
    INDEX_NAME, NOT_RETAINED, PARTS_DIR, SCHEMA, _prune, read_index, retain, revision_models, store_root,
)

# A biped, as small as one gets: a torso on two legs, the feet a parameter.
BIPED = """
p = params(foot=num(40.0, unit="mm", min=20.0, max=90.0, step=1.0))
result = {
    "torso": part.box(60.0, 40.0, 30.0),
    "leg_l": part.box(12.0, 12.0, 50.0),
    "leg_r": part.box(12.0, 12.0, 50.0),
    "foot_l": part.box(p.foot, 20.0, 6.0),
}
"""


def _run(capsys, *argv: str) -> tuple[int, dict]:
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


def _blobs(root: Path) -> dict[str, int]:
    parts = store_root(root) / PARTS_DIR
    return {path.name: path.stat().st_size for path in parts.iterdir()} if parts.is_dir() else {}


def test_each_accepted_revision_is_kept_and_an_unchanged_part_costs_nothing(engine, tmp_path, capsys) -> None:
    root = tmp_path / "orun3-biped-meshes"
    (tmp_path / "biped.py").write_text(BIPED, encoding="utf-8")
    project = ["--project", str(root)]
    code, first = _run(capsys, "script", "--set", str(tmp_path / "biped.py"), *project)
    assert code == EXIT_OK, first
    assert any("kept revision 1's model" in note for note in first["notes"])
    one = read_index(root)["revisions"]["1"]
    assert one["revision"] == first["accepted_revision"] and one["digest"] == first["digest"]
    assert set(one["parts"]) == {"torso", "leg_l", "leg_r", "foot_l"}
    # Two identical legs are one blob: a .tess.bin and its .tess.json.
    assert one["parts"]["leg_l"]["sha256"] == one["parts"]["leg_r"]["sha256"]
    assert len(_blobs(root)) == 2 * 3 and one["added_bytes"] == sum(_blobs(root).values())

    code, wide = _run(capsys, "params", "--set", "foot=70", *project)
    assert code == EXIT_OK, wide
    two = read_index(root)["revisions"]["2"]
    # Only the foot changed, so only the foot is new bytes.
    for name in ("torso", "leg_l", "leg_r"):
        assert two["parts"][name]["sha256"] == one["parts"][name]["sha256"], name
    assert two["parts"]["foot_l"]["sha256"] != one["parts"]["foot_l"]["sha256"]
    assert len(_blobs(root)) == 2 * 4
    foot = two["parts"]["foot_l"]["sha256"]
    assert two["added_bytes"] == _blobs(root)[f"{foot}.tess.bin"] + _blobs(root)[f"{foot}.tess.json"]
    assert 0 < two["added_bytes"] < two["full_bytes"]

    # A second session on the same acceptance keeps nothing twice.
    before = (store_root(root) / INDEX_NAME).read_bytes()
    assert retain(root)["status"] == "kept"
    assert (store_root(root) / INDEX_NAME).read_bytes() == before

    code, listed = _run(capsys, "revision", "list", *project)
    assert [(row["ordinal"], row["retained"]) for row in listed["revisions"]["models"]] == [(1, True), (2, True)]
    rows = revision_models(root)
    assert rows[1]["parts"]["foot_l"]["sha256"] == foot
    assert {c["name"] for c in rows[1]["components"]} >= {"torso", "foot_l"}


def test_a_bridge_build_keeps_its_model_like_a_cli_one(engine, tmp_path) -> None:
    """``cadex mcp`` holds one session for a whole turn; each accepted build
    through it is kept when it lands, not when the session closes."""

    root = tmp_path / "orun3-biped-mcp"
    root.mkdir()
    client = CadexdClient(engine)
    client.start()
    try:
        open_project(client, root)
        with Bridge(client, project_root=root) as bridge:
            reply = bridge.call("write_script", {"source": BIPED})
            assert reply["is_error"] is False, reply
            assert [row["retained"] for row in revision_models(root)] == [True]
            reply = bridge.call("set_params", {"values": {"foot": 55}})
            assert reply["is_error"] is False, reply
            assert [row["retained"] for row in revision_models(root)] == [True, True]
    finally:
        client.shutdown()


def _history(root: Path, revisions: list[str]) -> None:
    trail = root / "script_history"
    trail.mkdir(parents=True, exist_ok=True)
    entries = [{"ordinal": n, "revision": rev, "file": f"{n:04d}-{rev[:12]}.py"}
               for n, rev in enumerate(revisions, start=1)]
    (trail / "history.json").write_text(json.dumps({"entries": entries}), encoding="utf-8")


def _store(root: Path, rows: dict[str, dict]) -> None:
    store = store_root(root)
    (store / PARTS_DIR).mkdir(parents=True, exist_ok=True)
    (store / INDEX_NAME).write_text(json.dumps({"schema": SCHEMA, "revisions": rows}), encoding="utf-8")


def test_a_revision_without_its_own_model_says_why_and_borrows_none(tmp_path) -> None:
    root = tmp_path / "orun3-biped-old"
    _history(root, ["a" * 64, "b" * 64, "c" * 64, "d" * 64])
    blob = "f" * 64
    _store(root, {
        # Ordinal 2 retained; 3 names another revision; 4's blob is gone.
        "2": {"ordinal": 2, "revision": "b" * 64, "digest": "x", "parts": {"torso": {"sha256": blob}}},
        "3": {"ordinal": 3, "revision": "e" * 64, "parts": {"torso": {"sha256": blob}}},
        "4": {"ordinal": 4, "revision": "d" * 64, "parts": {"foot_l": {"sha256": "0" * 64}}},
    })
    (store_root(root) / PARTS_DIR / f"{blob}.tess.bin").write_bytes(b"\0" * 8)
    rows = revision_models(root)
    assert [row["retained"] for row in rows] == [False, True, False, False]
    assert rows[0]["reason"] == NOT_RETAINED and "parts" not in rows[0]
    assert "not shown" in rows[2]["reason"] and "parts" not in rows[2]
    assert "missing from the store: foot_l" in rows[3]["reason"] and "parts" not in rows[3]
    # Nothing accepted yet: nothing kept, and nothing written.
    assert retain(tmp_path / "orun3-biped-empty")["status"] == "skipped"
    assert not store_root(tmp_path / "orun3-biped-empty").exists()


def test_the_store_is_bounded_by_the_trail_it_shadows(tmp_path) -> None:
    """The engine keeps 25 sources (HISTORY_LIMIT); a row whose ordinal left
    the trail goes, and so does every blob only it named."""

    root = tmp_path / "orun3-biped-prune"
    _history(root, ["b" * 64])
    shared, gone = "1" * 64, "2" * 64
    _store(root, {})
    for sha in (shared, gone):
        for suffix in (".tess.bin", ".tess.json"):
            (store_root(root) / PARTS_DIR / f"{sha}{suffix}").write_bytes(b"x")
    index = {"schema": SCHEMA, "revisions": {
        "0": {"revision": "a" * 64, "parts": {"torso": {"sha256": shared}, "foot_l": {"sha256": gone}}},
        "1": {"revision": "b" * 64, "parts": {"torso": {"sha256": shared}}},
    }}
    _prune(root, index)
    assert list(index["revisions"]) == ["1"]
    assert sorted(os.listdir(store_root(root) / PARTS_DIR)) == [f"{shared}.tess.bin", f"{shared}.tess.json"]
