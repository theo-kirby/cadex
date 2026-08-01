# SPDX-License-Identifier: LGPL-2.1-or-later

"""Isolated Mesh domain evaluation for the project worker.

Materializes validated mesh definitions with the native ``Mesh``/``MeshPart``
kernels: tessellation of part-domain shapes, mesh-asset import from the staged
``assets`` directory, native mesh set operations, and decimation.  Each mesh
output is exported as one binary artifact whose SHA-256 joins the project
content digest, and the returned facts let publication verify the applied
native state byte-for-byte against this isolated validation.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
import struct
from typing import Any

# Re-exported: the approximating-tree test moved to the API module so
# ``part.shape_from_mesh`` can apply it without importing a worker (ADR-043),
# and every existing reader of it lives on this side of the boundary.
from cadex_mesh_api import payload_tree_is_deterministic  # noqa: F401


class MeshOperationError(ValueError):
    """One mesh definition could not be materialized by the native kernels."""

    def __init__(self, message: str, *, correction: str = "") -> None:
        super().__init__(message)
        self.details = {"stage": "mesh_kernel", "correction": correction}


def _argument(payload: dict[str, Any], index: int, name: str) -> Any:
    arguments = list(payload.get("arguments") or [])
    if index < len(arguments):
        return arguments[index]
    return dict(payload.get("properties") or {}).get(name)


def _nested_payload(value: Any) -> dict[str, Any]:
    from cadex_domain_worker import _payload

    return _payload(value, serialized=True)


def _import_asset(root: Path, filename: str):
    import Mesh

    from cadex_mesh_api import ASSET_SUFFIXES

    clean = str(filename or "")
    suffix = ("." + clean.rsplit(".", 1)[-1]).lower() if "." in clean else ""
    if (
        not clean
        or any(separator in clean for separator in ("/", "\\"))
        or ".." in clean
        or suffix not in ASSET_SUFFIXES
    ):
        raise MeshOperationError(
            f"api.import_file: {clean!r} is not a valid staged mesh asset name.",
            correction=(
                "Name one STL/OBJ/PLY file placed directly inside the project "
                "assets directory."
            ),
        )
    path = (root / "assets" / clean).resolve()
    if path.parent != (root / "assets").resolve() or not path.is_file():
        raise MeshOperationError(
            f"api.import_file: no staged mesh asset named {clean!r} exists.",
            correction=(
                "Place the file in the project assets directory before running "
                "the script; the runtime stages assets for the isolated worker."
            ),
        )
    mesh = Mesh.Mesh()
    mesh.read(Filename=str(path))
    return mesh


def _triple(value: Any, fallback: tuple[float, float, float]) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return list(fallback)
    return [float(item) for item in value]


def _transform_matrix(properties: dict[str, Any]):
    """One matrix for a whole ``mesh.transform``: scale, rotate, translate.

    ``Mesh`` has no ``scale()`` and no ``rotate()`` -- only ``transform(m)`` --
    so where ``part.transform`` applies three kernel calls in order, this
    composes the same three steps into one matrix, right-to-left:
    ``T · (P · R · P⁻¹) · S``, with ``S`` already carrying its own pivot
    correction. Same order of operations, same result.
    """

    import FreeCAD as App

    pivot = App.Vector(*_triple(properties.get("pivot"), (0.0, 0.0, 0.0)))
    factors = _triple(properties.get("scale"), (1.0, 1.0, 1.0))
    axis = App.Vector(*_triple(properties.get("rotation_axis"), (0.0, 0.0, 1.0)))
    translation = App.Vector(*_triple(properties.get("translation"), (0.0, 0.0, 0.0)))
    degrees = float(properties.get("rotation_degrees", 0.0))

    scaling = App.Matrix()
    scaling.A11, scaling.A22, scaling.A33 = factors
    scaling.A14 = pivot.x * (1.0 - factors[0])
    scaling.A24 = pivot.y * (1.0 - factors[1])
    scaling.A34 = pivot.z * (1.0 - factors[2])

    rotation = App.Rotation(axis, degrees).toMatrix()
    to_pivot = App.Matrix()
    to_pivot.A14, to_pivot.A24, to_pivot.A34 = pivot.x, pivot.y, pivot.z
    from_pivot = App.Matrix()
    from_pivot.A14, from_pivot.A24, from_pivot.A34 = -pivot.x, -pivot.y, -pivot.z

    moving = App.Matrix()
    moving.A14, moving.A24, moving.A34 = (
        translation.x,
        translation.y,
        translation.z,
    )
    return (
        moving.multiply(to_pivot)
        .multiply(rotation)
        .multiply(from_pivot)
        .multiply(scaling)
    )


#: The leaves a placement chain may bottom out on. A layout names coordinates
#: in one asset's own frame, and only these two have one: a boolean of two
#: placed meshes has two frames and no leaf to compose from.
_PLACEABLE_LEAVES = frozenset({"import_file", "from_shape"})


def composed_placement(payload: dict[str, Any]) -> tuple[float, ...]:
    """The matrix that carries one mesh value's leaf frame into the model.

    ``mesh.terminals`` states its layout in the **asset's own** coordinates —
    the numbers you read off the datasheet, once, for a component you then
    place four times (ADR-062). This walks the value tree down to that asset
    and composes every ``mesh.transform`` above it, so the same spec resolves
    to four correctly placed sets of terminals rather than four copies of one.

    Returned as a plain 16-tuple, row-major, rather than an ``App.Matrix``:
    the consumer is ``CadexTerminals``, which touches no kernel type, and the
    part worker reaches this through the callable ``configure_part_assets``
    binds rather than by importing this module (see that function).
    """

    import CadexTerminals

    operation = str(payload.get("operation") or "")
    if operation in _PLACEABLE_LEAVES:
        return CadexTerminals.identity_matrix()
    if operation == "transform":
        import FreeCAD as App

        inner = composed_placement(_nested_payload(_argument(payload, 0, "mesh")))
        # The same order ``build_mesh`` applies them in: this node's matrix
        # multiplies whatever the tree below it already composed to.
        composed = _transform_matrix(
            dict(payload.get("properties") or {})
        ).multiply(App.Matrix(*inner))
        return tuple(
            float(getattr(composed, f"A{row}{column}"))
            for row in range(1, 5)
            for column in range(1, 5)
        )
    raise MeshOperationError(
        f"api.terminals: a terminal layout needs one placed asset to ride, and "
        f"api.{operation} does not have one frame to state it in.",
        correction=(
            "State the terminals on the imported asset (optionally placed with "
            "mesh.transform), not on a mesh built by combining two of them."
        ),
    )


def build_mesh(payload: dict[str, Any], root: Path):
    """Execute one validated Mesh definition and wrap kernel errors usefully."""

    operation = str(payload.get("operation") or "")
    properties = dict(payload.get("properties") or {})
    try:
        if operation == "from_shape":
            import MeshPart

            from cadex_part_worker import build_part_shape

            shape = build_part_shape(_nested_payload(_argument(payload, 0, "shape")))
            return MeshPart.meshFromShape(
                Shape=shape,
                LinearDeflection=float(properties.get("linear_deflection", 0.25)),
                AngularDeflection=math.radians(
                    float(properties.get("angular_deflection", 30.0))
                ),
                Relative=bool(properties.get("relative")),
            )
        if operation == "import_file":
            return _import_asset(root, _argument(payload, 0, "filename"))
        if operation in {"union", "difference", "intersection"}:
            left = build_mesh(_nested_payload(_argument(payload, 0, "left")), root)
            right = build_mesh(_nested_payload(_argument(payload, 1, "right")), root)
            method = {
                "union": "unite",
                "difference": "difference",
                "intersection": "intersect",
            }[operation]
            # The native set operations emit run-dependent vertex/facet
            # orderings; canonicalize immediately so downstream consumers
            # (e.g. decimate) see one deterministic input.
            return canonical_mesh(getattr(left, method)(right))
        if operation == "transform":
            source = build_mesh(_nested_payload(_argument(payload, 0, "mesh")), root)
            # Mesh.transform mutates in place, as decimate does.
            result = source.copy()
            result.transform(_transform_matrix(properties))
            return result
        if operation == "decimate":
            mesh = build_mesh(_nested_payload(_argument(payload, 0, "mesh")), root)
            result = mesh.copy()
            result.decimate(
                float(properties.get("tolerance", 0.1)),
                float(properties.get("reduction", 0.5)),
            )
            return result
    except MeshOperationError:
        raise
    except Exception as exc:
        raise MeshOperationError(
            f"api.{operation}: the native mesh kernel rejected the operation: "
            f"{exc.__class__.__name__}: {exc}",
            correction=(
                f"Inspect api.{operation} inputs; change the smallest invalid "
                "mesh or tolerance instead of repeating the unchanged call."
            ),
        ) from exc
    raise MeshOperationError(
        f"Mesh operation {operation!r} has no native implementation.",
        correction="Return only values created by the declared Mesh runtime exports.",
    )


def canonical_mesh(mesh: Any):
    """Rebuild a mesh in canonical vertex/facet order for byte-stable artifacts.

    The native set operations return the same point set in a run-dependent
    order, which would flip the content digest on every rebuild. Sorting the
    vertices, remapping each facet, rotating each index cycle to its smallest
    vertex (preserving winding), and sorting the facets yields one canonical
    kernel for identical geometry — so facts, artifact bytes, and the digest
    are deterministic.
    """

    import Mesh

    points, facets = mesh.Topology
    coordinates = [(float(p.x), float(p.y), float(p.z)) for p in points]
    order = sorted(range(len(coordinates)), key=lambda i: coordinates[i])
    remap = {old: new for new, old in enumerate(order)}
    canonical_facets = []
    for facet in facets:
        mapped = [remap[int(index)] for index in facet]
        start = mapped.index(min(mapped))
        canonical_facets.append(tuple(mapped[start:] + mapped[:start]))
    canonical_facets.sort()
    ordered = [coordinates[i] for i in order]
    return Mesh.Mesh(
        [[ordered[a], ordered[b], ordered[c]] for a, b, c in canonical_facets]
    )


def canonical_mesh_from_payload(payload: dict[str, Any], root: Path):
    """One materialized mesh value, in canonical order — the BREP ingest entry.

    ``part.shape_from_mesh`` reaches this through the callable
    ``cadex_part_worker.configure_part_assets`` binds, rather than by
    importing it: the part worker is in cadexd's import closure and this
    module is deliberately not. Canonicalizing inside the entry point rather
    than at the call site makes the order-stability guarantee part of the
    contract, and BREP ingest is the one caller that cannot do without it.
    """

    return canonical_mesh(build_mesh(payload, root))


def mesh_geometry_fingerprint(mesh: Any) -> str:
    """SHA-256 over the sorted exact vertex set — the digest identity of a mesh.

    The native set operations re-triangulate coplanar cut regions
    non-deterministically (same surface, different facet split), so artifact
    bytes cannot join the content digest. The vertex set is exact and stable
    across runs: identical geometry always fingerprints identically, and no
    rounding is involved, so there are no quantization boundary flips.
    """

    points, _facets = mesh.Topology
    coordinates = sorted((float(p.x), float(p.y), float(p.z)) for p in points)
    digest = hashlib.sha256()
    for x, y, z in coordinates:
        digest.update(struct.pack("<3d", x, y, z))
    return digest.hexdigest()


def mesh_facts(mesh: Any) -> dict[str, Any]:
    """Bounded JSON-safe facts publication re-verifies on the applied kernel."""

    box = mesh.BoundBox
    return {
        "points": int(mesh.CountPoints),
        "facets": int(mesh.CountFacets),
        "edges": int(mesh.CountEdges),
        "area_mm2": float(mesh.Area),
        "volume_mm3": float(mesh.Volume),
        "bounds": {
            "minimum": [float(box.XMin), float(box.YMin), float(box.ZMin)],
            "maximum": [float(box.XMax), float(box.YMax), float(box.ZMax)],
        },
        "is_solid": bool(mesh.isSolid()),
    }


def serialize_mesh_output(
    root: Path,
    index: int,
    expected: dict[str, str],
    value: Any,
) -> dict[str, Any]:
    """Materialize, validate, and export one mesh output artifact."""

    from cadex_domain_worker import _payload

    payload = _payload(value)
    output_type = str(payload.get("output_type") or "")
    if output_type != expected["type"] or output_type != "mesh":
        raise ValueError(
            f"Output {expected['name']!r} returned type {output_type!r}; "
            "the Mesh domain publishes only 'mesh' outputs."
        )
    mesh = canonical_mesh(build_mesh(payload, root))
    facts = mesh_facts(mesh)
    if facts["facets"] < 1 or facts["points"] < 3:
        raise ValueError(
            f"Output {expected['name']!r} produced an empty mesh; every mesh "
            "output needs at least one facet."
        )
    relative = Path("outputs") / f"output-{index:03d}.ply"
    target = root / relative
    mesh.write(str(target))
    if not target.is_file() or target.stat().st_size <= 0:
        raise RuntimeError(f"Could not export mesh output {expected['name']!r}.")
    item = {
        "name": expected["name"],
        "type": output_type,
        "definition": payload,
        "artifact_kind": "mesh",
        "artifact_path": str(relative),
        "facts": facts,
        "mesh_data": {
            "operation": str(payload.get("operation") or ""),
            "facts": facts,
        },
    }
    if payload_tree_is_deterministic(payload):
        item["geometry_sha256"] = mesh_geometry_fingerprint(mesh)
    return item
