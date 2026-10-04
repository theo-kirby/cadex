# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Going back through the revisions: list, reject, restore (ADR-506, orun2 D2 item 4).

``cadex revision`` reads the engine's stored trail (``script_history/``,
ADR-045) and puts a stored version back through the engine's own
``write_script`` and ``set_params``. The owner's verdicts, and the
dashboard's buttons that wrote them, went with the dashboard's writes and
the turns that read them (ADR-537, ADR-538).
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from cadex_cli.__main__ import main
from cadex_cli.project_docs import PROGRESS_NAME
from cadex_cli.report import EXIT_OK, EXIT_USAGE
from cadex_cli.revisions import previous, read_history, read_source, select

PLATE = """
p = params(width=num(30.0, unit="mm", min=10.0, max=90.0, step=1.0))
result = {"plate": part.box(p.width, 20.0, 6.0)}
"""
THICK = PLATE.replace("20.0, 6.0", "20.0, 12.0")


def _trail(root: Path, entries: list[dict]) -> None:
    history = root / "script_history"
    history.mkdir(parents=True)
    for entry in entries:
        (history / entry["file"]).write_text(f"# {entry['ordinal']}\n", encoding="utf-8")
    (history / "history.json").write_text(json.dumps({"entries": entries}), encoding="utf-8")


def test_the_trail_is_read_and_selected_the_way_the_engine_selects(tmp_path) -> None:
    root = tmp_path / "p"
    assert read_history(root) == []
    entries = [{"ordinal": n, "revision": rev, "file": f"{n:04d}-{rev[:12]}.py"}
               for n, rev in ((1, "aa11"), (2, "ab22"), (3, "aa11"), (4, "cc44"))]
    _trail(root, entries)
    assert [e["ordinal"] for e in read_history(root)] == [1, 2, 3, 4]
    assert select(read_history(root), "2")["revision"] == "ab22"
    assert select(read_history(root), "CC")["ordinal"] == 4
    with pytest.raises(ValueError, match="2 do"):
        select(read_history(root), "aa")  # two entries carry aa11
    with pytest.raises(ValueError, match="no single"):
        select(read_history(root), "zz")
    with pytest.raises(ValueError, match="name a revision"):
        select(read_history(root), "")
    # Before the latest acceptance of a revision, skipping repeats of it.
    assert previous(read_history(root), "cc44")["ordinal"] == 3
    assert previous(read_history(root), "aa11")["ordinal"] == 2
    with pytest.raises(ValueError, match="nothing to go back to"):
        previous(read_history(root)[:1], "aa11")
    with pytest.raises(ValueError, match="not in the stored trail"):
        previous(read_history(root), "dd")
    assert read_source(root, entries[0]) == "# 1\n"
    (root / "script_history" / entries[1]["file"]).unlink()
    with pytest.raises(ValueError, match="missing"):
        read_source(root, entries[1])


def _run(capsys, *argv: str) -> tuple[int, dict]:
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


def test_reject_and_restore_through_the_engine(engine, tmp_path, capsys) -> None:
    root = tmp_path / "plate"
    (tmp_path / "plate.py").write_text(PLATE, encoding="utf-8")
    (tmp_path / "thick.py").write_text(THICK, encoding="utf-8")
    project = ["--project", str(root)]
    code, first = _run(capsys, "script", "--set", str(tmp_path / "plate.py"), *project)
    assert code == EXIT_OK
    code, wide = _run(capsys, "params", "--set", "width=50", *project)
    assert code == EXIT_OK
    code, thick = _run(capsys, "script", "--set", str(tmp_path / "thick.py"), *project)
    assert code == EXIT_OK

    code, listed = _run(capsys, "revision", "list", *project)
    trail = listed["revisions"]["history"]
    assert [e["revision"] for e in trail] == [first["accepted_revision"], wide["accepted_revision"],
                                             thick["accepted_revision"]]
    # The engine now keeps what each revision was accepted with (ADR-506).
    assert trail[1]["values"]["params"] == {"width": 50.0}
    assert trail[0]["values"]["params"] == {} and trail[2]["digest"] == thick["digest"]

    # Listing is a read: no row, no commit.
    rows = (root / PROGRESS_NAME).read_text().count("\n")
    commits = subprocess.run(["git", "-C", str(root), "rev-list", "--count", "HEAD"],
                             capture_output=True, text=True, check=True).stdout
    _run(capsys, "revision", "list", *project)
    assert (root / PROGRESS_NAME).read_text().count("\n") == rows
    assert subprocess.run(["git", "-C", str(root), "rev-list", "--count", "HEAD"],
                          capture_output=True, text=True, check=True).stdout == commits
    code, refused = _run(capsys, "revision", "reject", "0123", *project)
    assert code == EXIT_USAGE and "only the accepted revision" in refused["error"]

    # Reject: the revision before it comes back exactly, source and values.
    code, rejected = _run(capsys, "revision", "reject", *project)
    assert code == EXIT_OK, rejected
    change = rejected["revisions"]
    assert change["from"] == thick["accepted_revision"]
    assert rejected["accepted_revision"] == wide["accepted_revision"] == change["target"]
    assert change["exact"] is True and rejected["digest"] == wide["digest"]
    assert "revision reject" in (root / PROGRESS_NAME).read_text()

    # Restore #1: its width was the default, which cannot be unset once
    # stored, so the same geometry lands under an explicit-default revision.
    code, restored = _run(capsys, "revision", "restore", "1", *project)
    assert code == EXIT_OK, restored
    change = restored["revisions"]
    assert change["target"] == first["accepted_revision"] and change["exact"] is False
    assert change["same_geometry"] is True and restored["digest"] == first["digest"]
    assert restored["params"]["width"] == 30.0
    # Again: already there, nothing rebuilt.
    code, again = _run(capsys, "revision", "restore", "1", *project)
    assert code == EXIT_OK and any("already accepted" in note for note in again["notes"])

    code, bad = _run(capsys, "revision", "restore", "zz", *project)
    assert code == EXIT_USAGE and "no single stored revision" in bad["error"]
