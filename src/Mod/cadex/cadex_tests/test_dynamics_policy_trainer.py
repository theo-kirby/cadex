# SPDX-License-Identifier: LGPL-2.1-or-later

"""The offboard trainer, and the same policy twice (M7, phases 2 and 5).

``training/cadex_train.py`` is not part of the engine. It is never installed
by CMake, it is in no payload, and its dependencies -- ``jax``,
``mujoco-mjx`` -- never enter ``pixi.toml``. So most of this file tests it
the way you test a contract with something that is not here: by reading its
source and asserting what it may and may not contain.

The parts that *run* it are gated on those dependencies existing, and skip
in the engine environment. They were run for real in a venv built from
``training/requirements.txt``.

**Phase 5's claim, stated once.** There are two implementations of the
container format (``CadexDynamics.encode_policy`` and the trainer's own) and
two implementations of the forward pass (the engine's pure-Python one and
the trainer's JAX one). The engine cannot import the trainer and the trainer
must not import the engine, so neither can be made correct by sharing code
with the other. What keeps them equal is that both are written down and this
file compares them -- the same move the reward whitelist gets, and for the
same reason.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import CadexDynamics as dyn
import dynamics_policy_fixtures as pf

TRAINER = Path(__file__).resolve().parents[4] / "training" / "cadex_train.py"
REQUIREMENTS = TRAINER.parent / "requirements.txt"


def _trainer_module():
    """The trainer imported as a module, without importing jax.

    Its top-level imports are standard library only -- ``jax`` and
    ``mujoco`` are imported inside ``train()`` -- which is what lets this run
    in the engine environment at all, and is itself asserted below.
    """

    import importlib.util

    spec = importlib.util.spec_from_file_location("cadex_train", TRAINER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Where it lives, and what that placement is for.
# ---------------------------------------------------------------------------


def test_the_trainer_lives_at_the_repository_root_and_not_under_the_engine() -> None:
    """Three reasons, and this test is the first of them.

    CMake never installs it, so it cannot reach the payload by accident; it
    is a thing you copy to another machine rather than a test; and its
    dependencies are pinned in a requirements.txt installed into a venv on
    whatever box trains.
    """

    assert TRAINER.is_file()
    assert REQUIREMENTS.is_file()
    assert (TRAINER.parent / "README.md").is_file()
    assert "src/Mod/cadex" not in TRAINER.as_posix()


def test_no_cmake_rule_installs_the_trainer() -> None:
    """The payload check that does not need a payload built.

    ``test_engine_purity_guardrails`` asserts jax and mjx reach no *staged*
    payload; this asserts nothing would ever put them there.
    """

    root = TRAINER.parents[1]
    hits = []
    for path in root.rglob("CMakeLists.txt"):
        if any(part in {"build", "build_darwin", ".pixi", "shell"}
               for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "cadex_train" in text or "training/" in text:
            hits.append(str(path))
    assert not hits, f"CMake references the offboard trainer: {hits}"


def test_the_requirements_are_exactly_pinned_and_stay_out_of_pixi() -> None:
    """ADR-061's constant stays one entry long, which is what it is named for.

    MuJoCo's own VERSIONING.md disclaims cross-version numerical
    reproducibility, so a training run is only reproducible if the thing it
    ran against is -- hence ``==`` and not ``>=``.
    """

    lines = [
        line.strip()
        for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert lines, "the requirements file declares nothing"
    for line in lines:
        assert "==" in line, f"{line!r} is not exactly pinned"
    names = {line.split("==")[0] for line in lines}
    assert names == {"mujoco", "mujoco-mjx", "jax", "numpy"}

    pixi = (TRAINER.parents[1] / "pixi.toml").read_text(encoding="utf-8")
    for forbidden in ("jax", "mujoco-mjx", "mjx"):
        assert forbidden not in pixi, (
            f"{forbidden} entered pixi.toml; training is offboard by design "
            "(ADR-060) and the engine must build and ship without it"
        )


# ---------------------------------------------------------------------------
# What it may import, which is the whole of its discipline.
# ---------------------------------------------------------------------------


_ALLOWED_TOP_LEVEL = {
    "__future__", "argparse", "ast", "hashlib", "json", "math", "pathlib",
    "platform", "random", "sys", "time", "typing",
}
_ALLOWED_DEFERRED = _ALLOWED_TOP_LEVEL | {
    "jax", "jax.numpy", "numpy", "mujoco", "mujoco.mjx", "struct",
    "CadexDynamics",
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

    The sibling discipline to ``dynamics_task_episode``'s, and it earns its
    keep here: everything above ``train()`` -- the container encoder, the
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


# ---------------------------------------------------------------------------
# Three evaluators of one whitelist.
# ---------------------------------------------------------------------------


def test_the_trainers_whitelist_equals_the_engines_and_the_reference_runners() -> None:
    """M6 had two evaluators; M7 makes three, which is where a set drifts.

    ``CadexDynamics`` compiles reward expressions, ``dynamics_task_episode``
    compiles them again, and the trainer compiles them a third time under
    ``jax.numpy`` so they vectorise. The bundle ships its ``functions``
    array precisely so this can be one assertion instead of three habits.
    """

    import dynamics_task_episode as runner

    module = _trainer_module()

    class _Spellings:
        """A stand-in for ``jax.numpy`` that answers with its own names.

        The trainer's table is built by naming ``jnp`` attributes, so the
        whitelist is checkable without jax installed: what matters is the
        set of *keys*, and those are written out in the trainer's source.
        """

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    trainer_names = module.function_names(module.globals_for(_Spellings()))
    assert trainer_names == runner.function_names()
    assert trainer_names == list(dyn.REWARD_FUNCTIONS)


def test_the_trainer_refuses_a_bundle_whose_functions_it_does_not_offer(
    tmp_path,
) -> None:
    """Outright, before a GPU is touched, rather than mid-run.

    A run that would fail on the last reward term is a run that wasted the
    box. The reference runner refuses the same way and for the same reason.
    """

    module = _trainer_module()
    prepared = pf.swing_up_bundle()
    root = tmp_path / "project"
    (root / "outputs").mkdir(parents=True)
    (root / "outputs" / "job-model.xml").write_bytes(prepared["model_xml"])

    bundle = json.loads(prepared["task_bytes"])
    bundle["functions"] = list(bundle["functions"]) + ["logit"]
    path = root / "outputs" / "job-task.json"
    path.write_bytes(json.dumps(bundle, indent=2, sort_keys=True).encode())

    table = {"__builtins__": {}, "pi": 3.14159}
    table.update({name: (lambda *a: None) for name in dyn.REWARD_FUNCTIONS})
    with pytest.raises(SystemExit) as excinfo:
        module.load_bundle(str(path), table)
    assert "whitelist differs" in str(excinfo.value)


def test_the_trainer_refuses_a_model_that_does_not_match_its_bundles_digest(
    tmp_path,
) -> None:
    module = _trainer_module()
    prepared = pf.swing_up_bundle()
    root = tmp_path / "project"
    (root / "outputs").mkdir(parents=True)
    (root / "outputs" / "job-model.xml").write_bytes(
        prepared["model_xml"] + b"<!-- moved -->"
    )
    path = root / "outputs" / "job-task.json"
    path.write_bytes(prepared["task_bytes"])

    table = {"__builtins__": {}, "pi": 3.14159}
    table.update({name: (lambda *a: None) for name in dyn.REWARD_FUNCTIONS})
    with pytest.raises(SystemExit) as excinfo:
        module.load_bundle(str(path), table)
    assert "does not match the digest" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Two implementations of the container. Phase 5.
# ---------------------------------------------------------------------------


def test_the_trainers_encoder_and_the_engines_produce_the_same_bytes() -> None:
    """The claim that lets ``assembly.policy(..., sha256=...)`` mean anything.

    The trainer writes the file and the engine digests it. If the two
    encoders disagreed by so much as a key order, every policy would arrive
    with a digest the engine could reproduce only by accident.
    """

    module = _trainer_module()
    prepared = pf.swing_up_bundle()
    container = pf.policy_container(prepared, normalise=True)

    theirs = module.encode_policy(container["header"], container["weights"])
    ours = dyn.encode_policy(container["header"], container["weights"])
    assert theirs == ours
    assert hashlib.sha256(theirs).hexdigest() == container["sha256"]

    # ...and the engine reads back what the trainer's encoder wrote.
    decoded = dyn.decode_policy(theirs)
    assert decoded["header"] == container["header"]
    assert decoded["weights"] == container["weights"]


def test_the_two_encoders_agree_on_the_constants_that_define_the_format() -> None:
    module = _trainer_module()
    assert module.POLICY_SCHEMA == dyn.POLICY_SCHEMA
    assert module.POLICY_MAGIC == dyn.POLICY_MAGIC
    assert module.MAXIMUM_POLICY_BYTES == dyn.MAXIMUM_POLICY_BYTES
    assert dyn.MINIMUM_POLICY_WITNESS_SAMPLES <= module.WITNESS_SAMPLES
    assert module.WITNESS_SAMPLES <= dyn.MAXIMUM_POLICY_WITNESS_SAMPLES


def test_the_trainer_states_its_randomisation_extension_rather_than_improvising(
) -> None:
    """A "reproducible" run whose draws are not stated is not one.

    The bundle states exactly one algorithm, which is one parameter set.
    Training needs thousands, so the extension goes into the container --
    where a reader finds it -- rather than into whichever loop happened to
    run.
    """

    module = _trainer_module()
    assert module.RANDOMISATION_MODE == "per_environment"
    assert "base_seed + environment_index" in module.RANDOMISATION_ALGORITHM
    assert "uniform(low, high)" in module.RANDOMISATION_ALGORITHM
    assert "bundle order" in module.RANDOMISATION_ALGORITHM


def test_the_trainer_adds_no_unit_conversion_site() -> None:
    """Hazard 1's fifth payment, pinned on the file that could break it.

    A policy's action vector crosses the boundary *out* of a trainer and
    *into* ``data.ctrl``. The answer is M5's and it is structural: the
    network emits in the bundle's advertised units and the only arithmetic
    is the ``clamp then x scale`` ``evaluate_episode`` already performs. This
    asserts the trainer contains exactly that and no second factor.

    The *grep* half of this lives in ``test_dynamics_units``, which now runs
    its existing conversion-arithmetic regex over ``training/cadex_train.py``
    as well as the engine's assembly stack -- one regex, one list of files,
    rather than a second and looser pattern here. What this asserts is the
    positive: that the two operations which *are* allowed are present and are
    the bundle's own.
    """

    source = TRAINER.read_text(encoding="utf-8")
    assert "jnp.clip(surface, low, high)" in source
    assert "clamped * ctrl_scale" in source

    # Both bounds and the scale come from the bundle's action table and are
    # never recomputed from a joint or an actuator.
    assert 'float(a["low"]) for a in actions' in source
    assert 'float(a["high"]) for a in actions' in source
    assert 'float(a["scale"]) for a in actions' in source

    # ...and the observation side multiplies by the per-channel scale the
    # bundle already computed, rather than converting anything.
    assert 'float(r["scale"])' in source
    assert "obs_scale" in source

    from pathlib import Path as _Path
    import re as _re

    units = _Path(__file__).with_name("test_dynamics_units.py").read_text(
        encoding="utf-8")
    assert "training" in units and "cadex_train.py" in units, (
        "test_dynamics_units no longer greps the offboard trainer, so a "
        "conversion appearing there would not be a test failure"
    )
    assert _re.search(r"_OFFBOARD_NO_CONVERSION_FILES", units)


# ---------------------------------------------------------------------------
# Running it, which needs the dependencies it is offboard because of.
# ---------------------------------------------------------------------------


def _venv_python() -> str | None:
    """An interpreter with the trainer's dependencies, if this one has them."""

    try:
        import jax  # noqa: F401
        import mujoco.mjx  # noqa: F401
    except Exception:
        return None
    return sys.executable


@pytest.mark.parametrize("seed", [0])
def test_the_trainer_writes_a_policy_the_engine_verifies(tmp_path, seed) -> None:
    """End to end, in a process that cannot import Cadex. Phase 5.

    Deliberately tiny -- 3 iterations, 8 environments -- because this test is
    about the *file*, not about convergence. The live gate trains the same
    task properly.
    """

    python = _venv_python()
    if python is None:
        pytest.skip(
            "jax and mujoco.mjx are the offboard trainer's dependencies and "
            "are deliberately absent from the engine environment (ADR-070). "
            "Run this file from a venv built from training/requirements.txt."
        )

    prepared = pf.swing_up_bundle()
    root = tmp_path / "project"
    (root / "outputs").mkdir(parents=True)
    (root / "outputs" / "job-model.xml").write_bytes(prepared["model_xml"])
    (root / "outputs" / "job-task.json").write_bytes(prepared["task_bytes"])
    out = tmp_path / "walk.cxpolicy"

    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [python, "-P", str(TRAINER), str(root / "outputs" / "job-task.json"),
         "--out", str(out), "--seed", str(seed), "--iterations", "3",
         "--envs", "8", "--unroll", "10", "--quiet"],
        capture_output=True, text=True, env=environment, check=False,
    )
    assert result.returncode == 0, result.stderr[-4000:]
    report = json.loads(result.stdout.strip().splitlines()[-1])

    # The negative, asserted rather than trusted.
    assert report["cadex_importable"] is False
    assert report["task_sha256"] == prepared["task_sha256"]
    assert report["sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()
    assert report["witness_samples"] >= dyn.MINIMUM_POLICY_WITNESS_SAMPLES

    evidence = dyn.verify_policy(
        dyn.decode_policy(out.read_bytes()),
        prepared["bundle"],
        task_sha256=prepared["task_sha256"],
    )
    assert evidence["witness_error"] < dyn.POLICY_WITNESS_TOLERANCE
    assert evidence["parameters"] > 0
    assert evidence["training"]["device"] in {"cpu", "gpu", "tpu"}
    assert evidence["training"]["randomisation"]["mode"] == "per_environment"


def test_a_second_run_at_the_same_seed_writes_the_same_policy(tmp_path) -> None:
    """Reproducible on CPU at a fixed seed, which phase 0 measured.

    This does **not** claim a GPU run is reproducible -- it is not, which is
    why docs/MUJOCO.md 3.1 makes a policy an asset with a digest rather than
    a derivation. What it pins is that the trainer itself introduces no
    additional nondeterminism on top of JAX's.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")

    prepared = pf.swing_up_bundle()
    root = tmp_path / "project"
    (root / "outputs").mkdir(parents=True)
    (root / "outputs" / "job-model.xml").write_bytes(prepared["model_xml"])
    (root / "outputs" / "job-task.json").write_bytes(prepared["task_bytes"])

    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    digests = []
    for index in range(2):
        out = tmp_path / f"run{index}.cxpolicy"
        result = subprocess.run(
            [python, "-P", str(TRAINER),
             str(root / "outputs" / "job-task.json"), "--out", str(out),
             "--seed", "0", "--iterations", "2", "--envs", "8",
             "--unroll", "10", "--quiet"],
            capture_output=True, text=True, env=environment, check=False,
        )
        assert result.returncode == 0, result.stderr[-4000:]
        header = dyn.decode_policy(out.read_bytes())["header"]
        # The wall time and the trainer's own reward curve are not part of
        # the claim; the weights and the witness are.
        digests.append(hashlib.sha256(json.dumps({
            "observations": header["observations"],
            "network": header["network"],
            "normaliser": header["normaliser"],
            "evaluation": header["evaluation"],
        }, sort_keys=True).encode()).hexdigest())
    assert digests[0] == digests[1]
