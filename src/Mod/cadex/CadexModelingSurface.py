# SPDX-License-Identifier: LGPL-2.1-or-later

"""Exact modeling-engine/workbench surface resolution.

This is the single authority for deciding which CAD authoring surface exists.
It deliberately returns one pack, never a union or fallback.  Runtime filters
may remove tools for document/edit-state reasons, but they may not add tools to
the resolved tuple.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Iterable

from CadexScriptedDomains import domain_availability, get_xscript_pack

MODELING_ENGINES = frozenset({"xscript"})
UNSUPPORTED_WORKBENCHES = frozenset({"NoneWorkbench", "TestWorkbench"})

CORE_CONVERSATION_VIEW_TOOLS = frozenset(
    {
        "conversation.ask_user",
        "core.inspect",
        "core.capture_view_screenshot",
        "core.set_view",
        # Repointing a dead link is a document-level repair, available on every
        # surface (mirrors how core.* tools ride along).
        "core.relink_object",
        # File import/export/link is document-level, not workbench-specific, so
        # every session surface carries it. "file" is treated as a shared
        # utility namespace by validate_surface_names().
        "file.import_model",
        "file.export_model",
        "file.link_external_part",
    }
)

# Domain-specific read entry points stay available to the application, but are
# not duplicated in provider declarations. ``core.inspect`` is the one
# model-facing read interface and remains bound to the resolved
# workbench/engine tuple.
HIDDEN_PROVIDER_INSPECTION_TOOLS = frozenset(
    {
        "assembly.list_structure",
    }
)


def _provider_cad_tool_names(names: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            str(name)
            for name in names
            if str(name) not in HIDDEN_PROVIDER_INSPECTION_TOOLS
            and not str(name).endswith(".describe_api")
            and not str(name).endswith(".inspect_program")
        )
    )

@dataclass(frozen=True)
class ModelingSurface:
    workbench: str | None
    engine: str
    domain: str | None
    surface_id: str
    core_tool_names: tuple[str, ...]
    cad_tool_names: tuple[str, ...]
    available: bool
    unavailable_reason: str

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.core_tool_names, *self.cad_tool_names)))

    def summary(self) -> dict[str, Any]:
        return {
            "workbench": str(self.workbench or ""),
            "engine": self.engine,
            "domain": self.domain,
            "surface_id": self.surface_id,
            "available": self.available,
            "unavailable_reason": self.unavailable_reason,
            "core_tool_names": list(self.core_tool_names),
            "cad_tool_names": list(self.cad_tool_names),
            "tool_names": list(self.tool_names),
        }


def _surface_id(*, workbench: str | None, engine: str, domain: str | None, generation: str) -> str:
    readable = "/".join(
        (
            "cadex",
            "surface",
            str(workbench or "none"),
            engine,
            str(domain or "unavailable"),
            generation,
        )
    )
    digest = hashlib.sha256(readable.encode("utf-8")).hexdigest()[:12]
    return f"{readable}/{digest}"


def _unavailable(
    workbench: str | None,
    engine: str,
    reason: str,
    *,
    domain: str | None = None,
) -> ModelingSurface:
    return ModelingSurface(
        workbench=workbench,
        engine=engine,
        domain=domain,
        surface_id=_surface_id(
            workbench=workbench,
            engine=engine,
            domain=domain,
            generation="v2-unavailable",
        ),
        core_tool_names=tuple(sorted(CORE_CONVERSATION_VIEW_TOOLS)),
        cad_tool_names=(),
        available=False,
        unavailable_reason=reason,
    )


def resolve_modeling_surface(
    workbench: str | None,
    engine: str,
) -> ModelingSurface:
    """Resolve exactly one CAD pack for ``(workbench, engine)``."""

    clean_engine = str(engine or "").strip().lower()
    if clean_engine not in MODELING_ENGINES:
        return _unavailable(
            workbench,
            clean_engine or "unknown",
            f"Unknown modeling engine: {clean_engine or '<missing>'}.",
        )
    clean_workbench = str(workbench or "").strip() or None
    if clean_workbench is None:
        return _unavailable(
            clean_workbench,
            clean_engine,
            "No active FreeCAD workbench has a CAD authoring surface.",
        )
    if clean_workbench in UNSUPPORTED_WORKBENCHES:
        return _unavailable(
            clean_workbench,
            clean_engine,
            f"{clean_workbench} intentionally has no CAD authoring surface.",
        )
    # Reachability guard: an unknown workbench has no CAD authoring surface.
    # The scripted pack registry is the single authority for which workbenches
    # exist.
    if get_xscript_pack(clean_workbench) is None:
        return _unavailable(
            clean_workbench,
            clean_engine,
            f"Unknown FreeCAD workbench {clean_workbench!r}; no fallback surface is permitted.",
        )

    if clean_engine == "xscript":
        from CadexScriptedDomains import xscript_domain_availability

        xscript_pack = get_xscript_pack(clean_workbench)
        if xscript_pack is None:
            return _unavailable(
                clean_workbench,
                clean_engine,
                f"No xscript domain is registered for {clean_workbench}.",
            )
        available, reason = xscript_domain_availability(clean_workbench)
        if not available:
            return _unavailable(
                clean_workbench,
                clean_engine,
                reason,
                domain=xscript_pack.domain,
            )
        return ModelingSurface(
            workbench=clean_workbench,
            engine=clean_engine,
            domain=xscript_pack.domain,
            surface_id=_surface_id(
                workbench=clean_workbench,
                engine=clean_engine,
                domain=xscript_pack.domain,
                generation="domain-v4-unified-lifecycle",
            ),
            core_tool_names=tuple(sorted(CORE_CONVERSATION_VIEW_TOOLS)),
            cad_tool_names=_provider_cad_tool_names(xscript_pack.tool_names),
            available=True,
            unavailable_reason="",
        )

    return _unavailable(
        clean_workbench,
        clean_engine,
        f"Unknown modeling engine: {clean_engine}.",
    )


def engine_from_service(service: Any) -> str:
    getter = getattr(service, "modeling_engine", None)
    if not callable(getter):
        raise RuntimeError("Cadex service has no modeling-engine accessor.")
    engine = str(getter() or "").strip().lower()
    if engine not in MODELING_ENGINES:
        raise RuntimeError(f"Cadex service returned invalid modeling engine {engine!r}.")
    return engine


def resolve_service_surface(service: Any, workbench: str | None) -> ModelingSurface:
    return resolve_modeling_surface(workbench, engine_from_service(service))


SCRIPTED_ENGINES: tuple[str, ...] = ("xscript",)


def _scripted_domains(names: Iterable[str], engine: str) -> set[str]:
    result: set[str] = set()
    for name in names:
        parts = str(name).split(".")
        if not parts or parts[0] != engine:
            continue
        if len(parts) == 3:
            result.add(parts[1])
        else:
            result.add("<malformed>")
    return result


def validate_surface_names(
    *,
    workbench: str | None,
    engine: str,
    names: Iterable[str],
    allowed_names: Iterable[str] | None = None,
) -> None:
    """Reject mixed engines, workbenches, domains, or undeclared names."""

    clean_names = [str(name or "").strip() for name in names]
    if any(not name for name in clean_names):
        raise ValueError("Every provider tool must have a non-empty name.")
    if len(clean_names) != len(set(clean_names)):
        raise ValueError("The provider surface contains duplicate tools.")
    scripted = {
        candidate
        for candidate in SCRIPTED_ENGINES
        if any(name.startswith(f"{candidate}.") for name in clean_names)
    }
    if len(scripted) > 1:
        raise ValueError(
            "The provider surface contains multiple modeling engines: "
            + ", ".join(sorted(scripted))
        )
    allowed = set(allowed_names) if allowed_names is not None else None
    expects_engine_tools = (
        any(name.startswith(f"{engine}.") for name in allowed) if allowed is not None else True
    )
    non_core_names = [
        name
        for name in clean_names
        if name.partition(".")[0] not in {"conversation", "core", "file"}
    ]
    if engine == "xscript":
        if scripted and scripted != {engine}:
            raise ValueError(f"The {engine} surface declaration does not match its tool schemas.")
        if expects_engine_tools and non_core_names and scripted != {engine}:
            raise ValueError(f"The {engine} surface declaration does not match its tool schemas.")
    if engine == "xscript" and scripted:
        native_cad = [
            name
            for name in clean_names
            if name.partition(".")[0] not in {"conversation", "core", "file", engine}
        ]
        if native_cad:
            raise ValueError(
                f"A {engine} surface cannot contain native workbench CAD tools: "
                + ", ".join(sorted(native_cad))
            )
        domains = _scripted_domains(clean_names, engine)
        if len(domains) != 1:
            raise ValueError(
                f"A {engine} surface must contain exactly one domain namespace."
            )
    if allowed is not None:
        undeclared = sorted(set(clean_names) - allowed)
        if undeclared:
            raise ValueError(
                "The provider surface contains tools outside the resolved tuple: "
                + ", ".join(undeclared)
            )


def infer_engine_from_names(names: Iterable[str]) -> str:
    values = [str(name or "") for name in names]
    engines = [
        engine
        for engine in SCRIPTED_ENGINES
        if any(name.startswith(f"{engine}.") for name in values)
    ]
    if len(engines) > 1:
        raise ValueError(
            "The provider surface contains multiple modeling engines: " + ", ".join(sorted(engines))
        )
    return engines[0] if engines else "xscript"
