# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex train``: the dispatcher for the offboard trainer (ADR-191).

Training is offboard by design (ADR-084): the engine verifies a policy and
never produces one, ``training/`` is in no payload, and its jax lives in a
venv the engine's environment deliberately lacks. What the lifecycle audit
(``docs/MUJOCO.md`` §7c, row 4) found missing was not a trainer but a
*dispatcher* — the one command that takes the accepted script's training
bundle to ``training/cadex_train.py`` in that venv and reads the receipt
back, so the leg is a pipeline's, or the agent's caller's, rather than a
person's who knows the flags.

This module is the half that owns no engine: which interpreter, which
command, and what the trainer said. ``__main__.command_train`` does the
rebuild and export before it and the ``put_asset`` after it. The trainer's
own flags are pinned here by name because the audit twice caught the agent
guessing them (``--num-envs`` for ``--envs``, ``--output`` for ``--out``);
``test_train.py`` reads them back out of the trainer's source so a rename
there fails here.

**Remote training** (ADR-200) substitutes `remote_train.sh` for the local
interpreter. Blocking dispatch copies the policy back to the same path and
checks its digest; warm-start files travel and are re-pointed by the dispatcher
(ADR-268). With `--detach` (ADR-278), the dispatcher instead returns a pending
run locator. The caller persists it without checking or storing any policy.
The full walk remains blocking.

**And the leg can be planned rather than run** (ADR-255). ``--dry-run``
stops after the export and reports :func:`training_plan`: the files the
leg would touch and the steps it would take, in either mode. It is how the
claim that the two modes land the same artifacts is checked on a machine
that may not dispatch to a box at all — and it is the preflight to put in
front of ``cadex walk --remote``, whose remote leg otherwise fails only
after the design and assembly legs have already run.
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from typing import Any, Sequence

from .engine import REPO_ROOT
from .export import ExportedOutput

#: The trainer, by path from the repository root. The CLI runs from the
#: repository (``docs/CLI.md`` §8), and so does the trainer: neither is in
#: a payload, and this is the one place the two meet.
TRAINER_SCRIPT = REPO_ROOT / "training" / "cadex_train.py"

#: The remote dispatcher (ADR-089), by the same rule. It is a bash script
#: configured by ``training/.remote.env``; the CLI adds no configuration of
#: its own and never reads that file.
REMOTE_SCRIPT = REPO_ROOT / "training" / "remote_train.sh"

#: The interpreters tried, in order, after ``--trainer-python``: the
#: environment variable, then the two places ``training/SETUP.md`` names —
#: the repo-root ``.venv`` (gitignored) and the home-directory venv.
TRAINER_PYTHON_ENV = "CADEX_TRAIN_PYTHON"
TRAINER_VENV_CANDIDATES: tuple[Path, ...] = (
    REPO_ROOT / ".venv" / "bin" / "python",
    Path.home() / "cadex-train-venv" / "bin" / "python",
)

#: The export kind a training task is staged under.
TASK_KIND = "assembly_training_task_json"


class TrainError(RuntimeError):
    """The trainer could not be found, could not be run, or refused."""


def resolve_trainer_python(explicit: str | os.PathLike[str] | None = None) -> Path:
    """The interpreter the trainer runs under.

    An explicit path is trusted as given and must exist. Otherwise the
    environment variable, then the two documented venv locations. Nothing
    here creates a venv: a venv this silently built is a venv nobody knows
    the contents of, which is the same rule ``remote_train.sh`` keeps.
    """

    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise TrainError(f"--trainer-python: no such interpreter: {path}")
        return path
    from_env = os.environ.get(TRAINER_PYTHON_ENV, "")
    if from_env:
        path = Path(from_env).expanduser()
        if not path.is_file():
            raise TrainError(f"{TRAINER_PYTHON_ENV}: no such interpreter: {path}")
        return path
    for candidate in TRAINER_VENV_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise TrainError(
        "no trainer venv found. Tried "
        + ", ".join(str(item) for item in TRAINER_VENV_CANDIDATES)
        + "; build one as training/SETUP.md says, or pass --trainer-python "
        f"/ set {TRAINER_PYTHON_ENV}."
    )


def find_task(
    outputs: Sequence[ExportedOutput], name: str = ""
) -> ExportedOutput:
    """The one exported training task, or the one ``name`` picks."""

    tasks = [
        row for row in outputs if row.kind == TASK_KIND and row.files.get("json")
    ]
    if name:
        for row in tasks:
            if row.name == name:
                return row
        raise TrainError(
            f"--task {name}: the accepted revision exports no training task "
            "by that name"
            + (f" (it has: {', '.join(row.name for row in tasks)})." if tasks
               else ".")
        )
    if not tasks:
        raise TrainError(
            "the accepted revision exports no training task: declare one "
            "with assembly.task(...) and put it in result."
        )
    if len(tasks) > 1:
        raise TrainError(
            "the accepted revision exports more than one training task; "
            "pick one with --task NAME: "
            + ", ".join(row.name for row in tasks)
            + "."
        )
    return tasks[0]


def trainer_flags(
    *,
    iterations: int,
    envs: int,
    seed: int = 0,
    label: str = "",
    init_from: str = "",
    init_from_parent_task: str = "",
    init_from_task_change: str = "",
) -> list[str]:
    """The trainer's flags, by their real names, without the bundle or
    ``--out`` — the part of the command that is the same wherever the
    trainer runs.

    ``init_from_parent_task`` and ``init_from_task_change`` are the
    curriculum pair (ADR-161): together with ``init_from`` they warm-start
    across a task change, which is what the iterate leg of the lifecycle
    walk does after a parameter sweep moved the task digest (ADR-192).
    They are passed through as given; the trainer owns the rule about
    which keys may move, and refuses the rest itself.
    """

    flags = [
        "--iterations", str(int(iterations)),
        "--envs", str(int(envs)),
        "--seed", str(int(seed)),
    ]
    if label:
        flags += ["--label", label]
    if init_from:
        flags += ["--init-from", str(Path(init_from).expanduser())]
    if init_from_parent_task:
        flags += [
            "--init-from-parent-task",
            str(Path(init_from_parent_task).expanduser()),
        ]
    if init_from_task_change:
        flags += ["--init-from-task-change", init_from_task_change]
    return flags


def trainer_command(
    python: Path | str,
    bundle: Path | str,
    out: Path | str,
    *,
    script: Path | str | None = None,
    **flags: Any,
) -> list[str]:
    """The local trainer's invocation: the venv's interpreter, the trainer,
    the bundle, ``--out``, then :func:`trainer_flags`."""

    return [
        str(python),
        str(script if script is not None else TRAINER_SCRIPT),
        str(bundle),
        "--out", str(out),
        *trainer_flags(**flags),
    ]


def remote_trainer_command(
    bundle: Path | str,
    out: Path | str,
    *,
    allow_cpu: bool = False,
    detach: bool = False,
    script: Path | str | None = None,
    **flags: Any,
) -> list[str]:
    """The remote dispatcher's invocation (ADR-089, ADR-200).

    ``remote_train.sh train <bundle> <out> [--allow-cpu] -- <trainer
    flags>``: the script copies the bundle and the model it names out of
    ``out``'s directory, runs the box's own trainer, copies the policy back
    to ``out`` and verifies its sha256 against the receipt; after ``--``
    the flags are :func:`trainer_flags`, untouched. It refuses a run that
    fell back to CPU unless ``allow_cpu`` — a policy from a silent CPU run
    is real and costs hours it did not need to.

    A warm start travels (ADR-268). ``--init-from`` and
    ``--init-from-parent-task`` name files on this machine, and the
    dispatcher lifts those two out of the trailing flags, copies them into
    the run directory's ``warm/`` and re-emits the flags pointing at the
    copies. Nothing changes here: the flags this builds are still the local
    trainer's, byte for byte, which is what makes the two legs the same
    argument list. The rewriting is transport, and transport is the
    dispatcher's job (ADR-089).
    """

    command = [str(script if script is not None else REMOTE_SCRIPT),
               "train", str(bundle), str(out)]
    if allow_cpu:
        command.append("--allow-cpu")
    if detach:
        command.append("--detach")
    return [*command, "--", *trainer_flags(**flags)]


#: The two steps a remote leg has and a local one does not (ADR-089): the
#: transport either side of the trainer. Everything else about the leg —
#: which files it reads, which file it writes, what is verified and what is
#: stored — is the same, and :func:`training_plan` is what lets a person
#: check that offline rather than by dispatching.
REMOTE_TRANSPORT_STEPS = ("copy-out", "copy-back")

#: The warm-start flags whose values are local file paths, and which the
#: remote leg therefore has to carry (ADR-268). ``--init-from-task-change``
#: is a sentence and is not here.
WARM_START_PATH_FLAGS = {
    "--init-from": "warm_start_policy",
    "--init-from-parent-task": "warm_start_parent_task",
}


def warm_start_files(command: Sequence[str]) -> dict[str, str]:
    """The warm start's local files named in ``command``, keyed by artifact
    name, or an empty mapping for a cold run.

    Read back out of the built command rather than passed in beside it, so
    the plan cannot disagree with the argument list it describes — and so
    both modes derive the same answer from the same flags.
    """

    items = [str(item) for item in command]
    found: dict[str, str] = {}
    for flag, name in WARM_START_PATH_FLAGS.items():
        if flag in items:
            index = items.index(flag)
            if index + 1 < len(items):
                found[name] = items[index + 1]
    return found


def resolve_bundle_model(bundle: Path | str) -> Path:
    """The model file a training bundle names, resolved the way the trainer
    and ``remote_train.sh`` resolve it: the recorded relative path against
    the bundle's grandparent, then its basename beside the bundle.

    The remote leg copies these two out for every run — and a warm start's
    two more beside them (ADR-268) — so a plan that cannot name the model
    is a dispatch that would fail on the box after the copy started.
    """

    path = Path(bundle)
    try:
        task = json.loads(path.read_text(encoding="utf-8"))
        relative = Path(str(task["model"]["path"]))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise TrainError(
            f"{path}: not a training bundle naming a model ({exc})."
        ) from exc
    for candidate in (path.parent.parent / relative, path.parent / relative.name):
        if candidate.exists():
            return candidate
    raise TrainError(
        f"the model {relative} this bundle references is beside neither "
        f"{path.parent.parent} nor {path.parent}."
    )


def training_plan(
    command: Sequence[str],
    *,
    bundle: Path | str,
    out: Path | str,
    remote: bool,
    allow_cpu: bool = False,
    store_as: str = "",
) -> dict[str, Any]:
    """What the training leg would do, without doing any of it (``--dry-run``).

    This answers the one question ``--remote`` raises that nothing offline
    could otherwise answer: does the box's leg land the same artifacts as
    this machine's? The plan names the files the leg touches — the bundle,
    the model beside it, the policy, and the stored asset — and the ordered
    steps that touch them. **The artifacts are identical in both modes by
    construction**, because the remote leg writes the policy to the very
    path the local trainer would have; the remote mode's steps are the
    local mode's with :data:`REMOTE_TRANSPORT_STEPS` around the trainer,
    because the trainer runs somewhere else.

    Nothing here runs a subprocess, reads ``training/.remote.env`` or
    reaches a box: a dry run is exactly as offline as ``--json``. That is
    also its limit — it proves the shape of the leg, never that the box is
    reachable, which is what ``training/remote_train.sh check`` is for.
    """

    bundle_path = Path(bundle)
    policy = Path(out)
    model = resolve_bundle_model(bundle_path)
    runner = Path(command[0])
    steps: list[dict[str, str]] = [
        {
            "step": "export",
            "where": "this machine",
            "detail": f"{bundle_path} and the model it names, {model}",
        }
    ]
    warm = warm_start_files(command)
    if remote:
        carried = f"{bundle_path.name} and {model.name}"
        if warm:
            carried += ", and " + " and ".join(
                Path(value).name for value in warm.values()
            ) + " into its warm/"
        steps.append({
            "step": "copy-out",
            "where": "this machine -> the box",
            "detail": (
                f"{runner.name} copies {carried} into the box's run directory"
            ),
        })
    steps.append({
        "step": "train",
        "where": f"the box, through {runner.name}" if remote else str(runner),
        "detail": " ".join(str(item) for item in command),
    })
    if remote:
        steps.append({
            "step": "copy-back",
            "where": "the box -> this machine",
            "detail": f"{runner.name} brings the policy home to {policy}",
        })
    steps.append({
        "step": "verify",
        "where": "this machine",
        "detail": f"{policy} hashes to the sha256 the receipt claims",
    })
    if store_as:
        steps.append({
            "step": "store",
            "where": "this machine",
            "detail": f"put_asset {store_as} into the project store",
        })
    return {
        "mode": "remote" if remote else "local",
        "runner": str(runner),
        "allow_cpu": bool(allow_cpu and remote),
        "command": [str(item) for item in command],
        "artifacts": {
            "bundle": str(bundle_path),
            "model": str(model),
            "policy": str(policy),
            "stored_asset": store_as,
            #: Present in both modes for a warm start (ADR-268), and in
            #: neither for a cold one: the files are the leg's inputs
            #: wherever the trainer runs.
            **warm,
        },
        "steps": steps,
        #: Always false. The field is here so a pipeline reading a plan can
        #: never mistake it for a receipt.
        "executed": False,
    }


def verify_returned_policy(out: Path | str, receipt: dict[str, Any]) -> None:
    """The policy at ``out`` is the one the receipt describes, or the leg
    fails — and the receipt's ``out`` becomes that local path.

    The local trainer writes the file it hashes, so for it this is a check
    that cannot fail. The remote dispatcher hashes what came back, and so
    does this, because the sha256 in the receipt is the digest the script
    will name (``assembly.policy(sha256=…)``) and a wrong file at the right
    path is otherwise a policy refusal with no obvious cause. The remote
    receipt's ``out`` is a path on the box; it is kept under
    ``trainer_out`` and ``out`` is where the file is *here*, which is what
    every later leg reads.
    """

    path = Path(out)
    claimed = str(receipt.get("sha256") or "")
    if not path.is_file():
        raise TrainError(
            f"the trainer reported sha256 {claimed[:12]}… but no policy is at "
            f"{path}; nothing came back."
        )
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if claimed and actual != claimed:
        raise TrainError(
            f"{path} hashes {actual[:12]}…; the trainer wrote {claimed[:12]}…. "
            "The transfer is wrong. Do not paste either digest into a script."
        )
    reported = str(receipt.get("out") or "")
    if reported and reported != str(path):
        receipt["trainer_out"] = reported
    receipt["out"] = str(path)


#: How many of the trainer's last stderr lines are kept for a failure
#: message. A jax or MuJoCo traceback is a dozen frames; four lines of it
#: is the exception and the frame that raised, which is the part that
#: names the cause.
_STDERR_TAIL_LINES = 4


def _tee_stderr(stream, keep: collections.deque) -> None:
    """Write the trainer's stderr through to ours, keeping the last lines.

    Progress must still stream live while the trainer runs, so this reads
    a line at a time and writes it straight on rather than buffering the
    whole stream and replaying it at the end.
    """

    for line in stream:
        sys.stderr.write(line)
        sys.stderr.flush()
        if line.strip():
            keep.append(line.rstrip())
    stream.close()


def run_trainer(
    command: Sequence[str], *, timeout: float = 0.0
) -> dict[str, Any]:
    """Run the trainer and return its receipt.

    Its stderr — the progress lines and the witness margin — passes straight
    through to ours, where progress belongs (``docs/CLI.md`` §2). Its stdout
    is one JSON object on the last line, and that object is the receipt:
    nothing here reads a number off a stream the trainer did not mean as
    data (ADR-093). A ``timeout`` of zero is no limit.

    **A failure names its cause** (ADR-280). Passing stderr straight through
    is right for a person watching a terminal and useless to the caller who
    reads ``--json``: an MJX refusal to build the model arrives as a
    traceback on a stream the envelope never saw, so ``walk.json`` reported
    two benign import warnings off stdout and not the ``NotImplementedError``
    that actually stopped the leg. The stream is therefore *teed* — written
    through as before, and its last lines kept — so the machine-readable
    error carries what the terminal showed.
    """

    try:
        process = subprocess.Popen(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        raise TrainError(f"could not run the trainer: {exc}") from exc

    # Both pipes are drained by threads: stderr through to ours as it
    # arrives, stdout into a buffer for the receipt. Draining only one of
    # them would deadlock a chatty trainer on the other's full pipe.
    kept: collections.deque = collections.deque(maxlen=_STDERR_TAIL_LINES)
    chunks: list[str] = []
    pumps = [
        threading.Thread(
            target=_tee_stderr, args=(process.stderr, kept), daemon=True
        ),
        threading.Thread(target=lambda: chunks.append(process.stdout.read())),
    ]
    for pump in pumps:
        pump.start()
    try:
        process.wait(timeout=timeout or None)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        for pump in pumps:
            pump.join(timeout=5.0)
        raise TrainError(
            f"the trainer was stopped after {timeout:g}s (--timeout)."
        ) from None
    for pump in pumps:
        pump.join(timeout=5.0)
    process.stdout.close()
    stdout = "".join(chunks)

    if process.returncode != 0:
        # The remote dispatcher explains its refusals on stdout (``FAIL:
        # ...``), which nobody sees once it is captured; the trainer
        # explains its own on stderr. Both tails go into the error instead
        # of the bin, stderr last because it is where a crash lands.
        tail = [line for line in stdout.splitlines() if line.strip()]
        tail = tail[-_STDERR_TAIL_LINES:] + list(kept)
        raise TrainError(
            f"the trainer exited {process.returncode}; its stderr is above."
            + ("".join("\n  " + line for line in tail) if tail else "")
        )
    receipt = last_json_line(stdout)
    if receipt is None:
        raise TrainError("the trainer exited 0 but printed no receipt.")
    return receipt


def last_json_line(stdout: str) -> dict[str, Any] | None:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None
