# SPDX-FileCopyrightText: 2026 Cadex Authors
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


@pytest.fixture
def cpu_training(monkeypatch):
    """Select CPU for requested toy runs, including child dispatchers."""
    monkeypatch.setenv("JAX_PLATFORMS", "cpu")


@pytest.fixture(autouse=True)
def private_training_slot(tmp_path, monkeypatch):
    """Every test gets a machine training slot of its own (ADR-543).

    ``cadex train`` and ``cadex walk`` refuse while another run holds the
    machine's slot, so a suite run beside a live training job would
    otherwise be refused by it -- or, worse, hold it against that job.
    """
    monkeypatch.setenv("CADEX_TRAIN_LOCK", str(tmp_path / "machine-training.lock"))


@pytest.fixture
def small_renders(monkeypatch):
    """Draw the review render small, for tests whose claim is not its pixels.

    The four review views are drawn at 64 px, and the hero at 64 px scaled up
    to the 1024 px the concept sheet is laid out for, so every file is still
    written at its real size. The full-size renders stay pinned by
    ``test_look`` and ``test_render`` (ADR-562, ADR-563).
    """
    from cadex_cli.studio import STUDIO

    drawn, small = STUDIO.studio, 64

    def studio(prepared, basis, *, bounds, size, **kwargs):
        if size != STUDIO.HERO_SIZE:
            return drawn(prepared, basis, bounds=bounds, size=size, **kwargs)
        pixels, details = drawn(prepared, basis, bounds=bounds, size=small, **kwargs)
        k = size // small
        rows = (b"".join(bytes(pixels[3 * (y * small + x):3 * (y * small + x) + 3]) * k
                         for x in range(small)) * k for y in range(small))
        return bytearray(b"".join(rows)), {**details, "covered_pixels": details["covered_pixels"] * k * k}

    monkeypatch.setattr(STUDIO, "SIZE", small)
    monkeypatch.setattr(STUDIO, "studio", studio)


@pytest.fixture
def small_presentation(small_renders, monkeypatch):
    """Draw a pass's videos at 128 px and its heroes at 64 px scaled up.

    For tests whose claims are which files a pass and a fail leave, the
    blocks the report and the envelope carry, and the pushes read from the
    shove episode -- never their pixels. Full-size drawing stays pinned
    where it is the claim: the 512 px studio video by ``test_video``, the
    1024 px hero by ``test_look``, the print bed by the engine suite's
    ``test_studio_print_bed`` (ADR-579).
    """
    from cadex_cli.video import STUDIO as VIDEO

    monkeypatch.setitem(VIDEO, "size", 128)
