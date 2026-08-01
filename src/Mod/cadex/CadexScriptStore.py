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
SCRIPT_HISTORY_DIR_NAME = "script_history"
SCRIPT_HISTORY_INDEX_NAME = "history.json"

#: Accepted revisions kept in ``script_history/``. Each entry is the script
#: text and a line of metadata — single-digit kilobytes — so this bound is
#: about keeping the directory readable, not about disk (ADR-045).
HISTORY_LIMIT = 25

#: Attempt staging directories kept per project, beyond the accepted one.
#: An attempt is ~2 MB (it stages the whole worker bundle next to the run's
#: BREP), it exists to run one script, and nothing reads a stale one — but
#: the most recent few are what a post-mortem needs, so they are not free to
#: delete on sight either.
ATTEMPT_KEEP = 3


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
    - ``script.json`` — parameter spec cache + values, connection spec cache
      + stored rows, working/accepted revision, accepted contract (recorded
      output list), accepted digest, and the latest candidate summary.
    - ``script_artifacts/<revision>/`` — per-revision staged artifacts,
      pruned to the accepted attempt plus :data:`ATTEMPT_KEEP` (ADR-045).
    - ``script_history/`` — the last :data:`HISTORY_LIMIT` accepted sources
      as plain ``.py`` files, plus ``history.json`` indexing them. This is
      the undo trail: text only, no BREP, no worker bundle.

    Pre-release v2 per-domain program stores are not migrated: conversations
    are preserved by their own store, scripts start empty (ADR-011).
    """

    def __init__(self, project_root: str | Path) -> None:
        self.root = Path(str(project_root))
        self.script_path = self.root / SCRIPT_FILE_NAME
        self.state_path = self.root / SCRIPT_STATE_FILE_NAME
        self.artifacts_root = self.root / SCRIPT_ARTIFACTS_DIR_NAME
        self.history_root = self.root / SCRIPT_HISTORY_DIR_NAME
        self.history_index_path = self.history_root / SCRIPT_HISTORY_INDEX_NAME

    @staticmethod
    def default_state() -> dict[str, Any]:
        return {
            "schema": SCRIPT_STATE_SCHEMA,
            "param_specs": [],
            "param_values": {},
            # The connection table's declaration cache and its stored
            # overrides (ADR-065), beside the parameter pair and read the
            # same way. ``read_state`` merges over these defaults and keeps
            # only known keys, so a script.json written before ADR-065 loads
            # unchanged with no nets and needs no migration.
            "net_specs": {},
            "net_values": [],
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

    def read_accepted_source(self) -> str:
        """The source of the accepted revision, or ``""`` if there is none.

        ``script.py`` is the working source and stays the project's source of
        truth. This is the last source that provably reproduced
        ``accepted_digest``, kept in that revision's pinned staging directory
        (``accepted_attempt``, which no GC removes). It is the restore pass's
        fallback for the one case where the working source cannot be run at
        all — a store left broken by something other than the user (ADR-044).
        """

        attempt = self.read_state().get("accepted_attempt")
        if not isinstance(attempt, dict):
            return ""
        staging = str(attempt.get("staging") or "")
        if not staging:
            return ""
        request = self.root / staging / "request.json"
        try:
            payload = json.loads(request.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ""
        source = payload.get("source") if isinstance(payload, dict) else None
        return str(source or "")

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

    # -- history: the undo trail (ADR-045) ---------------------------------

    def read_history(self) -> list[dict[str, Any]]:
        """Accepted revisions, oldest first. Never raises on a bad index."""

        try:
            data = json.loads(self.history_index_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        entries = data.get("entries") if isinstance(data, dict) else None
        return [dict(item) for item in entries or [] if isinstance(item, dict)]

    def read_history_source(self, selector: str | int) -> str:
        """One historical source, by ordinal (``3``, ``"3"``) or revision.

        A revision may be given by any unique prefix, which is what makes the
        12-character revisions people actually read out of a listing usable.
        Returns ``""`` when nothing matches.
        """

        entries = self.read_history()
        want = str(selector).strip().lower()
        if not want:
            return ""
        matched = [e for e in entries if str(e.get("ordinal")) == want]
        if not matched:
            matched = [e for e in entries
                       if str(e.get("revision") or "").startswith(want)]
        if len(matched) != 1:
            return ""
        path = self.history_root / str(matched[0].get("file") or "")
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def record_history(
        self, revision: str, source: str, contract: Any = None
    ) -> dict[str, Any] | None:
        """Append one accepted revision to the history; prune to the limit.

        Called only on acceptance, so the trail is entirely of scripts that
        ran and published — which is what makes reverting to any of them
        safe. A repeat of the revision already at the tip is not recorded:
        re-opening a project re-runs its accepted script, and an undo trail
        that fills with identical entries is not one.
        """

        revision = str(revision or "")
        source = str(source or "")
        if not revision or not source.strip():
            return None
        entries = self.read_history()
        if entries and str(entries[-1].get("revision") or "") == revision:
            return dict(entries[-1])

        ordinal = int(entries[-1].get("ordinal") or 0) + 1 if entries else 1
        name = "{:04d}-{:s}.py".format(ordinal, revision[:12])
        atomic_write_bytes(self.history_root / name, source.encode("utf-8"))
        entry = {
            "ordinal": ordinal,
            "revision": revision,
            "file": name,
            "saved_at": now_iso(),
            "characters": len(source),
            "outputs": sorted(
                str(item.get("name"))
                for item in (contract or [])
                if isinstance(item, dict) and item.get("name")
            ),
        }
        entries.append(entry)

        for stale in entries[:-HISTORY_LIMIT]:
            try:
                (self.history_root / str(stale.get("file") or "")).unlink()
            except OSError:
                pass
        entries = entries[-HISTORY_LIMIT:]
        atomic_write_json(
            self.history_index_path,
            {"schema": SCRIPT_STATE_SCHEMA, "entries": entries},
        )
        return entry

    def prune_artifacts(self, keep_recent: int = ATTEMPT_KEEP) -> list[str]:
        """Drop stale attempt directories; return what was removed.

        An attempt directory stages the whole worker bundle beside the run's
        BREP — about 2 MB — and nothing reads one once the run is over. The
        accepted attempt is pinned (``inspect scope=output`` reads it), the
        most recent few stay for post-mortems, and the rest are the reason a
        single afternoon's project reached 56 MB (ADR-045).
        """

        import shutil

        pinned = self.read_state().get("accepted_attempt")
        pinned_dir = None
        if isinstance(pinned, dict) and pinned.get("staging"):
            pinned_dir = (self.root / str(pinned["staging"])).resolve()

        attempts = []
        if self.artifacts_root.is_dir():
            for revision_dir in self.artifacts_root.iterdir():
                if not revision_dir.is_dir():
                    continue
                for attempt in revision_dir.iterdir():
                    if attempt.is_dir() and attempt.name.startswith("attempt-"):
                        attempts.append(attempt)
        # Attempt ids lead with a zero-padded millisecond stamp, so the name
        # sorts chronologically without stat()ing anything.
        attempts.sort(key=lambda path: path.name)

        removed: list[str] = []
        for attempt in attempts[:-keep_recent] if keep_recent else attempts:
            if pinned_dir is not None and attempt.resolve() == pinned_dir:
                continue
            shutil.rmtree(attempt, ignore_errors=True)
            removed.append(attempt.name)
            parent = attempt.parent
            try:
                if parent.is_dir() and not any(parent.iterdir()):
                    parent.rmdir()
            except OSError:
                pass
        return removed
