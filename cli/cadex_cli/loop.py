# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The training loop's run registry and its supervisor (ADR-464).

The product agent designs a task, trains a policy on it, evaluates the
policy against the task's success spec and revises. Three of those four are
tools it already had or ``cadex evaluate`` already was; this module is the
fourth, **a training run the agent can start, watch and stop, and that
outlives the agent session that started it**.

A run is a directory, ``runs/<name>/`` in the project, and three files say
everything about it:

* ``registration.json`` is written **before anything is launched**: the
  accepted revision and the task it trains, the trainer's settings and seed,
  the wall-clock budget, the stop rule, and the one-line reason the run
  exists. A run with no budget is never registered, so it is never started.
* ``training-status.json`` is the supervisor's: how the run ended and what
  it left. It is rewritten atomically and only by the supervisor.
* ``train/progress.json`` is the trainer's own, rewritten every iteration.

The supervisor is ``python -m cadex_cli.loop RUN_DIR``, spawned into a
session of its own so that the agent session, the CLI and the terminal can all
go away while it trains. It holds two advisory locks for as long as it
lives: the run's, which is how a reader tells a live run from one whose
supervisor was killed (an **interruption**, never an attempt), and the
machine's, which is what makes training one job at a time. It stops the
trainer at the budget, on a stop request, or when it is itself told to
terminate, and it never signals a process it did not start.

Nothing here knows what behaviour is being trained. A task is a task.
"""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from typing import Any, Iterator, Mapping, Sequence

from .checkpoints import CheckpointRollouts
from .engine import EngineError, resolve_engine
from .review_record import RUNS_DIRNAME, write_run_record
from .smoke import SmokeError, retained_attempt, smoke_interpreter
from .train import (
    TASK_KIND, TrainError, last_json_line, resolve_trainer_python, trainer_command,
    ungrounded_channels, verify_returned_policy,
)

REGISTRATION_SCHEMA = "cadex-training-registration-v1"
STATUS_SCHEMA = "cadex-training-status-v1"
LEDGER_SCHEMA = "cadex-loop-ledger-v1"
REGISTRATION_NAME = "registration.json"
STATUS_NAME = "training-status.json"
STOP_NAME = "stop-requested.json"
LOCK_NAME = "supervisor.lock"
TRAIN_DIRNAME = "train"
LOG_NAME = "train.log"
STDOUT_NAME = "trainer-stdout.log"
#: One line per thing the loop did, in the project root: a run registered, a
#: run ended, a stop asked for, an evaluation measured. It is what a later
#: session -- and the closing report -- reads the rounds back from.
LEDGER_NAME = "loop-ledger.jsonl"

#: The machine's one training slot. A file lock rather than a pid file: the
#: kernel drops it when the holder dies, so nothing is ever stale.
MACHINE_LOCK_ENV = "CADEX_TRAIN_LOCK"

#: The longest budget a run may state. A bound on a typo, not a policy.
MAX_BUDGET_S = 6 * 3600.0
#: How long a stopped trainer is given to exit before it is killed.
TERMINATION_GRACE_S = 10.0
POLL_S = 0.25
#: How long ``launch`` waits for the supervisor to say it has the slot.
LAUNCH_WAIT_S = 20.0
#: A registered run with no supervisor after this long was never started.
NEVER_STARTED_S = 60.0

#: The states a run can be read in. ``registered`` and ``running`` are live;
#: ``interrupted`` is a run whose supervisor is gone without a verdict.
LIVE_STATES = ("registered", "running")
END_STATES = ("finished", "collapsed", "failed", "stopped", "budget_exhausted",
              "interrupted", "refused")

_RUN_NAME = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")

#: Trainer settings beyond ``train.trainer_flags``, by the trainer's own flag
#: names and types. ``test_loop.py`` reads them back out of the trainer's
#: source, so a rename there fails here.
EXTRA_SETTINGS: dict[str, tuple[str, type]] = {
    "unroll": ("--unroll", int),
    "epochs": ("--epochs", int),
    "learning_rate": ("--learning-rate", float),
    "discount": ("--discount", float),
    "gae_lambda": ("--gae-lambda", float),
    "clip": ("--clip", float),
    "entropy": ("--entropy", float),
    "value_weight": ("--value-weight", float),
    "initial_std": ("--initial-std", float),
    "action_filter_alpha": ("--action-filter-alpha", float),
    "command_slew_deg": ("--command-slew-deg", float),
    "goal_pool": ("--goal-pool", int),
    "checkpoint_every": ("--checkpoint-every", int),
}
#: ``hidden`` is the one list: the layer widths, ``--hidden 64 64``.
BASE_SETTINGS = ("iterations", "envs", "seed", "label", "init_from",
                 "init_from_parent_task", "init_from_task_change")
SETTING_NAMES = (*BASE_SETTINGS, "hidden", *EXTRA_SETTINGS)

STOP_RULE = (
    "stops at the last iteration, at the wall-clock budget, when the mean "
    "episode collapses (--stop-on-collapse), or when a stop is requested"
)


class LoopError(RuntimeError):
    """The run could not be registered, launched or read; the text says why."""


def _now() -> float:
    return time.time()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    scratch = path.with_name(path.name + ".tmp")
    scratch.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    scratch.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def machine_lock_path() -> Path:
    given = os.environ.get(MACHINE_LOCK_ENV, "").strip()
    return Path(given).expanduser() if given else Path.home() / ".cache" / "cadex" / "training.lock"


def _try_lock(path: Path) -> Any:
    """The open, locked file, or None when another process holds the lock."""

    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+", encoding="utf-8")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def lock_held(path: Path) -> bool:
    """True when some live process holds ``path``'s lock."""

    if not path.exists():
        return False
    handle = _try_lock(path)
    if handle is None:
        return True
    handle.close()
    return False


#: What every refusal of the machine's slot says, the supervisor's and
#: ``cadex train``'s alike.
SLOT_BUSY = "another training run holds this machine's one training slot"


@contextmanager
def machine_slot() -> Iterator[None]:
    """Hold the machine's one training slot for the block, or raise LoopError.

    The supervisor holds it for its whole life; ``cadex train``, and every
    command that trains through it, holds it around a local trainer (ADR-543).
    """

    handle = _try_lock(machine_lock_path())
    if handle is None:
        raise LoopError(f"{SLOT_BUSY}; wait for it to end.")
    try:
        yield
    finally:
        handle.close()


def append_ledger(root: Path, kind: str, **fields: Any) -> None:
    """One line in the project's loop ledger; a ledger that cannot be written
    never fails the thing it describes."""

    row = {"schema": LEDGER_SCHEMA, "at": _now(), "kind": kind, **fields}
    try:
        with open(Path(root) / LEDGER_NAME, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    except OSError:
        pass


def read_ledger(root: Path) -> list[dict[str, Any]]:
    try:
        lines = (Path(root) / LEDGER_NAME).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("schema") == LEDGER_SCHEMA:
            rows.append(row)
    return rows


def retained_task(root: Path, task_name: str = "") -> dict[str, Any]:
    """The accepted revision's training task, as the store retained it.

    Read and never rebuilt, so the bundle a run trains on is the one the
    engine accepted. One task, or the one ``task_name`` picks.
    """

    try:
        state, staging, result = retained_attempt(root)
    except SmokeError as exc:
        raise LoopError(str(exc)) from exc
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise LoopError(f"cannot read the retained accepted attempt: {exc}") from exc
    items = {str(item["name"]): item for item in result["outputs"]}
    tasks = [name for name, item in items.items() if item.get("artifact_kind") == TASK_KIND]
    if task_name and task_name not in tasks:
        raise LoopError(f"the accepted revision declares no task {task_name!r}"
                        + (f" (it has: {', '.join(tasks)})." if tasks else "."))
    if not tasks:
        raise LoopError("the accepted revision declares no training task: declare one "
                        "with assembly.task(...) and put it in result.")
    if not task_name and len(tasks) > 1:
        raise LoopError("the accepted revision declares more than one task; name one: "
                        + ", ".join(tasks) + ".")
    name = task_name or tasks[0]

    def retained(item: Mapping[str, Any]) -> Path:
        path = (staging / str(item.get("artifact_path") or "")).resolve()
        if not path.is_relative_to(staging) or not path.is_file():
            raise LoopError(f"missing or escaping retained artifact: {item.get('name')}")
        if item.get("artifact_sha256") and _sha256(path) != item["artifact_sha256"]:
            raise LoopError(f"retained artifact digest mismatch: {item.get('name')}")
        return path

    task_path = retained(items[name])
    task = json.loads(task_path.read_text(encoding="utf-8"))
    model_item = items.get(str((task.get("model") or {}).get("output")))
    if model_item is None:
        raise LoopError(f"task {name} names no retained MJCF model")
    success = task.get("success") if isinstance(task.get("success"), Mapping) else {}
    return {
        "accepted_revision": str(state["accepted_revision"]),
        "accepted_digest": str(state.get("accepted_digest") or ""),
        "task_output": name,
        "task": task_path,
        "model": retained(model_item),
        "evaluation_seeds": [int(seed) for seed in success.get("seeds") or []],
        "has_success_spec": bool(success),
    }


def _settings(raw: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """The settings as registered, and the extra trainer flags they become."""

    unknown = sorted(set(raw) - set(SETTING_NAMES))
    if unknown:
        raise LoopError("unknown training setting(s): " + ", ".join(unknown)
                        + ". The settings are: " + ", ".join(SETTING_NAMES) + ".")
    settings: dict[str, Any] = {
        "iterations": int(raw.get("iterations", 200)),
        "envs": int(raw.get("envs", 256)),
        "seed": int(raw.get("seed", 0)),
    }
    if settings["iterations"] < 1 or settings["envs"] < 1:
        raise LoopError("iterations and envs must be at least 1.")
    if not 0 <= settings["seed"] <= 4294967295:
        raise LoopError("seed must be between 0 and 4294967295.")
    for key in ("label", "init_from", "init_from_parent_task", "init_from_task_change"):
        if raw.get(key):
            settings[key] = str(raw[key])
    warm = [key for key in ("init_from_parent_task", "init_from_task_change") if key in settings]
    if warm and not all(key in settings for key in
                        ("init_from", "init_from_parent_task", "init_from_task_change")):
        raise LoopError("a warm start across a task change needs init_from, "
                        "init_from_parent_task and init_from_task_change together.")
    extra: list[str] = []
    if raw.get("hidden") is not None:
        hidden = [int(width) for width in raw["hidden"]]
        if not hidden or min(hidden) < 1:
            raise LoopError("hidden must be one or more positive layer widths.")
        settings["hidden"] = hidden
        extra += ["--hidden", *(str(width) for width in hidden)]
    for key, (flag, kind) in EXTRA_SETTINGS.items():
        if raw.get(key) is None:
            continue
        try:
            value = kind(raw[key])
        except (TypeError, ValueError) as exc:
            raise LoopError(f"{key} must be {kind.__name__}.") from exc
        settings[key] = value
        extra += [flag, str(value)]
    return settings, extra


def live_run(root: Path) -> str:
    """The name of this project's live run, or the empty string."""

    for run in list_runs(root):
        if run["state"] in LIVE_STATES:
            return str(run["run"])
    return ""


def register(root: Path, *, run: str, budget_s: float, reason: str,
             settings: Mapping[str, Any] | None = None, task_name: str = "",
             trainer_python: str = "") -> Path:
    """Pre-register one training run and return its directory. Launches nothing.

    Everything the run will do is on disk before it does any of it: the
    revision and task, the settings and seed, the budget, the stop rule and
    the reason. ``--stop-on-collapse`` is always on.
    """

    root = Path(root).resolve()
    if not _RUN_NAME.fullmatch(str(run or "")):
        raise LoopError("run must be a short name of lowercase letters, digits, '.', '_' "
                        "and '-', starting with a letter or digit.")
    try:
        budget = float(budget_s)
    except (TypeError, ValueError) as exc:
        raise LoopError("budget_s must be a number of seconds.") from exc
    if not 0.0 < budget <= MAX_BUDGET_S:
        raise LoopError(f"budget_s must be within (0, {MAX_BUDGET_S:g}] seconds of wall "
                        "clock: a run with no budget is not started.")
    reason = " ".join(str(reason or "").split())
    if len(reason) < 12:
        raise LoopError("reason must say, in a sentence, what this run is for: the "
                        "measurement that motivated it and what is expected to change.")
    chosen, extra = _settings(settings or {})
    run_dir = root / RUNS_DIRNAME / run
    if run_dir.exists():
        raise LoopError(f"runs/{run} already exists; a run's name is used once.")
    busy = live_run(root)
    if busy:
        raise LoopError(f"run {busy} of this project is still live; wait for it or stop it.")
    if lock_held(machine_lock_path()):
        raise LoopError(f"{SLOT_BUSY}; wait for it to end.")
    task = retained_task(root, task_name)
    if chosen["seed"] in task["evaluation_seeds"]:
        raise LoopError(f"seed {chosen['seed']} is one of the task's evaluation seeds; "
                        "an evaluation seed is never a training seed.")
    ungrounded = ungrounded_channels(task["task"])
    if ungrounded:
        raise LoopError(
            f"{len(ungrounded)} policy channel(s) name no onboard sensor that measures "
            f"them: {', '.join(ungrounded[:8])}{' ...' if len(ungrounded) > 8 else ''}. "
            "Declare a sensor for each and pass it as observation(..., sensor=...), or "
            "mark a simulation-only channel role='privileged'.")
    for key in ("init_from", "init_from_parent_task"):
        if key in chosen:
            path = Path(chosen[key]).expanduser()
            path = path if path.is_absolute() else root / path
            if not path.is_file():
                hint = ""
                if key == "init_from_parent_task":
                    bundles = [f"{run['run']}: {task_bundle(run)['path']}"
                               for run in list_runs(root)]
                    hint = (" It is the task bundle the parent run trained on; each "
                            "run's is its train_status task_bundle"
                            + (" -- " + "; ".join(bundles) + "." if bundles else "."))
                raise LoopError(f"{key}: no such file: {chosen[key]}.{hint}")
            chosen[key] = str(path)
    try:
        python = resolve_trainer_python(trainer_python or None)
    except TrainError as exc:
        raise LoopError(str(exc)) from exc

    train_dir = run_dir / TRAIN_DIRNAME
    train_dir.mkdir(parents=True)
    bundle = train_dir / task["task"].name
    shutil.copyfile(task["task"], bundle)
    shutil.copyfile(task["model"], train_dir / task["model"].name)
    policy = train_dir / f"{task['task_output']}.cxpolicy"
    command = trainer_command(
        python, bundle, policy, stop_on_collapse=True,
        **{key: chosen[key] for key in BASE_SETTINGS if key in chosen}) + extra
    registration = {
        "schema": REGISTRATION_SCHEMA,
        "run": run,
        "registered_at": _now(),
        "reason": reason,
        "accepted_revision": task["accepted_revision"],
        "accepted_digest": task["accepted_digest"],
        "task_output": task["task_output"],
        "task_sha256": _sha256(bundle),
        "model_sha256": _sha256(train_dir / task["model"].name),
        "has_success_spec": task["has_success_spec"],
        "evaluation_seeds": task["evaluation_seeds"],
        "settings": chosen,
        "budget_s": budget,
        "stop_rule": STOP_RULE,
        "bundle": f"{TRAIN_DIRNAME}/{bundle.name}",
        "model": f"{TRAIN_DIRNAME}/{task['model'].name}",
        "policy": f"{TRAIN_DIRNAME}/{policy.name}",
        "command": command,
    }
    _write_json(run_dir / REGISTRATION_NAME, registration)
    _write_json(run_dir / STATUS_NAME, {"schema": STATUS_SCHEMA, "run": run, "state": "registered"})
    _record(root, run_dir, registration, "running")
    append_ledger(root, "train_registered", run=run, reason=reason,
                  accepted_revision=task["accepted_revision"], task=task["task_output"],
                  settings=chosen, budget_s=budget)
    return run_dir


def _record(root: Path, run_dir: Path, registration: Mapping[str, Any], status: str,
            state: Mapping[str, Any] | None = None) -> None:
    """The run as the review dashboard reads it: ``run.json``, mode ``loop``."""

    state = dict(state or {})
    policy = dict(state.get("policy") or {})
    try:
        write_run_record(
            run_dir, project_root=root, status=status, mode="loop",
            error=str(state.get("reason") or "") if status == "failed" else None,
            accepted_revision=str(registration["accepted_revision"]),
            digest=str(registration["accepted_digest"]),
            identity_source="accepted attempt retained when the run was registered",
            training=dict(state.get("receipt") or {}),
            requested={**dict(registration["settings"]), "budget_s": registration["budget_s"],
                       "reason": registration["reason"], "task": registration["task_output"]},
            policy_name=Path(str(registration["policy"])).name if policy else "",
            policy_sha256=str(policy.get("sha256") or ""),
            task_bundle=run_dir / str(registration["bundle"]),
            task_sha256=str(registration["task_sha256"]),
            model_xml=run_dir / str(registration["model"]),
            snapshot_docs=True,
        )
    except (OSError, ValueError, KeyError, TypeError):
        pass


def launch(run_dir: Path, *, wait_s: float = LAUNCH_WAIT_S) -> dict[str, Any]:
    """Start the run's supervisor in a session of its own and return the run
    as read once the supervisor has the training slot, or has been refused it."""

    run_dir = Path(run_dir)
    (run_dir / TRAIN_DIRNAME).mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    cli_dir = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = cli_dir + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    with open(run_dir / "supervisor.log", "ab") as log:
        try:
            subprocess.Popen(
                [sys.executable, "-m", "cadex_cli.loop", str(run_dir)],
                stdin=subprocess.DEVNULL, stdout=log, stderr=log, env=env,
                start_new_session=True, close_fds=True,
            )
        except OSError as exc:
            raise LoopError(f"could not start the supervisor: {exc}") from exc
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        if read_run(run_dir)["state"] != "registered":
            break
        time.sleep(POLL_S)
    return read_run(run_dir)


def request_stop(run_dir: Path, reason: str, *, wait_s: float = 30.0) -> dict[str, Any]:
    """Ask a live run's supervisor to stop it, and wait for it to say it has."""

    run_dir = Path(run_dir)
    run = read_run(run_dir)
    if run["state"] not in LIVE_STATES:
        return run
    _write_json(run_dir / STOP_NAME, {"requested_at": _now(), "reason": str(reason or "")})
    append_ledger(run_dir.parents[1], "train_stop_requested", run=run_dir.name,
                  reason=str(reason or ""))
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        run = read_run(run_dir)
        if run["state"] not in LIVE_STATES:
            break
        time.sleep(POLL_S)
    return run


def read_run(run_dir: Path) -> dict[str, Any]:
    """One run, whole: its registration, how it stands, and the trainer's progress.

    ``state`` is the supervisor's word while the supervisor lives. A status
    still saying ``running`` under a lock nobody holds is a supervisor that
    was killed: the run is reported ``interrupted``, which is not an attempt.
    """

    run_dir = Path(run_dir)
    registration = _read_json(run_dir / REGISTRATION_NAME)
    if registration.get("schema") != REGISTRATION_SCHEMA:
        raise LoopError(f"runs/{run_dir.name} is not a registered training run.")
    status = _read_json(run_dir / STATUS_NAME)
    state = str(status.get("state") or "registered")
    reason = str(status.get("reason") or "")
    if state == "running" and not lock_held(run_dir / LOCK_NAME):
        # Read twice: the supervisor writes its verdict and then lets go.
        status = _read_json(run_dir / STATUS_NAME)
        state = str(status.get("state") or "registered")
        reason = str(status.get("reason") or "")
        if state == "running":
            state = "interrupted"
            reason = ("the supervisor is gone and left no verdict: the run was killed. "
                      "This is an interruption, not an attempt.")
    elif (state == "registered" and not lock_held(run_dir / LOCK_NAME)
          and _now() - float(registration.get("registered_at") or 0.0) > NEVER_STARTED_S
          and _read_json(run_dir / STATUS_NAME).get("state", "registered") == "registered"):
        state = "interrupted"
        reason = "the run was registered and its supervisor never started: nothing was trained."
    progress = _read_json(run_dir / TRAIN_DIRNAME / "progress.json")
    started = status.get("started_at")
    ended = status.get("ended_at")
    return {
        "run": run_dir.name,
        "dir": str(run_dir),
        "state": state,
        "reason": reason,
        "registration": registration,
        "status": status,
        "progress": progress,
        "elapsed_s": (None if started is None
                      else round(float(ended if ended is not None else _now()) - float(started), 1)),
    }


def list_runs(root: Path) -> list[dict[str, Any]]:
    """Every registered training run of the project, oldest first."""

    runs_dir = Path(root) / RUNS_DIRNAME
    if not runs_dir.is_dir():
        return []
    runs = []
    for child in sorted(runs_dir.iterdir()):
        if (child / REGISTRATION_NAME).is_file():
            try:
                runs.append(read_run(child))
            except LoopError:
                continue
    runs.sort(key=lambda run: float(run["registration"].get("registered_at") or 0.0))
    return runs


def run_checkpoints(run: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every checkpoint the run left on disk, each with its file's own digest.

    The files are the authority, not ``progress.json``: the trainer writes a
    checkpoint before it rewrites its progress, so a run stopped between the
    two (ot11 ``bal-1``, ended by its budget) leaves its last checkpoint
    unlisted, and ``best`` is rewritten in place under a digest the progress
    names only for an earlier iteration. A checkpoint is a file the progress
    lists or one named the trainer's way, ``<task>.<tag>.cxpolicy``; what the
    progress knows of it -- the iteration and the reward per step -- is kept
    only where its digest is the file's.
    """

    train_dir = Path(str(run["dir"])) / TRAIN_DIRNAME
    listed = list((run.get("progress") or {}).get("checkpoints") or [])
    output = str(run["registration"].get("task_output") or "")
    names = {str(item.get("path")) for item in listed}
    if output and train_dir.is_dir():
        names.update(path.name for path in train_dir.glob(f"{glob.escape(output)}.*.cxpolicy"))
    rows = []
    for name in sorted(names):
        path = train_dir / name
        if Path(name).name != name or not path.is_file():
            continue
        sha = _sha256(path)
        item = next((item for item in reversed(listed)
                     if str(item.get("path")) == name and item.get("sha256") == sha), {})
        tag = str(item.get("tag") or "")
        if not tag:
            tag = name[len(output) + 1:-len(".cxpolicy")] if name.startswith(f"{output}.") else name
        iteration = item.get("iteration")
        if iteration is None and tag.isdigit():
            iteration = int(tag) - 1
        rows.append({"path": str(path), "tag": tag, "iteration": iteration, "sha256": sha,
                     "reward_per_step": item.get("reward_per_step")})
    return rows


def runs_that_trained(root: Path, policy_sha256: str) -> list[str]:
    """The registered runs that produced a policy: its final policy, or any
    checkpoint it wrote. An evaluated checkpoint of a run that never got to
    its last iteration is still that run's policy (ot11 ``bal-1``)."""

    names = []
    for run in list_runs(root):
        digests = {str((run["status"].get("policy") or {}).get("sha256") or "")}
        digests.update(str(item.get("sha256") or "")
                       for item in (run.get("progress") or {}).get("checkpoints") or [])
        digests.update(row["sha256"] for row in run_checkpoints(run))
        if policy_sha256 and policy_sha256 in digests:
            names.append(run["run"])
    return names


#: How many points of the reward curve a view carries.
VIEW_CURVE_POINTS = 16
VIEW_LOG_LINES = 8


def _thinned(curve: Any) -> list[Any]:
    rows = list(curve or [])
    if len(rows) <= VIEW_CURVE_POINTS:
        return rows
    step = (len(rows) - 1) / (VIEW_CURVE_POINTS - 1)
    return [rows[round(index * step)] for index in range(VIEW_CURVE_POINTS)]


#: What a view says about warm-starting from the run it shows.
WARM_START = (
    "To warm-start a new run from this one, pass settings init_from=<a policy or "
    "checkpoint path of this run>, init_from_parent_task=<task_bundle.path> and "
    "init_from_task_change=<one line on what changed in the task since>. The trainer "
    "refuses a change to what the network reads or emits.")


def task_bundle(run: Mapping[str, Any]) -> dict[str, Any]:
    """The task bundle a run trained on, as a warm start from it names it."""

    registration = run["registration"]
    return {"path": str(Path(str(run["dir"])) / str(registration.get("bundle") or "")),
            "sha256": registration.get("task_sha256")}


def run_view(run: Mapping[str, Any]) -> dict[str, Any]:
    """A run as the agent reads it: bounded, and saying what to do next."""

    registration = run["registration"]
    progress = run.get("progress") or {}
    status = run.get("status") or {}
    run_dir = Path(str(run["dir"]))
    view: dict[str, Any] = {
        "run": run["run"],
        "state": run["state"],
        "reason": run.get("reason") or registration.get("reason"),
        "registered_for": registration.get("reason"),
        "accepted_revision": registration.get("accepted_revision"),
        "task": registration.get("task_output"),
        "task_bundle": task_bundle(run),
        "settings": registration.get("settings"),
        "budget_s": registration.get("budget_s"),
        "elapsed_s": run.get("elapsed_s"),
        "stop_rule": registration.get("stop_rule"),
    }
    if progress:
        view["progress"] = {
            "iteration": progress.get("iteration"),
            "total": progress.get("total"),
            "eta_s": progress.get("eta_s"),
            "device": progress.get("device"),
            "reward_per_step": progress.get("reward_per_step"),
            "best_reward_per_step": progress.get("best_reward_per_step"),
            "best_iteration": progress.get("best_iteration"),
            "episode_steps": progress.get("episode_steps"),
            "action_std": progress.get("action_std"),
            "warning": progress.get("warning") or None,
            "error": progress.get("error") or None,
            "reward_curve": _thinned(progress.get("curve")),
            "episode_steps_curve": _thinned(progress.get("episode_steps_curve")),
        }
        checkpoints = run_checkpoints(run)
        if checkpoints:
            view["checkpoints"] = checkpoints[-6:]
    policy = status.get("policy")
    if policy or view.get("checkpoints"):
        view["warm_start"] = WARM_START
    if policy:
        view["policy"] = policy
        view["next"] = (
            "Store it with put_asset source_path=<policy.path>, name it in the script with "
            "assembly.policy(task, weights=<stored name>, sha256=<policy.sha256>), then call "
            "evaluate. The reward curve is not a verdict; the evaluation is.")
    elif run["state"] in LIVE_STATES:
        view["next"] = "Call train_status with wait_s to wait for it, or train_stop to end it."
    else:
        view["log_tail"] = _log_tail(run_dir / TRAIN_DIRNAME / LOG_NAME)
        view["next"] = (
            "No final policy. A checkpoint listed above is a complete policy and can be "
            "stored and evaluated the same way; otherwise diagnose from the progress and "
            "the log tail, revise, and register a new run under a new name.")
    return view


def _log_tail(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [line[:240] for line in lines if line.strip()][-VIEW_LOG_LINES:]


# -- the supervisor ------------------------------------------------------------


def _stop_trainer(process: "subprocess.Popen[bytes]") -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=TERMINATION_GRACE_S)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _checkpoint_rollouts(run_dir: Path, registration: Mapping[str, Any]) -> CheckpointRollouts | None:
    """The run's checkpoint watcher, when it writes checkpoints and an engine
    is there to roll them out (ADR-544); otherwise None, and the run trains
    exactly as it would have."""

    command = [str(item) for item in registration.get("command") or []]
    try:
        every = int(command[command.index("--checkpoint-every") + 1])
    except (ValueError, IndexError):
        return None
    if every <= 0:
        return None
    try:
        engine = resolve_engine(None)
    except EngineError as exc:
        print(f"{run_dir}: no checkpoint rollouts: {exc}", file=sys.stderr)
        return None
    return CheckpointRollouts(
        run_dir / TRAIN_DIRNAME, output=Path(str(registration["policy"])).stem,
        bundle=run_dir / str(registration["bundle"]), model=run_dir / str(registration["model"]),
        python=smoke_interpreter(engine), module_dir=engine.module_dir)


def supervise(run_dir: Path) -> int:
    """Run one registered training run to its end. The detached process's main."""

    run_dir = Path(run_dir).resolve()
    registration = _read_json(run_dir / REGISTRATION_NAME)
    if registration.get("schema") != REGISTRATION_SCHEMA:
        print(f"{run_dir}: not a registered training run", file=sys.stderr)
        return 2
    root = run_dir.parents[1]
    status_path = run_dir / STATUS_NAME
    base = {"schema": STATUS_SCHEMA, "run": run_dir.name, "supervisor_pid": os.getpid()}

    def end(state: str, reason: str, **fields: Any) -> None:
        payload = {**base, "state": state, "reason": reason, "ended_at": _now(), **fields}
        _write_json(status_path, payload)
        _record(root, run_dir, registration,
                "ok" if state == "finished" else "failed", payload)
        append_ledger(root, "train_ended", run=run_dir.name, state=state, reason=reason,
                      policy_sha256=(fields.get("policy") or {}).get("sha256"),
                      wall_time_s=fields.get("wall_time_s"))

    own = _try_lock(run_dir / LOCK_NAME)
    if own is None:
        print(f"{run_dir}: already supervised", file=sys.stderr)
        return 2
    if _read_json(status_path).get("state") != "registered":
        print(f"{run_dir}: already started; a run is launched once", file=sys.stderr)
        return 2
    machine = _try_lock(machine_lock_path())
    if machine is None:
        end("refused", f"{SLOT_BUSY}.")
        return 3

    told: list[int] = []
    for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(number, lambda received, _frame: told.append(received))

    train_dir = run_dir / TRAIN_DIRNAME
    started = _now()
    clock = time.monotonic()
    budget = float(registration["budget_s"])
    base["started_at"] = started
    _write_json(status_path, {**base, "state": "running"})
    rollouts = _checkpoint_rollouts(run_dir, registration)
    try:
        with open(train_dir / LOG_NAME, "ab") as log, open(train_dir / STDOUT_NAME, "wb") as out:
            try:
                process = subprocess.Popen(
                    [str(item) for item in registration["command"]],
                    stdin=subprocess.DEVNULL, stdout=out, stderr=log)
            except OSError as exc:
                end("failed", f"could not run the trainer: {exc}", wall_time_s=0.0)
                return 1
            verdict = ("", "")
            while process.poll() is None:
                if told:
                    verdict = ("interrupted",
                               f"the supervisor was told to terminate (signal {told[0]}). "
                               "This is an interruption, not an attempt.")
                elif (run_dir / STOP_NAME).is_file():
                    asked = _read_json(run_dir / STOP_NAME)
                    verdict = ("stopped", "stop requested: " + str(asked.get("reason") or "no reason given"))
                elif time.monotonic() - clock > budget:
                    verdict = ("budget_exhausted",
                               f"the wall-clock budget of {budget:g} s ran out before the last iteration.")
                if verdict[0]:
                    _stop_trainer(process)
                    break
                if rollouts is not None:
                    rollouts.poll()
                time.sleep(POLL_S)
        wall = round(time.monotonic() - clock, 2)
        progress = _read_json(train_dir / "progress.json")
        common = {"wall_time_s": wall, "exit": process.returncode,
                  "iterations_run": int(progress.get("iteration", -1)) + 1}
        if verdict[0]:
            end(verdict[0], verdict[1], **common)
            return 0 if verdict[0] != "interrupted" else 1
        if process.returncode != 0:
            collapse = str(progress.get("warning") or "")
            if collapse and "Stopped at" in str(progress.get("error") or ""):
                end("collapsed", collapse, **common)
            else:
                tail = _log_tail(train_dir / LOG_NAME)
                end("failed", f"the trainer exited {process.returncode}"
                    + (": " + tail[-1] if tail else "."), **common)
            return 1
        try:
            stdout = (train_dir / STDOUT_NAME).read_text(encoding="utf-8", errors="replace")
        except OSError:
            stdout = ""
        receipt = last_json_line(stdout)
        policy_path = run_dir / str(registration["policy"])
        if receipt is None:
            end("failed", "the trainer exited 0 but printed no receipt.", **common)
            return 1
        try:
            verify_returned_policy(policy_path, receipt)
        except TrainError as exc:
            end("failed", str(exc), **common)
            return 1
        if receipt.get("task_sha256") not in (None, "", registration["task_sha256"]):
            end("failed", "the trainer's receipt names another task than the one registered.",
                **common)
            return 1
        keep = ("sha256", "bytes", "reward_per_step", "best_reward_per_step", "best_iteration",
                "episode_steps", "action_std", "wall_time_s", "device", "task_sha256",
                "model_sha256", "witness_error", "witness_tolerance", "parameters")
        end("finished", "the trainer ran every iteration and its policy hashes to its receipt.",
            policy={"path": str(policy_path), "sha256": str(receipt["sha256"]),
                    "bytes": receipt.get("bytes")},
            receipt={key: receipt[key] for key in keep if key in receipt}, **common)
        return 0
    finally:
        if rollouts is not None:
            # The rollouts left over are CPU work: the slot is the GPU's, so
            # it is given back before they run (ADR-544).
            machine.close()
            rollouts.drain(finish=not told)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: python -m cadex_cli.loop RUN_DIR", file=sys.stderr)
        return 2
    return supervise(Path(args[0]))


if __name__ == "__main__":
    raise SystemExit(main())
