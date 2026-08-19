# SPDX-License-Identifier: LGPL-2.1-or-later

"""Engine purity guardrails (Phase 7, ADR-021).

Successor to ``test_engine_shell_split_guardrails.py``. That test pinned a
boundary *inside* one repo — shell modules here, engine modules there. After
Phase 7 there is no shell in this repo at all, so the contract inverts: the
engine's transitive import closure must contain nothing shell-shaped, and it
must equal a list somebody declared on purpose.

The closure is computed by AST walk from the two engine entry points, so it
holds for the packaged payload (which ships modules, not an import graph)
and not merely for whatever the pytest process happened to import.

:data:`KNOWN_RESIDUE` is empty as of C5: the Qt shell is gone, so the
forbidden-import check applies to the whole of ``src/Mod/cadex/**`` and not
merely to the closure. The ledger stays in place because it is the shape a
future exception would have to take -- named, dated, and asserted still
true -- rather than a quiet import.

The op table cross-check is the one that matters most now. With the shell
in another repository, ``docs/INTEGRATION.md`` is the protocol contract two
codebases are written against, and nothing but this test notices when the
document and the code drift apart.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent.parent

#: Everything the engine is: one service and one headless rebuild entry.
ENGINE_ENTRY_POINTS = ("cadexd", "cadex_rebuild")

#: Import roots that must never appear in the engine's closure. Qt and the
#: FreeCAD GUI layer because the engine runs under FreeCADCmd with no GUI
#: built at all (ADR-022); ``tool_impl`` and ``jsonschema`` because both
#: exist only to serve the provider tool surface that dies with the shell.
FORBIDDEN_ROOTS = frozenset(
    {"PySide", "PySide2", "PySide6", "FreeCADGui", "tool_impl", "jsonschema"}
)

#: Qt specifically has never been reachable from the engine and never may be
#: — this half of :data:`FORBIDDEN_ROOTS` admits no residue at any point.
NO_RESIDUE_EVER = frozenset({"PySide", "PySide2", "PySide6"})

#: (module, forbidden root) -> the Phase 7 commit that removes the edge.
KNOWN_RESIDUE: dict[tuple[str, str], str] = {
}

#: The engine, module by module. Not a summary of the closure — the closure
#: is asserted to equal it, so an accidental new engine dependency is a test
#: failure rather than a silent widening of the payload.
#:
#: Domain *workers* are staged into the sandbox by filename
#: (``_DOMAIN_WORKER_BUNDLES``), not imported, so they are outside this
#: closure by design — ``cadex_mesh_worker`` and ``cadex_assembly_worker``
#: always were. ``cadex_partdesign_worker`` joined them in Phase 10b: it was
#: here only because ``CadexPinResolution`` imported it to borrow
#: ``_subshape_geometry``, which meant resolving one pin dragged the whole
#: partdesign feature-building stack (and through it sketcher and part) into
#: cadexd. That vocabulary is now ``CadexSubshapeQuery``.
DECLARED_ENGINE_MODULES = frozenset(
    {
        # entry points
        "cadexd",
        "cadex_rebuild",
        # protocol + settings
        "CadexdProtocol",
        "CadexEngineSettings",
        # the project script store
        "CadexScriptStore",
        # the xscript pipeline
        "CadexScriptedRuntime",
        # the resident preview worker, host side. Its *worker* side is
        # cadex_preview_worker, staged by filename like every other domain
        # worker and therefore outside this closure by design (ADR-055).
        "CadexWarmWorker",
        # ...and live mode's host side (ADR-109), the same split for the
        # same reason. This one is the sharper case: its worker imports
        # CadexDynamics and through it mujoco, so "staged by filename, never
        # imported" is not a tidiness argument here — it is what keeps a
        # 53 MB physics dependency out of a service that never simulates.
        "CadexLiveSession",
        "CadexScriptedProcess",
        "CadexScriptedPublication",
        "CadexScriptedDomainPublication",
        "CadexScriptedDomains",
        "CadexScriptedOwnership",
        "CadexModelingSurface",
        "CadexReferenceContracts",
        "CadexTools",
        "CadexDigest",
        # inspection, pins, tessellation
        "CadexInspection",
        "CadexPinResolution",
        "CadexRouting",
        "CadexBundle",
        "CadexTerminals",
        "CadexSolder",
        "CadexNets",
        "CadexBoards",
        "CadexMounts",
        "CadexCage",
        # The linked-part container (ADR-138). In the closure *and* in the
        # worker bundle, which is CadexNets' standing exactly: cadexd's
        # link_part op builds a container with it, and the sandboxed part
        # worker reads one back. Both halves are pure Python with no FreeCAD
        # and no kernel, which is what makes being in two places free.
        "CadexLinkedPart",
        # The blueprint store (ADR-150): cadexd's put_blueprint op writes it
        # and inspect scope=blueprint reads it. Pure Python over the script
        # store's own idioms — no FreeCAD, no kernel, no pixels (the shell
        # renders; the engine only files).
        "CadexBlueprints",
        "CadexSubshapeQuery",
        "cadex_tessellation",
        # the five domain APIs and the host-side workers they pull in
        "cadex_domain_api",
        "cadex_project_api",
        "cadex_part_api",
        "cadex_part_worker",
        "cadex_partdesign_api",
        "cadex_sketcher_api",
        "cadex_sketcher_worker",
        "cadex_mesh_api",
        "cadex_assembly_api",
        # The linear-elastic solve (ADR-145). It is here, and CadexDynamics is
        # not, and the difference is which worker reaches them:
        # `cadex_assembly_worker` is staged by filename and outside this
        # closure, while `cadex_part_worker` is inside it. So static
        # reachability was never available as the mechanism here, and what
        # keeps the cost off `cadexd` is the *deferred* import instead --
        # `cadex_part_worker` imports CadexStress inside `stress_record`, and
        # CadexStress imports numpy and scipy inside its own functions.
        # `test_the_stress_solver_costs_a_service_that_never_solves_nothing`
        # asserts both, which is the property that actually matters: this
        # list is about what could be reached, and that one is about what is
        # loaded.
        "CadexStress",
    }
)


def _import_roots(path: Path) -> set[str]:
    """Top-level names imported by one module, absolute imports only."""

    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _module_scope_import_roots(path: Path) -> set[str]:
    """Only the imports that run at import time, not the deferred ones.

    The distinction is the whole point for ``mujoco``: an import inside a
    function body costs nothing until that function is called, which is how
    a 53 MB dependency stays out of a service that never builds a model.
    """

    roots: set[str] = set()
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _engine_closure() -> dict[str, set[str]]:
    """In-tree modules reachable from the entry points -> what each imports."""

    in_tree = {path.stem: path for path in MODULE_DIR.glob("*.py")}
    closure: dict[str, set[str]] = {}
    pending = list(ENGINE_ENTRY_POINTS)
    while pending:
        name = pending.pop()
        if name in closure or name not in in_tree:
            continue
        roots = _import_roots(in_tree[name])
        closure[name] = roots
        pending.extend(root for root in roots if root in in_tree)
    return closure


def test_engine_closure_never_reaches_qt() -> None:
    for module, roots in _engine_closure().items():
        leaked = NO_RESIDUE_EVER.intersection(roots)
        assert not leaked, (
            f"{module} imports {sorted(leaked)}; the engine runs under "
            "FreeCADCmd against a GUI-less build (ADR-022)."
        )


def test_engine_closure_carries_no_undeclared_shell_imports() -> None:
    """Whole-tree since C5: there is no shell in this repository to exempt."""

    undeclared: list[str] = []
    for path in sorted(MODULE_DIR.glob("*.py")):
        for root in sorted(FORBIDDEN_ROOTS.intersection(_import_roots(path))):
            if (path.stem, root) not in KNOWN_RESIDUE:
                undeclared.append(f"{path.stem} -> {root}")
    assert not undeclared, (
        f"New shell-shaped imports in the engine closure: {undeclared}. "
        "The engine may not gain Qt, GUI, tool_impl or jsonschema edges; "
        "widening KNOWN_RESIDUE needs an ADR (ADR-021)."
    )


def test_declared_residue_is_still_real() -> None:
    """The ledger may not outlive the edges it excuses."""

    stale = [
        f"{module} -> {root} (was to go in {commit})"
        for (module, root), commit in KNOWN_RESIDUE.items()
        if root not in _import_roots(MODULE_DIR / f"{module}.py")
    ]
    assert not stale, (
        f"KNOWN_RESIDUE excuses edges that no longer exist: {stale}. "
        "Delete those entries — the ledger is what proves the engine is "
        "still converging on purity."
    )


def test_engine_closure_is_the_declared_module_list() -> None:
    closure = set(_engine_closure())
    assert closure == DECLARED_ENGINE_MODULES, (
        "The engine's module closure drifted from its declaration.\n"
        f"  gained: {sorted(closure - DECLARED_ENGINE_MODULES)}\n"
        f"  lost:   {sorted(DECLARED_ENGINE_MODULES - closure)}\n"
        "This list is the packaged payload's contents (ADR-023): update it "
        "deliberately, in the commit that changes the engine's shape."
    )


def test_every_engine_module_is_installed_by_cmake() -> None:
    """The closure is what the engine imports; CMake is what the payload ships.

    Phase 10b added a module, and every source-tree gate stayed green while
    the payload silently lacked it — the packaged lifecycle test does not
    exercise the part ops that import it. That is exactly the failure ADR-023
    records ("a source tree that passes proves nothing about a payload"), so
    the two lists are pinned to each other here rather than discovered at a
    user.
    """

    cmake = (MODULE_DIR / "CMakeLists.txt").read_text(encoding="utf-8")
    installed = set(re.findall(r"([A-Za-z_][A-Za-z0-9_]*\.py)", cmake))

    from CadexScriptedRuntime import _DOMAIN_WORKER_BUNDLES

    needed = {f"{name}.py" for name in DECLARED_ENGINE_MODULES}
    needed.update(
        filename for bundle in _DOMAIN_WORKER_BUNDLES.values() for filename in bundle
    )
    # Staged into the sandbox as worker.py, and the API module every bundle
    # gets for free; both are real files that have to ship.
    needed.update({"cadex_domain_api.py", "cadex_project_worker.py"})

    missing = sorted(needed - installed)
    assert not missing, (
        f"{missing} are imported or staged by the engine but not listed in "
        "src/Mod/cadex/CMakeLists.txt, so they would be absent from the "
        "packaged payload."
    )


def test_mujoco_never_enters_the_engine_closure() -> None:
    """Dynamics is a staged worker dependency, not an engine dependency (ADR-077).

    ``CadexDynamics`` is the one module in the tree that imports ``mujoco``,
    and it is staged into the sandbox by filename like every other worker
    module. Were anything in the closure to import it -- a convenience
    helper reached from ``cadexd``, say -- the service would pull 53 MB of
    physics engine into a process whose job is to read NDJSON off a pipe,
    and :func:`test_engine_closure_is_the_declared_module_list` would be the
    only thing that noticed. This says why, so the next failure reads as a
    decision rather than as a list to append to.
    """

    closure = _engine_closure()
    assert "CadexDynamics" not in closure, (
        "CadexDynamics reached the engine closure. It is staged by filename "
        "into the worker bundle (ADR-077); cadexd must never import it."
    )
    # The live worker is the other module that reaches physics, and it is
    # the one most likely to be imported by accident: its *host* side,
    # CadexLiveSession, is in the closure and sits one obvious refactor away
    # from `import cadex_live_worker` to share a constant (ADR-109).
    assert "cadex_live_worker" not in closure, (
        "cadex_live_worker reached the engine closure. It imports "
        "CadexDynamics and through it mujoco; CadexLiveSession names it as "
        "a string and spawns it, and must never import it."
    )
    assert "CadexLiveSession" in closure, (
        "CadexLiveSession left the engine closure; cadexd needs its host "
        "side. If it is genuinely gone, DECLARED_ENGINE_MODULES is where "
        "that gets recorded."
    )
    for name in ("mujoco", "CadexDynamics"):
        assert name not in _import_roots(MODULE_DIR / "CadexLiveSession.py"), (
            f"CadexLiveSession imports {name}. Everything physical is on the "
            "far side of a process boundary; that is the whole architecture."
        )
    leaked = sorted(
        module for module, roots in closure.items() if "mujoco" in roots
    )
    assert not leaked, f"{leaked} import mujoco inside the engine closure."


def test_the_stress_solver_costs_a_service_that_never_solves_nothing() -> None:
    """ADR-077's mechanism, applied to the third thing that needs it (ADR-145).

    ``CadexStress`` is a linear-elastic solve on a structured hex grid, and
    the interesting thing about it is that the *cheap* answer was not
    available. ``CadexDynamics`` stays out of the engine closure entirely
    because the only module that reaches it, ``cadex_assembly_worker``, is
    itself staged by filename and outside the closure. ``cadex_part_worker``
    is **inside** it, so static unreachability was never on offer here and
    ``DECLARED_ENGINE_MODULES`` grows by one -- deliberately, and recorded as
    such rather than routed around with an ``importlib`` trick.

    What is asserted instead is the property that actually costs something:
    **nothing imports it at module scope, and it imports its numerics inside
    functions.** So a ``cadexd`` process that imports ``cadex_part_worker``
    does not load the solver, and a worker that loads the solver does not
    thereby load 73 MB of numpy and scipy. Reachable and loaded are different
    questions, and this is the one about loading.
    """

    import ast

    import CadexScriptedRuntime as runtime

    for path in sorted(MODULE_DIR.glob("*.py")):
        if path.stem == "CadexStress":
            continue
        assert "CadexStress" not in _module_scope_import_roots(path), (
            f"{path.name} imports CadexStress at module scope. The import "
            "belongs inside `stress_record`, so that a service which never "
            "solves anything never loads a solver."
        )

    assert "CadexStress.py" in runtime._DOMAIN_WORKER_BUNDLES["project"], (
        "CadexStress left the worker bundle, so a script that declares a "
        "stress check would fail inside the sandbox with an ImportError."
    )
    cmake = (MODULE_DIR / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "CadexStress.py" in cmake, (
        "CadexStress.py is staged by filename but no CMake rule installs it, "
        "so a source tree would pass and a payload would not (ADR-023)."
    )

    tree = ast.parse((MODULE_DIR / "CadexStress.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".")[0] for alias in node.names}
        else:
            roots = {(node.module or "").split(".")[0]}
        if node.col_offset == 0:
            assert roots <= {"__future__", "math", "typing"}, (
                f"CadexStress line {node.lineno} imports {roots} at module "
                "scope. numpy and scipy are deferred into functions on "
                "purpose."
            )
        assert "FreeCAD" not in roots and "Part" not in roots, (
            f"CadexStress line {node.lineno} imports the kernel. It takes "
            "triangles and point clouds, which is what makes it the same "
            "species of thing as analysis/cadex_stress.py and therefore "
            "comparable to it."
        )

    dynamics = _module_scope_import_roots(MODULE_DIR / "CadexDynamics.py")
    assert "mujoco" not in dynamics, (
        "CadexDynamics imports mujoco at module scope. The import belongs "
        "inside the functions that build a model, so the graph algebra stays "
        "testable in an environment without it."
    )


def test_the_training_stack_never_enters_the_engine_closure() -> None:
    """Training is offboard by design, and this is what makes that a fact.

    ADR-075 recorded the constraint and ADR-084 kept it: MJX needs
    JAX-on-GPU, so the trainer runs on a machine we do not ship to. It reads
    the bundle, writes a ``.cxpolicy``, and the engine *verifies* that file
    with a pure-Python forward pass that imports nothing at all.

    So neither ``jax`` nor ``mjx`` may appear anywhere in ``src/Mod/cadex``,
    at module scope or deferred. The engine is not merely able to run
    without them -- it must not be able to reach them, or the day one is
    installed the payload quietly grows a machine-learning framework.
    """

    offenders: list[str] = []
    for path in sorted(MODULE_DIR.glob("*.py")):
        roots = _import_roots(path)
        for forbidden in ("jax", "jaxlib", "flax", "optax", "brax"):
            if forbidden in roots:
                offenders.append(f"{path.name} -> {forbidden}")
        if "mujoco.mjx" in path.read_text(encoding="utf-8"):
            offenders.append(f"{path.name} -> mujoco.mjx")
    assert not offenders, (
        f"The engine reached for the training stack: {offenders}. Training "
        "is offboard (ADR-075, ADR-084); the engine verifies a policy and "
        "never produces one."
    )


def test_the_offboard_trainer_is_not_an_engine_module() -> None:
    """``training/`` is copied to another machine, not installed by CMake.

    Stated as its own assertion because the placement *is* the mechanism:
    ``DECLARED_ENGINE_MODULES`` is what the payload ships, and a trainer
    that lived under ``src/Mod/cadex`` would be one CMake line away from
    dragging jax into it.
    """

    assert "cadex_train" not in DECLARED_ENGINE_MODULES
    assert not (MODULE_DIR / "cadex_train.py").exists()
    trainer = MODULE_DIR.parents[2] / "training" / "cadex_train.py"
    assert trainer.is_file(), (
        "training/cadex_train.py is gone; this guardrail would now pass "
        "vacuously"
    )
    # ...and it is the trainer, rather than some other file that took the name.
    assert "mujoco.mjx" in trainer.read_text(encoding="utf-8")


def test_the_shell_never_learns_about_mujoco() -> None:
    """Dynamics is engine-side, permanently (ADR-075 decision 4, ADR-077).

    Slice M2 shipped with an empty ``shell/`` diff, which was its central
    claim: the shell already knows how to play a simulation trace and does
    not know what produced it. A physics authoring path in the add-on would
    be a second source of truth the way the deleted bpy modes were, so the
    invariant outlives the diff -- nothing under ``shell/`` may import
    mujoco or reach for the translator.
    """

    shell = MODULE_DIR.parents[2] / "shell"
    if not shell.is_dir():  # pragma: no cover - a source checkout always has it
        return
    offenders: list[str] = []
    for path in sorted((shell / "scripts" / "addons_core" / "mesh_agent").rglob("*.py")):
        roots = _import_roots(path)
        for forbidden in ("mujoco", "CadexDynamics"):
            if forbidden in roots:
                offenders.append(f"{path.relative_to(shell)} -> {forbidden}")
    assert not offenders, (
        f"The shell reached for the dynamics engine: {offenders}. Physics "
        "belongs in the script, engine-side; the shell only plays the trace."
    )


def test_the_conversation_store_left_the_engine() -> None:
    """History lives in the .blend now (ADR-020, decision 4)."""

    assert "CadexProject" not in _engine_closure(), (
        "CadexProject carries the conversation store; the engine reaches "
        "THE project script through CadexScriptStore only."
    )


def _documented_ops() -> set[str]:
    """Ops named in the protocol table of ``docs/INTEGRATION.md``.

    The table's rows begin ``| `op` |`` or ``| `a` / `b` |``; op names are
    the backticked cells in the first column.
    """

    doc = (MODULE_DIR.parents[2] / "docs" / "INTEGRATION.md").read_text(
        encoding="utf-8")
    ops: set[str] = set()
    for line in doc.splitlines():
        if not line.startswith("| `"):
            continue
        first_cell = line.split("|")[1]
        ops.update(re.findall(r"`([a-z_]+)`", first_cell))
    return ops


def test_the_protocol_document_matches_the_op_table() -> None:
    """docs/INTEGRATION.md is the cross-repository contract, so it is tested.

    The Blender shell is written against that document, in another
    repository, under another licence. Nothing else in either tree notices
    when the prose and ``OP_ARG_SPECS`` disagree — and a shell that calls an
    op the engine does not serve fails at the user, not at a test.
    """

    from CadexdProtocol import OP_ARG_SPECS

    documented = _documented_ops()
    implemented = set(OP_ARG_SPECS)
    assert documented == implemented, (
        "docs/INTEGRATION.md and CadexdProtocol.OP_ARG_SPECS disagree.\n"
        f"  documented but not served: {sorted(documented - implemented)}\n"
        f"  served but not documented: {sorted(implemented - documented)}\n"
        "With the shell in another repository, the document IS the contract."
    )
