# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The offboard trees stay offboard (ADR-084, ADR-141, ADR-143).

``training/`` and ``analysis/`` are not the engine: no CMake rule installs
them, their exact pins stay out of ``pixi.toml``, ``cadex_train.py`` imports
only the standard library at module scope, and ``analysis/`` imports no GPL
package. Kept from the test suites' pruning (ADR-725), where these were the
boundary half of test_analysis_stress.py and test_dynamics_policy_trainer.py.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[4]
ANALYSIS = ROOT / "analysis"
STRESS = ANALYSIS / "cadex_stress.py"
LOADS = ANALYSIS / "loads_from_rollout.py"
CALCULIX = ANALYSIS / "calculix.py"
SEARCH = ANALYSIS / "search.py"
TOPOLOGY = ANALYSIS / "topology.py"
SKELETON = ANALYSIS / "skeleton.py"
ANALYSIS_REQUIREMENTS = ANALYSIS / "requirements.txt"
TRAINER = ROOT / "training" / "cadex_train.py"
TRAINER_REQUIREMENTS = TRAINER.parent / "requirements.txt"


def test_the_analysis_tree_lives_at_the_root_and_not_under_the_engine() -> None:
    """The same three reasons ``training/`` is where it is (ADR-141).

    CMake never installs it, so it cannot reach the payload by accident; it
    is a thing you copy to a machine with time to spend; and its
    dependencies are pinned in a requirements.txt installed into a venv
    there.
    """

    for path in (STRESS, LOADS, CALCULIX, SEARCH, TOPOLOGY, SKELETON,
                 ANALYSIS_REQUIREMENTS,
                 ANALYSIS / "README.md"):
        assert path.is_file(), f"{path} is missing"
        assert "src/Mod/cadex" not in path.as_posix()


def test_no_cmake_rule_installs_the_analysis_tree() -> None:
    """The payload check that does not need a payload built.

    ``test_engine_purity_guardrails`` asserts what reaches a *staged*
    payload; this asserts nothing would ever put this there.
    """

    hits = []
    for path in ROOT.rglob("CMakeLists.txt"):
        if any(part in {"build", "build_darwin", ".pixi", ".git"}
               for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ("cadex_stress" in text or "topology.py" in text
                or "skeleton.py" in text or "analysis/" in text):
            hits.append(str(path))
    assert not hits, f"CMake references the offboard analysis tree: {hits}"


def test_the_analysis_requirements_are_exactly_pinned_and_stay_out_of_pixi() -> None:
    """ADR-076's constant stays one entry long, which is what it is named for.

    The three pins are the versions the engine payload itself carries. That
    is the point rather than a coincidence: if S3 ever moves a linear solve
    in-engine it costs no payload bytes, and the number it computes there is
    the number computed here.
    """

    lines = [
        line.strip()
        for line in ANALYSIS_REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert lines, "the requirements file declares nothing"
    for line in lines:
        assert "==" in line, f"{line!r} is not exactly pinned"
    assert {line.split("==")[0] for line in lines} == {"numpy", "scipy", "mujoco"}

    manifest = ROOT / "package/rattler-build/scripts/relocate_conda_environment.py"
    text = manifest.read_text(encoding="utf-8")
    start = text.index("CARRIED_PYPI_PACKAGES")
    carried = text[start:text.index(")", start)]
    assert carried.count('"') + carried.count("'") == 2, (
        "CARRIED_PYPI_PACKAGES grew past one entry. The analysis tree is "
        "offboard by design (ADR-141) and the engine must ship without it."
    )


def test_the_analysis_files_import_only_numpy_and_the_standard_library() -> None:
    """What may be reached at module scope, and what must be deferred.

    ``numpy`` is at module scope on purpose -- it is in the payload, so its
    presence proves nothing about whether this could be in-engine. ``scipy``
    and ``mujoco`` are deferred, so every contract assertion in this file
    runs on an interpreter that has neither.
    """

    allowed_top = {
        "__future__", "argparse", "collections", "dataclasses", "hashlib",
        "itertools", "json", "math", "os", "pathlib", "platform", "shutil",
        "struct", "subprocess", "sys", "tempfile", "time", "typing", "numpy",
        "cadex_stress", "topology",
    }
    allowed_deferred = allowed_top | {
        "scipy", "mujoco", "OCC", "CadexDynamics", "importlib",
    }
    for path in (STRESS, LOADS, CALCULIX, SEARCH, TOPOLOGY, SKELETON):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".")[0] for alias in node.names}
            else:
                roots = {(node.module or "").split(".")[0]}
            top_level = node.col_offset == 0
            permitted = allowed_top if top_level else allowed_deferred
            assert roots <= permitted, (
                f"{path.name} line {node.lineno} imports {roots - permitted}"
            )


def test_nothing_under_analysis_imports_a_gpl_package() -> None:
    """The one prohibition this tree has that ``training/`` did not need.

    ``analysis/`` is engine-side, and ``docs/PROVENANCE.md`` 1 puts the
    engine side at LGPL. The repository carries no GPL source at all since
    the Blender shell was deleted (ADR-498), and a GPL import in a
    repository-resident file is not a judgement call.

    The named packages are the ones a reasonable person reaches for while
    doing this work and that a survey found are GPL: the meshers, the mesh
    repairers, the MMA implementation everyone uses, and the ``.frd``
    converter that computes von Mises for you.
    """

    forbidden = {
        "gmsh": "GPL-2; its linking exception runs the other way",
        "pygmsh": "GPL-3",
        "pymeshlab": "GPL-3, and meshlabserver is gone so there is no CLI escape",
        "pymeshfix": "GPL-3",
        "pygalmesh": "GPL-3",
        "tetgen": "AGPL-3",
        "mmapy": "GPL-3",
        "ccx2paraview": "GPL-3",
        "jax_fem": "GPL-3",
        "fenitop": "GPL-3",
        "platypus": "GPL-3",
    }
    offenders = []
    for path in sorted(ANALYSIS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            roots: set[str] = set()
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                roots = {(node.module or "").split(".")[0]}
            for name in roots & set(forbidden):
                offenders.append(f"{path.name} -> {name} ({forbidden[name]})")
    assert not offenders, (
        f"A GPL package entered the engine-side tree: {offenders}"
    )


def test_calculix_is_driven_as_a_subprocess_and_never_imported() -> None:
    """``ccx`` is GPL-2, so the boundary is a process boundary.

    The same arm's length FreeCAD's own LGPL Fem module used: a text deck in,
    a text result out, nothing linked. Asserted rather than assumed, because
    "just import it" is exactly the shape of the mistake.
    """

    text = CALCULIX.read_text(encoding="utf-8")
    assert "subprocess.run" in text
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = {alias.name for alias in getattr(node, "names", [])}
            names |= {getattr(node, "module", None) or ""}
            assert not any("ccx" in name or "calculix" == name for name in names), (
                f"line {node.lineno} imports CalculiX rather than running it"
            )


def test_the_analysis_tree_is_not_an_engine_module() -> None:
    """Stated as its own assertion because the placement *is* the mechanism."""

    from test_engine_purity_guardrails import DECLARED_ENGINE_MODULES

    assert "cadex_stress" not in DECLARED_ENGINE_MODULES
    assert not (ROOT / "src/Mod/cadex/cadex_stress.py").exists()
    assert "scipy.sparse" in STRESS.read_text(encoding="utf-8"), (
        "cadex_stress.py is gone or is some other file that took the name; "
        "this guardrail would now pass vacuously"
    )


def test_the_trainer_lives_at_the_repository_root_and_not_under_the_engine() -> None:
    """Three reasons, and this test is the first of them.

    CMake never installs it, so it cannot reach the payload by accident; it
    is a thing you copy to another machine rather than a test; and its
    dependencies are pinned in a requirements.txt installed into a venv on
    whatever box trains.
    """

    assert TRAINER.is_file()
    assert TRAINER_REQUIREMENTS.is_file()
    assert (TRAINER.parent / "README.md").is_file()
    assert "src/Mod/cadex" not in TRAINER.as_posix()


def test_no_cmake_rule_installs_the_trainer() -> None:
    """The payload check that does not need a payload built.

    No test inspects a *staged* payload for jax or mjx since ADR-725; this
    asserts nothing would ever put them there.
    """

    root = TRAINER.parents[1]
    hits = []
    for path in root.rglob("CMakeLists.txt"):
        if any(part in {"build", "build_darwin", ".pixi"}
               for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "cadex_train" in text or "training/" in text:
            hits.append(str(path))
    assert not hits, f"CMake references the offboard trainer: {hits}"


def test_the_trainer_requirements_are_exactly_pinned_and_stay_out_of_pixi() -> None:
    """ADR-076's constant stays one entry long, which is what it is named for.

    MuJoCo's own VERSIONING.md disclaims cross-version numerical
    reproducibility, so a training run is only reproducible if the thing it
    ran against is -- hence ``==`` and not ``>=``.
    """

    lines = [
        line.strip()
        for line in TRAINER_REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert lines, "the requirements file declares nothing"
    for line in lines:
        assert "==" in line, f"{line!r} is not exactly pinned"
    names = {line.split("==")[0] for line in lines}
    # ADR-712: Brax's PPO and the two libraries its networks and optimiser
    # are -- each numerically load-bearing, so each pinned exactly.
    assert names == {"mujoco", "mujoco-mjx", "jax", "numpy", "brax", "flax", "optax"}

    pixi = (TRAINER.parents[1] / "pixi.toml").read_text(encoding="utf-8")
    for forbidden in ("jax", "mujoco-mjx", "mjx"):
        assert forbidden not in pixi, (
            f"{forbidden} entered pixi.toml; training is offboard by design "
            "(ADR-075) and the engine must build and ship without it"
        )


# ---------------------------------------------------------------------------
# What it may import, which is the whole of its discipline.
# ---------------------------------------------------------------------------


_ALLOWED_TOP_LEVEL = {
    "__future__", "argparse", "ast", "copy", "hashlib", "json", "math", "os", "pathlib",
    "platform", "random", "sys", "threading", "time", "typing", "xml.etree",
}
_ALLOWED_DEFERRED = _ALLOWED_TOP_LEVEL | {
    "jax", "jax.numpy", "numpy", "mujoco", "mujoco.mjx", "struct",
    "functools", "importlib",
    # ADR-712: Brax's PPO, and the network and optimiser libraries it is.
    "brax.envs.base", "brax.training", "brax.training.acme",
    "brax.training.agents.ppo", "flax", "optax",
    "CadexDynamics",
    # Inside the pinned mujoco-mjx wheel, not a dependency of its own: the
    # one private module ADR-465's derivative rule replaces a function in.
    "mujoco.mjx._src",
    # ADR-840: the go-to-point source beside it in training/, standard
    # library at module scope; a sibling file, not a dependency.
    "cadex_goto",
}


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    top, deferred = set(), set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Import):
            names = {alias.name for alias in node.names}
        else:
            names = {node.module or ""}
        # Column zero is module scope; anything indented is inside a def.
        (top if node.col_offset == 0 else deferred).update(names)
    return top, deferred


def test_the_trainer_imports_only_the_standard_library_at_module_scope() -> None:
    """So that a test can import it without a GPU box's dependencies.

    Everything above ``train()`` -- the container encoder, the
    whitelist, the bundle loader -- is testable in the engine environment
    precisely because none of it needs jax.
    """

    top, _deferred = _imports(TRAINER)
    unexpected = top - _ALLOWED_TOP_LEVEL
    assert not unexpected, f"{sorted(unexpected)} imported at module scope"


def test_the_trainer_imports_nothing_of_cadex_except_to_report_that_it_cannot() -> None:
    """The negative a test can assert rather than an invocation it must trust.

    The trainer tries ``import CadexDynamics`` once, catches whatever
    happens, and records the answer in the policy it writes. Run under
    ``python -P`` with a scrubbed ``PYTHONPATH`` that is ``false``; if it
    ever came back ``true`` the run was not stock and proves nothing about
    what a trainer can do with the bundle alone.
    """

    top, deferred = _imports(TRAINER)
    assert "CadexDynamics" not in top
    assert "CadexDynamics" in deferred

    source = TRAINER.read_text(encoding="utf-8")
    assert "cadex_importable" in source
    # ...and it is the only Cadex name mentioned at all.
    for forbidden in ("CadexScriptedRuntime", "cadex_assembly_worker",
                      "cadex_mesh_api", "CadexdProtocol"):
        assert forbidden not in source


def test_every_deferred_import_is_one_the_requirements_install() -> None:
    _top, deferred = _imports(TRAINER)
    unexpected = deferred - _ALLOWED_DEFERRED
    assert not unexpected, f"{sorted(unexpected)} is not a pinned dependency"
