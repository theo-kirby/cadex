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

from cadex_domain_api import DomainValue

#: Part topologies that tessellate into a triangle mesh.
_TESSELLATABLE_PART_TYPES = frozenset({"solid", "shell", "face", "compound"})
#: Mesh asset formats the isolated worker imports from the project assets tree.
ASSET_SUFFIXES = frozenset({".stl", ".obj", ".ply"})

#: Operations whose kernel result is approximate and run-dependent (the
#: GTS-derived decimation collapses edges in address-dependent tie order).
#: Their outputs — and anything built on them — are digest-identified by
#: their canonical definition instead of a geometry fingerprint.
APPROXIMATING_OPERATIONS = frozenset({"decimate"})


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


def _asset_filename(operation: str, value: Any) -> str:
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
    if suffix not in ASSET_SUFFIXES:
        raise _error(
            operation,
            "filename",
            f"must use one of the mesh formats {sorted(ASSET_SUFFIXES)}",
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
        if frozenset(str(item) for item in output_types) != {"mesh"}:
            raise RuntimeError(
                "Mesh pack output types do not match the production runtime contract."
            )

    @staticmethod
    def _value(
        operation: str,
        *arguments: Any,
        label: str = "",
        **properties: Any,
    ) -> DomainValue:
        clean_label = _label(operation, label)
        if clean_label:
            properties["label"] = clean_label
        return DomainValue(
            domain="mesh",
            operation=operation,
            output_type="mesh",
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
        )
