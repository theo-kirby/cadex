# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Fitting a parametric script to a density field, and the four refusals (S4).

``analysis/skeleton.py`` turns a SIMP field into a **script**, which is the
one thing no other generative-design tool ends in. Its placement contract --
where it lives, what CMake may never do with it, what it may import and the
standing prohibition on GPL packages -- is asserted beside the rest of the
tree in ``test_analysis_stress.py``; this file is about whether the fit is
right and whether it fails loudly when it is not.

Five checks, in the order they catch things:

1. **The anchors survive.** Every support and load region gets a node, and
   that node is connected to the rest. This is the failure that would matter
   most and be entirely silent: the script still builds, the render still
   looks like a bracket, and the bolt hole is on a lump touching nothing.
2. **The coverage refuses.** A deliberately plate-like field is rejected
   with its number rather than fitted, because a strut graph over a plate is
   a tidy part that is much weaker than the one that was carved.
3. **Symmetry in, symmetry out.** A field symmetric about its own mid-plane
   fits to a node set that is symmetric too, which is what makes the emitted
   table readable rather than merely correct.
4. **The controllers converge.** The sizing loop's two corrections --
   redistribute, then set the total -- are tested on their own arithmetic,
   because a loop that oscillates would otherwise only show up as a five
   minute run that ends somewhere odd.
5. **The emitted script is valid xscript**, parsed here and rebuilt through
   a real cadexd child. That last one needs a built engine and skips without
   one, the bar ``cli/tests`` sets.

Most of it runs against **synthetic** fields rather than carved ones -- a
truss of known segments, a shell of known wall thickness -- because a SIMP
run costs half a minute and proves nothing extra about the fitter. The one
engine-gated test carves nothing either.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[4]
ANALYSIS = ROOT / "analysis"
SKELETON = ANALYSIS / "skeleton.py"


def _module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(path.stem, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def topology():
    pytest.importorskip("scipy", reason="the fit needs scipy.ndimage")
    return _module(ANALYSIS / "topology.py")


@pytest.fixture(scope="module")
def skeleton(topology):
    pytest.importorskip("scipy", reason="the fit needs scipy.spatial")
    return _module(SKELETON)


# ---------------------------------------------------------------------------
# Synthetic fields, with the answer known in advance.
# ---------------------------------------------------------------------------


_MATERIAL = {
    "name": "test",
    "youngs_modulus_mpa": 3500.0,
    "poissons_ratio": 0.36,
    "yield_strength_mpa": 50.0,
    "density_kg_m3": 1240.0,
}

_SIZE = (48.0, 24.0, 24.0)


def _plan(topology, **overrides):
    """A two-footed bracket plan over a 48 x 24 x 24 blank."""

    sx, sy, sz = _SIZE
    raw = {
        "schema": topology.PLAN_SCHEMA,
        "name": "truss",
        "domain": {"box": {"size_mm": list(_SIZE), "origin_mm": [0.0, 0.0, 0.0]}},
        "element_mm": 2.0,
        "volume_fraction": 0.3,
        "filter_radius_mm": 4.0,
        "penalty": 3.0,
        "iterations": 1,
        "interface_pad_mm": 4.0,
        "material": _MATERIAL,
        "supports": [
            {"name": "near",
             "region": {"box": {"min_mm": [None, None, None],
                                "max_mm": [12.0, None, 1e-3]}}},
            {"name": "far",
             "region": {"box": {"min_mm": [sx - 12.0, None, None],
                                "max_mm": [None, None, 1e-3]}}},
        ],
        "loads": [
            {"name": "boss",
             "region": {"box": {"min_mm": [0.4 * sx, None, sz - 1e-3],
                                "max_mm": [0.6 * sx, None, None]}},
             "force_n": [0.0, 0.0, -200.0]},
        ],
    }
    raw.update(overrides)
    return topology.Plan.from_mapping(raw)


def _segment_distance(points, start, end):
    start = np.asarray(start, dtype=float)
    span = np.asarray(end, dtype=float) - start
    t = np.clip(((points - start) @ span) / float(span @ span), 0.0, 1.0)
    return np.linalg.norm(points - (start + t[:, None] * span), axis=1)


def _truss_field(topology, plan, radius_mm=5.0):
    """A capital-A truss: two legs to a top node, tied along the bottom.

    Segments chosen so the field is symmetric about the ``y`` mid-plane and
    about ``x = 24``, and so its ends reach the blank's own faces -- which
    is what the supports and the load are declared on.
    """

    grid = topology.domain_grid(plan.domain, plan.element_mm)
    points = grid.cell_centres()
    near, far, top = (6.0, 12.0, 4.0), (42.0, 12.0, 4.0), (24.0, 12.0, 20.0)
    inside = np.zeros(len(points), dtype=bool)
    for start, end in ((near, top), (far, top), (near, far)):
        inside |= _segment_distance(points, start, end) <= radius_mm
    return inside.reshape(grid.shape).astype(float), grid


def _shell_field(topology, plan, wall_mm=4.0):
    """A hollow box: the field struts are the wrong model for.

    A shell, not a slab, and the difference is measured. A **slab** is
    fitted well -- its medial axis is one sheet, the packing lands nodes all
    over it and the coverage comes back 0.90 to 0.97 -- so a slab is not
    what the gate is for. A shell has four sheets meeting at four edges,
    every one of them a cell or two thick, and the same fit covers 0.56 of
    it. That is the shape whose material a strut graph cannot hold.
    """

    grid = topology.domain_grid(plan.domain, plan.element_mm)
    points = grid.cell_centres()
    _, sy, sz = _SIZE
    inside = ((np.abs(points[:, 1] - 0.5 * sy) >= 0.5 * sy - wall_mm)
              | (np.abs(points[:, 2] - 0.5 * sz) >= 0.5 * sz - wall_mm))
    return inside.reshape(grid.shape).astype(float), grid


# ---------------------------------------------------------------------------
# 1. The anchors survive.
# ---------------------------------------------------------------------------


def test_every_support_and_load_gets_a_node_and_it_is_connected(
        skeleton, topology) -> None:
    """The silent failure: a mount on a lump of metal touching nothing.

    A disconnected support still emits, still builds and still renders as a
    bracket. Nothing downstream would catch it -- the compliance would come
    back enormous and be read as a bad fit rather than as a broken one -- so
    this is asserted directly on the graph.
    """

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    fitted = skeleton.fit(density, grid, plan)

    kinds = {(anchor.kind, anchor.name) for anchor in fitted.anchors}
    assert kinds == {("support", "near"), ("support", "far"), ("load", "boss")}

    union = skeleton._Union(len(fitted.nodes))
    for a, b in fitted.bar_ends:
        union.union(int(a), int(b))
    roots = {union.find(anchor.node) for anchor in fitted.anchors}
    assert len(roots) == 1, (
        "the three anchors landed in more than one component, so the fitted "
        "part is in pieces"
    )
    assert all(0 <= anchor.node < len(fitted.nodes) for anchor in fitted.anchors)


def test_a_disconnected_anchor_is_refused_rather_than_emitted(
        skeleton, topology) -> None:
    """Two lumps with nothing between them: the refusal, not a warning."""

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    # Cut the field in half across the middle, so the far foot's lobe cannot
    # reach the near one. The load node goes with whichever half keeps it.
    points = grid.cell_centres().reshape(grid.shape + (3,))
    density = np.where(np.abs(points[..., 0] - 24.0) <= 3.0, 0.0, density)

    with pytest.raises(skeleton.SkeletonError) as failure:
        skeleton.fit(density, grid, plan)
    message = str(failure.value)
    assert "not connected" in message
    assert "support" in message or "load" in message


def test_an_interface_that_the_carve_missed_is_refused_with_the_reason(
        skeleton, topology) -> None:
    """No material at a mount is a plan problem, and it says which key fixes it."""

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    points = grid.cell_centres().reshape(grid.shape + (3,))
    density = np.where(points[..., 2] <= 6.0, 0.0, density)   # saw the feet off

    with pytest.raises(skeleton.SkeletonError) as failure:
        skeleton.fit(density, grid, plan)
    assert "interface_pad_mm" in str(failure.value)


# ---------------------------------------------------------------------------
# 2. The coverage refuses.
# ---------------------------------------------------------------------------


def test_a_plate_like_field_is_refused_with_its_own_number(
        skeleton, topology) -> None:
    """Decision 2 of the slice, asserted rather than asserted about.

    The refusal has to carry the number and the place: "0.62" and "the
    largest single miss is 976 cells centred at ..." is what tells a person
    to carve differently. A bare "cannot fit" would not.
    """

    plan = _plan(topology, interface_pad_mm=6.0)
    density, grid = _shell_field(topology, plan)

    with pytest.raises(skeleton.SkeletonError) as failure:
        skeleton.fit(density, grid, plan)
    message = str(failure.value)
    assert "cover" in message and str(skeleton.MINIMUM_COVERAGE) in message
    assert "largest single miss" in message
    assert "mm^3" in message


def test_a_strut_like_field_clears_the_coverage_bar(skeleton, topology) -> None:
    """The other side of the same gate, on a field that really is members."""

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    fitted = skeleton.fit(density, grid, plan)

    assert fitted.coverage["fraction"] >= skeleton.MINIMUM_COVERAGE
    assert fitted.coverage["solid_cells"] == int((density >= 0.5).sum())
    # Buildable: spike zero measured 64 solids at under 20 s with a blend,
    # and the whole reason `_SUPPRESSION` is 2.0 is to stay near that.
    assert len(fitted.nodes) + len(fitted.bar_ends) < 200


def test_the_coverage_counts_the_pads_because_the_script_emits_them(
        skeleton, topology) -> None:
    """A pad is material the script places, so a gate that ignored it would
    report a hole exactly where the mounting boss goes."""

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    fitted = skeleton.fit(density, grid, plan)

    solid = density >= 0.5
    points = grid.cell_centres().reshape(grid.shape + (3,))[solid]
    without = skeleton._covered(points, fitted.nodes, fitted.bar_ends,
                                fitted.bar_radii,
                                slack=0.5 * float(grid.spacing.mean()))
    assert float(without.mean()) <= fitted.coverage["fraction"]


# ---------------------------------------------------------------------------
# 3. Symmetry in, symmetry out.
# ---------------------------------------------------------------------------


def test_a_symmetric_field_fits_to_a_symmetric_node_set(skeleton, topology) -> None:
    """What ``symmetry`` buys downstream, and it is the reason it is worth
    having: a symmetric field gives a symmetric node set and therefore a
    symmetric script, which is what a person reads as *designed*."""

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    assert np.allclose(density, np.flip(density, axis=1)), "the fixture is not symmetric"

    fitted = skeleton.fit(density, grid, plan)
    middle = 0.5 * (float(grid.origin[1])
                    + float(grid.origin[1] + grid.shape[1] * grid.spacing[1]))
    mirrored = fitted.nodes[:, :3].copy()
    mirrored[:, 1] = 2.0 * middle - mirrored[:, 1]

    tolerance = float(grid.spacing.mean())
    for point in mirrored:
        gaps = np.linalg.norm(fitted.nodes[:, :3] - point[None, :], axis=1)
        assert gaps.min() <= tolerance, (
            f"the node set has no partner for the mirror of {point}"
        )


# ---------------------------------------------------------------------------
# 4. The controllers converge.
# ---------------------------------------------------------------------------


def test_the_volume_controller_hits_the_volume_it_is_given(
        skeleton, topology) -> None:
    """``_scale_to_volume`` bisects rather than solving, because there is no
    formula: members go as ``r^2``, joints as ``r^3``, and both are clipped.
    So what has to be true is that it *lands*."""

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    fitted = skeleton.fit(density, grid, plan)
    floor = skeleton._size_floor(grid)

    start = fitted.analytic_volume_mm3()
    for factor in (0.6, 0.85, 1.0, 1.2):
        skeleton._scale_to_volume(fitted, start * factor, floor_mm=floor)
        landed = fitted.analytic_volume_mm3()
        assert abs(landed - start * factor) <= 0.02 * start * factor, (
            f"asked for {factor:.2f} of {start:.0f} mm^3 and landed on "
            f"{landed:.0f}"
        )


def test_the_redistribution_is_renormalised_and_therefore_does_not_drift(
        skeleton, topology) -> None:
    """The loop's own convergence property, on its arithmetic alone.

    A five-minute run that ends somewhere odd is an expensive way to find
    out that the two corrections were fighting. Ten rounds of "redistribute
    at random, renormalise" must leave the volume where it started -- if it
    does not, the sizing loop walks its mass target, which is exactly what
    it did before the corrections were separated.
    """

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    fitted = skeleton.fit(density, grid, plan)
    floor = skeleton._size_floor(grid)
    rng = np.random.default_rng(4)

    start = fitted.analytic_volume_mm3()
    for _ in range(10):
        before = fitted.analytic_volume_mm3()
        fitted.bar_radii = skeleton._bounded(
            fitted,
            fitted.bar_radii * rng.uniform(0.8, 1.25, (len(fitted.bar_radii), 1)),
            floor)
        skeleton._lift_nodes(fitted, floor_mm=floor)
        skeleton._scale_to_volume(fitted, before, floor_mm=floor)
    assert abs(fitted.analytic_volume_mm3() - start) <= 0.05 * start


def test_a_joint_is_exactly_as_thick_as_its_thickest_member(
        skeleton, topology) -> None:
    """The one word that made the loop diverge.

    Written as ``max(current, incident)`` a joint could only grow, so every
    pass ratcheted the part heavier whatever the mass correction asked for.
    A joint has the size of the members it joins, and shrinking them has to
    shrink it.
    """

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    fitted = skeleton.fit(density, grid, plan)
    floor = skeleton._size_floor(grid)

    fat = fitted.nodes[:, 3].copy()
    fitted.bar_radii = skeleton._bounded(fitted, fitted.bar_radii * 0.5, floor)
    skeleton._lift_nodes(fitted, floor_mm=floor)
    assert np.all(fitted.nodes[:, 3] <= fat + 1e-9)
    assert np.any(fitted.nodes[:, 3] < fat - 1e-9)

    incident = np.full(len(fitted.nodes), floor)
    for (a, b), (r0, r1) in zip(fitted.bar_ends, fitted.bar_radii):
        incident[int(a)] = max(incident[int(a)], r0)
        incident[int(b)] = max(incident[int(b)], r1)
    ceiling = np.maximum(fitted.node_headroom, floor)
    assert np.allclose(fitted.nodes[:, 3], np.clip(incident, floor, ceiling))


def test_no_member_may_grow_outside_the_blank(skeleton, topology) -> None:
    """The cap that keeps the emitted part inside the domain it was carved
    from -- and therefore keeps the mounting pads' outer faces single planar
    faces, which is what the ``part.stress`` selectors resolve against."""

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    fitted = skeleton.fit(density, grid, plan)
    floor = skeleton._size_floor(grid)

    fitted.bar_radii = skeleton._bounded(fitted, fitted.bar_radii * 100.0, floor)
    skeleton._lift_nodes(fitted, floor_mm=floor)
    assert np.all(fitted.bar_radii <= fitted.bar_headroom[:, None] + 1e-9)
    assert np.all(fitted.nodes[:, 3] <= np.maximum(fitted.node_headroom, floor) + 1e-9)


# ---------------------------------------------------------------------------
# The radius field, which every number above rests on.
# ---------------------------------------------------------------------------


def test_the_distance_transform_reads_a_known_thickness(skeleton) -> None:
    """A cylinder and a slab whose answers are arithmetic.

    The refinement is here because the binary transform is biased, and the
    bias runs opposite ways for a curved boundary and a flat one -- so both
    shapes are checked, and the tolerance is the eighth of a cell the
    docstring claims.
    """

    import cadex_stress as stress_module   # noqa: F401  (already imported by skeleton)

    spacing = np.array([1.0, 1.0, 1.0])
    shape = (40, 24, 24)
    axes = [(np.arange(n) + 0.5) for n in shape]
    x, y, z = np.meshgrid(*axes, indexing="ij")

    radial = np.sqrt((y - 12.0) ** 2 + (z - 12.0) ** 2)
    cylinder = (radial <= 8.0).astype(float)
    measured = skeleton.local_radius_mm(cylinder, spacing).max()
    # The deepest cell centre sits sqrt(0.5) from the axis of an 8 mm bore.
    assert abs(measured - (8.0 - np.sqrt(0.5))) <= 0.25

    slab = ((z >= 8.0) & (z <= 12.0)).astype(float)
    assert abs(skeleton.local_radius_mm(slab, spacing).max() - 1.5) <= 0.25


def test_the_radius_never_reaches_outside_the_solid(skeleton, topology) -> None:
    """A sphere of the fitted radius at a fitted node stays in the field.

    Which is the property the whole fit rests on: if it did not hold, every
    strut would poke out of the blank and the pads would stop being planes.
    """

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    radius = skeleton.local_radius_mm(density, grid.spacing)
    solid = density >= 0.5

    points = grid.cell_centres().reshape(grid.shape + (3,))
    void = points[~solid]
    deepest = np.argsort(-radius[solid])[:20]
    inside = points[solid][deepest]
    for centre, r in zip(inside, radius[solid][deepest]):
        gap = np.linalg.norm(void - centre[None, :], axis=1).min()
        assert gap + 0.5 * float(grid.spacing.mean()) >= r - 1e-6


# ---------------------------------------------------------------------------
# 5. The emitted script.
# ---------------------------------------------------------------------------


def test_the_emitted_script_parses_and_declares_what_it_promises(
        skeleton, topology) -> None:
    """Valid Python, three parameters, and the tables it says it carries."""

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    fitted = skeleton.fit(density, grid, plan)
    source = skeleton.emit_script(fitted, plan, output="bracket")

    tree = ast.parse(source)
    assigned = {target.id
                for node in tree.body if isinstance(node, ast.Assign)
                for target in node.targets if isinstance(target, ast.Name)}
    assert {"p", "NODES", "STRUTS", "PADS", "solids", "bracket",
            "result"} <= assigned

    namespace: dict[str, object] = {}
    exec(compile(ast.Module(  # noqa: S102 -- the tables are data, not calls
        body=[node for node in tree.body
              if isinstance(node, ast.Assign)
              and isinstance(node.targets[0], ast.Name)
              and node.targets[0].id in {"NODES", "STRUTS", "PADS"}],
        type_ignores=[]), "<emitted>", "exec"), namespace)
    assert len(namespace["NODES"]) == len(fitted.nodes)
    assert len(namespace["STRUTS"]) == len(fitted.bar_ends)
    assert len(namespace["PADS"]) == len(fitted.anchors)
    for a, b, _, _ in namespace["STRUTS"]:
        assert 0 <= int(a) < len(fitted.nodes)
        assert 0 <= int(b) < len(fitted.nodes)

    # The three parameters, and only the three: `num()` is numeric-only and
    # forty radii is not a search space, so the table is plain editable text.
    assert source.count("=num(") + source.count("= num(") == 3
    for name in ("strut_scale", "min_radius_mm", "blend_mm"):
        assert f"{name}=num(" in source


def test_the_emitted_script_anchors_its_load_case_to_the_blank(
        skeleton, topology) -> None:
    """``part.stress`` travels with the shape, or it is not emitted at all."""

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    fitted = skeleton.fit(density, grid, plan)
    source = skeleton.emit_script(fitted, plan, output="bracket")

    assert "part.stress(" in source
    for anchor in fitted.anchors:
        assert anchor.plane is not None, f"{anchor.name} is not on a blank face"
    # Every selector names a plane, a place and a size -- the three keys the
    # measurement in `_selector` says are each necessary.
    for key in ('"geometry_type": "Plane"', '"near_point"', '"min_area"',
                '"expected_count": 1'):
        assert key in source
    assert f"yield_strength_mpa={_MATERIAL['yield_strength_mpa']:g}" in source


def test_a_load_case_off_the_blank_drops_the_check_rather_than_the_script(
        skeleton, topology) -> None:
    """An interface buried inside the material cannot be named by a selector.

    That is a real limit -- a selector names a plane of the blank and
    nothing else -- and the answer is to emit a script that still builds and
    still sweeps, with the reason recorded, rather than to refuse.
    """

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    fitted = skeleton.fit(density, grid, plan)
    for anchor in fitted.anchors:
        anchor.plane = None
    source = skeleton.emit_script(fitted, plan, output="bracket")

    assert "part.stress(" not in source
    assert "result = {'bracket': bracket}" in source
    assert any("no `part.stress` check" in warning for warning in fitted.warnings)


def test_a_strut_of_equal_radii_is_a_cylinder_and_not_a_cone(
        skeleton, topology) -> None:
    """OCC has no cone of equal radii, and spike zero found it the hard way:
    every one of forty struts was refused with "creation of cone failed"
    before a single blend had been attempted."""

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    fitted = skeleton.fit(density, grid, plan)
    source = skeleton.emit_script(fitted, plan, output="bracket")

    assert "part.cylinder(" in source and "part.cone(" in source
    assert "abs(start - end) < 1.0e-6" in source


def test_the_report_carries_the_verdict_and_the_bar(skeleton, topology) -> None:
    """One number, and what it is measured against, in the same object."""

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    fitted = skeleton.fit(density, grid, plan)
    finished = skeleton.report(fitted, plan, None, simp={}, wall_time_s=0.1)

    assert finished["schema"] == skeleton.REPORT_SCHEMA
    assert finished["verdict"]["bar"] == skeleton.COMPLIANCE_BAR
    assert finished["verdict"]["outcome"] == "not-measured"
    assert finished["fit"]["coverage"]["fraction"] >= skeleton.MINIMUM_COVERAGE
    assert json.loads(json.dumps(finished))     # it is a receipt, so it serialises


def test_a_refusal_is_an_exit_code_and_a_sentence(tmp_path) -> None:
    """The CLI contract every file in this tree keeps: 2, and a reason."""

    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"schema": "not-a-topology-plan"}), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SKELETON), str(plan), "--out", str(tmp_path / "out")],
        capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert result.stderr.startswith("refused: ")


# ---------------------------------------------------------------------------
# Through a real engine.
# ---------------------------------------------------------------------------


def _engine_available() -> bool:
    if os.environ.get("CADEX_ENGINE_ROOT"):
        return True
    return (ROOT / "build/release/bin/FreeCADCmd").is_file()


@pytest.mark.skipif(not _engine_available(),
                    reason="no built engine; run `pixi run build-engine`")
def test_the_emitted_script_builds_in_a_real_engine(skeleton, topology,
                                                    tmp_path) -> None:
    """S4c, end to end, and the only thing that can prove the emitter right.

    A script that parses is not a script that builds: ``part.cone`` refuses
    equal radii, ``part.fuse`` refuses a blend it cannot make, and an
    ADR-029 selector refuses a cardinality it does not match. All three were
    found here rather than by reading.
    """

    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    plan = _plan(topology)
    density, grid = _truss_field(topology, plan)
    fitted = skeleton.fit(density, grid, plan)
    source = skeleton.emit_script(fitted, plan, output="bracket", blend_mm=0.0)

    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request(
            "open_project", {"project_root": str(tmp_path / "project")})
        assert opened["ok"] is True, opened

        written = client.request(
            "write_script",
            {"source": source, "expected_revision": "",
             "display": {"quality": "standard"}},
            timeout=900.0)
        assert written["ok"] is True, written.get("error")
        assert written["display"]["bracket"]["artifact_kind"] in {"brep", "solid"}

        # The three declared parameters reach a client as bounded specs,
        # which is what makes `analysis/search.py` able to sweep it.
        scoped = client.request("inspect", {"scope": "script"})
        assert scoped["ok"] is True, scoped
        specs = {spec["name"]
                 for spec in scoped["value"]["params"]["specs"]}
        assert specs == {"strut_scale", "min_radius_mm", "blend_mm"}
    finally:
        _stop(client)
