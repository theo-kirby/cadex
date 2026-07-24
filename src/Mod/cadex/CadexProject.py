# SPDX-License-Identifier: LGPL-2.1-or-later

"""Project persistence for Cadex.

Stores a small durable manifest per CAD project (title, summary, document
scope) plus a sqlite index of known projects. Deliberately contains no
workflow state: tool availability is driven by the active workbench pack,
not by project lifecycle gates.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from typing import Any
import uuid



PROJECT_SCHEMA = "cadex-project-v2"
SCRIPT_STATE_SCHEMA = "cadex-project-script-v1"
SCRIPT_FILE_NAME = "script.py"
SCRIPT_STATE_FILE_NAME = "script.json"
SCRIPT_ARTIFACTS_DIR_NAME = "script_artifacts"
CONVERSATIONS_DIR_NAME = "conversations"
CONVERSATION_INDEX_NAME = "index.json"
LEGACY_CONVERSATION_NAME = "conversation.json"
CONVERSATION_INDEX_SCHEMA = "cadex-conversation-index-v1"
CONVERSATION_THREAD_SCHEMA = "cadex-conversation-thread-v1"
DEFAULT_CONVERSATION_TITLE = "New conversation"
MODELING_ENGINES = frozenset({"xscript"})
DEFAULT_MODELING_ENGINE = "xscript"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def slugify(value: str, default: str = "cadex-project") -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip()).strip("._")
    return slug[:80] or default


def _freecad_user_appdata() -> Path | None:
    """FreeCAD's per-user application data dir, or None outside FreeCAD."""
    try:
        import FreeCAD as App
    except ImportError:
        return None
    raw = str(App.getUserAppDataDir() or "").strip()
    if not raw:
        raise RuntimeError("FreeCAD did not provide a user application data directory.")
    return Path(raw).expanduser()


def _platform_data_dir() -> Path:
    """Platform-appropriate per-user data dir without FreeCAD."""
    if os.name == "nt":
        appdata = str(os.environ.get("APPDATA") or "").strip()
        if appdata:
            return Path(appdata) / "Cadex"
        return Path.home() / "AppData" / "Roaming" / "Cadex"
    xdg = str(os.environ.get("XDG_DATA_HOME") or "").strip()
    if xdg:
        return Path(xdg).expanduser() / "cadex"
    return Path.home() / ".local" / "share" / "cadex"


def cadex_data_dir() -> Path:
    """Central Cadex data directory.

    Resolution order:
    1. ``CADEX_HOME`` environment override (tests, power users).
    2. FreeCAD's user appdata dir + ``Cadex`` when FreeCAD is importable
       (``~/.local/share/FreeCAD/Cadex`` on Linux,
       ``%APPDATA%/FreeCAD/Cadex`` on Windows).
    3. Platform default without FreeCAD (``$XDG_DATA_HOME/cadex`` or
       ``~/.local/share/cadex`` on Linux, ``%APPDATA%/Cadex`` on Windows).
    """
    configured = str(os.environ.get("CADEX_HOME") or "").strip()
    if configured:
        return Path(configured).expanduser()
    appdata = _freecad_user_appdata()
    if appdata is not None:
        return appdata / "Cadex"
    return _platform_data_dir()


def _default_index_path() -> Path:
    return cadex_data_dir() / "index.sqlite"


def _active_document_info() -> dict[str, Any]:
    try:
        import FreeCAD as App
    except Exception:
        return {"document": None, "label": None, "file_path": None, "saved": False}

    doc = getattr(App, "ActiveDocument", None)
    if doc is None:
        return {"document": None, "label": None, "file_path": None, "saved": False}
    file_path = str(getattr(doc, "FileName", "") or "")
    return {
        "document": str(getattr(doc, "Name", "") or ""),
        "label": str(getattr(doc, "Label", "") or getattr(doc, "Name", "") or ""),
        "file_path": file_path or None,
        "saved": bool(file_path),
    }


def _project_id_for_scope(scope: dict[str, Any], session_id: str) -> str:
    file_path = scope.get("file_path")
    source = (
        str(Path(str(file_path)).expanduser().resolve()) if file_path else session_id
    )
    return hashlib.sha1(source.encode("utf-8")).hexdigest()[:16]


def project_root_for_document_file(file_path: str | Path) -> Path:
    """Per-document project folder for a saved CAD file.

    Matches ``CadexProjectStore.project_scope()`` for saved documents so all
    document artifacts (manifest, conversation, design document, screenshots,
    references) share one folder under the central data dir.
    """
    cad_path = Path(str(file_path)).expanduser()
    source = str(cad_path.resolve())
    project_id = hashlib.sha1(source.encode("utf-8")).hexdigest()[:16]
    folder_name = f"{slugify(cad_path.stem)}-{project_id[:8]}"
    return cadex_data_dir() / "projects" / folder_name


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_bytes(content)
    tmp.replace(path)


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(
            f"Cadex {label} could not be read from {path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"Cadex {label} at {path} is not a JSON object.")
    return data


def _clean_conversation_turns(
    conversation: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in conversation:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if role not in {"user", "assistant", "system"} or not content:
            continue
        turn = dict(item)
        turn["role"] = role
        turn["content"] = content
        cleaned.append(turn)
    return cleaned


def _validated_conversation_turns(
    conversation: list[Any],
    *,
    source: str,
    conversation_id: str | None = None,
) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    seen_turn_ids: set[str] = set()
    namespace = uuid.UUID(hex=conversation_id) if conversation_id else None
    for index, item in enumerate(conversation):
        if not isinstance(item, dict):
            raise RuntimeError(
                f"Cadex conversation {source} turn {index} is not a JSON object."
            )
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant", "system"}:
            raise RuntimeError(
                f"Cadex conversation {source} turn {index} has invalid role {role!r}."
            )
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                f"Cadex conversation {source} turn {index} has no text content."
            )
        turn = dict(item)
        # Legacy files could retain complete tool arguments/results on an
        # assistant turn. Strip them during validation so the next atomic
        # thread write migrates the conversation to text-only history.
        turn.pop("tool_trace", None)
        turn["content"] = content.strip()
        sequence = int(turn.get("sequence") or index + 1)
        if sequence != index + 1:
            raise RuntimeError(
                f"Cadex conversation {source} turn {index} has sequence {sequence}; "
                f"expected {index + 1}."
            )
        turn_id = str(turn.get("turn_id") or "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{32}", turn_id):
            if namespace is None:
                raise RuntimeError(
                    f"Cadex conversation {source} turn {index} has no stable id."
                )
            seed = "\x1f".join(
                (
                    str(sequence),
                    str(role),
                    str(turn.get("timestamp") or ""),
                    content.strip(),
                )
            )
            turn_id = uuid.uuid5(namespace, seed).hex
        if turn_id in seen_turn_ids:
            raise RuntimeError(
                f"Cadex conversation {source} contains duplicate turn id {turn_id}."
            )
        seen_turn_ids.add(turn_id)
        turn["turn_id"] = turn_id
        turn["sequence"] = sequence
        validated.append(turn)
    return validated


def _conversation_title(conversation: list[dict[str, Any]]) -> str:
    for item in conversation:
        if item.get("role") != "user":
            continue
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        first_line = next(
            (line.strip() for line in content.splitlines() if line.strip()),
            content,
        )
        compact = re.sub(r"\s+", " ", first_line).strip()
        if len(compact) <= 72:
            return compact
        return compact[:69].rstrip() + "..."
    return DEFAULT_CONVERSATION_TITLE


def _conversation_id(value: Any) -> str:
    clean = str(value or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{32}", clean):
        raise RuntimeError(f"Invalid Cadex conversation id: {value!r}.")
    return clean


class CadexConversationStore:
    """Durable conversation threads scoped to one Cadex project root."""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.directory = self.project_root / CONVERSATIONS_DIR_NAME
        self.index_path = self.directory / CONVERSATION_INDEX_NAME
        self.legacy_path = self.project_root / LEGACY_CONVERSATION_NAME

    def thread_path(self, conversation_id: str) -> Path:
        return self.directory / f"{_conversation_id(conversation_id)}.json"

    def catalog(self) -> dict[str, Any]:
        index = self._ensure_index()
        conversations = [dict(item) for item in index["conversations"]]
        conversations.sort(
            key=lambda item: str(
                item.get("last_opened_at") or item.get("updated_at") or ""
            ),
            reverse=True,
        )
        return {
            "path": str(self.index_path),
            "store_path": str(self.directory),
            "active_conversation_id": index["active_conversation_id"],
            "conversation_count": len(conversations),
            "conversations": conversations,
        }

    def active_history(self) -> dict[str, Any]:
        index = self._ensure_index()
        return self._history(index["active_conversation_id"], index=index)

    def all_histories(self) -> list[dict[str, Any]]:
        index = self._ensure_index()
        return [
            self._history(str(item["id"]), index=index)
            for item in index["conversations"]
        ]

    def history(self, conversation_id: str) -> dict[str, Any]:
        index = self._ensure_index()
        return self._history(_conversation_id(conversation_id), index=index)

    def create_conversation(self) -> dict[str, Any]:
        index = self._ensure_index()
        current = self._history(index["active_conversation_id"], index=index)
        if not current["conversation"]:
            return {"created": False, **current, "catalog": self.catalog()}

        timestamp = now_iso()
        conversation_id = uuid.uuid4().hex
        thread = self._new_thread(conversation_id, [], timestamp=timestamp)
        self._write_thread_payload(thread)
        index["active_conversation_id"] = conversation_id
        index["conversations"].append(self._thread_metadata(thread, timestamp))
        self._write_index(index)
        return {
            "created": True,
            **self._history(conversation_id, index=index),
            "catalog": self.catalog(),
        }

    def activate_conversation(self, conversation_id: str) -> dict[str, Any]:
        clean_id = _conversation_id(conversation_id)
        index = self._ensure_index()
        metadata = self._metadata_for(index, clean_id)
        timestamp = now_iso()
        index["active_conversation_id"] = clean_id
        metadata["last_opened_at"] = timestamp
        self._write_index(index)
        return {
            "activated": True,
            **self._history(clean_id, index=index),
            "catalog": self.catalog(),
        }

    def write_conversation(
        self,
        conversation_id: str,
        conversation: list[dict[str, Any]],
    ) -> dict[str, Any]:
        clean_id = _conversation_id(conversation_id)
        index = self._ensure_index()
        metadata = self._metadata_for(index, clean_id)
        existing = self._read_thread(clean_id)
        cleaned = _validated_conversation_turns(
            conversation,
            source=f"write for {clean_id}",
            conversation_id=clean_id,
        )
        timestamp = now_iso()
        title = str(metadata.get("title") or DEFAULT_CONVERSATION_TITLE)
        if title == DEFAULT_CONVERSATION_TITLE:
            title = _conversation_title(cleaned)
        thread = {
            "schema": CONVERSATION_THREAD_SCHEMA,
            "version": 2,
            "conversation_id": clean_id,
            "title": title,
            "created_at": existing["created_at"],
            "updated_at": timestamp,
            "conversation": cleaned,
        }
        self._write_thread_payload(thread)
        metadata.update(
            {
                "title": title,
                "updated_at": timestamp,
                "last_opened_at": timestamp,
                "turn_count": len(cleaned),
            }
        )
        index["active_conversation_id"] = clean_id
        self._write_index(index)
        return self._history(clean_id, index=index)

    @classmethod
    def relocate_directory(
        cls,
        source_directory: str | Path,
        target_project_root: str | Path,
    ) -> dict[str, Any]:
        source = Path(source_directory)
        destination = Path(target_project_root) / CONVERSATIONS_DIR_NAME
        if source.resolve() == destination.resolve():
            return {
                "moved": False,
                "source": str(source),
                "path": str(destination),
                "reason": "already_at_destination",
            }
        if not source.is_dir():
            raise RuntimeError(f"Cadex conversation store does not exist: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            source.replace(destination)
            return {"moved": True, "source": str(source), "path": str(destination)}
        if not destination.is_dir():
            raise RuntimeError(
                f"Cadex conversation destination is not a directory: {destination}"
            )
        if not any(destination.iterdir()):
            destination.rmdir()
            source.replace(destination)
            return {"moved": True, "source": str(source), "path": str(destination)}

        source_store = cls(source.parent)
        destination_store = cls(destination.parent)
        source_index = source_store._read_index()
        if (
            not destination_store.index_path.is_file()
            and not destination_store.legacy_path.is_file()
        ):
            raise RuntimeError(
                "Cannot merge into an incomplete Cadex conversation store at "
                f"{destination}."
            )
        destination_index = destination_store._ensure_index()
        destination_ids = {
            str(item["id"]): item for item in destination_index["conversations"]
        }
        source_files: list[tuple[Path, Path]] = []
        for item in source_index["conversations"]:
            conversation_id = str(item["id"])
            source_file = source_store.thread_path(conversation_id)
            destination_file = destination_store.thread_path(conversation_id)
            if (
                destination_file.exists()
                and destination_file.read_bytes() != source_file.read_bytes()
            ):
                raise RuntimeError(
                    "Cannot merge Cadex conversation stores because thread "
                    f"{conversation_id} differs at the destination."
                )
            source_files.append((source_file, destination_file))

        for source_file, destination_file in source_files:
            if not destination_file.exists():
                _atomic_write_bytes(destination_file, source_file.read_bytes())
        for item in source_index["conversations"]:
            destination_ids[str(item["id"])] = dict(item)
        destination_index["conversations"] = list(destination_ids.values())
        destination_index["active_conversation_id"] = source_index[
            "active_conversation_id"
        ]
        destination_store._write_index(destination_index)

        for source_file, _destination_file in source_files:
            source_file.unlink()
        source_store.index_path.unlink()
        try:
            source.rmdir()
        except OSError:
            pass
        return {
            "moved": True,
            "merged": True,
            "source": str(source),
            "path": str(destination),
        }

    def _ensure_index(self) -> dict[str, Any]:
        if self.index_path.exists():
            index = self._read_index()
            if self.legacy_path.exists():
                if not bool(index.get("legacy_migration_complete")):
                    raise RuntimeError(
                        "Both legacy and threaded Cadex conversation stores exist at "
                        f"{self.project_root}; refusing to choose between them."
                    )
                self.legacy_path.unlink()
            return index
        if self.directory.is_dir() and any(self.directory.iterdir()):
            raise RuntimeError(
                "Cadex conversation store is incomplete: files exist without an "
                f"index at {self.directory}."
            )
        if self.legacy_path.exists():
            return self._migrate_legacy()
        return self._create_initial_index([])

    def _migrate_legacy(self) -> dict[str, Any]:
        try:
            data = json.loads(self.legacy_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError(
                "Cadex legacy conversation could not be read from "
                f"{self.legacy_path}: {exc}"
            ) from exc
        raw = data.get("conversation") if isinstance(data, dict) else data
        if not isinstance(raw, list):
            raise RuntimeError(
                f"Cadex legacy conversation at {self.legacy_path} has no turn list."
            )
        index = self._create_initial_index(
            _clean_conversation_turns(raw),
            legacy_migration_complete=True,
        )
        self.legacy_path.unlink()
        return index

    def _create_initial_index(
        self,
        conversation: list[dict[str, Any]],
        *,
        legacy_migration_complete: bool = False,
    ) -> dict[str, Any]:
        timestamp = now_iso()
        conversation_id = uuid.uuid4().hex
        thread = self._new_thread(conversation_id, conversation, timestamp=timestamp)
        self._write_thread_payload(thread)
        index = {
            "schema": CONVERSATION_INDEX_SCHEMA,
            "version": 1,
            "active_conversation_id": conversation_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            "legacy_migration_complete": legacy_migration_complete,
            "conversations": [self._thread_metadata(thread, timestamp)],
        }
        self._write_index(index)
        return index

    @staticmethod
    def _new_thread(
        conversation_id: str,
        conversation: list[dict[str, Any]],
        *,
        timestamp: str,
    ) -> dict[str, Any]:
        cleaned = _validated_conversation_turns(
            conversation,
            source=f"new thread {conversation_id}",
            conversation_id=conversation_id,
        )
        created_at = next(
            (
                str(item.get("timestamp"))
                for item in cleaned
                if str(item.get("timestamp") or "").strip()
            ),
            timestamp,
        )
        return {
            "schema": CONVERSATION_THREAD_SCHEMA,
            "version": 2,
            "conversation_id": conversation_id,
            "title": _conversation_title(cleaned),
            "created_at": created_at,
            "updated_at": timestamp,
            "conversation": cleaned,
        }

    @staticmethod
    def _thread_metadata(thread: dict[str, Any], last_opened_at: str) -> dict[str, Any]:
        return {
            "id": thread["conversation_id"],
            "title": thread["title"],
            "created_at": thread["created_at"],
            "updated_at": thread["updated_at"],
            "last_opened_at": last_opened_at,
            "turn_count": len(thread["conversation"]),
        }

    def _history(
        self,
        conversation_id: str,
        *,
        index: dict[str, Any],
    ) -> dict[str, Any]:
        metadata = self._metadata_for(index, conversation_id)
        thread = self._read_thread(conversation_id)
        return {
            "path": str(self.thread_path(conversation_id)),
            "store_path": str(self.directory),
            "conversation_id": conversation_id,
            "title": thread["title"],
            "created_at": thread["created_at"],
            "updated_at": thread["updated_at"],
            "turn_count": len(thread["conversation"]),
            "conversation": [dict(item) for item in thread["conversation"]],
            "active": index["active_conversation_id"] == conversation_id,
            "last_opened_at": metadata.get("last_opened_at"),
        }

    @staticmethod
    def _metadata_for(index: dict[str, Any], conversation_id: str) -> dict[str, Any]:
        for item in index["conversations"]:
            if item["id"] == conversation_id:
                return item
        raise RuntimeError(
            f"Cadex conversation {conversation_id} is not in the index."
        )

    def _read_index(self) -> dict[str, Any]:
        data = _read_json_object(self.index_path, "conversation index")
        if data.get("schema") != CONVERSATION_INDEX_SCHEMA or data.get("version") != 1:
            raise RuntimeError(
                f"Cadex conversation index at {self.index_path} has an invalid schema."
            )
        raw_items = data.get("conversations")
        if not isinstance(raw_items, list) or not raw_items:
            raise RuntimeError(
                f"Cadex conversation index at {self.index_path} has no conversations."
            )
        items: list[dict[str, Any]] = []
        ids: set[str] = set()
        for raw in raw_items:
            if not isinstance(raw, dict):
                raise RuntimeError(
                    f"Cadex conversation index at {self.index_path} contains a non-object entry."
                )
            conversation_id = _conversation_id(raw.get("id"))
            if conversation_id in ids:
                raise RuntimeError(
                    f"Cadex conversation index contains duplicate id {conversation_id}."
                )
            ids.add(conversation_id)
            if not self.thread_path(conversation_id).is_file():
                raise RuntimeError(
                    "Cadex conversation index references a missing thread file: "
                    f"{conversation_id}."
                )
            item = dict(raw)
            item["id"] = conversation_id
            item["title"] = str(item.get("title") or DEFAULT_CONVERSATION_TITLE)
            item["turn_count"] = int(item.get("turn_count") or 0)
            items.append(item)
        active = _conversation_id(data.get("active_conversation_id"))
        if active not in ids:
            raise RuntimeError(
                f"Active Cadex conversation {active} is absent from {self.index_path}."
            )
        result = dict(data)
        result["active_conversation_id"] = active
        result["conversations"] = items
        return result

    def _read_thread(self, conversation_id: str) -> dict[str, Any]:
        path = self.thread_path(conversation_id)
        data = _read_json_object(path, "conversation thread")
        version = int(data.get("version") or 0)
        if data.get("schema") != CONVERSATION_THREAD_SCHEMA or version not in {1, 2}:
            raise RuntimeError(
                f"Cadex conversation thread at {path} has an invalid schema."
            )
        if _conversation_id(data.get("conversation_id")) != conversation_id:
            raise RuntimeError(
                f"Cadex conversation thread id does not match {path.name}."
            )
        raw = data.get("conversation")
        if not isinstance(raw, list):
            raise RuntimeError(
                f"Cadex conversation thread at {path} has no turn list."
            )
        result = dict(data)
        result["title"] = str(result.get("title") or DEFAULT_CONVERSATION_TITLE)
        result["created_at"] = str(result.get("created_at") or "")
        result["updated_at"] = str(result.get("updated_at") or "")
        result["conversation"] = _validated_conversation_turns(
            raw,
            source=str(path),
            conversation_id=conversation_id,
        )
        if version != 2 or result["conversation"] != raw:
            result["version"] = 2
            self._write_thread_payload(result)
        return result

    def _write_thread_payload(self, thread: dict[str, Any]) -> None:
        payload = dict(thread)
        payload["schema"] = CONVERSATION_THREAD_SCHEMA
        payload["version"] = 2
        _atomic_write_json(self.thread_path(str(payload["conversation_id"])), payload)

    def _write_index(self, index: dict[str, Any]) -> None:
        payload = dict(index)
        payload["schema"] = CONVERSATION_INDEX_SCHEMA
        payload["version"] = 1
        payload["updated_at"] = now_iso()
        _atomic_write_json(self.index_path, payload)


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
            _atomic_write_bytes(self.script_path, str(source).encode("utf-8"))
        state = self.read_state()
        for key, value in dict(state_updates or {}).items():
            if key not in state or key == "schema":
                raise ValueError(f"Unknown project script state field {key!r}.")
            state[key] = value
        state["updated_at"] = now_iso()
        _atomic_write_json(self.state_path, state)
        return state

    def artifacts_dir(self, revision: str) -> Path:
        clean = str(revision or "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{8,64}", clean):
            raise ValueError("An artifacts directory needs a hexadecimal revision.")
        return self.artifacts_root / clean


class CadexProjectStore:
    """Small durable project store keyed to the active CAD document."""

    def __init__(self, session_id: str, index_path: Path | None = None) -> None:
        self.session_id = str(session_id)
        self.index_path = index_path or _default_index_path()

    def project_scope(self) -> dict[str, Any]:
        doc = _active_document_info()
        project_id = _project_id_for_scope(doc, self.session_id)
        label = doc.get("label") or doc.get("document") or "Unsaved Cadex Project"
        if doc.get("file_path"):
            cad_path = Path(str(doc["file_path"])).expanduser()
            folder_name = f"{slugify(cad_path.stem)}-{project_id[:8]}"
            root = project_root_for_document_file(cad_path)
        else:
            folder_name = f"{slugify(str(label))}-{project_id[:8]}"
            root = cadex_data_dir() / "projects" / folder_name
        persistent = True
        return {
            "project_id": project_id,
            "title": str(label),
            "root": str(root),
            "manifest_path": str(root / "project.cadex.json"),
            "persistent": persistent,
            "document_saved": bool(doc.get("saved")),
            "document": doc,
            "index_path": str(self.index_path),
        }

    def load_manifest(self) -> dict[str, Any]:
        scope = self.project_scope()
        path = Path(str(scope["manifest_path"]))
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise RuntimeError(
                    f"Cadex project manifest could not be read from {path}: {exc}"
                ) from exc
            if not isinstance(data, dict) or data.get("schema") != PROJECT_SCHEMA:
                raise RuntimeError(
                    f"Cadex project manifest at {path} has an invalid schema."
                )
            return self._merge_manifest_defaults(data, scope)
        return self._default_manifest(scope)

    def save_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        scope = self.project_scope()
        merged = self._merge_manifest_defaults(manifest, scope)
        merged["updated_at"] = now_iso()
        path = Path(str(scope["manifest_path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.name}.tmp")
        tmp.write_text(json.dumps(merged, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(path)
        self._update_index(merged, scope)
        return merged

    def context(self) -> dict[str, Any]:
        scope = self.project_scope()
        manifest = self.save_manifest(self.load_manifest())
        return {
            "schema": "cadex-project-context-v2",
            "project_id": manifest["project_id"],
            "title": manifest.get("title") or scope.get("title"),
            "summary": manifest.get("summary") or "",
            "root": scope["root"],
            "manifest_path": scope["manifest_path"],
            "index_path": scope["index_path"],
            "persistent": bool(scope.get("persistent")),
            "document_saved": bool(scope.get("document_saved")),
            "document": scope.get("document", {}),
            "documents": manifest.get("documents", {}),
            "modeling_engine": str(manifest.get("modeling_engine") or DEFAULT_MODELING_ENGINE),
        }

    def conversation_histories(self) -> list[dict[str, Any]]:
        return self.conversation_store().all_histories()

    def conversation_store(self) -> CadexConversationStore:
        root = Path(str(self.project_scope()["root"]))
        return CadexConversationStore(root)

    def update_summary(self, *, title: str = "", summary: str = "") -> dict[str, Any]:
        """Update the human-facing title/summary for the project."""
        manifest = self.load_manifest()
        if str(title or "").strip():
            manifest["title"] = str(title).strip()
        if str(summary or "").strip():
            manifest["summary"] = str(summary).strip()
        saved = self.save_manifest(manifest)
        return {
            "ok": True,
            "title": saved.get("title"),
            "summary": saved.get("summary"),
            "manifest_path": self.project_scope()["manifest_path"],
            "updated_at": saved.get("updated_at"),
        }

    def modeling_engine(self) -> str:
        engine = str(
            self.load_manifest().get("modeling_engine") or DEFAULT_MODELING_ENGINE
        ).strip().lower()
        # xscript is the only engine; a legacy tag migrates to it silently.
        return engine if engine in MODELING_ENGINES else DEFAULT_MODELING_ENGINE

    @staticmethod
    def read_modeling_engine_manifest(manifest_path: str | Path) -> str:
        """Read only the persisted engine from an already captured project path.

        This helper deliberately has no FreeCAD/document access, allowing the
        interactive session to perform the filesystem read off the document
        thread after it captures the active project's identity.
        """

        path = Path(str(manifest_path))
        if not path.is_file():
            return DEFAULT_MODELING_ENGINE
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError(
                f"Cadex project manifest could not be read from {path}: {exc}"
            ) from exc
        if not isinstance(data, dict) or data.get("schema") != PROJECT_SCHEMA:
            raise RuntimeError(
                f"Cadex project manifest at {path} has an invalid schema."
            )
        engine = str(
            data.get("modeling_engine")
            or data.get("partdesign_engine")
            or DEFAULT_MODELING_ENGINE
        ).strip().lower()
        # xscript is the only engine; a legacy tag migrates to it silently.
        return engine if engine in MODELING_ENGINES else DEFAULT_MODELING_ENGINE

    def set_modeling_engine(self, engine: str) -> dict[str, Any]:
        clean = str(engine or "").strip().lower()
        if clean not in MODELING_ENGINES:
            raise ValueError(f"Modeling engine must be one of: {sorted(MODELING_ENGINES)}.")
        manifest = self.load_manifest()
        manifest["modeling_engine"] = clean
        saved = self.save_manifest(manifest)
        return {
            "engine": clean,
            "manifest_path": self.project_scope()["manifest_path"],
            "updated_at": saved.get("updated_at"),
        }

    def _default_manifest(self, scope: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema": PROJECT_SCHEMA,
            "version": 2,
            "project_id": scope["project_id"],
            "title": scope["title"],
            "summary": "",
            "modeling_engine": DEFAULT_MODELING_ENGINE,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "documents": {"active": scope.get("document", {})},
        }

    def _merge_manifest_defaults(
        self, manifest: dict[str, Any], scope: dict[str, Any]
    ) -> dict[str, Any]:
        default = self._default_manifest(scope)
        merged = dict(default)
        migrated_engine = manifest.get("modeling_engine")
        if migrated_engine is None:
            migrated_engine = manifest.get("partdesign_engine")
        merged.update(
            {
                key: value
                for key, value in manifest.items()
                if key in default and value is not None
            }
        )
        merged["schema"] = PROJECT_SCHEMA
        merged["version"] = 2
        # xscript is the only engine; migrate any legacy engine tag to it (the
        # api graph and published geometry are engine-agnostic).
        migrated = str(migrated_engine or DEFAULT_MODELING_ENGINE).strip().lower()
        merged["modeling_engine"] = (
            migrated if migrated in MODELING_ENGINES else DEFAULT_MODELING_ENGINE
        )
        merged["project_id"] = scope["project_id"]
        merged["documents"] = dict(merged.get("documents") or {})
        merged["documents"]["active"] = scope.get("document", {})
        return merged

    def _update_index(self, manifest: dict[str, Any], scope: dict[str, Any]) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.index_path)) as conn:
            conn.execute(
                """
                    CREATE TABLE IF NOT EXISTS projects_v2 (
                        project_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        root TEXT NOT NULL,
                        manifest_path TEXT NOT NULL,
                        cad_file TEXT,
                        updated_at TEXT NOT NULL
                    )
                    """
            )
            conn.execute(
                """
                    INSERT INTO projects_v2 (
                        project_id, title, summary, root, manifest_path, cad_file, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(project_id) DO UPDATE SET
                        title=excluded.title,
                        summary=excluded.summary,
                        root=excluded.root,
                        manifest_path=excluded.manifest_path,
                        cad_file=excluded.cad_file,
                        updated_at=excluded.updated_at
                    """,
                (
                    manifest["project_id"],
                    str(manifest.get("title") or scope.get("title") or ""),
                    str(manifest.get("summary") or ""),
                    str(scope["root"]),
                    str(scope["manifest_path"]),
                    (scope.get("document") or {}).get("file_path"),
                    str(manifest.get("updated_at") or now_iso()),
                ),
            )
