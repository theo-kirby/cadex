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
import os
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
#: ``artifacts.policy`` is the trainer's own output under the run's
#: ``train/``; ``project_artifacts.policy`` is the project-store copy, and is
#: named only when the store held it, with the recorded digest, at record
#: time (ADR-326). A named locator is a fact, never an intention.
RUN_ARTIFACT_KEYS = ("script", "review", "trace", "task_bundle", "model_xml",
                     "progress", "receipt", "project_docs", "policy")
PROJECT_ARTIFACT_KEYS = ("policy", "render", "section", "inventory", "clearance")
#: The largest policy file whose digest the reader will verify against the
#: store, the same bound the lineage check uses on retained training bytes.
POLICY_DIGEST_LIMIT_BYTES = 4 * 1024 * 1024


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


_policy_verification_lock = threading.Lock()


@lru_cache(maxsize=256)
def _cached_policy_sha256(path: Path, stamp: tuple[int, ...]) -> str:
    return _sha256(path)


def _policy_sha256(path: Path) -> str:
    """The video check's stamp-keyed cache, for policy files, on a lock of
    its own: the store check runs on every poll of every run, and a cold
    hash of one large video must not stall it (ADR-326)."""

    path = path.resolve()
    with _policy_verification_lock:
        stamp = _video_stamp(path)
        digest = _cached_policy_sha256(path, stamp)
    if _video_stamp(path) != stamp:
        raise OSError("policy changed during verification")
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
    policy_asset = stored_policy_asset(root, policy_name, policy_sha256)
    artifacts["policy"] = (
        relative_under(run_dir, train_dir / policy_name)
        if policy_name and (train_dir / policy_name).is_file() else None
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


def stored_policy_asset(project_root: Path | str, policy_name: str,
                        policy_sha256: str = "") -> str | None:
    """``assets/<name>`` when the project store holds it now, else ``None``.

    The store copy is a ``cadex asset --put`` (or a train leg's ``--put``)
    the walk makes before it records; a bounded driver, or a walk that
    failed between training and storing, has no such copy, and its record
    must not name one (ADR-326). With ``policy_sha256`` given, a stored
    file holding different bytes is not the policy either.
    """

    if not policy_name:
        return None
    root = Path(project_root).expanduser()
    stored = root / "assets" / policy_name
    relative = relative_under(root, stored)
    if relative is None or not stored.is_file():
        return None
    if policy_sha256 and _sha256(stored) != policy_sha256:
        return None
    return relative


def policy_store(project_root: Path | str, record: Mapping[str, Any],
                 resolved: Mapping[str, Any]) -> dict[str, Any]:
    """Where a run's policy bytes are **now**, and the CLI action that follows.

    ``state`` is ``stored`` (the project store holds ``assets/<name>`` with
    the recorded digest, whether or not the record named it — a later
    ``cadex asset --put`` counts), ``digest mismatch`` (the store holds
    other bytes under that name), ``unstored`` (no store copy; the record
    may have named one that is gone, and ``problems`` says so), ``refused``
    (the recorded locator escapes the project) or ``none`` (no policy
    recorded). ``retained`` is the run-relative path of the trainer's own
    copy when it is on disk; ``next_action`` stores it when it is, and
    starts a new attempt when it is not. Digests are verified on files up
    to ``POLICY_DIGEST_LIMIT_BYTES`` through a stamp-keyed cache of their
    own, so a polled page never re-hashes an unchanged file and never
    waits behind a video verification. ``store_command`` is the one
    command that puts the retained copy in the store — bare, for a caller
    that needs the action without the alternatives — and is ``None`` when
    the policy is stored or nothing is retained. The store command names
    the project directory twice, as ``<project-dir>``: ``--put`` resolves
    against the working directory and ``--project`` defaults to ``./.cadex``,
    so a bare ``cadex asset --put runs/…`` run from the project directory
    creates a nested project instead of storing into this one.
    """

    root = Path(project_root).expanduser()
    run = str(record.get("run") or "")
    policy = record.get("policy") or {}
    name = str(policy.get("name") or "")
    sha256 = str(policy.get("sha256") or "")
    result: dict[str, Any] = {"state": "none", "name": name or None, "asset": None,
                              "retained": None, "reason": "no policy recorded",
                              "next_action": None, "store_command": None}
    if not name:
        return result
    trained = (resolved.get("artifacts") or {}).get("policy") or {}
    retained = trained.get("path") if trained.get("exists") and not trained.get("error") else None
    result["retained"] = retained
    new_attempt = "start a new attempt: cadex walk --out runs/<new-name>"
    # ``--put`` resolves against the working directory and ``--project``
    # defaults to ``./.cadex``, so both name the project directory
    # explicitly: run from anywhere, and never a nested project by accident.
    put = (f"cadex asset --project <project-dir> --put <project-dir>/runs/{run}/{retained}"
           if retained else "")
    keep = (f"store it: {put} · or {new_attempt}" if retained
            else f"the trainer's copy is not retained in this run; {new_attempt}")
    result["next_action"] = keep
    result["store_command"] = put or None
    recorded = (resolved.get("project_artifacts") or {}).get("policy") or {}
    if recorded.get("path") is not None and recorded.get("error"):
        result.update(state="refused",
                      reason="recorded store locator " + str(recorded["error"]))
        return result
    stored = root / "assets" / name
    if Path(name).name == name and relative_under(root, stored) and stored.is_file():
        digest = None
        try:
            if stored.stat().st_size <= POLICY_DIGEST_LIMIT_BYTES:
                digest = _policy_sha256(stored)
        except OSError:
            digest = None
        if digest is not None and (not sha256 or digest == sha256):
            result.update(state="stored", asset=f"assets/{name}", next_action=None, store_command=None,
                          reason="the project store holds this policy"
                                 + (" with the recorded digest" if sha256
                                    else "'s name; no digest was recorded to check it against"))
            return result
        result.update(state="digest mismatch",
                      reason=(f"assets/{name} holds different bytes than this run's policy"
                              if digest is not None else f"assets/{name} could not be verified"),
                      next_action=(f"store it under another name: {put} --name <other>.cxpolicy"
                                   if retained else keep),
                      store_command=f"{put} --name <other>.cxpolicy" if retained else None)
        return result
    result.update(state="unstored",
                  reason=(f"the record named {recorded['path']} but the project store does not hold it"
                          if recorded.get("path") else
                          "never stored as a project asset (no cadex asset --put ran for it)"))
    return result


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
    (the references that are recorded but missing or escaping, and — for a
    completed run — a policy the trainer retained that the project store
    does not hold, with the command that stores it: an ``ok`` run whose
    result lives only under its own ``train/`` is a retention gap, not a
    finished run, ADR-327), and marks a ``running`` record as
    ``interrupted``-looking without claiming it: the reader cannot tell a
    live walk from one that died, so it says which two it could be and
    leaves the CLI action to the caller.
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
    artifacts = dict(record.get("artifacts") or {})
    policy_name = str((record.get("policy") or {}).get("name") or "")
    if "policy" not in artifacts and policy_name and Path(policy_name).name == policy_name:
        # A record from before ADR-326 named no run-local policy; the
        # trainer's output has one fixed location, the same one
        # ``train/progress.json`` is read from, so it is resolved there
        # when — and only when — it exists.
        trained = resolve_reference(directory, f"train/{policy_name}")
        if trained["exists"] and not trained["error"]:
            artifacts["policy"] = trained["path"]
    resolved = {
        "artifacts": _resolved(directory, artifacts, RUN_ARTIFACT_KEYS),
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
    store = policy_store(root, record, resolved)
    if status == "ok" and store["store_command"]:
        problems.append(f"policy_store: {store['state']} — this completed run's policy "
                        f"{store['name']} is retained at {store['retained']} but the project "
                        f"store does not hold it; store it: {store['store_command']}")
    return {**record, "outcome": outcome, "resolved": resolved, "problems": problems,
            "policy_store": store}


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


# -- disk use, per run, from permitted project-local files only --------------

DISK_USE_SCHEMA = "cadex-run-disk-use-v1"
#: Directory entries one run's count will visit before it stops and says
#: ``truncated``: a run directory is a few hundred files at most, and a
#: reader that finds tens of thousands reports the bound rather than the
#: whole tree.
DISK_USE_ENTRY_LIMIT = 20_000
#: How many skipped entries are listed by path; the rest are counted.
DISK_USE_SKIPPED_LISTED = 32


def _walk_counted(top: Path, base: Path, budget: list[int], seen: set[tuple[int, int]],
                  skipped: list[dict[str, str]], counts: dict[str, int]) -> None:
    """Sum regular files under ``top`` that resolve inside ``base``, each inode
    once. Symlinks are never followed: a linked file or directory is listed
    as skipped, because bytes kept elsewhere are not this run retaining
    them. ``budget[0]`` is the remaining entry allowance; ``counts`` gains
    ``bytes``, ``files``, ``hardlinked_entries`` and ``skipped_count``."""

    pending = [top]
    while pending:
        if budget[0] <= 0:
            counts["truncated"] = 1
            return
        directory = pending.pop()
        try:
            entries = os.scandir(directory)
        except OSError as exc:
            counts["skipped_count"] += 1
            if len(skipped) < DISK_USE_SKIPPED_LISTED:
                skipped.append({"path": relative_under(base, directory) or directory.name,
                                "reason": f"unreadable: {exc.__class__.__name__}"})
            continue
        with entries:
            while True:
                # Do not enumerate one more entry to discover whether the
                # directory ends exactly at the limit: conservatively a floor.
                if budget[0] <= 0:
                    counts["truncated"] = 1
                    return
                try:
                    entry = next(entries)
                except StopIteration:
                    break
                budget[0] -= 1
                relative = relative_under(base, Path(entry.path)) if not entry.is_symlink() else None
                if entry.is_symlink() or relative is None:
                    counts["skipped_count"] += 1
                    if len(skipped) < DISK_USE_SKIPPED_LISTED:
                        shown = os.path.relpath(entry.path, base)
                        skipped.append({"path": shown.replace(os.sep, "/"),
                                        "reason": "symlink not followed" if entry.is_symlink() else "escapes the run directory"})
                    continue
                if entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
                try:
                    stat = entry.stat(follow_symlinks=False)
                except OSError:
                    counts["skipped_count"] += 1
                    if len(skipped) < DISK_USE_SKIPPED_LISTED:
                        skipped.append({"path": relative, "reason": "unreadable"})
                    continue
                key = (stat.st_dev, stat.st_ino)
                if key in seen:
                    counts["hardlinked_entries"] += 1
                    continue
                seen.add(key)
                counts["bytes"] += stat.st_size
                counts["files"] += 1
                head = relative.split("/", 1)[0] if "/" in relative else "."
                by_dir = counts.setdefault("by_dir", {}).setdefault(head, {"bytes": 0, "files": 0})
                by_dir["bytes"] += stat.st_size
                by_dir["files"] += 1


def _reference_size(base: Path, item: Mapping[str, Any], budget: list[int]) -> dict[str, Any]:
    """Bytes of one resolved reference: a file's size, or a directory's
    counted files. A reference the reader refused is never opened; a
    missing one has no size."""

    if item.get("path") is None:
        return {"path": None, "status": "not recorded", "bytes": None, "files": 0}
    if item.get("error"):
        return {"path": item["path"], "status": "refused", "bytes": None, "files": 0, "reason": item["error"]}
    if not item.get("exists"):
        return {"path": item["path"], "status": "missing", "bytes": None, "files": 0}
    target = base / item["path"]
    try:
        if target.is_dir():
            counts = {"bytes": 0, "files": 0, "hardlinked_entries": 0, "skipped_count": 0}
            _walk_counted(target, base, budget, set(), [], counts)
            return {"path": item["path"], "status": "truncated" if counts.get("truncated") else "retained",
                    "lower_bound": bool(counts.get("truncated") or counts["skipped_count"]),
                    "bytes": counts["bytes"], "files": counts["files"]}
        stat = target.stat()
    except OSError as exc:
        return {"path": item["path"], "status": "missing", "bytes": None, "files": 0,
                "reason": f"unreadable: {exc.__class__.__name__}"}
    return {"path": item["path"], "status": "retained", "bytes": stat.st_size, "files": 1}


def run_disk_use(project_root: Path | str, record: Mapping[str, Any],
                 others: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """What one run keeps on disk, from permitted project-local files only.

    ``bytes``/``files`` count every regular file under ``runs/<run>`` that
    resolves inside it, each inode once (a hard-linked pair is one file and
    one ``hardlinked_entries``), with nothing followed through a symlink —
    linked entries are listed under ``skipped`` with the reason. ``by_dir``
    splits that by the run's top-level subdirectories (``.`` for files at
    its root). ``references`` sizes each reference the record names, with
    status words: ``retained`` (with bytes), ``truncated`` (a floor),
    ``missing`` (no bytes), ``refused`` (never opened) or ``not recorded``.
    A project-level reference (``project_artifacts``) that resolves outside
    this run's directory is **not** in the run total: it is sized under
    ``shared_bytes`` and, when other runs' records name the same path,
    ``shared_with`` lists them, so a policy asset two runs share is counted
    once however many runs cite it. ``state`` is ``counted``, ``truncated``
    (the walk hit ``DISK_USE_ENTRY_LIMIT`` and the totals are a floor) or
    ``unreadable`` (the run directory is missing or escapes the project,
    and nothing under it was stat'ed). Only ``stat`` is read: no file
    bytes, no hashing, with one entry budget shared by the run walk and all
    directory references.
    Reference ``truncated`` sizes and ``lower_bound`` sizes are floors, as is
    ``shared_bytes`` when ``shared_lower_bound`` is true.
    """

    root = Path(project_root).expanduser()
    name = str(record.get("run"))
    result: dict[str, Any] = {
        "schema": DISK_USE_SCHEMA, "run": name, "state": "unreadable", "reason": None,
        "bytes": 0, "files": 0, "hardlinked_entries": 0, "skipped_count": 0, "skipped": [],
        "by_dir": {}, "references": {"artifacts": {}, "project_artifacts": {}, "videos": [],
                                     "project_docs": None},
        "shared_bytes": 0, "shared_lower_bound": False, "entry_limit": DISK_USE_ENTRY_LIMIT,
    }
    run_ref = resolve_reference(root, f"{RUNS_DIRNAME}/{name}")
    if run_ref["error"] or not run_ref["exists"]:
        result["reason"] = ("run directory escapes the project directory" if run_ref["error"]
                            else "run directory missing")
        return result
    run_dir = root / RUNS_DIRNAME / name
    if not run_dir.is_dir():
        result["reason"] = "run directory is not a directory"
        return result
    seen: set[tuple[int, int]] = set()
    counts = {"bytes": 0, "files": 0, "hardlinked_entries": 0, "skipped_count": 0}
    budget = [DISK_USE_ENTRY_LIMIT]
    _walk_counted(run_dir, run_dir, budget, seen, result["skipped"], counts)
    result["by_dir"] = counts.pop("by_dir", {})
    truncated = bool(counts.pop("truncated", 0))
    result.update(counts)
    result["state"] = "truncated" if truncated else "counted"
    result["reason"] = (f"stopped after {DISK_USE_ENTRY_LIMIT} directory entries; totals are a floor"
                        if truncated else None)
    resolved = record.get("resolved") or {}
    for key, item in (resolved.get("artifacts") or {}).items():
        sized = _reference_size(run_dir, item, budget)
        sized["in_run"] = True
        result["references"]["artifacts"][key] = sized
    run_real = run_dir.resolve()
    cited: dict[str, list[str]] = {}
    for other in others:
        if str(other.get("run")) == name:
            continue
        for value in ((other.get("resolved") or {}).get("project_artifacts") or {}).values():
            if isinstance(value, Mapping) and value.get("exists") and not value.get("error"):
                cited.setdefault(str(value["path"]), []).append(str(other.get("run")))
    for key, item in (resolved.get("project_artifacts") or {}).items():
        sized = _reference_size(root, item, budget)
        in_run = False
        if sized["status"] in {"retained", "truncated"}:
            in_run = relative_under(run_real, root / item["path"]) is not None
            if not in_run:
                result["shared_bytes"] += sized["bytes"]
                if sized.get("lower_bound"):
                    result["shared_lower_bound"] = True
        sized["in_run"] = in_run
        sized["shared_with"] = sorted(set(cited.get(str(item.get("path")), []))) if item.get("path") else []
        result["references"]["project_artifacts"][key] = sized
    for index, item in enumerate(resolved.get("videos") or []):
        sized = _reference_size(run_dir, item, budget)
        sized["in_run"] = True
        sized["index"] = index
        result["references"]["videos"].append(sized)
    docs = record.get("project_docs") or {}
    if docs.get("dir"):
        item = resolve_reference(run_dir, docs["dir"])
        sized = _reference_size(run_dir, item, budget)
        sized["in_run"] = True
        result["references"]["project_docs"] = sized
    result["entries_visited"] = DISK_USE_ENTRY_LIMIT - budget[0]
    return result


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
