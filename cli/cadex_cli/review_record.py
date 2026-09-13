# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The run record and the project review reader (ADR-285).

A walk leaves ``runs/<name>/review.json`` with its numbers, but a reader
who arrives later — a person, or the review dashboard the ot5 charter asks
for — needs identities before numbers: which accepted revision and digest
the run's rollout ran on, the parameters and their specs *at that
revision*, the task, the policy digest, and where every retained artifact
is. ``review.json`` carries some of this by accident (the legs' identity
fields) and none of it by contract. This module is the contract.

Two halves, and one rule between them:

* :func:`write_run_record` lands ``runs/<name>/run.json`` (schema
  ``cadex-run-record-v1``) from what the walk already holds — the envelopes
  its legs returned, the trainer's receipt, the accepted-revision script
  state it read during the review — plus a bounded snapshot of the
  project's documents at that moment, so the specs and decisions a run was
  made under stay readable after the design moves on.
* :func:`read_project_review` reads a project back: the accepted identity
  now, the documents now, and every run under ``runs/`` with its record
  resolved against the disk. It **only reads**. It never rebuilds, never
  opens an engine and never re-accepts anything: a historical run is shown
  from what was recorded when it ran, and a run whose files are gone says
  so rather than borrowing today's.

The rule: every path in a record is relative — to the run directory in
``artifacts`` and to the project root in ``project_artifacts`` — and the
reader resolves each one with a containment check. A reference that
escapes its base, by ``..`` or by a symlink, is reported as an error and
never opened, which is what lets a review client serve a project's
permitted artifacts and nothing else.
"""

from __future__ import annotations

import datetime as _datetime
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import shutil
import threading
from typing import Any, Mapping, Sequence

RUN_RECORD_FILENAME = "run.json"
RUN_RECORD_SCHEMA = "cadex-run-record-v1"
PROJECT_REVIEW_SCHEMA = "cadex-project-review-v1"
#: Where the walk's runs live, relative to the project (``docs/CLI.md``).
RUNS_DIRNAME = "runs"
#: The project-document snapshot a record carries, relative to the run.
DOC_SNAPSHOT_DIRNAME = "project-docs"
#: Bounds on that snapshot: the documents are the agent's prose, a few KB
#: each; a file past this is not a document and is listed as skipped.
DOC_SNAPSHOT_LIMIT_BYTES = 262_144
DOC_SNAPSHOT_LIMIT_FILES = 32
#: The project manifest the accepted identity is read from (read-only; the
#: layout is ``docs/ARCHITECTURE.md``'s "Project store").
PROJECT_SCRIPT_FILENAME = "script.json"
PROJECT_SCRIPT_SCHEMA = "cadex-project-script-v1"
#: What a run may be in. ``running`` is written when the walk starts and is
#: what an interrupted walk leaves behind; the reader names it as such.
RUN_STATES = ("running", "ok", "failed", "pending")

#: The retained artifacts a record names, and the base each resolves against.
RUN_ARTIFACT_KEYS = ("script", "review", "trace", "task_bundle", "model_xml",
                     "progress", "receipt", "project_docs")
PROJECT_ARTIFACT_KEYS = ("policy", "render", "section", "inventory", "clearance")


def _now() -> str:
    return (
        _datetime.datetime.now(_datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _video_stamp(path: Path) -> tuple[int, ...]:
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


_video_verification_lock = threading.Lock()


@lru_cache(maxsize=256)
def _cached_video_sha256(path: Path, stamp: tuple[int, ...]) -> str:
    """Bounded process-local digests; never retain file bytes or project state."""
    digest = _sha256(path)
    if _video_stamp(path) != stamp:
        raise OSError("video changed during verification")
    return digest


def _video_sha256(path: Path) -> str:
    # Containment is checked by the caller on every read, before this cache.
    # ctime catches same-size edits even when a writer restores mtime.
    path = path.resolve()
    # lru_cache protects its mapping, but permits concurrent duplicate misses.
    # Serialize lookup plus hashing, with no per-file lock registry to grow.
    with _video_verification_lock:
        stamp = _video_stamp(path)
        digest = _cached_video_sha256(path, stamp)
    if _video_stamp(path) != stamp:
        raise OSError("video changed during verification")
    return digest


def relative_under(base: Path | str, path: Path | str | None) -> str | None:
    """``path`` relative to ``base`` as a POSIX string, or None when outside.

    Both sides are resolved first, so a symlinked run directory and its
    real location agree; this is the one place the writer decides whether a
    reference is recordable at all.
    """

    if path is None or str(path) == "":
        return None
    try:
        relative = Path(str(path)).expanduser().resolve().relative_to(
            Path(base).expanduser().resolve()
        )
    except (ValueError, OSError):
        return None
    return relative.as_posix()


def resolve_reference(base: Path | str, relative: Any) -> dict[str, Any]:
    """Resolve one recorded reference against its base, never outside it.

    Returns ``{"path", "exists", "error"}``: ``path`` is the reference as
    recorded, ``exists`` whether it is on disk *inside* the base, ``error``
    why it could not be honoured — absent, not a string, absolute, or
    escaping the base by ``..`` or by a symlink. A reference with an error
    is never opened.
    """

    if relative is None:
        return {"path": None, "exists": False, "error": "not recorded"}
    if not isinstance(relative, str) or not relative:
        return {"path": relative, "exists": False, "error": "not a relative path"}
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        return {"path": relative, "exists": False,
                "error": "escapes the base directory"}
    root = Path(base).expanduser().resolve()
    try:
        resolved = (root / candidate).resolve()
        resolved.relative_to(root)
    except (ValueError, OSError):
        return {"path": relative, "exists": False,
                "error": "escapes the base directory"}
    return {"path": relative, "exists": resolved.exists(), "error": None}


def snapshot_project_docs(project_root: Path | str, out_dir: Path | str) -> dict[str, Any]:
    """Copy the project's documents beside the run, bounded, with digests.

    ``ARCHITECTURE.md``, ``DECISIONS.md``, ``PROGRESS.md`` and ``docs/*.md``
    — the specs and decisions the agent wrote, as they stood when the run
    was recorded. ``PROGRESS.md`` is copied before this run's own row lands
    (the row is appended after the command returns), and the record says
    so. Files past the size bound, or past the count bound, are listed as
    skipped rather than half-copied.
    """

    root = Path(project_root).expanduser()
    target = Path(out_dir).expanduser() / DOC_SNAPSHOT_DIRNAME
    candidates: list[Path] = [
        root / name for name in ("ARCHITECTURE.md", "DECISIONS.md", "PROGRESS.md")
    ]
    candidates.extend(sorted((root / "docs").glob("*.md")) if (root / "docs").is_dir() else [])
    files: dict[str, str] = {}
    skipped: list[dict[str, str]] = []
    if target.exists():
        shutil.rmtree(target)
    for source in candidates:
        if not source.is_file():
            continue
        relative = source.relative_to(root).as_posix()
        if len(files) >= DOC_SNAPSHOT_LIMIT_FILES:
            skipped.append({"path": relative, "reason": "file count bound"})
            continue
        if source.stat().st_size > DOC_SNAPSHOT_LIMIT_BYTES:
            skipped.append({"path": relative, "reason": "size bound"})
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        files[relative] = _sha256(destination)
    return {
        "dir": DOC_SNAPSHOT_DIRNAME if files else None,
        "files": files,
        "skipped": skipped,
        "note": "copied when the run was recorded, before this run's own PROGRESS.md row.",
    }


def write_run_record(
    out_dir: Path | str,
    *,
    project_root: Path | str,
    status: str,
    mode: str,
    legs: Sequence[Mapping[str, Any]] = (),
    error: str | None = None,
    accepted_revision: str = "",
    digest: str = "",
    params: Mapping[str, Any] | None = None,
    param_specs: Sequence[Any] | None = None,
    specs_source: str = "",
    training: Mapping[str, Any] | None = None,
    requested: Mapping[str, Any] | None = None,
    policy_name: str = "",
    policy_sha256: str = "",
    task_bundle: Path | str | None = None,
    task_sha256: str = "",
    model_xml: Path | str | None = None,
    trace: Path | str | None = None,
    review: Mapping[str, Any] | None = None,
    walk_seconds: float | None = None,
    snapshot_docs: bool = False,
    identity_source: str = "",
) -> Path:
    """Land ``run.json`` under ``out_dir``; rewritten whole at each state.

    Written by a walk as ``running`` when it starts (so an interrupted walk
    leaves a record that says it never finished), again as ``running``
    before its train leg when a design turn or sweep moved the accepted
    revision, then ``ok``, ``failed`` or ``pending`` when it ends. Every
    path is relative to the run directory or the project root; anything
    outside either is recorded as null rather than as an absolute path, so
    the file reads the same from a copy of the project.

    ``identity_source`` names where ``accepted_revision`` and ``digest``
    came from — the project manifest at walk start, or the last leg whose
    envelope reported them — so a run that is still training, or that
    failed before its rollout, is tied to the revision it trained on
    rather than to nothing. Left blank, it is ``rollout leg envelope`` when
    a revision is given and ``not reached`` otherwise.
    """

    if status not in RUN_STATES:
        raise ValueError(f"run status must be one of {RUN_STATES}, not {status!r}")
    run_dir = Path(out_dir).expanduser()
    run_dir.mkdir(parents=True, exist_ok=True)
    root = Path(project_root).expanduser()
    review = dict(review or {})
    training = dict(training or {})
    train_dir = run_dir / "train"
    progress = train_dir / "progress.json"
    receipt = train_dir / "training-receipt.json"
    frozen, _ = _load_json(run_dir / "training-view.json")
    docs = frozen["project_docs"] if frozen else (
        snapshot_project_docs(root, run_dir) if snapshot_docs else {
            "dir": None, "files": {}, "skipped": [], "note": "not snapshotted",
        })
    if frozen and frozen["identity"].get("available"):
        param_specs = frozen["identity"].get("param_specs")
        specs_source = "project manifest before training"
        params = frozen["identity"].get("param_values", params)
    artifacts = {
        "script": "script.py" if (run_dir / "script.py").is_file() else None,
        "review": "review.json" if (run_dir / "review.json").is_file() else None,
        "trace": relative_under(run_dir, trace),
        "task_bundle": relative_under(run_dir, task_bundle),
        "model_xml": relative_under(run_dir, model_xml),
        "progress": "train/progress.json" if progress.is_file() else None,
        "receipt": "train/training-receipt.json" if receipt.is_file() else None,
        "project_docs": docs["dir"],
    }
    policy_asset = (
        relative_under(root, root / "assets" / policy_name) if policy_name else None
    )
    project_artifacts = {
        "policy": policy_asset,
        "render": (review.get("render") or {}).get("path"),
        "section": (review.get("section") or {}).get("summary_path"),
        "inventory": (review.get("inventory") or {}).get("path"),
        "clearance": (review.get("clearance") or {}).get("path"),
    }
    receipt_keys = ("sha256", "reward_per_step", "wall_time_s", "device",
                    "task_sha256", "witness_error", "parameters", "comparison",
                    "state", "run_id")
    payload: dict[str, Any] = {
        "schema": RUN_RECORD_SCHEMA,
        "run": run_dir.name,
        "recorded_at": _now(),
        "status": status,
        "error": error or None,
        "mode": mode,
        "walk_seconds": round(float(walk_seconds), 2) if walk_seconds is not None else None,
        "model": {
            "accepted_revision": accepted_revision or None,
            "digest": digest or None,
            "identity_source": identity_source or (
                "rollout leg envelope" if accepted_revision else "not reached"
            ),
        },
        "params": {
            "values": dict(params or {}),
            "specs": list(param_specs) if param_specs is not None else None,
            "specs_source": specs_source or ("unavailable" if param_specs is None else ""),
        },
        "task": {
            "bundle": artifacts["task_bundle"],
            "sha256": task_sha256 or None,
            "model_xml": artifacts["model_xml"],
        },
        "training": {
            "requested": dict(requested or {}),
            "receipt": {key: training[key] for key in receipt_keys if key in training},
        },
        "policy": {
            "name": policy_name or None,
            "sha256": policy_sha256 or None,
            "asset": policy_asset,
        },
        "rollout": {
            "trace": artifacts["trace"],
            "seed": review.get("rollout_seed",
                               (review.get("comparison") or {}).get("rollout_seed")),
            "total_reward": review.get("total_reward"),
        },
        "artifacts": artifacts,
        "project_artifacts": project_artifacts,
        "project_docs": docs,
        # The D4 slot: each entry names the video file (run-relative), the
        # checkpoint or final policy it shows by sha256, the rollout seed
        # and the simulated seconds. Empty means no video was recorded —
        # not that one is missing.
        "videos": [],
        "legs": [
            {key: value for key, value in leg.items() if key != "argv"}
            for leg in legs
        ],
    }
    path = run_dir / RUN_RECORD_FILENAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"{path.name}: {exc.__class__.__name__}: {exc}"
    if not isinstance(payload, dict):
        return None, f"{path.name}: not a JSON object"
    return payload, None


def read_accepted_identity(project_root: Path | str) -> dict[str, Any]:
    """The project's accepted revision, digest and parameter block, now.

    Read from the project manifest, read-only, and only when it says it is
    the schema this reader knows; anything else is ``available: false``
    with the reason. Reading it does not rebuild, accept or move anything.
    """

    path = Path(project_root).expanduser() / PROJECT_SCRIPT_FILENAME
    if not path.is_file():
        return {"available": False, "reason": f"no {PROJECT_SCRIPT_FILENAME}"}
    payload, error = _load_json(path)
    if payload is None:
        return {"available": False, "reason": error}
    if payload.get("schema") != PROJECT_SCRIPT_SCHEMA:
        return {"available": False,
                "reason": f"unknown manifest schema {payload.get('schema')!r}"}
    revision = payload.get("accepted_revision")
    if not revision:
        return {"available": False, "reason": "nothing accepted yet"}
    return {
        "available": True,
        "revision": str(revision),
        "digest": str(payload.get("accepted_digest") or ""),
        "working_revision": str(payload.get("working_revision") or ""),
        "updated_at": payload.get("updated_at"),
        "param_specs": list(payload.get("param_specs") or []),
        "param_values": dict(payload.get("param_values") or {}),
    }


def manifest_identity(project_root: Path | str, moment: str) -> dict[str, Any]:
    """The record fields a walk can claim from the manifest alone, at ``moment``.

    Read before any leg runs, and again before the train leg once a design
    turn or sweep has moved the accepted revision: the revision, digest and
    parameter specs the training input *is*, so the record on disk names
    them before the first telemetry sample lands and keeps them if the walk
    fails. Nothing is inferred from a manifest that is unavailable — the
    fields stay empty and ``specs_source`` says why. The keys are
    :func:`write_run_record` keyword arguments.
    """

    accepted = read_accepted_identity(project_root)
    if not accepted.get("available"):
        return {
            "accepted_revision": "", "digest": "", "identity_source": "",
            "param_specs": None,
            "specs_source": f"unavailable: project manifest {moment}: {accepted['reason']}",
        }
    return {
        "accepted_revision": accepted["revision"],
        "digest": accepted["digest"],
        "identity_source": f"project manifest ({PROJECT_SCRIPT_FILENAME}) {moment}",
        "param_specs": accepted["param_specs"],
        "specs_source": f"project manifest ({PROJECT_SCRIPT_FILENAME}) {moment}",
    }


def decision_headings(project_root: Path | str) -> list[str]:
    """The ``## ADR-…`` headings of the project's ``DECISIONS.md``, in order."""

    path = Path(project_root).expanduser() / "DECISIONS.md"
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


def _resolved(base: Path, references: Mapping[str, Any], keys: Sequence[str]) -> dict[str, Any]:
    return {key: resolve_reference(base, references.get(key)) for key in keys}


def _legacy_record(run_dir: Path, review: dict[str, Any]) -> dict[str, Any]:
    """A run from before the record existed: identity off the review's legs.

    The rollout leg's envelope fields are the only identity ``review.json``
    carries, so that is what is reported, labelled as such. Nothing else is
    inferred: no specs, no snapshot, no policy asset path.
    """

    revision = digest = None
    for leg in reversed(review.get("legs") or []):
        if isinstance(leg, Mapping) and leg.get("accepted_revision"):
            revision = leg.get("accepted_revision")
            digest = leg.get("digest")
            break
    return {
        "schema": None,
        "run": run_dir.name,
        "recorded_at": None,
        "status": "unrecorded",
        "error": None,
        "mode": None,
        "model": {
            "accepted_revision": revision, "digest": digest,
            "identity_source": "review.json legs (legacy run, no run.json)",
        },
        "params": {"values": dict(review.get("params") or {}), "specs": None,
                   "specs_source": "unavailable (legacy run)"},
        "policy": {"name": review.get("weights"), "sha256": review.get("sha256"),
                   "asset": None},
        "rollout": {"trace": review.get("trace"), "seed": None,
                    "total_reward": review.get("total_reward")},
        "artifacts": {"review": "review.json", "trace": review.get("trace")},
        "project_artifacts": {
            "render": (review.get("render") or {}).get("path"),
            "section": (review.get("section") or {}).get("summary_path"),
            "inventory": (review.get("inventory") or {}).get("path"),
            "clearance": (review.get("clearance") or {}).get("path"),
        },
        "project_docs": {"dir": None, "files": {}, "skipped": [],
                         "note": "not snapshotted (legacy run)"},
        "videos": [],
        "legs": list(review.get("legs") or []),
    }


def read_run_record(run_dir: Path | str, project_root: Path | str) -> dict[str, Any]:
    """One run, as recorded, with every reference resolved against the disk.

    Adds ``resolved`` (per artifact: path, exists, error) and ``problems``
    (the references that are recorded but missing or escaping), and marks
    a ``running`` record as ``interrupted``-looking without claiming it: the
    reader cannot tell a live walk from one that died, so it says which
    two it could be and leaves the CLI action to the caller.
    """

    directory = Path(run_dir).expanduser()
    root = Path(project_root).expanduser()
    record_path = directory / RUN_RECORD_FILENAME
    record: dict[str, Any]
    if relative_under(root, directory) is None:
        # A ``runs/<name>`` that is a symlink out of the project is not a
        # run of this project: nothing under it is opened, so it carries
        # no record, no references and no videos to resolve.
        return {"run": directory.name, "status": "unreadable",
                "error": "run directory escapes the project directory",
                "artifacts": {}, "project_artifacts": {}, "videos": [], "legs": [],
                "outcome": "record unreadable",
                "resolved": {"artifacts": {}, "project_artifacts": {}, "videos": []},
                "problems": ["run: directory escapes the project directory"]}
    if record_path.is_file():
        payload, error = _load_json(record_path)
        if payload is None:
            record = {"run": directory.name, "status": "unreadable", "error": error,
                      "artifacts": {}, "project_artifacts": {}, "videos": [], "legs": []}
        elif payload.get("schema") != RUN_RECORD_SCHEMA:
            record = {"run": directory.name, "status": "unreadable",
                      "error": f"unknown record schema {payload.get('schema')!r}",
                      "artifacts": {}, "project_artifacts": {}, "videos": [], "legs": []}
        else:
            record = payload
    elif (directory / "review.json").is_file():
        payload, error = _load_json(directory / "review.json")
        record = _legacy_record(directory, payload or {})
        if error:
            record["error"] = error
    else:
        record = {"run": directory.name, "status": "empty",
                  "error": "no run.json and no review.json", "artifacts": {},
                  "project_artifacts": {}, "videos": [], "legs": []}
    video_status = resolve_reference(directory, "video.json")
    if video_status["exists"] and not video_status["error"]:
        payload, error = _load_json(directory / "video.json")
        if payload and payload.get("schema") == "cadex-run-video-v1":
            record["video_render"] = {key: payload.get(key) for key in ("state", "error")}
            record["videos"] = payload.get("videos") or []
        else:
            record["video_render"] = {"state": "invalid", "error": error or "unsupported video status"}
    resolved = {
        "artifacts": _resolved(directory, record.get("artifacts") or {}, RUN_ARTIFACT_KEYS),
        "project_artifacts": _resolved(root, record.get("project_artifacts") or {},
                                       PROJECT_ARTIFACT_KEYS),
        "videos": [resolve_reference(directory, (video or {}).get("path"))
                   for video in record.get("videos") or []],
    }
    problems = []
    for group in ("artifacts", "project_artifacts"):
        for key, item in resolved[group].items():
            if item["path"] is None:
                continue
            if item["error"]:
                problems.append(f"{group}.{key}: {item['error']}")
            elif not item["exists"]:
                problems.append(f"{group}.{key}: missing")
    for index, item in enumerate(resolved["videos"]):
        expected = (record["videos"][index] or {}).get("sha256")
        if expected and item["exists"] and not item["error"]:
            try:
                if _video_sha256(directory / item["path"]) != expected:
                    item["error"] = "video digest mismatch"
            except OSError:
                item["error"] = "video unavailable during verification"
        if item["error"]:
            problems.append(f"videos[{index}]: {item['error']}")
        elif not item["exists"]:
            problems.append(f"videos[{index}]: missing")
    docs = record.get("project_docs") or {}
    if docs.get("dir"):
        for relative, sha in (docs.get("files") or {}).items():
            item = resolve_reference(directory, f"{docs['dir']}/{relative}")
            if item["error"] or not item["exists"]:
                problems.append(f"project_docs.{relative}: "
                                + (item["error"] or "missing"))
            elif _sha256(directory / docs["dir"] / relative) != sha:
                problems.append(f"project_docs.{relative}: digest differs from record")
    status = record.get("status")
    outcome = {
        "ok": "completed",
        "failed": "failed",
        "pending": "pending (detached training not collected)",
        "running": "started and never finished: still running, or interrupted",
        "unrecorded": "legacy run: review.json only",
        "unreadable": "record unreadable",
        "empty": "no record and no review",
    }.get(status, f"unknown status {status!r}")
    return {**record, "outcome": outcome, "resolved": resolved, "problems": problems}


def list_runs(project_root: Path | str) -> list[dict[str, Any]]:
    """Every run directory under ``runs/``, read, oldest recorded first.

    Directories with neither a record nor a review are listed as empty
    rather than skipped: a run that lost its files is a fact about the
    project, not noise.
    """

    root = Path(project_root).expanduser()
    runs_dir = root / RUNS_DIRNAME
    if not runs_dir.is_dir():
        return []
    records = [read_run_record(child, root) for child in sorted(runs_dir.iterdir())
               if child.is_dir()]
    records.sort(key=lambda record: (str(record.get("recorded_at") or ""), record["run"]))
    return records


def read_project_review(project_root: Path | str) -> dict[str, Any]:
    """The project as a reviewer sees it: accepted now, and every run then.

    Each run carries ``relation``: ``current`` when its recorded accepted
    revision is the project's accepted revision now, ``historical`` when it
    differs, ``unknown`` when either side is unavailable. A historical run
    is shown from its own record and snapshot only.
    """

    root = Path(project_root).expanduser()
    accepted = read_accepted_identity(root)
    runs = list_runs(root)
    for record in runs:
        recorded = (record.get("model") or {}).get("accepted_revision")
        if accepted.get("available") and recorded:
            record["relation"] = (
                "current" if recorded == accepted["revision"] else "historical"
            )
        else:
            record["relation"] = "unknown"
    docs = {
        name: (root / name).is_file()
        for name in ("ARCHITECTURE.md", "DECISIONS.md", "PROGRESS.md")
    }
    domain_docs = (
        sorted(path.relative_to(root).as_posix() for path in (root / "docs").glob("*.md"))
        if (root / "docs").is_dir() else []
    )
    return {
        "schema": PROJECT_REVIEW_SCHEMA,
        "project": root.name,
        "accepted": accepted,
        "docs": {**docs, "domain": domain_docs},
        "decisions": decision_headings(root),
        "runs": runs,
    }


# -- policy lineage, from retained identities and never from run names ------

POLICY_LINEAGE_SCHEMA = "cadex-policy-lineage-v1"
POLICY_FILE_LIMIT_BYTES = 4 * 1024 * 1024


def _retained_policies(root: Path) -> dict[str, list[dict[str, Any]]]:
    """Every policy digest some run retains as bytes under its own ``train/``.

    A training run keeps what it produced — its final policy and the
    checkpoints its telemetry lists — beside its telemetry; a playback run
    copies the telemetry snapshot but not the bytes. So the run whose
    ``train/`` holds a file with a policy's digest is the run that made it,
    whatever either run is called. Files over ``POLICY_FILE_LIMIT_BYTES``
    and anything that is not a regular file inside ``runs/<run>/train`` are
    skipped: this is an identity index, not a directory listing.

    Every path is resolved against the **project root**, never against the
    run directory it sits in: a ``runs/<name>`` that is itself a symlink out
    of the project would pass a check anchored at that already-escaped
    directory, so the run, its ``train/`` and each file in it are each
    required to resolve inside the project before anything is hashed — and
    a file must also resolve inside that run's own ``train/``, because a
    symlink to bytes kept elsewhere in the project is not this run
    retaining them.
    """

    index: dict[str, list[dict[str, Any]]] = {}
    root = root.expanduser()
    runs_dir = root / RUNS_DIRNAME
    if not runs_dir.is_dir():
        return index
    for run_dir in sorted(child for child in runs_dir.iterdir() if child.is_dir()):
        train_reference = f"{RUNS_DIRNAME}/{run_dir.name}/train"
        train = resolve_reference(root, train_reference)
        if train["error"] or not train["exists"] or not (run_dir / "train").is_dir():
            continue
        train_dir = (run_dir / "train").resolve()
        for path in sorted((run_dir / "train").iterdir()):
            ref = resolve_reference(root, f"{train_reference}/{path.name}")
            if ref["error"] or not path.is_file() or path.name == "progress.json":
                continue
            if relative_under(train_dir, path) is None:
                continue
            try:
                if path.stat().st_size > POLICY_FILE_LIMIT_BYTES:
                    continue
                digest = _sha256(path)
            except OSError:
                continue
            index.setdefault(digest, []).append({"run": run_dir.name, "path": path.name})
    return index


def _retained_progress(root: Path, run_name: str) -> dict[str, Any] | None:
    """A run's own telemetry, read only when ``runs/<run>/train/progress.json``
    resolves inside the project and inside that run's own ``train/``; a
    symlink out of either is never opened."""

    reference = f"{RUNS_DIRNAME}/{run_name}/train/progress.json"
    ref = resolve_reference(root, reference)
    if ref["error"] or not ref["exists"]:
        return None
    if relative_under((root / RUNS_DIRNAME / run_name / "train").resolve(), root / reference) is None:
        return None
    progress, _ = _load_json(root / reference)
    return progress


def _origin(root: Path, records: Mapping[str, Mapping[str, Any]], index: Mapping[str, list[dict[str, Any]]],
            digest: str | None) -> tuple[dict[str, Any] | None, str]:
    """The run that retains ``digest``'s bytes, and how it names them.

    ``kind`` is ``final`` when that run's own record carries the digest as
    its policy, ``checkpoint`` (with the iteration) when its telemetry lists
    it, and ``retained`` when the bytes are there but neither says so. Two
    runs retaining the same bytes is reported, with the earliest recorded
    taken as the origin: a later copy of the bytes is derivative.
    """

    if not digest:
        return None, "no policy recorded for this run"
    holders = index.get(digest) or []
    if not holders:
        return None, "no run in this project retains a policy with this digest under its train/"
    candidates = []
    for holder in holders:
        record = records.get(holder["run"]) or {}
        kind, iteration = "retained", None
        if ((record.get("policy") or {}).get("sha256")) == digest:
            kind = "final"
        progress = _retained_progress(root, holder["run"])
        for item in (progress or {}).get("checkpoints") or []:
            if isinstance(item, Mapping) and item.get("sha256") == digest and item.get("path") == holder["path"]:
                kind, iteration = "checkpoint", item.get("iteration")
        candidates.append({"run": holder["run"], "path": holder["path"], "kind": kind, "iteration": iteration,
                           "recorded_at": record.get("recorded_at")})
    candidates.sort(key=lambda item: (str(item["recorded_at"] or ""), item["run"]))
    origin = dict(candidates[0])
    origin["also_retained_by"] = [item["run"] for item in candidates[1:]]
    reason = f"{origin['kind']} policy retained by run {origin['run']} as train/{origin['path']}"
    return origin, reason


def policy_lineage(project_root: Path | str, run_name: str) -> dict[str, Any]:
    """Where a run's policy came from, and which other runs play it — from
    retained identities, never from how anyone named the runs.

    A run's ``policy.sha256`` is matched against the bytes every run keeps
    under its own ``train/`` (``_retained_policies``). The run's recorded
    ``training.requested.source_run`` is reported beside that match, and
    ``source_agrees`` says whether the name the record kept and the bytes
    agree: ``None`` when no source was recorded (a walk that trained and
    rolled out in one run names none), ``False`` when the record names one
    run and carries another's policy — a fact to show, not to reconcile.
    ``playbacks`` is every *other* run whose policy the same origin run
    retains, each with its own kind, relation and video count, so a checker
    can pick an older sibling of this run without a naming convention.
    This walks and hashes ``runs/*/train`` once per call; it is a reader
    for checkers, reports and explicit dashboard origin checks, never polling.
    """

    root = Path(project_root).expanduser()
    review = read_project_review(root)
    records = {record["run"]: record for record in review["runs"]}
    result: dict[str, Any] = {"schema": POLICY_LINEAGE_SCHEMA, "run": run_name, "policy_sha256": None,
                              "origin": None, "reason": None, "recorded_source_run": None,
                              "source_agrees": None, "playbacks": []}
    record = records.get(run_name)
    if record is None:
        result["reason"] = f"run {run_name!r} is not in this project"
        return result
    digest = (record.get("policy") or {}).get("sha256")
    result["policy_sha256"] = digest if isinstance(digest, str) and digest else None
    requested = (record.get("training") or {}).get("requested") or {}
    source = requested.get("source_run") if isinstance(requested, Mapping) else None
    result["recorded_source_run"] = source if isinstance(source, str) and source else None
    index = _retained_policies(root)
    origin, reason = _origin(root, records, index, result["policy_sha256"])
    result["origin"], result["reason"] = origin, reason
    if origin is not None and result["recorded_source_run"] is not None:
        result["source_agrees"] = origin["run"] == result["recorded_source_run"]
    if origin is None:
        return result
    for other in review["runs"]:
        if other["run"] == run_name:
            continue
        other_origin, _ = _origin(root, records, index, (other.get("policy") or {}).get("sha256"))
        if other_origin is None or other_origin["run"] != origin["run"] or other["run"] == origin["run"]:
            continue
        result["playbacks"].append({"run": other["run"], "kind": other_origin["kind"],
                                    "iteration": other_origin["iteration"], "path": other_origin["path"],
                                    "recorded_at": other.get("recorded_at"), "relation": other.get("relation"),
                                    "status": other.get("status"), "videos": len(other.get("videos") or [])})
    return result
