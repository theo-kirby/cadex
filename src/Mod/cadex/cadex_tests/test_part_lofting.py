# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A loft that is not the shape its own table describes (ADR-129).

The robot wolf's dominant visible defect was never a bad row. Its
neck-and-head loft, through eight perfectly reasonable sections, came back
enclosing **4.5x the volume** of a straight loft through the identical
eight — a smooth plate three times the section width, with the head poking
out of the middle of it. It published, it tessellated, it was valid, and
eleven accepted revisions later a person said "looks better but not good"
(``docs/ORGANIC.md`` §4).

Two halves as usual: the measure is exercised against a fake kernel here,
and the wolf's own table is run against a live engine at the bottom.
"""

from __future__ import annotations

import tempfile

import pytest

import cadex_part_worker as worker


# -- a kernel that only has to know how big things are -----------------------


class _Box:
    def __init__(self, low, high) -> None:
        self.XMin, self.YMin, self.ZMin = low
        self.XMax, self.YMax, self.ZMax = high


class _Sized:
    """A shape that knows its own extent and nothing else."""

    def __init__(self, low, high, *, optimal=True) -> None:
        self._box = _Box(low, high)
        self._optimal = optimal

    def optimalBoundingBox(self, _triangulation):  # noqa: N802 - kernel spelling
        if not self._optimal:
            raise RuntimeError("no optimal box for this shape")
        return self._box

    @property
    def BoundBox(self):  # noqa: N802 - kernel spelling
        return self._box


def _sections():
    """Three rings 100 apart, 100 wide and 100 tall."""

    return [
        _Sized((-50.0, -50.0, position), (50.0, 50.0, position))
        for position in (0.0, 100.0, 200.0)
    ]


def test_a_loft_that_stays_inside_its_sections_is_not_a_bulge() -> None:
    result = _Sized((-52.0, -52.0, 0.0), (52.0, 52.0, 200.0))
    report = worker._loft_bulge(result, _sections())
    assert report["excessive"] is False
    assert report["bulge_mm"] == 2.0


def test_a_loft_that_swings_wide_is_measured_in_millimetres() -> None:
    """The wolf's defect, in miniature: three times the section width."""

    result = _Sized((-150.0, -50.0, 0.0), (150.0, 50.0, 200.0))
    report = worker._loft_bulge(result, _sections())
    assert report["excessive"] is True
    assert report["bulge_axis"] == "x"
    assert report["bulge_mm"] == 100.0
    assert report["section_span_mm"] == 100.0
    assert report["bulge_share"] == 1.0


def test_the_measure_falls_back_when_a_shape_has_no_optimal_box() -> None:
    """``BoundBox`` bounds a spline by its poles, so it is the last resort.

    Measured on the wolf: the torso's pole box overshot its own sections by
    127 mm in Z while the surface enclosed 2.5% more volume than a straight
    loft through the same rings. A check built on it refuses the shapes that
    are fine. It is still better than refusing to measure at all.
    """

    result = _Sized((-150.0, -50.0, 0.0), (150.0, 50.0, 200.0), optimal=False)
    assert worker._loft_bulge(result, _sections())["excessive"] is True


def test_a_ruled_loft_is_never_checked() -> None:
    """It is straight between its sections and cannot leave them."""

    result = _Sized((-150.0, -50.0, 0.0), (150.0, 50.0, 200.0))
    worker._check_loft_bulge("loft", result, _sections(), {"ruled": True})
    worker._check_loft_bulge("loft", result, _sections(), {"on_bulge": "allow"})
    with pytest.raises(worker.PartOperationError):
        worker._check_loft_bulge("loft", result, _sections(), {})


def test_the_refusal_names_a_lower_degree_and_a_longer_gap() -> None:
    result = _Sized((-150.0, -50.0, 0.0), (150.0, 50.0, 200.0))
    with pytest.raises(worker.PartOperationError) as caught:
        worker._check_loft_bulge("loft", result, _sections(), {"max_degree": 5})
    details = caught.value.details
    assert "max_degree" in details["correction"]
    assert "ruled=True" in details["correction"]
    assert details["observed"]["max_degree"] == 5
    assert "100.0 mm" in str(caught.value)


def test_on_bulge_is_validated_before_the_kernel_sees_it() -> None:
    from cadex_part_api import _bulge_mode

    assert _bulge_mode("loft", "ALLOW") == "allow"
    with pytest.raises(ValueError) as caught:
        _bulge_mode("loft", "reduce")
    assert "on_bulge" in str(caught.value)


# -- against a live kernel, on the table that paid for this ------------------

#: The wolf's neck and head, verbatim: eight sections whose spacing runs
#: 72, 30, 45, 49, 45, 12, 6 mm and whose half-width falls 51 -> 2.
_NECK = """
cwh, chh, bz = 70.0, 87.5, 280.0
L, hl = 400.0, 150.0
def sec(x, z, w, h):
    e = part.ellipse(h, w)
    e = part.transform(e, rotation_axis=(0, 1, 0), rotation_degrees=-90)
    e = part.transform(e, translation=(x, 0, z))
    return part.wire([e], closed=True)

rows = [
    (0.30 * L, bz + 0.05 * chh, 0.732 * cwh, 0.799 * chh),
    (0.48 * L, bz + 0.25 * chh, 0.50 * cwh, 0.55 * chh),
    (0.50 * L + 0.15 * hl, bz + 0.56 * chh, 0.35 * cwh, 0.38 * chh),
    (0.50 * L + 0.45 * hl, bz + 0.63 * chh, 0.34 * cwh, 0.33 * chh),
    (0.50 * L + 0.78 * hl, bz + 0.55 * chh, 0.16 * cwh, 0.16 * chh),
    (0.50 * L + 1.08 * hl, bz + 0.50 * chh, 0.105 * cwh, 0.11 * chh),
    (0.50 * L + 1.16 * hl, bz + 0.485 * chh, 0.06 * cwh, 0.065 * chh),
    (0.50 * L + 1.20 * hl, bz + 0.47 * chh, 0.03 * cwh, 0.033 * chh),
]
sections = [sec(*row) for row in rows]
"""

REFUSED_SOURCE = _NECK + """
head = part.loft(sections, solid=True, label="head")
result = {"head": head}
"""

ALLOWED_SOURCE = _NECK + """
head = part.loft(sections, solid=True, on_bulge="allow", label="head")
result = {"head": head}
"""

TAMED_SOURCE = _NECK + """
head = part.loft(sections, solid=True, max_degree=3, label="head")
ruled = part.loft(sections, solid=True, ruled=True, label="ruled")
result = {"head": head, "ruled": ruled}
"""


def _live():
    from test_cadexd_lifecycle import FREECADCMD

    return FREECADCMD is not None


def _write(client, source: str, prefix: str):
    client.request("open_project", {"project_root": tempfile.mkdtemp(prefix=prefix)})
    return client.request("write_script", {"source": source, "expected_revision": ""})


def _volume(client, output: str) -> float:
    probe = client.request(
        "resolve_pin",
        {"output": output, "selection": {"element_type": "solid", "expected_count": 0}},
    )
    solids = ((probe.get("observed") or {}).get("available")) or []
    assert len(solids) == 1, (output, solids)
    return float(solids[0]["volume_mm3"])


@pytest.mark.skipif(not _live(), reason="No FreeCADCmd binary available.")
def test_the_wolfs_head_is_refused_and_says_what_to_do_about_it() -> None:
    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()

        refused = _write(client, REFUSED_SOURCE, "cadexd-bulge-no-")
        assert refused["ok"] is False, refused
        observed = (refused.get("observed") or {}).get("details", {}).get("observed")
        assert observed is not None, refused
        # Across the body, where the plate is: about 99 mm outside sections
        # whose own span is 102 mm.
        assert observed["bulge_axis"] == "y", observed
        assert 90.0 < observed["bulge_mm"] < 110.0, observed
        assert observed["bulge_share"] > 0.9, observed

        allowed = _write(client, ALLOWED_SOURCE, "cadexd-bulge-ok-")
        assert allowed["ok"] is True, allowed
        bulged = _volume(client, "head")

        tamed = _write(client, TAMED_SOURCE, "cadexd-bulge-deg3-")
        assert tamed["ok"] is True, tamed
        degree_three = _volume(client, "head")
        straight = _volume(client, "ruled")

        # The measurement this whole slice comes from: the default degree
        # encloses four and a half times the straight loft through the same
        # eight sections, and degree 3 does not.
        assert bulged / straight > 4.0, (bulged, straight)
        assert degree_three / straight < 1.5, (degree_three, straight)
    finally:
        _stop(client)
