# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""OCCT subshape-enumeration fingerprint (Phase 9, ADR-025).

Five xscript ops — ``subshape``, ``defeature``, ``fillet``, ``chamfer`` and
``thicken`` — take **1-based ``TopExp::MapShapes`` ordinals as script
arguments**, saved in agent-authored programs. That ordering is not a
documented OCCT contract and has changed across releases. If it shifts, a
saved script does not fail: it builds *different geometry* that still passes
``isValid()``, and every downstream index shifts with it.

So the ordering is pinned here, against a canonical shape whose construction
exercises the operations that reorder subshapes in practice — a boolean cut
(``removeSplitter`` is default-on) and a fillet. A red test after a
dependency bump means every saved script in every project just changed
meaning; it does not mean this file needs updating.

Requires a real ``FreeCADCmd``; skipped without one.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile

import pytest

from test_cadexd_lifecycle import FREECADCMD, _spawn_cadexd, _stop

GOLDEN = Path(__file__).resolve().parent / "subshape_enumeration.json"

#: Box, four drilled holes, then a fillet on every edge. The two published
#: outputs pin the enumeration before and after the fillet, which is where
#: the plan expects drift to appear if it appears at all.
CANONICAL_SCRIPT = """
drilled = part.box(40, 30, 10)
for x in (8.0, 32.0):
    for y in (7.5, 22.5):
        drilled = part.cut(drilled, part.cylinder(3.0, 20.0, origin=[x, y, -5.0]))
result = {"drilled": drilled, "rounded": part.fillet(drilled, 1.5)}
"""

_PROBES = (("drilled", "face"), ("drilled", "edge"),
           ("rounded", "face"), ("rounded", "edge"))


def _round(value, places: int = 6):
    """Round a detail value, folding -0.0 into 0.0 so signs stay stable."""

    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        rounded = round(float(value), places)
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, list):
        return [_round(item, places) for item in value]
    return value


def _fingerprint(detail: dict) -> dict:
    """The identity of one subshape at one ordinal, kernel-comparable."""

    return {
        key: _round(detail.get(key))
        for key in (
            "name",
            "element_type",
            "geometry_type",
            "center_mm",
            "area_mm2",
            "normal",
            "length_mm",
            "direction",
            "radius_mm",
        )
        if key in detail
    }


def _collect(client) -> dict[str, dict]:
    """Drive one cadexd through the canonical script and fingerprint it."""

    written = client.request(
        "write_script", {"source": CANONICAL_SCRIPT, "expected_revision": ""}
    )
    assert written["ok"] is True, written

    collected: dict[str, dict] = {}
    for output, kind in _PROBES:
        # `expected_count` is the query's declared cardinality; the harvest
        # runs against it so a changed *count* fails loudly and separately
        # from a changed *order*.
        probe = client.request(
            "resolve_pin",
            {"output": output, "selection": {"element_type": kind,
                                             "expected_count": 0}},
        )
        available = probe.get("observed", {}).get("available") or []
        assert available, f"No {kind} details for {output}: {probe}"
        collected[f"{output}.{kind}"] = {
            "count": int(probe["observed"]["actual_count"]),
            "subshapes": [_fingerprint(item) for item in available],
        }
    return collected


def _occt_version() -> str:
    result = subprocess.run(
        [str(FREECADCMD), "-c", "import Part; print('OCCT', Part.OCC_VERSION)"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    for line in result.stdout.splitlines():
        if line.startswith("OCCT "):
            return line.split(" ", 1)[1].strip()
    raise AssertionError(f"Could not read Part.OCC_VERSION: {result.stdout!r}")


def _pinned_version() -> str:
    text = (Path(__file__).resolve().parents[4] / "pixi.toml").read_text(
        encoding="utf-8"
    )
    for line in text.splitlines():
        if line.startswith("occt = "):
            return line.split("=", 1)[1].strip().strip('"')
    raise AssertionError("pixi.toml declares no occt dependency.")


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for the OCCT gate."
)
def test_occt_is_pinned_to_an_exact_version() -> None:
    """A range would let a patch bump re-index every saved script silently."""

    pinned = _pinned_version()
    assert pinned.startswith("=="), (
        f"pixi.toml pins occt as {pinned!r}. Subshape ordering is a saved-script "
        "contract, so the kernel is pinned exactly, not to a range (ADR-025)."
    )
    assert _occt_version() == pinned.lstrip("="), (
        f"The environment runs OCCT {_occt_version()} but pixi.toml pins "
        f"{pinned}. Re-resolve the environment before trusting this suite."
    )


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for the OCCT gate."
)
def test_subshape_enumeration_matches_the_recorded_fingerprint() -> None:
    """Ordinal-for-ordinal, against the recorded kernel ordering."""

    tempfile.mkdtemp(prefix="cadexd-enumeration-")
    client = None
    try:
        client = _spawn_cadexd()
        client.request(
            "open_project",
            {"project_root": tempfile.mkdtemp(prefix="cadexd-enumeration-")},
        )
        observed = _collect(client)
    finally:
        _stop(client)

    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert set(observed) == set(expected["probes"])

    for probe, recorded in sorted(expected["probes"].items()):
        actual = observed[probe]
        assert actual["count"] == recorded["count"], (
            f"{probe}: the kernel now reports {actual['count']} subshapes, "
            f"recorded {recorded['count']}. Every saved script indexing this "
            "shape changed meaning."
        )
        for index, (got, want) in enumerate(
            zip(actual["subshapes"], recorded["subshapes"]), start=1
        ):
            assert got == want, (
                f"{probe}: ordinal {index} moved.\n  recorded: {want}\n"
                f"  observed: {got}\n"
                "This is the failure mode ADR-025 exists to catch: the shape "
                "is still valid, the indices no longer mean what the saved "
                "scripts meant."
            )
