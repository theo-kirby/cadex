# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Each accepted revision's model, kept so its history can play (orun3 V3, ADR-546).

The engine keeps every accepted *source* (``script_history/``, ADR-045) but
only the latest accepted attempt's geometry: older staging directories are
pruned (``ATTEMPT_KEEP``). So once a revision is replaced, what it looked
like is gone unless something kept it. This module keeps it, in a store the
CLI owns under ``review/revisions/`` (ignored by the project's own git,
ADR-194):

- ``parts/<sha256>.tess.bin`` and ``.tess.json`` — one part's tessellation,
  named by the sha256 of its buffer, so a part that did not change between
  revisions is the same file and costs no new bytes;
- ``index.json`` — per history ordinal: the revision, its digest, which
  blob each output's tessellation is, and how the accepted model placed its
  components (the dashboard's ``accepted_model`` at that moment).

:func:`retain` runs where the CLI already holds the project — at the end of
every engine session and after each successful modelling call through
``cadex mcp`` — and is idempotent: it keeps the *currently accepted*
attempt under the ordinal the engine gave it, and does nothing when that
ordinal is already kept. It never fails the call that triggered it.

:func:`revision_models` is the read side: one row per stored revision, with
its parts, or why it has none. A revision accepted before this store
existed reads as not retained, with that reason; another revision's
geometry is never offered in its place.

:func:`backfill` fills that gap, and only when asked (``cadex revision
backfill``, ADR-548): it rebuilds an old revision's stored source in a
scratch project and keeps the result only if the engine lands on exactly
that revision id. Nothing that reads the store ever calls it.
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import tarfile
import time
from pathlib import Path
from typing import Any, Mapping

from .revisions import read_history

STORE_DIR = Path("review") / "revisions"
PARTS_DIR = "parts"
INDEX_NAME = "index.json"
SCHEMA = "cadex-revision-meshes-v1"

#: Why a stored revision has no retained model, when a backfill could not rebuild it.
UNREBUILT = "accepted before this project retained revision meshes, and `cadex revision backfill` could not rebuild it: "

#: Why a stored revision has no retained model, when it predates this store.
NOT_RETAINED = ("accepted before this project retained revision meshes (ADR-546); "
                "its geometry was not kept. `cadex revision backfill` rebuilds it (ADR-548)")


def store_root(project_root: Path | str) -> Path:
    return Path(project_root).expanduser() / STORE_DIR


def read_index(project_root: Path | str) -> dict[str, Any]:
    """The store's index; an empty one when absent or unreadable."""

    path = store_root(project_root) / INDEX_NAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        return {"schema": SCHEMA, "revisions": {}, "unrebuilt": {}}
    if not isinstance(data.get("revisions"), dict):
        data["revisions"] = {}
    if not isinstance(data.get("unrebuilt"), dict):
        data["unrebuilt"] = {}
    return data


def _write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_bytes(content)
    tmp.replace(path)


def _current_entry(root: Path, revision: str, digest: str) -> dict[str, Any] | None:
    """The history entry the engine wrote for this acceptance: the latest one
    carrying the revision, and only if its digest (when it has one) agrees."""

    for entry in reversed(read_history(root)):
        if str(entry.get("revision") or "") == revision:
            recorded = str(entry.get("digest") or "")
            return entry if not recorded or not digest or recorded == digest else None
    return None


def retain(project_root: Path | str) -> dict[str, Any]:
    """Keep the accepted attempt's model under its history ordinal.

    Returns what happened: ``{"status": "retained" | "kept" | "skipped",
    "ordinal", "added_bytes", "reason"}``. ``kept`` means the ordinal was
    already in the store. Never raises.
    """

    try:
        return _retain(Path(project_root).expanduser())
    except Exception as exc:  # a store hiccup must never fail a build
        return {"status": "skipped", "reason": f"retaining failed: {exc}"}


def _retain(root: Path) -> dict[str, Any]:
    # The dashboard's own reading of the accepted attempt: the same
    # sha256 link from each output's BREP to its tessellation, and the same
    # placements, so the store holds exactly what the page drew.
    from .review_server import accepted_model_uncached

    model = accepted_model_uncached(root)
    revision, digest = str(model.get("revision") or ""), str(model.get("digest") or "")
    if not model.get("available"):
        return {"status": "skipped", "reason": str(model.get("reason") or "no accepted model")}
    entry = _current_entry(root, revision, digest)
    if entry is None:
        return {"status": "skipped",
                "reason": f"revision {revision[:12]} is not the latest matching entry in the stored trail"}
    ordinal = str(entry.get("ordinal"))
    index = read_index(root)
    held = index["revisions"].get(ordinal)
    if isinstance(held, Mapping) and held.get("revision") == revision:
        return {"status": "kept", "ordinal": int(ordinal), "added_bytes": 0}

    return _store(root, root, model, ordinal)


def _store(root: Path, built: Path, model: Mapping[str, Any], ordinal: str,
           provenance: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Keep ``model`` — the accepted model of the project at ``built`` — in
    ``root``'s store under ``ordinal``. ``built`` is ``root`` itself when
    retaining, and a scratch rebuild when backfilling."""

    from .review_server import _accepted_staging

    staging, _manifest, reason = _accepted_staging(built)
    if staging is None:
        return {"status": "skipped", "reason": str(reason)}
    index = read_index(root)
    parts_dir = store_root(root) / PARTS_DIR
    parts: dict[str, dict[str, Any]] = {}
    added = full = 0
    for output, artifact in sorted((model.get("meshes") or {}).items()):
        data = (staging / artifact).read_bytes()
        sidecar = _load(staging / str(artifact).replace(".tess.bin", ".tess.json")) or {}
        sha = hashlib.sha256(data).hexdigest()
        sidecar = {**sidecar, "artifact_path": f"{sha}.tess.bin"}
        sidecar_bytes = json.dumps(sidecar, sort_keys=True).encode("utf-8")
        full += len(data) + len(sidecar_bytes)
        blob, meta = parts_dir / f"{sha}.tess.bin", parts_dir / f"{sha}.tess.json"
        if not blob.is_file():
            _write_atomic(blob, data)
            added += len(data)
        if not meta.is_file():
            _write_atomic(meta, sidecar_bytes)
            added += len(sidecar_bytes)
        parts[output] = {"sha256": sha, "bytes": len(data),
                         "triangles": (sidecar.get("counts") or {}).get("triangles")}

    row = {
        "ordinal": int(ordinal),
        "revision": str(model.get("revision") or ""),
        "digest": str(model.get("digest") or ""),
        "retained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "attempt": staging.name,
        "parts": parts,
        "components": [
            {key: component.get(key) for key in ("name", "output", "placement", "placement_source", "world")}
            for component in model.get("components") or []
        ],
        "placement_source": model.get("placement_source"),
        "full_bytes": full,
        "added_bytes": added,
    }
    if provenance:
        row["backfilled"] = dict(provenance)
    index["revisions"][ordinal] = row
    index["unrebuilt"].pop(ordinal, None)
    return {**_write_index(root, index), "ordinal": int(ordinal), "added_bytes": added, "full_bytes": full}


def _write_index(root: Path, index: dict[str, Any]) -> dict[str, Any]:
    _prune(root, index)
    path = store_root(root) / INDEX_NAME
    old_size = path.stat().st_size if path.is_file() else 0
    payload = json.dumps(index, sort_keys=True, separators=(",", ":")).encode("utf-8")
    _write_atomic(path, payload)
    return {"status": "retained", "index_bytes_delta": len(payload) - old_size}


def _prune(root: Path, index: dict[str, Any]) -> None:
    """Drop rows for ordinals the engine's trail no longer holds
    (``HISTORY_LIMIT``), then every blob no remaining row names, so the
    store is bounded by the trail it shadows."""

    alive = {str(entry.get("ordinal")) for entry in read_history(root)}
    index["revisions"] = {key: row for key, row in index["revisions"].items() if key in alive}
    index["unrebuilt"] = {key: row for key, row in index.get("unrebuilt", {}).items() if key in alive}
    named = {part.get("sha256") for row in index["revisions"].values()
             for part in (row.get("parts") or {}).values()}
    parts_dir = store_root(root) / PARTS_DIR
    if parts_dir.is_dir():
        for path in parts_dir.iterdir():
            if path.name.split(".", 1)[0] not in named:
                path.unlink(missing_ok=True)


def revision_models(project_root: Path | str) -> list[dict[str, Any]]:
    """One row per stored revision, oldest first: its retained parts, or why
    there are none. A row is retained only when its index entry names the
    same revision and every blob it names is on disk."""

    root = Path(project_root).expanduser()
    stored = read_index(root)
    index, unrebuilt = stored["revisions"], stored["unrebuilt"]
    parts_dir = store_root(root) / PARTS_DIR
    rows: list[dict[str, Any]] = []
    for entry in read_history(root):
        ordinal, revision = entry.get("ordinal"), str(entry.get("revision") or "")
        row: dict[str, Any] = {"ordinal": ordinal, "revision": revision, "retained": False}
        held = index.get(str(ordinal))
        failed = unrebuilt.get(str(ordinal))
        if not isinstance(held, Mapping) and isinstance(failed, Mapping) and failed.get("revision") == revision:
            row["reason"] = UNREBUILT + str(failed.get("reason") or "")
        elif not isinstance(held, Mapping):
            row["reason"] = NOT_RETAINED
        elif held.get("revision") != revision:
            row["reason"] = (f"the store's row for ordinal {ordinal} names revision "
                             f"{str(held.get('revision'))[:12]}, not this one; not shown")
        else:
            parts = dict(held.get("parts") or {})
            missing = sorted(name for name, part in parts.items()
                             if not (parts_dir / f"{part.get('sha256')}.tess.bin").is_file())
            if missing:
                row["reason"] = "retained meshes missing from the store: " + ", ".join(missing)
            else:
                row.update(retained=True, digest=held.get("digest"), parts=parts,
                           components=list(held.get("components") or []))
        rows.append(row)
    return rows


# -- backfill ----------------------------------------------------------------
#
# A revision accepted before this store existed has its source in the trail
# but no geometry anywhere. ``cadex revision backfill`` rebuilds it through
# the engine, in a scratch project so the project's own acceptance never
# moves, and keeps the result only when the rebuild *is* that revision: the
# engine's revision id binds the source and every stored value, so an equal
# id is the same model, and a different one is said, never stored.


def _acceptances(root: Path) -> dict[str, dict[str, Any]]:
    """Per accepted revision, what the project's own repository (ADR-194)
    recorded with it: the earliest commit whose ``script.json`` names it as
    accepted, and the values that ``script.json`` held. Empty when the
    project keeps no history."""

    from .project_docs import _git

    if not (root / ".git").exists():
        return {}
    log = _git(root, "log", "--format=%H", "--", "script.json")
    found: dict[str, dict[str, Any]] = {}
    for commit in log.stdout.split() if log.returncode == 0 else []:
        shown = _git(root, "show", f"{commit}:script.json")
        try:
            state = json.loads(shown.stdout) if shown.returncode == 0 else None
        except ValueError:
            state = None
        if not isinstance(state, dict) or not state.get("accepted_revision"):
            continue
        # Newest first, so the last write per revision is its earliest commit.
        found[str(state["accepted_revision"])] = {"commit": commit, "values": {
            "params": dict(state.get("param_values") or {}),
            **{key: list(state.get(f"{key[:-1]}_values") or [])
               for key in ("nets", "boards", "mounts", "cages")}}}
    return found


def _candidates(entry: Mapping[str, Any], recorded: Mapping[str, Any] | None) -> list[tuple[str, dict[str, Any]]]:
    """The values to try a revision's source with, most trusted first: those
    the trail stored with it (ADR-506), those the project's repository
    recorded at its acceptance, then none at all (every parameter at its
    default). The revision check decides which, if any, is right."""

    out: list[tuple[str, dict[str, Any]]] = []
    if isinstance(entry.get("values"), Mapping):
        out.append(("the values the trail stored with it (ADR-506)", dict(entry["values"])))
    if recorded is not None:
        out.append((f"the values script.json held at its acceptance (project commit "
                    f"{recorded['commit'][:12]})", dict(recorded["values"])))
    out.append(("no stored values: every parameter at its default", {}))
    seen, unique = set(), []
    for label, values in out:
        key = json.dumps(values, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append((label, values))
    return unique


def _scratch_assets(root: Path, scratch: Path, commit: str | None) -> str:
    """Give the scratch project the assets the revision was built with: the
    ones the repository held at its acceptance commit, else today's. The
    revision id does not bind asset bytes, so this is what keeps an imported
    mesh replaced since from passing for the old one."""

    target = scratch / "assets"
    target.mkdir(parents=True, exist_ok=True)
    if commit:
        archive = subprocess.run(
            ["git", "-C", str(root), "archive", "--format=tar", commit, "--", "assets"],
            capture_output=True, check=False)
        if archive.returncode != 0:
            # `git archive` refuses a pathspec the commit does not have.
            return f"no assets at project commit {commit[:12]}"
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            for member in tar.getmembers():
                name = Path(member.name)
                handle = tar.extractfile(member) if member.isfile() else None
                if handle is not None and name.parent == Path("assets"):
                    (target / name.name).write_bytes(handle.read())
        return f"assets as of project commit {commit[:12]}"
    source = root / "assets"
    if source.is_dir():
        for path in source.iterdir():
            if path.is_file() and not path.is_symlink():
                shutil.copy2(path, target / path.name)
    return "today's assets: no project commit recorded its acceptance"


def backfill(project_root: Path | str, client: Any, *, display: Mapping[str, Any],
             selector: str = "", progress: Any = None) -> list[dict[str, Any]]:
    """Rebuild every stored revision without a retained model, and keep each
    one whose rebuild reproduces its revision id exactly.

    ``client`` is a started cadexd; it opens one scratch project per try and
    never the project itself, so nothing the project accepted moves. One row
    per revision attempted, the accepted one first when it was not yet kept:
    ``retained`` (with what it was built from and
    the bytes it added), ``copied`` (another ordinal of the same revision was
    already kept), or ``failed`` with the reason — a rebuild that lands on
    another revision is reported, never stored. ``selector`` limits it to
    one ordinal.
    """

    import tempfile
    from .client import open_project
    from .review_server import accepted_model_uncached
    from .revisions import read_source
    from .session import read_working_revision

    root = Path(project_root).expanduser().resolve()
    say = progress or (lambda _text: None)
    rows: list[dict[str, Any]] = []
    # The accepted revision's attempt is still on disk: keep it from there,
    # as any session would, rather than ask today's engine to rebuild it.
    kept = retain(root)
    if kept.get("status") == "retained":
        rows.append({"ordinal": kept["ordinal"], "revision": str(read_index(root)["revisions"]
                     [str(kept["ordinal"])]["revision"]), "status": "retained",
                     "values": "none rebuilt: the accepted attempt still on disk (ADR-546)",
                     "added_bytes": kept["added_bytes"], "full_bytes": kept["full_bytes"]})
    acceptances: dict[str, dict[str, Any]] | None = None
    for model_row in revision_models(root):
        ordinal, revision = model_row["ordinal"], str(model_row["revision"])
        if model_row["retained"] or (selector and str(ordinal) != str(selector)):
            continue
        entry = next(e for e in read_history(root) if e.get("ordinal") == ordinal)
        result: dict[str, Any] = {"ordinal": ordinal, "revision": revision}
        rows.append(result)
        index = read_index(root)
        twin = next((row for key, row in index["revisions"].items()
                     if key != str(ordinal) and isinstance(row, Mapping) and row.get("revision") == revision
                     and not row.get("backfilled", {}).get("copied_from")), None)
        if twin is not None:
            index["revisions"][str(ordinal)] = {
                **twin, "ordinal": ordinal, "added_bytes": 0,
                "backfilled": {"copied_from": twin["ordinal"],
                               "why": "the same revision id: the same source and values"}}
            _write_index(root, index)
            result.update(status="copied", copied_from=twin["ordinal"], added_bytes=0)
            continue
        try:
            source = read_source(root, entry)
        except ValueError as exc:
            result.update(status="failed", reason=str(exc))
            continue
        if acceptances is None:
            acceptances = _acceptances(root)
        recorded = acceptances.get(revision)
        tries: list[str] = []
        for label, values in _candidates(entry, recorded):
            say(f" · revision {ordinal}: rebuilding with {label}")
            started = time.monotonic()
            with tempfile.TemporaryDirectory(prefix="cadex-backfill-") as scratch_dir:
                scratch = Path(scratch_dir)
                assets = _scratch_assets(root, scratch, recorded["commit"] if recorded else None)
                open_project(client, scratch, restore=False)
                reply = client.request("write_script", {
                    "source": source, "replace": True, "display": dict(display),
                    "expected_revision": read_working_revision(client)})
                patch = {key: value for key, value in values.items()
                         if value and key in ("nets", "boards", "mounts", "cages")}
                if reply.get("ok") is True and (values.get("params") or patch):
                    reply = client.request("set_params", {
                        "values": dict(values.get("params") or {}), **patch,
                        "display": dict(display), "expected_revision": read_working_revision(client)})
                if reply.get("ok") is not True:
                    tries.append(f"with {label}: the engine refused it: "
                                 f"{reply.get('error') or reply.get('failure_code') or 'no reason given'}")
                    continue
                model = accepted_model_uncached(scratch)
                got, digest = str(model.get("revision") or ""), str(model.get("digest") or "")
                if got != revision:
                    tries.append(f"with {label}: rebuilt as revision {got[:12]}, not {revision[:12]}")
                    continue
                if entry.get("digest") and digest != entry["digest"]:
                    tries.append(f"with {label}: the revision matched but the digest "
                                 f"{digest[:12]} is not the trail's {str(entry['digest'])[:12]}")
                    continue
                if not model.get("available"):
                    tries.append(f"with {label}: {model.get('reason') or 'no model to keep'}")
                    continue
                stored = _store(root, scratch, model, str(ordinal), provenance={
                    "values": label, "assets": assets,
                    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
                result.update(status="retained", values=label, assets=assets,
                              added_bytes=stored.get("added_bytes", 0),
                              full_bytes=stored.get("full_bytes", 0),
                              seconds=round(time.monotonic() - started, 1))
                break
        else:
            result.update(status="failed", reason="no rebuild reproduced it: " + "; ".join(tries))
            # Remembered, so the page says why rather than suggest a backfill again.
            index = read_index(root)
            index["unrebuilt"][str(ordinal)] = {
                "revision": revision, "reason": result["reason"],
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            _write_index(root, index)
    return rows


def _load(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


#: Where the page fetches one retained part, by the sha256 of its buffer.
MESH_ROUTE = "/mesh/revision/{sha}.stl"


def _drawn(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """A retained row's components as the viewer draws them: each with the
    route of its own part's blob, or none when that part was not kept."""

    parts = row.get("parts") or {}
    out = []
    for component in row.get("components") or []:
        part = parts.get(component.get("output")) or {}
        sha = part.get("sha256")
        out.append({**component, "sha256": sha,
                    "mesh": MESH_ROUTE.format(sha=sha) if sha else None,
                    "mesh_status": "retained" if sha else "missing"})
    return out


def revision_model(project_root: Path | str, ordinal: int) -> dict[str, Any] | None:
    """``/api/model/revision/<ordinal>``: one stored revision's retained model,
    the one before it as a ghost, and which parts changed between them.

    ``None`` when the trail holds no such ordinal. A revision that was not
    retained is ``available: false`` with :func:`revision_models`' reason
    and no components. ``previous`` is the stored revision before it,
    drawn only when it was retained too; ``changed`` names the outputs
    whose part digest differs from it (or that it did not have), and is
    ``None`` when there is nothing retained to compare with.
    """

    rows = revision_models(project_root)
    index = next((i for i, row in enumerate(rows) if row.get("ordinal") == ordinal), None)
    if index is None:
        return None
    row = rows[index]
    model: dict[str, Any] = {
        "view": "revision", "ordinal": row["ordinal"], "revision": row["revision"],
        "digest": row.get("digest"), "available": bool(row["retained"]),
        "reason": row.get("reason", ""), "components": [], "previous": None, "changed": None,
        "source": "the store of retained revision meshes (review/revisions/, ADR-546)",
    }
    if not row["retained"]:
        return model
    model["components"] = _drawn(row)
    if index == 0:
        model["compare"] = "the first stored revision: nothing before it to compare with"
        return model
    before = rows[index - 1]
    model["previous"] = {"ordinal": before["ordinal"], "revision": before["revision"],
                         "available": bool(before["retained"]), "reason": before.get("reason", ""),
                         "components": _drawn(before) if before["retained"] else []}
    if not before["retained"]:
        model["compare"] = f"revision {before['ordinal']} was not retained: nothing to compare with"
        return model
    old = {name: part.get("sha256") for name, part in (before.get("parts") or {}).items()}
    model["changed"] = sorted(name for name, part in (row.get("parts") or {}).items()
                              if old.get(name) != part.get("sha256"))
    model["compare"] = f"against revision {before['ordinal']}"
    for component in model["components"]:
        component["changed"] = component.get("output") in model["changed"]
    return model


def revision_mesh_paths(project_root: Path | str, sha: str) -> tuple[Path, Path] | None:
    """The kept ``.tess.bin`` and ``.tess.json`` for one part digest, or
    ``None`` unless ``sha`` is a sha256 the store holds."""

    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        return None
    parts = store_root(project_root) / PARTS_DIR
    blob, meta = parts / f"{sha}.tess.bin", parts / f"{sha}.tess.json"
    if not blob.is_file() or not meta.is_file() or blob.is_symlink() or meta.is_symlink():
        return None
    return blob, meta
