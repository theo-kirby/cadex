#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A declared blank and a load case in, a watertight shape out (S2).

**This program is not part of the engine and is never installed into the
payload.** Same contract as ``cadex_stress.py`` beside it and
``training/cadex_train.py`` above it: CMake never installs it, no payload
carries it, nothing in it enters ``pixi.toml``, and nothing in it may import
a GPL package. ADR-143 records the slice; ``docs/STRUCTURAL.md`` 5 is the
arc.

It is S0's solver in a loop. Density in ``[0, 1]`` on every cell of the same
structured hex grid, a filter, a linear solve, a compliance sensitivity, an
optimality-criteria update, repeat. The *only* thing that had to change in
the solver is that the assembly scales each element's matrix by
``simp_scale(rho, p)`` before it scatters it -- which is legitimate with the
condensed C3D8I element because static condensation commutes with a uniform
scaling of the element energy, the property ADR-141 chose that element for.

Measured on an M-series laptop, so that nobody has to guess whether this
needs a GPU box: one iteration is about **0.8 s at 13.5k elements** and
**3.7 s at 48k**, so a 100-iteration run is one and a half to six minutes.

**Geometry extraction is hand-written marching tetrahedra**, and that is a
decision rather than an accident. The alternative was ``scikit-image``, a
new pinned dependency for one function; the six-tetrahedron split of a cube
is about sixty lines, has **no ambiguous-face cases** at all -- which is
exactly what marching cubes has and what makes its output non-manifold --
and welds its vertices on the grid edge each one sits on rather than on a
floating-point tolerance. So the surface is watertight by construction, and
``analysis/requirements.txt`` stays at three pins.

**What is deliberately not here.** No printability constraint: overhang
angle and minimum wall thickness are not built and are not planned, because
supports handle overhangs and a constraint nobody needs is a constraint that
distorts the result. The *filter radius* stays, and it is not a
manufacturing parameter -- without it SIMP checkerboards, because the
discretised problem has no minimiser and the answer changes with the grid.
It is what makes the problem well-posed. That is the whole of its
justification and it is enough.

And no stress constraint: SIMP minimises compliance. Read the result's
stress by running the extracted shape back through ``cadex_stress.py``,
which is a real second measurement rather than a number this loop produced
about itself.

**S4a adds four keys, all opt-in and all off by default** (ADR-146), so a
plan written against S2 carves the same field under this file. Three of them
are defects the first real render exposed and one is what makes a result
read as designed:

``symmetry``
    Average the filtered sensitivity with its own mirror each iteration. The
    eye reads asymmetry as *error* before it reads anything else, so this is
    the largest looks-designed win per line in the file -- and it halves
    ``skeleton.py``'s job, because a symmetric field gives a symmetric node
    set and therefore a symmetric script.
``extrude``
    Average the sensitivity along one axis, so density is constant through
    the thickness. A 2.5-D part you can route or laser-cut, not only print.
``interface_pad_mm``
    Grow every ``supports`` and ``loads`` region and hold it. Without this a
    load declared on a 2 mm-deep face gets the cheapest membrane that can
    receive the force -- structurally correct, and useless as a mounting
    interface.
``pin_domain_planes``
    Keep the vertices that came out on a face of the blank on it through the
    smoother. A mounting face is flat; the smoother does not know that.

**Read the discreteness off the design variable, not off the density.** The
two fields are different things and only one of them is the answer. A
density filter of radius R smears a perfectly binary design over a band of
width R, so a member thinner than 2R is grey right through its core however
well the run converged. Measured on the cantilever: a design variable of
3833 cells at 0, 1638 at 1 and 129 anywhere else -- a non-discreteness of
**0.017**, which is as resolved as SIMP gets -- has a *density*
non-discreteness of **0.32**. Both numbers are in the report, and the
warning is spent on the first. What makes this safe rather than a matter of
taste is that the extracted surface is the ``rho = 0.5`` level set, and on
that same run the cells above the level set came to 1683 against a density
integral of 1680: the grey band is symmetric about the surface, so it
cancels.

Usage::

    python analysis/topology.py plan.json --out ./run
    python analysis/topology.py --self-check
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from typing import Any, Sequence

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cadex_stress as stress  # noqa: E402

PLAN_SCHEMA = "cadex-analysis-topology-v1"
REPORT_SCHEMA = "cadex-analysis-topology-report-v1"

#: The level set the surface is extracted at. Halfway is the only choice
#: that treats solid and void alike, and it is far from both the void floor
#: and the ``keep`` value of 1, so no sample lands exactly on it and no
#: triangle comes out degenerate.
_ISO_LEVEL = 0.5

#: How far one optimality-criteria step may move a density. The classic
#: value; larger oscillates, smaller just costs iterations.
_MOVE_LIMIT = 0.2

#: The optimality-criteria exponent. 0.5 is the standard damping.
_OC_DAMPING = 0.5

#: A run has converged when no density moved more than this in a step --
#: and only once the penalty continuation has finished, because a design
#: that has stopped moving at ``p = 1.4`` has not stopped moving.
_CHANGE_TOLERANCE = 0.01


class TopologyError(RuntimeError):
    """A refusal with a sentence a person can act on."""


# ---------------------------------------------------------------------------
# The plan.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Plan:
    """One declared optimisation.

    ``material``, ``supports`` and ``loads`` are reused **verbatim** from
    ``cadex-analysis-load-case-v1``, and ``keep`` / ``void`` reuse S0's
    region vocabulary unchanged -- ``face``, ``box``, ``sphere``, ``all``.
    S2 invents no new geometry language, so a load case written for a stress
    check is already most of a topology plan.
    """

    domain: dict[str, Any]
    element_mm: float
    volume_fraction: float
    filter_radius_mm: float
    penalty: float
    iterations: int
    load_case: dict[str, Any]
    keep: list[dict[str, Any]] = field(default_factory=list)
    void: list[dict[str, Any]] = field(default_factory=list)
    solver: str = "auto"
    name: str = "topology"
    #: S4a. All four default to off, so a plan written for S2 carves
    #: **bit-identically** under this file (``test_analysis_topology``
    #: asserts it).
    symmetry: tuple[int, ...] = ()
    extrude: int | None = None
    interface_pad_mm: float = 0.0
    pin_domain_planes: bool = False

    @classmethod
    def from_mapping(cls, raw: Any, *, base: Path | None = None) -> "Plan":
        if not isinstance(raw, dict):
            raise TopologyError("A topology plan is a JSON object.")
        schema = str(raw.get("schema") or "")
        if schema != PLAN_SCHEMA:
            raise TopologyError(
                f"This plan declares schema {schema!r}, and this reads "
                f"{PLAN_SCHEMA!r}."
            )
        domain = raw.get("domain")
        if not isinstance(domain, dict) or len(domain) != 1:
            raise TopologyError(
                "A plan declares exactly one `domain`: either "
                '`{"box": {"size_mm": [...], "origin_mm": [...]}}` or '
                '`{"solid": "part.stl"}`.'
            )
        if "solid" in domain and base is not None:
            path = Path(str(domain["solid"]))
            if not path.is_absolute():
                domain = {"solid": str((base / path).resolve())}

        fraction = float(raw.get("volume_fraction", 0.0))
        if not 0.0 < fraction < 1.0:
            raise TopologyError(
                f"`volume_fraction` is {fraction}, and it is the fraction of "
                "the declared domain that may keep material, so it lies "
                "strictly between 0 and 1."
            )
        element_mm = float(raw.get("element_mm", 0.0))
        if element_mm <= 0.0:
            raise TopologyError("`element_mm` must be positive.")
        radius = float(raw.get("filter_radius_mm", 0.0))
        if radius < element_mm:
            raise TopologyError(
                f"`filter_radius_mm` is {radius} against an element of "
                f"{element_mm} mm. The filter is what makes this problem "
                "well-posed -- below one element it filters nothing, the "
                "design checkerboards, and the answer becomes a function of "
                "the grid rather than of the loads. Declare at least 1.5 "
                "elements; 2 to 3 is usual."
            )
        penalty = float(raw.get("penalty", 3.0))
        if not 1.0 <= penalty <= 6.0:
            raise TopologyError(
                f"`penalty` is {penalty}, and SIMP's exponent lies in [1, 6]. "
                "3 is the standard value; 1 is a linear interpolation that "
                "does not push the design toward 0 or 1 at all."
            )
        iterations = int(raw.get("iterations", 60))
        if iterations < 1:
            raise TopologyError("`iterations` must be at least 1.")

        symmetry = tuple(_axis_index("symmetry", name)
                         for name in (raw.get("symmetry") or []))
        if len(set(symmetry)) != len(symmetry):
            raise TopologyError("`symmetry` names the same axis twice.")
        extrude = raw.get("extrude")
        extrude_axis = None if extrude is None else _axis_index("extrude", extrude)
        pad = float(raw.get("interface_pad_mm") or 0.0)
        if pad < 0.0:
            raise TopologyError(
                "`interface_pad_mm` is how far a support or load region is "
                "grown before it is held, so it is not negative.")

        return cls(
            domain=domain,
            element_mm=element_mm,
            volume_fraction=fraction,
            filter_radius_mm=radius,
            penalty=penalty,
            iterations=iterations,
            load_case={
                "schema": stress.LOAD_CASE_SCHEMA,
                "material": raw.get("material"),
                "supports": raw.get("supports") or [],
                "loads": raw.get("loads") or [],
                "gravity_m_s2": raw.get("gravity_m_s2"),
            },
            keep=list(raw.get("keep") or []),
            void=list(raw.get("void") or []),
            solver=str(raw.get("solver") or "auto"),
            name=str(raw.get("name") or "topology"),
            symmetry=symmetry,
            extrude=extrude_axis,
            interface_pad_mm=pad,
            pin_domain_planes=bool(raw.get("pin_domain_planes") or False),
        )


_AXES = {"x": 0, "y": 1, "z": 2}


def _axis_index(key: str, value: Any) -> int:
    name = str(value).lower()
    if name not in _AXES:
        raise TopologyError(
            f"`{key}` names an axis from x, y and z, not {value!r}.")
    return _AXES[name]


def domain_grid(domain: dict[str, Any], element_mm: float) -> stress.Grid:
    """The design domain, voxelised.

    A **box** is the primary case S2 was specified around: declare a blank
    and let the loop carve it. A **solid** is the same code path with a
    different starting occupancy -- lightening an existing part is a
    topology run whose design domain happens to be the part -- and it falls
    out for free rather than being a second feature.
    """

    (kind, spec), = domain.items()
    if kind == "box":
        size = np.asarray(spec.get("size_mm"), dtype=float)
        origin = np.asarray(spec.get("origin_mm") or [0.0, 0.0, 0.0], dtype=float)
        if size.shape != (3,) or np.any(size <= 0.0):
            raise TopologyError(
                "A `box` domain needs a positive `size_mm` of three numbers."
            )
        triangles = stress.box_triangles(size, origin)
        return stress.voxelise(triangles, element_mm)
    if kind == "solid":
        path = Path(str(spec))
        if not path.is_file():
            raise TopologyError(f"The domain solid {path} is not a file.")
        triangles, _ = stress.read_solid(path)
        if stress.mesh_volume_mm3(triangles) <= 0.0:
            raise TopologyError(
                f"{path.name} tessellates to a non-positive volume, so it is "
                "either inside out or not closed."
            )
        return stress.voxelise(triangles, element_mm)
    raise TopologyError(f"Unknown domain kind {kind!r}; it is `box` or `solid`.")


# ---------------------------------------------------------------------------
# The filter.
# ---------------------------------------------------------------------------


def cone_kernel(radius_mm: float, spacing: np.ndarray) -> np.ndarray:
    """The classic ``max(0, R - distance)`` weight, on this grid's spacing.

    In **physical** millimetres rather than in cells, which is the whole
    point: the same declared radius at two grid resolutions must give the
    same topology, and that is what mesh independence means and what the
    filter is tested on.
    """

    spacing = np.asarray(spacing, dtype=float)
    half = np.maximum(np.ceil(radius_mm / spacing).astype(int), 1)
    axes = [np.arange(-half[axis], half[axis] + 1) * spacing[axis]
            for axis in range(3)]
    dx, dy, dz = np.meshgrid(*axes, indexing="ij")
    distance = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
    return np.maximum(0.0, radius_mm - distance)


class DensityFilter:
    """A linear density filter, and its exact transpose.

    Density filtering rather than sensitivity filtering, because the chain
    rule through it is *exact*: ``rho = H x / d`` with ``d = H 1``, so
    ``dc/dx = H^T (dc/drho / d)``, and ``H`` is a symmetric convolution so
    its transpose is the same convolution. That means the analytic
    sensitivity this hands back can be checked against a finite difference
    and either agree or be wrong -- which is what the check is for. A
    sensitivity filter is a heuristic and has no such check.
    """

    def __init__(self, shape: tuple[int, int, int], radius_mm: float,
                 spacing: np.ndarray, inside: np.ndarray):
        self.shape = shape
        self.weights = cone_kernel(radius_mm, spacing)
        self.inside = inside.astype(float)
        self.denominator = self._convolve(self.inside)
        # A cell no weight reaches at all cannot happen with a radius of at
        # least one element, but dividing by it would be silent if it did.
        self.denominator[self.denominator <= 0.0] = 1.0
        #: ``d(sum rho)/dx``, and therefore the volume functional itself,
        #: since the filter is linear: ``sum(rho) = x . volume_gradient``
        #: exactly. That identity is what lets the optimality-criteria
        #: bisection constrain the **physical** volume without running a
        #: convolution inside the bisection loop -- two hundred of those an
        #: iteration would cost more than the solve. It also means the
        #: constraint that is enforced is the constraint that is reported,
        #: which the first version of this got wrong by 1.4%: it bisected on
        #: ``sum(x)``, and the normalised filter does not preserve a sum.
        self.volume_gradient = self.backward(self.inside)

    def _convolve(self, field: np.ndarray) -> np.ndarray:
        from scipy.ndimage import convolve

        return convolve(field, self.weights, mode="constant", cval=0.0)

    def forward(self, design: np.ndarray) -> np.ndarray:
        return self._convolve(design * self.inside) / self.denominator * self.inside

    def backward(self, gradient: np.ndarray) -> np.ndarray:
        return self._convolve(gradient * self.inside / self.denominator) * self.inside


# ---------------------------------------------------------------------------
# Compliance, its sensitivity, and the update.
# ---------------------------------------------------------------------------


def compliance_and_sensitivity(prepared: stress.Prepared, density: np.ndarray,
                               penalty: float, *, guess: np.ndarray | None = None,
                               solver: str = "auto"
                               ) -> tuple[float, np.ndarray, np.ndarray, dict[str, Any]]:
    """``c = f^T u``, and ``dc/drho`` element by element.

    For a self-adjoint compliance problem the sensitivity is

        ``dc/drho_e = -(d scale/d rho) * u_e^T k0 u_e``

    with ``k0`` the **condensed** element matrix -- the same one the
    assembly scatters, for the same reason the assembly may scale it. The
    minus sign is the physics: more material is never less stiff.

    Returned alongside the free-DOF solution, because the next iteration
    wants it as a warm start.
    """

    result = stress.solve_system(
        prepared, density=density, penalty=penalty, guess=guess,
        solver=solver, recover_stress=False,
    )
    free_solution = result.displacement.reshape(-1)[prepared.free]
    compliance = float(prepared.forces[prepared.free] @ free_solution)

    element_displacement = result.displacement.reshape(-1)[prepared.element_dofs]
    energy = np.einsum("ei,ij,ej->e", element_displacement,
                       prepared.element.stiffness, element_displacement)
    sensitivity = -stress.simp_scale_gradient(density, penalty) * energy
    return compliance, sensitivity, free_solution, dict(result.solver)


def optimality_criteria(design: np.ndarray, sensitivity: np.ndarray,
                        volume_gradient: np.ndarray, target_volume: float,
                        free: np.ndarray, lower: np.ndarray,
                        upper: np.ndarray) -> np.ndarray:
    """One bisection on the Lagrange multiplier of the volume constraint.

    The standard update, ``x <- x * (-dc/dx / (lambda dV/dx))**eta``, clipped
    to a move limit and to the cell's own bounds, with ``lambda`` bisected
    until the volume lands. ``keep`` and ``void`` enter as **bounds** rather
    than as a special case, which is why they cost nothing here.

    ``dV/dx`` is not a constant, because the volume being constrained is the
    filtered one. The filter is linear, so the volume it produces is exactly
    ``x . dV/dx`` and the bisection stays arithmetic.
    """

    negative = np.maximum(-sensitivity, 0.0)
    gradient = np.maximum(volume_gradient, 1e-12)
    if not np.any(negative[free] > 0.0):
        return design.copy()

    low, high = 1e-12, 1e12
    updated = np.clip(design, lower, upper)
    for _ in range(200):
        mid = 0.5 * (low + high)
        step = design * (negative / (mid * gradient)) ** _OC_DAMPING
        updated = np.clip(step, design - _MOVE_LIMIT, design + _MOVE_LIMIT)
        updated = np.clip(updated, lower, upper)
        if float(updated @ gradient) > target_volume:
            low = mid
        else:
            high = mid
        if (high - low) / (high + low) < 1.0e-9:
            break
    return updated


def penalty_at(iteration: int, iterations: int, final: float) -> float:
    """Continuation from 1 to the declared penalty over the first half.

    A run that starts at ``p = 3`` lands in whatever local minimum the
    initial uniform density happens to sit next to, and the classic symptom
    is a design that is already grey-free by iteration five and wrong. At
    ``p = 1`` the problem is convex, so the first half of the run finds the
    right *arrangement* and the second half sharpens it.
    """

    ramp = max(1, iterations // 2)
    if iteration >= ramp:
        return float(final)
    return 1.0 + (float(final) - 1.0) * iteration / ramp


# ---------------------------------------------------------------------------
# The loop.
# ---------------------------------------------------------------------------


@dataclass
class Run:
    """A finished optimisation: the field, the grid it lives on, the history."""

    grid: stress.Grid
    prepared: stress.Prepared
    density: np.ndarray            # (nx, ny, nz), the physical density
    design: np.ndarray             # (nx, ny, nz), the design variable
    history: list[dict[str, Any]]
    keep: np.ndarray               # (nx, ny, nz) bool
    void: np.ndarray               # (nx, ny, nz) bool
    pads: np.ndarray               # (nx, ny, nz) bool, the S4a interface pads
    inside: np.ndarray             # (nx, ny, nz) bool, the design domain
    warnings: list[str]
    continuation_ends: int
    wall_time_s: float


def _cell_regions(regions: Sequence[dict[str, Any]], grid: stress.Grid,
                  context: str) -> np.ndarray:
    """A keep/void mask, from S0's region vocabulary, on **cell centres**.

    Supports and loads are declared on nodes because that is where a
    boundary condition lives; keep and void are declared on cells because
    that is where a density lives. Same four region kinds either way.
    """

    centres = grid.cell_centres()
    mask = np.zeros(len(centres), dtype=bool)
    solid = np.asarray(grid.occupancy, dtype=bool).ravel()
    low = centres[solid].min(axis=0) if solid.any() else centres.min(axis=0)
    high = centres[solid].max(axis=0) if solid.any() else centres.max(axis=0)
    for index, region in enumerate(regions):
        name = region.get("name", index) if isinstance(region, dict) else index
        spec = region.get("region", region) if isinstance(region, dict) else region
        mask |= stress._region_mask(spec, centres, (low, high),
                                    f"{context} {name!r}")
    return mask.reshape(grid.shape)


def _interface_cells(regions: Sequence[dict[str, Any]], grid: stress.Grid,
                     context: str) -> np.ndarray:
    """Which **cells** a set of node-declared regions touches.

    Supports and loads are declared on nodes, because that is where a
    boundary condition lives, and ``_cell_regions`` above cannot be reused
    for them: a load declared as a zero-thickness plane at ``x = 60``
    selects nodes there and *no* cell centre at all, since the last centre
    sits half an element short of the face. So the mask is taken on nodes,
    with the same bounds ``assemble_forces`` uses, and a cell is selected
    when any of its eight corners is.
    """

    nodes = grid.node_positions()
    nx, ny, nz = grid.shape
    occupied = np.asarray(grid.occupancy, dtype=bool)
    corners = np.zeros((nx + 1, ny + 1, nz + 1), dtype=bool)
    for di in (0, 1):
        for dj in (0, 1):
            for dk in (0, 1):
                corners[di:di + nx, dj:dj + ny, dk:dk + nz] |= occupied
    active = corners.ravel(order="F")
    low = nodes[active].min(axis=0)
    high = nodes[active].max(axis=0)

    mask = np.zeros(len(nodes), dtype=bool)
    for index, region in enumerate(regions):
        name = region.get("name", index) if isinstance(region, dict) else index
        spec = region.get("region", region) if isinstance(region, dict) else region
        mask |= stress._region_mask(spec, nodes, (low, high),
                                    f"{context} {name!r}")
    mask &= active

    selected = mask.reshape((nx + 1, ny + 1, nz + 1), order="F")
    cells = np.zeros(grid.shape, dtype=bool)
    for di in (0, 1):
        for dj in (0, 1):
            for dk in (0, 1):
                cells |= selected[di:di + nx, dj:dj + ny, dk:dk + nz]
    return cells & occupied


def _dilate(mask: np.ndarray, radius_mm: float, spacing: np.ndarray) -> np.ndarray:
    """Grow a cell mask by a physical radius, not by a cell count.

    Same discipline as :func:`cone_kernel`: the declared millimetre has to
    mean the same thing at two grid resolutions, or the pad it produces is a
    function of ``element_mm`` rather than of the bolt it is there for.
    """

    from scipy.ndimage import binary_dilation

    spacing = np.asarray(spacing, dtype=float)
    half = np.maximum(np.ceil(radius_mm / spacing - 1e-9).astype(int), 0)
    axes = [np.arange(-half[axis], half[axis] + 1) * spacing[axis]
            for axis in range(3)]
    dx, dy, dz = np.meshgrid(*axes, indexing="ij")
    ball = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2) <= radius_mm + 1e-9
    return binary_dilation(mask, structure=ball)


def _impose_symmetry(field_: np.ndarray, axes: Sequence[int]) -> np.ndarray:
    """Average a field with its own mirror about each named mid-plane.

    On the **sensitivity**, once a step, rather than on the design variable:
    the optimality-criteria update is a pointwise monotone function of the
    sensitivity, so a symmetric sensitivity and a symmetric starting design
    give a symmetric step, and the design stays symmetric for the whole run
    without ever being projected. Projecting the design would fight the
    volume bisection; this does not touch it.

    The mirror is ``np.flip``, which is the mid-plane of the *grid*. For a
    ``box`` domain that is the mid-plane of the declared blank, which is
    what the plan means; for a ``solid`` domain it is the mid-plane of its
    bounding box, and :func:`optimise` refuses when the domain itself is not
    symmetric about it rather than quietly mirroring material into air.
    """

    for axis in axes:
        field_ = 0.5 * (field_ + np.flip(field_, axis=axis))
    return field_


def _impose_extrusion(field_: np.ndarray, axis: int,
                      inside: np.ndarray) -> np.ndarray:
    """Average a field along one axis, over the cells that are in the domain.

    Over the domain's own cells rather than over the whole column, because a
    column that leaves the solid half way would otherwise have its mean
    diluted by the air it passes through, and the resulting design would
    thin out exactly where the domain is thickest.
    """

    count = inside.sum(axis=axis, keepdims=True)
    total = np.where(inside, field_, 0.0).sum(axis=axis, keepdims=True)
    mean = total / np.maximum(count, 1)
    return np.where(inside, np.broadcast_to(mean, field_.shape), 0.0)


def optimise(plan: Plan, *, progress: Any = None) -> Run:
    """The whole of S2a: carve the declared domain against the declared loads."""

    started = time.monotonic()
    warnings: list[str] = []
    grid = domain_grid(plan.domain, plan.element_mm)
    if not grid.solid_count:
        raise TopologyError(
            "The design domain voxelised to no cells. Either `element_mm` is "
            "larger than the domain or the solid is not closed."
        )

    material = stress.Material.from_mapping(plan.load_case.get("material"))
    keep = _cell_regions(plan.keep, grid, "keep")
    void = _cell_regions(plan.void, grid, "void")

    # S4a. A support or a load is declared over a region of the *surface*, so
    # left to itself the optimiser builds the cheapest membrane that can
    # receive the force there -- correct, and useless as a mounting
    # interface. `interface_pad_mm` grows each interface into a solid pad and
    # holds it, which is a bug fix wearing an aesthetics hat: it is also what
    # stops S4b fitting struts to a fin.
    pads = np.zeros(grid.shape, dtype=bool)
    if plan.interface_pad_mm > 0.0:
        interfaces = _interface_cells(
            list(plan.load_case.get("supports") or [])
            + list(plan.load_case.get("loads") or []), grid, "interface")
        pads = _dilate(interfaces, plan.interface_pad_mm, grid.spacing)
        pads &= np.asarray(grid.occupancy, dtype=bool)
        clipped = int((pads & void).sum())
        if clipped:
            warnings.append(
                f"{clipped} cells of the {plan.interface_pad_mm} mm interface "
                "pad fall inside a declared `void` region and were dropped "
                "from it. `void` wins, because it is the region a person "
                "declared and the pad is the one this file grew."
            )
        pads &= ~void
        keep = keep | pads

    overlap = int((keep & void).sum())
    if overlap:
        raise TopologyError(
            f"{overlap} cells are declared both `keep` and `void`. One of the "
            "two regions is not the region it was meant to be."
        )

    inside = np.asarray(grid.occupancy, dtype=bool) & ~void
    if not inside.any():
        raise TopologyError("Every cell of the design domain is declared void.")

    for axis in plan.symmetry:
        if not np.array_equal(inside, np.flip(inside, axis=axis)):
            raise TopologyError(
                f"`symmetry` names {'xyz'[axis]}, and the design domain is "
                "not symmetric about its own mid-plane on that axis -- either "
                "the domain solid is asymmetric or a `void` region is. "
                "Mirroring the sensitivity here would push material into "
                "cells that are not in the domain, so the design would come "
                "out neither symmetric nor optimal."
            )
    for axis in plan.symmetry:
        if not np.array_equal(keep, np.flip(keep, axis=axis)):
            warnings.append(
                f"`symmetry` names {'xyz'[axis]} and the `keep` regions are "
                "not symmetric about that axis. The sensitivity is mirrored "
                "but `keep` is a promise about the shape and is held as "
                "declared, so the design will be symmetric everywhere except "
                "there."
            )

    # The solve runs on the **whole** design domain, void cells included at
    # the stiffness floor, because a SIMP iteration needs a system whose
    # connectivity does not change under it. Declared void enters as an
    # upper bound of zero, not as a hole in the mesh.
    solve_grid = stress.Grid(grid.origin, grid.spacing, grid.shape,
                             np.asarray(grid.occupancy, dtype=bool))
    prepared = stress.prepare(solve_grid, material, plan.load_case)
    warnings.extend(prepared.warnings)

    indices = prepared.element_indices
    cell = tuple(indices.T)
    keep_e = keep[cell]
    void_e = void[cell]
    inside_e = inside[cell]
    count = len(indices)

    lower = np.where(keep_e, 1.0, 0.0)
    upper = np.where(void_e | ~inside_e, 0.0, 1.0)
    free_e = ~(keep_e | void_e | ~inside_e)
    if not free_e.any():
        raise TopologyError(
            "Every cell is pinned by a `keep` or a `void` region, so there is "
            "nothing for the optimiser to decide."
        )

    filt = DensityFilter(grid.shape, plan.filter_radius_mm, grid.spacing, inside)
    volume_gradient = filt.volume_gradient
    if plan.extrude is not None:
        # The gradient is averaged along the extrusion axis as well as the
        # sensitivity, and it is what makes the *design variable* come out
        # constant through the thickness rather than merely tending that
        # way. Without it the filter's edge effect leaks back in through the
        # bisection: measured on a 40 x 16 x 20 cantilever, the largest
        # column standard deviation of the density falls from **0.105 to
        # 0.0009** when the gradient is averaged too. The first is a taper
        # you can see; the second is not.
        #
        # It costs nothing, because averaging preserves each column's sum:
        # for a design that is already constant along the axis,
        # ``x . gradient_extruded`` equals ``x . gradient`` term for term,
        # so the volume the bisection enforces is still the volume the
        # filter produces. And the design *is* constant along the axis from
        # iteration zero, because the initial one is uniform.
        #
        # The remaining 0.0009 is the **density**, and it is left alone on
        # purpose. The cone filter is not separable, so its normalised
        # response to a column-constant design still varies a little near
        # the domain's own faces. Projecting the density would remove that
        # and break the one property this file's tests rest on: ``rho = Hx/d``
        # is what makes the analytic sensitivity exactly checkable against a
        # finite difference. A 0.09% ripple is not worth an unfalsifiable
        # gradient.
        volume_gradient = _impose_extrusion(volume_gradient, plan.extrude, inside)
        for mask, label in ((keep, "keep"), (void, "void")):
            if mask.any() and not np.array_equal(
                    mask, _impose_extrusion(mask.astype(float), plan.extrude,
                                            inside) > 0.5):
                warnings.append(
                    f"`extrude` names {'xyz'[plan.extrude]} and the `{label}` "
                    "regions do not run the whole way through on that axis, "
                    "so the design cannot be constant through the thickness "
                    "where they are. Everything else will be."
                )
    gradient = volume_gradient[tuple(indices.T)]
    target = plan.volume_fraction * float(inside_e.sum())
    pinned = float(lower @ gradient)
    if pinned > target:
        raise TopologyError(
            f"The `keep` regions alone carry {pinned:.1f} cells' worth of "
            f"material and the volume fraction allows {target:.1f}. Either "
            "the fraction is too small or the keep regions are larger than "
            "the plan intends."
        )

    design = np.zeros(count, dtype=float)
    design[free_e] = np.clip(
        (target - pinned) / max(float(gradient[free_e].sum()), 1e-12), 1e-3, 1.0)
    design[keep_e] = 1.0
    design = np.clip(design, lower, upper)

    def _to_field(values: np.ndarray) -> np.ndarray:
        field_ = np.zeros(grid.shape, dtype=float)
        field_[cell] = values
        return field_

    history: list[dict[str, Any]] = []
    guess: np.ndarray | None = None
    continuation_ends = max(1, plan.iterations // 2)
    density = design.copy()

    for iteration in range(plan.iterations):
        penalty = penalty_at(iteration, plan.iterations, plan.penalty)
        density = filt.forward(_to_field(design))[cell]
        # `keep` is a promise about the *shape*, so it survives the filter.
        density[keep_e] = 1.0
        density[void_e | ~inside_e] = 0.0
        density = np.clip(density, 0.0, 1.0)

        compliance, sensitivity, guess, solver_info = compliance_and_sensitivity(
            prepared, density, penalty, guess=guess, solver=plan.solver)
        # S4a: symmetry and extrusion are imposed on the **filtered**
        # sensitivity, between the chain rule and the update. Before the
        # filter they would be smeared back out by it; after the update they
        # would fight the volume bisection.
        smeared = filt.backward(_to_field(sensitivity))
        if plan.symmetry:
            smeared = _impose_symmetry(smeared, plan.symmetry)
        if plan.extrude is not None:
            smeared = _impose_extrusion(smeared, plan.extrude, inside)
        sensitivity = smeared[cell]
        sensitivity[~free_e] = 0.0

        updated = optimality_criteria(design, sensitivity, gradient, target,
                                      free_e, lower, upper)
        change = float(np.abs(updated - design).max())
        design = updated

        # Discreteness is measured on the **design variable**, not on the
        # physical density, and the difference is not a detail. A density
        # filter of radius R smears a perfectly binary design over a band
        # of width R, so any member thinner than 2R is grey right through
        # its core no matter how well the run converged. Measured here: a
        # 150-iteration cantilever whose design variable is 3833 cells at 0,
        # 1638 at 1 and 129 anywhere else -- a discreteness of 0.017 -- has
        # a *density* discreteness of 0.32. Reading the second number as a
        # quality score says the run failed when it did not.
        #
        # ``measure_of_non_discreteness`` is the standard ``mean 4x(1-x)``:
        # 0 for a fully black-and-white design, 1 for a uniform grey.
        record = {
            "iteration": iteration,
            "penalty": penalty,
            "compliance_n_mm": compliance,
            "volume_fraction": float(density.sum() / max(inside_e.sum(), 1)),
            "max_change": change,
            "measure_of_non_discreteness": float(
                np.mean(4.0 * design[free_e] * (1.0 - design[free_e]))),
            "grey_fraction": float(
                np.mean((design[free_e] > 0.05) & (design[free_e] < 0.95))),
            "density_non_discreteness": float(
                np.mean(4.0 * density[free_e] * (1.0 - density[free_e]))),
            "solver": solver_info,
        }
        history.append(record)
        if progress is not None:
            progress(record)
        if iteration >= continuation_ends and change < _CHANGE_TOLERANCE:
            break

    density = filt.forward(_to_field(design))[cell]
    density[keep_e] = 1.0
    density[void_e | ~inside_e] = 0.0
    density = np.clip(density, 0.0, 1.0)

    if history and history[-1]["measure_of_non_discreteness"] > 0.2:
        warnings.append(
            f"The design variable finished at a non-discreteness of "
            f"{history[-1]['measure_of_non_discreteness']:.2f}, so it has not "
            "resolved into solid and void and the extracted surface is a "
            "level set through a cloud rather than a shape. Give it more "
            "iterations, or a larger penalty."
        )
    achieved = history[-1]["volume_fraction"] if history else plan.volume_fraction
    if achieved > plan.volume_fraction + 1e-4:
        warnings.append(
            f"The design finished at a volume fraction of {achieved:.4f} "
            f"against a declared {plan.volume_fraction:.4f}. That is the "
            "`keep` regions: they are a promise about the shape, so they are "
            "held at 1.0 after the filter rather than being allowed to blur, "
            "and the material that adds is above the constraint the optimiser "
            "bisected. Without `keep` the constraint holds to 1e-6."
        )
    if history and history[-1]["max_change"] > _CHANGE_TOLERANCE:
        warnings.append(
            f"The run used all {len(history)} iterations and was still moving "
            f"by {history[-1]['max_change']:.3f} when it stopped, so this is "
            "where it had got to rather than where it was going. Declare more "
            "`iterations`."
        )

    return Run(
        grid=grid,
        prepared=prepared,
        density=_to_field(density),
        design=_to_field(design),
        history=history,
        keep=keep,
        void=void,
        pads=pads,
        inside=inside,
        warnings=warnings,
        continuation_ends=continuation_ends,
        wall_time_s=time.monotonic() - started,
    )


# ---------------------------------------------------------------------------
# S2b: the density field to a surface, by marching tetrahedra.
# ---------------------------------------------------------------------------


#: The six tetrahedra a cube splits into, all sharing the main diagonal
#: 0--7. Corner ``v = i + 2j + 4k`` over the cube's own 0/1 offsets, which is
#: ``cadex_stress._NODE_SIGNS``' ordering.
#:
#: All six share one diagonal on purpose. Every cube of a structured grid is
#: then split the same way, so two cubes meeting at a face split that face
#: on the *same* diagonal -- which is what makes the surface continuous
#: across a cell boundary rather than merely nearly so.
_CUBE_CORNERS = np.array(
    [[i, j, k] for k in (0, 1) for j in (0, 1) for i in (0, 1)], dtype=float)


def _orient(tetrahedra: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    """Each tetrahedron listed so that its own volume is positive.

    :func:`_tetrahedron_cases` derives its winding from a parity argument on
    the vertex order, and a parity argument only means anything against a
    fixed handedness. Three of the six natural listings below happen to be
    left-handed, and leaving them so is not a subtle failure: it produced a
    surface that was topologically closed and had **half its triangles
    inside out**, so the closure check passed and the enclosed volume came
    out as exactly zero. Fixed here, once, rather than by hand in the table.
    """

    oriented = []
    for tet in tetrahedra:
        p = _CUBE_CORNERS[list(tet)]
        volume = float(np.linalg.det(
            np.stack([p[1] - p[0], p[2] - p[0], p[3] - p[0]])))
        oriented.append(tuple(tet) if volume > 0.0
                        else (tet[0], tet[1], tet[3], tet[2]))
    return tuple(oriented)


_TETRAHEDRA = _orient((
    (0, 1, 3, 7), (0, 1, 5, 7), (0, 2, 3, 7),
    (0, 2, 6, 7), (0, 4, 5, 7), (0, 4, 6, 7),
))


def _parity(order: Sequence[int]) -> int:
    """+1 for an even permutation of four indices, -1 for an odd one."""

    inversions = sum(1 for i in range(4) for j in range(i + 1, 4)
                     if order[i] > order[j])
    return 1 if inversions % 2 == 0 else -1


def _tetrahedron_cases() -> tuple[tuple[tuple[tuple[int, int], ...], ...], ...]:
    """Which edges each of the sixteen sign patterns cuts, wound outward.

    Sixteen cases, not two hundred and fifty-six, and **none of them
    ambiguous** -- a tetrahedron's four vertices admit no configuration
    where two different surfaces would separate them, which is precisely the
    hole in marching cubes that produces non-manifold output.

    Generated rather than typed out, because the winding is a parity
    argument and a parity argument that has been transcribed sixteen times
    by hand has been transcribed wrong at least once. A vertex above the
    level set is solid, so a triangle is wound to face away from the solid.
    """

    table = []
    for case in range(16):
        above = [v for v in range(4) if (case >> v) & 1]
        below = [v for v in range(4) if not (case >> v) & 1]
        if not above or not below:
            table.append(())
            continue
        if len(above) == 1 or len(below) == 1:
            apex = above[0] if len(above) == 1 else below[0]
            rest = below if len(above) == 1 else above
            a, b, c = rest
            if _parity((apex, a, b, c)) < 0:
                b, c = c, b
            triangle = ((apex, a), (apex, b), (apex, c))
            if len(below) == 1:
                # The lone vertex is the void one, so the solid is on the
                # far side and the surface faces the other way.
                triangle = triangle[::-1]
            table.append((triangle,))
            continue
        (v, w), (a, b) = above, below
        quad = ((v, a), (v, b), (w, b), (w, a))
        if _parity((v, w, a, b)) < 0:
            quad = quad[::-1]
        table.append((quad[0:3], (quad[0], quad[2], quad[3])))
    return tuple(table)


_CASES = _tetrahedron_cases()


def _sample_lattice(density: np.ndarray, grid: stress.Grid
                    ) -> tuple[np.ndarray, list[np.ndarray]]:
    """Cell-centre samples, padded by one layer of void.

    Sampling at cell centres rather than at nodes is what makes a fully
    solid block come out at exactly the right size: the level set of a step
    from 1 to 0 sits halfway between two centres, which is the cell face,
    which is the boundary. Padding with a void layer is what closes the
    surface at the edge of the domain instead of leaving it open there.
    """

    nx, ny, nz = grid.shape
    padded = np.zeros((nx + 2, ny + 2, nz + 2), dtype=float)
    padded[1:-1, 1:-1, 1:-1] = density
    axes = [grid.origin[axis] + (np.arange(n + 2) - 0.5) * grid.spacing[axis]
            for axis, n in enumerate((nx, ny, nz))]
    return padded, axes


def extract_surface(density: np.ndarray, grid: stress.Grid, *,
                    level: float = _ISO_LEVEL
                    ) -> tuple[np.ndarray, np.ndarray]:
    """The ``density = level`` isosurface, as welded vertices and triangles.

    Watertight by construction, and by two separate mechanisms rather than
    by a tolerance:

    * every cube is split into the same six tetrahedra, so neighbouring
      cubes cut their shared face along the same diagonal;
    * an intersection point is identified by **the grid edge it lies on**,
      so two tetrahedra sharing an edge produce the same vertex index --
      not two vertices a millionth of a millimetre apart that a welding pass
      then has to guess about.
    """

    values, axes = _sample_lattice(density, grid)
    shape = values.shape
    positions = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1)
    flat_values = values.ravel()
    flat_positions = positions.reshape(-1, 3)

    # Corner offsets of one cube, in `v = i + 2j + 4k` order.
    offsets = np.array([[i, j, k] for k in (0, 1) for j in (0, 1) for i in (0, 1)],
                       dtype=np.int64)
    counts = np.array(shape, dtype=np.int64) - 1
    base = np.stack(np.meshgrid(*[np.arange(n) for n in counts], indexing="ij"),
                    axis=-1).reshape(-1, 3)
    strides = np.array([shape[1] * shape[2], shape[2], 1], dtype=np.int64)
    corner_ids = ((base[:, None, :] + offsets[None, :, :]) * strides).sum(axis=2)

    edge_keys: list[np.ndarray] = []
    for tet in _TETRAHEDRA:
        ids = corner_ids[:, list(tet)]                    # (cubes, 4)
        f = flat_values[ids]
        case = ((f > level).astype(np.int64)
                * np.array([1, 2, 4, 8], dtype=np.int64)[None, :]).sum(axis=1)
        for pattern in range(1, 15):
            entry = _CASES[pattern]
            if not entry:
                continue
            chosen = np.nonzero(case == pattern)[0]
            if not len(chosen):
                continue
            for triangle in entry:
                corners = []
                for p, q in triangle:
                    lo = ids[chosen, p]
                    hi = ids[chosen, q]
                    corners.append(np.stack(
                        [np.minimum(lo, hi), np.maximum(lo, hi)], axis=1))
                edge_keys.append(np.stack(corners, axis=1))   # (n, 3, 2)
        del f, case

    if not edge_keys:
        return np.zeros((0, 3), dtype=float), np.zeros((0, 3), dtype=np.int64)

    keyed = np.concatenate(edge_keys, axis=0)                # (tris, 3, 2)
    pairs = keyed.reshape(-1, 2)
    unique, inverse = np.unique(pairs, axis=0, return_inverse=True)
    faces = np.asarray(inverse).ravel().reshape(-1, 3).astype(np.int64)

    lo_value = flat_values[unique[:, 0]]
    hi_value = flat_values[unique[:, 1]]
    span = hi_value - lo_value
    t = np.where(np.abs(span) > 1e-300, (level - lo_value) / np.where(
        np.abs(span) > 1e-300, span, 1.0), 0.5)
    t = np.clip(t, 0.0, 1.0)
    vertices = (flat_positions[unique[:, 0]]
                + t[:, None] * (flat_positions[unique[:, 1]]
                                - flat_positions[unique[:, 0]]))
    return vertices, faces


def domain_planes(grid: stress.Grid) -> list[tuple[int, float]]:
    """The six planes of the grid's own box, as ``(axis, coordinate)``.

    For a ``box`` domain these are the faces of the declared blank, and a
    vertex that came out exactly on one came out of a cell the run held at
    density 1 -- the level set of a step from 1 to a padded 0 lands exactly
    on the cell face, which is exactly the box face. That exactness is what
    makes :func:`taubin_smooth`'s pinning a test rather than a tolerance.
    """

    high = grid.origin + np.asarray(grid.shape, dtype=float) * grid.spacing
    return [(axis, float(value))
            for axis in range(3)
            for value in (float(grid.origin[axis]), float(high[axis]))]


def taubin_smooth(vertices: np.ndarray, faces: np.ndarray, *, passes: int = 10,
                  lam: float = 0.53, mu: float = -0.55,
                  planes: Sequence[tuple[int, float]] | None = None,
                  plane_tolerance_mm: float = 1.0e-6) -> np.ndarray:
    """Alternating lambda/mu Laplacian passes, so the shape does not shrink.

    A plain Laplacian smoother shrinks a closed surface toward its centroid
    -- run it long enough on a sphere and there is no sphere. Taubin's fix is
    to follow every positive step with a slightly larger negative one, which
    is a low-pass filter with unity gain at low frequency: the staircase goes
    and the volume stays. ``|mu| > lam`` is the condition, and it is the
    whole trick.

    ``planes`` is S4a's fourth key, and it is a defect fix. A mounting face
    is a flat plane of the blank that the run held solid; the smoother does
    not know that, so it treats the rim where that face meets the carved
    body as curvature and pulls the face in -- which rounds the one surface
    the part is bolted through. A vertex that *started* on a declared plane
    is projected back onto it after every half-pass: it still slides
    **within** the plane, so the staircase along the rim still goes, but the
    face stays a face. Only the coordinate normal to the plane is touched,
    so a vertex on two planes (an edge of the blank) is pinned by both and
    stays on the edge.
    """

    if not len(faces):
        return vertices
    import scipy.sparse as sparse

    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges = np.concatenate([edges, edges[:, ::-1]])
    count = len(vertices)
    adjacency = sparse.coo_matrix(
        (np.ones(len(edges)), (edges[:, 0], edges[:, 1])),
        shape=(count, count)).tocsr()
    # `tocsr` has already summed the duplicates; flattening the counts back
    # to one is what turns the edge list into a plain adjacency.
    adjacency.data[:] = 1.0
    degree = np.asarray(adjacency.sum(axis=1)).ravel()
    degree[degree == 0.0] = 1.0

    pinned = [(axis, value,
               np.abs(vertices[:, axis] - value) <= plane_tolerance_mm)
              for axis, value in (planes or [])]

    smoothed = np.array(vertices, dtype=float)
    for _ in range(passes):
        for weight in (lam, mu):
            neighbour_mean = (adjacency @ smoothed) / degree[:, None]
            smoothed = smoothed + weight * (neighbour_mean - smoothed)
            for axis, value, on_plane in pinned:
                smoothed[on_plane, axis] = value
    return smoothed


def surface_is_watertight(faces: np.ndarray) -> dict[str, Any]:
    """Every undirected edge in exactly two triangles, every directed one once.

    Two claims, not one. The first is closure; the second is that the
    closure is *consistently wound*, which is what makes the divergence
    theorem give a volume rather than a number.
    """

    if not len(faces):
        return {"watertight": False, "reason": "the surface has no triangles"}
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    undirected = np.sort(directed, axis=1)
    _, counts = np.unique(undirected, axis=0, return_counts=True)
    _, directed_counts = np.unique(directed, axis=0, return_counts=True)
    return {
        "watertight": bool(np.all(counts == 2) and np.all(directed_counts == 1)),
        "edges": int(len(counts)),
        "boundary_edges": int(np.sum(counts == 1)),
        "non_manifold_edges": int(np.sum(counts > 2)),
        "reversed_edges": int(np.sum(directed_counts > 1)),
    }


# ---------------------------------------------------------------------------
# The report.
# ---------------------------------------------------------------------------


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(run: Run, plan: Plan, *, stl: Path | None = None,
           smoothing_passes: int = 10) -> dict[str, Any]:
    """One run, and the shape it produced, as a JSON receipt."""

    vertices, faces = extract_surface(run.density, run.grid)
    if smoothing_passes:
        vertices = taubin_smooth(
            vertices, faces, passes=smoothing_passes,
            planes=domain_planes(run.grid) if plan.pin_domain_planes else None)
    triangles = vertices[faces] if len(faces) else np.zeros((0, 3, 3))
    closure = surface_is_watertight(faces)
    surface_volume = (stress.mesh_volume_mm3(triangles) if len(faces) else 0.0)
    density_volume = float(run.density.sum()) * run.grid.element_volume_mm3
    solid_volume = float((run.density > _ISO_LEVEL).sum()) * run.grid.element_volume_mm3

    warnings = list(run.warnings)
    if not closure["watertight"]:
        warnings.append(
            "The extracted surface is not watertight, which marching "
            "tetrahedra cannot produce and therefore means something "
            "upstream is wrong. Do not import it."
        )
    if solid_volume > 0 and abs(surface_volume - solid_volume) / solid_volume > 0.15:
        warnings.append(
            f"The extracted surface encloses {surface_volume:.1f} mm^3 against "
            f"{solid_volume:.1f} mm^3 of cells above the level set. That gap "
            "is the grid being coarse against the members the run found, not "
            "the smoothing: measured on a sphere, marching tetrahedra is "
            "4.5% low at 10 cells across and 0.16% low at 40, and Taubin "
            "smoothing moves the volume by less than a tenth of that. Halve "
            "`element_mm` if the number matters."
        )

    written = None
    if stl is not None and len(faces):
        stress.write_binary_stl(triangles, stl)
        written = {"path": str(stl), "sha256": _digest(stl)}

    last = run.history[-1] if run.history else {}
    first = run.history[0] if run.history else {}
    return {
        "schema": REPORT_SCHEMA,
        "plan": {
            "name": plan.name,
            "domain": plan.domain,
            "element_mm": plan.element_mm,
            "volume_fraction": plan.volume_fraction,
            "filter_radius_mm": plan.filter_radius_mm,
            "penalty": plan.penalty,
            "iterations": plan.iterations,
            "symmetry": ["xyz"[axis] for axis in plan.symmetry],
            "extrude": None if plan.extrude is None else "xyz"[plan.extrude],
            "interface_pad_mm": plan.interface_pad_mm,
            "pin_domain_planes": plan.pin_domain_planes,
        },
        "grid": {
            "shape": list(run.grid.shape),
            "spacing_mm": [float(value) for value in run.grid.spacing],
            "origin_mm": [float(value) for value in run.grid.origin],
            "design_cells": int(run.inside.sum()),
            "keep_cells": int(run.keep.sum()),
            "void_cells": int(run.void.sum()),
            "interface_pad_cells": int(run.pads.sum()),
            "elements": int(run.prepared.element_count),
            "free_dofs": int(len(run.prepared.free)),
        },
        "result": {
            "iterations_run": len(run.history),
            "continuation_ends_at": run.continuation_ends,
            "initial_compliance_n_mm": first.get("compliance_n_mm"),
            "final_compliance_n_mm": last.get("compliance_n_mm"),
            "final_volume_fraction": last.get("volume_fraction"),
            "measure_of_non_discreteness": last.get("measure_of_non_discreteness"),
            "grey_fraction": last.get("grey_fraction"),
            "density_non_discreteness": last.get("density_non_discreteness"),
            "max_change": last.get("max_change"),
            "converged": bool(
                last.get("max_change", 1.0) < _CHANGE_TOLERANCE
                and len(run.history) > run.continuation_ends),
            "density_volume_mm3": density_volume,
            "solid_volume_mm3": solid_volume,
            "mass_g": density_volume * float(
                run.prepared.material.density_kg_m3) * 1.0e-6,
            "wall_time_s": run.wall_time_s,
        },
        "surface": {
            "vertices": int(len(vertices)),
            "triangles": int(len(faces)),
            "volume_mm3": surface_volume,
            "smoothing_passes": smoothing_passes,
            **closure,
            "stl": written,
        },
        "history": run.history,
        "warnings": sorted(set(warnings)),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "cadex_importable": stress._cadex_importable(),
    }


# ---------------------------------------------------------------------------
# The self-check: the 3-D cantilever every SIMP implementation is checked on.
# ---------------------------------------------------------------------------


def cantilever_plan(*, size_mm: Sequence[float] = (60.0, 20.0, 30.0),
                    element_mm: float = 2.5, volume_fraction: float = 0.3,
                    force_n: float = 100.0) -> dict[str, Any]:
    """A 3-D cantilever: held at ``x = 0``, pulled down at the far bottom edge.

    The benchmark, in the same shape as ``cadex_stress.cantilever_case`` and
    for the same reason -- a benchmark whose geometry is written twice is a
    benchmark that can disagree with itself.
    """

    return {
        "schema": PLAN_SCHEMA,
        "name": "cantilever",
        "domain": {"box": {"size_mm": list(size_mm), "origin_mm": [0.0, 0.0, 0.0]}},
        "element_mm": element_mm,
        "volume_fraction": volume_fraction,
        "filter_radius_mm": 2.0 * element_mm,
        "penalty": 3.0,
        "iterations": 40,
        "material": {
            "name": "self-check",
            "youngs_modulus_mpa": 3500.0,
            "poissons_ratio": 0.36,
            "yield_strength_mpa": 50.0,
            "density_kg_m3": 1240.0,
        },
        "supports": [
            {"name": "root",
             "region": {"face": {"axis": "x", "at": "min", "depth_mm": 1e-6}}},
        ],
        "loads": [
            {"name": "tip",
             "region": {"box": {
                 "min_mm": [size_mm[0] - 1e-6, None, -1e-6],
                 "max_mm": [None, None, 1e-6]}},
             "force_n": [0.0, 0.0, -force_n]},
        ],
    }


def run_self_check(**overrides: Any) -> dict[str, Any]:
    """The cantilever, carved, and the number that says it worked.

    The comparison that matters is against a **uniform** design of the same
    volume: SIMP's whole claim is that where the material goes matters more
    than how much of it there is, and the ratio is how much more.
    """

    import tempfile

    plan = Plan.from_mapping(cantilever_plan(**overrides))
    run = optimise(plan)
    with tempfile.TemporaryDirectory() as directory:
        finished = report(run, plan, stl=Path(directory) / "design.stl")

    uniform = np.where(run.inside, plan.volume_fraction, 0.0)
    cell = tuple(run.prepared.element_indices.T)
    baseline, _, _, _ = compliance_and_sensitivity(
        run.prepared, uniform[cell], plan.penalty)
    optimised = finished["result"]["final_compliance_n_mm"]
    return {
        "schema": "cadex-analysis-topology-self-check-v1",
        "uniform_compliance_n_mm": baseline,
        "optimised_compliance_n_mm": optimised,
        "improvement_factor": (baseline / optimised) if optimised else None,
        "volume_fraction": finished["result"]["final_volume_fraction"],
        "measure_of_non_discreteness": finished["result"][
            "measure_of_non_discreteness"],
        "density_non_discreteness": finished["result"]["density_non_discreteness"],
        "iterations_run": finished["result"]["iterations_run"],
        "wall_time_s": finished["result"]["wall_time_s"],
        "surface": {key: finished["surface"][key]
                    for key in ("triangles", "watertight", "volume_mm3")},
        "cadex_importable": stress._cadex_importable(),
    }


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="topology.py",
        description="Carve a declared blank against a declared load case.")
    parser.add_argument("plan", nargs="?", type=Path,
                        help=f"a {PLAN_SCHEMA} JSON file")
    parser.add_argument("--out", type=Path, default=None,
                        help="a directory for the STL, the density field and "
                             "the report")
    parser.add_argument("--smoothing-passes", type=int, default=10,
                        help="Taubin passes over the extracted surface")
    parser.add_argument("--self-check", action="store_true",
                        help="run the 3-D cantilever benchmark")
    options = parser.parse_args(list(argv[1:]))

    try:
        if options.self_check:
            finished = run_self_check()
        else:
            if options.plan is None:
                parser.error("a plan is required")
            raw = json.loads(options.plan.read_text(encoding="utf-8"))
            plan = Plan.from_mapping(raw, base=options.plan.resolve().parent)

            def _progress(record: dict[str, Any]) -> None:
                print(
                    f"iteration {record['iteration']:3d}  p={record['penalty']:.2f}"
                    f"  c={record['compliance_n_mm']:.6g}"
                    f"  vol={record['volume_fraction']:.3f}"
                    f"  change={record['max_change']:.4f}",
                    file=sys.stderr,
                )

            run = optimise(plan, progress=_progress)
            stl = None
            if options.out:
                options.out.mkdir(parents=True, exist_ok=True)
                stl = options.out / f"{plan.name}.stl"
            finished = report(run, plan, stl=stl,
                              smoothing_passes=options.smoothing_passes)
            if options.out:
                np.save(options.out / f"{plan.name}-density.npy", run.density)
                (options.out / "report.json").write_text(
                    json.dumps(finished, indent=2, sort_keys=True),
                    encoding="utf-8")
    except (TopologyError, stress.StressError) as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2

    for warning in finished.get("warnings", []):
        print(f"warning: {warning}", file=sys.stderr)
    print(json.dumps(finished, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
