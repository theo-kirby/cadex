# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex asset``, and ``put_asset`` in the tool surface (ADR-190).

The lifecycle audit (``docs/MUJOCO.md`` §7c, row 5) found the one write to
the project store that is not the script's — a trained policy coming home —
reachable only over raw NDJSON. These pin the two headless doors: the
no-model subcommand a pipeline drives, and the tool the agent is offered.
The engine-needing tests skip without a built engine; the tool-surface one
reads ``OP_ARG_SPECS`` off the source tree and does not.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cadex_cli.__main__ import main
from cadex_cli.report import EXIT_OK, EXIT_REJECTED, EXIT_USAGE

BLOCK = """
block = part.box(10.0, 10.0, 10.0)
result = {"block": block}
"""


def _run(capsys, *argv: str) -> tuple[int, dict]:
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def project(engine, tmp_path, capsys) -> Path:
    script = tmp_path / "block.py"
    script.write_text(BLOCK, encoding="utf-8")
    root = tmp_path / "project"
    code, _ = _run(capsys, "script", "--set", str(script), "--project", str(root))
    assert code == EXIT_OK
    return root


def test_a_policy_and_its_receipt_come_home_with_their_digests(
    project, tmp_path, capsys
) -> None:
    """The store takes the file, and the envelope carries the sha256 the
    script needs — read from the engine's reply, never recomputed here."""

    policy = tmp_path / "walk.cxpolicy"
    policy.write_bytes(b"CXPOLICY-not-a-real-policy\n" * 64)
    receipt = tmp_path / "walk-task.json"
    receipt.write_text(json.dumps({"task": "walk"}), encoding="utf-8")

    code, envelope = _run(
        capsys,
        "asset",
        "--put",
        str(policy),
        "--put",
        str(receipt),
        "--project",
        str(project),
    )
    assert code == EXIT_OK, envelope
    assert (project / "assets" / "walk.cxpolicy").read_bytes() == policy.read_bytes()
    assert (project / "assets" / "walk-task.json").is_file()
    by_name = {item["name"]: item for item in envelope["assets"]}
    assert set(by_name) == {"walk.cxpolicy", "walk-task.json"}, by_name
    assert by_name["walk.cxpolicy"]["sha256"] == hashlib.sha256(
        policy.read_bytes()
    ).hexdigest()
    assert by_name["walk.cxpolicy"]["bytes"] == policy.stat().st_size
    assert sum("stored " in note for note in envelope["notes"]) == 2, envelope
    # Storing changes no geometry: the accepted revision is untouched.
    assert envelope["digest"] == "", envelope

    # Listing is the same command with nothing to put.
    code, listed = _run(capsys, "asset", "--project", str(project))
    assert code == EXIT_OK, listed
    assert [item["name"] for item in listed["assets"]] == [
        "walk-task.json",
        "walk.cxpolicy",
    ]


def test_a_name_keeps_the_suffix_and_replaces_what_it_names(
    project, tmp_path, capsys
) -> None:
    first = tmp_path / "a.cxpolicy"
    first.write_bytes(b"one")
    second = tmp_path / "b.cxpolicy"
    second.write_bytes(b"two")

    code, stored = _run(
        capsys, "asset", "--put", str(first), "--name", "walk.cxpolicy",
        "--project", str(project),
    )
    assert code == EXIT_OK, stored
    code, replaced = _run(
        capsys, "asset", "--put", str(second), "--name", "walk.cxpolicy",
        "--project", str(project),
    )
    assert code == EXIT_OK, replaced
    assert (project / "assets" / "walk.cxpolicy").read_bytes() == b"two"
    assert len(replaced["assets"]) == 1, replaced

    # A name that changes the format is the engine's refusal, exit 3.
    code, refused = _run(
        capsys, "asset", "--put", str(first), "--name", "walk.stl",
        "--project", str(project),
    )
    assert code == EXIT_REJECTED, refused
    assert ".cxpolicy" in refused["error"], refused


def test_a_file_the_store_does_not_hold_is_refused_by_the_engine(
    project, tmp_path, capsys
) -> None:
    stray = tmp_path / "notes.txt"
    stray.write_text("no", encoding="utf-8")
    code, envelope = _run(
        capsys, "asset", "--put", str(stray), "--project", str(project)
    )
    assert code == EXIT_REJECTED, envelope
    assert "notes.txt" in envelope["error"], envelope
    assert not (project / "assets" / "notes.txt").exists()


def test_a_missing_file_is_a_usage_error_before_the_engine_runs(
    tmp_path, capsys
) -> None:
    code, envelope = _run(
        capsys,
        "asset",
        "--put",
        str(tmp_path / "absent.cxpolicy"),
        "--project",
        str(tmp_path / "project"),
    )
    assert code == EXIT_USAGE, envelope
    assert "absent.cxpolicy" in envelope["error"], envelope
    assert not (tmp_path / "project").exists()


def test_a_name_for_two_files_is_a_usage_error(tmp_path, capsys) -> None:
    for stem in ("a", "b"):
        (tmp_path / f"{stem}.cxpolicy").write_bytes(b"x")
    code, envelope = _run(
        capsys,
        "asset",
        "--put",
        str(tmp_path / "a.cxpolicy"),
        "--put",
        str(tmp_path / "b.cxpolicy"),
        "--name",
        "walk.cxpolicy",
        "--project",
        str(tmp_path / "project"),
    )
    assert code == EXIT_USAGE, envelope
    assert "--name" in envelope["error"], envelope


def test_the_model_can_bring_a_file_into_the_store(protocol) -> None:
    """The tool surface is generated, but the op list is chosen.

    Asked to bring a trained policy home, the agent invented a command
    (§7c). ``put_asset`` is the one write to the store that is not the
    script's, and nothing else in the surface performs it.
    """

    from cadex_cli.tools import CLI_TOOL_OPS, tool_definitions

    assert CLI_TOOL_OPS[-1] == "put_asset"
    by_name = {item["name"]: item for item in tool_definitions(protocol)}
    schema = by_name["put_asset"]["input_schema"]
    assert schema["required"] == ["source_path"], schema
    assert set(schema["properties"]) == {"source_path", "name"}, schema
    description = by_name["put_asset"]["description"]
    assert ".cxpolicy" in description and "sha256" in description
    assert "assembly.policy" in description


def test_the_prompt_tells_the_agent_it_cannot_train() -> None:
    from cadex_cli.agent import CLI_OVERLAY

    assert "put_asset" in CLI_OVERLAY
    assert "cannot train" in CLI_OVERLAY
    assert "cadex asset --put" in CLI_OVERLAY
