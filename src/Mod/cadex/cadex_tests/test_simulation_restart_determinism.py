# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""One script, two engines, the same trace bytes.

This is the precondition for a simulation trace's bytes joining the project
digest, and it is written before that change rather than after it: a digest
is a promise that two people who open the same project get the same thing,
and a trace whose bytes moved between runs would turn that promise into an
intermittent refusal to open the project at all.

Determinism *within* one process proves very little here — a stable dict
order, a warm allocator and a solver that has already been through its own
initialisation are all doing part of the work. So the comparison is between
two separate `cadexd` processes with two separate project roots, sharing
nothing but the script text, and the file compared is the one the project
store retained rather than anything a helper recomputed.

``assembly.simulation`` runs on OndselSolver, which is the half of this
question `main` owns.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import pytest

from test_cadexd_lifecycle import (
    FREECADCMD,
    SIMULATION_SCRIPT,
    _spawn_cadexd,
    _stop,
)

pytestmark = pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)


def _retained_trace(source: str) -> tuple[bytes, str]:
    """One script, one cadexd, one project root, and the bytes it wrote."""

    root = Path(tempfile.mkdtemp(prefix="simulation-restart-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened
        written = client.request(
            "write_script", {"source": source, "expected_revision": ""}
        )
        assert written["ok"] is True, json.dumps(written)[:4000]
        entry = written["display"]["sim"]
        assert entry["artifact_kind"] == "assembly_simulation_json", entry
        raw = Path(entry["artifact_path"]).read_bytes()
        done = client.request("shutdown", timeout=60)
        assert done["ok"] is True
        return raw, str(written["digest"])
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


def test_the_same_script_writes_the_same_trace_across_cadexd_restarts() -> None:
    """OndselSolver is reproducible across processes, byte for byte.

    Three runs rather than two: two agreeing could be two runs that happened
    to take the same path through an allocator, and the third is what makes
    "reproducible" cost something to claim.
    """

    runs = [_retained_trace(SIMULATION_SCRIPT) for _ in range(3)]
    payloads = {raw for raw, _digest in runs}
    assert len(payloads) == 1, [len(raw) for raw, _digest in runs]

    digest = hashlib.sha256(runs[0][0]).hexdigest()
    for raw, _project_digest in runs:
        assert hashlib.sha256(raw).hexdigest() == digest


def test_the_project_digest_is_the_same_across_those_restarts() -> None:
    """The number `open_project` compares, over two independent builds.

    Whatever `compute_project_digest` chooses to hash, it has to produce the
    same answer in a process that has never seen the first one — that is
    what makes a stored `accepted_digest` meaningful at all, and it is the
    property a change to what the digest covers must not break.
    """

    first_raw, first_digest = _retained_trace(SIMULATION_SCRIPT)
    second_raw, second_digest = _retained_trace(SIMULATION_SCRIPT)
    assert first_raw == second_raw
    assert first_digest == second_digest
    assert len(first_digest) == 64


def test_the_run_being_compared_is_one_where_the_mechanism_moved() -> None:
    """A byte comparison over a trace of a mechanism that sat still would pass.

    So the same run is checked for containing the thing it is supposed to
    contain: a driven joint that swept the arm through a full turn, sampled
    into distinct frames.
    """

    raw, _digest = _retained_trace(SIMULATION_SCRIPT)
    trace = json.loads(raw.decode("utf-8"))
    assert trace["schema"] == "cadex-assembly-simulation-trace-v1"

    frames = trace["frames"]
    assert len(frames) > 2, len(frames)
    positions = {
        tuple(frame["component_placements"]["swing"]["rotation_xyzw"])
        for frame in frames
    }
    assert len(positions) > 2, "the driven component never moved"
    assert len({
        tuple(frame["component_placements"]["base"]["position_mm"])
        for frame in frames
    }) == 1, "the grounded component moved"
