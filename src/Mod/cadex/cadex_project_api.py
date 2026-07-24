# SPDX-License-Identifier: LGPL-2.1-or-later

"""Project-script parameter declaration and multi-domain API composition.

The project domain executes ONE script with every capability domain staged:
the exec namespace carries ``sketcher``, ``part``, ``partdesign`` and
``assembly`` API objects plus the ``params``/``num`` parameter vocabulary.
This module is FreeCAD-free; it runs inside the sandboxed worker and is
importable by host-side tests.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Any, Mapping

from cadex_domain_api import DomainValue

PROJECT_DOMAIN = "project"
EVALUATION_ORDER = ("sketcher", "part", "partdesign", "assembly")
CONTROL_FIELDS = ("label", "unit", "min", "max", "step", "description")
INLINE_SOURCE_UID = "xscript-project"

_PARAM_NAME = re.compile(r"^[a-z_][a-z0-9_]{0,63}$")
_MAX_PARAMS = 64
_SPEC_MARKER = "cadex-project-param-spec"


class ProjectParameterError(ValueError):
    """A parameter declaration or value violates the project contract."""


def num(
    default: float,
    *,
    unit: str = "",
    min: float | None = None,
    max: float | None = None,
    step: float | None = None,
    label: str = "",
    description: str = "",
) -> dict[str, Any]:
    """Declare one numeric parameter control.

    Usage inside a project script::

        p = params(width=num(100, unit="mm", min=10, max=500, step=1))
        ... part.box(p.width, 20, 5) ...
    """

    if isinstance(default, bool) or not isinstance(default, (int, float)):
        raise ProjectParameterError("num() default must be a number.")
    default = float(default)
    if not math.isfinite(default):
        raise ProjectParameterError("num() default must be finite.")
    spec: dict[str, Any] = {"kind": _SPEC_MARKER, "type": "num", "default": default}
    for name, value in (("min", min), ("max", max), ("step", step)):
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ProjectParameterError(f"num() {name} must be a number.")
        value = float(value)
        if not math.isfinite(value):
            raise ProjectParameterError(f"num() {name} must be finite.")
        spec[name] = value
    if "step" in spec and spec["step"] <= 0:
        raise ProjectParameterError("num() step must be positive.")
    if "min" in spec and "max" in spec and spec["min"] > spec["max"]:
        raise ProjectParameterError("num() min must not exceed max.")
    low = spec.get("min")
    high = spec.get("max")
    if (low is not None and default < low) or (high is not None and default > high):
        raise ProjectParameterError("num() default must lie within [min, max].")
    if not isinstance(unit, str) or len(unit) > 16:
        raise ProjectParameterError("num() unit must be a short string.")
    if not isinstance(label, str) or len(label) > 80:
        raise ProjectParameterError("num() label must be a short string.")
    if not isinstance(description, str) or len(description) > 400:
        raise ProjectParameterError("num() description must be a short string.")
    spec["unit"] = unit
    spec["label"] = label
    spec["description"] = description
    return spec


class ParamValues:
    """Immutable attribute-access view of the effective parameter values."""

    __slots__ = ("_values",)

    def __init__(self, values: Mapping[str, float]) -> None:
        object.__setattr__(self, "_values", MappingProxyType(dict(values)))

    def __getattr__(self, name: str) -> float:
        try:
            return self._values[name]
        except KeyError:
            raise AttributeError(
                f"Unknown parameter {name!r}; declare it in params(...)."
            ) from None

    def __getitem__(self, name: str) -> float:
        return self._values[name]

    def __iter__(self):
        return iter(self._values)

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("Parameter values are immutable inside the script.")


class ParamsCollector:
    """The ``params(...)`` callable: collects specs, applies stored values."""

    def __init__(self, overrides: Mapping[str, Any] | None = None) -> None:
        cleaned: dict[str, float] = {}
        for key, value in dict(overrides or {}).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ProjectParameterError(
                    f"Stored parameter value {key!r} must be a number."
                )
            value = float(value)
            if not math.isfinite(value):
                raise ProjectParameterError(
                    f"Stored parameter value {key!r} must be finite."
                )
            cleaned[str(key)] = value
        self._overrides = cleaned
        self.specs: list[dict[str, Any]] = []
        self._called = False

    def __call__(self, **declarations: Any) -> ParamValues:
        if self._called:
            raise ProjectParameterError(
                "params(...) may be called at most once per script."
            )
        self._called = True
        if len(declarations) > _MAX_PARAMS:
            raise ProjectParameterError(
                f"A project script may declare at most {_MAX_PARAMS} parameters."
            )
        values: dict[str, float] = {}
        for name, spec in declarations.items():
            if not _PARAM_NAME.fullmatch(name):
                raise ProjectParameterError(
                    f"Parameter name {name!r} must be lower_snake_case (max 64 chars)."
                )
            if not isinstance(spec, dict) or spec.get("kind") != _SPEC_MARKER:
                raise ProjectParameterError(
                    f"Parameter {name!r} must be declared with num(...)."
                )
            record = {"name": name, "type": str(spec["type"])}
            record["default"] = float(spec["default"])
            for field in ("min", "max", "step"):
                if field in spec:
                    record[field] = float(spec[field])
            for field in ("unit", "label", "description"):
                if spec.get(field):
                    record[field] = str(spec[field])
            self.specs.append(record)
            value = self._overrides.get(name, record["default"])
            low = record.get("min")
            high = record.get("max")
            if low is not None and value < low:
                value = low
            if high is not None and value > high:
                value = high
            values[name] = value
        return ParamValues(values)


def inline_source_token(payload: Mapping[str, Any]) -> str:
    """Deterministic identity for one same-script component source payload."""

    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "src-" + hashlib.sha256(canonical).hexdigest()[:24]


def create_project_assembly_api(
    exports: Any,
    output_types: Any,
    inline_sources: dict[str, dict[str, Any]],
) -> Any:
    """Assembly API whose components take same-script part/partdesign values.

    ``assembly.component(part_or_body_value, ...)`` records the source payload
    in ``inline_sources`` keyed by its deterministic token and rewrites the
    component reference to ``{document_uid: INLINE_SOURCE_UID, object_name:
    token}``. Every component source value must ALSO be returned as a declared
    part/partdesign output of the same script: the worker refuses undeclared
    sources so publication can link each live component to a published stable
    output object. Cross-document references are retired in the project
    domain: v0.0.1 assemblies are rigid, same-script solids.
    """

    from cadex_assembly_api import AssemblyDomainAPI

    class _ProjectAssemblyAPI(AssemblyDomainAPI):
        def component(
            self,
            source: Any,
            *,
            placement: Any = None,
            grounded: bool = False,
            label: str = "",
        ) -> DomainValue:
            if not isinstance(source, DomainValue) or source.domain not in {
                "part",
                "partdesign",
            }:
                raise ProjectParameterError(
                    "assembly.component source must be a part or partdesign value "
                    "created in this script (cross-document references are not "
                    "supported in project scripts)."
                )
            payload = source.to_payload()
            token = inline_source_token(payload)
            inline_sources[token] = payload
            return super().component(
                {"document_uid": INLINE_SOURCE_UID, "object_name": token},
                placement=placement,
                grounded=grounded,
                flexible=False,
                label=label,
            )

    return _ProjectAssemblyAPI(exports, output_types)
