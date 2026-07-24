# SPDX-License-Identifier: LGPL-2.1-or-later

"""Guardrail: every provider-callable tool is deliberate and structurally safe.

Phase 2.4 (ADR-013) dissolved the per-domain multi-program tool surface; the
ONLY mutation surface is now ``xscript.project.{write_script, edit_script,
set_params}`` plus the read-only ``xscript.project.describe_api``, and every
model-facing read lives in ``core.inspect``. The invariants enforced here:

1. No orphan provider tools — every provider-visible tool spec is surfaced
   through ``CORE_PROVIDER_TOOLS``, the registered ``tool_impl`` surface, or
   the project engine surface (``XSCRIPT_PROVIDER_TOOLS``).
2. No dangling names — every surfaced name resolves to a registered,
   validating :class:`ToolSpec`.
3. Writes are transactional — every non-READ tool either contains a FreeCAD
   transaction marker in its own module or in a same-package module it
   imports, or appears in a justified allowlist.
4. No command-string execution — ``tool_impl`` never contains
   ``runCommand``/``doCommand``/``sendMsgToActiveView``.
5. The xscript surface is EXACTLY the four project tools on every workbench,
   and the dissolved per-domain lifecycle tools stay gone.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import re
from typing import Any, Iterator

import pytest

from CadexTools import SafetyLevel, ToolSpec, CadexTool
from tool_impl.service import TOOL_MODULE_NAMES

TOOL_PACKAGES = ("tool_impl.service", "tool_impl.sketcher")

TOOL_IMPL_DIR = Path(__file__).resolve().parent.parent / "tool_impl"

PROJECT_TOOL_NAMES = (
    "xscript.project.describe_api",
    "xscript.project.write_script",
    "xscript.project.edit_script",
    "xscript.project.set_params",
)

#: The dissolved per-domain lifecycle operations. They stay gone: no registered
#: tool spec may ever carry one of these operation names again (ADR-013).
DISSOLVED_OPERATIONS = frozenset(
    {
        "create_program",
        "edit_source",
        "set_inputs",
        "set_parameter_controls",
        "reconfigure_program",
        "delete_program",
        "inspect_program",
    }
)

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

# Runner-handled engine tools carry only a spec outside tool_impl; their
# document mutations run inside the publication module, so search it for
# transaction markers too.
ENGINE_MODULES = {
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

    runtime_path = TOOL_IMPL_DIR.parent / "CadexScriptedRuntime.py"
    for raw_spec in domains.project_tool_specs():
        spec = ToolSpec.from_mapping(raw_spec)
        assert spec.name not in specs
        specs[spec.name] = (spec, runtime_path, "xscript.project")
    return specs


@pytest.fixture(scope="module")
def specs() -> dict[str, tuple[ToolSpec, Path, str]]:
    return _collect_specs()


@pytest.fixture(scope="module")
def native_tool_names() -> frozenset[str]:
    """Provider-visible names registered by the ``tool_impl`` service/sketcher
    packages. These native tools are registered but no longer surfaced by any
    session surface; they are slated for culling in a later phase."""
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

    return frozenset(session.XSCRIPT_PROVIDER_TOOLS)


def _surfaced_names(
    core_tools: frozenset[str],
    native_tool_names: frozenset[str],
    engine_tools: frozenset[str] = frozenset(),
) -> set[str]:
    return set(core_tools) | set(native_tool_names) | set(engine_tools)


def test_no_orphan_tools(specs, native_tool_names, core_tools, engine_tools) -> None:
    """1. Every registered tool must belong to core, the native surface, or the engine."""
    orphans = sorted(
        set(specs) - _surfaced_names(core_tools, native_tool_names, engine_tools)
    )
    assert not orphans, (
        "Tools registered but not surfaced by CORE_PROVIDER_TOOLS, the registered "
        "tool_impl surface, or the project engine surface (add to one or remove "
        f"the registration): {orphans}"
    )


def test_no_dangling_names(specs, native_tool_names, core_tools, engine_tools) -> None:
    """2. Every surfaced name must resolve to a registered spec."""
    dangling = sorted(
        _surfaced_names(core_tools, native_tool_names, engine_tools) - set(specs)
    )
    assert not dangling, (
        f"Names surfaced by core/native/engine with no registered tool spec: {dangling}"
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


# ---------------------------------------------------------------------------
# The project surface: exactly four xscript.project.* tools, globally.
# ---------------------------------------------------------------------------


def test_xscript_surface_is_exactly_the_project_tools() -> None:
    """5. The engine surface is the core tools plus the four project tools."""
    import CadexSession as session
    from CadexModelingSurface import CORE_CONVERSATION_VIEW_TOOLS

    assert session.XSCRIPT_PROVIDER_TOOLS == {
        *CORE_CONVERSATION_VIEW_TOOLS,
        *PROJECT_TOOL_NAMES,
    }


def test_every_registered_xscript_tool_is_a_project_tool(specs) -> None:
    registered = sorted(name for name in specs if name.startswith("xscript."))
    assert registered == sorted(PROJECT_TOOL_NAMES)
    for name in registered:
        namespace, domain, operation = name.split(".")
        assert namespace == "xscript"
        assert domain == "project"
        assert operation in {"describe_api", "write_script", "edit_script", "set_params"}


def test_dissolved_per_domain_lifecycle_tools_stay_gone(specs) -> None:
    """The per-domain lifecycle operations must never be registered again."""
    offenders = sorted(
        name
        for name in specs
        if name.rsplit(".", 1)[-1] in DISSOLVED_OPERATIONS
    )
    assert not offenders, (
        f"Dissolved per-domain lifecycle tools re-registered (ADR-013): {offenders}"
    )


def test_resolved_surface_is_global_and_identical_for_all_workbenches() -> None:
    from CadexModelingSurface import resolve_modeling_surface

    surfaces = [
        resolve_modeling_surface(workbench, "xscript")
        for workbench in (
            "PartDesignWorkbench",
            "PartWorkbench",
            "SketcherWorkbench",
            "AssemblyWorkbench",
            "TestWorkbench",
            "NoneWorkbench",
            "UnknownWorkbench",
            None,
        )
    ]
    assert len({surface.surface_id for surface in surfaces}) == 1
    for surface in surfaces:
        assert surface.available is True
        assert surface.domain == "project"
        assert surface.cad_tool_names == PROJECT_TOOL_NAMES
        assert "core.inspect" in surface.tool_names


def test_project_write_tools_are_safe_write_and_revision_guarded(specs) -> None:
    for name in PROJECT_TOOL_NAMES:
        spec, _, _ = specs[name]
        if name.endswith(".describe_api"):
            assert spec.safety == SafetyLevel.READ
            continue
        assert spec.safety == SafetyLevel.SAFE_WRITE
        assert "expected_revision" in spec.parameters["properties"]
        assert "expected_revision" in spec.parameters["required"]


def test_core_inspect_is_the_only_model_facing_read_scope_owner(specs) -> None:
    """Reads live in core.inspect; the one engine read tool is describe_api."""
    import CadexSession as session

    assert "core.inspect" in session.XSCRIPT_PROVIDER_TOOLS
    engine_reads = [
        name
        for name in session.XSCRIPT_PROVIDER_TOOLS
        if name.startswith("xscript.") and specs[name][0].safety == SafetyLevel.READ
    ]
    assert engine_reads == ["xscript.project.describe_api"]
    inspect_scopes = specs["core.inspect"][0].parameters["properties"]["scope"]["enum"]
    assert "script" in inspect_scopes
    assert "domain" not in inspect_scopes
    assert "program" not in inspect_scopes


# ---------------------------------------------------------------------------
# Engine table, transport budgets, and session construction
# ---------------------------------------------------------------------------


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
    """The isolated build123d/openscad runner bridge was removed; the project
    lifecycle executes through the runtime, so no engine registers a runner."""
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
    """The surface build must not rebuild CAD state once per visible tool."""
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
    assert any(schema["name"] == "xscript.project.write_script" for schema in schemas)
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


def test_project_surface_fits_every_model_context_budget(specs) -> None:
    """The global surface stays under the tactical budget and the transport
    ceiling on every workbench, and the provider instructions stay bounded."""
    import json

    import CadexProvider as provider
    import CadexSession as session
    from CadexModelingSurface import resolve_modeling_surface

    for workbench in (
        "PartDesignWorkbench",
        "PartWorkbench",
        "SketcherWorkbench",
        "AssemblyWorkbench",
        None,
    ):
        surface = resolve_modeling_surface(workbench, "xscript")
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


def test_session_surface_names_match_the_resolved_surface() -> None:
    import CadexSession as session
    from CadexModelingSurface import resolve_modeling_surface

    for workbench in (
        "PartDesignWorkbench",
        "AssemblyWorkbench",
        "UnknownWorkbench",
        None,
    ):
        surface = resolve_modeling_surface(workbench, "xscript")
        names = session._surface_tool_names(_SurfaceService("xscript"), workbench)
        assert names == set(surface.tool_names)
        assert {
            name.split(".")[1] for name in names if name.startswith("xscript.")
        } == {"project"}


def test_real_project_schemas_form_valid_codex_snapshots(specs) -> None:
    """The global surface must survive the subscription wire format."""
    import CadexProvider as provider
    import CadexSession as session

    service = _SurfaceService("xscript")
    names = session._surface_tool_names(service, "PartDesignWorkbench")
    schemas = [
        session._provider_schema_copy(
            specs[name][0].to_schema(active_workbench="PartDesignWorkbench")
        )
        for name in sorted(names)
        if specs[name][0].supports_edit_mode("none")
    ]
    snapshot = session._turn_start_tool_surface("PartDesignWorkbench", schemas)
    dynamic_tools, dynamic_names = provider._codex_dynamic_tool_surface(
        {
            "provider_tool_schemas": schemas,
            "provider_tool_surface": snapshot,
        }
    )

    assert dynamic_tools
    assert set(dynamic_names.values()) == {str(schema["name"]) for schema in schemas}


# ---------------------------------------------------------------------------
# Removed machinery stays gone
# ---------------------------------------------------------------------------


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


def test_removed_editor_and_per_domain_runtime_stay_gone() -> None:
    """The Model Code Editor and the per-domain lifecycle stay deleted."""
    with pytest.raises(ModuleNotFoundError):
        import_module("CadexScriptedEditor")
    import CadexScriptedRuntime as runtime
    import CadexScriptedDomains as domains

    for symbol in (
        # per-domain lifecycle (Runtime)
        "capture_operation_state",
        "prepare_candidate",
        "finalize_candidate",
        "capture_reference_inputs",
        "validate_candidate",
        "accept_candidate",
        "retain_candidate",
        "prepare_delete",
        "finish_delete",
        "restore_prepared_delete",
        "complete_inspection",
        "capture_inspection_state",
        "capture_editor_inspection_state",
        "apply_parameter_controls",
        "clean_parameter_controls",
        "prune_controls",
        "parse_domain_tool",
    ):
        assert not hasattr(runtime, symbol), symbol
    for symbol in (
        # per-domain tool specs and the adapter registry (Domains)
        "domain_tool_specs",
        "register_domain_tools",
        "get_domain_adapter",
        "register_domain_adapter",
        "domain_availability",
        "migrate_program_manifest",
        "program_revision",
        "program_revision_with_references",
        "LIFECYCLE_OPERATIONS",
    ):
        assert not hasattr(domains, symbol), symbol


def test_removed_partdesign_runtime_files_do_not_exist() -> None:
    removed = (
        "CadexXScript.py",
        "xscript_api.py",
        "xscript_executor.py",
        "xscript_worker.py",
        "CadexScriptedEditor.py",
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


def test_publication_has_no_worker_or_artifact_io() -> None:
    """Publication applies validated detached values; it never touches worker
    processes or artifact files (those run off the document thread)."""
    import inspect as _inspect

    import CadexScriptedDomainPublication as publication

    source = _inspect.getsource(publication)
    for forbidden in (
        "subprocess.",
        "run_process(",
        ".wait(",
        "read_text(",
        "write_text(",
        "importBrep(",
        "exportBrep(",
    ):
        assert forbidden not in source
