# SPDX-License-Identifier: LGPL-2.1-or-later

"""Test bootstrap for the CLI suite.

Two things, and deliberately not a third: ``cli/`` goes on ``sys.path`` so
``cadex_cli`` imports, and the shared fixtures live here. There is **no
FreeCAD stub** — unlike ``cadex_tests/conftest.py``, nothing in this package
imports FreeCAD at all. The CLI spawns the engine as a subprocess, which is
what makes half this suite runnable with no engine present and the other
half honest when there is one.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

CLI_DIR = Path(__file__).resolve().parents[1]
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from cadex_cli.engine import Engine, EngineError, resolve_engine  # noqa: E402
from cadex_cli.protocol import load_protocol  # noqa: E402

REPO_ROOT = CLI_DIR.parent
SOURCE_MODULE_DIR = REPO_ROOT / "src" / "Mod" / "cadex"


def _available_engine() -> Engine | None:
    try:
        return resolve_engine(None)
    except EngineError:
        return None


ENGINE = _available_engine()


@pytest.fixture(scope="session")
def engine() -> Engine:
    """A built engine, or the test is skipped.

    The same bar the engine suite's cadexd tests set: no binary, no run. A
    CI job that silently passes because it never spawned anything is worse
    than a skip that says so.
    """

    if ENGINE is None:
        pytest.skip("No engine available; run `pixi run build-engine`.")
    return ENGINE


@pytest.fixture(scope="session")
def protocol():
    """``CadexdProtocol`` from the source tree.

    Loaded by path, which needs no engine binary: the module is pure Python
    with no FreeCAD import, which is exactly why the CLI can validate frames
    against it before anything is built.
    """

    return load_protocol(SOURCE_MODULE_DIR)
