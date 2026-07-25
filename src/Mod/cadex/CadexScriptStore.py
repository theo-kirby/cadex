# SPDX-License-Identifier: LGPL-2.1-or-later

"""Durable store for THE project script (schema ``cadex-project-script-v1``).

Split out of ``CadexProject`` in Phase 7 (ADR-021). ``CadexProject`` is two
stores wearing one module: this one — the script, its parameters and its
acceptance state, which every engine path touches — and the conversation
store, which is Qt shell state and dies with the shell (conversation
history moves into the ``.blend``, ADR-020). Separating them lets the
engine's transitive closure stop at the script store.

Nothing here imports FreeCAD, so the store is exercised by the stubbed
pytest suite exactly as it runs in a worker.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import time
from typing import Any

SCRIPT_STATE_SCHEMA = "cadex-project-script-v1"
SCRIPT_FILE_NAME = "script.py"
SCRIPT_STATE_FILE_NAME = "script.json"
SCRIPT_ARTIFACTS_DIR_NAME = "script_artifacts"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_bytes(content)
    tmp.replace(path)


class CadexProjectScriptStore:
    """Durable store for THE project script and its parameter/acceptance state.

    Layout under one project root (schema ``cadex-project-script-v1``):

    - ``script.py`` — the single project script, the sole source of truth.
    - ``script.json`` — parameter spec cache + values, working/accepted
      revision, accepted contract (recorded output list), accepted digest,
      and the latest candidate summary.
    - ``script_artifacts/<revision>/`` — per-revision staged artifacts.

    Pre-release v2 per-domain program stores are not migrated: conversations
    are preserved by their own store, scripts start empty (ADR-011).
    """

    def __init__(self, project_root: str | Path) -> None:
        self.root = Path(str(project_root))
        self.script_path = self.root / SCRIPT_FILE_NAME
        self.state_path = self.root / SCRIPT_STATE_FILE_NAME
        self.artifacts_root = self.root / SCRIPT_ARTIFACTS_DIR_NAME

    @staticmethod
    def default_state() -> dict[str, Any]:
        return {
            "schema": SCRIPT_STATE_SCHEMA,
            "param_specs": [],
            "param_values": {},
            "working_revision": "",
            "accepted_revision": "",
            "accepted_contract": None,
            "accepted_digest": "",
            # Locator for the accepted revision's staged artifacts (BREP +
            # worker report). The accepted attempt directory is pinned: no GC
            # removes it while it is referenced here (Phase 5.2).
            "accepted_attempt": None,
            "latest_candidate": None,
            "updated_at": "",
        }

    def read_source(self) -> str:
        if not self.script_path.is_file():
            return ""
        return self.script_path.read_text(encoding="utf-8")

    def read_state(self) -> dict[str, Any]:
        default = self.default_state()
        if not self.state_path.is_file():
            return default
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError(
                f"Project script state could not be read from {self.state_path}: {exc}"
            ) from exc
        if not isinstance(data, dict) or data.get("schema") != SCRIPT_STATE_SCHEMA:
            raise RuntimeError(
                f"Project script state at {self.state_path} has an invalid schema."
            )
        merged = dict(default)
        merged.update({key: data[key] for key in default if key in data})
        merged["schema"] = SCRIPT_STATE_SCHEMA
        return merged

    def write(
        self,
        *,
        source: str | None = None,
        state_updates: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Atomically persist the script source and/or state updates."""

        self.root.mkdir(parents=True, exist_ok=True)
        if source is not None:
            atomic_write_bytes(self.script_path, str(source).encode("utf-8"))
        state = self.read_state()
        for key, value in dict(state_updates or {}).items():
            if key not in state or key == "schema":
                raise ValueError(f"Unknown project script state field {key!r}.")
            state[key] = value
        state["updated_at"] = now_iso()
        atomic_write_json(self.state_path, state)
        return state

    def artifacts_dir(self, revision: str) -> Path:
        clean = str(revision or "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{8,64}", clean):
            raise ValueError("An artifacts directory needs a hexadecimal revision.")
        return self.artifacts_root / clean
