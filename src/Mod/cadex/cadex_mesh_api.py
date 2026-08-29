# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Production provider-facing API for the Mesh XScript domain.

The mesh domain covers the minimal Phase 4 surface: tessellating part-domain
shapes, importing mesh assets, native mesh booleans, and decimation.  All
distances are millimetres and all angles are degrees.  Methods validate their
declarative contract before returning a :class:`DomainValue`, so source errors
identify the exact operation and parameter before Mesh execution begins.
"""

from __future__ import annotations

import math
from typing import Any, Iterable

from CadexTerminals import TerminalError, TerminalSet, declared_layout
from cadex_domain_api import DomainValue

#: Mesh operations one asset frame can be composed from, and therefore the
#: only ones ``mesh.terminals`` accepts. A boolean of two placed meshes has
#: two frames and no leaf, so a layout stated against it means nothing.
_PLACEABLE_OPERATIONS = frozenset({"import_file", "from_shape", "transform"})

#: Part topologies that tessellate into a triangle mesh.
_TESSELLATABLE_PART_TYPES = frozenset({"solid", "shell", "face", "compound"})
#: Mesh asset formats the isolated worker imports from the project assets tree.
ASSET_SUFFIXES = frozenset({".stl", ".obj", ".ply"})

#: Operations whose kernel result is approximate and run-dependent (the
#: GTS-derived decimation collapses edges in address-dependent tie order).
#: Their outputs — and anything built on them — are digest-identified by
#: their canonical definition instead of a geometry fingerprint.
#:
#: ``check`` is deliberately **not** here. It is approximating in no sense:
#: it reads a mesh and returns counts, it mutates nothing, and it publishes
#: no geometry at all — so there is nothing for a fingerprint to identify
#: and its digest is the hash of its own declaration either way (ADR-144).
APPROXIMATING_OPERATIONS = frozenset({"decimate"})

#: What the Mesh pack may publish. ``mesh_check`` is the one member that is
#: not a triangle mesh: it is a declared output carrying four integers and no
#: geometry, the way ``part.measurement`` is on the part side (ADR-139) and
#: ``solver_diagnostics`` is on the assembly side. The split exists so that
#: ``__init__`` can still assert the pack and the runtime agree exactly.
_PACK_OUTPUT_TYPES = frozenset({"mesh", "mesh_check"})


def payload_tree_is_deterministic(payload: Any) -> bool:
    """False when any operation in the value tree is approximating.

    Lives here rather than in the worker (where it began) because two
    callers outside the mesh kernel need it: the digest branch that decides
    whether a mesh output carries a geometry fingerprint, and
    ``part.shape_from_mesh``, which must refuse an approximating tree at
    script-eval time — a BREP output's identity *is* its exported bytes, so
    it has no by-definition fallback (ADR-043).
    """

    if isinstance(payload, dict):
        if str(payload.get("operation") or "") in APPROXIMATING_OPERATIONS:
            return False
        return all(payload_tree_is_deterministic(value) for value in payload.values())
    if isinstance(payload, (list, tuple)):
        return all(payload_tree_is_deterministic(item) for item in payload)
    return True


def _error(operation: str, parameter: str, message: str, value: Any = None) -> ValueError:
    received = "" if value is None else f" Received {value!r}."
    return ValueError(f"api.{operation}: invalid {parameter}: {message}.{received}")


def _number(
    operation: str,
    parameter: str,
    value: Any,
    *,
    minimum: float | None = None,
    strict: bool = False,
) -> float:
    if isinstance(value, bool):
        raise _error(operation, parameter, "expected a finite number", value)
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise _error(operation, parameter, "expected a finite number", value) from exc
    if not math.isfinite(result):
        raise _error(operation, parameter, "expected a finite number", value)
    if minimum is not None and (result <= minimum if strict else result < minimum):
        relation = "greater than" if strict else "at least"
        raise _error(operation, parameter, f"must be {relation} {minimum:g}", value)
    return result


def _vector(
    operation: str,
    parameter: str,
    value: Any,
    *,
    nonzero: bool = False,
) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise _error(operation, parameter, "expected [x, y, z]", value)
    result = [
        _number(operation, f"{parameter}[{index}]", item)
        for index, item in enumerate(value)
    ]
    if nonzero and math.sqrt(sum(item * item for item in result)) <= 1.0e-12:
        raise _error(operation, parameter, "vector magnitude must be non-zero", value)
    return result


def _label(operation: str, value: Any) -> str:
    result = str(value or "").strip()
    if len(result) > 120:
        raise _error(operation, "label", "must contain at most 120 characters", value)
    return result


def _mesh(operation: str, parameter: str, value: Any) -> DomainValue:
    if not isinstance(value, DomainValue) or value.domain != "mesh":
        raise _error(
            operation,
            parameter,
            "expected a value returned by this Mesh api",
            type(value).__name__,
        )
    # The domain alone stopped being enough when the domain gained a second
    # output type (ADR-144). A `mesh_check` is four integers about a mesh,
    # not a mesh, so it has no triangles to unite, place or decimate -- and
    # left unchecked here it would reach the kernel and fail there, naming
    # the composed chain instead of the line the script wrote.
    if value.output_type != "mesh":
        raise _error(
            operation,
            parameter,
            f"expected a mesh, and mesh.{value.operation} returns a "
            f"{value.output_type} -- a statement about a mesh, with no "
            "triangles of its own. Pass the mesh it checked",
            value.output_type,
        )
    return value


def _placeable(operation: str, value: DomainValue) -> DomainValue:
    """Refuse a mesh value whose terminals would have no one frame to ride.

    Checked here rather than in the worker as well as there: the worker sees
    the composed chain and can only say *that* it failed, while this sees the
    operation the script actually wrote and can name it.
    """

    node: Any = value
    while isinstance(node, DomainValue):
        if node.operation not in _PLACEABLE_OPERATIONS:
            raise _error(
                operation,
                "component",
                (
                    f"api.{node.operation} reshapes or combines meshes rather "
                    "than placing one, so its result has no single asset frame "
                    "for a terminal layout to be stated in; declare the "
                    "terminals on the imported component itself"
                ),
                node.operation,
            )
        if node.operation != "transform":
            return value
        node = node.arguments[0] if node.arguments else None
    return value


def _part_shape(operation: str, parameter: str, value: Any) -> DomainValue:
    if not isinstance(value, DomainValue) or value.domain != "part":
        raise _error(
            operation,
            parameter,
            "expected a value returned by the Part api",
            type(value).__name__,
        )
    if value.output_type not in _TESSELLATABLE_PART_TYPES:
        raise _error(
            operation,
            parameter,
            f"expected part topology {sorted(_TESSELLATABLE_PART_TYPES)}",
            value.output_type,
        )
    return value


def _asset_filename(
    operation: str, value: Any, *, suffixes: Any = ASSET_SUFFIXES
) -> str:
    """One name for a file directly inside the project assets directory.

    ``suffixes`` defaults to the three mesh formats this module is about, so
    ``mesh.import_file`` reads exactly as it did. The project store passes
    its own wider set (ADR-084) — the same name check, the same traversal
    refusal, one more accepted extension — rather than this module learning
    what a trained control policy is.
    """

    result = str(value or "").strip()
    if not result or len(result) > 120:
        raise _error(
            operation, "filename", "must contain 1-120 characters", value
        )
    if any(separator in result for separator in ("/", "\\")) or ".." in result:
        raise _error(
            operation,
            "filename",
            "must name a file directly inside the project assets directory",
            value,
        )
    suffix = ("." + result.rsplit(".", 1)[-1]).lower() if "." in result else ""
    if suffix not in suffixes:
        raise _error(
            operation,
            "filename",
            f"must use one of the formats {sorted(suffixes)}",
            value,
        )
    return result


class MeshDomainAPI:
    """Explicit, immutable construction API injected into Mesh XScript source."""

    __slots__ = ()

    domain = "mesh"

    def __init__(self, exports: Iterable[str], output_types: Iterable[str]) -> None:
        declared = tuple(dict.fromkeys(str(item) for item in exports))
        missing = [name for name in declared if not callable(getattr(self, name, None))]
        if missing:
            raise RuntimeError(
                f"Mesh runtime is missing declared exports: {', '.join(missing)}."
            )
        undeclared = [name for name in self.exported_names if name not in declared]
        if undeclared:
            raise RuntimeError(
                f"Mesh pack does not declare runtime exports: {', '.join(undeclared)}."
            )
        if frozenset(str(item) for item in output_types) != _PACK_OUTPUT_TYPES:
            raise RuntimeError(
                "Mesh pack output types do not match the production runtime contract."
            )

    @staticmethod
    def _value(
        operation: str,
        *arguments: Any,
        label: str = "",
        output_type: str = "mesh",
        **properties: Any,
    ) -> DomainValue:
        clean_label = _label(operation, label)
        if clean_label:
            properties["label"] = clean_label
        return DomainValue(
            domain="mesh",
            operation=operation,
            output_type=output_type,
            arguments=tuple(arguments),
            properties=properties,
        )

    def from_shape(
        self,
        shape: DomainValue,
        *,
        linear_deflection: float = 0.25,
        angular_deflection: float = 30.0,
        relative: bool = False,
        label: str = "",
    ) -> DomainValue:
        """Tessellate a Part api solid, shell, face, or compound into a mesh."""

        operation = "from_shape"
        return self._value(
            operation,
            _part_shape(operation, "shape", shape),
            linear_deflection=_number(
                operation, "linear_deflection", linear_deflection, minimum=0.0, strict=True
            ),
            angular_deflection=_number(
                operation, "angular_deflection", angular_deflection, minimum=0.0, strict=True
            ),
            relative=bool(relative),
            label=label,
        )

    def import_file(self, filename: str, *, label: str = "") -> DomainValue:
        """Import one STL, OBJ, or PLY file from the project assets directory."""

        operation = "import_file"
        return self._value(
            operation,
            _asset_filename(operation, filename),
            label=label,
        )

    def union(self, left: DomainValue, right: DomainValue, *, label: str = "") -> DomainValue:
        """Unite two meshes with the native mesh set operation."""

        operation = "union"
        return self._value(
            operation,
            _mesh(operation, "left", left),
            _mesh(operation, "right", right),
            label=label,
        )

    def difference(self, left: DomainValue, right: DomainValue, *, label: str = "") -> DomainValue:
        """Subtract the right mesh from the left with the native mesh set operation."""

        operation = "difference"
        return self._value(
            operation,
            _mesh(operation, "left", left),
            _mesh(operation, "right", right),
            label=label,
        )

    def intersection(self, left: DomainValue, right: DomainValue, *, label: str = "") -> DomainValue:
        """Intersect two meshes with the native mesh set operation."""

        operation = "intersection"
        return self._value(
            operation,
            _mesh(operation, "left", left),
            _mesh(operation, "right", right),
            label=label,
        )

    def decimate(
        self,
        mesh: DomainValue,
        *,
        tolerance: float,
        reduction: float,
        label: str = "",
    ) -> DomainValue:
        """Reduce a mesh's facet count by up to ``reduction`` (0-1) within ``tolerance``."""

        operation = "decimate"
        clean_reduction = _number(
            operation, "reduction", reduction, minimum=0.0, strict=True
        )
        if clean_reduction > 1.0:
            raise _error(operation, "reduction", "must not exceed 1.0", reduction)
        return self._value(
            operation,
            _mesh(operation, "mesh", mesh),
            tolerance=_number(operation, "tolerance", tolerance, minimum=0.0, strict=True),
            reduction=clean_reduction,
            label=label,
        )

    def check(self, mesh: DomainValue, *, label: str = "") -> DomainValue:
        """Report whether a mesh is sound: four integers and no geometry.

        Non-manifold edges, self-intersecting facet pairs, whether the
        surface is closed, and the volume it encloses. It publishes **no
        geometry** — it is a row in the tree that states a fact about
        another output, the way ``part.measurement`` states a dimension
        (ADR-139, ADR-144).

        Two things it exists for, both measured rather than anticipated:

        * **A combinatorial closure check cannot see a self-intersection.**
          A surface can have every edge in exactly two triangles and still
          have two facets passing through each other. Measured on a
          marching-tetrahedra topology-optimisation result: watertight by
          every count, and one self-intersecting pair.
        * **``decimate`` does not tell you what it did.** Measured on that
          same mesh, a 50% and a 90% reduction request both returned 7248
          facets — the tolerance bound, not the reduction, and nothing said
          so. ``check`` is how a script finds out.

        It never repairs. A repair op that mutates geometry and reports
        nothing is the wrong shape of answer to "is this sound"; the script
        owns the geometry, so the script decides what to do about the
        answer.
        """

        operation = "check"
        return self._value(
            operation,
            _mesh(operation, "mesh", mesh),
            output_type="mesh_check",
            label=label,
        )

    def transform(
        self,
        mesh: DomainValue,
        *,
        translation: Iterable[float] = (0.0, 0.0, 0.0),
        rotation_axis: Iterable[float] = (0.0, 0.0, 1.0),
        rotation_degrees: float = 0.0,
        scale: float | Iterable[float] = 1.0,
        pivot: Iterable[float] = (0.0, 0.0, 0.0),
        label: str = "",
    ) -> DomainValue:
        """Copy, scale and rotate about pivot, then translate a mesh.

        The same contract as ``part.transform``, so positioning an imported
        component reads the same as positioning a modelled solid. Exactly
        reproducible on float coordinates, so it does not make its tree
        approximating: a transformed import keeps its geometry fingerprint.
        """

        operation = "transform"
        if isinstance(scale, (list, tuple)):
            clean_scale = _vector(operation, "scale", scale)
            if any(value <= 0.0 for value in clean_scale):
                raise _error(operation, "scale", "all scale factors must be positive", scale)
        else:
            factor = _number(operation, "scale", scale, minimum=0.0, strict=True)
            clean_scale = [factor, factor, factor]
        return self._value(
            operation,
            _mesh(operation, "mesh", mesh),
            translation=_vector(operation, "translation", translation),
            rotation_axis=_vector(operation, "rotation_axis", rotation_axis, nonzero=True),
            rotation_degrees=_number(operation, "rotation_degrees", rotation_degrees),
            scale=clean_scale,
            pivot=_vector(operation, "pivot", pivot),
            label=label,
        )

    def terminals(
        self,
        component: DomainValue,
        *,
        terminals: Iterable[Any] | None = None,
        header: Any = None,
        names: Iterable[str],
    ) -> TerminalSet:
        """Name the places a wire attaches to an imported component (ADR-062).

        The mesh half of ``part.terminals``, and **declared only**: a
        triangle mesh has no ``Cylinder`` face to select, so there is nothing
        for a selector to name.  Detecting holes by fitting cylinders to
        triangle bands is deliberately not done — iterative fitting is a
        determinism risk against the rebuild digest, and it is fragile on the
        coarse STLs vendors actually ship.

        **The coordinates are the asset's own**, before any
        ``mesh.transform``.  That is what makes define-once/place-many work:
        state one header from the datasheet, place the component four times,
        and each instance carries its own correctly placed terminals::

            spec = dict(header=dict(origin=(0, 0, 4.2), along=(0, 1, 0),
                                    axis=(0, 0, 1), pitch=1.2, count=3,
                                    hole_dia=0.6, depth=0.8),
                        names=["a", "b", "c"])
            for index, (x, y, z) in enumerate(centers):
                motors[index] = mesh.transform(motor_raw, translation=(x, y, z))
                leads[index] = mesh.terminals(motors[index], **spec)

        Resolution walks the value tree to its imported leaf and composes
        every transform above it.  Points carry the whole placement and
        directions only its rotation, so a rotated component's terminals face
        the way the component does.  A **non-uniform scale** on the chain is
        refused rather than silently skewing an axis off the hole it belongs
        to.

        ``header=`` and ``terminals=`` mean exactly what they do on
        ``part.terminals``; see that docstring for the layout keys.
        """

        operation = "terminals"
        clean_component = _mesh(operation, "component", component)
        _placeable(operation, clean_component)
        try:
            layout = declared_layout(terminals, header=header, names=names)
        except TerminalError as exc:
            raise TerminalError(f"api.{operation}: {exc}", details=exc.details) from exc
        return TerminalSet(clean_component, layout)

    @property
    def exported_names(self) -> tuple[str, ...]:
        return (
            "from_shape",
            "import_file",
            "union",
            "difference",
            "intersection",
            "decimate",
            "transform",
            "terminals",
            "check",
        )
