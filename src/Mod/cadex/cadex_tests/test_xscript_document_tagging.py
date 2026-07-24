# SPDX-License-Identifier: LGPL-2.1-or-later

"""Per-document engine classification and convert-on-open re-tag (B3/B4)."""

from __future__ import annotations

import json
from pathlib import Path

import CadexScriptedDomains as domains
import CadexScriptedDomains as xdomains


class _Obj:
    def __init__(self, program_id: str, domain: str) -> None:
        self.PropertiesList = [
            domains.PROP_PROGRAM_ID,
            domains.PROP_PROGRAM_DOMAIN,
        ]
        setattr(self, domains.PROP_PROGRAM_ID, program_id)
        setattr(self, domains.PROP_PROGRAM_DOMAIN, domain)


class _Doc:
    def __init__(self, objects: list[_Obj]) -> None:
        self.Objects = objects


def _write_manifest(root: Path, domain: str, program_id: str, schema: str) -> None:
    directory = root / "xscript" / domain / program_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "program.json").write_text(
        json.dumps(
            {
                "schema": schema,
                "version": 2,
                "program_id": program_id,
                "domain": domain,
                "source": "result = {}",
            }
        ),
        encoding="utf-8",
    )


def test_plain_document_has_no_programs(tmp_path: Path) -> None:
    assert xdomains.document_engine(_Doc([]), str(tmp_path)) == "plain"


def test_classifies_legacy_and_xscript_and_mixed(tmp_path: Path) -> None:
    legacy_id = "a" * 32
    xs_id = "b" * 32
    _write_manifest(tmp_path, "partdesign", legacy_id, domains.PROGRAM_SCHEMA)
    _write_manifest(tmp_path, "partdesign", xs_id, domains.XSCRIPT_PROGRAM_SCHEMA)

    only_legacy = _Doc([_Obj(legacy_id, "partdesign")])
    only_xs = _Doc([_Obj(xs_id, "partdesign")])
    both = _Doc([_Obj(legacy_id, "partdesign"), _Obj(xs_id, "partdesign")])

    assert xdomains.document_engine(only_legacy, str(tmp_path)) == "legacy"
    assert xdomains.document_engine(only_xs, str(tmp_path)) == "xscript"
    assert xdomains.document_engine(both, str(tmp_path)) == "mixed"


def test_convert_retags_legacy_programs_to_xscript(tmp_path: Path) -> None:
    legacy_id = "c" * 32
    _write_manifest(tmp_path, "partdesign", legacy_id, domains.PROGRAM_SCHEMA)
    doc = _Doc([_Obj(legacy_id, "partdesign")])
    assert xdomains.document_engine(doc, str(tmp_path)) == "legacy"

    result = xdomains.retag_programs_to_xscript(
        str(tmp_path), xdomains.document_program_refs(doc)
    )
    assert result["retagged"] == [legacy_id]

    # The document now classifies as xscript, and the manifest keeps everything
    # else (metadata-only re-tag).
    assert xdomains.document_engine(doc, str(tmp_path)) == "xscript"
    manifest = json.loads(
        (tmp_path / "xscript" / "partdesign" / legacy_id / "program.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["schema"] == domains.XSCRIPT_PROGRAM_SCHEMA
    assert manifest["program_id"] == legacy_id
    assert manifest["source"] == "result = {}"


def test_missing_manifest_defaults_to_xscript(tmp_path: Path) -> None:
    doc = _Doc([_Obj("d" * 32, "partdesign")])
    # No manifest on disk: an untagged live program is treated as xscript.
    assert xdomains.document_engine(doc, str(tmp_path)) == "xscript"
