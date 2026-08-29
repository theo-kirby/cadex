#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""One solid and one declared load in, one stress report out (S0).

**This program is not part of the engine and is never installed into the
payload.** It lives at the repository root beside ``training/`` because it
is the same species of thing: something you copy to whatever machine has
the time to run it. CMake never installs it, no payload carries it, and
nothing in it enters ``pixi.toml`` -- ``CARRIED_PYPI_PACKAGES`` stays one
entry long, which is what ADR-076 named that constant for. ADR-141 records
the decision; ``docs/STRUCTURAL.md`` is the arc.

It is held to ``training/cadex_train.py``'s discipline, for the same
reasons:

* It does not speak the cadexd protocol. It reads files off disk -- a
  tessellation or a STEP, and a load-case JSON -- and writes one JSON
  report. It never opens a socket and never spawns an engine.
* It reports whether ``CadexDynamics`` was importable, so a test can assert
  the negative. A run where that comes back ``true`` was not a stock
  process and proves nothing about what this file can do alone.
* Exactly one JSON line on stdout; the human-readable stream is stderr, and
  **nothing parses stderr** (ADR-093 measured what happens when a receipt is
  taken from a stream something else can write into).

**Why a hand-written hex core rather than a library.** The measured facts
are in ADR-141, and the short form is: SIMP topology optimisation (S2) runs
on a structured hex grid anyway, so a tetrahedral pipeline for S0 and a
voxel pipeline for S2 would be two codebases for one job; ``numpy`` and
``scipy`` are already in the engine payload, so this costs no bytes if a
solve ever moves in-engine (S3); and filling a structured grid needs no
mesher, so it needs no ``gmsh``, so it raises no GPL question. The August
2026 survey found no maintained permissive package that is numpy/scipy-only
-- the two closest are GPL-3 (JAX-FEM) or drag in PyTorch (torch-fem).

**The element is C3D8I, not C3D8, and that is the load-bearing choice.**
A fully-integrated trilinear hex shear-locks in bending: at the resolutions
a laptop can afford it reports a beam several times too stiff, and a stress
number derived from it is wrong in the direction that flatters the part.
So the element carries Wilson incompatible modes, statically condensed at
the element level. Every element in a structured grid is geometrically
identical, so the condensed 24x24 matrix is computed **once**; and because
condensation commutes with a uniform scaling of the element energy, the
same matrix is reusable under a SIMP density. ``--element c3d8`` selects
the locking element, which exists so a test can measure the difference
rather than assert it.

**A single grid is not a measurement.** A voxel mesh reports inflated peak
stress where a curved or re-entrant boundary is stair-stepped, and the
inflation does not go away with refinement at a genuine singularity -- it
grows. So the default is a refinement sweep, and the report says plainly
which quantities settled and which did not. ADR-129 is the standing lesson:
a plausible-looking result survived being written down and was wrong, and
what caught it was a second method. ``analysis/calculix.py`` is that second
method.

Usage::

    python analysis/cadex_stress.py bracket.stl --load-case bracket-loads.json
    python analysis/cadex_stress.py bracket.step --load-case l.json --element-mm 1.5
    python analysis/cadex_stress.py --self-check
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import platform
import struct
import sys
import time
from typing import Any, Iterable, Sequence

import numpy as np

REPORT_SCHEMA = "cadex-analysis-stress-v1"
LOAD_CASE_SCHEMA = "cadex-analysis-load-case-v1"

#: Gauss points of the 2x2x2 rule, and their weights. Written out rather
#: than derived so the quadrature a reader is checking is the quadrature
#: that runs.
_GAUSS = 1.0 / math.sqrt(3.0)

#: Node ordering inside one element: ``n = i + 2*j + 4*k`` over the corner
#: signs. Everything downstream -- the element matrix, the global node id,
#: and ``calculix.py``'s permutation into Abaqus order -- reads this array
#: rather than re-deriving a corner ordering of its own.
_NODE_SIGNS = np.array(
    [[xi, eta, zeta]
     for zeta in (-1.0, 1.0)
     for eta in (-1.0, 1.0)
     for xi in (-1.0, 1.0)],
    dtype=float,
)

#: How far the refinement sweep goes by default, and by what ratio. 0.75
#: per level is 2.4x the elements each time: enough to see a quantity move,
#: cheap enough that three levels is still a laptop-minute at useful sizes.
_REFINEMENT_RATIO = 0.75
_DEFAULT_LEVELS = 3

#: A displacement that changes by less than this between the two finest
#: levels is called converged. Peak stress gets the same test and usually
#: fails it, which is the report being honest rather than the sweep being
#: too short -- see ``_convergence``.
_CONVERGENCE_FRACTION = 0.05

#: Above this many free degrees of freedom the direct factorisation is not
#: worth its fill-in and the solve goes to conjugate gradients.
#: ``--solver`` overrides it in both directions.
#:
#: This was 60,000 until S2 measured it, on the same M-series laptop that
#: set it. It was wrong by a wide margin -- Jacobi-preconditioned CG beats
#: the direct factorisation everywhere above a few thousand degrees of
#: freedom, and by more the larger the problem gets:
#:
#: ====================  ==========  ==========  ==========
#: free dofs                 21,800      47,000     158,000
#: direct (``splu``)         1.22 s      7.22 s          --
#: CG + Jacobi               0.24 s      0.65 s      3.13 s
#: ====================  ==========  ==========  ==========
#:
#: So the old limit sent every problem in the interesting range to the
#: slower solver: 3x at 21.8k and 11x at 47k. The new one keeps the direct
#: path for the small systems where a factorisation really is cheaper than
#: a few hundred sparse mat-vecs, and hands everything else to CG.
_DIRECT_DOF_LIMIT = 10_000

#: What a CG solve is asked for, and what it is allowed to spend. The
#: residual it actually reached is in the report either way: a solve that
#: stopped on the iteration cap is a number with a caveat attached, not a
#: failure, and hiding that in a log would be exactly the ADR-093 mistake.
_CG_TOLERANCE = 1.0e-10
_CG_ITERATION_FACTOR = 40


class StressError(RuntimeError):
    """A refusal with a sentence a person can act on."""


# ---------------------------------------------------------------------------
# Material, regions and the load case.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Material:
    """Everything the linear solve and the verdict need, in mm/N/MPa.

    ``yield_strength_mpa`` is what the safety factor divides by. It has no
    default and never will: a stress number carries a verdict only against
    a strength somebody declared, and inventing one here would make the
    verdict look like a measurement.
    """

    youngs_modulus_mpa: float
    poissons_ratio: float
    yield_strength_mpa: float
    density_kg_m3: float
    name: str = "declared"

    @classmethod
    def from_mapping(cls, raw: Any) -> "Material":
        if not isinstance(raw, dict):
            raise StressError("The load case declares no `material` block.")
        missing = [
            key for key in (
                "youngs_modulus_mpa", "poissons_ratio",
                "yield_strength_mpa", "density_kg_m3",
            )
            if key not in raw
        ]
        if missing:
            raise StressError(
                f"The material declares no {', '.join(missing)}. All four are "
                "required: two set the stiffness, one sets the verdict, and "
                "one sets the mass the report is asked for."
            )
        nu = float(raw["poissons_ratio"])
        if not -1.0 < nu < 0.5:
            raise StressError(
                f"A Poisson's ratio of {nu} is outside (-1, 0.5), where the "
                "isotropic stiffness matrix is not positive definite."
            )
        if float(raw["youngs_modulus_mpa"]) <= 0.0:
            raise StressError("Young's modulus must be positive.")
        return cls(
            youngs_modulus_mpa=float(raw["youngs_modulus_mpa"]),
            poissons_ratio=nu,
            yield_strength_mpa=float(raw["yield_strength_mpa"]),
            density_kg_m3=float(raw["density_kg_m3"]),
            name=str(raw.get("name") or "declared"),
        )

    def elasticity_matrix(self) -> np.ndarray:
        """The 6x6 isotropic D, in the engineering-shear strain order.

        ``[exx, eyy, ezz, gxy, gyz, gzx]`` -- the same order ``_strain_matrix``
        builds and the same order CalculiX prints, which is why
        ``calculix.py`` compares component by component rather than only on
        von Mises.
        """

        e = self.youngs_modulus_mpa
        nu = self.poissons_ratio
        lam = e * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))
        mu = e / (2.0 * (1.0 + nu))
        d = np.zeros((6, 6), dtype=float)
        d[:3, :3] = lam
        d[0, 0] = d[1, 1] = d[2, 2] = lam + 2.0 * mu
        d[3, 3] = d[4, 4] = d[5, 5] = mu
        return d


def _region_mask(region: Any, points: np.ndarray, bounds: tuple[np.ndarray, np.ndarray],
                 context: str) -> np.ndarray:
    """Which of ``points`` a declared region selects.

    Four kinds, all named geometrically rather than by a face id, because a
    face id is a thing the script owns and this file has no script. ``face``
    is the one that carries a bracket: "the base", "the far end".
    """

    if not isinstance(region, dict) or len(region) != 1:
        raise StressError(
            f"{context} declares a region that is not exactly one of "
            "`face`, `box`, `sphere` or `all`."
        )
    low, high = bounds
    (kind, spec), = region.items()

    if kind == "all":
        return np.ones(len(points), dtype=bool)

    if kind == "face":
        axis = {"x": 0, "y": 1, "z": 2}.get(str(spec.get("axis", "")).lower())
        if axis is None:
            raise StressError(f"{context}: a `face` region needs axis x, y or z.")
        at = str(spec.get("at", "")).lower()
        depth = float(spec.get("depth_mm", 0.0))
        if depth <= 0.0:
            raise StressError(
                f"{context}: a `face` region needs a positive `depth_mm`. A "
                "zero-thickness face selects the nodes that happen to land "
                "exactly on a plane, which is a function of the grid rather "
                "than of the part."
            )
        if at == "min":
            return points[:, axis] <= low[axis] + depth
        if at == "max":
            return points[:, axis] >= high[axis] - depth
        raise StressError(f"{context}: a `face` region is `at` min or max.")

    if kind == "box":
        lo = spec.get("min_mm") or [None, None, None]
        hi = spec.get("max_mm") or [None, None, None]
        mask = np.ones(len(points), dtype=bool)
        for axis in range(3):
            if lo[axis] is not None:
                mask &= points[:, axis] >= float(lo[axis])
            if hi[axis] is not None:
                mask &= points[:, axis] <= float(hi[axis])
        return mask

    if kind == "sphere":
        centre = np.asarray(spec["centre_mm"], dtype=float)
        radius = float(spec["radius_mm"])
        return np.linalg.norm(points - centre[None, :], axis=1) <= radius

    raise StressError(f"{context}: unknown region kind {kind!r}.")


# ---------------------------------------------------------------------------
# Reading a solid: tessellations by hand, STEP through OCCT when it is there.
# ---------------------------------------------------------------------------


def _read_binary_stl(blob: bytes) -> np.ndarray:
    count = struct.unpack("<I", blob[80:84])[0]
    expected = 84 + count * 50
    if len(blob) < expected:
        raise StressError(
            f"This STL declares {count} triangles and carries {len(blob) - 84} "
            "bytes of them."
        )
    raw = np.frombuffer(blob[84:expected], dtype=np.uint8).reshape(count, 50)
    values = raw[:, 12:48].copy().view("<f4").reshape(count, 3, 3)
    return np.asarray(values, dtype=float)


def _read_ascii_stl(text: str) -> np.ndarray:
    points: list[list[float]] = []
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0] == "vertex":
            points.append([float(value) for value in parts[1:4]])
    if len(points) % 3:
        raise StressError("This ASCII STL has a triangle with fewer than three vertices.")
    return np.asarray(points, dtype=float).reshape(-1, 3, 3)


def _read_ply(blob: bytes) -> np.ndarray:
    end = blob.find(b"end_header")
    if end < 0:
        raise StressError("This PLY has no `end_header`.")
    header = blob[:end].decode("ascii", errors="replace").splitlines()
    body = blob[blob.find(b"\n", end) + 1:]
    fmt = ""
    vertex_count = face_count = 0
    vertex_properties: list[str] = []
    element = ""
    for line in header:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "format":
            fmt = parts[1]
        elif parts[0] == "element":
            element = parts[1]
            if element == "vertex":
                vertex_count = int(parts[2])
            elif element == "face":
                face_count = int(parts[2])
        elif parts[0] == "property" and element == "vertex" and parts[1] != "list":
            vertex_properties.append(parts[1])
    if fmt == "ascii":
        tokens = body.split()
        stride = len(vertex_properties)
        flat = np.asarray(tokens[:vertex_count * stride], dtype=float)
        vertices = flat.reshape(vertex_count, stride)[:, :3]
        cursor = vertex_count * stride
        faces: list[tuple[int, int, int]] = []
        for _ in range(face_count):
            n = int(tokens[cursor])
            idx = [int(tokens[cursor + 1 + k]) for k in range(n)]
            cursor += 1 + n
            for k in range(1, n - 1):
                faces.append((idx[0], idx[k], idx[k + 1]))
        return vertices[np.asarray(faces, dtype=int)]
    if fmt != "binary_little_endian":
        raise StressError(f"PLY format {fmt!r} is not read here; use ASCII, "
                          "binary_little_endian, or an STL.")
    sizes = {"float": 4, "float32": 4, "double": 8, "float64": 8,
             "uchar": 1, "uint8": 1, "char": 1, "int8": 1,
             "short": 2, "int16": 2, "ushort": 2, "uint16": 2,
             "int": 4, "int32": 4, "uint": 4, "uint32": 4}
    dtype_names = {4: "<f4", 8: "<f8"}
    stride = 0
    for line in header:
        parts = line.split()
        if parts and parts[0] == "property" and parts[1] in sizes:
            stride += sizes[parts[1]]
    if stride == 0:
        raise StressError("This PLY declares no vertex properties.")
    raw = np.frombuffer(body[:vertex_count * stride], dtype=np.uint8)
    raw = raw.reshape(vertex_count, stride)
    first = next(line.split()[1] for line in header
                 if line.startswith("property") and line.split()[1] in sizes)
    width = sizes[first]
    vertices = raw[:, :3 * width].copy().view(dtype_names[width]).astype(float)
    cursor = vertex_count * stride
    faces = []
    for _ in range(face_count):
        n = int(body[cursor])
        cursor += 1
        idx = np.frombuffer(body[cursor:cursor + 4 * n], dtype="<i4")
        cursor += 4 * n
        for k in range(1, n - 1):
            faces.append((int(idx[0]), int(idx[k]), int(idx[k + 1])))
    return vertices[np.asarray(faces, dtype=int)]


def _read_obj(text: str) -> np.ndarray:
    vertices: list[list[float]] = []
    faces: list[tuple[int, int, int]] = []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            vertices.append([float(value) for value in parts[1:4]])
        elif parts[0] == "f":
            idx = [int(token.split("/")[0]) - 1 for token in parts[1:]]
            for k in range(1, len(idx) - 1):
                faces.append((idx[0], idx[k], idx[k + 1]))
    return np.asarray(vertices, dtype=float)[np.asarray(faces, dtype=int)]


def _read_step(path: Path, deflection_mm: float) -> tuple[np.ndarray, float | None]:
    """A STEP through ``pythonocc-core``, tessellated to the same triangles.

    Optional on purpose. ``pythonocc-core`` is in the pixi environment and is
    LGPL like the engine side, but it is a conda package rather than a wheel,
    and ``analysis/requirements.txt`` pins only what pip can install into a
    venv on any machine. So STEP is the precise path when OCCT is present and
    a tessellation is the path that always works -- and the tessellation is
    what ``./cadex --out`` writes beside the STEP anyway.

    Returns the triangles and OCCT's exact volume, which becomes a third
    number in the report's fill evidence: exact, tessellated, and voxelised.
    """

    try:
        from OCC.Core.STEPControl import STEPControl_Reader
        from OCC.Core.IFSelect import IFSelect_RetDone
        from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
        from OCC.Core.TopExp import TopExp_Explorer
        from OCC.Core.TopAbs import TopAbs_FACE
        from OCC.Core.BRep import BRep_Tool
        from OCC.Core.TopoDS import topods
        from OCC.Core.TopLoc import TopLoc_Location
        from OCC.Core.BRepGProp import brepgprop
        from OCC.Core.GProp import GProp_GProps
    except ImportError as error:  # pragma: no cover - environment dependent
        raise StressError(
            "Reading a STEP needs `pythonocc-core`, which is not installed "
            "here. Point this at the tessellation the same export wrote "
            "(`.stl`, `.ply` or `.obj`) instead -- that path needs numpy "
            f"only. ({error})"
        ) from error

    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise StressError(f"OCCT declined to read {path.name}.")
    reader.TransferRoots()
    shape = reader.OneShape()

    props = GProp_GProps()
    brepgprop.VolumeProperties(shape, props)
    exact_volume = float(props.Mass())

    BRepMesh_IncrementalMesh(shape, deflection_mm, False, 0.5, True)
    triangles: list[list[list[float]]] = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        location = TopLoc_Location()
        facing = BRep_Tool.Triangulation(face, location)
        if facing is not None:
            transform = location.Transformation()
            reversed_face = face.Orientation() == 1  # TopAbs_REVERSED
            for index in range(1, facing.NbTriangles() + 1):
                tri = facing.Triangle(index)
                a, b, c = tri.Get()
                if reversed_face:
                    a, c = c, a
                corners = []
                for node in (a, b, c):
                    point = facing.Node(node).Transformed(transform)
                    corners.append([point.X(), point.Y(), point.Z()])
                triangles.append(corners)
        explorer.Next()
    if not triangles:
        raise StressError(f"{path.name} tessellated to no triangles.")
    return np.asarray(triangles, dtype=float), exact_volume


def read_solid(path: Path, *, deflection_mm: float = 0.2) -> tuple[np.ndarray, float | None]:
    """Triangles of a closed surface, and an exact volume when one is known."""

    suffix = path.suffix.lower()
    if suffix in {".step", ".stp"}:
        return _read_step(path, deflection_mm)
    blob = path.read_bytes()
    if suffix == ".stl":
        head = blob[:5].lower()
        if head == b"solid" and b"facet" in blob[:2048].lower():
            return _read_ascii_stl(blob.decode("utf-8", errors="replace")), None
        return _read_binary_stl(blob), None
    if suffix == ".ply":
        return _read_ply(blob), None
    if suffix == ".obj":
        return _read_obj(blob.decode("utf-8", errors="replace")), None
    raise StressError(
        f"{path.name} is not a solid this reads. It takes `.stl`, `.ply`, "
        "`.obj` or -- with pythonocc-core installed -- `.step`."
    )


def mesh_volume_mm3(triangles: np.ndarray) -> float:
    """Signed volume by the divergence theorem.

    Its sign is the winding check: a closed surface with consistent outward
    normals gives a positive number, and anything else is a tessellation
    this file should refuse to voxelise rather than quietly fill inside out.
    """

    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


# ---------------------------------------------------------------------------
# Voxelisation: a scanline parity fill, which is all a closed surface needs.
# ---------------------------------------------------------------------------


@dataclass
class Grid:
    """A structured hex grid and which of its cells are solid."""

    origin: np.ndarray
    spacing: np.ndarray
    shape: tuple[int, int, int]
    occupancy: np.ndarray  # (nx, ny, nz) bool

    @property
    def element_volume_mm3(self) -> float:
        return float(np.prod(self.spacing))

    @property
    def solid_count(self) -> int:
        return int(self.occupancy.sum())

    def cell_centres(self) -> np.ndarray:
        nx, ny, nz = self.shape
        axes = [self.origin[axis] + (np.arange(n) + 0.5) * self.spacing[axis]
                for axis, n in enumerate((nx, ny, nz))]
        grid = np.meshgrid(*axes, indexing="ij")
        return np.stack([value.ravel() for value in grid], axis=1)

    def node_positions(self) -> np.ndarray:
        nx, ny, nz = self.shape
        axes = [self.origin[axis] + np.arange(n + 1) * self.spacing[axis]
                for axis, n in enumerate((nx, ny, nz))]
        grid = np.meshgrid(*axes, indexing="ij")
        return np.stack([value.ravel(order="F") for value in grid], axis=1)


def voxelise(triangles: np.ndarray, element_mm: float) -> Grid:
    """Fill a closed triangle soup onto a structured grid.

    A ray up the +z axis through each cell centre, counting crossings: a
    cell is solid when an odd number of triangles lie below it.

    **Two defences against the one case parity gets wrong**, which is a ray
    that meets an edge two triangles share and is therefore counted twice:

    * The sample points are nudged off the grid lines by a *different*
      irrational fraction of a cell on each axis. A single shared fraction
      is not enough, and the difference is not theoretical: with the same
      nudge on x and y, every sample point on the ``x = y`` diagonal stays
      on it, so a cap tessellated as a triangle fan lost its whole diagonal
      -- 11 columns of a 20-cell cylinder, a 4.5% volume error that appeared
      only after a float32 round trip through an STL, which is the worst way
      for a bug to be visible.
    * Crossings that coincide within a fraction of a nanometre are collapsed
      to one. That is not a fudge: a ray through a shared edge crosses the
      surface once, and both triangles reporting it report the same height.
      This one is exact where the nudge is only unlikely.

    **The grid is fitted to the part's bounding box**, one axis at a time:
    ``element_mm`` sets how many cells go across each extent, and the cell
    size is then that extent divided by that count. So the cells are very
    slightly anisotropic and the outer surface lands exactly on a node
    plane.

    That is not a nicety. Centre-sampled voxelisation of a 10 mm bar at
    1.875 mm keeps five cells and throws away 6% of the height, and a beam's
    stiffness goes as the cube of its height -- measured here before the fit
    was added, a refinement sweep moved the tip deflection 1.14 -> 1.45 ->
    1.21 mm and there was no convergence to read, because each level was
    solving a differently-shaped beam. Fitting the grid makes the sequence a
    sequence about the discretisation rather than about the shape.
    """

    if element_mm <= 0.0:
        raise StressError("The element size must be positive.")
    low = triangles.reshape(-1, 3).min(axis=0)
    high = triangles.reshape(-1, 3).max(axis=0)
    extent = high - low
    counts = np.maximum(np.rint(np.where(extent > 0.0, extent, element_mm)
                                / float(element_mm)), 1.0)
    spacing = np.where(extent > 0.0, extent / counts, float(element_mm))
    shape = counts.astype(int)
    origin = low.copy()

    nx, ny, nz = (int(value) for value in shape)
    # The nudge, a different irrational per axis -- see the docstring for
    # what a shared one costs.
    jitter = spacing * np.array([
        (math.sqrt(2.0) - 1.0) * 0.037,
        (math.sqrt(3.0) - 1.0) * 0.041,
        (math.sqrt(5.0) - 2.0) * 0.043,
    ])
    xs = origin[0] + (np.arange(nx) + 0.5) * spacing[0] + jitter[0]
    ys = origin[1] + (np.arange(ny) + 0.5) * spacing[1] + jitter[1]
    zs = origin[2] + (np.arange(nz) + 0.5) * spacing[2] + jitter[2]

    crossings: dict[tuple[int, int], list[float]] = {}
    a = triangles[:, 0]
    ab = triangles[:, 1] - a
    ac = triangles[:, 2] - a
    # The 2-D cross product of the projected edges: zero means the triangle
    # is vertical, and a vertical triangle is crossed by no vertical ray.
    denominator = ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0]
    live = np.abs(denominator) > 1e-14
    for index in np.nonzero(live)[0]:
        tri = triangles[index]
        lo = tri.min(axis=0)
        hi = tri.max(axis=0)
        i0 = int(np.searchsorted(xs, lo[0], side="left"))
        i1 = int(np.searchsorted(xs, hi[0], side="right"))
        j0 = int(np.searchsorted(ys, lo[1], side="left"))
        j1 = int(np.searchsorted(ys, hi[1], side="right"))
        if i0 >= i1 or j0 >= j1:
            continue
        px = xs[i0:i1]
        py = ys[j0:j1]
        qx = px[:, None] - tri[0, 0]
        qy = py[None, :] - tri[0, 1]
        det = denominator[index]
        u = (qx * ac[index, 1] - qy * ac[index, 0]) / det
        v = (qy * ab[index, 0] - qx * ab[index, 1]) / det
        inside = (u >= 0.0) & (v >= 0.0) & (u + v <= 1.0)
        if not inside.any():
            continue
        z = tri[0, 2] + u * ab[index, 2] + v * ac[index, 2]
        for local_i, local_j in zip(*np.nonzero(inside)):
            crossings.setdefault(
                (i0 + int(local_i), j0 + int(local_j)), []
            ).append(float(z[local_i, local_j]))

    occupancy = np.zeros((nx, ny, nz), dtype=bool)
    coincident = 1.0e-7 * float(spacing[2])
    for (i, j), hits in crossings.items():
        ordered = np.sort(np.asarray(hits))
        if len(ordered) > 1:
            ordered = ordered[np.concatenate(
                ([True], np.diff(ordered) > coincident))]
        below = np.searchsorted(ordered, zs, side="left")
        occupancy[i, j] = (below % 2) == 1
    return Grid(origin=origin, spacing=spacing, shape=(nx, ny, nz),
                occupancy=occupancy)


# ---------------------------------------------------------------------------
# The element: a trilinear hex with Wilson incompatible modes, condensed.
# ---------------------------------------------------------------------------


def _strain_matrix(gradients: np.ndarray) -> np.ndarray:
    """A 6 x 3k strain-displacement block from k gradient triples.

    One function for both halves of the element -- the eight corner shape
    functions and the three incompatible modes -- because they differ only
    in how many gradients they bring.
    """

    count = len(gradients)
    matrix = np.zeros((6, 3 * count), dtype=float)
    for index, (dx, dy, dz) in enumerate(gradients):
        base = 3 * index
        matrix[0, base + 0] = dx
        matrix[1, base + 1] = dy
        matrix[2, base + 2] = dz
        matrix[3, base + 0] = dy
        matrix[3, base + 1] = dx
        matrix[4, base + 1] = dz
        matrix[4, base + 2] = dy
        matrix[5, base + 0] = dz
        matrix[5, base + 2] = dx
    return matrix


def _corner_gradients(natural: np.ndarray, spacing: np.ndarray) -> np.ndarray:
    xi, eta, zeta = natural
    signs = _NODE_SIGNS
    gradients = np.empty((8, 3), dtype=float)
    gradients[:, 0] = 0.125 * signs[:, 0] * (1 + signs[:, 1] * eta) * (1 + signs[:, 2] * zeta)
    gradients[:, 1] = 0.125 * signs[:, 1] * (1 + signs[:, 0] * xi) * (1 + signs[:, 2] * zeta)
    gradients[:, 2] = 0.125 * signs[:, 2] * (1 + signs[:, 0] * xi) * (1 + signs[:, 1] * eta)
    return gradients * (2.0 / spacing)[None, :]


def _incompatible_gradients(natural: np.ndarray, spacing: np.ndarray) -> np.ndarray:
    """Gradients of ``1 - xi^2``, ``1 - eta^2`` and ``1 - zeta^2``.

    Each integrates to zero over the element, which is why the element still
    passes the constant-strain patch test with the modes switched on.
    """

    gradients = np.zeros((3, 3), dtype=float)
    for axis in range(3):
        gradients[axis, axis] = -2.0 * natural[axis]
    return gradients * (2.0 / spacing)[None, :]


@dataclass(frozen=True)
class Element:
    """One element's condensed stiffness, and how to recover its strain.

    ``stiffness`` is 24x24 and is what the global assembly sees.
    ``recover`` is the 9x24 map from corner displacements to the internal
    incompatible amplitudes, which stress recovery needs and the assembly
    does not. ``strain_at`` are the eight Gauss-point strain matrices,
    already split into their corner and internal halves.
    """

    spacing: np.ndarray
    stiffness: np.ndarray
    recover: np.ndarray
    corner_strain: np.ndarray      # (8, 6, 24)
    internal_strain: np.ndarray    # (8, 6, 9)
    centroid_strain: np.ndarray    # (6, 24) with the internal part folded in
    volume_mm3: float


def build_element(spacing: np.ndarray, material: Material, *,
                  incompatible: bool = True) -> Element:
    """The one element matrix a structured grid needs, computed once.

    Every element of the grid is this element translated, so this is
    computed once and reused for all of them -- which is what makes the
    assembly a single vectorised scatter rather than a loop over elements.
    """

    d = material.elasticity_matrix()
    det = float(np.prod(spacing)) / 8.0
    points = [np.array([xi, eta, zeta], dtype=float)
              for zeta in (-_GAUSS, _GAUSS)
              for eta in (-_GAUSS, _GAUSS)
              for xi in (-_GAUSS, _GAUSS)]

    kcc = np.zeros((24, 24), dtype=float)
    kci = np.zeros((24, 9), dtype=float)
    kii = np.zeros((9, 9), dtype=float)
    corner_strain = np.zeros((8, 6, 24), dtype=float)
    internal_strain = np.zeros((8, 6, 9), dtype=float)

    for index, natural in enumerate(points):
        bc = _strain_matrix(_corner_gradients(natural, spacing))
        bi = _strain_matrix(_incompatible_gradients(natural, spacing))
        corner_strain[index] = bc
        internal_strain[index] = bi
        kcc += bc.T @ d @ bc * det
        if incompatible:
            kci += bc.T @ d @ bi * det
            kii += bi.T @ d @ bi * det

    if incompatible:
        recover = -np.linalg.solve(kii, kci.T)
        stiffness = kcc + kci @ recover
    else:
        recover = np.zeros((9, 24), dtype=float)
        stiffness = kcc

    centre = np.zeros(3, dtype=float)
    bc_centre = _strain_matrix(_corner_gradients(centre, spacing))
    bi_centre = _strain_matrix(_incompatible_gradients(centre, spacing))
    centroid_strain = bc_centre + bi_centre @ recover

    return Element(
        spacing=spacing,
        stiffness=0.5 * (stiffness + stiffness.T),
        recover=recover,
        corner_strain=corner_strain,
        internal_strain=internal_strain,
        centroid_strain=centroid_strain,
        volume_mm3=float(np.prod(spacing)),
    )


# ---------------------------------------------------------------------------
# Assembly, boundary conditions and the solve.
# ---------------------------------------------------------------------------


@dataclass
class Result:
    """One solve, with everything the report and the tests want off it."""

    grid: Grid
    material: Material
    displacement: np.ndarray            # (nodes, 3) mm
    element_indices: np.ndarray         # (ne, 3) grid coordinates of solid cells
    element_dofs: np.ndarray            # (ne, 24)
    von_mises_mpa: np.ndarray           # (ne,) worst Gauss point per element
    centroid_stress_mpa: np.ndarray     # (ne, 6)
    support_adjacent: np.ndarray        # (ne,) bool
    fixed_dofs: np.ndarray              # (3 * nodes,) bool
    solver: dict[str, Any]
    warnings: list[str] = field(default_factory=list)

    @property
    def max_displacement_mm(self) -> float:
        return float(np.linalg.norm(self.displacement, axis=1).max())

    @property
    def peak_von_mises_mpa(self) -> float:
        return float(self.von_mises_mpa.max())

    @property
    def peak_away_from_supports_mpa(self) -> float:
        free = ~self.support_adjacent
        if not free.any():
            return self.peak_von_mises_mpa
        return float(self.von_mises_mpa[free].max())

    def element_centres(self) -> np.ndarray:
        return (self.grid.origin[None, :]
                + (self.element_indices + 0.5) * self.grid.spacing[None, :])

    def volume_mm3(self) -> float:
        return len(self.element_indices) * self.grid.element_volume_mm3

    def mass_g(self) -> float:
        return self.volume_mm3() * self.material.density_kg_m3 * 1.0e-6


def _node_ids(indices: np.ndarray, shape: tuple[int, int, int]) -> np.ndarray:
    """Global node ids of the eight corners of each element.

    Node numbering is ``i + (nx+1) * (j + (ny+1) * k)``, and the corner order
    is ``_NODE_SIGNS`` -- so element-local dof ``3n+c`` always means the same
    corner, in this file and in the CalculiX deck.
    """

    nx, ny, _ = shape
    corners = ((_NODE_SIGNS + 1.0) / 2.0).astype(int)  # (8, 3) of 0/1
    ids = np.empty((len(indices), 8), dtype=np.int64)
    for corner in range(8):
        i = indices[:, 0] + corners[corner, 0]
        j = indices[:, 1] + corners[corner, 1]
        k = indices[:, 2] + corners[corner, 2]
        ids[:, corner] = i + (nx + 1) * (j + (ny + 1) * k)
    return ids


def _prune_unsupported(grid: Grid, supported_cells: np.ndarray) -> tuple[np.ndarray, int]:
    """Drop solid cells that no support can reach, face by face.

    An island of material with nothing holding it is a rigid-body mode, and
    a rigid-body mode is a singular stiffness matrix -- a direct solve fails
    and an iterative one wanders. Dropping it is the only honest option, and
    the count goes in the report rather than into a log.
    """

    from collections import deque

    reachable = np.zeros_like(grid.occupancy)
    queue = deque(zip(*np.nonzero(supported_cells)))
    for seed in queue:
        reachable[seed] = True
    nx, ny, nz = grid.shape
    neighbours = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    while queue:
        i, j, k = queue.popleft()
        for di, dj, dk in neighbours:
            a, b, c = i + di, j + dj, k + dk
            if 0 <= a < nx and 0 <= b < ny and 0 <= c < nz:
                if grid.occupancy[a, b, c] and not reachable[a, b, c]:
                    reachable[a, b, c] = True
                    queue.append((a, b, c))
    dropped = int(grid.occupancy.sum() - reachable.sum())
    return reachable, dropped


def _active_nodes(grid: Grid, element_dofs: np.ndarray) -> np.ndarray:
    active = np.zeros(3 * (grid.shape[0] + 1) * (grid.shape[1] + 1)
                      * (grid.shape[2] + 1), dtype=bool)
    active[element_dofs.ravel()] = True
    return active.reshape(-1, 3).any(axis=1)


def assemble_forces(grid: Grid, material: Material, load_case: dict[str, Any],
                    element_dofs: np.ndarray) -> np.ndarray:
    """The right-hand side one declared load case produces on one grid.

    Its own function because ``analysis/calculix.py`` needs the **same**
    vector: a cross-check that re-derived the loads from the declaration
    would be comparing two readings of the load case as well as two solvers,
    and a disagreement would not say which of the two was at fault.

    A total force is shared equally over the nodes the region selects. A
    torque is applied as a couple: solve ``A w = T`` for a spin field, where
    ``A = (sum |r|^2) I - sum r r^T`` over the arms from the region's own
    centroid, and set ``f_i = w x r_i``. That lands the couple exactly and
    adds no net force, which is what makes a 6-D wrench out of a MuJoCo
    rollout expressible as one load entry.
    """

    nodes = grid.node_positions()
    active_nodes = _active_nodes(grid, element_dofs)
    node_low = nodes[active_nodes].min(axis=0)
    node_high = nodes[active_nodes].max(axis=0)
    forces = np.zeros(3 * len(nodes), dtype=float)

    for index, load in enumerate(load_case.get("loads") or []):
        context = f"load {load.get('name', index)!r}"
        mask = _region_mask(load.get("region"), nodes, (node_low, node_high), context)
        mask &= active_nodes
        chosen = np.nonzero(mask)[0]
        if not len(chosen):
            raise StressError(f"{context} selects no node of the solid.")
        force = np.asarray(load.get("force_n") or [0.0, 0.0, 0.0], dtype=float)
        torque = np.asarray(load.get("torque_n_mm") or [0.0, 0.0, 0.0], dtype=float)
        share = force / len(chosen)
        for axis in range(3):
            forces[3 * chosen + axis] += share[axis]
        if np.any(torque):
            points = nodes[chosen]
            arms = points - points.mean(axis=0)[None, :]
            gram = arms.T @ arms
            matrix = np.trace(gram) * np.eye(3) - gram
            if np.linalg.matrix_rank(
                    matrix, tol=1e-9 * max(float(np.trace(gram)), 1.0)) < 3:
                raise StressError(
                    f"{context} applies a torque over nodes that are collinear "
                    "or coincident, which cannot carry a couple. Widen the "
                    "region."
                )
            couple = np.cross(np.linalg.solve(matrix, torque)[None, :], arms)
            for axis in range(3):
                forces[3 * chosen + axis] += couple[:, axis]

    gravity = load_case.get("gravity_m_s2")
    if gravity:
        vector = np.asarray(gravity, dtype=float)
        cell_mass_kg = grid.element_volume_mm3 * 1.0e-9 * material.density_kg_m3
        nodal = cell_mass_kg * vector / 8.0
        corners = element_dofs[:, ::3].ravel() // 3
        for axis in range(3):
            np.add.at(forces, 3 * corners + axis, np.repeat(nodal[axis], corners.size))
    return forces


@dataclass
class Prepared:
    """Everything about one grid and one load case a density cannot change.

    Split out of ``solve`` for S2 (ADR-143). A SIMP run solves the *same*
    system a hundred times over with a different density vector each time,
    and every one of these is identical at all hundred iterations: the
    element matrix, the pruned occupancy, the node numbering, the held
    degrees of freedom, the assembled force vector and the free-DOF index.
    Building them once is most of what makes an iteration 0.8 s rather than
    several.

    S0's ``solve`` is now the thin wrapper over this that it always was in
    effect, and its behaviour is unchanged -- which is checked by the fact
    that S0's tests were not touched to accommodate the split.
    """

    grid: Grid
    material: Material
    element: Element
    element_indices: np.ndarray     # (ne, 3) grid coordinates of solid cells
    element_dofs: np.ndarray        # (ne, 24)
    forces: np.ndarray              # (3 * nodes,)
    fixed: np.ndarray               # (3 * nodes,) bool
    free: np.ndarray                # indices into the full dof vector
    support_adjacent: np.ndarray    # (ne,) bool
    incompatible: bool = True
    warnings: list[str] = field(default_factory=list)

    @property
    def total_dofs(self) -> int:
        return len(self.forces)

    @property
    def element_count(self) -> int:
        return len(self.element_dofs)


#: SIMP's floor under an element's stiffness, as a fraction of the solid
#: material's. It is not cosmetic: at exactly zero a void element makes the
#: stiffness matrix singular, and the whole reason a converged SIMP result
#: is *one* connected structure is that nothing is ever quite disconnected
#: while the optimiser is deciding.
_VOID_STIFFNESS = 1.0e-9


def simp_scale(density: np.ndarray, penalty: float,
               void_stiffness: float = _VOID_STIFFNESS) -> np.ndarray:
    """How much of the solid stiffness an element of this density carries.

    ``E(rho) / E_0 = e_min + (1 - e_min) * rho**p`` -- the "modified SIMP"
    interpolation, which differs from the bare ``rho**p`` only in keeping
    the floor out of the penalisation, so that the gradient at ``rho = 0``
    is finite for ``p > 1``.

    This is one function rather than an expression written twice because
    :func:`simp_scale_gradient` has to be its exact derivative. A sensitivity
    that disagrees with the objective it is meant to differentiate is *the*
    SIMP bug, and it is invisible: the run still converges, to the wrong
    shape.
    """

    return void_stiffness + (1.0 - void_stiffness) * np.asarray(
        density, dtype=float) ** penalty


def simp_scale_gradient(density: np.ndarray, penalty: float,
                        void_stiffness: float = _VOID_STIFFNESS) -> np.ndarray:
    """``d(simp_scale)/d(rho)``, and nothing else, ever."""

    return penalty * (1.0 - void_stiffness) * np.asarray(
        density, dtype=float) ** (penalty - 1.0)


def prepare(grid: Grid, material: Material, load_case: dict[str, Any], *,
            incompatible: bool = True) -> Prepared:
    """Everything up to the assembly: the part that a density cannot change."""

    warnings: list[str] = []
    element = build_element(grid.spacing, material, incompatible=incompatible)
    nodes = grid.node_positions()

    supports = load_case.get("supports") or []
    if not supports:
        raise StressError(
            "The load case declares no `supports`. An unheld part has six "
            "rigid-body modes and no stress."
        )

    solid = np.stack(np.nonzero(grid.occupancy), axis=1)
    if not len(solid):
        raise StressError(
            "The voxelisation found no solid cells. Either the element size "
            "is larger than the part or the tessellation is not closed."
        )
    all_ids = _node_ids(solid, grid.shape)
    active_nodes = np.zeros(len(nodes), dtype=bool)
    active_nodes[all_ids.ravel()] = True

    # A region is measured against **the part**, not against the grid the
    # part was voxelised onto. The grid is padded by a cell so that the fill
    # has somewhere to be outside, and a `face` region resolved against the
    # padded extent would land in that empty shell -- which is the first
    # thing this got wrong, and failed loudly rather than quietly only
    # because nothing was selected at all.
    node_low = nodes[active_nodes].min(axis=0)
    node_high = nodes[active_nodes].max(axis=0)

    # Which cells a support touches -- both for pruning and for the report's
    # "away from the supports" peak, which is the number that is not the
    # clamp's own stress singularity.
    fixed_node = np.zeros((len(nodes), 3), dtype=bool)
    support_nodes = np.zeros(len(nodes), dtype=bool)
    for index, support in enumerate(supports):
        mask = _region_mask(support.get("region"), nodes, (node_low, node_high),
                            f"support {support.get('name', index)!r}")
        axes = support.get("axes") or ["x", "y", "z"]
        columns = [{"x": 0, "y": 1, "z": 2}[str(axis).lower()] for axis in axes]
        for column in columns:
            fixed_node[mask, column] = True
        support_nodes |= mask

    supported_cells = np.zeros_like(grid.occupancy)
    touching = support_nodes[all_ids].any(axis=1)
    supported_cells[tuple(solid[touching].T)] = True
    if not touching.any():
        raise StressError(
            "No support region reaches a node of the solid. Check that the "
            "region is expressed in the same millimetres as the solid."
        )

    reachable, dropped = _prune_unsupported(grid, supported_cells)
    if dropped:
        warnings.append(
            f"{dropped} solid cells are not connected to any support and were "
            "dropped; they carry no load and would make the system singular."
        )
        grid = Grid(grid.origin, grid.spacing, grid.shape, reachable)
        solid = np.stack(np.nonzero(grid.occupancy), axis=1)
        all_ids = _node_ids(solid, grid.shape)
        active_nodes = np.zeros(len(nodes), dtype=bool)
        active_nodes[all_ids.ravel()] = True

    element_dofs = (3 * all_ids[:, :, None] + np.arange(3)[None, None, :]).reshape(-1, 24)

    fixed = (fixed_node & active_nodes[:, None]).ravel()
    if int(fixed.sum()) < 6:
        warnings.append(
            f"Only {int(fixed.sum())} degrees of freedom are held, which "
            "cannot suppress all six rigid-body modes. Read the residual."
        )

    forces = assemble_forces(grid, material, load_case, element_dofs)
    free = np.nonzero(active_nodes.repeat(3) & ~fixed)[0]

    return Prepared(
        grid=grid,
        material=material,
        element=element,
        element_indices=solid,
        element_dofs=element_dofs,
        forces=forces,
        fixed=fixed,
        free=free,
        support_adjacent=support_nodes[all_ids].any(axis=1),
        incompatible=incompatible,
        warnings=warnings,
    )


def assemble_stiffness(prepared: Prepared, density: np.ndarray | None = None,
                       penalty: float = 1.0):
    """The reduced stiffness matrix, optionally under a SIMP density.

    **This one line is the whole of what makes the S0 solver a SIMP solver.**
    Without a density every element contributes the same 24x24 matrix, so the
    assembly tiles it; with one, each element's contribution is scaled by
    ``simp_scale(rho, p)`` before it is scattered.

    It is correct with C3D8I -- the incompatible-mode element whose internal
    degrees of freedom are condensed out at element level -- because **static
    condensation commutes with a uniform scaling of the element energy.**
    Scaling every block of the element's energy by ``s`` scales ``Kcc``,
    ``Kci`` and ``Kii`` alike, and the condensed matrix
    ``s*Kcc - (s*Kci)(s*Kii)^-1(s*Kci)^T`` is exactly ``s`` times the
    unscaled one. That is the property ADR-141 claimed when it chose the
    element and S0 already relied on; S2 is where it is cashed in.
    """

    import scipy.sparse as sparse

    element_dofs = prepared.element_dofs
    total_dofs = prepared.total_dofs
    flat = prepared.element.stiffness.ravel()
    if density is not None:
        scale = simp_scale(np.asarray(density, dtype=float).ravel(), penalty)
        if len(scale) != len(element_dofs):
            raise StressError(
                f"The density vector has {len(scale)} entries and the grid has "
                f"{len(element_dofs)} elements."
            )
    else:
        scale = None

    matrix = sparse.csr_matrix((total_dofs, total_dofs), dtype=float)
    # Chunked so the triplet arrays stay bounded no matter how many elements
    # the grid has.
    chunk = max(1, 4_000_000 // 576)
    for start in range(0, len(element_dofs), chunk):
        block = element_dofs[start:start + chunk]
        rows = np.repeat(block, 24, axis=1).ravel()
        cols = np.tile(block, (1, 24)).ravel()
        if scale is None:
            data = np.tile(flat, len(block))
        else:
            data = (scale[start:start + chunk, None] * flat[None, :]).ravel()
        matrix = matrix + sparse.coo_matrix(
            (data, (rows, cols)), shape=(total_dofs, total_dofs)
        ).tocsr()

    free = prepared.free
    return matrix[free][:, free].tocsc()


def solve_system(prepared: Prepared, *, density: np.ndarray | None = None,
                 penalty: float = 1.0, guess: np.ndarray | None = None,
                 solver: str = "auto", recover_stress: bool = True) -> Result:
    """Assemble under a density, solve, and recover stress.

    ``density`` is ``None`` for S0 -- every solid element is solid -- and a
    per-element value in ``[0, 1]`` for S2. ``guess`` is the previous
    iteration's free-DOF solution: densities move slowly under an
    optimality-criteria update, so the previous displacement is a good
    starting point and warm-starting CG is the standard SIMP win.
    """

    import scipy.sparse.linalg as splinalg

    warnings = list(prepared.warnings)
    grid = prepared.grid
    material = prepared.material
    element = prepared.element
    element_dofs = prepared.element_dofs
    free = prepared.free
    fixed = prepared.fixed

    reduced = assemble_stiffness(prepared, density, penalty)
    rhs = prepared.forces[free]

    started = time.monotonic()
    method = solver
    iterations = None
    if method == "auto":
        method = "direct" if len(free) <= _DIRECT_DOF_LIMIT else "cg"
    if method == "direct":
        try:
            solution = splinalg.splu(reduced).solve(rhs)
        except (RuntimeError, ValueError) as error:
            warnings.append(f"The direct factorisation failed ({error}); "
                            "the solve fell back to conjugate gradients.")
            method = "cg"
    if method == "cg":
        diagonal = reduced.diagonal()
        diagonal[diagonal == 0.0] = 1.0
        preconditioner = splinalg.LinearOperator(
            reduced.shape, matvec=lambda vector: vector / diagonal)
        counter = {"n": 0}

        def _count(_x: Any) -> None:
            counter["n"] += 1

        x0 = None
        if guess is not None:
            x0 = np.asarray(guess, dtype=float).ravel()
            if len(x0) != len(free):
                raise StressError(
                    f"The starting guess has {len(x0)} entries and the free "
                    f"system has {len(free)}."
                )
        solution, info = splinalg.cg(
            reduced, rhs, x0=x0, rtol=_CG_TOLERANCE, atol=0.0,
            maxiter=_CG_ITERATION_FACTOR * len(free),
            M=preconditioner, callback=_count,
        )
        iterations = counter["n"]
        if info:
            warnings.append(
                f"Conjugate gradients stopped with info={info} after "
                f"{iterations} iterations. Read the residual before trusting "
                "the numbers."
            )
    wall = time.monotonic() - started

    rhs_scale = float(np.linalg.norm(rhs)) or 1.0
    residual = float(np.linalg.norm(reduced @ solution - rhs) / rhs_scale)
    if residual > 1e-6:
        warnings.append(
            f"The solve's relative residual is {residual:.3g}, which is too "
            "large for the answer to be read as a converged linear solution."
        )

    displacement = np.zeros(prepared.total_dofs, dtype=float)
    displacement[free] = solution
    displacement = displacement.reshape(-1, 3)

    # Stress recovery, at the eight Gauss points, per element. Skipped by the
    # SIMP loop, which wants compliance and a sensitivity and would pay for
    # eight strain evaluations per element per iteration to get neither.
    #
    # Under a density this reports the stress the **solid material** would
    # carry at the recovered strain, not that stress scaled by ``rho**p``.
    # That is the quantity a stress constraint is written against; it is also
    # meaningless in a cell that has converged to void, which is one of the
    # reasons S2 minimises compliance and leaves stress to the S0 run on the
    # extracted shape.
    d = material.elasticity_matrix()
    if recover_stress:
        element_displacement = displacement.reshape(-1)[element_dofs]  # (ne, 24)
        internal = element_displacement @ element.recover.T            # (ne, 9)
        worst = np.zeros(len(element_dofs), dtype=float)
        for point in range(8):
            strain = (element_displacement @ element.corner_strain[point].T
                      + internal @ element.internal_strain[point].T)
            stress = strain @ d.T
            worst = np.maximum(worst, von_mises(stress))
        centroid = (element_displacement @ element.centroid_strain.T) @ d.T
    else:
        worst = np.zeros(len(element_dofs), dtype=float)
        centroid = np.zeros((len(element_dofs), 6), dtype=float)

    return Result(
        grid=grid,
        material=material,
        displacement=displacement,
        element_indices=prepared.element_indices,
        element_dofs=element_dofs,
        von_mises_mpa=worst,
        centroid_stress_mpa=centroid,
        support_adjacent=prepared.support_adjacent,
        fixed_dofs=fixed,
        solver={
            "method": method,
            "iterations": iterations,
            "relative_residual": residual,
            "free_dofs": int(len(free)),
            "fixed_dofs": int(fixed.sum()),
            "non_zeros": int(reduced.nnz),
            "element": "c3d8i" if prepared.incompatible else "c3d8",
            "wall_time_s": wall,
        },
        warnings=warnings,
    )


def solve(grid: Grid, material: Material, load_case: dict[str, Any], *,
          solver: str = "auto", incompatible: bool = True) -> Result:
    """Assemble, constrain, solve and recover stress on one grid.

    S0's entry point, and now the two-line wrapper it always was in effect.
    Everything it used to do in one function is in :func:`prepare` and
    :func:`solve_system`, split where a SIMP iteration needs the seam.
    """

    return solve_system(
        prepare(grid, material, load_case, incompatible=incompatible),
        solver=solver,
    )


def von_mises(stress: np.ndarray) -> np.ndarray:
    """von Mises from ``[sxx, syy, szz, sxy, syz, szx]`` rows."""

    sxx, syy, szz, sxy, syz, szx = (stress[:, index] for index in range(6))
    return np.sqrt(
        0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
        + 3.0 * (sxy ** 2 + syz ** 2 + szx ** 2)
    )


# ---------------------------------------------------------------------------
# The sweep, and the report.
# ---------------------------------------------------------------------------


def _percentile(values: np.ndarray, fraction: float) -> float:
    return float(np.percentile(values, fraction))


def _level_record(result: Result) -> dict[str, Any]:
    return {
        "element_mm": float(result.grid.spacing.mean()),
        "spacing_mm": [float(value) for value in result.grid.spacing],
        "elements": int(len(result.element_indices)),
        "free_dofs": int(result.solver["free_dofs"]),
        "peak_von_mises_mpa": result.peak_von_mises_mpa,
        "peak_away_from_supports_mpa": result.peak_away_from_supports_mpa,
        "p99_von_mises_mpa": _percentile(result.von_mises_mpa, 99.0),
        "p95_von_mises_mpa": _percentile(result.von_mises_mpa, 95.0),
        "max_displacement_mm": result.max_displacement_mm,
        "volume_mm3": result.volume_mm3(),
        "relative_residual": float(result.solver["relative_residual"]),
        "wall_time_s": float(result.solver["wall_time_s"]),
    }


def _convergence(levels: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """What settled between the two finest grids, and what did not.

    Displacement is an integral of the solution and settles; peak stress is
    a point value and at a re-entrant corner or a clamped face it is a
    genuine singularity, so it does **not** settle -- it grows with every
    refinement. Saying so is the point. When the peak has not settled, the
    number to read is ``p99``, which is a volume statistic rather than the
    value of a function that does not have one there.
    """

    if len(levels) < 2:
        return {
            "levels": list(levels),
            "converged": False,
            "note": "A single grid is not a measurement; run at least two.",
        }
    coarse, fine = levels[-2], levels[-1]

    def _change(key: str) -> float:
        reference = abs(fine[key]) or 1.0
        return abs(fine[key] - coarse[key]) / reference

    displacement_change = _change("max_displacement_mm")
    peak_change = _change("peak_von_mises_mpa")
    p99_change = _change("p99_von_mises_mpa")
    return {
        "levels": list(levels),
        "displacement_change_fraction": displacement_change,
        "peak_change_fraction": peak_change,
        "p99_change_fraction": p99_change,
        "displacement_converged": displacement_change <= _CONVERGENCE_FRACTION,
        "peak_converged": peak_change <= _CONVERGENCE_FRACTION,
        "p99_converged": p99_change <= _CONVERGENCE_FRACTION,
        "converged": (displacement_change <= _CONVERGENCE_FRACTION
                      and p99_change <= _CONVERGENCE_FRACTION),
        "tolerance_fraction": _CONVERGENCE_FRACTION,
    }


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyse(solid: Path, load_case: dict[str, Any], *, element_mm: float | None = None,
            levels: int = _DEFAULT_LEVELS, solver: str = "auto",
            incompatible: bool = True,
            note: Any = None) -> dict[str, Any]:
    """The whole of S0: read, voxelise, solve at several grids, report."""

    material = Material.from_mapping(load_case.get("material"))
    triangles, exact_volume = read_solid(solid)
    tessellated_volume = mesh_volume_mm3(triangles)
    warnings: list[str] = []
    if tessellated_volume <= 0.0:
        raise StressError(
            f"{solid.name} tessellates to a volume of {tessellated_volume:.4g} "
            "mm^3. A closed surface with outward normals gives a positive "
            "number, so this is either inside out or not closed, and filling "
            "it would produce a part that is not the part."
        )

    extent = triangles.reshape(-1, 3).ptp(axis=0)
    if element_mm is None:
        # Twenty elements across the smallest dimension that is not
        # degenerate: enough for bending to be resolved by the incompatible
        # modes, small enough to be a laptop-second at the coarsest level.
        element_mm = float(max(extent[extent > 0].min() / 20.0, 1e-6))
        warnings.append(
            f"No element size was declared, so the sweep starts at "
            f"{element_mm:.4g} mm -- one twentieth of the part's smallest "
            "extent. Declare `--element-mm` for a comparable number."
        )

    if levels < 2:
        warnings.append(
            "This ran on a single grid. A voxel mesh overstates stress at a "
            "stair-stepped boundary, so a single-grid peak is an estimate "
            "and not a measurement."
        )

    records: list[dict[str, Any]] = []
    finest: Result | None = None
    for level in range(max(1, levels)):
        size = element_mm * (_REFINEMENT_RATIO ** level)
        grid = voxelise(triangles, size)
        result = solve(grid, material, load_case, solver=solver,
                       incompatible=incompatible)
        records.append(_level_record(result))
        warnings.extend(result.warnings)
        finest = result

    assert finest is not None
    convergence = _convergence(records)
    voxel_volume = finest.volume_mm3()
    reference_volume = exact_volume if exact_volume else tessellated_volume
    fill_error = abs(voxel_volume - reference_volume) / (abs(reference_volume) or 1.0)
    if fill_error > 0.05:
        warnings.append(
            f"The voxelisation is {fill_error * 100:.1f}% off the solid's own "
            "volume, so the grid is too coarse for the shape it is standing "
            "in for."
        )

    yield_mpa = material.yield_strength_mpa
    peak = finest.peak_von_mises_mpa
    p99 = _percentile(finest.von_mises_mpa, 99.0)
    away = finest.peak_away_from_supports_mpa

    return {
        "schema": REPORT_SCHEMA,
        "input": {
            "solid": str(solid),
            "solid_sha256": _digest(solid),
            "triangles": int(len(triangles)),
            "note": note,
        },
        "material": {
            "name": material.name,
            "youngs_modulus_mpa": material.youngs_modulus_mpa,
            "poissons_ratio": material.poissons_ratio,
            "yield_strength_mpa": yield_mpa,
            "density_kg_m3": material.density_kg_m3,
        },
        "grid": {
            "element_mm": float(finest.grid.spacing.mean()),
            "spacing_mm": [float(value) for value in finest.grid.spacing],
            "shape": list(finest.grid.shape),
            "elements": int(len(finest.element_indices)),
            "origin_mm": [float(value) for value in finest.grid.origin],
        },
        "mass": {
            "voxel_volume_mm3": voxel_volume,
            "tessellated_volume_mm3": tessellated_volume,
            "exact_volume_mm3": exact_volume,
            "fill_error_fraction": fill_error,
            "mass_g": finest.mass_g(),
        },
        "result": {
            "peak_von_mises_mpa": peak,
            "peak_away_from_supports_mpa": away,
            "p99_von_mises_mpa": p99,
            "p95_von_mises_mpa": _percentile(finest.von_mises_mpa, 95.0),
            "max_displacement_mm": finest.max_displacement_mm,
            "safety_factor_peak": (yield_mpa / peak) if peak > 0 else None,
            "safety_factor_p99": (yield_mpa / p99) if p99 > 0 else None,
            "safety_factor_away_from_supports": (
                (yield_mpa / away) if away > 0 else None),
        },
        "solver": dict(finest.solver),
        "convergence": convergence,
        "warnings": sorted(set(warnings)),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "cadex_importable": _cadex_importable(),
    }


def _cadex_importable() -> bool:
    """Whether the engine is on this interpreter's path.

    Reported for the reason ``training/cadex_train.py`` reports it: this file
    must work with nothing but its own pinned dependencies, and a run where
    this comes back ``true`` did not prove that.
    """

    try:
        import CadexDynamics  # noqa: F401
    except Exception:
        return False
    return True


# ---------------------------------------------------------------------------
# The self-check: a cantilever against the answer engineering already knows.
# ---------------------------------------------------------------------------


def box_triangles(size_mm: Sequence[float],
                  origin_mm: Sequence[float] = (0.0, 0.0, 0.0)) -> np.ndarray:
    """A closed axis-aligned box as twelve outward triangles.

    Here rather than in the tests because the self-check and the tests want
    the same box, and a benchmark whose geometry is written twice is a
    benchmark that can disagree with itself.
    """

    low = np.asarray(origin_mm, dtype=float)
    high = low + np.asarray(size_mm, dtype=float)
    corners = np.array([[x, y, z] for z in (low[2], high[2])
                        for y in (low[1], high[1])
                        for x in (low[0], high[0])], dtype=float)
    quads = [
        (0, 2, 3, 1),  # z = low, normal -z
        (4, 5, 7, 6),  # z = high, normal +z
        (0, 1, 5, 4),  # y = low, normal -y
        (2, 6, 7, 3),  # y = high, normal +y
        (0, 4, 6, 2),  # x = low, normal -x
        (1, 3, 7, 5),  # x = high, normal +x
    ]
    triangles = []
    for a, b, c, d in quads:
        triangles.append([corners[a], corners[b], corners[c]])
        triangles.append([corners[a], corners[c], corners[d]])
    return np.asarray(triangles, dtype=float)


def write_binary_stl(triangles: np.ndarray, path: Path) -> Path:
    """The tessellation this file reads, written by this file.

    Used by the self-check and by the CalculiX cross-check so that a
    benchmark's geometry travels as a file rather than as an assumption.
    """

    count = len(triangles)
    payload = bytearray(b"\0" * 80 + struct.pack("<I", count))
    for triangle in triangles:
        normal = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
        length = np.linalg.norm(normal)
        normal = normal / length if length else normal
        payload += struct.pack("<3f", *normal.astype(np.float32))
        for corner in triangle:
            payload += struct.pack("<3f", *np.asarray(corner, dtype=np.float32))
        payload += b"\0\0"
    path.write_bytes(bytes(payload))
    return path


def cantilever_case(*, length_mm: float = 100.0, height_mm: float = 10.0,
                    width_mm: float = 10.0, force_n: float = 10.0,
                    youngs_modulus_mpa: float = 3500.0,
                    poissons_ratio: float = 0.36) -> dict[str, Any]:
    """The benchmark, its closed form, and the load case that produces it.

    An end-loaded cantilever, fixed at ``x = 0`` and pushed down at
    ``x = L``. Timoshenko rather than Euler-Bernoulli, because at the
    length-to-height ratios a printed bracket actually has, the shear term
    is several percent and leaving it out would put a real error inside the
    tolerance a test is checking.
    """

    inertia = width_mm * height_mm ** 3 / 12.0
    area = width_mm * height_mm
    shear_modulus = youngs_modulus_mpa / (2.0 * (1.0 + poissons_ratio))
    bending = force_n * length_mm ** 3 / (3.0 * youngs_modulus_mpa * inertia)
    shear = force_n * length_mm / (shear_modulus * area * 5.0 / 6.0)
    return {
        "size_mm": [length_mm, width_mm, height_mm],
        "force_n": force_n,
        "tip_deflection_mm": bending + shear,
        "bending_only_mm": bending,
        # Midspan, deliberately: the peak at the clamp is a singularity the
        # theory does not have, so a benchmark that checked it would be
        # checking the mesh rather than the solver.
        "midspan_bending_stress_mpa": (
            force_n * (length_mm / 2.0) * (height_mm / 2.0) / inertia),
        "second_moment_mm4": inertia,
        "load_case": {
            "schema": LOAD_CASE_SCHEMA,
            "material": {
                "name": "self-check",
                "youngs_modulus_mpa": youngs_modulus_mpa,
                "poissons_ratio": poissons_ratio,
                "yield_strength_mpa": 50.0,
                "density_kg_m3": 1240.0,
            },
            "supports": [
                {"name": "root",
                 "region": {"face": {"axis": "x", "at": "min", "depth_mm": 1e-6}}}
            ],
            "loads": [
                {"name": "tip",
                 "region": {"face": {"axis": "x", "at": "max", "depth_mm": 1e-6}},
                 "force_n": [0.0, 0.0, -force_n]}
            ],
        },
    }


def run_self_check(element_mm: float = 2.5, levels: int = 3) -> dict[str, Any]:
    """The cantilever, both elements, against the closed form.

    Runs the locking element beside the incompatible-mode one on purpose:
    the ratio between them is the measurement that says why the element
    choice is not a detail, and a number is worth more than the paragraph
    at the top of this file.
    """

    import tempfile

    case = cantilever_case()
    with tempfile.TemporaryDirectory() as directory:
        path = write_binary_stl(box_triangles(case["size_mm"]),
                                Path(directory) / "cantilever.stl")
        rich = analyse(path, case["load_case"], element_mm=element_mm,
                       levels=levels, note="self-check: c3d8i")
        locking = analyse(path, case["load_case"], element_mm=element_mm,
                          levels=1, incompatible=False,
                          note="self-check: c3d8, for comparison")

    tip = rich["result"]["max_displacement_mm"]
    closed = case["tip_deflection_mm"]
    return {
        "schema": "cadex-analysis-self-check-v1",
        "closed_form": {
            "tip_deflection_mm": closed,
            "bending_only_mm": case["bending_only_mm"],
            "midspan_bending_stress_mpa": case["midspan_bending_stress_mpa"],
        },
        "c3d8i": {
            "tip_deflection_mm": tip,
            "error_fraction": abs(tip - closed) / closed,
            "levels": rich["convergence"]["levels"],
            "converged": rich["convergence"]["converged"],
        },
        "c3d8": {
            "tip_deflection_mm": locking["result"]["max_displacement_mm"],
            "error_fraction": abs(
                locking["result"]["max_displacement_mm"] - closed) / closed,
            "note": ("The fully-integrated element, at the same grid. It "
                     "shear-locks, and the gap is why the default is not it."),
        },
        "cadex_importable": _cadex_importable(),
    }


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def _load_case(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    schema = str(raw.get("schema") or "")
    if schema != LOAD_CASE_SCHEMA:
        raise StressError(
            f"{path.name} declares schema {schema!r}, and this reads "
            f"{LOAD_CASE_SCHEMA!r}."
        )
    return raw


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="cadex_stress.py",
        description="Peak stress and a safety factor for one declared load.")
    parser.add_argument("solid", nargs="?", type=Path,
                        help="the part: .stl, .ply, .obj, or .step")
    parser.add_argument("--load-case", type=Path,
                        help=f"a {LOAD_CASE_SCHEMA} JSON file")
    parser.add_argument("--element-mm", type=float, default=None,
                        help="the coarsest grid; the sweep refines from here")
    parser.add_argument("--refine", type=int, default=_DEFAULT_LEVELS,
                        help="how many grids to run (2 or more is a measurement)")
    parser.add_argument("--solver", choices=("auto", "direct", "cg"), default="auto")
    parser.add_argument("--element", choices=("c3d8i", "c3d8"), default="c3d8i",
                        help="c3d8 shear-locks in bending and is here to be measured")
    parser.add_argument("--out", type=Path, default=None,
                        help="also write the report here")
    parser.add_argument("--self-check", action="store_true",
                        help="run the cantilever benchmark and report the error")
    options = parser.parse_args(list(argv[1:]))

    try:
        if options.self_check:
            report = run_self_check()
        else:
            if options.solid is None or options.load_case is None:
                parser.error("a solid and --load-case are required")
            report = analyse(
                options.solid, _load_case(options.load_case),
                element_mm=options.element_mm, levels=options.refine,
                solver=options.solver, incompatible=options.element == "c3d8i",
            )
    except StressError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2

    for warning in report.get("warnings", []):
        print(f"warning: {warning}", file=sys.stderr)
    if options.out:
        options.out.write_text(json.dumps(report, indent=2, sort_keys=True),
                               encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
