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
import math
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
    """ADR-076's constant stays one entry long, which is what it is named for.

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
            "(ADR-075) and the engine must build and ship without it"
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


def test_the_trainers_decoder_agrees_with_the_engines() -> None:
    """The read half, pinned the way the write half already is.

    ``--init-from`` needs the trainer to *read* a container, and the trainer
    may not import ``CadexDynamics``. So the format is now implemented four
    times -- encoded twice, decoded twice -- and this is what stops the
    fourth from drifting. A decoder that disagreed would warm-start from
    weights nobody wrote.
    """

    module = _trainer_module()
    prepared = pf.swing_up_bundle()
    container = pf.policy_container(prepared, normalise=True)
    blob = dyn.encode_policy(container["header"], container["weights"])

    theirs = module.decode_policy(blob)
    ours = dyn.decode_policy(blob)
    assert theirs["header"] == ours["header"] == container["header"]
    assert theirs["weights"] == ours["weights"] == container["weights"]


def test_the_trainers_decoder_refuses_what_is_not_a_container() -> None:
    """Each refusal names what it looked at, because "invalid" is not a
    diagnosis somebody can act on."""

    module = _trainer_module()
    prepared = pf.swing_up_bundle()
    container = pf.policy_container(prepared, normalise=True)
    blob = dyn.encode_policy(container["header"], container["weights"])

    with pytest.raises(SystemExit, match="does not begin with"):
        module.decode_policy(b"not a policy at all")
    with pytest.raises(SystemExit, match="no header length"):
        module.decode_policy(module.POLICY_MAGIC + b"\x00\x00")
    with pytest.raises(SystemExit, match="truncated"):
        module.decode_policy(blob[:len(blob) // 2])
    # One byte short of a whole float32 is a real corruption and a silent
    # one: the header still parses.
    with pytest.raises(SystemExit, match="whole number of float32"):
        module.decode_policy(blob + b"\x00")


def test_the_trainers_action_fields_agree_with_the_engines() -> None:
    """The fourth copy of a table, checked rather than remembered.

    ``source`` is deliberately absent from both: two bundles deriving the
    same numbers by different routes describe the same action space (ADR-131).
    """

    module = _trainer_module()
    assert module._POLICY_ACTION_FIELDS == dyn._POLICY_ACTION_FIELDS
    assert "source" not in module._POLICY_ACTION_FIELDS


def test_unflattening_the_weights_inverts_flattening_them() -> None:
    """The layout, round-tripped rather than described.

    Per layer in order: the weight matrix ``(inputs, outputs)`` row-major,
    then the bias. Getting this transposed produces a network of exactly the
    right size that computes something else, and nothing downstream would
    refuse it.
    """

    numpy = pytest.importorskip("numpy")
    module = _trainer_module()
    shapes = module.layer_shapes(5, 2, [4, 3])
    assert shapes == [(5, 4), (4, 3), (3, 2)]

    generator = numpy.random.default_rng(0)
    original = [
        (
            generator.standard_normal((inputs, outputs)).astype(numpy.float32),
            generator.standard_normal((outputs,)).astype(numpy.float32),
        )
        for inputs, outputs in shapes
    ]
    flat = module.flat_parameters(numpy, original)
    restored = module.unflatten_parameters(numpy, flat, shapes)

    assert len(restored) == len(original)
    for (want_w, want_b), (got_w, got_b) in zip(original, restored):
        assert got_w.shape == want_w.shape
        assert got_b.shape == want_b.shape
        assert numpy.array_equal(got_w, want_w)
        assert numpy.array_equal(got_b, want_b)

    with pytest.raises(SystemExit, match="needs"):
        module.unflatten_parameters(numpy, flat[:-1], shapes)


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
            "are deliberately absent from the engine environment (ADR-084). "
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


# ---------------------------------------------------------------------------
# M9: the third implementation of the reset variation and the disturbance.
# ---------------------------------------------------------------------------


def test_the_trainer_states_its_own_episode_draw_and_says_it_differs() -> None:
    """Two algorithms, both written down, and the difference is deliberate.

    The bundle's stream is a host-side ``random.Random``. A reset here
    happens on device inside a jitted scan, thousands of times an iteration,
    so it cannot be that stream and does not try to be. What has to match is
    the *arithmetic* -- the quaternion product, the window test, the
    centre-of-mass application point -- and this asserts the trainer says so
    rather than leaving a reader to infer it from two blocks of code.
    """

    source = TRAINER.read_text(encoding="utf-8")
    module = _trainer_module()
    assert module.RESET_VARIATION_MODE == "per_episode"
    assert "jax.random.split" in module.RESET_VARIATION_ALGORITHM
    assert "bundle order" in module.RESET_VARIATION_ALGORITHM
    assert "Deliberately NOT" in module.RESET_VARIATION_ALGORITHM
    # ...and the header carries it, so a policy file says which stream fed it.
    assert '"episode_variation"' in source
    assert '"bundle_algorithm"' in source


def test_the_trainers_reset_variation_is_the_engines_arithmetic() -> None:
    """The Hamilton product, written out three times, compared by test.

    ``CadexDynamics._write_reset_variation``,
    ``dynamics_task_episode.write_variation`` and the trainer's
    ``varied_reset`` are three implementations of six lines. This is the
    fourth time this branch has paid hazard 1, and the mitigation is the one
    that worked: write the second copy down and pin it.
    """

    source = TRAINER.read_text(encoding="utf-8")
    for line in (
        "tw * qw - tx * qx - ty * qy",
        "tw * qx + tx * qw - ty * qz",
        "tw * qy + tx * qz + ty * qw",
        "tw * qz - tx * qy + ty * qx",
    ):
        assert line in source, line
    # The three things phase 0 measured, each visible where it is relied on.
    assert "qvel.at[:, dof + 3 : dof + 6].set(spin)" in source
    assert "xfrc_applied=applied_forces" in source
    assert "int(entry[\"body_id\"]), :3" in source

    # B1b's stumble lands in the dofs beside the spin, and in the OTHER
    # frame. Two implementations of one asymmetry, so the second one is
    # written down and pinned like the four lines above it.
    assert "qvel.at[:, dof + 0].set(speed * jnp.cos(speed_azimuth))" in source
    assert "qvel.at[:, dof + 1].set(speed * jnp.sin(speed_azimuth))" in source
    assert "linear_velocity_low_m_s" in source

    # B1a's arc, with the bracketing that makes the full circle exactly the
    # identity. Written as `drawn * span / (2*pi)` it rounds twice and every
    # task that declares no arc quietly moves by an ulp.
    assert (
        "arc_low + drawn * ((arc_high - arc_low) / (2.0 * math.pi))" in source
    )


def test_the_trainer_runs_a_varied_and_shoved_task(tmp_path) -> None:
    """The paths a compile check cannot reach.

    ``varied_reset``, ``drawn_pushes`` and ``applied_forces`` all run inside
    ``jax.lax.scan`` under ``jit``, where a shape error is a trace-time
    exception and a carry whose structure changes is a different one. The
    only way to know they work is to run them, and the only way to run them
    is a venv with the trainer's dependencies.

    Three iterations and eight environments: this is about the *paths*, not
    about convergence.
    """

    python = _venv_python()
    if python is None:
        pytest.skip(
            "jax and mujoco.mjx are the offboard trainer's dependencies and "
            "are deliberately absent from the engine environment (ADR-084)."
        )

    prepared = pf.shoved_bundle()
    assert prepared["bundle"]["reset_variation"], "the fixture must vary"
    assert prepared["bundle"]["disturbance"], "the fixture must shove"

    root = tmp_path / "project"
    (root / "outputs").mkdir(parents=True)
    (root / "outputs" / "job-model.xml").write_bytes(prepared["model_xml"])
    (root / "outputs" / "job-task.json").write_bytes(prepared["task_bytes"])
    out = tmp_path / "shoved.cxpolicy"

    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [python, "-P", str(TRAINER), str(root / "outputs" / "job-task.json"),
         "--out", str(out), "--seed", "0", "--iterations", "3",
         "--envs", "8", "--unroll", "10", "--quiet"],
        capture_output=True, text=True, env=environment, check=False,
    )
    assert result.returncode == 0, result.stderr[-4000:]
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report["cadex_importable"] is False

    # The policy the engine will accept, with both streams recorded in it.
    evidence = dyn.verify_policy(
        dyn.decode_policy(out.read_bytes()),
        prepared["bundle"],
        task_sha256=prepared["task_sha256"],
    )
    variation = evidence["training"]["episode_variation"]
    assert variation["mode"] == "per_episode"
    assert variation["reset_variation"] == ["start"]
    assert variation["disturbance"] == ["shove", "wind"]
    assert variation["bundle_algorithm"] == (
        prepared["bundle"]["variation_algorithm"]
    )


def test_a_task_with_neither_still_trains(tmp_path) -> None:
    """M9 is additive: every task written before it is unchanged.

    Worth its own run rather than an argument, because the code paths are
    guarded by Python-level conditions on the entry lists -- and a guard that
    was wrong would make the *old* shape the broken one.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")

    prepared = pf.swing_up_bundle()
    assert prepared["bundle"]["reset_variation"] == []
    assert prepared["bundle"]["disturbance"] == []

    root = tmp_path / "project"
    (root / "outputs").mkdir(parents=True)
    (root / "outputs" / "job-model.xml").write_bytes(prepared["model_xml"])
    (root / "outputs" / "job-task.json").write_bytes(prepared["task_bytes"])
    out = tmp_path / "plain.cxpolicy"

    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [python, "-P", str(TRAINER), str(root / "outputs" / "job-task.json"),
         "--out", str(out), "--seed", "0", "--iterations", "2",
         "--envs", "8", "--unroll", "10", "--quiet"],
        capture_output=True, text=True, env=environment, check=False,
    )
    assert result.returncode == 0, result.stderr[-4000:]
    evidence = dyn.verify_policy(
        dyn.decode_policy(out.read_bytes()),
        prepared["bundle"],
        task_sha256=prepared["task_sha256"],
    )
    assert evidence["training"]["episode_variation"]["reset_variation"] == []


def test_the_variation_actually_reaches_the_physics(tmp_path) -> None:
    """The assertion that separates plumbed from live.

    Two bundles differing in **nothing** but the two M9 lists, trained at the
    same seed with the same everything. Without them every environment runs
    the identical episode and the reward is a constant; with them it is not.

    Measured on this fixture: the unvaried run sits in a band nine parts in
    a hundred thousand wide around +0.2989 while the varied one keeps moving.
    A feature that compiled, jitted, traced and did nothing would pass every
    other test in this file.

    That band used to be a *point* -- +0.298921 repeated to six figures --
    and ADR-101 is why it no longer is. The unvaried run's reward stopped
    moving because nothing ever ended its episode: one endless run of a block
    sitting still. It now restarts every ``max_steps``, and since the
    iteration window is 20 steps against a 50-step episode the restart falls
    in a different place each iteration. That band is the reset: 9.4e-5 wide,
    against the 9.0e-4 the variation moves the same curve.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")

    import copy

    curves = {}
    for name in ("varied", "plain"):
        task = copy.deepcopy(pf.SHOVED_TASK)
        if name == "plain":
            task["reset_variation"] = []
            task["disturbance"] = []
        prepared = pf.shoved_bundle(task=task)
        root = tmp_path / name
        (root / "outputs").mkdir(parents=True)
        (root / "outputs" / "job-model.xml").write_bytes(prepared["model_xml"])
        (root / "outputs" / "job-task.json").write_bytes(prepared["task_bytes"])
        out = root / "p.cxpolicy"
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        result = subprocess.run(
            [python, "-P", str(TRAINER),
             str(root / "outputs" / "job-task.json"), "--out", str(out),
             "--seed", "0", "--iterations", "4", "--envs", "32",
             "--unroll", "20", "--quiet"],
            capture_output=True, text=True, env=environment, check=False,
        )
        assert result.returncode == 0, result.stderr[-4000:]
        header = dyn.decode_policy(out.read_bytes())["header"]
        curves[name] = [
            round(float(row["reward_per_step"]), 6)
            for row in header["training"]["reward_curve"]
        ]

    # The unvaried run is the same episode in every environment and repeats
    # it, so its reward barely moves at all once the policy's own output
    # settles: what is left is the episode boundary sliding through the
    # iteration window.
    plain = max(curves["plain"]) - min(curves["plain"])
    varied = max(curves["varied"]) - min(curves["varied"])
    assert plain < 1.0e-3, curves["plain"]
    # The varied one is not, and is a different run from the first step.
    # Measured at 9.6x on this fixture; the bound is 5 because what is being
    # asserted is an order of magnitude, not a number.
    assert varied > 5.0 * plain, (curves["varied"], curves["plain"])
    assert curves["varied"] != curves["plain"]
    assert curves["varied"][0] != curves["plain"][0]


# ---------------------------------------------------------------------------
# M9 slice 2: a run you can watch, interrupt and pull from (ADR-098).
# ---------------------------------------------------------------------------


def test_a_checkpoint_is_a_whole_policy_rather_than_a_weight_dump() -> None:
    """The decision, asserted where it could quietly stop being true.

    A checkpoint goes through the same ``policy_header`` and the same
    ``checked_policy`` the final file does, so what lands mid-run is a
    ``.cxpolicy`` that ``assembly.policy`` accepts -- pull it off the box,
    paste its digest, rebuild, watch it. A weight dump would need a reader
    nobody has written and would be a thing you cannot play.
    """

    source = TRAINER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {node.name for node in ast.walk(tree)
             if isinstance(node, ast.FunctionDef)}
    # The three that had to come out of `main` for a checkpoint to exist.
    assert {"policy_header", "checked_policy", "write_atomically",
            "checkpoint_path"} <= names
    # And `main` uses them for both, rather than having a second path.
    assert source.count("policy_header(bundle, options,") == 2
    assert "checked_policy(header, trained, what=" in source


def test_the_witness_is_checked_on_checkpoints_too() -> None:
    """ADR-094's lesson, applied where it now costs nothing.

    The witness error is a *relative* one that grows with the activations a
    policy learns, so a checkpoint that fails it is a run that is going to
    fail it. Four hours of GPU time died once because nothing checked until
    the end; now the first checkpoint does.
    """

    module = _trainer_module()
    source = TRAINER.read_text(encoding="utf-8")
    assert "witness_disagreement(header, trained[\"parameters\"])" in source
    # `checked_policy` raises rather than returning a flag, so there is no
    # call site that can forget to look.
    checked = next(node for node in ast.walk(ast.parse(source))
                   if isinstance(node, ast.FunctionDef)
                   and node.name == "checked_policy")
    assert any(isinstance(node, ast.Raise) for node in ast.walk(checked))
    assert module.POLICY_WITNESS_TOLERANCE == dyn.POLICY_WITNESS_TOLERANCE


def test_the_progress_file_is_written_atomically_and_versioned() -> None:
    """Two other machines read it while it is being written.

    ``remote_train.sh watch`` polls it over rsync and the shell's Training
    panel polls the copy that lands beside the project. A plain write is a
    window -- small, real, and hit often when the writer runs every
    iteration -- in which both of them read a truncated file and report a
    run that has gone wrong.
    """

    module = _trainer_module()
    source = TRAINER.read_text(encoding="utf-8")
    assert module.PROGRESS_SCHEMA == "cadex-training-progress-v1"
    written = next(node for node in ast.walk(ast.parse(source))
                   if isinstance(node, ast.FunctionDef)
                   and node.name == "write_atomically")
    body = ast.dump(written)
    assert "partial" in body and "replace" in body
    # Every iteration, not every checkpoint: a run you can see the state of
    # once every hundred iterations is a run you still cannot decide about.
    assert "progress(\n" in source or "progress(" in source


def test_checkpoint_names_sort_into_training_order() -> None:
    """A directory listing is the comparison's index, so it has to sort."""

    module = _trainer_module()
    from pathlib import Path as _Path

    out = _Path("/tmp/walk.cxpolicy")
    assert module.checkpoint_path(out, "000100").name == "walk.000100.cxpolicy"
    assert module.checkpoint_path(out, "best").name == "walk.best.cxpolicy"
    names = sorted(
        module.checkpoint_path(out, f"{n:06d}").name for n in (5, 100, 2000)
    )
    assert names == ["walk.000005.cxpolicy", "walk.000100.cxpolicy",
                     "walk.002000.cxpolicy"]
    # Still a .cxpolicy, so nothing has to be renamed before it is used.
    assert all(name.endswith(".cxpolicy") for name in names)


def test_the_dispatch_script_gained_four_subcommands() -> None:
    """A dropped ssh stops being a lost run.

    ``train`` without ``--detach`` is one ssh that lives as long as the run,
    and the mg-legs run this slice was written for took 76 minutes -- long
    enough for a closed laptop, a sleeping wifi chip or a dropped VPN.
    """

    script = (TRAINER.parent / "remote_train.sh").read_text(encoding="utf-8")
    for name in ("cmd_watch", "cmd_pull", "cmd_stop", "detached_train"):
        assert f"{name}()" in script, name
    for line in ("watch)  shift; cmd_watch", "pull)   shift; cmd_pull",
                 "stop)   shift; cmd_stop"):
        assert line in script, line
    assert "--detach)    detach=1" in script

    # `watch` writes the file the shell panel reads, and does it by name so
    # that the panel and the dispatch cannot disagree about it.
    assert "training-progress.json" in script
    # Nothing parses the trainer's stderr. ADR-093 measured what happens
    # when a receipt is taken from a stream something else writes into.
    assert "progress.json" in script


def test_the_pid_file_holds_the_trainer_rather_than_its_wrapper() -> None:
    """Measured the expensive way, on a live 5090.

    ``echo $!`` after backgrounding records the wrapping subshell, and
    ``setsid`` forks again on top of that -- so ``stop`` reported "stopped",
    killed the subshell, and left a 4000-iteration run training with nothing
    pointing at it. The inner shell writes its **own** pid and then
    ``exec``s, which makes the recorded number the trainer by construction.
    """

    script = (TRAINER.parent / "remote_train.sh").read_text(encoding="utf-8")
    assert "echo \\$\\$ > $(shquote \"${remote_dir}/train.pid\")" in script
    assert "; exec" in script
    # And `stop` verifies rather than trusting `kill` returning zero.
    assert "kill -0" in script


# ---------------------------------------------------------------------------
# ADR-101: the episode the bundle declares is the episode the trainer runs.
#
# Two runs on two different tasks produced a rising reward curve and a policy
# that got steadily worse at the task. The cause was one line: `horizon` was
# read out of the episode block and never used again, so `done` was the
# task's termination terms and nothing else and an environment the policy
# kept upright never reset. The trainer was optimising a different problem
# from the one the script declared, which on its own makes every reward
# number it reported non-comparable with any evaluation.
# ---------------------------------------------------------------------------


def test_the_horizon_the_trainer_uses_is_the_bundles_own() -> None:
    """One episode length, declared in one place, honoured in two.

    ``CadexDynamics.evaluate_episode`` bounds its loop by
    ``episode["max_steps"]``; so, now, does the trainer's scan. A constant
    here -- or a horizon derived from ``--unroll``, which is a batching
    choice and not a property of the task -- would be a second declaration of
    the episode, and the two would be free to disagree without anything
    saying so.
    """

    source = TRAINER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assignments = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "horizon"
                for target in node.targets)
    ]
    assert len(assignments) == 1, "the horizon is assigned in exactly one place"
    assert ast.unparse(assignments[0].value) == "int(episode['max_steps'])"

    # ...and it is *used*, which is the whole of ADR-101. The bound is an
    # integer compare on a step counter rather than a float compare on the
    # episode-local clock: 600 additions of a 0.02 s interval do not land on
    # 12.0.
    assert "timeout = steps >= horizon" in source
    assert "done = jnp.logical_or(terminated, timeout)" in source
    assert "steps = jnp.where(done, 0, steps)" in source

    # The same field, read by the engine's own episode loop. If either side
    # ever moves to a different key, this is where the two stop matching.
    engine = Path(dyn.__file__).read_text(encoding="utf-8")
    assert 'max_steps = int(episode["max_steps"])' in engine


def test_a_timeout_is_bootstrapped_and_a_failure_is_not() -> None:
    """The one line where a plausible-looking edit is silently wrong.

    A failure ends the future, so the state after it is worth zero. A timeout
    ends only our looking at it, so the state we landed in is worth whatever
    the critic thinks. Collapsing the two -- ``done`` on both terms, which is
    what the obvious edit produces -- teaches the critic that surviving to
    step 600 is worth exactly as much as falling over, and at
    ``--discount 0.99`` over a 600-step episode that is a large bias traded
    for the one this slice removed.

    Written down as a test because it is invisible in any curve: the wrong
    version still trains, still climbs and still produces a policy.
    """

    source = TRAINER.read_text(encoding="utf-8")
    outer = next(node for node in ast.walk(ast.parse(source))
                 if isinstance(node, ast.FunctionDef)
                 and node.name == "advantages")
    inner = next(node for node in ast.walk(outer)
                 if isinstance(node, ast.FunctionDef) and node.name == "one")

    unpack = inner.body[0]
    assert isinstance(unpack, ast.Assign)
    assert [element.id for element in unpack.targets[0].elts] == [
        "reward", "value", "done", "terminal", "following"
    ]

    assigned = {
        node.targets[0].id: node.value for node in inner.body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    }

    def mentions(node):
        return {name.id for name in ast.walk(node) if isinstance(name, ast.Name)}

    delta = mentions(assigned["delta"])
    carry = mentions(assigned["carry"])
    assert "terminal" in delta and "done" not in delta, (
        "the bootstrap is cut on `terminal`: a timeout keeps its next-state "
        "value, a failure does not"
    )
    assert "done" in carry and "terminal" not in carry, (
        "the GAE carry is cut on `done`: the trajectory genuinely "
        "discontinues either way"
    )

    # And the state it bootstraps from is the post-step, *pre-reset* one.
    # `values[t + 1]` at a boundary is the value of an environment that has
    # already been reset, which is a different state entirely.
    assert 'landed_values = net(params["critic"],' in source
    assert (
        "advantages(rewards, values, dones, terminals, landed_values)"
        in source
    )
    # The separately-computed trailing bootstrap is gone rather than left
    # beside the new one.
    assert "bootstrap = net(" not in source


def _no_termination_bundle():
    """A task nothing can fail, so only the horizon can end an episode.

    Ten control steps at 50 Hz. Before ADR-101 no environment running this
    bundle ever reset, at any length of run.
    """

    import copy

    task = copy.deepcopy(pf.SWING_UP_TASK)
    task["termination"] = []
    task["episode_seconds"] = 0.2
    task["label"] = "unfailable"
    prepared = pf.swing_up_bundle(task=task)
    assert prepared["bundle"]["termination"] == []
    assert int(prepared["bundle"]["episode"]["max_steps"]) == 10
    return prepared


def _train(python, prepared, tmp_path, *, name, extra=()):
    """One short run of the trainer, and its stdout receipt."""

    root = tmp_path / name
    (root / "outputs").mkdir(parents=True)
    (root / "outputs" / "job-model.xml").write_bytes(prepared["model_xml"])
    (root / "outputs" / "job-task.json").write_bytes(prepared["task_bytes"])
    out = root / f"{name}.cxpolicy"
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [python, "-P", str(TRAINER), str(root / "outputs" / "job-task.json"),
         "--out", str(out), "--seed", "0", "--quiet", *extra],
        capture_output=True, text=True, env=environment, check=False,
    )
    assert result.returncode == 0, result.stderr[-4000:]
    return out, json.loads(result.stdout.strip().splitlines()[-1])


def test_the_trainer_truncates_at_the_bundles_episode_length(tmp_path) -> None:
    """The decisive one, and it fails hard on the code ADR-101 replaced.

    The bundle declares a ten-step episode and can terminate for no other
    reason, so the only thing that can end one is the horizon. Twenty control
    steps of eight environments is exactly sixteen episodes; the mean episode
    length is therefore exactly ten, and it is ten every iteration because
    the counter is carried across them.

    Without the truncation the same run reports 160 -- the whole batch over
    zero endings -- which is not an episode length and is meant to read as
    one.
    """

    python = _venv_python()
    if python is None:
        pytest.skip(
            "jax and mujoco.mjx are the offboard trainer's dependencies and "
            "are deliberately absent from the engine environment (ADR-084)."
        )

    prepared = _no_termination_bundle()
    horizon = int(prepared["bundle"]["episode"]["max_steps"])
    out, report = _train(
        python, prepared, tmp_path, name="unfailable",
        extra=("--iterations", "3", "--envs", "8", "--unroll", "20"),
    )
    header = dyn.decode_policy(out.read_bytes())["header"]
    lengths = [float(row["episode_steps"])
               for row in header["training"]["reward_curve"]]
    assert lengths == [pytest.approx(float(horizon))] * 3, lengths
    assert report["episode_steps"] == pytest.approx(float(horizon))


def test_the_trainer_reports_episode_length(tmp_path) -> None:
    """The observable that did not exist, on a task that also terminates.

    There was no external record of episode length at all before ADR-101,
    which is both why two runs went wrong unnoticed and why the fix could not
    be checked from outside. It has to reach the curve rows -- the policy
    file's own record of the run -- and ``progress.json``, which is what
    ``remote_train.sh watch`` and the shell's Training panel poll.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the offboard trainer's dependencies are not installed here")

    prepared = pf.shoved_bundle()
    assert prepared["bundle"]["termination"], "this fixture can also fail"
    envs, unroll = 8, 20
    out, report = _train(
        python, prepared, tmp_path, name="reported",
        extra=("--iterations", "2", "--envs", str(envs),
               "--unroll", str(unroll)),
    )

    header = dyn.decode_policy(out.read_bytes())["header"]
    rows = header["training"]["reward_curve"]
    assert rows and all("episode_steps" in row for row in rows)
    for row in rows:
        length = float(row["episode_steps"])
        # Steps in the batch over episodes that ended in it, so the batch's
        # own size is the ceiling -- that is the reading with nothing ending,
        # and it is a number no episode length can be. The exact value is
        # pinned by the truncation test above, on a bundle where every
        # episode ends for the same reason.
        assert math.isfinite(length) and 0.0 < length <= float(envs * unroll), row

    progress = json.loads((out.parent / "progress.json").read_text("utf-8"))
    assert progress["schema"] == "cadex-training-progress-v1"
    assert math.isfinite(float(progress["episode_steps"]))
    assert progress["episode_steps"] == pytest.approx(
        rows[-1]["episode_steps"]
    )
    assert report["episode_steps"] == pytest.approx(rows[-1]["episode_steps"])


def test_shquote_survives_a_string_containing_a_quote() -> None:
    """The latent bug M9 walked into, pinned so it cannot come back.

    ``${1//.../...}`` is wrong in bash 3.2 -- it turns ``a'b`` into
    ``'a\\'\\\\'\\''b'`` rather than ``'a'\\''b'``. Nothing had ever passed
    it a string containing a quote, so it worked until the first command
    that did, and then produced an unterminated string whose error pointed
    at the wrong line.
    """

    import subprocess as sp

    script = (TRAINER.parent / "remote_train.sh").read_text(encoding="utf-8")
    start = script.index("shquote() {")
    end = script.index("\n}", start) + 2
    harness = script[start:end] + '\nq="$(shquote "$1")"\neval "printf %s $q"\n'
    for original in ("plain/path", "a'b", "echo $$ > '/x/p'; exec '/y/z'"):
        done = sp.run(["bash", "-c", harness, "bash", original],
                      capture_output=True, text=True, check=True)
        assert done.stdout == original, (original, done.stdout)
