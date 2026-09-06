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
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any, Sequence

from .engine import REPO_ROOT
from .export import ExportedOutput

#: The trainer, by path from the repository root. The CLI runs from the
#: repository (``docs/CLI.md`` §8), and so does the trainer: neither is in
#: a payload, and this is the one place the two meet.
TRAINER_SCRIPT = REPO_ROOT / "training" / "cadex_train.py"

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


def trainer_command(
    python: Path | str,
    bundle: Path | str,
    out: Path | str,
    *,
    iterations: int,
    envs: int,
    seed: int = 0,
    label: str = "",
    init_from: str = "",
    script: Path | str | None = None,
) -> list[str]:
    """The trainer's invocation, with its real flag names."""

    command = [
        str(python),
        str(script if script is not None else TRAINER_SCRIPT),
        str(bundle),
        "--out", str(out),
        "--iterations", str(int(iterations)),
        "--envs", str(int(envs)),
        "--seed", str(int(seed)),
    ]
    if label:
        command += ["--label", label]
    if init_from:
        command += ["--init-from", str(Path(init_from).expanduser())]
    return command


def run_trainer(
    command: Sequence[str], *, timeout: float = 0.0
) -> dict[str, Any]:
    """Run the trainer and return its receipt.

    Its stderr — the progress lines and the witness margin — passes straight
    through to ours, where progress belongs (``docs/CLI.md`` §2). Its stdout
    is one JSON object on the last line, and that object is the receipt:
    nothing here reads a number off a stream the trainer did not mean as
    data (ADR-093). A ``timeout`` of zero is no limit.
    """

    try:
        completed = subprocess.run(
            list(command),
            stdout=subprocess.PIPE,
            stderr=None,  # inherit ours: progress belongs on stderr
            text=True,
            timeout=timeout or None,
        )
    except OSError as exc:
        raise TrainError(f"could not run the trainer: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise TrainError(
            f"the trainer was stopped after {timeout:g}s (--timeout)."
        ) from exc
    if completed.returncode != 0:
        raise TrainError(
            f"the trainer exited {completed.returncode}; its stderr is above."
        )
    receipt = _last_json_line(completed.stdout)
    if receipt is None:
        raise TrainError("the trainer exited 0 but printed no receipt.")
    return receipt


def _last_json_line(stdout: str) -> dict[str, Any] | None:
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
