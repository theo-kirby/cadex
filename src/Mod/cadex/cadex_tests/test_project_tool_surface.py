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

from CadexTools import SafetyLevel, ToolSpec


MODULE_DIR = Path(__file__).resolve().parent.parent

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
    "xscript": MODULE_DIR / "CadexScriptedDomainPublication.py",
}

TRANSACTION_MARKERS = ("run_freecad_transaction", "openTransaction")

FORBIDDEN_COMMAND_STRINGS = ("runCommand", "doCommand", "sendMsgToActiveView")

_INTRA_PACKAGE_IMPORT = re.compile(
    r"^from\s+\.\s+import\s+(?P<plain>[\w,\s]+)$|^from\s+\.(?P<dotted>\w+)\s+import\s+",
    re.MULTILINE,
)


def _collect_specs() -> dict[str, tuple[ToolSpec, Path, str]]:
    """Return {tool name: (validated spec, module path, package name)}.

    Since Phase 7 the engine registers exactly one surface: THE project
    script's tools. The ``tool_impl`` service/sketcher packages that used to
    contribute the rest were deleted with the provider stack (ADR-021).
    """
    specs: dict[str, tuple[ToolSpec, Path, str]] = {}
    import CadexScriptedDomains as domains

    runtime_path = MODULE_DIR / "CadexScriptedRuntime.py"
    for raw_spec in domains.project_tool_specs():
        spec = ToolSpec.from_mapping(raw_spec)
        assert spec.name not in specs, spec.name
        specs[spec.name] = (spec, runtime_path, "xscript.project")
    return specs


@pytest.fixture(scope="module")
def specs() -> dict[str, tuple[ToolSpec, Path, str]]:
    return _collect_specs()






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
    """Reads live in one inspect op; the one engine read tool is describe_api.

    ``core.inspect``'s ToolSpec lived in tool_impl and died with it; cadexd's
    ``inspect`` op is the surviving owner of the same contract.
    """
    from CadexdProtocol import OP_ARG_SPECS, READ_OPS

    engine_reads = sorted(
        name for name, (spec, _path, _pkg) in specs.items()
        if spec.safety == SafetyLevel.READ)
    assert engine_reads == ["xscript.project.describe_api"]

    assert "inspect" in READ_OPS
    required, optional = OP_ARG_SPECS["inspect"]
    assert set(required) == {"scope"}
    # The scopes a shell may ask for; per-domain and per-program scopes
    # dissolved with ADR-013 and must not come back.
    assert "path" in optional and "target" in optional



# ---------------------------------------------------------------------------
# Engine table, transport budgets, and session construction
# ---------------------------------------------------------------------------


def test_engine_surface_table_covers_every_scripted_engine() -> None:
    """One scripted engine, and the protocol serves exactly its tools.

    Phase 6 asserted this against CadexSession.SCRIPTED_ENGINE_PROVIDER_TOOLS.
    With the provider gone (ADR-021) the engine's surface *is* the cadexd op
    table, so that is what the table is checked against.
    """
    from CadexModelingSurface import MODELING_ENGINES
    from CadexdProtocol import OP_ARG_SPECS

    assert set(MODELING_ENGINES) == {"xscript"}
    for name in PROJECT_TOOL_NAMES:
        operation = name.rsplit(".", 1)[-1]
        assert operation in OP_ARG_SPECS, (
            f"{name} has no cadexd op; the protocol is the engine's only "
            "surface now."
        )



def test_retired_surface_and_publication_shims_are_absent() -> None:
    import CadexScriptedDomainPublication as publication

    # The native workbench-tool pack module was retired entirely.
    with pytest.raises(ModuleNotFoundError):
        import_module("CadexWorkbenchTools")
    assert not hasattr(publication, "_configure_material")
    # The culled-domain worker modules were removed entirely.
    with pytest.raises(ModuleNotFoundError):
        import_module("xscript_cam_worker")


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
    root = MODULE_DIR
    assert all(not (root / name).exists() for name in removed)


def test_the_tool_impl_package_is_gone(specs) -> None:
    """The provider tool package is deleted, not merely unregistered."""
    assert not (MODULE_DIR / "tool_impl").exists()
    with pytest.raises(ModuleNotFoundError):
        import_module("tool_impl.service")
    assert all(not name.startswith(("core.", "part.", "assembly."))
               for name in specs), sorted(specs)



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
