# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Each checkpoint, rolled out while the run is still training (ADR-544).

A checkpoint is a complete policy the trainer leaves in its output directory
every ``--checkpoint-every`` iterations, as ``<out>.<tag>.cxpolicy``. This
module is the one watcher both training paths share -- the registered run's
supervisor (:func:`loop.supervise`) and ``cadex train``'s local trainer, which
is ``cadex walk``'s train leg -- and it turns each new numbered checkpoint
into a ``cadex-assembly-simulation-trace-v1`` trace beside it, through the
engine, on the CPU, while the trainer goes on using the GPU.

The rules it keeps:

* **It never stops or slows the run it watches.** :meth:`poll` does not
  block: it reaps a finished child, starts the next one and returns. The
  child runs one at a time under ``nice``, with the GPU hidden. A watcher
  that raises is switched off with its reason, never propagated.
* **A checkpoint is a file on disk**, whoever wrote it. Only numbered tags
  are rolled out; ``best`` is rewritten in place under a new digest and the
  final policy is the run's own, evaluated by ``cadex evaluate``.
* **The checkpoint is named by what the trainer said of it.** Its iteration
  and reward per step come from the progress row whose digest is the file's;
  a checkpoint the progress does not list yet waits for the next poll, until
  the trainer has ended, when the tag alone names its iteration and the
  reward is left unmeasured rather than borrowed.
* **Newest first.** The page loops the newest checkpoint, so a watcher that
  fell behind rolls out the newest pending one next and the older ones after.
* **A failure is a record.** ``<out>.<tag>.rollout-failed.json`` says why;
  a trace is never partial and never written beside a failure.

The traces end in ``-trace.json``, which a project's own repository ignores:
they are run outputs, never committed.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any, Mapping

#: The child, run by path under the engine's interpreter.
RUNNER_SCRIPT = Path(__file__).resolve().with_name("checkpoint_runner.py")
TRACE_SUFFIX = ".rollout-trace.json"
FAILURE_SUFFIX = ".rollout-failed.json"
FAILURE_SCHEMA = "cadex-checkpoint-rollout-failure-v1"
PROGRESS_NAME = "progress.json"
#: A bound on one child that hung, not a budget: a biped's nominal episode
#: takes well under a second.
ROLLOUT_TIMEOUT_S = 300.0
#: How often the directory is listed; the trainer's own poll is faster.
SCAN_S = 2.0
#: The child's niceness: the trainer is the job, the rollout is the view.
NICENESS = 10
_NUMBERED = re.compile(r"\d+")


def rollout_paths(checkpoint: Path) -> tuple[Path, Path]:
    """``walk.000040.cxpolicy`` -> its trace and its failure record."""

    stem = checkpoint.name[:-len(".cxpolicy")] if checkpoint.name.endswith(".cxpolicy") \
        else checkpoint.name
    return (checkpoint.with_name(stem + TRACE_SUFFIX),
            checkpoint.with_name(stem + FAILURE_SUFFIX))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_atomically(path: Path, payload: Mapping[str, Any]) -> None:
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, path)


def _quiet_child() -> None:  # pragma: no cover - runs in the child
    os.nice(NICENESS)


class CheckpointRollouts:
    """Watch ``train_dir`` for ``<output>.<tag>.cxpolicy`` and roll each out."""

    def __init__(self, train_dir: Path | str, *, output: str, bundle: Path | str,
                 model: Path | str, python: Path | str, module_dir: Path | str,
                 timeout_s: float = ROLLOUT_TIMEOUT_S, scan_s: float = SCAN_S) -> None:
        self.train_dir = Path(train_dir)
        self.output = str(output)
        self.bundle = Path(bundle)
        self.model = Path(model)
        self.python = Path(python)
        self.module_dir = Path(module_dir)
        self.timeout_s = float(timeout_s)
        self.scan_s = float(scan_s)
        self.error = ""
        self.written: list[str] = []
        self.failed: list[str] = []
        self._scratch = Path(tempfile.mkdtemp(prefix="cadex-checkpoint-"))
        self._child: tuple[subprocess.Popen[bytes], Path, float, Any] | None = None
        self._scanned = float("-inf")

    # -- what is waiting -------------------------------------------------------

    def pending(self, *, final: bool = False) -> list[dict[str, Any]]:
        """The numbered checkpoints with neither a trace nor a failure, newest
        first, each with what the progress recorded of it."""

        listed = _read_json(self.train_dir / PROGRESS_NAME).get("checkpoints") or []
        prefix = self.output + "."
        running = self._child[1] if self._child else None
        rows = []
        for path in self.train_dir.glob("*.cxpolicy"):
            tag = path.name[len(prefix):-len(".cxpolicy")] if path.name.startswith(prefix) else ""
            if not _NUMBERED.fullmatch(tag) or path == running:
                continue
            trace, failure = rollout_paths(path)
            if trace.exists() or failure.exists():
                continue
            sha = _sha256(path)
            row = next((item for item in reversed(listed) if isinstance(item, Mapping)
                        and str(item.get("path")) == path.name and item.get("sha256") == sha),
                       None)
            if row is None and not final:
                continue  # the trainer has not said what this one is yet
            rows.append({
                "checkpoint": path, "tag": tag, "sha256": sha,
                "iteration": int(row["iteration"]) if row else int(tag) - 1,
                "reward_per_step": row.get("reward_per_step") if row else None,
            })
        rows.sort(key=lambda row: int(row["tag"]), reverse=True)
        return rows

    # -- the child -------------------------------------------------------------

    def _start(self, row: Mapping[str, Any]) -> None:
        checkpoint = Path(row["checkpoint"])
        trace, failure = rollout_paths(checkpoint)
        plan = self._scratch / f"{checkpoint.name}.plan.json"
        plan.write_text(json.dumps({
            "module_dir": str(self.module_dir), "model": str(self.model),
            "task": str(self.bundle), "checkpoint": str(checkpoint), "tag": row["tag"],
            "iteration": row["iteration"], "reward_per_step": row["reward_per_step"],
            "trace": str(trace), "failure": str(failure),
        }), encoding="utf-8")
        environment = dict(os.environ, CUDA_VISIBLE_DEVICES="", JAX_PLATFORMS="cpu")
        stderr = open(self._scratch / f"{checkpoint.name}.stderr", "wb")
        try:
            process = subprocess.Popen(
                [str(self.python), str(RUNNER_SCRIPT), str(plan)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=stderr,
                env=environment, preexec_fn=_quiet_child)
        except OSError as exc:
            stderr.close()
            self._fail(row, "child_not_started", f"could not run the rollout: {exc}")
            return
        self._child = (process, checkpoint, time.monotonic(), (row, stderr))

    def _fail(self, row: Mapping[str, Any], reason: str, error: str) -> None:
        checkpoint = Path(row["checkpoint"])
        _write_atomically(rollout_paths(checkpoint)[1], {
            "schema": FAILURE_SCHEMA, "checkpoint": checkpoint.name, "tag": row["tag"],
            "iteration": row["iteration"], "reason": reason, "error": error})
        self.failed.append(checkpoint.name)

    def _reap(self, *, block: bool) -> None:
        if self._child is None:
            return
        process, checkpoint, started, (row, stderr) = self._child
        remaining = self.timeout_s - (time.monotonic() - started)
        try:
            process.wait(timeout=max(remaining, 0.0) if block else 0.0)
        except subprocess.TimeoutExpired:
            if not block and remaining > 0:
                return
            remaining = 0.0
            process.kill()
            process.wait()
        stderr.close()
        self._child = None
        trace, failure = rollout_paths(checkpoint)
        if process.returncode == 0 and trace.is_file():
            self.written.append(checkpoint.name)
            return
        if failure.is_file():
            self.failed.append(checkpoint.name)
            return
        if remaining <= 0:
            self._fail(row, "rollout_timeout",
                       f"the rollout ran past its bound of {self.timeout_s:g} s and was killed.")
            return
        tail = [line for line in Path(stderr.name).read_text(
            encoding="utf-8", errors="replace").splitlines() if line.strip()][-3:]
        self._fail(row, "child_failed", f"the rollout exited {process.returncode}"
                   + (": " + " | ".join(tail) if tail else "."))

    # -- the two entry points -------------------------------------------------

    def poll(self) -> None:
        """Reap, then start the newest pending rollout. Never blocks, never raises."""

        if self.error:
            return
        try:
            self._reap(block=False)
            if self._child is None and time.monotonic() - self._scanned >= self.scan_s:
                self._scanned = time.monotonic()
                waiting = self.pending()
                if waiting:
                    self._start(waiting[0])
        except Exception as exc:  # noqa: BLE001 - the view never breaks the run
            self.error = f"checkpoint rollouts stopped: {exc.__class__.__name__}: {exc}"

    def drain(self, *, finish: bool = True) -> None:
        """After the trainer: finish every pending rollout, then clean up.
        ``finish=False`` -- an interrupted supervisor -- only stops the child."""

        try:
            while finish and not self.error:
                self._reap(block=True)
                waiting = self.pending(final=True)
                if not waiting:
                    break
                self._start(waiting[0])
        except Exception as exc:  # noqa: BLE001 - the run already ended; say why
            self.error = f"checkpoint rollouts stopped: {exc.__class__.__name__}: {exc}"
        finally:
            if self._child is not None:
                self._child[0].kill()
                self._child[0].wait()
                self._child[3][1].close()
                self._child = None
            shutil.rmtree(self._scratch, ignore_errors=True)

    def summary(self) -> dict[str, Any]:
        return {"written": len(self.written), "failed": len(self.failed),
                **({"error": self.error} if self.error else {})}
