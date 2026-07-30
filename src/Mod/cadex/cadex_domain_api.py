# SPDX-License-Identifier: LGPL-2.1-or-later

"""Runtime values exposed to workbench-qualified XScript programs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType, MethodType
from typing import Any, Iterable

_OPERATION_OUTPUT_TYPES: dict[str, str] = {
    "box": "solid",
    "cylinder": "solid",
    "sphere": "solid",
    "extrude": "solid",
    "revolve": "solid",
    "fuse": "solid",
    "cut": "solid",
    "common": "solid",
    "face": "face",
    "wire": "wire",
    "compound": "compound",
    "shell": "shell",
    "fill": "fill",
    "blend": "blend",
    "extend": "extension",
    "loft": "loft",
    "thicken": "solid",
    "sketch": "sketch",
    "sheet": "sheet",
    "assign": "material_assignment",
    "appearance": "appearance",
    "site": "site",
    "building": "building",
    "level": "level",
    "wall": "wall",
    "slab": "slab",
    "structure": "structure",
    "opening": "opening",
    "mesh": "mesh",
    "mesh_from_shape": "mesh",
    "shape_from_mesh": "solid",
    "points": "points",
    "point_cloud": "points",
    "inspection": "inspection_group",
    "measurement": "measurement",
    "report": "report",
    "robot": "robot",
    "waypoint": "waypoints",
    "trajectory": "trajectory",
    "dressup": "dressup",
    "simulate": "simulation",
    "analysis": "analysis",
    "solver": "solver",
    "material": "material",
    "constraint": "constraint",
    "load_case": "load_case",
    "solve": "result",
    "job": "job",
    "stock": "stock",
    "tool": "tool",
    "operation": "operation",
    "generate_toolpath": "toolpath",
    "postprocess": "toolpath",
    "page": "page",
    "template": "template",
    "view": "view",
    "projection": "projection",
    "dimension": "dimension",
    "annotation": "annotation",
    "assembly": "assembly",
    "component": "component_link",
    "joint": "joint",
    "connector": "joint",
}

_DOMAIN_OPERATION_OUTPUT_TYPES: dict[str, dict[str, str]] = {
    "surface": {
        # Boundary builders are intermediate domain values; only the pack's
        # declared output types may appear at the top-level result contract.
        "wire": "wire",
        "face": "face",
    },
    "assembly": {
        "assembly": "assembly",
        "component": "component_link",
        "connector": "joint",
        "joint": "joint",
        "solve": "solver_diagnostics",
        "motion": "motion",
        "simulation": "simulation",
        # Dynamics produces a `simulation`, not a type of its own: a script
        # has one simulation whichever solver ran it, and two
        # assembly_simulation_json artifacts would leave the shell baking
        # neither (ADR-062). `body` is an intermediate, like `connector`.
        "dynamics": "simulation",
        # An exported MuJoCo model *does* get a type of its own, for the
        # converse of the reason dynamics does not: nothing bakes it, so
        # two of them in one script is a reasonable thing to write and the
        # "exactly one simulation" rule must not catch them (ADR-066).
        "mjcf": "mjcf",
        "body": "body",
        # A collision shape is an argument to a body, never an output: it
        # has no native type and nothing publishes it (M3 phase 1).
        "collision": "collision",
        # A joint's damping and its motor are arguments to a dynamics run
        # for the same reason a collision shape is: they have no native
        # type, nothing publishes them, and a script that returned one would
        # be declaring a fact about a joint rather than a result (M4).
        "joint_dynamics": "joint_dynamics",
        "actuator": "actuator",
        "exploded_view": "exploded_view",
    },
    "material": {
        "material": "material_assignment",
        "assign": "material_assignment",
        "appearance": "appearance",
    },
    "meshpart": {
        "mesh_from_shape": "mesh",
        "shape_from_mesh": "solid",
    },
    "points": {"point_cloud": "points"},
    "reverse_engineering": {
        "fit_curve": "curve",
        "fit_surface": "surface",
        "reconstruct": "mesh",
        "segment": "mesh",
        "fit_metrics": "fit_metrics",
    },
    "inspection": {
        "comparison": "inspection_feature",
        "group": "inspection_group",
        "measurement": "measurement",
        "report": "report",
    },
}


def _json_value(value: Any) -> Any:
    if isinstance(value, DomainValue):
        return value.to_payload()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    raise TypeError(
        "XScript domain API values must contain only bounded JSON or other "
        f"domain API values, not {type(value).__name__}."
    )


def _immutable_value(value: Any) -> Any:
    """Recursively detach and freeze one declarative graph value."""

    if isinstance(value, DomainValue):
        return value
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return tuple(_immutable_value(item) for item in value)
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _immutable_value(item) for key, item in value.items()}
        )
    raise TypeError(
        "XScript domain API values must contain only bounded JSON or other "
        f"domain API values, not {type(value).__name__}."
    )


@dataclass(frozen=True)
class DomainValue:
    domain: str
    operation: str
    output_type: str
    arguments: tuple[Any, ...]
    properties: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "arguments",
            tuple(_immutable_value(item) for item in self.arguments),
        )
        object.__setattr__(self, "properties", _immutable_value(self.properties))

    def to_payload(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "operation": self.operation,
            "output_type": self.output_type,
            "arguments": [_json_value(item) for item in self.arguments],
            "properties": _json_value(self.properties),
        }


class DomainAPI:
    """One immutable domain-qualified API object injected as ``api``."""

    def __init__(
        self,
        domain: str,
        exports: Iterable[str],
        output_types: Iterable[str],
    ) -> None:
        object.__setattr__(self, "_locked", False)
        object.__setattr__(self, "_domain", str(domain))
        object.__setattr__(
            self,
            "_output_types",
            frozenset(str(item) for item in output_types),
        )
        object.__setattr__(
            self,
            "_exports",
            tuple(dict.fromkeys(str(item) for item in exports)),
        )
        for operation in self._exports:
            if not operation.isidentifier() or operation.startswith("_"):
                raise ValueError(f"Invalid domain API export: {operation!r}.")
            object.__setattr__(
                self,
                operation,
                MethodType(self._builder(operation), self),
            )
        object.__setattr__(self, "_locked", True)

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_locked", False):
            raise TypeError("The XScript domain api is immutable.")
        object.__setattr__(self, name, value)

    @staticmethod
    def _builder(operation: str):
        def build(_self: "DomainAPI", *args: Any, **properties: Any) -> DomainValue:
            requested_type = str(properties.pop("output_type", "") or "")
            output_type = (
                requested_type
                or _DOMAIN_OPERATION_OUTPUT_TYPES.get(_self._domain, {}).get(operation)
                or _OPERATION_OUTPUT_TYPES.get(operation, operation)
            )
            intermediate = (
                output_type
                in _DOMAIN_OPERATION_OUTPUT_TYPES.get(_self._domain, {}).values()
            )
            if output_type not in _self._output_types and not intermediate:
                if len(_self._output_types) == 1:
                    output_type = next(iter(_self._output_types))
                else:
                    raise ValueError(
                        f"api.{operation} requires output_type to be one of "
                        f"{sorted(_self._output_types)}."
                    )
            return DomainValue(
                domain=_self._domain,
                operation=operation,
                output_type=output_type,
                arguments=tuple(args),
                properties={str(key): value for key, value in properties.items()},
            )

        build.__name__ = operation
        build.__qualname__ = f"DomainAPI.{operation}"
        build.__doc__ = (
            f"Build one {operation} definition for the active XScript domain."
        )
        return build

    def output(self, output_type: str, **properties: Any) -> DomainValue:
        """Build an explicitly typed output when no higher-level helper applies."""

        clean = str(output_type or "")
        if clean not in self._output_types:
            raise ValueError(
                f"output_type must be one of {sorted(self._output_types)}."
            )
        return DomainValue(
            domain=self._domain,
            operation="output",
            output_type=clean,
            arguments=(),
            properties={str(key): value for key, value in properties.items()},
        )

    @property
    def exported_names(self) -> tuple[str, ...]:
        return (*self._exports, "output")


def create_domain_api(
    domain: str,
    exports: Iterable[str],
    output_types: Iterable[str],
) -> Any:
    """Construct the exact runtime API registered for one domain.

    Production domains use explicit classes with real signatures and
    operation-specific validation.  The generic builder remains available only
    to unfinished, unavailable development packs; surface resolution never
    treats that fallback as production-ready.
    """

    clean_domain = str(domain or "").strip().lower()
    if clean_domain == "partdesign":
        from cadex_partdesign_api import PartDesignDomainAPI

        return PartDesignDomainAPI(exports, output_types)
    if clean_domain == "part":
        from cadex_part_api import PartDomainAPI

        return PartDomainAPI(exports, output_types)
    if clean_domain == "assembly":
        from cadex_assembly_api import AssemblyDomainAPI

        return AssemblyDomainAPI(exports, output_types)
    if clean_domain == "sketcher":
        from cadex_sketcher_api import SketcherDomainAPI

        return SketcherDomainAPI(exports, output_types)
    if clean_domain == "mesh":
        from cadex_mesh_api import MeshDomainAPI

        return MeshDomainAPI(exports, output_types)
    return DomainAPI(clean_domain, exports, output_types)
