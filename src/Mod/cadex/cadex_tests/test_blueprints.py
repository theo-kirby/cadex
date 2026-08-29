# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The blueprint store (ADR-150): store, index, prune, refuse, resolve.

``CadexBlueprints`` imports no FreeCAD, so this suite exercises it exactly
as it runs under cadexd — a temp project root, a real ``script.json``, and
real PNG bytes.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

import CadexBlueprints as blueprints
from CadexScriptStore import CadexProjectScriptStore

#: A real 1x1 PNG, so the magic check passes on honest bytes.
ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
    "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

REVISION = "ab12cd34ef56ab12cd34ef56ab12cd34"
DIGEST = "d1" * 16


def _accepted_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    store = CadexProjectScriptStore(root)
    store.write(
        source="result = {}\n",
        state_updates={
            "accepted_revision": REVISION,
            "accepted_digest": DIGEST,
            "accepted_contract": [{"name": "plate"}, {"name": "boss"}],
        },
    )
    return root


def _png(tmp_path: Path, name: str = "sheet.png", payload: bytes = b"") -> Path:
    path = tmp_path / name
    path.write_bytes(ONE_PIXEL_PNG + payload)
    return path


def test_store_refuses_before_the_first_accepted_revision(tmp_path: Path) -> None:
    root = tmp_path / "project"
    CadexProjectScriptStore(root).write(source="result = {}\n")
    with pytest.raises(ValueError, match="no accepted revision"):
        blueprints.store_project_blueprint(root, str(_png(tmp_path)))


def test_store_indexes_a_sheet_against_the_accepted_pair(tmp_path: Path) -> None:
    root = _accepted_project(tmp_path)
    source = _png(tmp_path)
    entry = blueprints.store_project_blueprint(
        root, str(source), label="the bracket, sectioned",
        meta={"theme": "blueprint"},
    )

    # The entry keys are the contract inspect and the shell both read.
    assert set(entry) == {
        "ordinal", "name", "version", "revision", "digest", "file", "bytes",
        "sha256", "created_at", "label", "outputs", "meta",
    }
    assert entry["ordinal"] == 1
    assert entry["name"] == "" and entry["version"] == 1
    assert entry["revision"] == REVISION
    assert entry["digest"] == DIGEST
    assert entry["file"] == f"0001-{REVISION[:12]}.png"
    assert entry["outputs"] == ["boss", "plate"]
    assert entry["meta"] == {"theme": "blueprint"}
    assert entry["label"] == "the bracket, sectioned"

    stored = root / "blueprints" / entry["file"]
    assert stored.is_file()
    assert stored.read_bytes() == ONE_PIXEL_PNG
    assert entry["bytes"] == len(ONE_PIXEL_PNG)
    assert entry["sha256"] == hashlib.sha256(ONE_PIXEL_PNG).hexdigest()

    index = json.loads(
        (root / "blueprints" / "blueprints.json").read_text(encoding="utf-8")
    )
    assert index["schema"] == "cadex-blueprint-v1"
    assert blueprints.read_blueprints(root) == [entry]


def test_store_refuses_dishonest_or_oversized_input(tmp_path: Path) -> None:
    root = _accepted_project(tmp_path)

    not_png = tmp_path / "sheet.png"
    not_png.write_bytes(b"JFIF not a png at all")
    with pytest.raises(ValueError, match="not a PNG"):
        blueprints.store_project_blueprint(root, str(not_png))

    huge = _png(tmp_path, "huge.png",
                payload=b"\0" * (blueprints.MAX_BLUEPRINT_BYTES + 1))
    with pytest.raises(ValueError, match="caps a"):
        blueprints.store_project_blueprint(root, str(huge))

    good = _png(tmp_path)
    with pytest.raises(ValueError, match="characters"):
        blueprints.store_project_blueprint(
            root, str(good), label="x" * (blueprints.MAX_LABEL_CHARS + 1))
    with pytest.raises(ValueError, match="not JSON-encodable"):
        blueprints.store_project_blueprint(
            root, str(good), meta={"bad": {1, 2}})
    with pytest.raises(ValueError, match="cap is"):
        blueprints.store_project_blueprint(
            root, str(good), meta={"pad": "y" * blueprints.MAX_META_BYTES})
    with pytest.raises(ValueError, match="Could not read"):
        blueprints.store_project_blueprint(root, str(tmp_path / "absent.png"))

    assert blueprints.read_blueprints(root) == []


def test_prune_keeps_the_newest_and_the_ordinals_counting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(blueprints, "BLUEPRINT_LIMIT", 3)
    root = _accepted_project(tmp_path)
    source = _png(tmp_path)
    for _ in range(5):
        blueprints.store_project_blueprint(root, str(source))

    entries = blueprints.read_blueprints(root)
    assert [entry["ordinal"] for entry in entries] == [3, 4, 5]
    kept = {entry["file"] for entry in entries}
    on_disk = {path.name for path in (root / "blueprints").glob("*.png")}
    assert on_disk == kept, "pruned entries take their files with them"


def test_resolve_by_ordinal_revision_prefix_and_filename(tmp_path: Path) -> None:
    root = _accepted_project(tmp_path)
    source = _png(tmp_path)
    first = blueprints.store_project_blueprint(root, str(source))
    second = blueprints.store_project_blueprint(root, str(source))

    assert blueprints.resolve_blueprint(root, 2) == second
    assert blueprints.resolve_blueprint(root, "2") == second
    assert blueprints.resolve_blueprint(root, first["file"]) == first
    # Both sheets share the accepted revision, so its prefix is ambiguous.
    assert blueprints.resolve_blueprint(root, REVISION[:8]) is None
    assert blueprints.resolve_blueprint(root, "") is None
    assert blueprints.resolve_blueprint(root, "no-such") is None


def test_a_name_versions_the_sheet_and_captions_it(tmp_path: Path) -> None:
    """ADR-157: a name is an identity, so storing again revises it."""

    root = _accepted_project(tmp_path)
    source = _png(tmp_path)

    first = blueprints.store_project_blueprint(
        root, str(source), name="  Gearbox   Overview v1 ")
    assert first["name"] == "Gearbox Overview v1"
    assert first["version"] == 1
    # The name collapses to one line, and captions the sheet by default.
    assert first["label"] == "Gearbox Overview v1"
    # The slug is what an exported directory reads as.
    assert first["file"] == "0001-gearbox-overview-v1.png"
    assert (root / "blueprints" / first["file"]).is_file()

    second = blueprints.store_project_blueprint(
        root, str(source), label="now with the housing off",
        name="gearbox overview v1")
    assert second["version"] == 2, "the same name is the next version"
    assert second["label"] == "now with the housing off"
    assert second["file"] == "0002-gearbox-overview-v1.png"

    other = blueprints.store_project_blueprint(root, str(source), name="detail")
    assert other["version"] == 1, "a different name starts its own count"

    # Resolution: the newest version of a name, or a pinned one.
    assert blueprints.resolve_blueprint(root, "gearbox overview v1") == second
    assert blueprints.resolve_blueprint(root, "GEARBOX OVERVIEW V1") == second
    assert blueprints.resolve_blueprint(root, "gearbox overview v1@1") == first
    assert blueprints.resolve_blueprint(root, "gearbox overview v1@9") is None
    assert blueprints.resolve_blueprint(root, "detail") == other
    assert blueprints.resolve_blueprint(root, 1) == first


def test_a_name_is_refused_when_it_is_not_one_line(tmp_path: Path) -> None:
    root = _accepted_project(tmp_path)
    source = _png(tmp_path)

    with pytest.raises(ValueError, match="the cap is 60"):
        blueprints.store_project_blueprint(
            root, str(source), name="x" * (blueprints.MAX_NAME_CHARS + 1))
    with pytest.raises(ValueError, match="one line of plain text"):
        blueprints.store_project_blueprint(root, str(source), name="a\x07b")
    assert blueprints.read_blueprints(root) == []

    # A name of pure punctuation has no slug; the file falls back to the
    # revision prefix rather than becoming "0001-.png".
    punctuation = blueprints.store_project_blueprint(
        root, str(source), name="!!!")
    assert punctuation["file"] == f"0001-{REVISION[:12]}.png"
    assert blueprints.resolve_blueprint(root, "!!!") == punctuation


def test_the_prune_never_drops_a_named_sheets_newest_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A drawing you named is one you meant to come back to (ADR-157)."""

    monkeypatch.setattr(blueprints, "BLUEPRINT_LIMIT", 3)
    root = _accepted_project(tmp_path)
    source = _png(tmp_path)

    kept = blueprints.store_project_blueprint(root, str(source), name="keep me")
    superseded = blueprints.store_project_blueprint(
        root, str(source), name="revised")
    current = blueprints.store_project_blueprint(
        root, str(source), name="revised")
    for _ in range(6):
        blueprints.store_project_blueprint(root, str(source))

    entries = blueprints.read_blueprints(root)
    names = [(entry["name"], entry["version"]) for entry in entries]
    assert ("keep me", 1) in names, "the only version of a name survives"
    assert ("revised", 2) in names and ("revised", 1) not in names, (
        "only the newest version of a name is protected"
    )
    assert [entry["ordinal"] for entry in entries][-3:] == [7, 8, 9]
    assert blueprints.resolve_blueprint(root, "keep me") == kept
    assert blueprints.resolve_blueprint(root, "revised") == current
    assert blueprints.resolve_blueprint(root, superseded["file"]) is None

    on_disk = {path.name for path in (root / "blueprints").glob("*.png")}
    assert on_disk == {entry["file"] for entry in entries}


def test_a_broken_index_reads_as_empty(tmp_path: Path) -> None:
    root = _accepted_project(tmp_path)
    directory = root / "blueprints"
    directory.mkdir(parents=True)
    (directory / "blueprints.json").write_text("not json", encoding="utf-8")
    assert blueprints.read_blueprints(root) == []
