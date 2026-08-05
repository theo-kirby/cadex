# SPDX-License-Identifier: LGPL-2.1-or-later

"""A blend that survives the edges the kernel refuses (ADR-125).

``TopoShapePy::makeFillet`` builds a ``BRepFilletAPI_MakeFillet`` and calls
``.Shape()`` without checking ``IsDone``, so one impossible edge in three
hundred used to throw away the other 299 and answer ``15StdFail_NotDone``.
The robot wolf (``docs/ORGANIC.md`` §1) is the measurement: it reached for
exactly this operation three times and got nothing back it could act on.

Two halves, for the usual reason. The search — which edges fail, how few
kernel calls it takes to find them, what the refusal says — is exercised
against a fake kernel here and needs no FreeCAD. The geometry is proved
against a live engine at the bottom, and skips without one.
"""

from __future__ import annotations

import json
import tempfile

import pytest

import cadex_part_worker as worker


# -- a kernel that refuses on demand ----------------------------------------


class _Built:
    """Stands in for the shape a successful blend returns."""

    def __init__(self, edges, radius) -> None:
        self.edges = tuple(edges)
        self.radius = radius

    def isNull(self) -> bool:  # noqa: N802 - the kernel's spelling
        return False

    def isValid(self) -> bool:  # noqa: N802
        return True


class _FakeShape:
    """One shape whose ``makeFillet`` refuses a named set of edges.

    ``impossible`` are edges that fail at any radius above ``ceiling``,
    which is how a real body behaves: a fillet fails because the radius does
    not fit the geometry, not because the edge is cursed.
    """

    def __init__(self, impossible=(), ceiling: float = 0.0) -> None:
        self.impossible = set(impossible)
        self.ceiling = ceiling
        self.calls: list[tuple[float, int]] = []

    def makeFillet(self, radius, edges, *rest):  # noqa: N802
        if isinstance(radius, (list, tuple)):
            # ADR-128's per-edge form: one radius each, or a [start, end]
            # pair each. An edge fails on its OWN radius, which is the whole
            # point of the form.
            self.calls.append((tuple(radius), len(edges)))
            for edge, spec in zip(edges, radius):
                first = spec[0] if isinstance(spec, (list, tuple)) else spec
                if first > self.ceiling and edge in self.impossible:
                    raise RuntimeError("StdFail_NotDone BRep_API: command not done")
            return _Built(edges, tuple(radius))
        self.calls.append((radius, len(edges)))
        if radius > self.ceiling and self.impossible.intersection(edges):
            raise RuntimeError("StdFail_NotDone BRep_API: command not done")
        return _Built(edges, radius)

    makeChamfer = makeFillet


def _edges(count: int) -> list[str]:
    return ["e{:02d}".format(index) for index in range(count)]


def _details(edges):
    return [
        {
            "element_type": "edge",
            "geometry_type": "BSpline",
            "center_mm": [float(index), 0.0, 0.0],
            "length_mm": 10.0 + index,
        }
        for index, _edge in enumerate(edges)
    ]


def _blend(shape, edges, radius, **kwargs):
    return worker._blend(shape, "fillet", edges, _details(edges), radius, **kwargs)


# -- the fast path is still one call ----------------------------------------


def test_a_blend_that_works_costs_exactly_one_kernel_call() -> None:
    """The path every working model is on must not pay for this feature."""

    shape = _FakeShape()
    edges = _edges(300)
    result = _blend(shape, edges, 2.0)
    assert isinstance(result, _Built)
    assert result.edges == tuple(edges)
    assert len(shape.calls) == 1


# -- the search -------------------------------------------------------------


def test_one_impossible_edge_no_longer_throws_away_the_others() -> None:
    """The defect, stated as a test: 1 bad edge in 64, 63 survive."""

    edges = _edges(64)
    shape = _FakeShape(impossible={edges[37]}, ceiling=0.5)
    result = _blend(shape, edges, 2.0, on_failure="skip")
    assert isinstance(result, _Built)
    assert edges[37] not in result.edges
    assert len(result.edges) == 63


def test_the_search_is_logarithmic_not_linear() -> None:
    """Bisection, and the cost is what makes this usable on a real body."""

    edges = _edges(256)
    shape = _FakeShape(impossible={edges[200]}, ceiling=0.5)
    with pytest.raises(worker.PartOperationError) as caught:
        _blend(shape, edges, 2.0)
    observed = caught.value.details["observed"]
    # One bad edge out of 256: a linear scan is 256 calls, bisection is
    # ~2*log2(256). The cap is 48 and this must stay far inside it.
    assert observed["probe_calls"] <= 24, observed
    assert observed["probe_capped"] is False


def test_the_refusal_names_the_edge_and_quotes_a_radius_that_works() -> None:
    """What the wolf never got: a failing edge, a count, and a number."""

    edges = _edges(32)
    shape = _FakeShape(impossible={edges[5]}, ceiling=0.75)
    with pytest.raises(worker.PartOperationError) as caught:
        _blend(shape, edges, 3.0)

    details = caught.value.details
    observed = details["observed"]
    assert observed["edges_selected"] == 32
    assert observed["edges_blended"] == 31
    assert observed["edges_refused"] == 1
    # Named by the fingerprint the selection already computed, not by an
    # ordinal into an enumeration that the next edit renumbers.
    assert observed["refused_edges"] == ["edge|BSpline|5.000,0.000,0.000|length_mm=15.000"]
    workable = observed["largest_workable_radius_mm"]
    assert workable is not None and 0.0 < workable <= 0.75
    assert "on_failure='skip'" in details["correction"]
    assert str(workable) in details["correction"]
    assert "StdFail" not in str(caught.value)


def test_an_edge_is_refused_only_against_the_set_already_accepted() -> None:
    """Fillets interact, and the report says what it actually measured."""

    edges = _edges(16)
    shape = _FakeShape(impossible={edges[0], edges[9]}, ceiling=0.1)
    with pytest.raises(worker.PartOperationError) as caught:
        _blend(shape, edges, 1.0)
    observed = caught.value.details["observed"]
    assert observed["edges_refused"] == 2
    assert observed["edges_blended"] == 14


# -- the three failure modes ------------------------------------------------


def test_skip_blends_the_rest_and_reduce_lowers_the_radius() -> None:
    edges = _edges(16)
    impossible = {edges[3]}

    skipped = _blend(_FakeShape(impossible, ceiling=0.2), edges, 4.0,
                     on_failure="skip")
    assert len(skipped.edges) == 15
    assert skipped.radius == 4.0

    reduced = _blend(_FakeShape(impossible, ceiling=0.2), edges, 4.0,
                     on_failure="reduce")
    # Every edge is blended, and only the one that refused came down
    # (ADR-128). Lowering all sixteen to what the worst edge accepts is a
    # visible loss on an organic body: one tight crotch should not flatten
    # every haunch.
    assert len(reduced.edges) == 16
    assert isinstance(reduced.radius, tuple)
    assert reduced.radius.count(4.0) == 15
    lowered = [value for value in reduced.radius if value != 4.0]
    assert len(lowered) == 1 and 0.0 < lowered[0] <= 0.2


def test_reduce_reports_which_edges_it_had_to_lower() -> None:
    """A model cannot see the shape; the split has to be in the result."""

    edges = _edges(16)
    shape = _FakeShape({edges[3]}, ceiling=0.2)
    diagnostics: dict = {}
    _blend(shape, edges, 4.0, on_failure="reduce", diagnostics=diagnostics)
    report = diagnostics["fillet_partial"][-1]
    assert report["applied"] == "reduce"
    assert report["edges_at_requested"] == 15
    assert report["edges_reduced"] == 1


def test_a_chamfer_reduces_uniformly_because_it_has_no_per_edge_form() -> None:
    """``makeChamfer`` takes one distance per call, and we say so.

    The alternative is a chamfer that silently reports a per-edge split it
    never applied.
    """

    edges = _edges(16)
    shape = _FakeShape({edges[3]}, ceiling=0.2)
    diagnostics: dict = {}
    result = worker._blend(shape, "chamfer", edges, _details(edges), 4.0,
                           on_failure="reduce", diagnostics=diagnostics)
    assert not isinstance(result.radius, tuple)
    report = diagnostics["chamfer_partial"][-1]
    assert report["edges_at_requested"] == 0
    assert report["edges_reduced"] == 16


def test_reduce_falls_back_to_skipping_when_no_radius_works() -> None:
    """An edge that fails at every radius is skipped, not silently dropped."""

    edges = _edges(16)
    shape = _FakeShape(impossible={edges[7]}, ceiling=-1.0)
    result = _blend(shape, edges, 4.0, on_failure="reduce")
    assert len(result.edges) == 15
    assert edges[7] not in result.edges


def test_refuse_is_the_default_and_nothing_is_skipped_unaskedfor() -> None:
    """The expected_count principle: loud first, partial work only on request."""

    edges = _edges(8)
    shape = _FakeShape(impossible={edges[1]}, ceiling=0.1)
    with pytest.raises(worker.PartOperationError):
        _blend(shape, edges, 1.0)


def test_skip_with_nothing_blendable_still_refuses() -> None:
    edges = _edges(4)
    shape = _FakeShape(impossible=set(edges), ceiling=-1.0)
    with pytest.raises(worker.PartOperationError) as caught:
        _blend(shape, edges, 1.0, on_failure="skip")
    assert "no edge" in str(caught.value)


# -- the cost cap -----------------------------------------------------------


def test_the_probe_cap_is_reported_rather_than_hidden() -> None:
    """A capped probe says so. Silently doing less work is the thing to avoid."""

    edges = _edges(256)
    # Every other edge impossible: the bisection cannot finish inside the cap.
    shape = _FakeShape(impossible=set(edges[::2]), ceiling=-1.0)
    with pytest.raises(worker.PartOperationError) as caught:
        _blend(shape, edges, 1.0)
    observed = caught.value.details["observed"]
    assert observed["probe_capped"] is True
    assert observed["edges_unprobed"] > 0
    assert observed["probe_calls"] <= worker._BLEND_PROBE_CALLS + 8
    assert "cap" in str(caught.value)


def test_a_long_refusal_list_is_counted_not_dumped() -> None:
    edges = _edges(128)
    shape = _FakeShape(impossible=set(edges[:40]), ceiling=-1.0)
    with pytest.raises(worker.PartOperationError) as caught:
        _blend(shape, edges, 1.0)
    observed = caught.value.details["observed"]
    assert len(observed["refused_edges"]) <= worker._BLEND_REPORTED_EDGES


# -- partial work is recorded where a caller is collecting ------------------


def test_partial_work_reaches_the_diagnostics_channel() -> None:
    edges = _edges(16)
    shape = _FakeShape(impossible={edges[2]}, ceiling=0.1)
    diagnostics: dict = {}
    _blend(shape, edges, 1.0, on_failure="skip", diagnostics=diagnostics)
    report = diagnostics["fillet_partial"][0]
    assert report["applied"] == "skip"
    assert report["edges_blended"] == 15
    assert report["edges_refused"] == 1


# -- the argument itself ----------------------------------------------------


def test_on_failure_is_validated_before_the_kernel_sees_it() -> None:
    from cadex_part_api import _blend_failure_mode

    assert _blend_failure_mode("fillet", "SKIP") == "skip"
    with pytest.raises(ValueError) as caught:
        _blend_failure_mode("fillet", "carry on")
    assert "on_failure" in str(caught.value)


# -- against a live kernel --------------------------------------------------


#: A post welded into a bar: 8 faces, 15 edges, and one seam circle where
#: the cylinder enters. Small enough to read, real enough to refuse.
_BODY = """
bar = part.box(60, 30, 12, origin=[0, 0, 0])
post = part.cylinder(5, 40, origin=[30, 15, 0])
welded = part.fuse([bar, post], label="welded")
"""

WORKING_SOURCE = _BODY + """
rounded = part.fillet(welded, 3.0, label="rounded")
result = {"welded": welded, "rounded": rounded}
"""

IMPOSSIBLE_SOURCE = _BODY + """
rounded = part.fillet(welded, 40.0, label="rounded")
result = {"welded": welded, "rounded": rounded}
"""

REDUCED_SOURCE = _BODY + """
rounded = part.fillet(welded, 40.0, on_failure="reduce", label="rounded")
result = {"welded": welded, "rounded": rounded}
"""

#: A body with a *mixed* answer, which is what the per-edge form is for: the
#: slab's twelve edges take 12 mm comfortably (its thinnest dimension is 40)
#: and the 5 mm post's two circles cannot take it at any price.
_MIXED_BODY = """
slab = part.box(200, 60, 40, origin=[0, 0, 0])
post = part.cylinder(5, 30, origin=[100, 30, 40])
welded = part.fuse([slab, post], label="welded")
"""

MIXED_REFUSED_SOURCE = _MIXED_BODY + """
rounded = part.fillet(welded, 12.0, label="rounded")
result = {"welded": welded, "rounded": rounded}
"""

MIXED_REDUCED_SOURCE = _MIXED_BODY + """
rounded = part.fillet(welded, 12.0, on_failure="reduce", label="rounded")
result = {"welded": welded, "rounded": rounded}
"""

MIXED_UNIFORM_SOURCE = _MIXED_BODY + """
rounded = part.fillet(welded, {radius}, label="rounded")
result = {{"welded": welded, "rounded": rounded}}
"""


def _face_count(client, output: str) -> int:
    """Count a shape's faces through the expected_count=0 failure envelope."""

    probe = client.request(
        "resolve_pin",
        {"output": output, "selection": {"element_type": "face", "expected_count": 0}},
    )
    return len(((probe.get("observed") or {}).get("available")) or [])


def _write(client, source: str, prefix: str):
    """One script into a project of its own, so no revision is carried."""

    client.request(
        "open_project", {"project_root": tempfile.mkdtemp(prefix=prefix)}
    )
    return client.request(
        "write_script", {"source": source, "expected_revision": ""}
    )


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available for a real blend.",
)
def test_a_real_blend_survives_a_radius_the_body_cannot_take() -> None:
    """End to end, on geometry the kernel actually refuses.

    Measured on this body: every edge takes 3 mm, no edge takes 40 mm, and
    4.375 mm is the largest the whole selection accepts. Before ADR-125 the
    40 mm call answered ``15StdFail_NotDone``; there was no way to learn the
    4.375 short of guessing.
    """

    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()

        working = _write(client, WORKING_SOURCE, "cadexd-blend-ok-")
        assert working["ok"] is True, working
        plain, blended = _face_count(client, "welded"), _face_count(client, "rounded")
        assert plain == 8, plain
        assert blended > plain, (plain, blended)

        refused = _write(client, IMPOSSIBLE_SOURCE, "cadexd-blend-no-")
        assert refused["ok"] is False, refused
        message = json.dumps(refused)
        assert "StdFail" not in message, message
        observed = (refused.get("observed") or {}).get("details", {}).get("observed")
        assert observed is not None, refused
        assert observed["edges_selected"] == 15, observed
        assert observed["edges_refused"] == 15, observed
        workable = observed["largest_workable_radius_mm"]
        assert workable is not None and 3.0 < workable < 6.0, observed
        # And the search stayed cheap on real geometry.
        assert observed["probe_calls"] <= worker._BLEND_PROBE_CALLS, observed

        reduced = _write(client, REDUCED_SOURCE, "cadexd-blend-red-")
        assert reduced["ok"] is True, reduced
        assert _face_count(client, "rounded") == blended
    finally:
        _stop(client)


def _solid_volume(client, output: str) -> float:
    probe = client.request(
        "resolve_pin",
        {"output": output, "selection": {"element_type": "solid", "expected_count": 0}},
    )
    solids = ((probe.get("observed") or {}).get("available")) or []
    assert len(solids) == 1, solids
    return float(solids[0]["volume_mm3"])


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available for a real blend.",
)
def test_reduce_keeps_the_radius_on_the_edges_that_can_take_it() -> None:
    """ADR-128, against the kernel rather than against a fake.

    The per-edge form is a Cadex addition to ``TopoShapePy::makeFillet``, so
    the assertion that matters is geometric: a mixed reduce must remove
    **more** material than lowering the whole body to what its worst edge
    accepts. Same edges, same call count, more of the shape people asked for.
    """

    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()

        refused = _write(client, MIXED_REFUSED_SOURCE, "cadexd-mixed-no-")
        assert refused["ok"] is False, refused
        observed = (refused.get("observed") or {}).get("details", {}).get("observed")
        assert observed["edges_blended"] == 14, observed
        assert observed["edges_refused"] == 1, observed
        workable = float(observed["largest_workable_radius_mm"])
        assert 0.0 < workable < 12.0, observed

        mixed = _write(client, MIXED_REDUCED_SOURCE, "cadexd-mixed-red-")
        assert mixed["ok"] is True, mixed
        mixed_volume = _solid_volume(client, "rounded")

        uniform = _write(
            client,
            MIXED_UNIFORM_SOURCE.format(radius=workable),
            "cadexd-mixed-uni-",
        )
        assert uniform["ok"] is True, uniform
        uniform_volume = _solid_volume(client, "rounded")

        assert mixed_volume < uniform_volume, (mixed_volume, uniform_volume)
    finally:
        _stop(client)
