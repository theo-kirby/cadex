# SPDX-License-Identifier: LGPL-2.1-or-later

"""Experimental mode's scripted-engine "Parts" tool surface.

The native Parts union was retired: experimental mode now serves exactly the
resolved scripted-engine (xscript/xscript) surface for the workbench, with no
extra native Part/Assembly tools. Manual mode must stay byte-identical to today,
and the ChatGPT-subscription fixed-surface contract must accept the resolved
surface — otherwise subscription turns silently zero out every tool.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

import pytest

import CadexSession as session
import CadexScriptedDomains as domains
from CadexModelingSurface import resolve_modeling_surface
from CadexTools import SafetyLevel, ToolSpec


def _resolved_surface_names(workbench: str, engine: str) -> set[str]:
    """The authoritative single-workbench surface names for (workbench, engine).

    ``_surface_tool_names`` resolves exactly one workbench pack (its core view
    tools plus that pack's provider-visible CAD tools). Expectations are derived
    from the same resolver so they track the exact-surface architecture instead
    of the retired global provider-tool unions.
    """
    return set(resolve_modeling_surface(workbench, engine).tool_names)

TOOL_PACKAGES = ("tool_impl.service", "tool_impl.sketcher")


def _collect_specs() -> dict[str, ToolSpec]:
    specs: dict[str, ToolSpec] = {}
    for package_name in TOOL_PACKAGES:
        package = import_module(package_name)
        for module_name in package.TOOL_MODULE_NAMES:
            module = import_module(f"{package_name}.{module_name}")
            spec = ToolSpec.from_mapping(module.TOOL_SPEC)
            specs[spec.name] = spec
    # The surface resolves the global project tools, so the fake registry
    # must carry their specs too.
    for raw_spec in domains.project_tool_specs():
        spec = ToolSpec.from_mapping(raw_spec)
        specs[spec.name] = spec
    return specs


@pytest.fixture(scope="module")
def specs() -> dict[str, ToolSpec]:
    return _collect_specs()


class _Registry:
    def __init__(self, specs: dict[str, ToolSpec]) -> None:
        self._specs = specs

    def get(self, name: str) -> ToolSpec:
        return self._specs[name]


class _FakeService:
    def __init__(
        self,
        specs: dict[str, ToolSpec],
        engine: str = "xscript",
        has_document: bool = True,
    ) -> None:
        self.registry = _Registry(specs)
        self._engine = engine
        self._has_document = has_document

    def modeling_engine(self) -> str:
        return self._engine

    def _active_document(self) -> Any:
        return object() if self._has_document else None


def _set_experimental_mode(monkeypatch: pytest.MonkeyPatch, enabled: bool) -> None:
    monkeypatch.setattr(session, "_experimental_mode_session", lambda: enabled)


def test_manual_xscript_surface_is_unchanged(specs, monkeypatch) -> None:
    _set_experimental_mode(monkeypatch, False)
    service = _FakeService(specs, engine="xscript")
    names = session._surface_tool_names(service, "PartDesignWorkbench")
    # Manual mode resolves exactly the PartDesign xscript domain surface.
    assert names == _resolved_surface_names("PartDesignWorkbench", "xscript")
    assert "xscript.project.write_script" in names


def test_experimental_xscript_surface_is_the_resolved_surface(
    specs, monkeypatch
) -> None:
    _set_experimental_mode(monkeypatch, True)
    service = _FakeService(specs, engine="xscript")
    names = session._surface_tool_names(service, "PartDesignWorkbench")
    # Experimental mode serves exactly the resolved xscript authoring surface.
    assert names == _resolved_surface_names("PartDesignWorkbench", "xscript")
    assert "xscript.project.write_script" in names


def test_turn_start_surface_accepts_experimental_xscript_surface(monkeypatch) -> None:
    _set_experimental_mode(monkeypatch, True)
    names = sorted(set(session.XSCRIPT_PROVIDER_TOOLS))
    schemas = [{"name": name, "parameters": {}} for name in names]
    surface = session._turn_start_tool_surface(
        "PartDesignWorkbench", schemas, engine="xscript"
    )
    assert surface["kind"] == "turn_start_snapshot"
    assert surface["engine"] == "xscript"
    assert surface["tool_names"] == names


def test_experimental_no_document_filter_still_applies(specs, monkeypatch) -> None:
    _set_experimental_mode(monkeypatch, True)
    service = _FakeService(specs, engine="xscript", has_document=False)
    names = session._surface_tool_names(service, "PartDesignWorkbench")
    assert names
    read_levels = {SafetyLevel.READ, SafetyLevel.VIEW}
    assert all(specs[name].safety in read_levels for name in names)


def test_turn_start_surface_plain_xscript_still_fixed(monkeypatch) -> None:
    _set_experimental_mode(monkeypatch, False)
    # The exact-surface architecture serves one domain namespace per workbench,
    # so freeze the resolved PartDesign xscript surface (not the retired
    # cross-domain provider-tool union, which the validator rejects).
    names = sorted(_resolved_surface_names("PartDesignWorkbench", "xscript"))
    schemas = [{"name": name, "parameters": {}} for name in names]
    surface = session._turn_start_tool_surface(
        "PartDesignWorkbench", schemas, engine="xscript"
    )
    assert surface["kind"] == "turn_start_snapshot"
    assert surface["frozen"] is True
    assert surface["engine"] == "xscript"
