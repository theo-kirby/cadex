# SPDX-License-Identifier: LGPL-2.1-or-later

"""Guardrail: every provider-callable tool is deliberate and structurally safe.

Four invariants are enforced:

1. No orphan provider tools — every provider-visible tool spec is surfaced through
   ``CORE_PROVIDER_TOOLS``, the registered ``tool_impl`` surface, or one of the
   scripted-engine session surfaces (``XSCRIPT_PROVIDER_TOOLS`` /
   ``XSCRIPT_PROVIDER_TOOLS``). A tool registered without any surface fails this
   test, so stale or experimental tools cannot silently become callable by
   default.
2. No dangling names — every name in ``CORE_PROVIDER_TOOLS`` and every pack
   ``tool_names`` entry resolves to a registered, validating :class:`ToolSpec`.
3. Writes are transactional — every non-READ tool either contains a FreeCAD
   transaction marker in its own module or in a same-package module it
   imports, or appears in a justified allowlist.
4. No command-string execution — ``tool_impl`` never contains
   ``runCommand``/``doCommand``/``sendMsgToActiveView``; all FreeCAD
   semantics run through the typed Python APIs.
"""

from __future__ import annotations

import ast
from importlib import import_module
from pathlib import Path
import re
from typing import Any, Iterator

import pytest

from CadexTools import SafetyLevel, ToolSpec, CadexTool
from tool_impl.service import TOOL_MODULE_NAMES

TOOL_PACKAGES = ("tool_impl.service", "tool_impl.sketcher")

TOOL_IMPL_DIR = Path(__file__).resolve().parent.parent / "tool_impl"

# Write-safety tools that legitimately run without a
# FreeCAD document transaction. Each entry needs a reason.
TRANSACTION_EXEMPT = {
    # Enters native sketch edit mode; changes UI state, not document data.
    "partdesign.edit_sketch",
    # Accepts native sketch edit mode; resetEdit owns the Sketcher transaction commit.
    "sketcher.close_sketch",
    # Writes an export file on disk; the FreeCAD document is never mutated.
    "file.export_model",
}

# Runner-handled engine tools carry only a spec in tool_impl; their document
# mutations run inside the engine module, so search it for markers too.
ENGINE_MODULES = {
    "xscript": TOOL_IMPL_DIR.parent / "CadexScriptedDomainPublication.py",
    # xscript reuses the shared xscript domain runtime/publication machinery.
    "xscript": TOOL_IMPL_DIR.parent / "CadexScriptedDomainPublication.py",
}

TRANSACTION_MARKERS = ("run_freecad_transaction", "openTransaction")

FORBIDDEN_COMMAND_STRINGS = ("runCommand", "doCommand", "sendMsgToActiveView")

_INTRA_PACKAGE_IMPORT = re.compile(
    r"^from\s+\.\s+import\s+(?P<plain>[\w,\s]+)$|^from\s+\.(?P<dotted>\w+)\s+import\s+",
    re.MULTILINE,
)


def _collect_specs() -> dict[str, tuple[ToolSpec, Path, str]]:
    """Return {tool name: (validated spec, module path, package name)}."""
    specs: dict[str, tuple[ToolSpec, Path, str]] = {}
    for package_name in TOOL_PACKAGES:
        package = import_module(package_name)
        for module_name in package.TOOL_MODULE_NAMES:
            module = import_module(f"{package_name}.{module_name}")
            spec = ToolSpec.from_mapping(module.TOOL_SPEC)
            if not spec.provider_visible:
                continue
            assert spec.name not in specs, (
                f"Duplicate tool name {spec.name!r} from {module.__file__}"
            )
            specs[spec.name] = (spec, Path(module.__file__), package_name)
    import CadexScriptedDomains as domains

    # xscript is now the only scripted engine; XSCRIPT_WORKBENCH_PACKS is an
    # alias of XSCRIPT_WORKBENCH_PACKS, so iterate the single pack set once.
    domain_path = TOOL_IMPL_DIR.parent / "CadexScriptedRuntime.py"
    for pack in domains.XSCRIPT_WORKBENCH_PACKS.values():
        for raw_spec in domains.domain_tool_specs(pack):
            spec = ToolSpec.from_mapping(raw_spec)
            assert spec.name not in specs
            specs[spec.name] = (spec, domain_path, "xscript.domain")
    return specs


@pytest.fixture(scope="module")
def specs() -> dict[str, tuple[ToolSpec, Path, str]]:
    return _collect_specs()


@pytest.fixture(scope="module")
def native_tool_names() -> frozenset[str]:
    """Provider-visible names registered by the ``tool_impl`` service/sketcher
    packages. The native workbench-pack registry was retired, so the registered
    ``tool_impl`` modules are the authoritative native surface for the guardrail's
    orphan/dangling invariants until those tools are culled in a later phase."""
    names: set[str] = set()
    for package_name in TOOL_PACKAGES:
        package = import_module(package_name)
        for module_name in package.TOOL_MODULE_NAMES:
            module = import_module(f"{package_name}.{module_name}")
            spec = ToolSpec.from_mapping(module.TOOL_SPEC)
            if spec.provider_visible:
                names.add(spec.name)
    return frozenset(names)


@pytest.fixture(scope="module")
def core_tools() -> frozenset[str]:
    import CadexSession as session

    return frozenset(session.CORE_PROVIDER_TOOLS)


@pytest.fixture(scope="module")
def engine_tools() -> frozenset[str]:
    import CadexSession as session
    import CadexScriptedDomains as domains
    from CadexModelingSurface import HIDDEN_PROVIDER_INSPECTION_TOOLS
    from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS

    return frozenset(
        session.XSCRIPT_PROVIDER_TOOLS
        | session.XSCRIPT_PROVIDER_TOOLS
        | set(HIDDEN_PROVIDER_INSPECTION_TOOLS)
        | {
            name
            for pack in domains.XSCRIPT_WORKBENCH_PACKS.values()
            for name in pack.tool_names
        }
        | {
            name
            for pack in XSCRIPT_WORKBENCH_PACKS.values()
            for name in pack.tool_names
        }
    )


def _surfaced_names(
    core_tools: frozenset[str],
    native_tool_names: frozenset[str],
    engine_tools: frozenset[str] = frozenset(),
) -> set[str]:
    return set(core_tools) | set(native_tool_names) | set(engine_tools)


def test_no_orphan_tools(specs, native_tool_names, core_tools, engine_tools) -> None:
    """1. Every registered tool must belong to core, the native surface, or an engine."""
    orphans = sorted(
        set(specs) - _surfaced_names(core_tools, native_tool_names, engine_tools)
    )
    assert not orphans, (
        "Tools registered but not surfaced by CORE_PROVIDER_TOOLS, the registered "
        "tool_impl surface, or an engine session surface (add to one or remove "
        f"the registration): {orphans}"
    )


def test_no_dangling_names(specs, native_tool_names, core_tools, engine_tools) -> None:
    """2. Every surfaced name must resolve to a registered spec."""
    dangling = sorted(
        _surfaced_names(core_tools, native_tool_names, engine_tools) - set(specs)
    )
    assert not dangling, (
        f"Names surfaced by core/native/engines with no registered tool spec: {dangling}"
    )


def _module_sources_with_local_imports(module_path: Path) -> Iterator[str]:
    """Yield the module source plus sources of same-package imports (BFS)."""
    queue = [module_path]
    visited: set[Path] = set()
    while queue:
        path = queue.pop()
        if path in visited or not path.is_file():
            continue
        visited.add(path)
        source = path.read_text(encoding="utf-8")
        yield source
        for match in _INTRA_PACKAGE_IMPORT.finditer(source):
            if match.group("dotted"):
                names = [match.group("dotted")]
            else:
                names = [
                    part.strip()
                    for part in (match.group("plain") or "").split(",")
                    if part.strip()
                ]
            queue.extend(path.parent / f"{name}.py" for name in names)


def test_write_tools_run_in_transactions(specs) -> None:
    """3. Every write tool reaches a FreeCAD transaction (possibly via helpers)."""
    read_levels = {SafetyLevel.READ, SafetyLevel.VIEW}
    offenders = []
    for name, (spec, path, _) in sorted(specs.items()):
        if spec.safety in read_levels or name in TRANSACTION_EXEMPT:
            continue
        module_paths = [path]
        engine_module = ENGINE_MODULES.get(name.split(".", 1)[0])
        if engine_module is not None:
            module_paths.append(engine_module)
        if not any(
            marker in source
            for module_path in module_paths
            for source in _module_sources_with_local_imports(module_path)
            for marker in TRANSACTION_MARKERS
        ):
            offenders.append(name)
    assert not offenders, (
        "Write-safety tools with no transaction marker in their module or "
        f"same-package imports: {offenders}"
    )


def test_transaction_exemptions_are_current(specs) -> None:
    """3b. Transaction exemptions must reference registered tools."""
    unknown = sorted(TRANSACTION_EXEMPT - set(specs))
    assert not unknown, f"Transaction-exempt tools no longer registered: {unknown}"


def test_no_legacy_command_execution() -> None:
    """4. tool_impl never shells out to GUI command names or script strings."""
    offenders = []
    for path in sorted(TOOL_IMPL_DIR.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_COMMAND_STRINGS:
            if pattern in source:
                offenders.append(f"{path.name}: {pattern}")
    assert not offenders, (
        "Legacy FreeCAD command-execution strings found in tool_impl "
        f"(implement via typed APIs instead): {offenders}"
    )


def test_intentionally_empty_packs_stay_empty() -> None:
    """TestWorkbench and NoneWorkbench must never surface CAD tools."""
    from CadexModelingSurface import resolve_modeling_surface
    from CadexScriptedDomains import get_xscript_pack

    for workbench in ("TestWorkbench", "NoneWorkbench"):
        assert get_xscript_pack(workbench) is None
        for engine in ("xscript", "xscript"):
            surface = resolve_modeling_surface(workbench, engine)
            assert surface.cad_tool_names == (), (
                f"{workbench} must stay empty; found {surface.cad_tool_names}"
            )


def test_native_tools_never_direct_the_provider_to_foreign_pack_tools(specs) -> None:
    """Native guidance may name only tools owned by its exact pack."""
    scripted_or_core = {"xscript", "xscript", "core", "conversation", "file"}
    native_namespaces = {
        name.split(".", 1)[0]
        for name in specs
        if "." in name and name.split(".", 1)[0] not in scripted_or_core
    }
    reference = re.compile(r"\b([a-z][a-z0-9_]*)\.([a-z][a-z0-9_]*)\b")
    offenders: dict[str, list[str]] = {}
    for name, (_spec, module_path, _package_name) in specs.items():
        owner = name.split(".", 1)[0]
        if owner in scripted_or_core:
            continue
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        foreign = sorted(
            {
                match.group(0)
                for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
                for match in reference.finditer(node.value)
                if match.group(1) in native_namespaces and match.group(1) != owner
            }
        )
        if foreign:
            offenders[name] = foreign
    assert not offenders, f"Native tools reference foreign pack tools: {offenders}"


# ---------------------------------------------------------------------------
# Scripted-engine surface guardrails: XScript integration is deliberate and
# does not regress the existing build123d/OpenSCAD surfaces.
# ---------------------------------------------------------------------------


def test_every_xscript_tool_is_surfaced(specs) -> None:
    """Every XScript spec belongs to exactly one engine/domain pack."""
    import CadexSession as session
    import CadexScriptedDomains as domains

    registered = {name for name in specs if name.startswith("xscript.")}
    assert registered, "expected registered xscript.* tool specs"
    surfaced = set(session.XSCRIPT_PROVIDER_TOOLS)
    surfaced.update(
        name
        for pack in domains.XSCRIPT_WORKBENCH_PACKS.values()
        for name in pack.tool_names
    )
    orphans = sorted(registered - surfaced)
    assert not orphans, (
        f"xscript tools registered but missing from XSCRIPT_PROVIDER_TOOLS: {orphans}"
    )


def test_every_surfaced_xscript_tool_is_registered(specs) -> None:
    """All Part Design and domain-qualified surface names are registered."""
    import CadexSession as session
    import CadexScriptedDomains as domains

    surfaced = {
        name
        for name in session.XSCRIPT_PROVIDER_TOOLS
        if name.startswith("xscript.")
    }
    surfaced.update(
        name
        for pack in domains.XSCRIPT_WORKBENCH_PACKS.values()
        for name in pack.tool_names
    )
    dangling = sorted(surfaced - set(specs))
    assert not dangling, (
        f"XSCRIPT_PROVIDER_TOOLS names unregistered tools: {dangling}"
    )


def test_engine_surface_table_covers_every_scripted_engine() -> None:
    """Each non-native engine gets a provider surface, and nothing else does."""
    import CadexSession as session
    from CadexProject import MODELING_ENGINES

    scripted_engines = set(MODELING_ENGINES) - {"native"}
    assert set(session.SCRIPTED_ENGINE_PROVIDER_TOOLS) == scripted_engines


def test_default_engine_is_xscript_with_a_provider_surface() -> None:
    """The out-of-box default engine is xscript, and its tool surface is
    registered so new projects are immediately usable without configuration."""
    import CadexSession as session
    from CadexProject import DEFAULT_MODELING_ENGINE, MODELING_ENGINES

    assert DEFAULT_MODELING_ENGINE == "xscript"
    assert DEFAULT_MODELING_ENGINE in MODELING_ENGINES
    surface = session.SCRIPTED_ENGINE_PROVIDER_TOOLS[DEFAULT_MODELING_ENGINE]
    assert surface, "default engine must expose a non-empty provider tool surface"


def test_runner_dispatch_is_empty_after_isolated_engine_removal() -> None:
    """The isolated build123d/openscad runner bridge was removed; xscript and
    xscript execute through the domain runtime, so no engine registers a runner."""
    import CadexSession as session

    assert session._SCRIPTED_RUNNER_BY_TOOL == {}
    assert session._SCRIPTED_ENGINE_RUNNERS == ()


class _SurfaceService:
    def __init__(self, engine: str) -> None:
        self.engine = engine

    def modeling_engine(self) -> str:
        return self.engine

    def _active_document(self) -> object:
        return object()


class _SpecRegistry:
    def __init__(self, specs: dict[str, tuple[ToolSpec, Path, str]]) -> None:
        self._specs = specs

    def get(self, name: str) -> CadexTool:
        return CadexTool(self._specs[name][0], None)


def test_provider_schema_build_captures_runtime_state_once(
    monkeypatch,
    specs: dict[str, tuple[ToolSpec, Path, str]],
) -> None:
    """Exact domain surfaces must not rebuild CAD state once per visible tool."""
    import CadexSession as session

    service = _SurfaceService("xscript")
    service.registry = _SpecRegistry(specs)
    calls: list[str] = []

    def runtime_state(_service: object) -> dict[str, Any]:
        calls.append("runtime")
        return {"edit_mode": None}

    monkeypatch.setattr(session, "_minimal_runtime_state", runtime_state)

    schemas = session.provider_tool_schemas(service, "PartWorkbench")

    assert calls == ["runtime"]
    assert any(schema["name"] == "xscript.part.create_program" for schema in schemas)
    assert not any(schema["name"].startswith("part.") for schema in schemas)


def test_provider_schema_build_reuses_turn_context_runtime_state(
    monkeypatch,
    specs: dict[str, tuple[ToolSpec, Path, str]],
) -> None:
    """Turn-start context may provide its already captured edit state."""
    import CadexSession as session

    service = _SurfaceService("xscript")
    service.registry = _SpecRegistry(specs)

    def unexpected_runtime_state(_service: object) -> dict[str, Any]:
        raise AssertionError("runtime state was captured twice")

    monkeypatch.setattr(session, "_minimal_runtime_state", unexpected_runtime_state)

    schemas = session.provider_tool_schemas(
        service,
        "PartWorkbench",
        runtime_state={"edit_mode": None},
    )

    assert schemas


def test_oversize_xscript_surface_warns_instead_of_raising(specs, caplog) -> None:
    """Crossing the tactical XScript budget warns; the turn still proceeds.

    A single production XScript domain surface already exceeds the tactical
    budget, so building it must not raise (experimental mode's bundled surfaces
    run far past it). The over-budget condition is reported as a warning.
    """
    import json
    import logging

    import CadexSession as session
    from CadexModelingSurface import resolve_modeling_surface

    surface = resolve_modeling_surface("PartDesignWorkbench", "xscript")
    schemas = [
        session._provider_schema_copy(
            specs[name][0].to_schema(active_workbench="PartDesignWorkbench")
        )
        for name in surface.tool_names
    ]

    def _bytes(payload: object) -> int:
        return len(
            json.dumps(
                payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        )

    # A compacted single-domain surface fits; pad one description so the whole
    # surface crosses the tactical budget the way an experimental bundle does.
    pad = session.MAX_XSCRIPT_TOOL_SCHEMAS_JSON_BYTES - _bytes(schemas) + 512
    schemas[0]["description"] = str(schemas[0].get("description", "")) + "x" * pad
    schema_bytes = _bytes(schemas)
    # Precondition: this surface is now genuinely over the tactical budget.
    assert schema_bytes > session.MAX_XSCRIPT_TOOL_SCHEMAS_JSON_BYTES
    assert schema_bytes <= session.MAX_PROVIDER_TOOL_SCHEMAS_JSON_BYTES

    # Experimental mode is the only mode now, so the over-budget condition is a
    # DEBUG-level "sending it anyway" notice rather than a WARNING popup.
    with caplog.at_level(logging.DEBUG, logger="Cadex.session"):
        snapshot = session._turn_start_tool_surface(
            "PartDesignWorkbench", schemas, resolution=surface
        )

    assert snapshot["kind"] == "turn_start_snapshot"
    assert snapshot["schema_count"] == len(schemas)
    assert any("tactical" in record.message for record in caplog.records)


def test_all_exact_surfaces_fit_their_model_context_budgets(specs) -> None:
    """All workbench surfaces stay under the hard transport ceiling.

    The tactical XScript budget (``MAX_XSCRIPT_TOOL_SCHEMAS_JSON_BYTES``)
    is a discipline signal, not a hard cap: crossing it warns and the turn
    proceeds, so it is intentionally not asserted here. Only the real transport
    ceiling is enforced.
    """

    import json

    import CadexProvider as provider
    import CadexSession as session
    import CadexScriptedDomains as domains
    from CadexModelingSurface import resolve_modeling_surface

    observed_workbenches = 0
    for workbench in domains.XSCRIPT_WORKBENCH_PACKS:
        if workbench in {"NoneWorkbench", "TestWorkbench"}:
            continue
        observed_workbenches += 1
        for engine in ("xscript",):
            surface = resolve_modeling_surface(workbench, engine)
            schemas = [
                session._provider_schema_copy(
                    specs[name][0].to_schema(active_workbench=workbench)
                )
                for name in surface.tool_names
            ]
            schema_bytes = len(
                json.dumps(
                    schemas,
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
            snapshot = session._turn_start_tool_surface(
                workbench,
                schemas,
                resolution=surface,
            )
            assert snapshot["schema_count"] == len(schemas)
            assert schema_bytes <= session.MAX_PROVIDER_TOOL_SCHEMAS_JSON_BYTES

            context = {
                "workbench": workbench,
                "modeling_surface": surface.summary(),
                "provider_tool_schemas": schemas,
            }
            instructions = provider._provider_instructions(context)
            assert (
                len(instructions.encode("utf-8"))
                <= provider.MAX_PROVIDER_INSTRUCTIONS_BYTES
            )

    assert observed_workbenches == 4


@pytest.mark.parametrize(
    ("workbench", "production_ready"),
    (
        ("PartWorkbench", True),
        ("SketcherWorkbench", True),
        ("AssemblyWorkbench", True),
    ),
)
def test_selected_xscript_replaces_representative_native_surfaces(
    workbench: str,
    production_ready: bool,
) -> None:
    import CadexSession as session
    from CadexScriptedDomains import get_xscript_pack

    service = _SurfaceService("xscript")
    names = session._surface_tool_names(service, workbench)

    domain_pack = get_xscript_pack(workbench)
    assert domain_pack is not None
    assert domain_pack.production_ready is production_ready
    if production_ready:
        visible_domain_tools = {
            name
            for name in domain_pack.tool_names
            if not name.endswith(".describe_api")
            and not name.endswith(".inspect_program")
        }
        assert visible_domain_tools <= names
        assert "core.inspect" in names
        assert len([name for name in names if name.startswith("xscript.")]) == 6
    else:
        assert not any(name.startswith("xscript.") for name in names)


def test_selected_xscript_surfaces_only_its_own_domain_pack() -> None:
    import CadexSession as session

    # xscript is the sole scripted engine; selecting it for a user workbench
    # surfaces exactly that workbench's xscript domain pack and never leaks a
    # foreign domain's tools.
    names = session._surface_tool_names(
        _SurfaceService("xscript"),
        "AssemblyWorkbench",
    )
    scripted = {name for name in names if name.startswith("xscript.")}
    assert scripted
    assert {name.split(".")[1] for name in scripted} == {"assembly"}


def test_partdesign_xscript_surface_is_its_exact_domain_pack() -> None:
    import CadexSession as session
    from CadexModelingSurface import resolve_modeling_surface

    expected = (
        "conversation.ask_user",
        "core.capture_view_screenshot",
        "core.inspect",
        "core.relink_object",
        "core.set_view",
        "file.export_model",
        "file.import_model",
        "file.link_external_part",
        "xscript.partdesign.create_program",
        "xscript.partdesign.edit_source",
        "xscript.partdesign.set_inputs",
        "xscript.partdesign.set_parameter_controls",
        "xscript.partdesign.reconfigure_program",
        "xscript.partdesign.delete_program",
    )
    surface = resolve_modeling_surface("PartDesignWorkbench", "xscript")
    names = session._surface_tool_names(
        _SurfaceService("xscript"), "PartDesignWorkbench"
    )
    assert surface.tool_names == expected
    assert names == set(expected)
    assert {name.split(".")[1] for name in names if name.startswith("xscript.")} == {
        "partdesign"
    }


def test_retired_surface_and_publication_shims_are_absent() -> None:
    import CadexScriptedDomainPublication as publication

    # The native workbench-tool pack module was retired entirely.
    with pytest.raises(ModuleNotFoundError):
        import_module("CadexWorkbenchTools")
    assert not hasattr(publication, "_configure_material")
    # The culled-domain worker modules were removed entirely.
    with pytest.raises(ModuleNotFoundError):
        import_module("xscript_cam_worker")
    assert "core_delete_object" not in TOOL_MODULE_NAMES


def test_non_user_workbenches_do_not_gain_xscript() -> None:
    import CadexSession as session

    service = _SurfaceService("xscript")
    for workbench in (None, "NoneWorkbench", "TestWorkbench", "UnknownWorkbench"):
        names = session._surface_tool_names(service, workbench)
        assert not any(name.startswith("xscript.") for name in names)


def test_every_constructed_surface_contains_at_most_one_scripted_engine() -> None:
    import CadexSession as session
    import CadexScriptedDomains as domains

    prefixes = tuple(f"{engine}." for engine in session.SCRIPTED_ENGINE_PROVIDER_TOOLS)
    for engine in session.SCRIPTED_ENGINE_PROVIDER_TOOLS:
        service = _SurfaceService(engine)
        for workbench in domains.XSCRIPT_WORKBENCH_PACKS:
            names = session._surface_tool_names(service, workbench)
            surfaced_engines = {
                prefix
                for prefix in prefixes
                if any(name.startswith(prefix) for name in names)
            }
            assert len(surfaced_engines) <= 1, (
                f"{workbench} with {engine} surfaced {sorted(surfaced_engines)}"
            )


def test_real_xscript_workbench_schemas_form_valid_codex_snapshots(specs) -> None:
    """Every extended native pack must survive the subscription wire format."""
    import CadexProvider as provider
    import CadexSession as session
    import CadexScriptedDomains as domains

    service = _SurfaceService("xscript")
    for workbench in domains.XSCRIPT_WORKBENCH_PACKS:
        if workbench in {"NoneWorkbench", "TestWorkbench"}:
            continue
        names = session._surface_tool_names(service, workbench)
        schemas = [
            session._provider_schema_copy(
                specs[name][0].to_schema(active_workbench=workbench)
            )
            for name in sorted(names)
            if specs[name][0].supports_edit_mode("none")
        ]
        snapshot = session._turn_start_tool_surface(workbench, schemas)
        dynamic_tools, dynamic_names = provider._codex_dynamic_tool_surface(
            {
                "provider_tool_schemas": schemas,
                "provider_tool_surface": snapshot,
            }
        )

        assert dynamic_tools, workbench
        assert set(dynamic_names.values()) == {
            str(schema["name"]) for schema in schemas
        }, workbench


def test_experimental_xscript_surface_survives_provider_transport(
    specs, monkeypatch
) -> None:
    """The native Parts union was retired: experimental mode now serves exactly
    the resolved xscript surface. The frozen turn-start snapshot must still
    survive provider transport instead of raising ProviderUnavailable.
    """
    import CadexProvider as provider
    import CadexSession as session
    from CadexModelingSurface import resolve_modeling_surface

    monkeypatch.setattr(session, "_experimental_mode_session", lambda: True)

    surface = resolve_modeling_surface("PartDesignWorkbench", "xscript")
    names = sorted(set(surface.tool_names))
    schemas = [
        session._provider_schema_copy(
            specs[name][0].to_schema(active_workbench="PartDesignWorkbench")
        )
        for name in names
        if specs[name][0].supports_edit_mode("none")
    ]
    # Precondition: the surface is a single xscript namespace (no native extras).
    prefixes = {
        name.partition(".")[0]
        for name in names
        if name.partition(".")[0] not in {"conversation", "core", "file"}
    }
    assert prefixes == {"xscript"}

    snapshot = session._turn_start_tool_surface(
        "PartDesignWorkbench", schemas, resolution=surface, engine="xscript"
    )

    # This must not raise ProviderUnavailable.
    dynamic_tools, dynamic_names = provider._codex_dynamic_tool_surface(
        {"provider_tool_schemas": schemas, "provider_tool_surface": snapshot}
    )
    assert dynamic_tools
    assert set(dynamic_names.values()) == {str(schema["name"]) for schema in schemas}


def test_xscript_uses_only_domain_qualified_v2_lifecycle_tools(specs) -> None:
    removed_names = {
        "xscript.describe_api",
        "xscript.inspect_model",
        "xscript.create_model",
        "xscript.edit_source",
        "xscript.set_parameters",
        "xscript.reconfigure_model",
        "xscript.delete_model",
    }
    assert removed_names.isdisjoint(specs)

    lifecycle = {
        "set_parameter_controls",
        "describe_api",
        "inspect_program",
        "create_program",
        "edit_source",
        "set_inputs",
        "reconfigure_program",
        "delete_program",
    }
    domain_names = {name for name in specs if name.startswith("xscript.")}
    assert domain_names
    for name in domain_names:
        namespace, domain, operation = name.split(".")
        assert namespace == "xscript"
        assert domain
        assert operation in lifecycle


def test_domain_lifecycle_schemas_accept_bounded_structured_inputs(specs) -> None:
    from CadexTools import ToolArgumentValidationError

    create, _, _ = specs["xscript.partdesign.create_program"]
    valid = {
        "program_name": "Parametric Bracket",
        "source": "result = {'Part': api.body(api.pad(api.sketch([api.circle([0,0], inputs['radius'])]), inputs['height']))}",
        "input_schema": {
            "type": "object",
            "properties": {
                "radius": {"type": "number", "exclusiveMinimum": 0},
                "height": {"type": "number", "exclusiveMinimum": 0},
                "variant": {"type": "string", "enum": ["short", "tall"]},
                "offsets": {
                    "type": "array",
                    "items": {"type": "number"},
                    "maxItems": 8,
                },
            },
            "required": ["radius", "height", "variant", "offsets"],
            "additionalProperties": False,
        },
        "inputs": {
            "radius": 4.0,
            "height": 12.0,
            "variant": "short",
            "offsets": [0.0, 5.0],
        },
        "expected_outputs": [{"name": "Part", "type": "solid"}],
    }
    create.validate_arguments(valid)

    with pytest.raises(ToolArgumentValidationError):
        create.validate_arguments(
            {
                **valid,
                "expected_outputs": [{"name": "Part", "type": "mesh"}],
            }
        )


def test_each_domain_describe_api_matches_its_runtime_and_is_json_safe() -> None:
    import json

    import CadexScriptedDomains as domains

    for pack in domains.XSCRIPT_WORKBENCH_PACKS.values():
        adapter = domains.get_domain_adapter(pack.domain)
        assert adapter is not None
        payload = adapter.describe_api()
        assert json.loads(json.dumps(payload)) == payload
        assert payload["domain"] == pack.domain
        assert payload["workbench"] == pack.workbench
        assert payload["source_globals"] == ["doc", "inputs", "x"]
        assert [entry["name"] for entry in payload["runtime_exports"]] == list(
            pack.api_exports
        )


def test_core_inspect_is_the_only_model_facing_xscript_read_tool(specs) -> None:
    import CadexSession as session

    assert "core.inspect" in session.XSCRIPT_PROVIDER_TOOLS
    for name in session.XSCRIPT_PROVIDER_TOOLS:
        assert not name.endswith(".describe_api")
        assert not name.endswith(".inspect_program")

    for name, (spec, _, _) in specs.items():
        if not name.startswith("xscript.") or not name.endswith(
            (".describe_api", ".inspect_program")
        ):
            continue
        assert spec.safety == SafetyLevel.READ


def test_removed_partdesign_runtime_files_do_not_exist() -> None:
    removed = (
        "CadexXScript.py",
        "xscript_api.py",
        "xscript_executor.py",
        "xscript_worker.py",
    )
    root = TOOL_IMPL_DIR.parent
    assert all(not (root / name).exists() for name in removed)


def test_removed_hidden_delete_compatibility_tool_does_not_exist() -> None:
    assert not (TOOL_IMPL_DIR / "core_delete_object.py").exists()


def test_removed_engine_and_xscript_forwarders_do_not_exist() -> None:
    import CadexCore as core
    import CadexProject as project

    for owner in (core.CadexService, project.CadexProjectStore):
        assert not hasattr(owner, "partdesign_engine")
        assert not hasattr(owner, "partdesign_engine_state")
        assert not hasattr(owner, "set_partdesign_engine")
    assert not hasattr(project, "PARTDESIGN_ENGINES")
    assert not hasattr(project, "DEFAULT_PARTDESIGN_ENGINE")
