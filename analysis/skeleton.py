#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A SIMP density field in, a **parametric script** out (S4).

**This program is not part of the engine and is never installed into the
payload.** Same contract as ``topology.py`` and ``cadex_stress.py`` beside
it and ``training/cadex_train.py`` above it: CMake never installs it, no
payload carries it, nothing in it enters ``pixi.toml``, and nothing in it
may import a GPL package. ADR-147 records the slice; ``docs/STRUCTURAL.md``
§8 is the arc.

**Why this exists.** Every generative-design tool on the market ends in a
mesh you cannot edit -- nTop, Fusion, Altair. Move the hole 2 mm and you
re-run the optimisation. Cadex is the one product whose native artifact is a
parametric script, so it can end somewhere else: the optimiser finds the
*topology*, and the deliverable is a feature tree a human and an agent can
both edit. ``docs/VISION.md`` principle 3 already demands it -- *the
optimiser never authors geometry the script does not own* -- and until S4
that was honoured only in spirit, by handing over an STL and hoping the
agent redrew it.

**What it fits, and what it refuses to fit.** Straight struts and spheres,
and nothing else. Curved spines are ``part.sweep(scale_law=)``'s job and
they are what makes a part read as organic rather than as CAD. A SIMP field
often wants a flat web, and rather than grow a plate fitter this file
**measures** the fraction of solid cells its struts cover and refuses below
:data:`MINIMUM_COVERAGE`, naming the number and where the misses are. A
model that reports its own inapplicability beats one that quietly produces a
weak tidy part.

**No 3-D thinning.** Thinning a blobby SIMP field gives spurious branches
and noisy junctions, and it is 250 hand-written lines. What is here instead
is a Euclidean distance transform -- whose value *is* the local member
radius, the number the whole fit turns on -- with its maxima as nodes and a
Delaunay triangulation for candidate bars. Both are in the pinned scipy
1.17.0, so ``analysis/requirements.txt`` stays at **three pins**, as ADR-143
kept it.

**The verdict is one number** and it is the point of the slice::

    compliance ratio = the rebuilt parametric part's compliance
                       / the SIMP optimum's, at equal or lower mass

Ship at :data:`COMPLIANCE_BAR`. Above it the fit was wrong, and this file
says so rather than handing over a tidy part that is 40% weaker.

Usage::

    python analysis/topology.py plan.json --out ./carve
    python analysis/skeleton.py plan.json --run ./carve \\
        --project ./bracket --out ./fit
    python analysis/skeleton.py --self-check

The rebuild is driven through ``./cadex script --set`` **as a subprocess**,
never by importing ``cli/`` -- ADR-142's precedent and for its reason: this
tree keeps no view on the protocol, and gets crash isolation per rebuild.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from typing import Any, Sequence

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cadex_stress as stress  # noqa: E402
import topology as topo  # noqa: E402

REPORT_SCHEMA = "cadex-analysis-skeleton-v1"

#: The fraction of the SIMP solid a fitted strut graph must cover before it
#: is worth calling a fit. Below this the field wanted a plate or a shell,
#: and struts are the wrong model for it -- see the module docstring.
MINIMUM_COVERAGE = 0.85

#: How much stiffer than the SIMP optimum the rebuilt part may be, at equal
#: or lower mass. 1.15 is 15%. It is adjustable and it should **not** be
#: adjusted after seeing a result.
COMPLIANCE_BAR = 1.15

#: The density level set the fit reads the solid off. The same one
#: ``topology.extract_surface`` extracts at, so the shape being fitted is
#: the shape that was exported.
_ISO_LEVEL = topo._ISO_LEVEL

#: How far apart two medial-axis nodes must be, as a multiple of the deeper
#: one's own radius. 2.0 is **a diameter**: consecutive spheres along a
#: member just touch, and the strut between them fills the gap rather than
#: being buried inside them.
#:
#: It is also the number that makes the output buildable, which is a
#: constraint spike zero put on this file from outside. Measured on a
#: two-footed bracket and on the plate-like cantilever, as
#: (solids, coverage):
#:
#:     ====  ================  ==================
#:     a     bracket           cantilever
#:     ====  ================  ==================
#:     1.0   556, 0.99         577, 0.84
#:     1.4   200, 0.95         294, 0.80
#:     2.0    74, 0.93         134, 0.76
#:     ====  ================  ==================
#:
#: Below 2.0 the coverage barely moves and the solid count explodes past
#: what ``part.fuse`` will blend in a sane time. At 2.0 the strut-like field
#: clears :data:`MINIMUM_COVERAGE` and the plate-like one does not, which is
#: the discrimination the gate is for.
_SUPPRESSION = 2.0

#: A bar is rejected if the density anywhere along it falls below this. The
#: level set again: a bar that leaves the solid is not a member.
_BAR_FLOOR = _ISO_LEVEL


class SkeletonError(RuntimeError):
    """A refusal with a sentence a person can act on."""


# ---------------------------------------------------------------------------
# The field, and the distance that is the radius.
# ---------------------------------------------------------------------------


#: How far below the grid the distance transform is refined. Every step
#: halves the half-cell bias below; 2 is where the measurement stopped
#: paying (see :func:`local_radius_mm`) and 8x the cells is already the
#: memory cost.
_REFINE = 2

#: Above this many refined cells the refinement is dropped and the bias is
#: taken instead. 30 million doubles is a quarter of a gigabyte, which is
#: more than a radius estimate is worth.
_REFINE_CELL_LIMIT = 30_000_000


def local_radius_mm(density: np.ndarray, spacing: np.ndarray, *,
                    refine: int = _REFINE) -> np.ndarray:
    """Distance from every solid cell to the **material boundary**, in mm.

    Three things separate this from a bare
    ``scipy.ndimage.distance_transform_edt`` of ``density >= 0.5``, and all
    three matter because this number is used directly as a member radius:

    * the field is padded with one layer of void, so a cell against the edge
      of the domain is a cell against air rather than one whose distance
      runs off the end of the array;
    * a fraction of a cell is subtracted, because the transform measures to
      the nearest void *cell centre* and the surface is the level set,
      which is nearer;
    * and the whole thing is done on a **refined** grid, trilinearly
      interpolating the *density* rather than thresholding it first,
      because the binary field throws away the information that says where
      between two cell centres the surface actually is.

    That last one is not a nicety. Measured on a synthetic 8 mm-radius
    cylinder on a 1 mm grid, whose deepest cell centre is a true 7.293 mm
    from the surface: the binary transform reads 7.616 and the refined one
    7.224.

    **How much to subtract is a measurement, not a derivation**, because
    the bias runs the other way for a curved boundary than for a flat one.
    Three canonical cases at ``refine = 2``, as raw transform minus truth:
    a convex cylinder **-0.069** cells, a slab between two parallel planes
    **+0.25**, a flat domain face **+0.125**. A quarter of a *fine* cell --
    an eighth of a coarse one -- is what minimises the worst of those,
    leaving every case inside **0.194 cells**. Without the refinement the
    same argument lands on half a coarse cell, and the cylinder comes out
    0.32 cells thin; that is the fallback, and it is deliberately the
    conservative direction, because a strut that is slightly thin stays
    inside the blank.
    """

    from scipy.ndimage import distance_transform_edt, map_coordinates

    spacing = np.asarray(spacing, dtype=float)
    shape = tuple(int(n) for n in density.shape)
    step = max(1, int(refine))
    if int(np.prod(shape)) * step ** 3 > _REFINE_CELL_LIMIT:
        step = 1

    if step > 1:
        axes = [(np.arange(n * step) + 0.5) / step - 0.5 for n in shape]
        coords = np.stack(np.meshgrid(*axes, indexing="ij"))
        # `nearest` and not a zero fill: the outer half of the outermost
        # cell is inside the domain, and filling it with void would erode
        # every flat mounting face by half a cell -- which is the one place
        # the pads have to stay exactly on the plane.
        field_ = map_coordinates(density, coords, order=1, mode="nearest")
        fine_spacing = spacing / step
    else:
        field_ = density
        fine_spacing = spacing

    solid = field_ >= _ISO_LEVEL
    padded = np.zeros(tuple(n + 2 for n in solid.shape), dtype=bool)
    padded[1:-1, 1:-1, 1:-1] = solid
    distance = distance_transform_edt(padded, sampling=fine_spacing)
    distance = (distance[1:-1, 1:-1, 1:-1]
                - (0.25 if step > 1 else 0.5) * float(fine_spacing.mean()))
    distance = np.where(solid, np.maximum(distance, 0.0), 0.0)

    if step > 1:
        centres = np.stack(np.meshgrid(
            *[(np.arange(n) + 0.5) * step - 0.5 for n in shape], indexing="ij"))
        distance = map_coordinates(distance, centres, order=1, mode="nearest")
    return np.where(density >= _ISO_LEVEL, distance, 0.0)


def _cell_of(points: np.ndarray, grid: stress.Grid) -> np.ndarray:
    """Which cell each point falls in, clipped to the grid."""

    index = np.floor((np.atleast_2d(points) - grid.origin[None, :])
                     / grid.spacing[None, :]).astype(int)
    return np.clip(index, 0, np.asarray(grid.shape) - 1)


def _sample(field_: np.ndarray, points: np.ndarray, grid: stress.Grid) -> np.ndarray:
    index = _cell_of(points, grid)
    return field_[index[:, 0], index[:, 1], index[:, 2]]


# ---------------------------------------------------------------------------
# Anchors: the places the part must physically reach.
# ---------------------------------------------------------------------------


@dataclass
class Anchor:
    """One support, load or keep region, and the node that serves it."""

    kind: str                       # "support" | "load" | "keep"
    name: str
    entry: dict[str, Any]           # the declaration it came from
    cells: np.ndarray               # (nx, ny, nz) bool, region ∩ solid
    node: int = -1
    pad_low: tuple[float, float, float] | None = None
    pad_high: tuple[float, float, float] | None = None
    plane: tuple[int, int] | None = None    # (axis, -1 for min / +1 for max)


def _region_cells(plan: topo.Plan, grid: stress.Grid,
                  solid: np.ndarray) -> list[Anchor]:
    """Every declared region that the part has to touch, as cell masks.

    Supports and loads go through ``topology._interface_cells`` because they
    are declared on **nodes**; ``keep`` goes through ``_cell_regions``
    because it is declared on cells. Getting that the wrong way round is
    silent: a load declared as a zero-thickness plane at ``x = 60`` selects
    no cell centre at all, because the last one sits half an element short
    of the face.

    Then the interfaces are **dilated by the plan's own**
    ``interface_pad_mm``, so the region a node is placed in is the pad the
    carve held solid rather than the one cell layer the declaration names.
    Measured on the cantilever without it: the support anchor landed on the
    outermost cell centre, where the distance transform reads one cell, and
    every bar into it was pruned for being thinner than a member -- so the
    fit refused for a disconnected mount that was in fact perfectly
    connected. The dilation is the same call ``topology.optimise`` makes,
    which is what makes the two agree by construction.
    """

    anchors: list[Anchor] = []
    for kind, entries in (("support", plan.load_case.get("supports") or []),
                          ("load", plan.load_case.get("loads") or [])):
        for index, entry in enumerate(entries):
            name = str(entry.get("name", index))
            cells = topo._interface_cells([entry], grid, kind)
            if plan.interface_pad_mm > 0.0:
                cells = topo._dilate(cells, plan.interface_pad_mm, grid.spacing)
            anchors.append(Anchor(kind=kind, name=name, entry=dict(entry),
                                  cells=cells & solid))
    for index, entry in enumerate(plan.keep):
        name = str(entry.get("name", index)) if isinstance(entry, dict) else str(index)
        cells = topo._cell_regions([entry], grid, "keep") & solid
        anchors.append(Anchor(kind="keep", name=name,
                              entry=dict(entry) if isinstance(entry, dict) else {},
                              cells=cells))
    return anchors


def _anchor_point(anchor: Anchor, grid: stress.Grid, radius: np.ndarray
                  ) -> tuple[np.ndarray, float]:
    """Where in a region the node goes: deep first, and central among equals.

    Not the plain centroid, and the difference is not cosmetic. A pad is a
    ball or a slab **intersected with the carved solid**, so its centroid is
    routinely pulled onto its own rim -- measured on the cantilever's tip
    load, the centroid landed one cell from the surface, where the distance
    transform reads a single cell, and every bar into it was then pruned for
    being thinner than a member. The anchor came out "disconnected" from a
    structure it was sitting in the middle of.

    So: take the cells within 20% of the region's own deepest, and among
    those the one nearest the centroid. The node goes where the pad has
    material to hold it, and among equally thick places, in the middle.
    """

    indices = np.argwhere(anchor.cells)
    centres = grid.origin[None, :] + (indices + 0.5) * grid.spacing[None, :]
    depth = radius[indices[:, 0], indices[:, 1], indices[:, 2]]
    deep = depth >= 0.8 * float(depth.max())
    centroid = centres.mean(axis=0)
    gaps = np.linalg.norm(centres - centroid[None, :], axis=1)
    gaps[~deep] = np.inf
    nearest = int(np.argmin(gaps))
    return centres[nearest], float(depth[nearest])


# ---------------------------------------------------------------------------
# Interior nodes: the maxima of the distance transform, packed.
# ---------------------------------------------------------------------------


def _interior_candidates(radius: np.ndarray, grid: stress.Grid,
                         floor_mm: float) -> tuple[np.ndarray, np.ndarray]:
    """Every solid cell deep enough to hold a member, deepest first.

    **Not** the local maxima of the distance transform, and that is a
    correction rather than a preference. A member is a *ridge* of the
    distance field, and a cell on a ridge is not a strict local maximum:
    the value along the ridge is flat, so a 3x3x3 maximum filter keeps only
    the handful of peaks where it is not. Measured on a two-footed bracket
    whose members run 8 to 14 mm thick, the filter proposed **25** cells out
    of 3500 solid ones, the packing kept 11, and the fitted struts covered
    0.45 of the part -- a fit starved of nodes, reported as a field that did
    not want struts.

    Handing the whole solid to :func:`_pack` instead is the classic maximal-
    ball medial axis, and it costs a sort.
    """

    indices = np.argwhere(radius >= floor_mm)
    if not len(indices):
        return np.zeros((0, 3)), np.zeros(0)
    points = grid.origin[None, :] + (indices + 0.5) * grid.spacing[None, :]
    values = radius[indices[:, 0], indices[:, 1], indices[:, 2]]
    order = np.argsort(-values)
    return points[order], values[order]


def _pack(seeds: np.ndarray, seed_radii: np.ndarray, candidates: np.ndarray,
          candidate_radii: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Greedily add candidates that are not already inside an accepted ball.

    ``_SUPPRESSION`` times the *accepted* node's radius, which -- because
    the candidates arrive deepest first -- is the larger of the two. So the
    suppression distance follows the local thickness rather than being one
    number for the whole part: a 12 mm-thick root gets sparse nodes and a
    3 mm web gets close ones, which is what keeps the strut count sane at a
    fine grid.

    The seeds are the anchors, and they go in first whatever their depth,
    because they are the places the part has to reach rather than places the
    fit discovered.
    """

    points = [np.asarray(row, dtype=float) for row in seeds]
    radii = [float(value) for value in seed_radii]
    if not len(candidates):
        return np.asarray(points, dtype=float).reshape(-1, 3), np.asarray(radii)

    alive = np.ones(len(candidates), dtype=bool)
    for point, value in zip(points, radii):
        alive &= (np.linalg.norm(candidates - point[None, :], axis=1)
                  > _SUPPRESSION * value)
    for index in range(len(candidates)):
        if not alive[index]:
            continue
        point = candidates[index]
        value = float(candidate_radii[index])
        points.append(point)
        radii.append(value)
        alive &= (np.linalg.norm(candidates - point[None, :], axis=1)
                  > _SUPPRESSION * value)
    return np.asarray(points, dtype=float), np.asarray(radii, dtype=float)


# ---------------------------------------------------------------------------
# Bars: Delaunay, pruned to what stays in the solid.
# ---------------------------------------------------------------------------


def _delaunay_edges(points: np.ndarray) -> np.ndarray:
    """Every edge of the Delaunay tetrahedralisation, deduplicated.

    Delaunay rather than a k-nearest graph because it needs no arbitrary
    *k*: it is the triangulation that maximises the smallest angle, so its
    edges are the neighbour pairs the point set itself proposes. A field
    that came out of ``extrude`` is nearly coplanar and Qhull refuses it,
    which is what the joggle retry is for.
    """

    from scipy.spatial import Delaunay

    if len(points) < 4:
        return np.array([[i, j] for i in range(len(points))
                         for j in range(i + 1, len(points))], dtype=int
                        ).reshape(-1, 2)
    try:
        mesh = Delaunay(points)
    except Exception:                                       # noqa: BLE001
        try:
            mesh = Delaunay(points, qhull_options="QJ")
        except Exception as error:                          # noqa: BLE001
            raise SkeletonError(
                f"Qhull could not triangulate {len(points)} fitted nodes, "
                f"even joggled: {error}. That is a degenerate node set -- "
                "every node on one line or one plane -- and it means the "
                "field is not a three-dimensional structure."
            ) from error
    simplices = np.asarray(mesh.simplices)
    pairs = np.concatenate([simplices[:, [a, b]]
                           for a in range(4) for b in range(a + 1, 4)])
    return np.unique(np.sort(pairs, axis=1), axis=0)


def _fit_bar(start: np.ndarray, end: np.ndarray, density: np.ndarray,
             radius: np.ndarray, grid: stress.Grid) -> tuple[float, float] | None:
    """The largest frustum from ``start`` to ``end`` that stays in the solid.

    ``None`` when the segment leaves the solid at all, which is the prune
    the whole candidate set turns on: Delaunay proposes edges across
    concavities and through holes, and those are the ones that would weld a
    bracket shut.

    The frustum is fitted rather than sized by the bar's thinnest point,
    because a member that tapers from a thick root to a thin tip is what the
    field actually contains and a uniform cylinder at the thin radius throws
    away the root. No end needs capping at its node's radius: the profile is
    sampled *including* the endpoints, so each end is already bounded by the
    distance transform there, which is exactly the node's own radius.
    """

    span = end - start
    length = float(np.linalg.norm(span))
    if length <= 0.0:
        return None
    steps = max(3, int(np.ceil(length / (0.5 * float(grid.spacing.min())))) + 1)
    t = np.linspace(0.0, 1.0, steps)
    points = start[None, :] + t[:, None] * span[None, :]
    if float(_sample(density, points, grid).min()) < _BAR_FLOOR:
        return None

    profile = _sample(radius, points, grid)
    head = float(profile[t <= 0.5].min())
    tail = float(profile[t >= 0.5].min())
    if head <= 0.0 or tail <= 0.0:
        return None
    line = head + t * (tail - head)
    scale = float(np.min(profile / np.maximum(line, 1e-12)))
    if scale < 1.0:
        head *= scale
        tail *= scale
    return head, tail


class _Union:
    """Union-find, for the two places connectivity is decided."""

    def __init__(self, count: int) -> None:
        self.parent = list(range(count))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> bool:
        a, b = self.find(left), self.find(right)
        if a == b:
            return False
        self.parent[b] = a
        return True


def _bars(points: np.ndarray, density: np.ndarray, radius: np.ndarray,
          grid: stress.Grid, floor: float
          ) -> tuple[list[tuple[int, int]], list[tuple[float, float]], list[float]]:
    """Every Delaunay edge that stays in the solid, floored -- then reconnected.

    The floor is the point of the whole function and so is the exception to
    it. A bar thinner than one cell is below what the grid resolves, so
    keeping it as a *size* would be inventing a number; dropping it as a
    *connection* invents something worse. Measured on the cantilever: the
    field is one connected component of 2916 cells, and the strong bars
    alone split the fit into 73 + 9 + 9 + 3 + ... nodes, orphaning the tip
    load. The graph was disagreeing with the field about a fact the field
    already knew.

    So the strong bars are taken first, and the thin ones are then added by
    Kruskal on ``min(r0, r1)`` -- largest first -- until nothing more joins
    two components. That is a maximum spanning forest over exactly the edges
    that were going to be thrown away, and it costs one sort. What comes
    back is a graph as connected as the valid-bar graph is, with a list of
    which bars had to be promoted so the caller can say so.
    """

    strong: list[tuple[int, int]] = []
    strong_radii: list[tuple[float, float]] = []
    weak: list[tuple[float, int, int, tuple[float, float]]] = []
    for a, b in _delaunay_edges(points):
        fitted = _fit_bar(points[a], points[b], density, radius, grid)
        if fitted is None:
            continue
        if min(fitted) >= floor:
            strong.append((int(a), int(b)))
            strong_radii.append(fitted)
        else:
            weak.append((min(fitted), int(a), int(b), fitted))

    union = _Union(len(points))
    for a, b in strong:
        union.union(a, b)
    promoted: list[float] = []
    for thinness, a, b, fitted in sorted(weak, key=lambda item: -item[0]):
        if union.union(a, b):
            strong.append((a, b))
            strong_radii.append(fitted)
            promoted.append(thinness)
    return strong, strong_radii, promoted


# ---------------------------------------------------------------------------
# Coverage: the number that says whether struts were the right model.
# ---------------------------------------------------------------------------


def _covered(points: np.ndarray, nodes: np.ndarray, bar_ends: np.ndarray,
             bar_radii: np.ndarray, *, slack: float = 0.0,
             pads: Sequence[tuple[np.ndarray, np.ndarray]] = ()) -> np.ndarray:
    """Which points fall inside some emitted sphere, frustum or pad.

    ``slack`` is half a cell, and it is not a fudge. The field knows its own
    occupancy only to within one cell, and a fitted node sits at a cell
    *centre* rather than on the true medial axis -- up to half a diagonal
    off it. Asking a cell centre to be strictly inside a fitted primitive is
    asking the fit for sub-cell accuracy the field it is fitted to does not
    have.

    The pads count because they are emitted: they are the interface rather
    than the structure, but they are still material the script places, and a
    coverage number that ignored them would report a hole where the script
    puts a mounting boss.
    """

    inside = np.zeros(len(points), dtype=bool)
    for x, y, z, r in nodes:
        gap = np.linalg.norm(points - np.array([x, y, z])[None, :], axis=1)
        inside |= gap <= r + slack
    for (a, b), (r0, r1) in zip(bar_ends, bar_radii):
        start = nodes[int(a), :3]
        span = nodes[int(b), :3] - start
        length2 = float(span @ span)
        if length2 <= 0.0:
            continue
        t = np.clip(((points - start[None, :]) @ span) / length2, 0.0, 1.0)
        gap = np.linalg.norm(points - (start[None, :] + t[:, None] * span[None, :]),
                             axis=1)
        inside |= gap <= r0 + t * (r1 - r0) + slack
    for low, high in pads:
        inside |= np.all((points >= np.asarray(low)[None, :] - slack)
                         & (points <= np.asarray(high)[None, :] + slack), axis=1)
    return inside


def _largest_miss(uncovered: np.ndarray, grid: stress.Grid) -> dict[str, Any]:
    """The biggest connected lump of solid the fit did not reach."""

    from scipy.ndimage import label

    if not uncovered.any():
        return {}
    tagged, count = label(uncovered)
    sizes = np.bincount(tagged.ravel())
    sizes[0] = 0
    biggest = int(np.argmax(sizes))
    indices = np.argwhere(tagged == biggest)
    centres = grid.origin[None, :] + (indices + 0.5) * grid.spacing[None, :]
    return {
        "regions": int(count),
        "cells": int(sizes[biggest]),
        "volume_mm3": float(sizes[biggest]) * grid.element_volume_mm3,
        "centroid_mm": [float(value) for value in centres.mean(axis=0)],
        "min_mm": [float(value) for value in centres.min(axis=0)],
        "max_mm": [float(value) for value in centres.max(axis=0)],
    }


# ---------------------------------------------------------------------------
# The fit.
# ---------------------------------------------------------------------------


@dataclass
class Fit:
    """A strut graph fitted to one density field."""

    grid: stress.Grid
    density: np.ndarray
    solid: np.ndarray
    radius: np.ndarray
    nodes: np.ndarray              # (N, 4) x, y, z, radius
    bar_ends: np.ndarray           # (M, 2) int
    bar_radii: np.ndarray          # (M, 2) float
    #: How fat each member may become before it leaves the **blank** -- not
    #: the carved solid. The sizing loop is allowed to grow a strut into
    #: space the optimiser emptied, because that is a design decision the
    #: script owns; it is not allowed to grow one outside the domain the
    #: plan declared, because then the part no longer fits where it was
    #: measured to fit, and (measured, on the S4 bracket) a strut that grew
    #: from 6.3 to 11.3 mm swallowed the boss pad's whole top face and the
    #: emitted `part.stress` selector stopped resolving.
    node_headroom: np.ndarray      # (N,)
    bar_headroom: np.ndarray       # (M,)
    anchors: list[Anchor]
    coverage: dict[str, Any]
    warnings: list[str] = field(default_factory=list)

    def analytic_volume_mm3(self) -> float:
        """Members and joints, as loose frusta and loose balls.

        Overlap and all: the joints double-count the members they join, and
        that is fine, because this number is only ever compared **against
        itself** across one sizing step. What it has to do is respond to a
        radius change the way the real part does, and both terms are here
        because the two respond differently -- a member's volume goes as
        ``r^2`` and a joint's as ``r^3``. Leaving the joints out made the
        redistribution look mass-neutral when it was not: the joints follow
        the fattest member entering them, so a redistribution that thickens
        a few members and thins many adds joint volume superlinearly, and
        the loop walked a 40.6 g target up to 43.7 g while the controller
        pulled the other way.

        The mass in the report is measured off the rebuilt STL. This is
        never it.
        """

        total = float(np.sum(4.0 / 3.0 * np.pi * self.nodes[:, 3] ** 3))
        for (a, b), (r0, r1) in zip(self.bar_ends, self.bar_radii):
            length = float(np.linalg.norm(self.nodes[int(b), :3]
                                          - self.nodes[int(a), :3]))
            total += np.pi * length / 3.0 * (r0 * r0 + r0 * r1 + r1 * r1)
        return float(total)


def fit(density: np.ndarray, grid: stress.Grid, plan: topo.Plan, *,
        min_radius_mm: float | None = None) -> Fit:
    """Fit a strut graph to a SIMP density field, or refuse and say why."""

    warnings: list[str] = []
    solid = density >= _ISO_LEVEL
    if not solid.any():
        raise SkeletonError(
            "No cell of the field reaches the 0.5 level set, so there is no "
            "shape to fit. That is a topology run that did not converge, not "
            "a fit that failed."
        )
    radius = local_radius_mm(density, grid.spacing)
    floor = (float(min_radius_mm) if min_radius_mm is not None
             else float(grid.spacing.mean()))

    anchors = _region_cells(plan, grid, solid)
    empty = [f"{anchor.kind} {anchor.name!r}" for anchor in anchors
             if not anchor.cells.any()]
    if empty:
        raise SkeletonError(
            f"{', '.join(empty)} selects no solid cell of the carved field, "
            "so the part does not reach where it is held or loaded. Declare "
            "`interface_pad_mm` on the topology plan: without it the "
            "optimiser is free to build the cheapest membrane that can "
            "receive the force, and a membrane at the 0.5 level set can miss "
            "the interface entirely."
        )

    seeds = []
    seed_radii = []
    for anchor in anchors:
        point, value = _anchor_point(anchor, grid, radius)
        anchor.node = len(seeds)
        seeds.append(point)
        seed_radii.append(max(value, floor))
    seeds = np.asarray(seeds, dtype=float).reshape(-1, 3)
    seed_radii = np.asarray(seed_radii, dtype=float)

    candidates, candidate_radii = _interior_candidates(radius, grid, floor)
    points, radii = _pack(seeds, seed_radii, candidates, candidate_radii)
    if len(points) < 2:
        raise SkeletonError(
            f"The fit found {len(points)} node(s). A structure needs at least "
            "two places to connect, so either the field is a single blob or "
            "`min_radius_mm` is larger than the part."
        )
    nodes = np.concatenate([points, radii[:, None]], axis=1)

    ends, bar_radii, promoted = _bars(points, density, radius, grid, floor)
    if not ends:
        raise SkeletonError(
            f"None of the {len(points)} fitted nodes could be joined by a bar "
            "that stays inside the solid. Delaunay proposes every neighbour "
            "pair, so this means the field is disconnected at the level set."
        )
    if promoted:
        warnings.append(
            f"{len(promoted)} bar(s) thinner than one cell "
            f"({min(promoted):.2f} mm at the thinnest, against a cell of "
            f"{floor:.2f} mm) were kept because nothing else joined the "
            "structure there. The grid cannot resolve a member that thin, so "
            "what those bars claim is the **topology** and not the size: the "
            "script's `min_radius_mm` builds them at one cell and the sizing "
            "loop takes them from there. Carve at a finer `element_mm` if the "
            "shape matters."
        )

    ends_array = np.asarray(ends, dtype=int)
    radii_array = np.asarray(bar_radii, dtype=float)
    ends_array, radii_array, nodes, anchors, dropped = _largest_component(
        ends_array, radii_array, nodes, anchors)
    if dropped:
        warnings.append(
            f"{dropped} fitted node(s) were not connected to the main "
            "structure and were dropped. That is normal -- the distance "
            "transform finds maxima in every isolated speck the level set "
            "leaves behind."
        )

    _pads(anchors, grid)
    blank = local_radius_mm(np.asarray(grid.occupancy, dtype=float),
                            grid.spacing)
    fitted = Fit(
        grid=grid, density=density, solid=solid, radius=radius, nodes=nodes,
        bar_ends=ends_array, bar_radii=radii_array,
        node_headroom=np.maximum(_sample(blank, nodes[:, :3], grid), floor),
        # Two ceilings, and the tighter one wins. The blank's own headroom
        # is what keeps the part inside the domain; three times the fitted
        # radius is what keeps it recognisable as the fit. Without the
        # second one the sizing loop chasing a mass target grew a 2 mm
        # member to 10 mm, and at that point the emitted script is no
        # longer a description of the field it came from.
        bar_headroom=np.minimum(
            np.array([_headroom(nodes[int(a), :3], nodes[int(b), :3], blank,
                                grid, floor) for a, b in ends_array]),
            3.0 * radii_array.max(axis=1)),
        anchors=anchors, coverage={}, warnings=warnings)
    # Before the coverage is measured, not after: the joints the script
    # emits are the ones `_lift_nodes` sizes, and a coverage number taken
    # off the packed radii would describe a part nobody builds.
    _lift_nodes(fitted, floor_mm=floor)

    centres = grid.cell_centres().reshape(grid.shape + (3,))
    solid_points = centres[solid]
    covered = _covered(
        solid_points, fitted.nodes, ends_array, radii_array,
        slack=0.5 * float(grid.spacing.mean()),
        pads=[(np.asarray(anchor.pad_low), np.asarray(anchor.pad_high))
              for anchor in anchors if anchor.pad_low is not None])
    fraction = float(covered.mean())
    uncovered = np.zeros(grid.shape, dtype=bool)
    uncovered[solid] = ~covered
    fitted.coverage = coverage = {
        "fraction": fraction,
        "solid_cells": int(solid.sum()),
        "covered_cells": int(covered.sum()),
        "minimum": MINIMUM_COVERAGE,
        "largest_miss": _largest_miss(uncovered, grid),
    }
    if fraction < MINIMUM_COVERAGE:
        miss = coverage["largest_miss"]
        where = (f" The largest single miss is {miss['cells']} cells "
                 f"({miss['volume_mm3']:.0f} mm^3) centred at "
                 f"[{miss['centroid_mm'][0]:.1f}, {miss['centroid_mm'][1]:.1f}, "
                 f"{miss['centroid_mm'][2]:.1f}] mm." if miss else "")
        raise SkeletonError(
            f"The fitted struts cover {fraction:.2f} of the carved solid and "
            f"the bar is {MINIMUM_COVERAGE:.2f}.{where} A field this far from "
            "a strut graph wanted a plate or a shell, and struts are the "
            "wrong model for it -- fitting them anyway would hand you a tidy "
            "part that is much weaker than the one that was carved. Try "
            "`extrude` plus a plate by hand, or a finer `element_mm` if the "
            "members came out only a cell or two across."
        )
    return fitted


def _headroom(start: np.ndarray, end: np.ndarray, blank: np.ndarray,
              grid: stress.Grid, floor: float) -> float:
    """The thinnest the **blank** gets along one bar."""

    span = end - start
    steps = max(3, int(np.ceil(float(np.linalg.norm(span))
                               / (0.5 * float(grid.spacing.min())))) + 1)
    t = np.linspace(0.0, 1.0, steps)
    profile = _sample(blank, start[None, :] + t[:, None] * span[None, :], grid)
    return float(max(profile.min(), floor))


def _largest_component(ends: np.ndarray, radii: np.ndarray, nodes: np.ndarray,
                       anchors: list[Anchor]
                       ) -> tuple[np.ndarray, np.ndarray, np.ndarray,
                                  list[Anchor], int]:
    """Keep the biggest connected piece, and refuse if it lost an anchor.

    **A disconnected mount is a part that falls apart**, and it is the
    failure that would matter most and be entirely silent: the script still
    builds, the render still looks like a bracket, and the bolt hole is on a
    lump of metal touching nothing.
    """

    count = len(nodes)
    union = _Union(count)
    for a, b in ends:
        union.union(int(a), int(b))
    labels = np.array([union.find(index) for index in range(count)])
    sizes = {label: int((labels == label).sum()) for label in set(labels.tolist())}
    biggest = max(sizes, key=lambda label: sizes[label])
    keep = labels == biggest

    orphaned = [f"{anchor.kind} {anchor.name!r}" for anchor in anchors
                if not keep[anchor.node]]
    if orphaned:
        raise SkeletonError(
            f"{', '.join(orphaned)} is not connected to the rest of the "
            "fitted structure. A support or a load that the load path does "
            "not reach is a part that falls apart, so this refuses rather "
            "than emitting it. The usual cause is a member only one cell "
            "across between two lobes: carve at a finer `element_mm`, or "
            "raise `volume_fraction`."
        )

    remap = -np.ones(count, dtype=int)
    remap[keep] = np.arange(int(keep.sum()))
    survives = keep[ends[:, 0]] & keep[ends[:, 1]]
    for anchor in anchors:
        anchor.node = int(remap[anchor.node])
    return (remap[ends[survives]], radii[survives], nodes[keep], anchors,
            int((~keep).sum()))


# ---------------------------------------------------------------------------
# S4c: the script.
# ---------------------------------------------------------------------------


_PREAMBLE = '''\
# Generated by analysis/skeleton.py from the topology plan {name!r} (S4,
# ADR-147). This is a **script**, not an export: every number below is
# editable, `cadex params` sweeps the three declared parameters, and
# `part.stress` re-checks the load case on every rebuild.
#
# NODES came from the maxima of the distance transform of the SIMP field;
# STRUTS from a Delaunay triangulation of them, pruned to the bars that stay
# inside the solid and then sized by a fully-stressed-design loop. The
# radii are a plain table rather than parameters on purpose: `num()` is
# numeric-only and {bars} parameters is not a search space. The three
# parameters are what `analysis/search.py` sweeps afterwards.

p = params(
    strut_scale=num(1.0, min=0.6, max=1.6, step=0.02, label="Strut scale"),
    min_radius_mm=num({min_radius:.2f}, unit="mm", min=0.2, max=12.0, step=0.1,
                      label="Minimum radius"),
    blend_mm=num({blend:.2f}, unit="mm", min=0.0, max=12.0, step=0.25,
                 label="Seam blend"),
)

# x, y, z, radius -- one sphere each, in millimetres.
NODES = [
{nodes}]

# from, to, radius at `from`, radius at `to`.
STRUTS = [
{struts}]

# The mounting pads: (length, width, height), origin. These are the
# interface, not the structure, and they are what the load case below is
# anchored to.
PADS = [
{pads}]


def _radius(value):
    return max(value * p.strut_scale, p.min_radius_mm)


def _strut(a, b, r0, r1):
    """One frustum from node `a` to node `b`, along their own axis."""

    span = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]
    length = (span[0] ** 2 + span[1] ** 2 + span[2] ** 2) ** 0.5
    start, end = _radius(r0), _radius(r1)
    if abs(start - end) < 1.0e-6:
        # OCC has no cone of equal radii: that surface is a cylinder.
        return part.cylinder(start, length, origin=[a[0], a[1], a[2]],
                             direction=span)
    return part.cone(start, end, length, origin=[a[0], a[1], a[2]],
                     direction=span)


solids = [part.sphere(_radius(r), center=[x, y, z]) for (x, y, z, r) in NODES]
solids += [_strut(NODES[a], NODES[b], r0, r1) for (a, b, r0, r1) in STRUTS]
solids += [part.box(size[0], size[1], size[2], origin=list(origin))
           for (size, origin) in PADS]

{output} = part.fuse(
    solids,
    # Measured in spike zero and then again on this fit (ADR-146). On a
    # lattice **no** blend radius survives `refuse`: even 0.4 mm left one
    # seam of 127 that OCC would not round. `reduce` clears a hand-written
    # lattice at every size tried, up to 64 solids in under 20 s -- but it
    # looks for one radius that blends *every* seam, and on a fitted lattice
    # with near-tangent members there is none, so it refused the whole part
    # down to 0.0555 mm. `skip` blends the seams that can be blended and
    # leaves the rest sharp, which is the right trade for a hundred seams
    # of which two are impossible.
    blend=(p.blend_mm if p.blend_mm > 0.0 else None),
    blend_on_failure="skip",
    # `refine` unifies same-domain faces after the boolean. On a lattice of
    # a hundred tangent primitives it is the step that fails -- "the boolean
    # succeeded and refining its result produced an invalid shape" -- and
    # what it buys is a tidier face list, which nothing downstream reads.
    refine=False,
)
'''

_STRESS = '''
check = part.stress(
    {output},
    hold={hold},
    load=[
{loads}    ],
    youngs_modulus_mpa={youngs:g}, poissons_ratio={poisson:g},
    yield_strength_mpa={yield_strength:g}, density_kg_m3={density:g},
    element_mm={element:g},
)

result = {{{output!r}: {output}, "check": check}}
'''

_NO_STRESS = '''
result = {{{output!r}: {output}}}
'''


def _identifier(name: str) -> str:
    cleaned = "".join(character if character.isalnum() else "_"
                      for character in str(name).lower()).strip("_")
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"part_{cleaned}" if cleaned else "part_"
    return cleaned


def _pads(anchors: Sequence[Anchor], grid: stress.Grid) -> None:
    """Give every anchor the box of the blank it mounts through.

    A fitted lattice has no flat face anywhere, and a mounting interface
    that is a sphere is not a mounting interface. The pad is the bounding
    box of the region's own cells, snapped **out** to whichever plane of the
    blank it touches, so its outer face is exactly that plane: flat, one
    face, with a normal a selector can name.
    """

    low = grid.origin
    high = grid.origin + np.asarray(grid.shape, dtype=float) * grid.spacing
    for anchor in anchors:
        indices = np.argwhere(anchor.cells)
        centres = grid.origin[None, :] + (indices + 0.5) * grid.spacing[None, :]
        pad_low = centres.min(axis=0) - 0.5 * grid.spacing
        pad_high = centres.max(axis=0) + 0.5 * grid.spacing
        touching = []
        for axis in range(3):
            if pad_low[axis] <= low[axis] + 0.25 * grid.spacing[axis]:
                touching.append((axis, -1, float(pad_high[axis] - pad_low[axis])))
            if pad_high[axis] >= high[axis] - 0.25 * grid.spacing[axis]:
                touching.append((axis, +1, float(pad_high[axis] - pad_low[axis])))
        if touching:
            # The shallowest touched axis is the one the pad is a slab on,
            # which is the face it mounts through.
            axis, sign, _ = min(touching, key=lambda item: item[2])
            anchor.plane = (axis, sign)
            if sign < 0:
                pad_low[axis] = low[axis]
            else:
                pad_high[axis] = high[axis]
        anchor.pad_low = tuple(float(value) for value in pad_low)
        anchor.pad_high = tuple(float(value) for value in pad_high)


def _selector(anchor: Anchor, others: Sequence[Anchor]) -> dict[str, Any]:
    """The ADR-029 selector naming this pad's outer face.

    Four keys, and each one is there because the three others were not
    enough. ``geometry_type`` and ``normal`` pick every plane facing that
    way, which on a fused lattice includes **the flat end cap of every
    strut** -- ``part.cone`` and ``part.cylinder`` both have two.
    ``near_point`` narrows that to the neighbourhood of the pad, and it is
    what separates two pads on the same plane. ``min_area`` is what
    separates the pad from the end caps that survived the boolean near it:
    a pad face is hundreds of square millimetres and a strut cap is tens.

    Measured, and this is why the area is here: on the S4 bracket a
    ``near_point`` of 18.7 mm around the boss caught more than one face and
    the engine refused the whole script for cardinality. The reach is now
    half the pad's *smallest* in-plane extent -- enough for the face's
    centre of mass to shift when the boolean trims its edges, and no more --
    still capped at 45% of the gap to the nearest other pad.
    """

    axis, sign = anchor.plane
    low = np.asarray(anchor.pad_low)
    high = np.asarray(anchor.pad_high)
    centre = 0.5 * (low + high)
    centre[axis] = high[axis] if sign > 0 else low[axis]

    plane_span = np.delete(high - low, axis)
    reach = 0.5 * float(plane_span.min())
    for other in others:
        if other is anchor or other.plane is None:
            continue
        gap = np.linalg.norm(centre - 0.5 * (np.asarray(other.pad_low)
                                             + np.asarray(other.pad_high)))
        reach = min(reach, 0.45 * float(gap))
    normal = [0.0, 0.0, 0.0]
    normal[axis] = float(sign)
    return {
        "geometry_type": "Plane",
        "normal": normal,
        "near_point": [round(float(value), 4) for value in centre],
        "max_distance": round(max(reach, 1e-3), 4),
        "min_area": round(0.4 * float(plane_span.prod()), 4),
        "expected_count": 1,
    }


def _size_floor(grid: stress.Grid) -> float:
    """The thinnest member anything downstream is allowed to build.

    Nine tenths of a cell, because that is the thinnest the carve could
    have resolved. One number, used by the sizing loop *and* emitted as the
    script's ``min_radius_mm`` default, so the loop measures the part the
    script builds rather than one a millimetre away from it.
    """

    return round(max(0.3, 0.9 * float(grid.spacing.mean())), 2)


def default_blend_mm(fit_: Fit) -> float:
    """A seam radius sized to the members, not to the part.

    Forty per cent of the median member radius. Larger reads as a blob and
    is what OCC refuses first; smaller is invisible at the scale a bracket
    is looked at.
    """

    if not len(fit_.bar_radii):
        return 0.0
    return round(max(0.2, 0.4 * float(np.median(fit_.bar_radii))), 2)


def emit_script(fit_: Fit, plan: topo.Plan, *, output: str | None = None,
                blend_mm: float | None = None,
                stress_element_mm: float | None = None) -> str:
    """The whole deliverable of S4: a parametric script, as text."""

    # The pads were placed in `fit`, where the coverage had to see them.
    name = _identifier(output or plan.name or "part")
    #: One cell, because that is the thinnest member the carve could have
    #: resolved -- and therefore the honest floor for the bars ``_bars``
    #: promoted to keep the structure in one piece.
    blend = (float(blend_mm) if blend_mm is not None
             else default_blend_mm(fit_))

    nodes = "".join(
        f"    ({x:.3f}, {y:.3f}, {z:.3f}, {r:.3f}),\n"
        for x, y, z, r in fit_.nodes)
    struts = "".join(
        f"    ({int(a)}, {int(b)}, {r0:.3f}, {r1:.3f}),\n"
        for (a, b), (r0, r1) in zip(fit_.bar_ends, fit_.bar_radii))
    pads = "".join(
        "    (({0:.3f}, {1:.3f}, {2:.3f}), ({3:.3f}, {4:.3f}, {5:.3f})),\n".format(
            *(np.asarray(anchor.pad_high) - np.asarray(anchor.pad_low)),
            *np.asarray(anchor.pad_low))
        for anchor in fit_.anchors)

    text = _PREAMBLE.format(
        name=plan.name, bars=len(fit_.bar_ends) + len(fit_.nodes),
        min_radius=_size_floor(fit_.grid), blend=blend,
        nodes=nodes, struts=struts, pads=pads, output=name)

    supports = [anchor for anchor in fit_.anchors if anchor.kind == "support"]
    loads = [anchor for anchor in fit_.anchors if anchor.kind == "load"]
    unplaced = [f"{anchor.kind} {anchor.name!r}"
                for anchor in supports + loads if anchor.plane is None]
    if unplaced or not supports or not loads:
        if unplaced:
            fit_.warnings.append(
                f"{', '.join(unplaced)} does not reach a face of the declared "
                "blank, so this script carries no `part.stress` check: a "
                "selector can name a plane of the blank and nothing else. The "
                "script is still valid and still sweepable, and "
                "`analysis/cadex_stress.py` still measures it from outside."
            )
        return text + _NO_STRESS.format(output=name)

    material = stress.Material.from_mapping(plan.load_case.get("material"))
    holds = [_selector(anchor, fit_.anchors) for anchor in supports]
    load_lines = "".join(
        "        {{\"at\": {selector},\n"
        "         \"force_n\": {force}}},\n".format(
            selector=json.dumps(_selector(anchor, fit_.anchors)),
            force=json.dumps([float(value) for value in
                              (anchor.entry.get("force_n") or [0.0, 0.0, 0.0])]))
        for anchor in loads)
    return text + _STRESS.format(
        output=name,
        hold=json.dumps(holds[0] if len(holds) == 1 else holds),
        loads=load_lines,
        youngs=material.youngs_modulus_mpa, poisson=material.poissons_ratio,
        yield_strength=material.yield_strength_mpa,
        density=material.density_kg_m3,
        element=float(stress_element_mm if stress_element_mm is not None
                      else max(2.0 * plan.element_mm, 1.5)),
    )


# ---------------------------------------------------------------------------
# Driving `./cadex`. A subprocess, on ADR-142's precedent.
# ---------------------------------------------------------------------------


def cadex_command(override: str | None = None) -> list[str]:
    if override:
        return [override]
    shim = Path(__file__).resolve().parents[1] / "cadex"
    if shim.is_file():
        return [str(shim)]
    found = shutil.which("cadex")
    if found:
        return [found]
    raise SkeletonError(
        "No `cadex` shim found. Pass `--cadex /path/to/cadex`, or run this "
        "from a checkout that has one at the repository root."
    )


def install(source: str, *, project: Path, out: Path,
            cadex: Sequence[str], engine: str | None = None,
            timeout_s: float = 1800.0) -> dict[str, Any]:
    """``cadex script --set`` -- an existing, test-pinned, token-free command.

    A subprocess and not an import of ``cli/``: this tree keeps no view on
    the protocol (ADR-142), and a rebuild that segfaults OCC takes the
    subprocess with it rather than this loop.
    """

    project = Path(project)
    out = Path(out)
    project.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    script_path = out / "script.py"
    script_path.write_text(source, encoding="utf-8")

    command = list(cadex) + [
        "script", "--set", str(script_path), "--replace",
        "--project", str(project), "--out", str(out),
        "--format", "stl", "--json",
    ]
    if engine:
        command += ["--engine", engine]
    result = subprocess.run(command, capture_output=True, text=True,
                            check=False, timeout=timeout_s)
    if not result.stdout.strip():
        raise SkeletonError(
            f"`cadex script --set` exited {result.returncode} and printed no "
            f"envelope: {result.stderr.strip()[-800:]}"
        )
    envelope = json.loads(result.stdout)
    if result.returncode != 0:
        raise SkeletonError(
            f"The engine refused the emitted script (exit "
            f"{result.returncode}): {envelope.get('error') or result.stderr.strip()[-800:]}"
        )
    return envelope


def _exported_stl(envelope: dict[str, Any], out: Path) -> Path:
    for item in envelope.get("outputs") or []:
        path = (item.get("files") or {}).get("stl")
        if path:
            return Path(path)
    found = sorted(Path(out).rglob("*.stl"))
    if found:
        return found[0]
    raise SkeletonError(
        "The rebuild published no STL, so there is nothing to measure. Ask "
        "for `--format stl`."
    )


# ---------------------------------------------------------------------------
# S4d: size it against the real hex FEA, on the real rebuilt CAD.
# ---------------------------------------------------------------------------


def _measure(solid: Path, plan: topo.Plan) -> stress.Result:
    """S0, on the part the engine actually built.

    No second physics model, and no surrogate: the number that sizes the
    part is the number CalculiX already cross-checked (ADR-141). A fit that
    will not build therefore fails on iteration one rather than at the end.
    """

    triangles, _ = stress.read_solid(solid)
    if stress.mesh_volume_mm3(triangles) <= 0.0:
        raise SkeletonError(
            f"{solid.name} tessellates to a non-positive volume, so the "
            "rebuild produced something that is inside out or not closed."
        )
    grid = stress.voxelise(triangles, plan.element_mm)
    material = stress.Material.from_mapping(plan.load_case.get("material"))
    return stress.solve(grid, material, plan.load_case)


def _compliance(result: stress.Result, plan: topo.Plan) -> float:
    """``c = f^T u`` on the solve that was just run.

    Re-assembled rather than carried out of ``solve``, because ``Result``
    holds the displacement and the load case and that is all a compliance
    is. The same quantity ``topology.compliance_and_sensitivity`` returns,
    so the ratio compares like with like.
    """

    prepared = stress.prepare(result.grid, result.material, plan.load_case)
    free = prepared.free
    return float(prepared.forces[free] @ result.displacement.reshape(-1)[free])


def _assign(result: stress.Result, fit_: Fit) -> list[np.ndarray]:
    """Every solid element to its nearest fitted member.

    Nearest by distance to the member's own axis, so an element inside a
    joint goes to whichever strut runs through it. Node radii are not sized
    directly: a node takes the largest radius of the struts that enter it,
    which is what keeps a joint at least as thick as the members it joins.
    """

    centres = result.element_centres()
    best = np.full(len(centres), np.inf)
    owner = np.zeros(len(centres), dtype=int)
    for index, ((a, b), _) in enumerate(zip(fit_.bar_ends, fit_.bar_radii)):
        start = fit_.nodes[int(a), :3]
        span = fit_.nodes[int(b), :3] - start
        length2 = float(span @ span)
        if length2 <= 0.0:
            continue
        t = np.clip(((centres - start[None, :]) @ span) / length2, 0.0, 1.0)
        gap = np.linalg.norm(
            centres - (start[None, :] + t[:, None] * span[None, :]), axis=1)
        closer = gap < best
        best[closer] = gap[closer]
        owner[closer] = index
    return [np.nonzero(owner == index)[0] for index in range(len(fit_.bar_ends))]


def _resize(fit_: Fit, result: stress.Result, *, floor_mm: float) -> np.ndarray:
    """One fully-stressed-design step: ``r *= (sigma / sigma_target)**0.5``.

    The exponent is the physics rather than a tuning constant -- a member's
    stress goes as one over its area, and its area goes as the square of its
    radius -- and the clip is what stops one singular element at a held face
    doubling a strut in a single step. ``sigma`` is the **p95** of the
    elements assigned to the member, for the reason ADR-141 gives for the
    safety factor: a peak on a stair-stepped grid is a singularity and grows
    with every refinement for ever.
    """

    owned = _assign(result, fit_)
    sigma = np.zeros(len(fit_.bar_ends))
    weight = np.zeros(len(fit_.bar_ends))
    for index, members in enumerate(owned):
        if not len(members):
            continue
        sigma[index] = stress._percentile(result.von_mises_mpa[members], 0.95)
        weight[index] = float(len(members))
    seen = weight > 0
    if not seen.any():
        raise SkeletonError(
            "No element of the rebuilt part could be assigned to a fitted "
            "member, which means the script built something the fit does not "
            "describe."
        )
    target = float(np.average(sigma[seen], weights=weight[seen]))
    if target <= 0.0:
        raise SkeletonError(
            "Every element of the rebuilt part reports zero stress, so the "
            "load case reaches none of it."
        )

    radii = fit_.bar_radii.copy()
    factor = np.ones(len(radii))
    factor[seen] = np.clip(np.sqrt(sigma[seen] / target), 0.8, 1.25)
    radii *= factor[:, None]
    return _bounded(fit_, radii, floor_mm)


def _bounded(fit_: Fit, radii: np.ndarray, floor_mm: float) -> np.ndarray:
    """Bar radii, held between one cell and the blank's own headroom."""

    return np.clip(radii, floor_mm,
                   np.maximum(fit_.bar_headroom, floor_mm)[:, None])


def _scale_members(fit_: Fit, factor: float, floor_mm: float,
                   base: np.ndarray) -> None:
    """Every member at ``factor`` times ``base``, joints brought along."""

    fit_.bar_radii = _bounded(fit_, base * factor, floor_mm)
    _lift_nodes(fit_, floor_mm=floor_mm)


def _scale_to_volume(fit_: Fit, target_mm3: float, *, floor_mm: float) -> float:
    """Find the one factor on every radius that hits an analytic volume.

    By bisection rather than by a formula, because there is no formula: a
    member's volume goes as ``r^2``, a joint's as ``r^3``, both are clipped
    at a floor and at the blank's headroom, and the joints are sized *from*
    the members. Forty bisection steps on an expression that costs a
    microsecond is the cheapest correct answer, and it is exact where
    ``sqrt(mass ratio)`` was only nearly right.
    """

    base = fit_.bar_radii.copy()
    low, high = 0.2, 5.0
    for _ in range(40):
        mid = 0.5 * (low + high)
        _scale_members(fit_, mid, floor_mm, base)
        if fit_.analytic_volume_mm3() < target_mm3:
            low = mid
        else:
            high = mid
    _scale_members(fit_, 0.5 * (low + high), floor_mm, base)
    return 0.5 * (low + high)


def _lift_nodes(fit_: Fit, *, floor_mm: float) -> None:
    """A joint is exactly as thick as the thickest member entering it.

    **Exactly**, not "at least" -- and that one word was a bug that made the
    whole sizing loop diverge. Written as ``max(current, incident)`` a node
    radius can only ever grow, so every pass ratcheted the joints up toward
    the blank's headroom whatever the mass correction asked for, and a
    40.6 g target settled at 45.2 g with the controller pulling the other
    way the whole time. A joint has no size of its own; it has the size of
    the members it joins.

    Capped by the blank's own headroom, which is the guarantee that keeps
    the part inside the domain it was carved from -- so the mounting pads'
    outer faces stay single planar faces and the selectors in the emitted
    ``part.stress`` keep resolving.
    """

    radii = np.full(len(fit_.nodes), floor_mm)
    for (a, b), (r0, r1) in zip(fit_.bar_ends, fit_.bar_radii):
        radii[int(a)] = max(radii[int(a)], r0)
        radii[int(b)] = max(radii[int(b)], r1)
    fit_.nodes[:, 3] = np.clip(radii, floor_mm,
                               np.maximum(fit_.node_headroom, floor_mm))


@dataclass
class Sized:
    """The sizing loop's own record."""

    history: list[dict[str, Any]]
    script: str
    envelope: dict[str, Any]
    stl: Path
    result: stress.Result
    compliance_n_mm: float
    mass_g: float
    #: The member sizes this record was measured at, so a later step can put
    #: the fit back exactly where it was when the geometry last built.
    bar_radii: np.ndarray
    nodes: np.ndarray


def size(fit_: Fit, plan: topo.Plan, *, project: Path, out: Path,
         cadex: Sequence[str], target_mass_g: float, passes: int = 5,
         engine: str | None = None, output: str | None = None,
         stress_element_mm: float | None = None,
         announce: Any = None) -> Sized:
    """Emit, rebuild, measure, resize -- a few times, on the real CAD.

    Decision 1 of the slice: no surrogate and no second physics model. Each
    pass writes the script, installs it through ``cadex script --set``,
    exports the STL, and runs S0 on *that*. It buys the property that
    matters: a fit that will not build fails on pass one.

    **The sizing passes do not blend, and the shipped part does.** A seam
    radius is a surface treatment: it moves the compliance by far less than
    the grid does, and it costs more wall time than the whole solve.
    Blending only the geometry that is finally kept makes the loop several
    times faster *and* means the number in the report is the number for the
    part that ships. If the kernel then refuses to blend that lattice at all
    -- which it does, and ``blend=None`` is the only thing that builds when
    it happens -- the unblended part stands and the refusal is reported.

    A pass that will not build ends the loop rather than the run. The last
    geometry that *did* build is a real answer, and throwing it away to
    report a refusal helps nobody; pass zero is the exception, because a fit
    that cannot be built at all has nothing behind it to fall back to.
    """

    floor = _size_floor(fit_.grid)
    history: list[dict[str, Any]] = []
    best: Sized | None = None
    passes = max(1, passes)

    for index in range(passes):
        try:
            best = _build_and_measure(
                fit_, plan, blend_mm=0.0, label=f"pass-{index}", index=index,
                project=project, out=out, cadex=cadex, engine=engine,
                output=output, stress_element_mm=stress_element_mm,
                target_mass_g=target_mass_g, history=history)
        except SkeletonError as error:
            if best is None:
                raise
            fit_.warnings.append(
                f"Sizing stopped at pass {index}, which the engine refused: "
                f"\"{str(error).split(': ', 2)[-1].strip()}\". Everything "
                f"reported is pass {index - 1}, which built. A late pass that "
                "will not build is the sizing loop having pushed the geometry "
                "somewhere OCC cannot follow -- the members it grew are in "
                "`history.mean_radius_mm`."
            )
            break
        if announce is not None:
            announce(history[-1])
        if index == passes - 1:
            break
        # Two corrections, in this order, and separating them is what makes
        # the loop converge. `_resize` decides *where* the material goes and
        # is not volume-neutral on its own -- measured, it walked a 40.6 g
        # target up to 43.7 g over four passes with the mass correction
        # pulling the other way the whole time. So the redistribution is
        # renormalised back to its own analytic volume, which makes it
        # purely a redistribution; and only then does the *measured* mass of
        # the last rebuild say how much material there should be in total.
        # One correction answers "which member", the other "how much
        # altogether", and mixing them meant neither converged.
        #
        # The second one is measured rather than computed because only the
        # rebuild knows what the joint overlaps, the pads and the blend
        # actually cost: the analytic volume is a shape the controller
        # steers by, and the STL is the truth it steers toward.
        before = fit_.analytic_volume_mm3()
        fit_.bar_radii = _resize(fit_, best.result, floor_mm=floor)
        _lift_nodes(fit_, floor_mm=floor)
        _scale_to_volume(fit_, before, floor_mm=floor)
        _scale_to_volume(fit_, before * target_mass_g / max(best.mass_g, 1e-9),
                         floor_mm=floor)

    if best is None:                                        # pragma: no cover
        raise SkeletonError("The sizing loop produced no build at all.")

    # The part that ships gets its seams rounded, on exactly the geometry
    # that was last measured -- which is why `Sized` carries the radii.
    fit_.bar_radii = best.bar_radii.copy()
    fit_.nodes = best.nodes.copy()
    radius = default_blend_mm(fit_)
    if radius > 0.0:
        try:
            best = _build_and_measure(
                fit_, plan, blend_mm=radius, label="blended",
                index=len(history), project=project, out=out, cadex=cadex,
                engine=engine, output=output,
                stress_element_mm=stress_element_mm,
                target_mass_g=target_mass_g, history=history)
            if announce is not None:
                announce(history[-1])
        except SkeletonError as error:
            fit_.warnings.append(
                f"OCC would not blend this lattice at {radius:.2f} mm -- "
                f"\"{str(error).split(': ', 2)[-1].strip()}\" -- so the part "
                "ships with `blend_mm = 0`. The parameter is still declared "
                "and still sweepable: whether a given lattice blends is a "
                "property of the lattice that only the kernel knows, so it "
                "is a knob to try rather than a promise this file can make."
            )
    return best


def _build_and_measure(fit_: Fit, plan: topo.Plan, *, blend_mm: float,
                       label: str, index: int, project: Path, out: Path,
                       cadex: Sequence[str], engine: str | None,
                       output: str | None, stress_element_mm: float | None,
                       target_mass_g: float,
                       history: list[dict[str, Any]]) -> Sized:
    """One geometry: emitted, installed, exported, solved and recorded."""

    started = time.monotonic()
    script = emit_script(fit_, plan, output=output, blend_mm=blend_mm,
                         stress_element_mm=stress_element_mm)
    envelope = install(script, project=project, out=out / label, cadex=cadex,
                       engine=engine)
    stl = _exported_stl(envelope, out / label)
    result = _measure(stl, plan)
    compliance = _compliance(result, plan)
    mass = result.mass_g()
    history.append({
        "pass": index,
        "label": label,
        "nodes": int(len(fit_.nodes)),
        "struts": int(len(fit_.bar_ends)),
        "mass_g": mass,
        "target_mass_g": target_mass_g,
        "compliance_n_mm": compliance,
        "p99_von_mises_mpa": stress._percentile(result.von_mises_mpa, 0.99),
        "max_displacement_mm": result.max_displacement_mm,
        "mean_radius_mm": float(fit_.bar_radii.mean()),
        "blend_mm": blend_mm,
        "seconds": round(time.monotonic() - started, 2),
    })
    return Sized(history=history, script=script, envelope=envelope, stl=stl,
                 result=result, compliance_n_mm=compliance, mass_g=mass,
                 bar_radii=fit_.bar_radii.copy(), nodes=fit_.nodes.copy())


# ---------------------------------------------------------------------------
# The report.
# ---------------------------------------------------------------------------


def report(fit_: Fit, plan: topo.Plan, sized: Sized | None, *,
           simp: dict[str, Any], wall_time_s: float) -> dict[str, Any]:
    """One fit, and the one number that says whether it was worth doing."""

    reference = float(simp.get("compliance_n_mm") or 0.0)
    reference_mass = float(simp.get("mass_g") or 0.0)
    ratio = None
    verdict = "not-measured"
    warnings = list(fit_.warnings)
    if sized is not None and reference > 0.0:
        ratio = sized.compliance_n_mm / reference
        heavier = reference_mass > 0.0 and sized.mass_g > reference_mass * 1.02
        if heavier:
            verdict = "over-mass"
            warnings.append(
                f"The rebuilt part is {sized.mass_g:.1f} g against the SIMP "
                f"optimum's {reference_mass:.1f} g. The compliance ratio of "
                f"{ratio:.2f} is therefore not a like-for-like comparison and "
                "the sizing loop did not reach the mass it was given -- read "
                "the history's `mass_g` column."
            )
        elif ratio <= COMPLIANCE_BAR:
            verdict = "ship"
        else:
            verdict = "refit"
            warnings.append(
                f"The rebuilt parametric part is {ratio:.2f} times as "
                f"compliant as the SIMP optimum at the same mass, and the bar "
                f"is {COMPLIANCE_BAR:.2f}. The fit lost something the field "
                "had: check `coverage.largest_miss`, and carve at a finer "
                "`element_mm` before believing the shape."
            )

    return {
        "schema": REPORT_SCHEMA,
        "plan": {"name": plan.name, "element_mm": plan.element_mm,
                 "volume_fraction": plan.volume_fraction,
                 "symmetry": ["xyz"[axis] for axis in plan.symmetry],
                 "interface_pad_mm": plan.interface_pad_mm},
        "fit": {
            "nodes": int(len(fit_.nodes)),
            "struts": int(len(fit_.bar_ends)),
            "anchors": [{"kind": anchor.kind, "name": anchor.name,
                         "node": anchor.node,
                         "on_blank_face": anchor.plane is not None}
                        for anchor in fit_.anchors],
            "min_radius_mm": float(fit_.bar_radii.min()) if len(fit_.bar_radii) else None,
            "max_radius_mm": float(fit_.nodes[:, 3].max()),
            "coverage": fit_.coverage,
        },
        "simp": {"compliance_n_mm": reference or None,
                 "mass_g": reference_mass or None},
        "rebuild": None if sized is None else {
            "compliance_n_mm": sized.compliance_n_mm,
            "mass_g": sized.mass_g,
            "p99_von_mises_mpa": stress._percentile(
                sized.result.von_mises_mpa, 0.99),
            "peak_away_from_supports_mpa": sized.result.peak_away_from_supports_mpa,
            "max_displacement_mm": sized.result.max_displacement_mm,
            "digest": sized.envelope.get("digest"),
            "stl": str(sized.stl),
            "part_stress": _part_stress(sized.envelope),
            "safety_factor": (
                None if sized.result is None else
                float(sized.result.material.yield_strength_mpa)
                / max(stress._percentile(sized.result.von_mises_mpa, 0.99), 1e-9)),
            "history": sized.history,
        },
        "verdict": {
            "compliance_ratio": ratio,
            "bar": COMPLIANCE_BAR,
            "outcome": verdict,
        },
        "warnings": sorted(set(warnings)),
        "wall_time_s": wall_time_s,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "cadex_importable": stress._cadex_importable(),
    }


def _part_stress(envelope: dict[str, Any]) -> dict[str, Any] | None:
    """What the rebuild said about the emitted ``part.stress`` check.

    **Not its numbers**, and that is a limitation of the road rather than a
    choice. ``part.stress`` is a declared output that carries no geometry
    (ADR-145), and ``cadex export``'s ``--json`` envelope describes only
    BREP outputs -- a stress check comes back as
    ``{"kind": "none", "skipped": "not a BREP output"}``. Its safety factor
    is computed, and it is in the project store, and there is no subcommand
    that serves it. Reading the store's own attempt files to get at it would
    couple this tree to a layout ADR-142 deliberately keeps it away from, so
    it does not.

    What the check is *for* still works, and it is the more valuable half:
    it is evaluated on every rebuild, so a parameter change that moves a
    mounting face until the load case no longer resolves fails the rebuild
    loudly instead of quietly measuring something else. The numbers in this
    report come from ``cadex_stress.py`` on the exported STL, which
    ``test_part_stress`` pins equal to ``part.stress`` anyway.
    """

    for item in envelope.get("outputs") or []:
        if not isinstance(item, dict) or item.get("name") != "check":
            continue
        return {"declared": True, "kind": item.get("kind"),
                "note": item.get("skipped") or ""}
    return None


# ---------------------------------------------------------------------------
# The whole thing.
# ---------------------------------------------------------------------------


def load_run(plan: topo.Plan, run_dir: Path
             ) -> tuple[np.ndarray, stress.Grid, dict[str, Any]]:
    """A finished ``topology.py`` run, read back off disk.

    The grid is rebuilt from the plan rather than stored, because
    ``domain_grid`` is deterministic in the plan and a grid read from a file
    could disagree with the density beside it without anything noticing.
    """

    density_path = run_dir / f"{plan.name}-density.npy"
    if not density_path.is_file():
        raise SkeletonError(
            f"{density_path} does not exist. Run `python analysis/topology.py "
            f"<plan> --out {run_dir}` first -- that is what writes it."
        )
    density = np.load(density_path)
    grid = topo.domain_grid(plan.domain, plan.element_mm)
    if density.shape != grid.shape:
        raise SkeletonError(
            f"The stored density is {density.shape} and this plan's domain "
            f"voxelises to {grid.shape}. The plan changed after the carve; "
            "re-run the carve."
        )
    report_path = run_dir / "report.json"
    simp: dict[str, Any] = {}
    if report_path.is_file():
        raw = json.loads(report_path.read_text(encoding="utf-8"))
        result = raw.get("result") or {}
        simp = {"compliance_n_mm": result.get("final_compliance_n_mm"),
                "mass_g": result.get("mass_g")}
    return density, grid, simp


def run(plan: topo.Plan, density: np.ndarray, grid: stress.Grid, *,
        simp: dict[str, Any], project: Path | None, out: Path,
        cadex: Sequence[str], passes: int = 5, engine: str | None = None,
        output: str | None = None, min_radius_mm: float | None = None,
        stress_element_mm: float | None = None,
        announce: Any = None) -> dict[str, Any]:
    """Fit, emit, install, size and judge."""

    started = time.monotonic()
    fitted = fit(density, grid, plan, min_radius_mm=min_radius_mm)

    if announce is not None:
        announce({"fitted_nodes": len(fitted.nodes),
                  "fitted_struts": len(fitted.bar_ends),
                  "coverage": fitted.coverage["fraction"]})

    sized = None
    if project is not None:
        target = float(simp.get("mass_g") or 0.0)
        if target <= 0.0:
            raise SkeletonError(
                "The carve's report carries no `mass_g`, so there is no mass "
                "to size against. Point `--run` at a directory that has "
                "`report.json` in it."
            )
        sized = size(fitted, plan, project=Path(project), out=Path(out),
                     cadex=cadex, target_mass_g=target, passes=passes,
                     engine=engine, output=output,
                     stress_element_mm=stress_element_mm, announce=announce)
    else:
        # No project: emit the script anyway, so `--out` is still useful
        # without an engine. The fit is the expensive half.
        Path(out).mkdir(parents=True, exist_ok=True)
        (Path(out) / "script.py").write_text(
            emit_script(fitted, plan, output=output,
                        stress_element_mm=stress_element_mm),
            encoding="utf-8")

    return report(fitted, plan, sized, simp=simp,
                  wall_time_s=time.monotonic() - started)


# ---------------------------------------------------------------------------
# The self-check: fit the cantilever, whose optimum is known.
# ---------------------------------------------------------------------------


def bracket_plan(*, size_mm: Sequence[float] = (60.0, 40.0, 40.0),
                 element_mm: float = 2.0, volume_fraction: float = 0.3,
                 force_n: float = 400.0) -> dict[str, Any]:
    """Two feet on the floor and a boss on the roof: the S4 benchmark.

    **Not** ``topology.cantilever_plan``, and the reason is the whole point
    of the coverage gate. A cantilever held over a whole face carries its
    load in *sheets* -- measured, half its cells lie within one cell of a
    surface -- and a strut graph fitted to it covers 0.76 and is refused.
    Two separated feet under one boss is the load path that has no sheet in
    it, and it covers 0.93. Both are in the suite: this one is what a fit
    looks like when it worked, and the cantilever is what the refusal is
    for.

    Everything else is S0's vocabulary unchanged, and the material is the
    same PLA the rest of the tree benchmarks on.
    """

    sx, sy, sz = (float(value) for value in size_mm)
    return {
        "schema": topo.PLAN_SCHEMA,
        "name": "bracket",
        "domain": {"box": {"size_mm": [sx, sy, sz], "origin_mm": [0.0, 0.0, 0.0]}},
        "element_mm": element_mm,
        "volume_fraction": volume_fraction,
        "filter_radius_mm": 5.0 * element_mm,
        "penalty": 3.0,
        "iterations": 60,
        "symmetry": ["y"],
        "interface_pad_mm": 6.0,
        "pin_domain_planes": True,
        "material": {
            "name": "self-check",
            "youngs_modulus_mpa": 3500.0,
            "poissons_ratio": 0.36,
            "yield_strength_mpa": 50.0,
            "density_kg_m3": 1240.0,
        },
        "supports": [
            {"name": "foot_near",
             "region": {"box": {"min_mm": [None, None, None],
                                "max_mm": [10.0, None, 1e-3]}}},
            {"name": "foot_far",
             "region": {"box": {"min_mm": [sx - 10.0, None, None],
                                "max_mm": [None, None, 1e-3]}}},
        ],
        "loads": [
            {"name": "boss",
             "region": {"box": {
                 "min_mm": [0.5 * sx - 8.0, 0.5 * sy - 8.0, sz - 1e-3],
                 "max_mm": [0.5 * sx + 8.0, 0.5 * sy + 8.0, None]}},
             "force_n": [0.0, 0.0, -force_n]},
        ],
    }


def cantilever_plan() -> dict[str, Any]:
    """S0's cantilever with S4a's keys on -- the field the gate refuses."""

    raw = topo.cantilever_plan(size_mm=(60.0, 20.0, 30.0), element_mm=1.5,
                               volume_fraction=0.3)
    raw["iterations"] = 60
    raw["filter_radius_mm"] = 4.5
    raw["symmetry"] = ["y"]
    raw["interface_pad_mm"] = 4.0
    raw["pin_domain_planes"] = True
    return raw


#: The self-check carves and fits this one.
self_check_plan = bracket_plan


def run_self_check(*, project: Path | None = None, out: Path | None = None,
                   cadex: Sequence[str] | None = None,
                   passes: int = 3) -> dict[str, Any]:
    """Carve the bracket, fit it, and report the compliance ratio."""

    import tempfile

    raw = bracket_plan()
    plan = topo.Plan.from_mapping(raw)
    carved = topo.optimise(plan)
    finished = topo.report(carved, plan)
    simp = {"compliance_n_mm": finished["result"]["final_compliance_n_mm"],
            "mass_g": finished["result"]["mass_g"]}

    with tempfile.TemporaryDirectory() as directory:
        return run(plan, carved.density, carved.grid, simp=simp,
                   project=project, out=Path(out or directory),
                   cadex=list(cadex or cadex_command()), passes=passes)


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="skeleton.py",
        description="Fit a parametric strut script to a carved density field.")
    parser.add_argument("plan", nargs="?", type=Path,
                        help=f"the {topo.PLAN_SCHEMA} JSON file that was carved")
    parser.add_argument("--run", type=Path, default=None,
                        help="the directory `topology.py --out` wrote. Omit "
                             "to carve it again here.")
    parser.add_argument("--project", type=Path, default=None,
                        help="a Cadex project to install the script into. "
                             "Omit to write the script and skip the sizing "
                             "loop, which needs a built engine.")
    parser.add_argument("--out", type=Path, default=None,
                        help="a directory for the script, the rebuilds and "
                             "the report")
    parser.add_argument("--passes", type=int, default=5,
                        help="sizing iterations (each is one real rebuild "
                             "plus one real solve)")
    parser.add_argument("--output", default=None,
                        help="the name the script publishes the part under")
    parser.add_argument("--min-radius-mm", type=float, default=None,
                        help="the thinnest member to fit; defaults to one cell")
    parser.add_argument("--stress-element-mm", type=float, default=None,
                        help="the budget for the emitted `part.stress` check")
    parser.add_argument("--cadex", default=None, help="path to the cadex shim")
    parser.add_argument("--engine", default=None, help="path to an engine root")
    parser.add_argument("--self-check", action="store_true",
                        help="carve and fit the 3-D cantilever benchmark")
    options = parser.parse_args(list(argv[1:]))

    def announce(record: dict[str, Any]) -> None:
        print(json.dumps(record, sort_keys=True), file=sys.stderr)

    try:
        if options.self_check:
            finished = run_self_check(
                project=options.project, out=options.out,
                cadex=None if options.cadex is None else [options.cadex],
                passes=options.passes)
        else:
            if options.plan is None:
                parser.error("a plan is required")
            if options.out is None:
                parser.error("--out is required")
            raw = json.loads(options.plan.read_text(encoding="utf-8"))
            plan = topo.Plan.from_mapping(raw, base=options.plan.resolve().parent)
            if options.run is not None:
                density, grid, simp = load_run(plan, options.run)
            else:
                carved = topo.optimise(plan)
                density, grid = carved.density, carved.grid
                finished_carve = topo.report(carved, plan)
                simp = {
                    "compliance_n_mm":
                        finished_carve["result"]["final_compliance_n_mm"],
                    "mass_g": finished_carve["result"]["mass_g"],
                }
            finished = run(
                plan, density, grid, simp=simp, project=options.project,
                out=options.out, cadex=cadex_command(options.cadex),
                passes=options.passes, engine=options.engine,
                output=options.output, min_radius_mm=options.min_radius_mm,
                stress_element_mm=options.stress_element_mm,
                announce=announce)
            options.out.mkdir(parents=True, exist_ok=True)
            (options.out / "report.json").write_text(
                json.dumps(finished, indent=2, sort_keys=True), encoding="utf-8")
    except (SkeletonError, topo.TopologyError, stress.StressError) as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2

    for warning in finished.get("warnings", []):
        print(f"warning: {warning}", file=sys.stderr)
    print(json.dumps(finished, sort_keys=True))
    return 0 if finished["verdict"]["outcome"] in ("ship", "not-measured") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
