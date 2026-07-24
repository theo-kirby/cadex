# SPDX-License-Identifier: LGPL-2.1-or-later

"""Exact modeling-engine surface resolution.

This is the single authority for deciding which CAD authoring surface exists.
Since the Phase 2.4 tool-surface swap (ADR-013) the surface is GLOBAL: the
xscript engine serves exactly one authoring surface — the four
``xscript.project.*`` tools of the single project script — regardless of the
active FreeCAD workbench. The workbench no longer selects a domain. Runtime
filters may remove tools for document/edit-state reasons, but they may not add
tools to the resolved tuple.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Iterable

from CadexScriptedDomains import PROJECT_PACK

MODELING_ENGINES = frozenset({"xscript"})

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


def _surface_id(*, engine: str, domain: str | None, generation: str) -> str:
    # The surface is global: the workbench deliberately does not participate,
    # so switching workbenches never changes the surface identity.
    readable = "/".join(
        (
            "cadex",
            "surface",
            "global",
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
) -> ModelingSurface:
    return ModelingSurface(
        workbench=workbench,
        engine=engine,
        domain=None,
        surface_id=_surface_id(
            engine=engine,
            domain=None,
            generation="project-v1-unavailable",
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
    """Resolve the one global project surface for ``engine``."""

    clean_engine = str(engine or "").strip().lower()
    clean_workbench = str(workbench or "").strip() or None
    if clean_engine not in MODELING_ENGINES:
        return _unavailable(
            clean_workbench,
            clean_engine or "unknown",
            f"Unknown modeling engine: {clean_engine or '<missing>'}.",
        )
    return ModelingSurface(
        workbench=clean_workbench,
        engine=clean_engine,
        domain=PROJECT_PACK.domain,
        surface_id=_surface_id(
            engine=clean_engine,
            domain=PROJECT_PACK.domain,
            generation="project-v1-single-script",
        ),
        core_tool_names=tuple(sorted(CORE_CONVERSATION_VIEW_TOOLS)),
        cad_tool_names=tuple(PROJECT_PACK.tool_names),
        available=True,
        unavailable_reason="",
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
    """Reject mixed engines, foreign namespaces, or undeclared names."""

    del workbench  # The surface is global; the workbench carries no authority.
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
        if domains != {PROJECT_PACK.domain}:
            raise ValueError(
                f"A {engine} surface must contain exactly the project namespace."
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
