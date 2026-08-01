# SPDX-License-Identifier: LGPL-2.1-or-later

"""M7's and M8's exit criteria, end to end (docs/MUJOCO.md M7--M8).

A script goes into a live ``cadexd`` and declares a mechanism, an exported
model, a trainable task and a **trained policy**. The weights arrive the way
every other byte arrives -- through ``put_asset`` (ADR-043) -- and the engine
verifies them against the task they were trained on before publishing a
receipt whose bytes are part of the project's identity.

**M8 adds the last link** (ADR-085): ``assembly.rollout`` plays that verified
policy against the model its task bundle names and publishes the result as an
ordinary simulation trace. So the chain this file drives now ends where the
arc was always going -- design a mechanism, train a policy for it offboard,
and watch the mechanism move under it.

**No protocol change and no ``shell/`` diff.** That is the invariant ADR-078
says the whole branch rests on, and M7 is designed so it stays true: a
policy needed no new op because ``put_asset`` performs no suffix check of
its own, and widening the store's accepted set is entirely engine-side.

Two gates rather than one, because they prove different things and are
available in different places:

* **The store-and-verify gate** runs wherever ``FreeCADCmd`` does. It builds
  the container against the bundle the *engine actually wrote*, stores it,
  and drives the whole verification and receipt path. It needs no jax.
* **The training gate** additionally runs ``training/cadex_train.py`` for
  real and skips where its dependencies are absent -- which is everywhere
  the engine is, because training is offboard by design.

**Honest scoping.** The training gate trains a *tiny* task -- one hinge,
swing-up, a fixed seed -- on **CPU**, because that is what a test machine
has. The GPU is a speed difference, not a semantic one, and it is the same
trainer file. A remote GPU run is exercised manually and its numbers are
recorded in ADR-084. This does not prove the GPU path.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest

import CadexDynamics as dyn
from test_cadexd_lifecycle import FREECADCMD, _spawn_cadexd, _stop

mujoco = pytest.importorskip("mujoco")

pytestmark = pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)

TRAINER = Path(__file__).resolve().parents[4] / "training" / "cadex_train.py"

#: One hinge and one motor: the smallest mechanism that is a real control
#: problem, and the one the CI training gate can converge in seconds.
#:
#: The hinge is at the link's *end*. A joint through the link's own centre
#: would be a perfectly balanced pendulum -- gravity produces no torque and
#: there is nothing to swing up -- and it looked like a converged policy the
#: first time it was measured.
#:
#: ``centre_of_mass`` rather than ``component_position`` for the height
#: channel, because M6 measured that a link hinged at its own origin has
#: that origin *on* the rotation axis and the position channel never moves.
TASK_SCRIPT = """
post = part.box(60, 60, 300)
link = part.box(200, 30, 15)
base = assembly.component(post, grounded=True)
swing = assembly.component(link, placement=[0, 0, 150])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin",
                                      offset={"position": [0, 0, 150],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": -90}),
                   assembly.connector(swing, "origin",
                                      offset={"position": [-100, 0, 0],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": -90}))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
motor = assembly.actuator(j, kind="motor", control_nmm="0",
                          torque_limit_nmm=2000)
model = assembly.mjcf(asm, [
    assembly.body(base, density_kg_m3=7850),
    assembly.body(swing, density_kg_m3=7850),
], actuators=[motor], observations=[
    assembly.observation(j, "position", name="angle"),
    assembly.observation(j, "velocity", name="rate"),
    assembly.observation(swing, "centre_of_mass", name="tip"),
])
job = assembly.task(model, actions=[motor],
                    reward=[
                        assembly.reward("tip_z", weight=0.01, label="height"),
                        assembly.reward("abs(rate)", weight=-1.0e-4,
                                        label="spin"),
                    ],
                    termination=[
                        assembly.termination("abs(rate)", above=3000.0,
                                             label="spun_out"),
                    ],
                    episode_seconds=2.0, control_hz=50, label="swing_up")
result = {"post": post, "link": link, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "model": model, "job": job}
"""

#: The same script with the policy declared. ``sha256`` is substituted after
#: the weights exist, which is the real authoring order: train, store, paste
#: the digest the store reported.
POLICY_SCRIPT = TASK_SCRIPT.replace(
    'result = {"post"',
    """gait = assembly.policy(job, weights="walk.cxpolicy",
                       sha256="__SHA256__", label="gait")
result = {"gait": gait, "post\"""",
)

#: M8's script: the same again, played (docs/MUJOCO.md M8, ADR-085). The
#: rollout samples at 25 fps against a 50 Hz task -- one frame per two
#: control steps -- so the frame count below is arithmetic rather than an
#: observation.
ROLLOUT_SCRIPT = POLICY_SCRIPT.replace(
    'result = {"gait": gait, "post"',
    """play = assembly.rollout(gait, frames_per_second=25, label="walk")
result = {"play": play, "gait": gait, "post\"""",
)


class _Session:
    """One live cadexd against one project root, reused across requests."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.client = None

    def __enter__(self):
        self.client = _spawn_cadexd()
        opened = self.client.request(
            "open_project", {"project_root": str(self.root)}
        )
        assert opened["ok"] is True, opened
        return self

    def __exit__(self, *_exception) -> None:
        try:
            if self.client is not None:
                self.client.request("shutdown", timeout=60)
        finally:
            _stop(self.client)

    def write(self, source: str, revision: str = "") -> dict:
        written = self.client.request(
            "write_script", {"source": source, "expected_revision": revision}
        )
        return written

    def put_asset(self, path: Path, name: str) -> dict:
        return self.client.request(
            "put_asset", {"source_path": str(path), "name": name}
        )


def _accepted(written: dict) -> tuple[str, Path]:
    """One accepted write, as its revision and the bundle it retained.

    The bundle path comes off ``display`` rather than out of a second
    request: it is the path the store *declared* for that output, which is
    the one a reader would follow.
    """

    assert written["ok"] is True, json.dumps(written)[:4000]
    entry = written["display"]["job"]
    assert entry["artifact_kind"] == "assembly_training_task_json", entry
    return str(written["revision"]), Path(entry["artifact_path"])


def _container_for(bundle_path: Path, **overrides) -> dict:
    """A policy container built against the bundle the engine really wrote.

    Not a fixture bundle: the whole point of a live gate is that the digests
    being checked are the ones a real Ondsel solve and a real export
    produced.
    """

    import dynamics_policy_fixtures as pf

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    prepared = {
        "bundle": bundle,
        "task_sha256": hashlib.sha256(bundle_path.read_bytes()).hexdigest(),
    }
    return pf.policy_container(prepared, normalise=True, **overrides)


# ---------------------------------------------------------------------------
# The exit criterion.
# ---------------------------------------------------------------------------


def test_a_policy_comes_home_and_the_engine_verifies_it() -> None:
    """The whole slice in one chain, through the engine a user runs.

    Design a mechanism, declare a task, bring back trained weights, and get
    a receipt that says the engine checked them against the task they claim.
    """

    root = Path(tempfile.mkdtemp(prefix="m7-live-"))
    try:
        with _Session(root) as session:
            revision, bundle_path = _accepted(session.write(TASK_SCRIPT))

            container = _container_for(bundle_path, label="run-17")
            weights = root.parent / "walk.cxpolicy"
            weights.write_bytes(container["blob"])

            # The weights enter the store through the tool that already
            # exists. No new op, no protocol change -- put_asset performs no
            # suffix check of its own and lets the engine refuse.
            stored = session.put_asset(weights, "walk.cxpolicy")
            assert stored["ok"] is True, stored
            assert stored["sha256"] == container["sha256"]
            assert stored["name"] == "walk.cxpolicy"
            assert stored["bytes"] == len(container["blob"])
            # The store lists it beside any meshes: one directory, two kinds
            # of file, and no new op to hold the second (ADR-084).
            assert "walk.cxpolicy" in [
                str(item["name"]) for item in stored["assets"]
            ]

            written = session.write(
                POLICY_SCRIPT.replace("__SHA256__", container["sha256"]),
                revision,
            )
            assert written["ok"] is True, json.dumps(written)[:4000]

            entry = written["display"]["gait"]
            assert entry["artifact_kind"] == "assembly_policy_receipt_json"
            # A policy is not display geometry and must not pretend to be:
            # this is what keeps it invisible to a shell never changed.
            assert entry["tessellation"] is None
            assert entry["placement"] is None

            receipt_path = Path(entry["artifact_path"])
            assert receipt_path.name == "gait-policy.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

            assert receipt["schema"] == "cadex-policy-receipt-v1"
            assert receipt["policy_schema"] == dyn.POLICY_SCHEMA
            assert receipt["weights"] == "walk.cxpolicy"

            # Two labels, kept apart: the *script* names this output and the
            # *container* carries whatever the training run was called. The
            # first version of this folded the evidence in wholesale and the
            # container's label silently won, so the published aLabel was a
            # name nobody had written in the script.
            assert receipt["label"] == "gait"
            assert receipt["trained_label"] == container["header"]["label"]
            assert receipt["policy_sha256"] == container["sha256"]
            assert receipt["policy_bytes"] == len(container["blob"])

            # The three digests that make a policy, a task and a model mean
            # anything together.
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            assert receipt["task_sha256"] == hashlib.sha256(
                bundle_path.read_bytes()
            ).hexdigest()
            assert receipt["model_sha256"] == bundle["model"]["sha256"]

            # ...and the verification actually ran.
            assert receipt["observation_channels"] == [
                "angle", "rate", "tip_x", "tip_y", "tip_z"
            ]
            assert receipt["action_count"] == 1
            assert receipt["witness_samples"] >= (
                dyn.MINIMUM_POLICY_WITNESS_SAMPLES
            )
            assert receipt["witness_error"] < dyn.POLICY_WITNESS_TOLERANCE
            assert receipt["witness_tolerance"] == dyn.POLICY_WITNESS_TOLERANCE
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_the_engine_plays_the_policy_it_verified_and_the_trace_is_a_trace() -> None:
    """M8's exit criterion, minus the claim that the gait is any good.

    The whole chain in one script -- mechanism, model, task, policy, rollout
    -- through the engine a user runs, ending in the artifact the shell has
    baked since ADR-050. Whether the policy *learned* anything is asserted by
    the training gate at the bottom of this file, which needs jax; this
    asserts the path, which needs nothing.

    **No protocol change and no ``shell/`` diff**, which is what the artifact
    kind below is really testing: a rollout is not a new kind of thing to the
    shell, it is a trace.
    """

    root = Path(tempfile.mkdtemp(prefix="m8-live-"))
    try:
        with _Session(root) as session:
            revision, bundle_path = _accepted(session.write(TASK_SCRIPT))
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

            container = _container_for(bundle_path, label="run-17")
            weights = root.parent / "walk.cxpolicy"
            weights.write_bytes(container["blob"])
            assert session.put_asset(weights, "walk.cxpolicy")["ok"] is True

            written = session.write(
                ROLLOUT_SCRIPT.replace("__SHA256__", container["sha256"]),
                revision,
            )
            assert written["ok"] is True, json.dumps(written)[:4000]

            entry = written["display"]["play"]
            assert entry["artifact_kind"] == "assembly_simulation_json"

            trace = json.loads(
                Path(entry["artifact_path"]).read_text(encoding="utf-8")
            )
            assert trace["schema"] == "cadex-assembly-simulation-trace-v1"
            assert trace["component_outputs"] == ["base", "swing"]
            assert trace["motion_outputs"] == []
            assert trace["parameters"]["frames_per_second"] == 25

            # The three digests, restated in the trace so it can be checked
            # without opening the receipt beside it.
            policy = trace["policy"]
            assert policy["policy_sha256"] == container["sha256"]
            assert policy["task_sha256"] == hashlib.sha256(
                bundle_path.read_bytes()
            ).hexdigest()
            assert policy["model_sha256"] == bundle["model"]["sha256"]
            assert policy["weights"] == "walk.cxpolicy"

            # The sampling rule, as arithmetic on what the episode did: one
            # frame per two control steps, the input frame in front, and the
            # final state whether or not it landed on a boundary. Random
            # weights spin this pendulum out, so the episode length is not
            # known here -- but the frame count follows from it exactly.
            steps = int(policy["step_count"])
            assert 0 < steps <= 100
            assert len(trace["frames"]) == 2 + steps // 2 + steps % 2
            assert trace["frames"][0]["frame_kind"] == "input"
            assert trace["frames"][0]["nominal_time_s"] is None
            assert all(frame["frame_kind"] == "solver_output"
                       for frame in trace["frames"][1:])
            assert trace["frames"][-1]["nominal_time_s"] == pytest.approx(
                steps / 50.0
            )

            # ...and the receipt is still published beside it. A rollout
            # consumes a policy; it does not replace one.
            assert (written["display"]["gait"]["artifact_kind"]
                    == "assembly_policy_receipt_json")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_a_rollout_of_a_policy_the_script_does_not_publish_is_refused_live() -> None:
    """An unpublished policy is one the engine never verified.

    The receipt is where the engine records that it checked the weights
    against the task they claim, and publishing is what produces it. A
    rollout of a policy with no receipt would be a gait nothing stands
    behind -- which is the exact failure ``verify_policy`` exists to turn
    into a refusal.
    """

    root = Path(tempfile.mkdtemp(prefix="m8-live-unpublished-"))
    try:
        with _Session(root) as session:
            revision, bundle_path = _accepted(session.write(TASK_SCRIPT))
            container = _container_for(bundle_path)
            weights = root.parent / "walk.cxpolicy"
            weights.write_bytes(container["blob"])
            assert session.put_asset(weights, "walk.cxpolicy")["ok"] is True

            # The policy is built and played, and simply not returned.
            source = ROLLOUT_SCRIPT.replace(
                "__SHA256__", container["sha256"]
            ).replace('result = {"play": play, "gait": gait, "post"',
                      'result = {"play": play, "post"')
            written = session.write(source, revision)
            assert written["ok"] is False
            text = json.dumps(written)
            assert "does not return as an output" in text
            assert "Return the api.policy value in result" in text
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# The refusals, live. Each one is a way for a policy to be confidently wrong
# about a mechanism, and each has to reach the author as a sentence.
# ---------------------------------------------------------------------------


def test_a_policy_whose_bytes_moved_under_a_fixed_script_is_refused() -> None:
    """The refusal ``sha256=`` exists for, and it names the digest observed.

    A policy is the one part of a project that cannot be rebuilt from the
    script, so the script states which bytes it meant. Retraining under a
    fixed script is exactly what this catches -- and the correction carries
    the observed digest so the agent can paste it back.
    """

    root = Path(tempfile.mkdtemp(prefix="m7-live-digest-"))
    try:
        with _Session(root) as session:
            revision, bundle_path = _accepted(session.write(TASK_SCRIPT))

            declared = _container_for(bundle_path, seed=1)
            retrained = _container_for(bundle_path, seed=2)
            assert declared["sha256"] != retrained["sha256"]

            weights = root.parent / "walk.cxpolicy"
            weights.write_bytes(retrained["blob"])
            assert session.put_asset(weights, "walk.cxpolicy")["ok"] is True

            written = session.write(
                POLICY_SCRIPT.replace("__SHA256__", declared["sha256"]),
                revision,
            )
            assert written["ok"] is False
            text = json.dumps(written)
            assert retrained["sha256"] in text, text[:3000]
            assert "sha256=" in text
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_a_policy_trained_on_another_task_is_refused_live() -> None:
    """The claim the receipt exists to make, refused when it is false."""

    root = Path(tempfile.mkdtemp(prefix="m7-live-task-"))
    try:
        with _Session(root) as session:
            revision, bundle_path = _accepted(session.write(TASK_SCRIPT))

            container = _container_for(bundle_path)
            header = dict(container["header"])
            header["task"] = {"sha256": "b" * 64, "label": "swing_up"}
            blob = dyn.encode_policy(header, container["weights"])

            weights = root.parent / "walk.cxpolicy"
            weights.write_bytes(blob)
            assert session.put_asset(weights, "walk.cxpolicy")["ok"] is True

            written = session.write(
                POLICY_SCRIPT.replace(
                    "__SHA256__", hashlib.sha256(blob).hexdigest()
                ),
                revision,
            )
            assert written["ok"] is False
            text = json.dumps(written)
            assert "policy_task_mismatch" in text or "trained on a task" in text
            assert "Retrain" in text
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_a_policy_the_engine_reads_differently_is_refused_live() -> None:
    """The witness, doing the job M8 depends on it for.

    Weights intact, digest correct, task correct -- and the network the
    engine evaluates is not the one that trained. Without the witness this
    would be a gait somebody has to watch and distrust.
    """

    root = Path(tempfile.mkdtemp(prefix="m7-live-witness-"))
    try:
        with _Session(root) as session:
            revision, bundle_path = _accepted(session.write(TASK_SCRIPT))

            container = _container_for(bundle_path)
            header = json.loads(json.dumps(container["header"]))
            header["evaluation"]["actions"][2][0] += 900.0
            blob = dyn.encode_policy(header, container["weights"])

            weights = root.parent / "walk.cxpolicy"
            weights.write_bytes(blob)
            assert session.put_asset(weights, "walk.cxpolicy")["ok"] is True

            written = session.write(
                POLICY_SCRIPT.replace(
                    "__SHA256__", hashlib.sha256(blob).hexdigest()
                ),
                revision,
            )
            assert written["ok"] is False
            text = json.dumps(written)
            assert "witness" in text
            assert "different network" in text
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_a_policy_naming_no_stored_asset_is_refused_live() -> None:
    root = Path(tempfile.mkdtemp(prefix="m7-live-missing-"))
    try:
        with _Session(root) as session:
            revision, _bundle_path = _accepted(session.write(TASK_SCRIPT))
            written = session.write(
                POLICY_SCRIPT.replace("__SHA256__", "c" * 64), revision
            )
            assert written["ok"] is False
            text = json.dumps(written)
            assert "walk.cxpolicy" in text
            assert "put_asset" in text
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# The digest. A policy that nothing published would be a policy the project's
# identity cannot see.
# ---------------------------------------------------------------------------


def test_the_project_digest_moves_when_a_single_weight_does() -> None:
    """Why the receipt is an output rather than the asset speaking for itself.

    ``compute_project_digest`` takes ``(root, outputs)`` and never walks
    ``assets/``, so a policy that only lived there would land with a sha256
    in ``put_asset``'s reply and in no project identity at all -- and a
    project could be reopened with different weights under the same digest.

    Declaring it as an output fixes that twice: the declared ``sha256`` is
    inside the definition JSON (``payload_sha256``), and the retained
    receipt's bytes join by ADR-068's have-an-artifact clause. This changes
    **one float** in the container and asserts the project's identity moved.
    """

    digests = []
    for seed in (1, 2):
        root = Path(tempfile.mkdtemp(prefix=f"m7-live-digest{seed}-"))
        try:
            with _Session(root) as session:
                revision, bundle_path = _accepted(session.write(TASK_SCRIPT))
                container = _container_for(bundle_path, seed=seed)

                weights = root.parent / f"walk{seed}.cxpolicy"
                weights.write_bytes(container["blob"])
                assert session.put_asset(weights, "walk.cxpolicy")["ok"] is True

                written = session.write(
                    POLICY_SCRIPT.replace("__SHA256__", container["sha256"]),
                    revision,
                )
                assert written["ok"] is True, json.dumps(written)[:3000]
                digests.append(written["digest"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    assert digests[0] != digests[1], (
        "the project digest is blind to which policy the project holds, so a "
        "stored policy could be replaced under a fixed script and the "
        "project would still open as accepted"
    )


# ---------------------------------------------------------------------------
# The training gate. Offboard by design, so it skips where the engine lives.
# ---------------------------------------------------------------------------


def _trainer_python() -> str | None:
    try:
        import jax  # noqa: F401
        import mujoco.mjx  # noqa: F401
    except Exception:
        return None
    return sys.executable


def test_a_task_the_engine_wrote_trains_to_a_policy_the_engine_accepts() -> None:
    """The slice's headline, with a real training run in the middle.

    Design a mechanism in Cadex; get a policy that controls it. The task
    comes from a live engine, the training happens in a process that cannot
    import Cadex, and the resulting file is stored and verified through the
    same path the gate above drives.

    **Tiny and on CPU.** One hinge, a fixed seed, a few hundred iterations,
    four seconds. It converges visibly -- which is what makes it a gate
    rather than a smoke test -- and it says nothing about a GPU.
    """

    python = _trainer_python()
    if python is None:
        pytest.skip(
            "jax and mujoco.mjx are the offboard trainer's dependencies and "
            "are deliberately absent from the engine environment (ADR-075, "
            "ADR-084). Run this file from a venv built from "
            "training/requirements.txt."
        )

    root = Path(tempfile.mkdtemp(prefix="m7-live-train-"))
    try:
        with _Session(root) as session:
            revision, bundle_path = _accepted(session.write(TASK_SCRIPT))
            artifact_root = bundle_path.parent.parent

            out = root.parent / "walk.cxpolicy"
            environment = dict(os.environ)
            environment.pop("PYTHONPATH", None)
            finished = subprocess.run(
                [python, "-P", str(TRAINER), str(bundle_path),
                 "--out", str(out), "--seed", "0", "--iterations", "150",
                 "--envs", "128", "--unroll", "25", "--quiet"],
                capture_output=True, text=True, timeout=1800,
                env=environment, check=False,
            )
            assert finished.returncode == 0, finished.stderr[-4000:]
            report = json.loads(finished.stdout.strip().splitlines()[-1])

            # The negative, asserted rather than trusted.
            assert report["cadex_importable"] is False
            assert report["device"] == "cpu"

            # It converged. The theoretical ceiling is 2.5 reward per step --
            # the link's centre of mass at 250 mm, held -- and a zero-torque
            # episode scores about 0.98. Anything above 2.0 is a policy that
            # swung the pendulum up and kept it there.
            assert report["reward_per_step"] > 2.0, (
                f"training did not converge: {report['reward_per_step']}"
            )

            stored = session.put_asset(out, "walk.cxpolicy")
            assert stored["ok"] is True, stored
            assert stored["sha256"] == report["sha256"]

            written = session.write(
                ROLLOUT_SCRIPT.replace("__SHA256__", report["sha256"]),
                revision,
            )
            assert written["ok"] is True, json.dumps(written)[:4000]

            receipt = json.loads(
                Path(written["display"]["gait"]["artifact_path"]).read_text(
                    encoding="utf-8"
                )
            )
            assert receipt["policy_sha256"] == report["sha256"]
            assert receipt["witness_error"] < dyn.POLICY_WITNESS_TOLERANCE
            assert receipt["training"]["device"] == "cpu"
            assert receipt["training"]["seed"] == 0

            # And the loop M8 closes: the engine rolled the trained policy
            # out against the very model the bundle names, and the trace it
            # published is of a mechanism doing something.
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            model = dyn.load_model(
                (artifact_root / bundle["model"]["path"]).read_bytes()
            )
            fallback = dyn.evaluate_episode(model, bundle)
            trace = json.loads(
                Path(written["display"]["play"]["artifact_path"]).read_text(
                    encoding="utf-8"
                )
            )
            driven = float(trace["policy"]["total_reward"])
            assert driven > fallback["total_reward"] * 1.5, (
                f"the trained policy ({driven:.1f}) did not beat doing "
                f"nothing ({fallback['total_reward']:.1f})"
            )
            # It ran the whole horizon rather than spinning out, which is
            # what "it learned to swing up and hold it" looks like in a
            # trace: 100 control steps, sampled every second one.
            assert trace["policy"]["truncated"] is True
            assert trace["policy"]["step_count"] == 100
            assert len(trace["frames"]) == 52

            # ...and the engine's own rollout agrees with a plain call to
            # evaluate_episode on the same file, which is the assertion that
            # M8 added a sampler rather than a second episode loop.
            container = dyn.decode_policy(out.read_bytes())
            direct = dyn.evaluate_episode(
                model, bundle,
                actions=lambda step, observation: dyn.policy_forward(
                    container["header"], container["weights"], observation
                ),
            )
            assert driven == pytest.approx(direct["total_reward"], rel=1.0e-12)
    finally:
        shutil.rmtree(root, ignore_errors=True)
