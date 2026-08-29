# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Resident preview worker: one NDJSON request loop that writes nothing.

The other end of :mod:`CadexWarmWorker`. Runs under the same
``FreeCADCmd --safe-mode`` and out of the same content-addressed bundle as
the per-run project worker, and answers ``mode: "preview"`` requests
(ADR-055) without spawning a process per answer — which is the entire point,
because what is left of a cold run's ~0.42 s is process spawn, FreeCAD's C++
init, ``--safe-mode``'s temporary-directory setup and the OCCT dylib load,
none of which Python can make cheaper.

**Stateless by contract.** It holds one generation — one
``(source, api_contracts, assets)`` — established by a ``load`` frame, plus
the definition fingerprints that generation's script produces at the stored
parameter values. Nothing else survives a request. That is what makes the
host's mitigations cheap: killing this process costs nothing but the next
spawn, so a generation change kills it, a deadline kills it, and a request
count respawns it.

**It never writes.** No result file, no staging, no store: the reply goes out
on the protocol fd and that is all. Every accepted byte still comes from a
cold run with a fresh attempt directory, which is what preserves digest
determinism and cross-revision isolation by construction.

Process discipline is deliberately the same shape as :mod:`cadexd`'s, for
the same reasons: fd 1 is dup()ed to a private protocol fd before FreeCAD
can print to it and then redirected to stderr, and stdin EOF is the lifetime
signal, so a dead host is a dead worker rather than an orphan.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from typing import Any

SCHEMA = "cadex-preview-worker-v1"

#: The directory ``mesh.import_file`` and ``part.shape_from_mesh`` resolve
#: assets against. Owned by the host, outside the project store, read-only in
#: practice — the worker never writes into it.
ROOT_ENV = "CADEX_PREVIEW_ROOT"


class _Generation:
    """The one script this worker is currently bound to."""

    def __init__(self, key: str, request: dict[str, Any]) -> None:
        self.key = key
        self.request = request
        self.baseline: dict[str, Any] | None = None


def _handle(
    frame: dict[str, Any], root: Any, generation: _Generation | None
) -> tuple[dict[str, Any], _Generation | None]:
    """Answer one frame; returns the reply and the generation to keep."""

    import cadex_project_worker

    op = str(frame.get("op") or "")
    if op == "load":
        key = str(frame.get("generation") or "")
        request = frame.get("request")
        if not key or not isinstance(request, dict):
            raise ValueError("A load frame needs a generation and a request.")
        request = dict(request)
        request["mode"] = "preview"
        request.pop("baseline", None)
        answer = cadex_project_worker._run_preview(request, root)
        generation = _Generation(key, request)
        generation.baseline = {
            "definitions_fingerprint": answer.get("definitions_fingerprint") or {}
        }
        return (
            {
                "ok": True,
                "generation": key,
                "definitions_fingerprint": generation.baseline[
                    "definitions_fingerprint"
                ],
            },
            generation,
        )

    if op == "preview":
        key = str(frame.get("generation") or "")
        if generation is None or generation.key != key:
            # The host is responsible for loading before previewing; saying so
            # rather than guessing is what keeps "no cross-revision leakage"
            # checkable instead of arguable.
            raise ValueError("This worker is not bound to that generation.")
        values = frame.get("param_values")
        if not isinstance(values, dict):
            raise ValueError("A preview frame needs param_values.")
        request = dict(generation.request)
        request["param_values"] = dict(values)
        request["baseline"] = generation.baseline
        return cadex_project_worker._run_preview(request, root), generation

    raise ValueError(f"Unsupported preview worker op: {op!r}.")


def main() -> int:
    module_root = os.path.dirname(os.path.abspath(__file__))
    if module_root not in sys.path:
        sys.path.insert(0, module_root)

    protocol_fd = os.dup(1)
    os.dup2(2, 1)
    protocol_out = os.fdopen(protocol_fd, "wb", buffering=0)

    def send(frame: dict[str, Any]) -> None:
        protocol_out.write(
            json.dumps(
                frame,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
                default=str,
            ).encode("utf-8")
            + b"\n"
        )

    from pathlib import Path

    root = Path(os.environ[ROOT_ENV]).resolve()
    send({"id": None, "event": {"event": "ready", "schema": SCHEMA, "pid": os.getpid()}})

    generation: _Generation | None = None
    for line in sys.stdin.buffer:  # EOF: the host died — self-exit.
        line = line.strip()
        if not line:
            continue
        request_id = None
        try:
            frame = json.loads(line.decode("utf-8"))
            if not isinstance(frame, dict):
                raise TypeError("A preview worker frame must be an object.")
            request_id = frame.get("id")
            reply, generation = _handle(frame, root, generation)
        except BaseException as exc:  # a bad frame must not kill the worker
            reply = {
                "ok": False,
                "exception_type": exc.__class__.__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(limit=20),
            }
        send({"id": request_id, **reply})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
