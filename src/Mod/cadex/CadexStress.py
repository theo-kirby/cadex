# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A linear-elastic stress solve, in-engine, on a structured hex grid (ADR-145).

**This module is staged into the sandboxed worker by filename and is never
imported by ``cadexd``.** That is the same mechanism that keeps 53 MB of
mujoco out of a service whose job is reading NDJSON off a pipe (ADR-077,
ADR-109), applied again for the same reason: ``numpy`` and ``scipy`` are
already in the payload, but a service that never solves anything should not
import them to find that out. ``DECLARED_ENGINE_MODULES`` does not name this
file, and ``test_engine_purity_guardrails`` asserts it stays that way.

It imports FreeCAD nothing at all. The shape work -- resolving an ADR-029
selector to faces, tessellating them -- is ``cadex_part_worker``'s, and what
arrives here is triangles and point clouds. That is not tidiness: it is what
makes this file the *same kind of thing* as ``analysis/cadex_stress.py`` and
therefore comparable to it, which is the whole basis for trusting the number
it produces.

**Two implementations, pinned equal by a test.** ``analysis/`` may not import
the engine and the engine may not import ``analysis/`` -- both test-enforced,
ADR-141 and ADR-084. So the algorithm is written twice, and
``test_part_stress`` solves the same cantilever on the same grid with the
same assembled force vector through both and requires them to agree. This is
exactly the ``encode_policy`` / ``cadex_train.py`` arrangement, and it is the
right answer rather than a compromise: a number the engine computes about a
part is worth what an independent implementation says it is worth.

**The element is C3D8I**, for the reason ADR-141 measured: a fully integrated
trilinear hex shear-locks in bending and reports a part several times stiffer
than it is -- wrong in the direction that flatters it. Wilson incompatible
modes, statically condensed at element level. Every element of a structured
grid is geometrically identical, so the condensed 24x24 matrix is computed
once.

**It publishes p99, not the peak, as the safety factor's denominator.**
ADR-141 measured that peak von Mises at a clamped face does not converge and
must not -- it is a genuine singularity and grows with every refinement for
ever. An output that published a peak safety factor would be lying. Both
numbers travel; only one carries the verdict.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

#: The most elements one declared solve may spend. `element_mm` is a
#: budget the script declares, and a script that declares a budget it cannot
#: afford gets a refusal naming the number rather than a rebuild that hangs.
#: Sized from measurement: 60k elements is about 200k free degrees of
#: freedom, which Jacobi-preconditioned CG solves in roughly four seconds on
#: an M-series laptop. `assembly.simulation` is the precedent for an output
#: that is expensive on every rebuild; the difference is that this one states
#: its ceiling.
MAX_ELEMENTS = 60_000

#: Below this many free degrees of freedom a direct factorisation is cheaper
#: than a few hundred sparse mat-vecs. Above it, CG. The measurement behind
#: the number is in ADR-143: at 21.8k dofs the direct solve is 3x slower and
#: at 47k it is 11x, so the limit belongs far lower than it looks.
_DIRECT_DOF_LIMIT = 10_000

_CG_TOLERANCE = 1.0e-10
_CG_ITERATION_FACTOR = 40

#: Corner order inside one element, ``n = i + 2j + 4k``. Everything
#: downstream reads this rather than re-deriving an ordering of its own --
#: and ``analysis/cadex_stress.py`` uses the identical one, which is what
#: lets the two implementations be compared element by element.
_CORNER_SIGNS = tuple(
    (xi, eta, zeta)
    for zeta in (-1.0, 1.0)
    for eta in (-1.0, 1.0)
    for xi in (-1.0, 1.0)
)

_GAUSS = 1.0 / math.sqrt(3.0)


class StressError(ValueError):
    """A refusal with a sentence a script author can act on."""

    def __init__(self, message: str, *, correction: str = "") -> None:
        super().__init__(message)
        self.details = {"stage": "stress", "correction": correction}


# ---------------------------------------------------------------------------
# The element.
# ---------------------------------------------------------------------------


def elasticity_matrix(youngs_modulus_mpa: float, poissons_ratio: float):
    """The 6x6 isotropic D in engineering-shear order.

    ``[sxx, syy, szz, sxy, syz, szx]`` -- the order ``_strain_matrix`` builds
    and the order ``analysis/cadex_stress.py`` builds, so the two can be
    compared component by component and not only on von Mises.
    """

    import numpy as np

    nu = float(poissons_ratio)
    lam = youngs_modulus_mpa * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))
    mu = youngs_modulus_mpa / (2.0 * (1.0 + nu))
    d = np.zeros((6, 6), dtype=float)
    d[:3, :3] = lam
    d[0, 0] = d[1, 1] = d[2, 2] = lam + 2.0 * mu
    d[3, 3] = d[4, 4] = d[5, 5] = mu
    return d


def _strain_matrix(gradients):
    import numpy as np

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


def _corner_gradients(natural, spacing):
    import numpy as np

    xi, eta, zeta = natural
    signs = np.asarray(_CORNER_SIGNS, dtype=float)
    gradients = np.empty((8, 3), dtype=float)
    gradients[:, 0] = 0.125 * signs[:, 0] * (1 + signs[:, 1] * eta) * (1 + signs[:, 2] * zeta)
    gradients[:, 1] = 0.125 * signs[:, 1] * (1 + signs[:, 0] * xi) * (1 + signs[:, 2] * zeta)
    gradients[:, 2] = 0.125 * signs[:, 2] * (1 + signs[:, 0] * xi) * (1 + signs[:, 1] * eta)
    return gradients * (2.0 / spacing)[None, :]


def _incompatible_gradients(natural, spacing):
    """Gradients of ``1 - xi^2``, ``1 - eta^2`` and ``1 - zeta^2``.

    Each integrates to zero over the element, which is why the element still
    passes the constant-strain patch test with the modes switched on.
    """

    import numpy as np

    gradients = np.zeros((3, 3), dtype=float)
    for axis in range(3):
        gradients[axis, axis] = -2.0 * natural[axis]
    return gradients * (2.0 / spacing)[None, :]


def build_element(spacing, d):
    """The one element a structured grid needs: condensed stiffness and recovery.

    Returns ``(stiffness, recover, corner_strain, internal_strain)``. Every
    element of the grid is this one translated, so it is computed once and
    the assembly is a single vectorised scatter rather than a loop.
    """

    import numpy as np

    spacing = np.asarray(spacing, dtype=float)
    det = float(np.prod(spacing)) / 8.0
    points = [
        np.array([xi, eta, zeta], dtype=float)
        for zeta in (-_GAUSS, _GAUSS)
        for eta in (-_GAUSS, _GAUSS)
        for xi in (-_GAUSS, _GAUSS)
    ]
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
        kci += bc.T @ d @ bi * det
        kii += bi.T @ d @ bi * det

    recover = -np.linalg.solve(kii, kci.T)
    stiffness = kcc + kci @ recover
    return (
        0.5 * (stiffness + stiffness.T),
        recover,
        corner_strain,
        internal_strain,
    )


# ---------------------------------------------------------------------------
# Voxelisation: the same scanline parity fill, and the same two defences.
# ---------------------------------------------------------------------------


def voxelise(triangles, element_mm: float):
    """Fill a closed triangle soup onto a structured grid.

    A ray up +z through each cell centre, counting crossings: a cell is solid
    when an odd number of triangles lie below it. Two defences against the
    one case parity gets wrong -- a ray meeting an edge two triangles share,
    and therefore counted twice:

    * the sample points are nudged off the grid lines by a **different**
      irrational fraction of a cell on each axis. A single shared fraction
      leaves every point on the ``x = y`` diagonal on it, and a cap
      tessellated as a triangle fan then loses its whole diagonal -- a 4.5%
      volume error that ADR-141 measured the hard way;
    * crossings coinciding within a fraction of a nanometre collapse to one,
      because a ray through a shared edge crosses the surface once and both
      triangles report the same height. That one is exact where the nudge is
      only unlikely.

    The grid is **fitted to the bounding box**: ``element_mm`` sets how many
    cells go across each extent and the cell size is that extent divided by
    that count. Centre-sampled voxelisation of a 10 mm bar at 1.875 mm keeps
    five cells and throws away 6% of its height, and a beam's stiffness goes
    as the cube of its height.
    """

    import numpy as np

    if element_mm <= 0.0:
        raise StressError("`element_mm` must be positive.")
    flat = triangles.reshape(-1, 3)
    low = flat.min(axis=0)
    high = flat.max(axis=0)
    extent = high - low
    counts = np.maximum(
        np.rint(np.where(extent > 0.0, extent, element_mm) / float(element_mm)), 1.0
    )
    spacing = np.where(extent > 0.0, extent / counts, float(element_mm))
    nx, ny, nz = (int(value) for value in counts)

    jitter = spacing * np.array(
        [
            (math.sqrt(2.0) - 1.0) * 0.037,
            (math.sqrt(3.0) - 1.0) * 0.041,
            (math.sqrt(5.0) - 2.0) * 0.043,
        ]
    )
    xs = low[0] + (np.arange(nx) + 0.5) * spacing[0] + jitter[0]
    ys = low[1] + (np.arange(ny) + 0.5) * spacing[1] + jitter[1]
    zs = low[2] + (np.arange(nz) + 0.5) * spacing[2] + jitter[2]

    crossings: dict[tuple[int, int], list[float]] = {}
    a = triangles[:, 0]
    ab = triangles[:, 1] - a
    ac = triangles[:, 2] - a
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
        qx = xs[i0:i1][:, None] - tri[0, 0]
        qy = ys[j0:j1][None, :] - tri[0, 1]
        det = denominator[index]
        u = (qx * ac[index, 1] - qy * ac[index, 0]) / det
        v = (qy * ab[index, 0] - qx * ab[index, 1]) / det
        inside = (u >= 0.0) & (v >= 0.0) & (u + v <= 1.0)
        if not inside.any():
            continue
        z = tri[0, 2] + u * ab[index, 2] + v * ac[index, 2]
        for local_i, local_j in zip(*np.nonzero(inside)):
            crossings.setdefault((i0 + int(local_i), j0 + int(local_j)), []).append(
                float(z[local_i, local_j])
            )

    occupancy = np.zeros((nx, ny, nz), dtype=bool)
    coincident = 1.0e-7 * float(spacing[2])
    for (i, j), hits in crossings.items():
        ordered = np.sort(np.asarray(hits))
        if len(ordered) > 1:
            ordered = ordered[np.concatenate(([True], np.diff(ordered) > coincident))]
        below = np.searchsorted(ordered, zs, side="left")
        occupancy[i, j] = (below % 2) == 1
    return low, spacing, (nx, ny, nz), occupancy


def node_positions(origin, spacing, shape):
    import numpy as np

    axes = [
        origin[axis] + np.arange(count + 1) * spacing[axis]
        for axis, count in enumerate(shape)
    ]
    grid = np.meshgrid(*axes, indexing="ij")
    return np.stack([value.ravel(order="F") for value in grid], axis=1)


def _node_ids(indices, shape):
    import numpy as np

    nx, ny, _ = shape
    corners = ((np.asarray(_CORNER_SIGNS, dtype=float) + 1.0) / 2.0).astype(int)
    ids = np.empty((len(indices), 8), dtype=np.int64)
    for corner in range(8):
        i = indices[:, 0] + corners[corner, 0]
        j = indices[:, 1] + corners[corner, 1]
        k = indices[:, 2] + corners[corner, 2]
        ids[:, corner] = i + (nx + 1) * (j + (ny + 1) * k)
    return ids


def _reachable_from(occupancy, seeds):
    """Solid cells a support can reach, face by face.

    An island of material with nothing holding it is a rigid-body mode, and a
    rigid-body mode is a singular stiffness matrix: a direct solve fails and
    an iterative one wanders. Dropping it is the only honest option, and the
    count goes in the report rather than into a log.
    """

    import numpy as np
    from collections import deque

    reachable = np.zeros_like(occupancy)
    queue = deque(zip(*np.nonzero(seeds)))
    for seed in queue:
        reachable[seed] = True
    nx, ny, nz = occupancy.shape
    neighbours = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    while queue:
        i, j, k = queue.popleft()
        for di, dj, dk in neighbours:
            a, b, c = i + di, j + dj, k + dk
            if 0 <= a < nx and 0 <= b < ny and 0 <= c < nz:
                if occupancy[a, b, c] and not reachable[a, b, c]:
                    reachable[a, b, c] = True
                    queue.append((a, b, c))
    return reachable


def _nodes_near(nodes, anchors, radius: float):
    """Which grid nodes lie within ``radius`` of a selected face's surface.

    The anchors are the face's own tessellation vertices, so this is how an
    **ADR-029 selector** becomes a set of held or loaded degrees of freedom.
    That is the design commitment: the boundary condition follows the face
    the script named, so it moves when a parameter moves the face and fails
    loudly, naming the selector, when a change removes it.
    """

    import numpy as np

    try:
        from scipy.spatial import cKDTree

        tree = cKDTree(anchors)
        return np.asarray(tree.query_ball_point(nodes, radius, return_length=True)) > 0
    except ImportError:  # pragma: no cover - scipy is in the payload
        mask = np.zeros(len(nodes), dtype=bool)
        for anchor in anchors:
            mask |= np.linalg.norm(nodes - anchor[None, :], axis=1) <= radius
        return mask


def von_mises(stress):
    import numpy as np

    sxx, syy, szz, sxy, syz, szx = (stress[:, index] for index in range(6))
    return np.sqrt(
        0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
        + 3.0 * (sxy ** 2 + syz ** 2 + szx ** 2)
    )


def assemble_forces(nodes, active, loads, radius):
    """The right-hand side one declared load set produces on one grid.

    Its own function because the comparison against ``analysis/`` needs the
    **same** vector: a cross-check that re-derived the loads would be
    comparing two readings of the declaration as well as two solvers, and a
    disagreement would not say which of the two was at fault.

    A total force is shared equally over the nodes the face selects. A torque
    lands as a couple -- solve ``A w = T`` for a spin field, where
    ``A = (sum |r|^2) I - sum r r^T`` over the arms from the region's own
    centroid, and set ``f_i = w x r_i``. That places the couple exactly and
    adds no net force.
    """

    import numpy as np

    forces = np.zeros(3 * len(nodes), dtype=float)
    touched = []
    for index, load in enumerate(loads):
        mask = _nodes_near(nodes, load["anchors"], radius) & active
        chosen = np.nonzero(mask)[0]
        if not len(chosen):
            raise StressError(
                f"load {index} selects a face that reaches no node of the "
                f"voxelised part. The grid is {radius * 2:.3g} mm across, "
                "which is coarser than the feature the load names; declare a "
                "smaller `element_mm`.",
                correction="Declare a smaller element_mm, or load a larger face.",
            )
        touched.append(len(chosen))
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
                matrix, tol=1e-9 * max(float(np.trace(gram)), 1.0)
            ) < 3:
                raise StressError(
                    f"load {index} applies a torque over nodes that are "
                    "collinear or coincident, which cannot carry a couple.",
                    correction="Name a face with area, or apply a force instead.",
                )
            couple = np.cross(np.linalg.solve(matrix, torque)[None, :], arms)
            for axis in range(3):
                forces[3 * chosen + axis] += couple[:, axis]
    return forces, touched


def analyse(
    triangles,
    *,
    element_mm: float,
    material: dict[str, Any],
    holds: Sequence[dict[str, Any]],
    loads: Sequence[dict[str, Any]],
    max_elements: int = MAX_ELEMENTS,
) -> dict[str, Any]:
    """One shape, one declared load case, one stress report.

    ``triangles`` is the shape's own tessellation; ``holds`` and ``loads``
    carry the tessellation vertices of the faces their selectors named. No
    FreeCAD object reaches this function, which is what makes it the same
    species of thing as the offboard solver it is checked against.
    """

    import time

    import numpy as np
    import scipy.sparse as sparse
    import scipy.sparse.linalg as splinalg

    started = time.monotonic()
    warnings: list[str] = []

    origin, spacing, shape, occupancy = voxelise(triangles, element_mm)
    element_count = int(occupancy.sum())
    if element_count < 1:
        raise StressError(
            f"An element size of {element_mm} mm voxelised this shape to no "
            "cells at all, so there is nothing to solve.",
            correction="Declare a smaller element_mm.",
        )
    if element_count > max_elements:
        raise StressError(
            f"An element size of {element_mm} mm puts {element_count} elements "
            f"in this shape, and one solve may spend {max_elements}. Declare "
            f"element_mm of about "
            f"{element_mm * (element_count / max_elements) ** (1.0 / 3.0):.3g} "
            "mm or larger.",
            correction="Declare a larger element_mm.",
        )

    nodes = node_positions(origin, spacing, shape)
    radius = 0.75 * float(np.max(spacing))

    solid = np.stack(np.nonzero(occupancy), axis=1)
    all_ids = _node_ids(solid, shape)
    active = np.zeros(len(nodes), dtype=bool)
    active[all_ids.ravel()] = True

    fixed_node = np.zeros((len(nodes), 3), dtype=bool)
    held_nodes = np.zeros(len(nodes), dtype=bool)
    for index, hold in enumerate(holds):
        mask = _nodes_near(nodes, hold["anchors"], radius) & active
        if not mask.any():
            raise StressError(
                f"hold {index} selects a face that reaches no node of the "
                "voxelised part; the grid is coarser than the feature it "
                "names.",
                correction="Declare a smaller element_mm, or hold a larger face.",
            )
        for axis in hold.get("axes") or (0, 1, 2):
            fixed_node[mask, int(axis)] = True
        held_nodes |= mask

    supported = np.zeros_like(occupancy)
    touching = held_nodes[all_ids].any(axis=1)
    supported[tuple(solid[touching].T)] = True
    reachable = _reachable_from(occupancy, supported)
    dropped = int(occupancy.sum() - reachable.sum())
    if dropped:
        warnings.append(
            f"{dropped} cells are not connected to anything held and were "
            "dropped; they carry no load and would make the system singular."
        )
        occupancy = reachable
        solid = np.stack(np.nonzero(occupancy), axis=1)
        all_ids = _node_ids(solid, shape)
        active = np.zeros(len(nodes), dtype=bool)
        active[all_ids.ravel()] = True

    element_dofs = (
        3 * all_ids[:, :, None] + np.arange(3)[None, None, :]
    ).reshape(-1, 24)
    fixed = (fixed_node & active[:, None]).ravel()
    if int(fixed.sum()) < 6:
        raise StressError(
            f"Only {int(fixed.sum())} degrees of freedom are held, which "
            "cannot suppress all six rigid-body modes, so the part would "
            "simply move rather than deform.",
            correction="Hold a face with area in all three axes.",
        )

    forces, loaded_counts = assemble_forces(nodes, active, list(loads), radius)
    total_force = float(np.linalg.norm(forces))
    if total_force <= 0.0:
        raise StressError(
            "Every declared load came to zero, so the part carries nothing "
            "and every stress in it is zero.",
            correction="Declare a non-zero force_n or torque_n_mm.",
        )

    d = elasticity_matrix(
        float(material["youngs_modulus_mpa"]), float(material["poissons_ratio"])
    )
    stiffness, recover, corner_strain, internal_strain = build_element(spacing, d)

    total_dofs = 3 * len(nodes)
    flat = stiffness.ravel()
    matrix = sparse.csr_matrix((total_dofs, total_dofs), dtype=float)
    chunk = max(1, 4_000_000 // 576)
    for start in range(0, len(element_dofs), chunk):
        block = element_dofs[start:start + chunk]
        rows = np.repeat(block, 24, axis=1).ravel()
        cols = np.tile(block, (1, 24)).ravel()
        matrix = matrix + sparse.coo_matrix(
            (np.tile(flat, len(block)), (rows, cols)),
            shape=(total_dofs, total_dofs),
        ).tocsr()

    free = np.nonzero(active.repeat(3) & ~fixed)[0]
    reduced = matrix[free][:, free].tocsc()
    rhs = forces[free]

    method = "direct" if len(free) <= _DIRECT_DOF_LIMIT else "cg"
    iterations = None
    if method == "direct":
        try:
            solution = splinalg.splu(reduced).solve(rhs)
        except (RuntimeError, ValueError) as error:
            warnings.append(
                f"The direct factorisation failed ({error}); the solve fell "
                "back to conjugate gradients."
            )
            method = "cg"
    if method == "cg":
        diagonal = reduced.diagonal()
        diagonal[diagonal == 0.0] = 1.0
        preconditioner = splinalg.LinearOperator(
            reduced.shape, matvec=lambda vector: vector / diagonal
        )
        counter = {"n": 0}

        def _count(_x: Any) -> None:
            counter["n"] += 1

        solution, info = splinalg.cg(
            reduced,
            rhs,
            rtol=_CG_TOLERANCE,
            atol=0.0,
            maxiter=_CG_ITERATION_FACTOR * len(free),
            M=preconditioner,
            callback=_count,
        )
        iterations = counter["n"]
        if info:
            warnings.append(
                f"Conjugate gradients stopped with info={info} after "
                f"{iterations} iterations; read `relative_residual` before "
                "trusting these numbers."
            )

    scale = float(np.linalg.norm(rhs)) or 1.0
    residual = float(np.linalg.norm(reduced @ solution - rhs) / scale)
    if residual > 1.0e-6:
        warnings.append(
            f"The solve's relative residual is {residual:.3g}, which is too "
            "large to read as a converged linear solution."
        )

    displacement = np.zeros(total_dofs, dtype=float)
    displacement[free] = solution
    displacement = displacement.reshape(-1, 3)

    element_displacement = displacement.reshape(-1)[element_dofs]
    internal = element_displacement @ recover.T
    worst = np.zeros(len(element_dofs), dtype=float)
    for point in range(8):
        strain = (
            element_displacement @ corner_strain[point].T
            + internal @ internal_strain[point].T
        )
        worst = np.maximum(worst, von_mises(strain @ d.T))

    held_adjacent = held_nodes[all_ids].any(axis=1)
    away = worst[~held_adjacent] if (~held_adjacent).any() else worst

    volume = float(len(solid)) * float(np.prod(spacing))
    yield_mpa = float(material["yield_strength_mpa"])
    peak = float(worst.max())
    p99 = float(np.percentile(worst, 99.0))
    peak_away = float(away.max())

    return {
        # The verdict, and it divides by p99. A peak safety factor would be
        # a number pretending to be a verdict: peak von Mises at a held face
        # is a genuine singularity and grows with every refinement for ever
        # (ADR-141). Both numbers travel; only one carries the verdict.
        "safety_factor": (yield_mpa / p99) if p99 > 0.0 else None,
        "p99_von_mises_mpa": p99,
        "peak_von_mises_mpa": peak,
        "peak_away_from_holds_mpa": peak_away,
        "max_displacement_mm": float(np.linalg.norm(displacement, axis=1).max()),
        "yield_strength_mpa": yield_mpa,
        "mass_g": volume * float(material["density_kg_m3"]) * 1.0e-6,
        "volume_mm3": volume,
        "grid": {
            "element_mm": float(np.mean(spacing)),
            "spacing_mm": [float(value) for value in spacing],
            "shape": [int(value) for value in shape],
            "elements": int(len(solid)),
            "dropped_cells": dropped,
        },
        "solver": {
            "method": method,
            "iterations": iterations,
            "relative_residual": residual,
            "free_dofs": int(len(free)),
            "held_dofs": int(fixed.sum()),
            "loaded_nodes": [int(value) for value in loaded_counts],
            "element": "c3d8i",
            "wall_time_s": float(time.monotonic() - started),
        },
        # A single grid is not a refinement study, and the report says so
        # rather than letting a number look more settled than it is. ADR-141
        # measured it: displacement and p99 converge, the peak does not.
        "note": (
            "One grid, one load case, linear elastic. `safety_factor` divides "
            "the yield strength by p99 von Mises, not by the peak: the peak at "
            "a held face is a stair-stepped singularity and does not converge. "
            "Run analysis/cadex_stress.py for a refinement sweep."
        ),
        "warnings": warnings,
    }
