#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Per-file modification notices for inherited FreeCAD and Blender files.

LGPL-2.1 §2(a) and GPL-2 §2(a) ask a modified file to carry a prominent
notice of the change. This tool holds that rule mechanically: it reads
``docs/inherited-modifications.json`` (itself pinned equal to the git diff
against each import commit by ``test_licensing_compliance.py``) and inserts
one comment line after each file's existing license header:

    /* Modified by the Cadex project, 2026. See docs/BLENDER-TREE.md. */

in the file's own comment style. The date is a fixed ``2026`` rather than a
per-file git date: the imports are squashed snapshots, so per-file dates
would be false precision. When a later year first touches one of these
files, extend the notice there to a range.

Idempotent. ``--check`` (default) lists files missing their notice and
exits non-zero if any; ``--write`` inserts them. Files whose manifest entry
says ``"notice": "ledger-only"`` are skipped here and must appear by name
in their ledger doc instead — the compliance test checks that half.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "docs" / "inherited-modifications.json"

NOTICE_TEXT = "Modified by the Cadex project, 2026. See {ledger}."

HASH_SUFFIXES = {".py", ".pyi", ".sh", ".cmake", ".yml", ".yaml"}
C_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".m", ".mm", ".h", ".hh", ".hpp", ".qss"}
XML_SUFFIXES = {".xml", ".qrc", ".plist", ".html", ".svg", ".ui"}


def comment_style(path: Path) -> str:
    if path.name == "CMakeLists.txt":
        return "hash"
    suffix = path.suffix.lower()
    if suffix in HASH_SUFFIXES:
        return "hash"
    if suffix in C_SUFFIXES:
        return "c"
    if suffix in XML_SUFFIXES:
        return "xml"
    raise ValueError(f"no comment style known for {path}")


def notice_line(path: Path, ledger: str) -> str:
    text = NOTICE_TEXT.format(ledger=ledger)
    style = comment_style(path)
    if style == "hash":
        return f"# {text}"
    if style == "c":
        return f"/* {text} */"
    return f"<!-- {text} -->"


def insertion_index(lines: list[str], style: str) -> int:
    """Index at which to insert the notice: after the prelude (shebang, XML
    declaration, DOCTYPE) and after the leading comment block, if any."""
    i = 0
    # Prelude: shebang / XML declaration / DOCTYPE.
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("#!") and i == 0:
            i += 1
        elif stripped.startswith("<?xml") or stripped.startswith("<!DOCTYPE"):
            i += 1
        else:
            break
    # Leading comment block, in the file's own style.
    in_block = False
    end = i
    j = i
    while j < len(lines):
        stripped = lines[j].strip()
        if in_block:
            end = j + 1
            if "*/" in stripped or "-->" in stripped:
                in_block = False
            j += 1
            continue
        if style == "hash" and stripped.startswith("#"):
            end = j + 1
            j += 1
            continue
        if style == "c" and (stripped.startswith("//") or stripped.startswith("/*")):
            end = j + 1
            if stripped.startswith("/*") and "*/" not in stripped:
                in_block = True
            j += 1
            continue
        if style == "xml" and stripped.startswith("<!--"):
            end = j + 1
            if "-->" not in stripped:
                in_block = True
            j += 1
            continue
        break
    return end


def iter_comment_entries():
    manifest = json.loads(MANIFEST.read_text())
    for tree in manifest["trees"].values():
        ledger = tree["ledger"]
        for entry in tree["files"]:
            if entry.get("notice") == "comment":
                yield REPO / entry["path"], ledger


def missing_notices() -> list[Path]:
    """Files whose manifest entry asks for a comment notice and that do not
    carry one. Imported by test_licensing_compliance.py."""
    missing = []
    for path, ledger in iter_comment_entries():
        if not path.exists():
            missing.append(path)
            continue
        expected = NOTICE_TEXT.format(ledger=ledger)
        head = "".join(path.read_text(errors="replace").splitlines(keepends=True)[:60])
        if expected not in head:
            missing.append(path)
    return missing


def write_notices() -> list[Path]:
    written = []
    for path, ledger in iter_comment_entries():
        text = path.read_text()
        expected = NOTICE_TEXT.format(ledger=ledger)
        if expected in "".join(text.splitlines(keepends=True)[:60]):
            continue
        lines = text.splitlines(keepends=True)
        style = comment_style(path)
        at = insertion_index(lines, style)
        lines.insert(at, notice_line(path, ledger) + "\n")
        path.write_text("".join(lines))
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report missing notices (default)")
    mode.add_argument("--write", action="store_true", help="insert missing notices")
    args = parser.parse_args(argv)

    if args.write:
        for path in write_notices():
            print(f"wrote  {path.relative_to(REPO)}")
        return 0

    missing = missing_notices()
    for path in missing:
        print(f"missing  {path.relative_to(REPO)}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
