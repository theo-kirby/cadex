# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The resident preview worker, from cadexd's side (ADR-055).

One per open project, owned by :class:`CadexdServer`, **spawned lazily on the
first preview** so a session that never drags a slider never pays for it.

What makes a resident process acceptable here is that it cannot affect the
model: it never writes the project store, never publishes, never moves a
revision or a digest. It is a read-only oracle, and every byte the store ever
accepts still comes from a cold ``--safe-mode`` run with a fresh attempt
directory. Digest determinism, cross-revision isolation and crash recovery
are therefore preserved by construction rather than by argument.

**Generation binding** is what makes "no cross-revision leakage" checkable
rather than arguable. The worker is bound to one
``(source, api_contracts, assets)`` generation, established by a ``load``
frame; anything that can change any of the three invalidates it, and
invalidation is free because the worker is stateless by contract — the cost
of being wrong is one respawn.

**Bounds without a process per run**, each cheap for the same reason:

- a deadline, then ``SIGKILL``. A preview that slow has already failed its
  purpose; there is nothing to salvage and a debounced ``set_params`` is
  right behind it.
- a memory ceiling, sampled after a request rather than during it, so the
  common path pays nothing.
- a respawn every N requests, as a leak backstop that needs no leak detector.

``--safe-mode``, the closed environment allowlist, the AST source policy and
the settrace budget are all unchanged: this changes how often a worker
starts, not what a worker is allowed to do.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
from typing import Any, Mapping

#: A preview that has not answered by now has already failed its purpose:
#: the debounced ``set_params`` behind it is the real answer, and a drag
#: frame is worth ~33 ms.
PREVIEW_DEADLINE_SECONDS = 5.0

#: Leak backstop. Respawning costs one cold start on one preview out of this
#: many, which is invisible next to the drag it happens during.
MAX_REQUESTS_PER_WORKER = 200

#: Sampled every this many requests. `ps` is a subprocess; paying for it on
#: every preview would be paying a millisecond to protect against a leak that
#: takes minutes to matter.
MEMORY_SAMPLE_INTERVAL = 16

#: The worker holds one document and one memo, both bounded. Well above what
#: a preview needs and well below anything that threatens the host.
MEMORY_CEILING_BYTES = 3 * 1024 * 1024 * 1024

#: The staged entry module. A *name*, never an import: this module lives in
#: cadexd's import closure and the preview worker deliberately does not
#: (``cadex_tests/test_engine_purity_guardrails``), exactly like every other
#: domain worker.
ENTRY_MODULE = "cadex_preview_worker"


def generation_key(source: str, api_contracts: Mapping[str, Any], assets: Any) -> str:
    """Identity of one ``(source, api_contracts, assets)`` generation."""

    material = json.dumps(
        {
            "source": str(source),
            "api_contracts": api_contracts,
            "assets": assets,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:24]


def assets_fingerprint(project_root: Path) -> list[list[Any]]:
    """``[[name, size, mtime_ns], ...]`` for the project's mesh assets.

    Belt and braces: ``put_asset`` invalidates the generation explicitly, so
    this exists to catch a route that forgets to. Cheap enough to compute per
    preview — the asset budget is 64 files.
    """

    directory = Path(project_root) / "assets"
    if not directory.is_dir():
        return []
    fingerprint: list[list[Any]] = []
    for path in sorted(directory.iterdir()):
        if path.is_symlink() or not path.is_file():
            continue
        stat = path.stat()
        fingerprint.append([path.name, stat.st_size, stat.st_mtime_ns])
    return fingerprint


class CadexWarmWorker:
    """A resident ``FreeCADCmd`` that answers previews and owns nothing else."""

    def __init__(self, project_root: Path) -> None:
        self._project_root = Path(project_root)
        self._process: subprocess.Popen | None = None
        self._replies: queue.SimpleQueue = queue.SimpleQueue()
        self._staging: Path | None = None
        self._generation: str | None = None
        self._requests = 0
        self._sequence = 0

    # -- lifetime --------------------------------------------------------

    def invalidate(self) -> None:
        """Drop the bound generation. Free: the worker is stateless.

        Called by every handler that can change the source, the parameters,
        the assets or the project. Implemented as a kill rather than a
        rebind because a killed worker cannot answer with the previous
        generation's geometry, and "cannot" is the only guarantee worth
        having here.
        """

        self.close()

    def close(self) -> None:
        process, self._process = self._process, None
        self._generation = None
        self._requests = 0
        if process is not None and process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        for stream in (
            getattr(process, "stdin", None),
            getattr(process, "stdout", None),
        ):
            try:
                stream.close()
            except Exception:
                pass
        staging, self._staging = self._staging, None
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)

    # -- the one public operation ---------------------------------------

    def preview(
        self, prepared: Mapping[str, Any], param_values: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Answer one parameter change, spawning and loading if needed.

        Returns the worker's reply, or a ``previewable: False`` refusal with
        a reason. A preview never raises at the caller: it is an
        optimisation, and the debounced accepting path behind it is the real
        answer.
        """

        generation = str(prepared["generation"])
        try:
            if self._process is None or self._process.poll() is not None:
                self._spawn(prepared)
            if self._generation != generation:
                loaded = self._exchange(
                    {
                        "op": "load",
                        "generation": generation,
                        "request": prepared["request"],
                    }
                )
                if loaded.get("ok") is not True:
                    return _declined(
                        f"the preview worker could not load this script: "
                        f"{loaded.get('error') or 'unknown error'}"
                    )
                self._generation = generation
            answer = self._exchange(
                {
                    "op": "preview",
                    "generation": generation,
                    "param_values": dict(param_values),
                }
            )
        except _WorkerFailure as exc:
            self.close()
            return _declined(str(exc))
        finally:
            self._enforce_bounds()
        if answer.get("ok") is not True:
            return _declined(str(answer.get("error") or "the preview failed"))
        return answer

    # -- internals -------------------------------------------------------

    def _spawn(self, prepared: Mapping[str, Any]) -> None:
        from CadexScriptedRuntime import stage_preview_assets, worker_environment

        self.close()
        staging = Path(tempfile.mkdtemp(prefix="cadex-preview-"))
        self._staging = staging
        stage_preview_assets(self._project_root, staging)
        bundle = str(prepared["bundle_dir"])
        code = (
            "import os,sys;"
            "sys.path.insert(0,os.getcwd());"
            f"sys.path.insert(0,{bundle!r});"
            f"import {ENTRY_MODULE} as _w;"
            "raise SystemExit(_w.main())"
        )
        environment = worker_environment(staging)
        environment["CADEX_PREVIEW_ROOT"] = str(staging)
        try:
            process = subprocess.Popen(
                [
                    str(prepared["freecadcmd_executable"]),
                    "--safe-mode",
                    "-c",
                    code,
                ],
                cwd=str(staging),
                env=environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise _WorkerFailure(f"the preview worker could not start: {exc}") from exc
        self._process = process
        self._replies = queue.SimpleQueue()
        threading.Thread(
            target=self._reader,
            args=(process, self._replies),
            name="cadex-preview-reader",
            daemon=True,
        ).start()
        ready = self._receive()
        if str(ready.get("event", {}).get("event") or "") != "ready":
            raise _WorkerFailure("the preview worker did not announce itself.")

    @staticmethod
    def _reader(process: subprocess.Popen, replies: queue.SimpleQueue) -> None:
        try:
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    frame = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, ValueError):
                    continue  # pre-hijack FreeCADCmd chatter
                if isinstance(frame, dict):
                    replies.put(frame)
        except (OSError, ValueError):
            pass
        finally:
            replies.put(None)  # the worker died: unblock whoever is waiting

    def _exchange(self, frame: dict[str, Any]) -> dict[str, Any]:
        process = self._process
        if process is None or process.poll() is not None:
            raise _WorkerFailure("the preview worker is not running.")
        self._sequence += 1
        self._requests += 1
        payload = dict(frame, id=f"p{self._sequence}")
        try:
            process.stdin.write(
                json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
            )
            process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise _WorkerFailure(f"the preview worker closed its input: {exc}") from exc
        return self._receive()

    def _receive(self) -> dict[str, Any]:
        try:
            frame = self._replies.get(timeout=PREVIEW_DEADLINE_SECONDS)
        except queue.Empty:
            raise _WorkerFailure(
                f"the preview worker did not answer within "
                f"{PREVIEW_DEADLINE_SECONDS:g} seconds."
            ) from None
        if frame is None:
            raise _WorkerFailure("the preview worker exited.")
        return frame

    def _enforce_bounds(self) -> None:
        """Respawn on a request count or a memory ceiling. Sampled, not live."""

        process = self._process
        if process is None:
            return
        if self._requests >= MAX_REQUESTS_PER_WORKER:
            self.close()
            return
        if self._requests % MEMORY_SAMPLE_INTERVAL:
            return
        from CadexScriptedProcess import process_memory_bytes

        observed = process_memory_bytes(process.pid)
        if observed is not None and observed > MEMORY_CEILING_BYTES:
            self.close()


class _WorkerFailure(RuntimeError):
    """The worker is unusable. Always ends in a kill and a declined preview."""


def _declined(reason: str) -> dict[str, Any]:
    return {"ok": True, "previewable": False, "placements": {}, "reason": reason}
