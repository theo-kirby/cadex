# SPDX-License-Identifier: LGPL-2.1-or-later

"""Which engine a run drives, and what it says when there is none.

Engine resolution decides *what is under test* for everything else, so it is
checked against hand-built payload directories rather than against whichever
engine this checkout happens to have. The fixtures carry a real
``CadexdProtocol.py`` because that is what a payload carries, and because
loading it is how a run proves the manifest and the implementation agree.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from cadex_cli.engine import (
    Engine,
    EngineError,
    MANIFEST_NAME,
    MANIFEST_SCHEMA,
    resolve_engine,
)
from cadex_cli.protocol import ProtocolUnavailable, load_protocol

from conftest import SOURCE_MODULE_DIR


def _payload(root: Path, *, protocol: str = "cadex-cadexd-v1") -> Path:
    """A minimal payload: a manifest, a stub binary, a real protocol module."""

    binary = root / "bin" / "FreeCADCmd"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    binary.chmod(0o755)

    module_dir = root / "Mod" / "cadex"
    module_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(SOURCE_MODULE_DIR / "CadexdProtocol.py", module_dir)

    (root / MANIFEST_NAME).write_text(
        json.dumps(
            {
                "schema": MANIFEST_SCHEMA,
                "protocol": protocol,
                "freecadcmd": "bin/FreeCADCmd",
                "module_dir": "Mod/cadex",
            }
        ),
        encoding="utf-8",
    )
    return root


def test_explicit_engine_beats_the_environment(tmp_path, monkeypatch) -> None:
    chosen = _payload(tmp_path / "chosen")
    ignored = _payload(tmp_path / "ignored")
    monkeypatch.setenv("CADEX_ENGINE_ROOT", str(ignored))

    engine = resolve_engine(str(chosen))

    assert engine.source == "explicit"
    assert engine.root == chosen.resolve()
    assert engine.freecadcmd == chosen.resolve() / "bin" / "FreeCADCmd"
    assert engine.module_dir == chosen.resolve() / "Mod" / "cadex"


def test_the_environment_is_read_when_no_engine_is_named(tmp_path, monkeypatch) -> None:
    root = _payload(tmp_path / "payload")
    monkeypatch.setenv("CADEX_ENGINE_ROOT", str(root))

    engine = resolve_engine(None)

    assert engine.source == "payload"
    assert engine.protocol.PROTOCOL_SCHEMA == "cadex-cadexd-v1"


def test_the_dev_tree_is_the_last_resort(monkeypatch) -> None:
    monkeypatch.delenv("CADEX_ENGINE_ROOT", raising=False)
    try:
        engine = resolve_engine(None)
    except EngineError as exc:
        # A checkout with nothing built says so, and says how to fix it.
        assert "build-engine" in str(exc)
        return
    assert engine.source == "dev-tree"
    assert engine.module_dir == SOURCE_MODULE_DIR


def test_a_payload_without_a_manifest_is_refused(tmp_path) -> None:
    (tmp_path / "empty").mkdir()
    with pytest.raises(EngineError) as caught:
        resolve_engine(str(tmp_path / "empty"))
    # The manifest is the payload's discovery contract (ADR-020); saying so
    # is the difference between a fixable message and "not found".
    assert MANIFEST_NAME in str(caught.value)


def test_a_manifest_naming_a_missing_binary_is_refused(tmp_path) -> None:
    root = _payload(tmp_path / "payload")
    (root / "bin" / "FreeCADCmd").unlink()
    with pytest.raises(EngineError) as caught:
        resolve_engine(str(root))
    assert "missing binary" in str(caught.value)


def test_a_manifest_disagreeing_with_its_own_protocol_is_refused(tmp_path) -> None:
    """A payload assembled out of two trees fails before a frame is sent."""

    root = _payload(tmp_path / "payload", protocol="cadex-cadexd-v0")
    with pytest.raises(EngineError) as caught:
        resolve_engine(str(root))
    assert "declares protocol" in str(caught.value)


def test_a_non_directory_engine_argument_is_a_usable_message(tmp_path) -> None:
    target = tmp_path / "not-a-dir"
    target.write_text("", encoding="utf-8")
    with pytest.raises(EngineError) as caught:
        resolve_engine(str(target))
    assert "staged engine payload root" in str(caught.value)


def test_the_protocol_is_loaded_from_the_engine_under_test(tmp_path) -> None:
    """Not imported from ``sys.path`` — read out of a named directory.

    This is what makes a run against a staged payload validate against *that
    payload's* contract rather than the source tree's (ADR-023). Two
    payloads resolved in one process must not shadow each other.
    """

    first = resolve_engine(str(_payload(tmp_path / "one")))
    second = resolve_engine(str(_payload(tmp_path / "two")))

    assert first.protocol is not second.protocol
    assert first.protocol is load_protocol(first.module_dir)  # cached per dir
    assert second.protocol.PROTOCOL_SCHEMA == "cadex-cadexd-v1"


def test_a_directory_with_no_protocol_module_says_so(tmp_path) -> None:
    with pytest.raises(ProtocolUnavailable):
        load_protocol(tmp_path)


def test_the_engine_describes_itself_for_the_report() -> None:
    engine = Engine(Path("/bin/true"), SOURCE_MODULE_DIR, "dev-tree")
    described = engine.describe()
    assert described["source"] == "dev-tree"
    assert described["module_dir"] == str(SOURCE_MODULE_DIR)
