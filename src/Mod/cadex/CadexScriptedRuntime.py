# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Asynchronous lifecycle for THE project xscript script (Phase 2.4).

One project script is the sole mutation surface. The session captures bounded
state on the document thread, persists the working script, executes it in a
sandboxed FreeCADCmd worker, validates the detached result off-thread, then
publishes once with detached values (see CadexScriptedDomainPublication).

The per-domain multi-program lifecycle (its tool surface, manifests,
host-side per-domain validators, and the domain adapter registry) was removed
with the Phase 2.4 tool-surface swap (docs/DECISIONS.md ADR-013).
"""

from __future__ import annotations

import ast
import hashlib
import inspect as _inspect
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
from typing import Any, Callable, Mapping
import uuid

from CadexTools import tool_failure
import CadexScriptedDomains as contracts
from cadex_domain_api import create_domain_api

#: How many threads a worker's BLAS may build a scratch pool for. Not a speed
#: knob -- an address-space one; see ``worker_environment``.
WORKER_BLAS_THREADS = 4

# Worker attempts are deliberately self-contained. The project bundle stages
# every capability domain plus the shared domain-worker helpers; the project
# entry module replaces cadex_domain_worker as the staged worker.py (see
# _stage_worker_bundle).
_DOMAIN_WORKER_BUNDLES: dict[str, tuple[str, ...]] = {
    "project": (
        "cadex_domain_worker.py",
        "CadexSubshapeQuery.py",
        # The digest material (ADR-389). In the bundle *and* in cadexd's
        # closure, which is CadexNets' standing exactly: the project worker
        # hashes an accepted run with it, and the service re-measures a
        # retained one with it when the bytes disagree. Pure at module scope
        # -- `Part` is imported inside the one function that needs a kernel.
        "CadexGeometryDigest.py",
        "cadex_project_api.py",
        "cadex_sketcher_api.py",
        "cadex_sketcher_worker.py",
        "cadex_part_api.py",
        "cadex_part_worker.py",
        # The linear-elastic solve (ADR-145). Staged by filename and never
        # imported by cadexd, for the reason CadexDynamics is: numpy and
        # scipy are in the payload already, but a service whose job is
        # reading NDJSON off a pipe should not import them to discover it.
        # `DECLARED_ENGINE_MODULES` does not name it, and
        # test_engine_purity_guardrails asserts it stays that way.
        "CadexStress.py",
        # The wire router (ADR-056). Staged like every other worker module —
        # by filename, not imported — so cadex_part_worker can import it
        # inside the sandbox.
        "CadexRouting.py",
        # The multi-conductor lay (ADR-057). Staged the same way, for the same
        # reason: cadex_part_worker imports it inside the sandbox.
        "CadexBundle.py",
        # Named, geometry-anchored ports (ADR-062). Imported by both the part
        # api and the part worker inside the sandbox, so it stages like the
        # two above it.
        "CadexTerminals.py",
        # The joint a terminal implies (ADR-063). Imported by the part worker
        # inside the sandbox, like the three above it.
        "CadexSolder.py",
        # The connection table (ADR-065). Imported by the project worker
        # inside the sandbox to stage nets()/wire(), and by the host to
        # validate a stored row list — pure either side, like the four above.
        "CadexNets.py",
        # The board table (ADR-120), staged for exactly CadexNets' reasons:
        # the project worker imports it inside the sandbox to stage
        # boards()/board()/term(), and the host imports it to validate a
        # stored row list. Pure on both sides.
        "CadexBoards.py",
        # The mount table (ADR-126). Staged for CadexBoards' reasons exactly:
        # the project worker imports it inside the sandbox to stage
        # mounts()/mount_set()/mount(), the part api and worker import it for
        # part.mate, and the host imports it to validate a stored row list.
        "CadexMounts.py",
        # The section cage (ADR-127). Staged for CadexMounts' reasons: the
        # project worker imports it to stage cage()/section_cage()/ring(),
        # the part api and worker import it for part.loft_cage, and the host
        # imports it to validate a stored row list.
        "CadexCage.py",
        # The linked-part container (ADR-138). Staged for CadexCage's reasons
        # exactly: the part worker imports it inside the sandbox to read one
        # `.cxpart` back into an OCCT solid, and the host imports it to build
        # one out of another project's accepted attempt. Pure on both sides.
        "CadexLinkedPart.py",
        "cadex_partdesign_api.py",
        "cadex_partdesign_worker.py",
        "cadex_mesh_api.py",
        "cadex_mesh_worker.py",
        "CadexScriptedProcess.py",
        "cadex_assembly_api.py",
        "cadex_assembly_worker.py",
        # The MuJoCo translator (ADR-077). Staged by filename for the same
        # reason as CadexRouting, plus one of its own: it is the only module
        # in the tree that imports mujoco, and the engine's import closure is
        # asserted to equal DECLARED_ENGINE_MODULES exactly. Reachable from
        # the sandboxed worker, never from cadexd.
        "CadexDynamics.py",
        # The behaviour metrics and the vocabulary a success spec may name
        # (ADR-455, ADR-456). Staged beside CadexDynamics because that is
        # what imports it, when a task declares a spec; pure standard
        # library, and like CadexDynamics never imported by cadexd.
        "CadexEvaluation.py",
        "cadex_tessellation.py",
        # The resident preview worker's entry (ADR-055). In the bundle rather
        # than beside cadexd because it runs inside the same --safe-mode
        # sandbox as everything else here, out of the same content-addressed
        # directory, and must never be importable by the service.
        "cadex_preview_worker.py",
    ),
}

#: Mesh assets stageable into the isolated worker (mesh.import_file).
#:
#: These are the mesh formats ``mesh.import_file`` reads. Other stageable
#: kinds (a policy, its provenance, a linked part) are added in the union
#: below rather than here, which is why M7 needed no new op (ADR-084). The
#: Blender shell once mirrored this set, so it was held at three; that
#: reason left with the shell (ADR-498).
_ASSET_SUFFIXES = frozenset({".stl", ".obj", ".ply"})

#: Trained control policies (ADR-084). A separate constant rather than three
#: more members above, so that "what mesh.import_file reads" and "what the
#: project store holds" stay two questions with two answers.
_POLICY_ASSET_SUFFIXES = frozenset({".cxpolicy"})

#: What a policy **travels with** (ADR-135): the task bundle it was trained on
#: and the MJCF that bundle references, which are what
#: ``assembly.policy(..., trained_task=)`` binds it to and compares against.
#:
#: A third constant rather than two more members above, for the reason there is
#: a second one: "what ``mesh.import_file`` reads", "what a trained policy
#: arrives in" and "what a policy's provenance travels as" are three questions
#: with three answers, and a single widened set would make all three unreadable.
#:
#: These two are the only *generic* suffixes the store holds, and that is
#: deliberately not a problem: neither is interpreted on arrival. A ``.json``
#: is read only when a script names it as ``trained_task``, and a ``.xml`` only
#: when its digest matches the one that bundle records. An asset nothing names
#: is bytes in a directory.
_PROVENANCE_ASSET_SUFFIXES = frozenset({".json", ".xml"})

#: A part built in another project (ADR-138): one exact OCCT solid, the
#: script that made it, and where it came from, in one content-addressed
#: file that ``part.import_part`` reads.
#:
#: A **fourth** constant rather than one more member above, for the reason
#: there is a third. What ``mesh.import_file`` reads, what a trained policy
#: arrives in, what that policy's provenance travels as, and what one project
#: hands to another are four questions with four answers, and the union below
#: is the only place they have to be one.
_LINKED_PART_ASSET_SUFFIXES = frozenset({".cxpart"})

#: Everything the store accepts, stages and lists. ``put_asset`` and
#: ``import_geometry`` perform no suffix check of their own -- they pass the
#: path through and let the engine refuse -- so widening this is the whole of
#: what it takes for a policy to reach the store through the tool that
#: already exists.
_STORED_ASSET_SUFFIXES = (
    _ASSET_SUFFIXES
    | _POLICY_ASSET_SUFFIXES
    | _PROVENANCE_ASSET_SUFFIXES
    | _LINKED_PART_ASSET_SUFFIXES
)

_MAX_ASSET_FILES = 64
_MAX_ASSET_BYTES = 128 * 1024 * 1024


class DomainRuntimeFailure(RuntimeError):
    def __init__(self, payload: Mapping[str, Any]):
        self.payload = dict(payload)
        super().__init__(str(self.payload.get("error") or "XScript domain failure."))


def _failure(
    tool_name: str,
    code: str,
    stage: str,
    message: str,
    **details: Any,
) -> dict[str, Any]:
    return tool_failure(
        tool_name,
        code,
        stage,
        message,
        requested=dict(details.pop("requested", {}) or {}),
        observed=dict(details.pop("observed", {}) or {}),
        **details,
    )


def _raise(
    tool_name: str,
    code: str,
    stage: str,
    message: str,
    **details: Any,
) -> None:
    raise DomainRuntimeFailure(_failure(tool_name, code, stage, message, **details))


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(
                dict(payload),
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ),
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Could not read {label} at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} at {path} must contain one JSON object.")
    return value


#: Where shared worker bundles live. Outside the project store on purpose:
#: they are a function of the *engine build*, not of any project, and a
#: per-project copy is what made this cost 608 KB and 16 ``compile()`` calls
#: on every single request.
_BUNDLE_CACHE_DIRNAME = "cadex-worker-bundles"


def _bundle_members(domain: str) -> tuple[str, tuple[str, ...]]:
    """``(entry_module, filenames)`` for one domain's isolated worker."""

    clean_domain = str(domain or "").strip().lower()
    domain_files = _DOMAIN_WORKER_BUNDLES.get(clean_domain)
    if domain_files is None:
        raise ValueError(
            f"XScript domain {clean_domain!r} has no isolated worker bundle."
        )
    filenames = ("cadex_domain_api.py", *domain_files)
    if len(filenames) != len(set(filenames)):
        raise RuntimeError(
            f"XScript domain {clean_domain!r} has duplicate worker dependencies."
        )
    entry_module = (
        "cadex_project_worker.py" if clean_domain == "project"
        else "cadex_domain_worker.py"
    )
    return entry_module, filenames


#: Bundle digests whose members have already been checked against each other.
#: The check is a function of the bytes, so the digest that keys the bundle
#: directory keys the check too, and a warm cache pays nothing for it.
_CHECKED_BUNDLE_DIGESTS: set[str] = set()


def _top_level_imports(source: bytes) -> set[str]:
    """Top-level module names one staged member imports at module scope.

    Only module scope, and only absolute imports: a member that imports a
    sibling inside a function (``CadexRouting`` in ``cadex_part_worker``, and
    the kernel in ``CadexGeometryDigest``) is not asking for it at import
    time, which is the only moment this guard is about.
    """

    try:
        tree = ast.parse(source)
    except SyntaxError:
        # It will fail on import with a better message than this guard's.
        return set()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def _unstaged_member_imports(
    module_root: Path, snapshot: Mapping[str, bytes]
) -> list[tuple[str, str]]:
    """``(member, module)`` pairs a bundle would fail to import.

    An engine module that lives beside the bundle's members, is imported by
    one of them at module scope, and is not itself a member. There is no such
    pair in a consistent engine, and the one way to make one is the one that
    cost F7 a frozen create prompt: the member *list* is read from
    ``_DOMAIN_WORKER_BUNDLES`` once, when the service imports this module,
    while the member *bytes* are read from disk on every cache miss. Edit the
    tree under a live ``cadexd`` and the two disagree -- a new worker naming a
    module the old list never staged. The bundle that results is keyed by the
    bytes of what it does hold, so it publishes cleanly, caches, and then
    fails identically on every attempt for the life of the session.
    """

    return sorted(
        (member, name)
        for member, data in snapshot.items()
        for name in _top_level_imports(data)
        if f"{name}.py" not in snapshot and (module_root / f"{name}.py").is_file()
    )


def _link_or_copy(source: Path, target: Path) -> None:
    """Hardlink, falling back to a copy that preserves mtime.

    The mtime matters and is the whole point: ``__pycache__`` validates a
    cached bytecode file against its source's mtime and size, so a
    ``shutil.copyfile`` (which does *not* preserve mtime) would invalidate
    the cache on every rebuild and the compile would come straight back.
    ``PYTHONPYCACHEPREFIX`` alone would not have fixed that either.
    """

    try:
        os.link(source, target)
    except OSError:
        # Different filesystem, or a platform without hardlinks.
        shutil.copy2(source, target)


def shared_worker_bundle(module_root: Path, domain: str) -> tuple[Path, str]:
    """The content-addressed bundle directory for one domain. Built once.

    Returns ``(bundle_dir, entry_module_name)``. Keyed by the bytes of every
    member, read once and staged from those same bytes. Reuse validates
    detached members against that snapshot; identical content retains the
    ``__pycache__`` next to it.

    Built atomically -- populated under ``.tmp-<uuid>`` and ``os.replace``d
    into place -- so two workers racing on the same bundle cannot read a
    half-populated directory.
    """

    entry_module, filenames = _bundle_members(domain)
    members = (entry_module, *filenames)

    snapshot = {}
    digest = hashlib.sha256()
    for name in sorted(set(members)):
        source = module_root / name
        if source.parent != module_root or not source.is_file():
            raise RuntimeError(
                f"Required XScript worker dependency {name!r} is missing."
            )
        data = source.read_bytes()
        snapshot[name] = data
        digest.update(name.encode("utf-8"))
        digest.update(str(len(data)).encode("ascii"))
        digest.update(data)

    clean_domain = str(domain or "").strip().lower()
    root = Path(tempfile.gettempdir()) / _BUNDLE_CACHE_DIRNAME
    fingerprint = digest.hexdigest()
    # Before publishing, and before trusting a cache hit: a bundle whose own
    # members cannot import each other must never become a directory. It would
    # be keyed by the bytes it holds, so it would cache, and every retry in the
    # session would recompute the same key and fail the same way.
    if fingerprint not in _CHECKED_BUNDLE_DIGESTS:
        unstaged = _unstaged_member_imports(module_root, snapshot)
        if unstaged:
            raise RuntimeError(
                f"The {clean_domain!r} XScript worker bundle cannot import "
                "itself: "
                + ", ".join(f"{member} imports {name}" for member, name in unstaged)
                + ", and "
                + ", ".join(f"{name}.py" for name in sorted({n for _, n in unstaged}))
                + " is not staged. The engine tree at "
                f"{module_root} has changed since this service imported its "
                "bundle list, so the list and the files on disk disagree. "
                "Restart the engine; if it recurs, the module is missing from "
                "_DOMAIN_WORKER_BUNDLES."
            )
        _CHECKED_BUNDLE_DIGESTS.add(fingerprint)
    bundle = root / f"{clean_domain}-{fingerprint[:24]}"

    def populated() -> bool:
        """Validate identity and reject mutable legacy hardlinks/symlinks."""

        try:
            return bundle.is_dir() and all(
                not (bundle / name).is_symlink()
                and (bundle / name).stat().st_nlink == 1
                and (bundle / name).read_bytes() == data
                for name, data in snapshot.items()
            )
        except OSError:
            return False

    if populated():
        return bundle, entry_module

    root.mkdir(parents=True, exist_ok=True)
    pending = root / f".tmp-{uuid.uuid4().hex}"
    pending.mkdir(parents=True, exist_ok=False)
    try:
        for name, data in snapshot.items():
            (pending / name).write_bytes(data)
        if bundle.is_dir():
            # Retire a corrupt, linked or incomplete bundle as a whole.
            # Existing readers are not guaranteed to survive this repair;
            # no member is replaced in place under stale bytecode.
            husk = root / f".dead-{uuid.uuid4().hex}"
            try:
                os.replace(bundle, husk)
            except OSError:
                husk = None
            if husk is not None:
                shutil.rmtree(husk, ignore_errors=True)
        os.replace(pending, bundle)
    except OSError:
        shutil.rmtree(pending, ignore_errors=True)
        # Lost a race with another worker, or could not publish. Either the
        # bundle is there now or the caller's next attempt rebuilds it.
        if not populated():
            raise
    return bundle, entry_module


def _stage_project_assets(project_root: Path, staging: Path) -> list[str]:
    """Copy the project's mesh asset files beside the isolated worker.

    ``mesh.import_file`` resolves names against ``<staging>/assets`` only, so
    the sandboxed worker never reads the durable project tree. Bounded: flat
    directory, known mesh suffixes, capped file count and total bytes.
    """

    source_dir = project_root / "assets"
    if not source_dir.is_dir():
        return []
    staged: list[str] = []
    total_bytes = 0
    target_dir = staging / "assets"
    for path in sorted(source_dir.iterdir()):
        if path.is_symlink() or not path.is_file():
            continue
        if path.suffix.lower() not in _STORED_ASSET_SUFFIXES:
            continue
        total_bytes += path.stat().st_size
        if len(staged) >= _MAX_ASSET_FILES or total_bytes > _MAX_ASSET_BYTES:
            raise ValueError(
                f"Project assets exceed the staging budget of {_MAX_ASSET_FILES} "
                f"mesh files / {_MAX_ASSET_BYTES} bytes."
            )
        target_dir.mkdir(parents=True, exist_ok=True)
        # Hardlink: a 128 MB asset budget copied per attempt is 128 MB of
        # I/O on every drag. Safe because put_asset writes through
        # `replace`, so overwriting an asset makes a new inode and never
        # mutates a file a live attempt has linked.
        _link_or_copy(path, target_dir / path.name)
        staged.append(path.name)
    return staged


def _asset_entry(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return {"name": path.name, "bytes": size, "sha256": digest.hexdigest()}


def list_project_assets(project_root: Path | str) -> list[dict[str, Any]]:
    """Every importable mesh asset in the project store, sorted by name.

    The same flat, suffix-filtered, symlink-skipping walk
    :func:`_stage_project_assets` performs, so what this reports is exactly
    what a run would stage for ``mesh.import_file``.
    """

    source_dir = Path(project_root) / "assets"
    if not source_dir.is_dir():
        return []
    return [
        _asset_entry(path)
        for path in sorted(source_dir.iterdir())
        if not path.is_symlink()
        and path.is_file()
        and path.suffix.lower() in _STORED_ASSET_SUFFIXES
    ]


def store_project_asset(
    project_root: Path | str,
    source_path: str,
    name: str = "",
) -> dict[str, Any]:
    """Copy one storable file into ``<project_root>/assets`` under a checked name.

    The engine is the sole writer of the project store
    (docs/ARCHITECTURE.md), so this is how a file the user picked outside the
    store becomes importable. Bounds are the staging bounds — same suffixes,
    same 64-file / 128 MB budget, counted *including* the incoming file, so a
    run can never be staged into a budget this write already broke.
    Overwriting an existing name is allowed: that is re-import.

    Two kinds of file rather than one since ADR-084: the three mesh formats
    ``mesh.import_file`` reads, and the ``.cxpolicy`` a trained control
    policy arrives in. Both travel the same ``put_asset`` path because that
    path performs **no suffix check of its own** — it passes the path through
    and lets the engine refuse — so a policy needed no new op and no
    front-end change to come home. ADR-135 added the ``.json``/``.xml`` a
    policy's provenance travels as, and ADR-138 the ``.cxpart`` a part built
    in another project arrives in — the last of those written by
    ``link_part`` rather than picked by a user, which is the only way the
    four differ here.
    """

    from cadex_mesh_api import _asset_filename

    raw_source = str(source_path or "").strip()
    if not raw_source:
        raise ValueError("source_path must name a readable file.")
    try:
        source = Path(raw_source).expanduser().resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"Could not read {raw_source!r}: {exc}") from exc
    if not source.is_file():
        raise ValueError(f"{raw_source!r} is not a regular file.")
    source_suffix = source.suffix.lower()
    if source_suffix not in _STORED_ASSET_SUFFIXES:
        raise ValueError(
            f"{source.name!r} is not one of the formats this project store "
            f"holds {sorted(_STORED_ASSET_SUFFIXES)}: the mesh formats "
            "mesh.import_file reads, the .cxpolicy a trained control policy "
            "arrives in, the .json task bundle and .xml model a policy "
            "travels with for assembly.policy(..., trained_task=), or the "
            ".cxpart a part built in another project arrives in for "
            "part.import_part."
        )
    target_name = _asset_filename(
        "put_asset",
        str(name or "").strip() or source.name,
        suffixes=_STORED_ASSET_SUFFIXES,
    )
    if Path(target_name).suffix.lower() != source_suffix:
        raise ValueError(
            f"name {target_name!r} must keep the source file's {source_suffix} "
            "format; the importer reads the format from the suffix."
        )

    size = source.stat().st_size
    existing = [
        item for item in list_project_assets(project_root) if item["name"] != target_name
    ]
    if len(existing) + 1 > _MAX_ASSET_FILES:
        raise ValueError(
            f"The project already holds {len(existing)} mesh assets; the "
            f"staging budget is {_MAX_ASSET_FILES} files."
        )
    total_bytes = sum(int(item["bytes"]) for item in existing) + size
    if total_bytes > _MAX_ASSET_BYTES:
        raise ValueError(
            f"Storing {target_name!r} would bring the project's mesh assets to "
            f"{total_bytes} bytes, over the staging budget of {_MAX_ASSET_BYTES}."
        )

    assets_dir = Path(project_root) / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    # Dot-prefixed and .tmp-suffixed, so a concurrent staging walk skips it
    # and no reader ever sees a half-copied asset under its final name.
    temporary = assets_dir / f".{target_name}.{uuid.uuid4().hex}.tmp"
    try:
        shutil.copyfile(source, temporary)
        temporary.replace(assets_dir / target_name)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return _asset_entry(assets_dir / target_name)


def _document_objects(doc: Any) -> list[dict[str, str]]:
    return [
        {
            "name": str(getattr(obj, "Name", "") or ""),
            "label": str(getattr(obj, "Label", "") or ""),
            "type_id": str(getattr(obj, "TypeId", "") or ""),
        }
        for obj in list(getattr(doc, "Objects", []) or [])[:10_000]
    ]


def _apply_replacements(source: str, replacements: Any) -> str:
    if not isinstance(replacements, list) or not replacements:
        raise ValueError("replacements must be a non-empty array.")
    result = source
    for index, replacement in enumerate(replacements):
        if not isinstance(replacement, dict) or set(replacement) != {"old", "new"}:
            raise ValueError(f"replacements[{index}] must contain exactly old and new.")
        old = str(replacement["old"])
        new = str(replacement["new"])
        count = result.count(old)
        if count != 1:
            raise ValueError(
                f"replacements[{index}].old must occur exactly once; found {count}."
            )
        result = result.replace(old, new, 1)
    return result


def _merge_patch(base: Mapping[str, Any], patch: Any) -> dict[str, Any]:
    if not isinstance(patch, dict) or not patch:
        raise ValueError("patch must be a non-empty object.")
    result = dict(base)
    for key, value in patch.items():
        if value is None:
            result.pop(str(key), None)
        else:
            result[str(key)] = value
    return result


def _freecadcmd(freecad_home: str) -> Path:
    names = (
        ("FreeCADCmd.exe", "freecadcmd.exe")
        if sys.platform == "win32"
        else (
            "FreeCADCmd",
            "freecadcmd",
        )
    )
    for name in names:
        path = Path(freecad_home) / "bin" / name
        if path.is_file():
            return path
    raise FileNotFoundError(
        f"No windowless FreeCADCmd executable exists under {freecad_home!r}."
    )


def stage_preview_assets(project_root: Path, staging: Path) -> list[str]:
    """Stage the project's assets beside the resident preview worker.

    The same bounded copy the per-run worker gets, for the same reason:
    ``mesh.import_file`` resolves names against ``<staging>/assets`` only, so
    a sandboxed worker never reads the durable project tree. Hardlinks, so
    this does not modify the store — which the preview path asserts.
    """

    return _stage_project_assets(Path(project_root), Path(staging))


def prepare_preview(service: Any, values: Mapping[str, Any]) -> dict[str, Any]:
    """Everything one preview needs, read from the store and nothing written.

    Deliberately *not* :func:`prepare_project_candidate`: that one mints an
    attempt directory, stages a request into it, and persists the source as
    the working script before the worker starts, because an accepting run
    must be recoverable from disk if the host dies mid-run. A preview has
    nothing to recover — it is a question, not a change — so it reads the
    store and writes none of it (ADR-055).

    Raises :class:`DomainRuntimeFailure` if the requested values do not match
    the declared parameters; the caller turns that into a declined preview
    rather than an error, since the debounced ``set_params`` behind it is the
    real answer.
    """

    from CadexScriptStore import CadexProjectScriptStore
    from CadexWarmWorker import assets_fingerprint, generation_key

    tool_name = "xscript.project.set_params"
    captured = capture_project_state(service, tool_name, {"values": dict(values)})
    project_root = Path(str(captured["project_root"]))
    store = CadexProjectScriptStore(project_root)
    state = store.read_state()
    source = store.read_source()
    if not source.strip():
        _raise(
            tool_name,
            "NO_PROJECT_SCRIPT",
            "precondition",
            "There is no project script to preview yet.",
        )
    api_contracts = _project_api_contracts()
    # The generation's baseline is the *stored* values -- the model as it
    # currently stands -- and the preview is the same program at the patched
    # values. Both go through the same validation as a real set_params, so a
    # preview cannot be asked something set_params would refuse.
    # Narrowed to the declared names, exactly as _project_param_values does
    # before its merge: a stale key left behind by a rewritten script is not
    # a caller error and must not wedge anything (ADR-039).
    declared = {
        str(spec.get("name") or "") for spec in list(state.get("param_specs") or [])
    }
    baseline_values = {
        name: value
        for name, value in dict(state.get("param_values") or {}).items()
        if name in declared
    }
    param_values = _project_param_values(state, dict(values), tool_name)
    bundle_dir, _entry_module = shared_worker_bundle(
        Path(__file__).resolve().parent, "project"
    )
    return {
        "generation": generation_key(
            source, api_contracts, assets_fingerprint(project_root)
        ),
        "project_root": str(project_root),
        "revision": str(state.get("working_revision") or ""),
        "param_values": param_values,
        "bundle_dir": str(bundle_dir),
        "freecadcmd_executable": str(_freecadcmd(str(captured["freecad_home"]))),
        "request": {
            "schema": PROJECT_WORKER_SCHEMA,
            "source": source,
            "inputs": {},
            "param_values": baseline_values,
            # The model as it currently stands includes its connections: a
            # preview generation built from the *declared* table would answer
            # about a harness the user is not looking at (ADR-065).
            "net_values": [
                dict(row) for row in list(state.get("net_values") or [])
            ],
            # ...and its boards, for the same reason: a preview generation
            # built from the *declared* terminals would answer about a board
            # the user is not looking at (ADR-120).
            "board_values": [
                dict(row) for row in list(state.get("board_values") or [])
            ],
            "api_contracts": api_contracts,
            "document_name": str(captured["document_name"]),
            "document_uid": str(captured["document_uid"]),
            "document_objects": list(captured["document_objects"]),
            "max_operations": 400_000,
            "max_seconds": float(captured["timeout_seconds"]),
        },
    }


def worker_environment(staging: str | Path) -> dict[str, str]:
    """The closed environment every isolated worker runs under.

    One allowlist, shared by the per-run worker and the resident preview
    worker (ADR-055): the point of it is that a worker sees nothing of the
    host's environment except what it is handed, and two copies of that list
    would eventually disagree about what "nothing" means.
    """

    staging = str(staging)
    preserved = (
        "COMSPEC",
        "LANG",
        "LC_ALL",
        "LD_LIBRARY_PATH",
        "PATH",
        "PATHEXT",
        "SystemRoot",
        "WINDIR",
    )
    environment = {
        name: os.environ[name]
        for name in preserved
        if str(os.environ.get(name) or "").strip()
    }
    environment.update(
        {
            "HOME": staging,
            # OpenBLAS reserves a per-thread scratch buffer at dlopen time --
            # measured at ~136 MB each on this build -- and sizes its pool
            # from the *host's* core count. On a 32-core box `import numpy`,
            # which `assembly.mjcf` reaches through mujoco, therefore reserves
            # 4.4 GB of address space before it does any arithmetic, the
            # worker's 6144 MB RLIMIT_AS refuses the mapping, and OpenBLAS
            # spins in its allocation retry loop until RLIMIT_CPU kills it.
            # Four threads is 624 MB, and it is the same four everywhere: a
            # worker that behaves differently on a laptop and a build box is
            # the bug this pins shut, the way PYTHONHASHSEED pins hashing
            # (ADR-250).
            "OPENBLAS_NUM_THREADS": str(WORKER_BLAS_THREADS),
            "PYTHONHASHSEED": "0",
            "PYTHONNOUSERSITE": "1",
            "TEMP": staging,
            "TMP": staging,
            "TMPDIR": staging,
            "CADEX_XSCRIPT_DOMAIN_REQUEST": str(Path(staging) / "request.json"),
            "CADEX_XSCRIPT_DOMAIN_RESULT": str(Path(staging) / "result.json"),
            "CADEX_XSCRIPT_DOMAIN_PROGRESS": str(Path(staging) / "progress.json"),
        }
    )
    if sys.platform == "win32":
        drive, tail = os.path.splitdrive(staging)
        environment["USERPROFILE"] = staging
        if drive:
            environment["HOMEDRIVE"] = drive
            environment["HOMEPATH"] = tail or "\\"
    return environment


#: The kernel's own budget refusals, which leave no ``result.json`` and so
#: used to arrive as the generic "exited without a result".
_RESOURCE_SIGNAL_FAILURES: dict[int, tuple[str, str]] = {
    24: (  # SIGXCPU
        "DOMAIN_CPU_LIMIT_EXCEEDED",
        "XScript domain execution exceeded its CPU limit of {seconds:g} "
        "CPU-seconds. That limit is charged across every thread the worker "
        "runs, so a parallel pass can reach it well inside the {seconds:g} "
        "second wall-clock timeout.",
    ),
    25: (  # SIGXFSZ
        "DOMAIN_OUTPUT_LIMIT_EXCEEDED",
        "XScript domain execution exceeded its output file size limit.",
    ),
}


def _resource_signal_failure(
    process: Mapping[str, Any], prepared: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Name the cap when the kernel, not the watchdog, ended the worker.

    ``run_process`` owns a wall-clock timeout; ``_resource_limits`` in the
    worker owns ``RLIMIT_CPU`` and ``RLIMIT_FSIZE``, set from the same
    numbers but charged in different units. When the kernel wins that race
    the worker dies by signal with no ``result.json`` written, which read
    as a crash. It is a budget refusal and says so.
    """

    returncode = process.get("returncode")
    if not isinstance(returncode, int) or returncode >= 0:
        return None
    known = _RESOURCE_SIGNAL_FAILURES.get(-returncode)
    if known is None:
        return None
    code, template = known
    message = template.format(seconds=float(prepared["timeout_seconds"]))
    observed = dict(process)
    if code == "DOMAIN_CPU_LIMIT_EXCEEDED":
        ledger = _cpu_ledger(Path(str(prepared.get("staging") or "")))
        if ledger is not None:
            message = f"{message} {_cpu_ledger_sentence(ledger)}"
            observed["cpu_ledger"] = ledger
    return _failure(
        str(prepared["tool_name"]),
        code,
        "external_process",
        message,
        observed=observed,
    )


def _cpu_ledger(staging: Path) -> dict[str, Any] | None:
    """The worker's last CPU ledger, or None when it never wrote one (ADR-436)."""

    if not str(staging):
        return None
    try:
        ledger = json.loads((staging / "progress.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    current = ledger.get("current") if isinstance(ledger, Mapping) else None
    if not isinstance(current, Mapping) or not str(current.get("stage") or ""):
        return None
    finished = [
        {"stage": str(item.get("stage")), "cpu_seconds": float(item.get("cpu_seconds") or 0.0)}
        for item in list(ledger.get("finished") or [])
        if isinstance(item, Mapping) and item.get("stage")
    ]
    return {
        "current": {
            "stage": str(current["stage"]),
            "started_cpu_seconds": float(current.get("started_cpu_seconds") or 0.0),
        },
        "finished": finished,
    }


def _cpu_ledger_sentence(ledger: Mapping[str, Any]) -> str:
    current = ledger["current"]
    sentence = (
        f"It was in {current['stage']!r}, which started {current['started_cpu_seconds']:g} "
        "CPU-seconds in."
    )
    costly = [item for item in ledger["finished"] if item["cpu_seconds"] >= 1.0]
    if costly:
        spent = ", ".join(f"{item['stage']!r} {item['cpu_seconds']:g}" for item in costly)
        sentence += f" Costliest finished stages, in CPU-seconds: {spent}."
    return sentence + (
        " Make the named stages cheaper rather than retrying: an 'output NAME' "
        "stage is that shape's own construction, and a 'static fit A / B' stage "
        "is the exact fit check between those two components, run because their "
        "boxes come within 10 mm."
    )


#: Must equal ``cadex_domain_worker.KERNEL_BREADCRUMB_NAME`` (a test holds
#: them equal; that module is staged into the sandbox, not imported here).
_KERNEL_BREADCRUMB_NAME = "kernel.json"

_SIGNAL_NAMES = {6: "SIGABRT", 7: "SIGBUS", 8: "SIGFPE", 11: "SIGSEGV"}


def _kernel_breadcrumb(staging: Path) -> dict[str, Any] | None:
    """The innermost kernel call a dead worker was in, or None (ADR-617)."""

    try:
        crumb = json.loads((staging / _KERNEL_BREADCRUMB_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    in_flight = crumb.get("in_flight") if isinstance(crumb, Mapping) else None
    if not isinstance(in_flight, list) or not in_flight:
        return None
    innermost = in_flight[-1]
    if not isinstance(innermost, Mapping) or not innermost.get("operation"):
        return None
    entry = {
        "operation": str(innermost.get("operation")),
        "lines": [int(line) for line in list(innermost.get("lines") or []) if isinstance(line, int)],
        "stage": str(innermost.get("stage") or ""),
        "scalars": dict(innermost.get("scalars") or {}),
    }
    if len(in_flight) > 1:
        entry["inside"] = [
            str(item.get("operation") or "")
            for item in in_flight[:-1]
            if isinstance(item, Mapping)
        ]
    return entry


def _kernel_crash_sentence(
    crashed_in: Mapping[str, Any], process: Mapping[str, Any]
) -> tuple[str, str]:
    operation = str(crashed_in["operation"])
    returncode = process.get("returncode")
    how = "crashed"
    if isinstance(returncode, int) and returncode < 0:
        how += f" ({_SIGNAL_NAMES.get(-returncode, f'signal {-returncode}')})"
    elif "SIGSEGV" in str(process.get("stderr") or ""):
        how += " (SIGSEGV)"
    lines = list(crashed_in.get("lines") or [])
    where = (
        f" made at script line{'s' if len(lines) > 1 else ''} {', '.join(map(str, lines))}"
        if lines
        else ""
    )
    scalars = dict(crashed_in.get("scalars") or {})
    shown = ", ".join(f"{key}={value}" for key, value in scalars.items())
    stage = str(crashed_in.get("stage") or "")
    message = (
        f"The isolated domain worker {how} inside OpenCascade while running "
        f"part.{operation}{where}"
        + (f" ({shown})" if shown else "")
        + (f", during {stage!r}" if stage else "")
        + ". A native crash is the kernel failing on this call's geometry, so "
        "the same call will crash again unchanged."
    )
    if operation in {"fillet", "chamfer"} or "blend" in scalars:
        correction = (
            f"Change the part.{operation} call{where}: a smaller radius, fewer "
            "edges (round the long edges and leave the corners where three "
            "rounded edges meet), or round before the boolean that made the "
            "corner."
        )
    else:
        correction = (
            f"Change the part.{operation} call{where}: move its inputs apart "
            "or into clear overlap by a fraction of a millimetre (a tangent "
            "or coincident face is what the kernel cannot resolve), or split "
            "it into smaller calls."
        )
    return message, correction


def execute_candidate(
    prepared: Mapping[str, Any],
    *,
    cancellation_check: Callable[[], bool] | None,
) -> dict[str, Any]:
    from CadexScriptedProcess import run_process

    # A plain import, not runpy.run_path: run_path compiles the entry
    # module from source every single time, while an import writes and
    # reuses __pycache__ next to the shared bundle. The bundle directory is
    # content-addressed, so this cache is never stale.
    bundle = str(prepared["bundle_dir"])
    entry = str(prepared["entry_module"]).removesuffix(".py")
    code = (
        "import os,sys;"
        "sys.path.insert(0,os.getcwd());"
        f"sys.path.insert(0,{bundle!r});"
        f"import {entry} as _w;"
        "raise SystemExit(_w.main())"
    )
    process = run_process(
        [str(prepared["freecadcmd_executable"]), "--safe-mode", "-c", code],
        cwd=str(prepared["staging"]),
        environment=worker_environment(prepared["staging"]),
        cancellation_check=cancellation_check,
        timeout_seconds=float(prepared["timeout_seconds"]),
        memory_limit_bytes=int(prepared["memory_limit_bytes"]),
    )
    if not process.get("started"):
        return _failure(
            str(prepared["tool_name"]),
            "DOMAIN_WORKER_START_FAILED",
            "external_process",
            f"The isolated domain worker could not start: {process.get('error')}",
            observed=process,
        )
    if process.get("cancelled"):
        return _failure(
            str(prepared["tool_name"]),
            "RUN_CANCELLED",
            "external_process",
            "XScript domain execution was cancelled.",
            observed=process,
            cancelled=True,
        )
    if process.get("timed_out"):
        return _failure(
            str(prepared["tool_name"]),
            "DOMAIN_EXECUTION_TIMEOUT",
            "external_process",
            f"XScript domain execution exceeded {prepared['timeout_seconds']:g} seconds.",
            observed=process,
        )
    if process.get("memory_exceeded"):
        return _failure(
            str(prepared["tool_name"]),
            "DOMAIN_MEMORY_LIMIT_EXCEEDED",
            "external_process",
            "XScript domain execution exceeded its memory limit.",
            observed=process,
        )
    resource_failure = _resource_signal_failure(process, prepared)
    if resource_failure is not None:
        return resource_failure
    result_path = Path(str(prepared["staging"])) / "result.json"
    if not result_path.is_file():
        crashed_in = _kernel_breadcrumb(Path(str(prepared["staging"])))
        if crashed_in is not None:
            message, correction = _kernel_crash_sentence(crashed_in, process)
            return _failure(
                str(prepared["tool_name"]),
                "DOMAIN_WORKER_NO_RESULT",
                "external_process",
                message,
                observed={**dict(process), "kernel_operation": crashed_in},
                domain_failure_stage="kernel_crash",
                required_changes=[correction],
            )
        return _failure(
            str(prepared["tool_name"]),
            "DOMAIN_WORKER_NO_RESULT",
            "external_process",
            "The isolated domain worker exited without a result.",
            observed=process,
        )
    try:
        report = _read_json(result_path, "domain worker result")
    except ValueError as exc:
        return _failure(
            str(prepared["tool_name"]),
            "DOMAIN_WORKER_RESULT_INVALID",
            "external_process",
            str(exc),
            observed=process,
        )
    if not report.get("ok"):
        domain_details = (
            dict(report.get("details") or {})
            if isinstance(report.get("details"), Mapping)
            else {}
        )
        domain_failure_stage = str(domain_details.get("stage") or "").strip()
        correction = str(domain_details.get("correction") or "").strip()
        return _failure(
            str(prepared["tool_name"]),
            "DOMAIN_CANDIDATE_FAILED",
            "external_process",
            str(report.get("error") or "The domain worker rejected the candidate."),
            observed={
                "exception_type": report.get("exception_type"),
                "details": report.get("details"),
                "traceback": report.get("traceback"),
                # The script's own prints when the worker sent them -- a project
                # worker always does now, refused or not (ADR-620) -- and the
                # process's stdout only from a worker that predates that.
                "stdout": (
                    report["stdout"] if "stdout" in report else process.get("stdout")
                ),
                "stderr": process.get("stderr"),
                "elapsed_seconds": process.get("elapsed_seconds"),
            },
            **(
                {"domain_failure_stage": domain_failure_stage}
                if domain_failure_stage
                else {}
            ),
            required_changes=[correction] if correction else [],
        )
    report["process"] = process
    return report


def _staged_artifact_path(
    prepared: Mapping[str, Any],
    relative: Any,
    *,
    context: str,
    maximum_bytes: int = 256 * 1024 * 1024,
) -> Path:
    root = Path(str(prepared["staging"])).resolve()
    raw = str(relative or "")
    candidate = root / raw
    path = candidate.resolve()
    if (
        not raw
        or root not in path.parents
        or not path.is_file()
        or candidate.is_symlink()
    ):
        raise ValueError(f"{context} does not resolve to a staged artifact.")
    try:
        relative_parts = candidate.relative_to(root).parts
    except ValueError as exc:
        raise ValueError(f"{context} is outside candidate staging.") from exc
    cursor = root
    for part in relative_parts[:-1]:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError(f"{context} traverses a staged symlink.")
    size = path.stat().st_size
    if not 1 <= size <= maximum_bytes:
        raise ValueError(f"{context} must contain 1-{maximum_bytes} artifact bytes.")
    return path


PROJECT_WORKER_SCHEMA = "cadex-xscript-project-worker-v1"


_PROJECT_OPERATIONS = frozenset({"write_script", "edit_script", "set_params"})


def parse_project_tool(tool_name: str) -> str | None:
    """Return the project lifecycle operation for xscript.project.* tools."""

    parts = str(tool_name or "").split(".")
    if len(parts) != 3 or parts[0] != "xscript" or parts[1] != "project":
        return None
    operation = parts[2]
    if operation not in _PROJECT_OPERATIONS and operation != "describe_api":
        return None
    return operation


def _project_api_contracts() -> dict[str, dict[str, list[str]]]:
    by_domain = {
        pack.domain: pack for pack in contracts.XSCRIPT_WORKBENCH_PACKS.values()
    }
    return {
        domain: {
            "exports": list(pack.api_exports),
            "output_types": list(pack.output_types),
        }
        for domain, pack in by_domain.items()
    }


def capture_project_state(
    service: Any,
    tool_name: str,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    """Capture document-affine state for one project script operation."""

    operation = parse_project_tool(tool_name)
    if operation is None:
        _raise(tool_name, "UNKNOWN_DOMAIN_TOOL", "surface", "Unknown project tool.")
    doc = service._active_document()
    if doc is None:
        _raise(tool_name, "NO_DOCUMENT", "precondition", "No active FreeCAD document.")
    scope = service.project_scope_snapshot()
    # Budgets come from the service when it carries them (cadexd resolves
    # them once at open_project); headless rebuild falls back to the
    # engine's defaults (ADR-530).
    timeout = 0.0
    memory_mb = 0
    budgets_reader = getattr(service, "scripted_budgets", None)
    if callable(budgets_reader):
        budgets = dict(budgets_reader() or {})
        timeout = float(budgets.get("timeout_seconds") or 0.0)
        memory_mb = int(budgets.get("memory_limit_mb") or 0)
    if timeout <= 0.0 or memory_mb <= 0:
        from CadexEngineSettings import default_budgets

        settings = default_budgets()
        timeout = float(settings.get("timeout_seconds") or 0.0)
        memory_mb = int(settings.get("memory_limit_mb") or 0)
    if timeout <= 0.0 or memory_mb <= 0:
        _raise(
            tool_name,
            "INVALID_SCRIPTED_BUDGET",
            "precondition",
            "XScript requires positive worker timeout and memory limits.",
            observed={"timeout_seconds": timeout, "memory_limit_mb": memory_mb},
        )
    try:
        import FreeCAD as App

        freecad_home = str(App.getHomePath())
    except Exception as exc:
        _raise(
            tool_name,
            "FREECAD_UNAVAILABLE",
            "precondition",
            f"FreeCAD is unavailable: {exc}",
        )
    return {
        "tool_name": tool_name,
        "operation": operation,
        "arguments": dict(arguments),
        "pack": contracts.PROJECT_PACK,
        "project_root": str(scope.get("root") or ""),
        "project_id": str(scope.get("project_id") or ""),
        "document_name": str(getattr(doc, "Name", "") or ""),
        "document_uid": str(getattr(doc, "Uid", "") or ""),
        "document_revision": str(service.provider_document_revision()),
        "document_objects": _document_objects(doc),
        "freecad_home": freecad_home,
        "timeout_seconds": timeout,
        "memory_limit_bytes": memory_mb * 1024 * 1024,
    }


def _project_param_values(
    state: Mapping[str, Any], patch: Any, tool_name: str
) -> dict[str, float]:
    """Apply one values-only RFC 7396 patch against the declared parameters.

    The strict check is on the *patch*: asking to set a parameter the script
    does not declare is a caller error and stays loud. A stale key in the
    stored values is not -- it is what a rewritten script leaves behind, and
    it used to wedge every later ``set_params`` permanently (ADR-039). So the
    stored base is narrowed to the declared names before the merge. Dropping
    undeclared keys cannot change what the worker computes: ``ParamsCollector``
    resolves each declared parameter by name and never reads the rest.
    """

    declared = {
        str(spec.get("name") or ""): spec
        for spec in list(state.get("param_specs") or [])
    }
    if isinstance(patch, dict):
        for name in patch:
            if str(name) not in declared:
                _raise(
                    tool_name,
                    "UNKNOWN_PROJECT_PARAMETER",
                    "precondition",
                    "The project script declares no parameter named "
                    f"{str(name)!r}.",
                    requested={"values": patch},
                    observed={"declared": sorted(declared)},
                )
    base = {
        name: value
        for name, value in dict(state.get("param_values") or {}).items()
        if name in declared
    }
    merged = _merge_patch(base, patch)
    cleaned: dict[str, float] = {}
    for name, value in merged.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            _raise(
                tool_name,
                "INVALID_PROJECT_PARAMETER_VALUE",
                "precondition",
                f"Parameter {name!r} must be a finite number.",
                requested={name: value},
            )
        cleaned[name] = float(value)
    return cleaned


def _project_net_values(
    state: Mapping[str, Any], rows: Any, tool_name: str
) -> list[dict[str, Any]]:
    """Validate one full connection-row list against the declared table.

    A **full row list**, not a patch: that is what lets the editor add and
    delete wires, and it is why this is not a line-for-line copy of
    :func:`_project_param_values`. What it does copy is ADR-039's asymmetry,
    and the halves land in different places for it. Here — the *request* —
    an endpoint the declared ports do not have is a caller error and stays
    loud, exactly as an undeclared parameter name does. The lenient half is
    on the *stored* rows, in ``validate_project_result`` and in
    ``CadexNets.effective_rows``: a row a rewritten script no longer supports
    is dropped there, because raising on it would wedge the editor forever in
    exactly the way a dropped parameter once wedged ``set_params``.
    """

    from CadexNets import NetError, canonical_rows, declared_ports

    try:
        clean = canonical_rows(rows, what="nets")
    except NetError as exc:
        _raise(
            tool_name,
            "INVALID_PROJECT_NET",
            "precondition",
            str(exc),
            requested={"nets": rows},
        )
    ports = declared_ports(state.get("net_specs"))
    if not ports:
        # No declaration to check against yet: the script has never run with
        # nets(...), so there is no port list. The worker refuses an
        # unresolvable endpoint on the run itself.
        return clean
    for row in clean:
        for side in ("a", "b"):
            address = str(row[side])
            port, _, terminal = address.partition(".")
            if port not in ports:
                _raise(
                    tool_name,
                    "UNKNOWN_PROJECT_NET_ENDPOINT",
                    "precondition",
                    f"Connection {row['name']!r} names port {port!r}, which "
                    "the project script does not declare.",
                    requested={"nets": rows},
                    observed={"declared_ports": sorted(ports)},
                )
            if terminal not in list(ports[port]):
                _raise(
                    tool_name,
                    "UNKNOWN_PROJECT_NET_ENDPOINT",
                    "precondition",
                    f"Connection {row['name']!r} names terminal {terminal!r} "
                    f"on port {port!r}, which has {list(ports[port])}.",
                    requested={"nets": rows},
                    observed={"terminals": list(ports[port])},
                )
    return clean


def _project_terminal_values(
    state: Mapping[str, Any], rows: Any, tool_name: str
) -> list[dict[str, Any]]:
    """Validate one full terminal-row list against the declared boards.

    The sibling of :func:`_project_net_values`, one table over, with the same
    ADR-039 asymmetry landing in the same two places: here — the *request* —
    a board the script does not declare is a caller error and stays loud; the
    lenient half is on the *stored* rows, in ``validate_project_result`` and
    ``CadexBoards.effective_terminals``, where a row a rewritten script no
    longer supports is dropped rather than raised on.

    A ``frame="world"`` row passes through **unconverted**: this process has
    no geometry and never runs user code, so it cannot resolve a component's
    placement. The worker converts it and the converted row is written back
    (ADR-120). What is checked here is that the row is well-formed and names
    a board that exists.
    """

    from CadexBoards import BoardError, canonical_terminal_rows, declared_boards

    try:
        clean = canonical_terminal_rows(rows, what="boards", allow_world=True)
    except BoardError as exc:
        _raise(
            tool_name,
            "INVALID_PROJECT_TERMINAL",
            "precondition",
            str(exc),
            requested={"boards": rows},
        )
    boards = declared_boards(state.get("board_specs"))
    if not boards:
        # No declaration to check against yet: the script has never run with
        # boards(...), so there is no board list. The worker refuses an
        # unresolvable row on the run itself.
        return clean
    for row in clean:
        name = str(row["board"])
        entry = boards.get(name)
        if entry is None:
            _raise(
                tool_name,
                "UNKNOWN_PROJECT_BOARD",
                "precondition",
                f"Terminal {row['name']!r} names board {name!r}, which the "
                "project script does not declare.",
                requested={"boards": rows},
                observed={"declared_boards": sorted(boards)},
            )
        if entry.get("selector"):
            _raise(
                tool_name,
                "UNKNOWN_PROJECT_BOARD",
                "precondition",
                f"Board {name!r} states its terminals with a selector, so they "
                "are derived from the shape on every run and cannot be edited "
                "here; change the selector in the script instead.",
                requested={"boards": rows},
                observed={"declared_boards": sorted(boards)},
            )
    return clean


def _project_mount_values(
    state: Mapping[str, Any], rows: Any, tool_name: str
) -> list[dict[str, Any]]:
    """Validate one full mount-row list against the declared components.

    :func:`_project_terminal_values`, one table over, with the same ADR-039
    asymmetry in the same two places: a *request* naming a component the
    script does not declare is a caller error and stays loud; a *stored* row
    that a rewritten script no longer supports is dropped, in
    ``CadexMounts.effective_mounts``.

    A ``frame="world"`` row passes through unconverted, for the reason a
    board's does: this process has no geometry and never runs user code.
    """

    from CadexMounts import MountError, canonical_mount_rows, declared_groups

    try:
        clean = canonical_mount_rows(rows, what="mounts", allow_world=True)
    except MountError as exc:
        _raise(
            tool_name,
            "INVALID_PROJECT_MOUNT",
            "precondition",
            str(exc),
            requested={"mounts": rows},
        )
    groups = declared_groups(state.get("mount_specs"))
    if not groups:
        # No declaration to check against yet: the script has never run with
        # mounts(...). The worker refuses an unresolvable row on the run.
        return clean
    for row in clean:
        name = str(row["component"])
        if name not in groups:
            _raise(
                tool_name,
                "UNKNOWN_PROJECT_MOUNT_COMPONENT",
                "precondition",
                f"Mount {row['name']!r} names component {name!r}, which the "
                "project script does not declare mounts for.",
                requested={"mounts": rows},
                observed={"declared_components": sorted(groups)},
            )
    return clean


def _project_cage_values(
    state: Mapping[str, Any], rows: Any, tool_name: str
) -> list[dict[str, Any]]:
    """Validate one full ring-row list against the declared cages (ADR-127)."""

    from CadexCage import CageError, canonical_ring_rows, declared_cages

    try:
        clean = canonical_ring_rows(rows, what="cages")
    except CageError as exc:
        _raise(
            tool_name,
            "INVALID_PROJECT_CAGE",
            "precondition",
            str(exc),
            requested={"cages": rows},
        )
    cages = declared_cages(state.get("cage_specs"))
    if not cages:
        return clean
    for row in clean:
        name = str(row["cage"])
        if name not in cages:
            _raise(
                tool_name,
                "UNKNOWN_PROJECT_CAGE",
                "precondition",
                f"A ring names cage {name!r}, which the project script does "
                "not declare.",
                requested={"cages": rows},
                observed={"declared_cages": sorted(cages)},
            )
    return clean


def prepare_project_candidate(captured: Mapping[str, Any]) -> dict[str, Any]:
    """Persist the working script state and stage one project candidate."""

    from CadexScriptStore import CadexProjectScriptStore

    tool_name = str(captured["tool_name"])
    operation = str(captured["operation"])
    arguments = dict(captured["arguments"])
    project_root = str(captured["project_root"] or "")
    if not project_root:
        _raise(
            tool_name,
            "NO_PROJECT_ROOT",
            "precondition",
            "The active document has no durable Cadex project root.",
        )
    store = CadexProjectScriptStore(project_root)
    state = store.read_state()
    current_source = store.read_source()

    expected_revision = str(arguments.get("expected_revision") or "")
    working_revision = str(state.get("working_revision") or "")
    if expected_revision != working_revision:
        _raise(
            tool_name,
            "STALE_PROGRAM_REVISION",
            "precondition",
            "The project script changed after inspection.",
            requested={"expected_revision": expected_revision},
            observed={"current_revision": working_revision},
            required_changes=[{"inspect": "core.inspect scope=script"}],
        )

    param_values = dict(state.get("param_values") or {})
    net_values = [dict(row) for row in list(state.get("net_values") or [])]
    board_values = [dict(row) for row in list(state.get("board_values") or [])]
    mount_values = [dict(row) for row in list(state.get("mount_values") or [])]
    cage_values = [dict(row) for row in list(state.get("cage_values") or [])]
    if operation == "write_script":
        source = str(arguments.get("source") or "")
        if not source.strip():
            _raise(
                tool_name,
                "EMPTY_PROJECT_SCRIPT",
                "precondition",
                "write_script requires a complete non-empty script source.",
            )
    elif operation == "edit_script":
        if not current_source:
            # hex3's first write_script was refused (a wrong horn style) and
            # its next call edited the refused source. A refused candidate is
            # rolled back (ADR-044), so say that, and say what to send.
            latest = state.get("latest_candidate")
            refused = isinstance(latest, Mapping) and latest.get("status") == "failed"
            _raise(
                tool_name,
                "NO_PROJECT_SCRIPT",
                "precondition",
                (
                    "There is no accepted project script to edit yet: the last "
                    "write_script was refused and rolled back, and edit_script "
                    "only edits an accepted source. "
                    if refused
                    else "There is no project script to edit yet. "
                )
                + "Resend the whole corrected source with write_script and "
                "expected_revision=''.",
                required_changes=[{"tool": "write_script", "expected_revision": ""}],
            )
        try:
            source = _apply_replacements(
                current_source, arguments.get("replacements")
            )
        except ValueError as exc:
            _raise(
                tool_name,
                "REPLACEMENT_NOT_UNIQUE",
                "precondition",
                str(exc),
                requested={"replacements": arguments.get("replacements")},
            )
    elif operation == "set_params":
        if not current_source:
            _raise(
                tool_name,
                "NO_PROJECT_SCRIPT",
                "precondition",
                "There is no project script yet; use write_script first.",
            )
        source = current_source
        # One op, because "set the values of declared controls without the AI"
        # is one concept and a slider, a wire and a terminal are all instances
        # of it (ADR-065, ADR-120). A table-only edit sends no parameter patch,
        # and an empty `values` there means "leave the sliders alone" rather
        # than the refusal it still is when `values` is the only thing asked
        # for.
        values_patch = arguments.get("values")
        nets_patch = arguments.get("nets")
        boards_patch = arguments.get("boards")
        mounts_patch = arguments.get("mounts")
        cages_patch = arguments.get("cages")
        tables_only = (
            nets_patch is not None
            or boards_patch is not None
            or mounts_patch is not None
            or cages_patch is not None
        ) and values_patch == {}
        if not tables_only:
            try:
                param_values = _project_param_values(
                    state, values_patch, tool_name
                )
            except ValueError as exc:
                _raise(
                    tool_name,
                    "INVALID_PROJECT_PARAMETER_VALUE",
                    "precondition",
                    str(exc),
                )
        else:
            declared = {
                str(spec.get("name") or "")
                for spec in list(state.get("param_specs") or [])
            }
            param_values = {
                name: value
                for name, value in param_values.items()
                if name in declared
            }
        if nets_patch is not None:
            net_values = _project_net_values(state, nets_patch, tool_name)
        if boards_patch is not None:
            board_values = _project_terminal_values(state, boards_patch, tool_name)
        if mounts_patch is not None:
            mount_values = _project_mount_values(state, mounts_patch, tool_name)
        if cages_patch is not None:
            cage_values = _project_cage_values(state, cages_patch, tool_name)
    else:
        _raise(tool_name, "UNKNOWN_DOMAIN_TOOL", "surface", "Unknown project tool.")

    try:
        contracts.validate_program_source(source)
    except ValueError as exc:
        _raise(
            tool_name,
            "INVALID_PROGRAM_SOURCE",
            "precondition",
            str(exc),
        )

    from cadex_tessellation import validate_display_request

    try:
        display_request = validate_display_request(arguments.get("display"))
    except ValueError as exc:
        _raise(
            tool_name,
            "INVALID_DISPLAY_REQUEST",
            "precondition",
            str(exc),
            requested={"display": arguments.get("display")},
        )

    freecadcmd_executable = _freecadcmd(str(captured["freecad_home"]))
    # Pre-run revision over the stored spec cache; validate_project_result
    # recomputes it with the worker-collected specs and records that as the
    # durable working revision.
    revision = contracts.project_script_revision(
        source=source,
        param_specs=list(state.get("param_specs") or []),
        param_values=param_values,
        net_specs=state.get("net_specs"),
        net_values=net_values,
        board_specs=state.get("board_specs"),
        board_values=board_values,
        mount_specs=state.get("mount_specs"),
        mount_values=mount_values,
        cage_specs=state.get("cage_specs"),
        cage_values=cage_values,
    )
    attempt_id = f"{int(time.time() * 1000):013d}-{uuid.uuid4().hex[:12]}"
    staging = store.artifacts_dir(revision) / f"attempt-{attempt_id}"
    staging.mkdir(parents=True, exist_ok=False)
    module_root = Path(__file__).resolve().parent
    try:
        bundle_dir, entry_module = shared_worker_bundle(module_root, "project")
        _stage_project_assets(Path(project_root), staging)
        request = {
            "schema": PROJECT_WORKER_SCHEMA,
            "source": source,
            "inputs": {},
            "param_values": param_values,
            "net_values": net_values,
            "board_values": board_values,
            "mount_values": mount_values,
            "cage_values": cage_values,
            "api_contracts": _project_api_contracts(),
            "document_name": str(captured["document_name"]),
            "document_uid": str(captured["document_uid"]),
            "document_objects": list(captured["document_objects"]),
            "max_operations": 400_000,
            "max_seconds": float(captured["timeout_seconds"]),
            "memory_limit_bytes": int(captured["memory_limit_bytes"]),
            "cpu_limit_seconds": max(1, int(float(captured["timeout_seconds"]))),
            "output_limit_bytes": 256 * 1024 * 1024,
        }
        if display_request is not None:
            request["display"] = display_request
        if captured.get("measure_fit") is False:
            # A restore proving the accepted digest (ADR-630). Not a recipe
            # key, so the drift comparison reads this attempt as it did.
            request["measure_fit"] = False
        _atomic_json(staging / "request.json", request)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    # The script file IS the working artifact: persist before execution, so a
    # host that dies mid-run still has the source that was running. A run that
    # *fails* rolls this back (record_project_candidate_failure): a candidate
    # the engine refused must never survive as the working source, because the
    # restore pass re-runs the working source at every open and a script that
    # raises would then lock the project shut (ADR-044). Nothing is lost by the
    # rollback -- the refused source stays in this attempt's request.json,
    # located by `latest_candidate`.
    store.write(
        source=source,
        state_updates={
            "param_values": param_values,
            "net_values": net_values,
            "board_values": board_values,
            "working_revision": revision,
        },
    )
    return {
        "tool_name": tool_name,
        "operation": operation,
        "arguments": arguments,
        "pack": captured["pack"],
        "program_id": "project",
        "revision": revision,
        "source_before": current_source,
        "working_revision_before": working_revision,
        "param_values_before": dict(state.get("param_values") or {}),
        "net_values_before": [
            dict(row) for row in list(state.get("net_values") or [])
        ],
        "board_values_before": [
            dict(row) for row in list(state.get("board_values") or [])
        ],
        "mount_values_before": [
            dict(row) for row in list(state.get("mount_values") or [])
        ],
        "cage_values_before": [
            dict(row) for row in list(state.get("cage_values") or [])
        ],
        "accepted_revision_before": str(state.get("accepted_revision") or ""),
        "accepted_contract_before": state.get("accepted_contract"),
        "accepted_digest_before": str(state.get("accepted_digest") or ""),
        "source": source,
        "param_values": param_values,
        "net_values": net_values,
        "board_values": board_values,
        "mount_values": mount_values,
        "cage_values": cage_values,
        "param_specs_before": list(state.get("param_specs") or []),
        "net_specs_before": dict(state.get("net_specs") or {}),
        "board_specs_before": dict(state.get("board_specs") or {}),
        "mount_specs_before": dict(state.get("mount_specs") or {}),
        "cage_specs_before": dict(state.get("cage_specs") or {}),
        "project_root": project_root,
        "staging": str(staging),
        "bundle_dir": str(bundle_dir),
        "entry_module": str(entry_module),
        "attempt_id": attempt_id,
        "freecadcmd_executable": str(freecadcmd_executable),
        "timeout_seconds": float(captured["timeout_seconds"]),
        "memory_limit_bytes": int(captured["memory_limit_bytes"]),
        "document_name": str(captured["document_name"]),
        "document_uid": str(captured["document_uid"]),
        "document_revision": str(captured["document_revision"]),
        "document_objects": list(captured["document_objects"]),
    }


def record_project_candidate_failure(
    prepared: Mapping[str, Any], failure: Mapping[str, Any]
) -> None:
    """Roll the working script back, then record the failed candidate.

    ``prepare_project_candidate`` writes the candidate source to ``script.py``
    before running it. If the run failed, that file now holds a source the
    engine refused — and ``open_project``'s restore pass re-runs the working
    source at every open. A candidate that raises would therefore fail every
    subsequent open, including the ``write_script`` the failure report tells
    the caller to perform: one refused edit would brick the project until a
    human restored the ``.cadex`` directory from a backup (ADR-044).

    So a failed candidate leaves no trace in the working state. The refused
    source is still recoverable from its attempt's ``request.json``, which
    ``latest_candidate`` locates.
    """

    from CadexScriptStore import CadexProjectScriptStore

    store = CadexProjectScriptStore(str(prepared["project_root"]))
    store.write(
        source=str(prepared.get("source_before") or ""),
        state_updates={
            "param_values": dict(prepared.get("param_values_before") or {}),
            "net_values": [
                dict(row) for row in list(prepared.get("net_values_before") or [])
            ],
            "board_values": [
                dict(row) for row in list(prepared.get("board_values_before") or [])
            ],
            "mount_values": [
                dict(row) for row in list(prepared.get("mount_values_before") or [])
            ],
            "cage_values": [
                dict(row) for row in list(prepared.get("cage_values_before") or [])
            ],
            "working_revision": str(prepared.get("working_revision_before") or ""),
            "latest_candidate": {
                "status": "failed",
                "revision": str(prepared["revision"]),
                "attempt_id": str(prepared["attempt_id"]),
                "failure_code": str(failure.get("failure_code") or ""),
                "error": str(failure.get("error") or ""),
            },
        }
    )


def validate_project_result(
    prepared: dict[str, Any], execution: Mapping[str, Any]
) -> dict[str, Any]:
    """Check the worker report, record the contract, persist working state."""

    from CadexScriptStore import CadexProjectScriptStore
    from CadexScriptedDomainPublication import publishable_output_type

    tool_name = str(prepared["tool_name"])
    if execution.get("schema") != PROJECT_WORKER_SCHEMA:
        _raise(
            tool_name,
            "DOMAIN_WORKER_RESULT_INVALID",
            "postcondition",
            f"Unexpected project worker schema {execution.get('schema')!r}.",
        )
    outputs = list(execution.get("outputs") or [])
    if not outputs:
        _raise(
            tool_name,
            "DOMAIN_RESULT_INVALID",
            "postcondition",
            "The project worker returned no outputs.",
        )
    digest = str(execution.get("digest") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        _raise(
            tool_name,
            "DOMAIN_RESULT_INVALID",
            "postcondition",
            "The project worker returned no content digest.",
        )
    param_specs = list(execution.get("param_specs") or [])
    contract: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in outputs:
        if not isinstance(item, Mapping):
            _raise(
                tool_name,
                "DOMAIN_RESULT_INVALID",
                "postcondition",
                "Every project worker output must be an object.",
            )
        name = str(item.get("name") or "")
        domain = str(item.get("domain") or "")
        output_type = str(item.get("type") or "")
        if not name or name in seen or domain not in {
            "sketcher",
            "part",
            "partdesign",
            "mesh",
            "assembly",
        }:
            _raise(
                tool_name,
                "DOMAIN_RESULT_INVALID",
                "postcondition",
                f"Project output {name!r} has an invalid identity.",
                observed={"name": name, "domain": domain, "type": output_type},
            )
        seen.add(name)
        if not publishable_output_type(output_type):
            # Refused here, before the document is touched: an argument
            # value in `result` used to raise half-way through the assembly
            # pass (ADR-434).
            _raise(
                tool_name,
                "PROJECT_OUTPUT_UNPUBLISHABLE",
                "postcondition",
                f"Project output {name!r} is a `{domain}.{output_type}` value, "
                "which is an argument to another call and cannot be published "
                f"on its own. Remove {name!r} from `result` and pass it to the "
                "call that uses it"
                + (
                    " (assembly.mjcf(..., actuators=[...]) and "
                    "assembly.task(..., actions=[...]))."
                    if output_type == "actuator"
                    else "."
                ),
                observed={"name": name, "domain": domain, "type": output_type},
            )
        if str(item.get("artifact_kind") or "") == "brep":
            path = _staged_artifact_path(
                prepared,
                item.get("artifact_path"),
                context=f"Project output {name!r}",
            )
            # Import the detached shape off the document thread now so
            # publication applies validated values without artifact I/O.
            import Part

            shape = Part.Shape()
            shape.importBrep(str(path))
            if shape.isNull() or not shape.isValid():
                _raise(
                    tool_name,
                    "DOMAIN_RESULT_INVALID",
                    "postcondition",
                    f"Project output {name!r} BREP artifact is invalid.",
                )
            item["detached_shape"] = shape
        elif str(item.get("artifact_kind") or "") == "mesh":
            path = _staged_artifact_path(
                prepared,
                item.get("artifact_path"),
                context=f"Project output {name!r}",
            )
            # Import the detached native mesh off the document thread now so
            # publication applies validated values without artifact I/O.
            import Mesh

            mesh = Mesh.Mesh()
            mesh.read(Filename=str(path))
            if int(mesh.CountFacets) <= 0:
                _raise(
                    tool_name,
                    "DOMAIN_RESULT_INVALID",
                    "postcondition",
                    f"Project output {name!r} mesh artifact is empty.",
                )
            item["detached_mesh"] = mesh
        display = item.get("display")
        if isinstance(display, Mapping):
            # Display artifacts are derived data (Phase 5.1): verify both the
            # buffer and its sidecar are real staged files, nothing more.
            try:
                _staged_artifact_path(
                    prepared,
                    display.get("artifact_path"),
                    context=f"Project output {name!r} display buffer",
                )
                _staged_artifact_path(
                    prepared,
                    display.get("sidecar_path"),
                    context=f"Project output {name!r} display sidecar",
                )
            except ValueError as exc:
                _raise(
                    tool_name,
                    "DOMAIN_RESULT_INVALID",
                    "postcondition",
                    str(exc),
                )
        contract.append({"name": name, "type": output_type, "domain": domain})

    # Durable working revision binds the worker-collected parameter specs --
    # and only the values those specs declare. A script that drops a parameter
    # leaves its value behind otherwise, and a stale value is what used to
    # wedge `set_params` forever (ADR-039). Pruning here is what heals a store
    # that is already stale: `open_project`'s restore pass and `rebuild` both
    # come through this path. It is digest-neutral -- the worker resolves
    # declared parameters by name and ignores every other key -- so only the
    # revision moves, and `final_revision` below, `working_revision` here and
    # `accepted_revision` in accept_project_candidate all derive from this
    # same pruned dict.
    declared_names = {str(spec.get("name") or "") for spec in param_specs}
    prepared["param_values"] = {
        name: value
        for name, value in dict(prepared["param_values"]).items()
        if name in declared_names
    }
    # The same pruning, for the same reason, on the connection table: a
    # stored row naming a port the rewritten script no longer declares is
    # dropped here rather than left to wedge the editor (ADR-039, ADR-065).
    # Digest-neutral for the identical reason -- the collector resolves the
    # declared ports by name and never reads the rest.
    from CadexNets import declared_ports, prune_rows

    net_specs = dict(execution.get("net_specs") or {})
    prepared["net_values"] = prune_rows(
        list(prepared.get("net_values") or []), declared_ports(net_specs)
    )
    # The board table, pruned the same way -- and with one thing the other two
    # tables do not have: a row measured in the viewport arrived carrying
    # ``frame="world"``, because the shell has no way to know a board's own
    # frame and ``cadexd`` has no geometry to convert it with. The worker did
    # the conversion against the placement chain it actually resolved, and the
    # canonical board-frame row it produced is written back here, replacing the
    # world one. That is what makes the conversion happen exactly once: every
    # later run reads a row that is already in the board's frame (ADR-120).
    from CadexBoards import prune_terminal_rows

    board_specs = dict(execution.get("board_specs") or {})
    converted = {
        (str(row.get("board") or ""), str(row.get("name") or "")): dict(row)
        for row in list(execution.get("board_rows_converted") or [])
    }
    board_values = []
    for row in list(prepared.get("board_values") or []):
        key = (str(row.get("board") or ""), str(row.get("name") or ""))
        board_values.append(converted.get(key) or {
            field: value for field, value in dict(row).items() if field != "frame"
        })
    prepared["board_values"] = prune_terminal_rows(board_values, board_specs)
    # ...and the mount table, on identical terms (ADR-126): pruned against
    # what the script still declares, and with every ``frame="world"`` row
    # replaced by the component-frame row the worker converted, so a mount
    # measured in the viewport is carried across exactly once.
    from CadexMounts import prune_mount_rows

    mount_specs = dict(execution.get("mount_specs") or {})
    converted_mounts = {
        (str(row.get("component") or ""), str(row.get("name") or "")): dict(row)
        for row in list(execution.get("mount_rows_converted") or [])
    }
    mount_values = []
    for row in list(prepared.get("mount_values") or []):
        key = (str(row.get("component") or ""), str(row.get("name") or ""))
        mount_values.append(converted_mounts.get(key) or {
            field: value for field, value in dict(row).items() if field != "frame"
        })
    prepared["mount_values"] = prune_mount_rows(mount_values, mount_specs)
    # ...and the cage, pruned the same way. A ring row carries no world frame
    # to convert: the overlay drags a ring along a spine the script declared,
    # so what comes back is already in the cage's own terms (ADR-127).
    from CadexCage import prune_ring_rows

    cage_specs = dict(execution.get("cage_specs") or {})
    prepared["cage_values"] = prune_ring_rows(
        list(prepared.get("cage_values") or []), cage_specs
    )
    # There is deliberately nothing here for the printable marks (ADR-158).
    # ADR-156 harvested a roster into the store at this point and pruned the
    # marks against it; both are gone. The roster is derived from this run's
    # own worker report when somebody asks for it, and the marks are the
    # shell's — so a rebuild that stops publishing a part costs this path no
    # code at all.
    store = CadexProjectScriptStore(str(prepared["project_root"]))
    final_revision = contracts.project_script_revision(
        source=str(prepared["source"]),
        param_specs=param_specs,
        param_values=dict(prepared["param_values"]),
        net_specs=net_specs,
        net_values=list(prepared["net_values"]),
        board_specs=board_specs,
        board_values=list(prepared["board_values"]),
        mount_specs=mount_specs,
        mount_values=list(prepared["mount_values"]),
        cage_specs=cage_specs,
        cage_values=list(prepared["cage_values"]),
    )
    store.write(
        state_updates={
            "param_specs": param_specs,
            "param_values": dict(prepared["param_values"]),
            "net_specs": net_specs,
            "net_values": list(prepared["net_values"]),
            "board_specs": board_specs,
            "board_values": list(prepared["board_values"]),
            "mount_specs": mount_specs,
            "mount_values": list(prepared["mount_values"]),
            "cage_specs": cage_specs,
            "cage_values": list(prepared["cage_values"]),
            "working_revision": final_revision,
            "latest_candidate": {
                "status": "validated",
                "revision": final_revision,
                "attempt_id": str(prepared["attempt_id"]),
                "digest": digest,
                "output_count": len(contract),
            },
        }
    )
    prepared["revision"] = final_revision
    return {
        "ok": True,
        "outputs": outputs,
        "contract": contract,
        "digest": digest,
        "param_specs": param_specs,
        "net_specs": net_specs,
        "board_specs": board_specs,
        "mount_specs": mount_specs,
        "cage_specs": cage_specs,
        "validations": dict(execution.get("validations") or {}),
        "component_sources": dict(execution.get("component_sources") or {}),
        "stdout": str(execution.get("stdout") or ""),
        "budget": dict(execution.get("budget") or {}),
    }


def accept_project_candidate(
    prepared: Mapping[str, Any],
    publication: Mapping[str, Any],
    validated: Mapping[str, Any],
    *,
    prune_artifacts: bool = True,
) -> dict[str, Any]:
    """Persist the accepted project revision/contract/digest; return the tool payload."""

    from CadexScriptStore import CadexProjectScriptStore

    revision = str(prepared["revision"])
    digest = str(validated["digest"])
    contract = [dict(item) for item in list(validated["contract"])]
    store = CadexProjectScriptStore(str(prepared["project_root"]))
    staging_relative = (
        Path(str(prepared["staging"]))
        .relative_to(Path(str(prepared["project_root"])))
        .as_posix()
    )
    accepted_attempt = {
        "attempt_id": str(prepared["attempt_id"]),
        "staging": staging_relative,
        "revision": revision,
    }
    previous = store.read_state()
    retained = previous.get("accepted_attempt")
    # Restore publishes fresh live geometry without requesting display buffers.
    # An identical acceptance must not replace the durable, display-bearing
    # attempt with that display-less replay. Keep it pinned against pruning.
    # Explicit display requests and changed identities publish the new attempt.
    if (
        previous.get("accepted_revision") == revision
        and previous.get("accepted_digest") == digest
        and not dict(prepared.get("arguments") or {}).get("display")
        and isinstance(retained, dict)
        and retained.get("staging")
        and (store.root / str(retained["staging"]) / "result.json").is_file()
    ):
        accepted_attempt = retained
    store.write(
        state_updates={
            "accepted_revision": revision,
            "accepted_contract": contract,
            "accepted_digest": digest,
            "accepted_attempt": accepted_attempt,
            "latest_candidate": {
                "status": "accepted",
                "revision": revision,
                "attempt_id": str(prepared["attempt_id"]),
                "digest": digest,
                "output_count": len(contract),
            },
        }
    )
    # The undo trail, and the reason the store stops growing without bound
    # (ADR-045). Both are best-effort: a project that cannot write its
    # history has still accepted a revision, and failing the run over that
    # would be the tail wagging the dog.
    try:
        # At acceptance `script.py` holds exactly the source being accepted
        # (prepare wrote it before the run), so it is the fallback rather
        # than a guess.
        source = str(prepared.get("source") or "") or store.read_source()
        store.record_history(revision, source, contract, values={
            "params": dict(prepared.get("param_values") or {}),
            "nets": list(prepared.get("net_values") or []),
            "boards": list(prepared.get("board_values") or []),
            "mounts": list(prepared.get("mount_values") or []),
            "cages": list(prepared.get("cage_values") or []),
        }, digest=digest)
    except OSError:
        pass
    if prune_artifacts:
        try:
            store.prune_artifacts()
        except OSError:
            pass
    return {
        "ok": True,
        "tool": str(prepared["tool_name"]),
        "outputs": contract,
        "live_outputs": dict(publication.get("live_outputs") or {}),
        "digest": digest,
        "revision": revision,
        "accepted_revision": revision,
        "removed": list(publication.get("removed") or []),
        # The script's own stdout. The failure envelope has always carried it;
        # dropping it here made `print()` work only when the run broke, which
        # left "make the script fail on purpose" as the only way to read a
        # value out of a working script (ADR-044).
        "stdout": str(validated.get("stdout") or ""),
        "model_state": {
            "status": "accepted",
            "accepted_is_current": True,
            "next_write_expected_revision": revision,
            "verification_goal": (
                "Confirm accepted_revision equals working_revision and every "
                "declared output has a live published object."
            ),
        },
    }


def dropped_outputs(
    prepared: Mapping[str, Any], validated: Mapping[str, Any]
) -> list[str]:
    """Accepted output names this candidate would silently remove (ADR-045).

    ``write_script`` replaces THE project script, and a model asked to "add a
    battery" can answer with a script containing only a battery — which
    builds, publishes, and is accepted, taking the rest of the project with
    it. Nothing about that run looks like a failure, so nothing catches it;
    the user finds out by looking at an empty viewport.

    Only ``write_script`` is checked, and only against the *accepted*
    contract. ``edit_script`` is a targeted replacement and ``set_params``
    does not touch the source, so neither can drop an output by accident.
    Deleting a part on purpose stays one ``replace=true`` away.
    """

    if str(prepared.get("operation") or "") != "write_script":
        return []
    arguments = dict(prepared.get("arguments") or {})
    if bool(arguments.get("replace")):
        return []
    before = {
        str(item.get("name"))
        for item in (prepared.get("accepted_contract_before") or [])
        if isinstance(item, Mapping) and item.get("name")
    }
    if not before:
        return []
    after = {
        str(item.get("name"))
        for item in (validated.get("contract") or [])
        if isinstance(item, Mapping) and item.get("name")
    }
    return sorted(before - after)


def candidate_model_state(prepared: Mapping[str, Any]) -> dict[str, Any]:
    """Model-facing state block attached to every failed candidate payload.

    ``next_write_expected_revision`` is the durable working revision from the
    script store (validate_project_result may have re-bound it with the
    worker-collected parameter specs).
    """

    try:
        from CadexScriptStore import CadexProjectScriptStore

        working = str(
            CadexProjectScriptStore(str(prepared["project_root"]))
            .read_state()
            .get("working_revision")
            or ""
        )
    except Exception:
        working = str(prepared["revision"])
    accepted = str(prepared.get("accepted_revision_before") or "")
    return {
        "status": "working_candidate_not_accepted",
        "program_id": "project",
        "working_revision": working,
        "accepted_revision": accepted,
        "accepted_live_state_preserved": bool(accepted),
        "next_write_expected_revision": working,
        "inspection_call": {
            "tool": "core.inspect",
            "arguments": {
                "scope": "script",
                "target": "",
                "path": "",
                "offset": 0,
                "limit": 50,
                "attach": False,
            },
        },
        "repair_rule": (
            "Inspect the script when the source or latest revision is "
            "uncertain, then repair the smallest exact cause. Use "
            "edit_script for unique targeted replacements, write_script "
            "for a full rewrite, and set_params for value-only parameter "
            "changes."
        ),
    }


def run_project_lifecycle(
    service: Any,
    tool_name: str,
    args: Mapping[str, Any],
    *,
    cancellation_check: Callable[[], bool] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    result_sink: dict[str, Any] | None = None,
    prune_artifacts: bool = True,
    measure_fit: bool = True,
) -> dict[str, Any]:
    """One complete inline project lifecycle: capture → prepare → execute →
    validate → publish → accept.

    This is the single engine-side entry shared by cadexd and the headless
    rebuild driver (Phase 5.3). Everything runs on the calling thread — the
    caller owns any document-thread marshalling. Payloads (accept payload /
    ``tool_failure`` envelope) are exactly what the in-process session tool
    produced, so protocol clients see an unchanged contract. When
    ``result_sink`` is given, ``prepared`` and ``validated`` are stored in it
    on success so the caller can reach staged artifacts (display buffers).
    A restore caller passes ``prune_artifacts=False`` and prunes only after
    settling the accepted pin: this acceptance is provisional until then.
    It may also pass ``measure_fit=False`` (ADR-630): the worker then skips
    the static and swept fit, which no digest covers, because the attempt
    reads are served from stays the one the project already accepted.
    """

    from CadexScriptedDomainPublication import publish_project_candidate

    args = dict(args)

    def emit(event: dict[str, Any]) -> None:
        if progress_callback is not None:
            progress_callback(event)

    operation = parse_project_tool(tool_name)
    if operation is None:
        return tool_failure(
            tool_name,
            "UNKNOWN_PROJECT_TOOL",
            "surface",
            f"Unknown project XScript tool: {tool_name}.",
            requested=args,
        )
    if operation == "describe_api":
        return describe_project_api()
    prepared = None
    try:
        captured = capture_project_state(service, tool_name, args)
        if not measure_fit:
            captured = {**captured, "measure_fit": False}
        prepared = prepare_project_candidate(captured)
        emit(
            {
                "event": "cadex_domain_worker_started",
                "domain": "project",
                "program_id": "project",
                "revision": prepared["revision"],
            }
        )
        execution = execute_candidate(prepared, cancellation_check=cancellation_check)
        if execution.get("ok") is not True:
            record_project_candidate_failure(prepared, execution)
            execution["model_state"] = candidate_model_state(prepared)
            return execution
        try:
            validated = validate_project_result(prepared, execution)
        except DomainRuntimeFailure as exc:
            record_project_candidate_failure(prepared, exc.payload)
            exc.payload["model_state"] = candidate_model_state(prepared)
            return exc.payload
        except Exception as exc:
            failure = tool_failure(
                tool_name,
                "DOMAIN_RESULT_INVALID",
                "postcondition",
                str(exc),
                requested=args,
                observed={"exception_type": exc.__class__.__name__},
            )
            record_project_candidate_failure(prepared, failure)
            failure["model_state"] = candidate_model_state(prepared)
            return failure
        dropped = dropped_outputs(prepared, validated)
        if dropped:
            failure = tool_failure(
                tool_name,
                "PROJECT_OUTPUTS_DROPPED",
                "postcondition",
                "This script drops {:s} that the accepted revision "
                "declares: {:s}. write_script replaces THE whole project "
                "script -- to add a part, edit the script you have. Pass "
                "replace=true if removing {:s} is what you meant.".format(
                    "an output" if len(dropped) == 1 else "outputs",
                    ", ".join(dropped),
                    "it" if len(dropped) == 1 else "them",
                ),
                requested={"replace": bool(args.get("replace"))},
                observed={"dropped_outputs": dropped},
            )
            record_project_candidate_failure(prepared, failure)
            failure["model_state"] = candidate_model_state(prepared)
            return failure
        try:
            publication = publish_project_candidate(service, prepared, validated)
        except Exception as exc:
            failure = tool_failure(
                tool_name,
                "DOMAIN_PUBLICATION_FAILED",
                "native_call",
                str(exc),
                requested=args,
                observed={"exception_type": exc.__class__.__name__},
            )
            record_project_candidate_failure(prepared, failure)
            failure["model_state"] = candidate_model_state(prepared)
            return failure
        payload = accept_project_candidate(
            prepared, publication, validated, prune_artifacts=prune_artifacts
        )
        if result_sink is not None:
            result_sink["prepared"] = prepared
            result_sink["validated"] = validated
        emit(
            {
                "event": "xscript_domain_publication_completed",
                "domain": "project",
                "program_id": "project",
                "revision": prepared["revision"],
                "output_count": len(payload.get("outputs") or []),
            }
        )
        return payload
    except DomainRuntimeFailure as exc:
        if prepared is not None:
            try:
                record_project_candidate_failure(prepared, exc.payload)
                exc.payload["model_state"] = candidate_model_state(prepared)
            except Exception:
                pass
        return exc.payload
    except Exception as exc:
        return tool_failure(
            tool_name,
            "DOMAIN_LIFECYCLE_FAILED",
            "external_process",
            str(exc),
            requested=args,
            observed={"exception_type": exc.__class__.__name__},
        )


def _capability_api_listing() -> dict[str, dict[str, Any]]:
    """Export listing (name/signature/doc) for each capability-domain API.

    The same listing style the retired per-domain describe_api adapters used,
    generated from the actual runtime API objects so it can never drift from
    the worker contract.
    """

    listing: dict[str, dict[str, Any]] = {}
    for pack in contracts.XSCRIPT_WORKBENCH_PACKS.values():
        api = create_domain_api(pack.domain, pack.api_exports, pack.output_types)
        exports = []
        for name in api.exported_names:
            member = getattr(api, name)
            exports.append(
                {
                    "name": name,
                    "signature": str(_inspect.signature(member)),
                    "description": str(_inspect.getdoc(member) or ""),
                }
            )
        listing[pack.domain] = {
            "api_global": pack.domain,
            "exports": exports,
            "accepted_output_types": list(pack.output_types),
        }
    listing["mesh"]["notes"] = (
        "In a project script mesh.from_shape(shape, ...) takes a part value "
        "created in the same script, and mesh.import_file(name) reads one "
        "STL/OBJ/PLY file placed directly in the project assets directory."
    )
    listing["part"]["notes"] = (
        "part.import_part(name) reads one .cxpart file placed directly in the "
        "project assets directory and yields the exact OCCT solid another "
        "project accepted. It is the lossless counterpart of "
        "part.shape_from_mesh: that one converts triangles and lands a shell "
        "of thousands of planar faces that selectors are near-useless on, "
        "this one carries the BREP itself, so subshape, fillet and booleans "
        "behave as they do on a solid built here, and assembly.component "
        "takes it like any other part value. It is a snapshot rather than a "
        "live link: the file changes only when the part is linked again, so "
        "a rebuild never depends on another project's current state. A "
        ".cxpart arrives through the link_part op, which is not a script "
        "surface -- a script that needs one and has none says so and stops. "
        "part.measurement(shape, kind=...) declares a dimension the viewport "
        "draws over the model: kind='distance' with start=/end= selectors "
        "measures between two subshapes, kind='diameter' with an at= selector "
        "measures one circular edge or cylindrical face, and kind='extent' "
        "with axis='x'|'y'|'z' measures the shape's overall span -- which is "
        "what 'the height of the part' means on anything that is not a box. "
        "element_type='face'|'edge' says which topology the selectors resolve "
        "against and applies to both ends. It is a declared output carrying "
        "no geometry, so return it in the result dict like any other output; "
        "it measures the shape it is given, so it follows a parameter that "
        "moves that shape."
    )
    listing["assembly"]["notes"] = (
        "In a project script assembly.component(source, ...) takes a part or "
        "partdesign value created in the same script; cross-document component "
        "references are not supported and every component source must also be "
        "a declared result output. "
        "assembly.dynamics(...) is the dynamics counterpart of "
        "assembly.simulation: it needs one assembly.body(component, "
        "density_kg_m3=...) per component and runs the mechanism under gravity "
        "instead of prescribing its motion, so a script uses api.motion or "
        "api.dynamics and never both. Both produce a simulation output and a "
        "script may declare exactly one. Density has no default (steel 7850, "
        "aluminium 2700). A body touches nothing until it is given "
        "assembly.collision(kind, ...) shapes -- 'box'/'sphere'/'cylinder'/"
        "'capsule' primitives placed with offset=, 'plane' for ground, or "
        "'mesh' for the component's own shape. A plane's surface passes "
        "through the component origin facing local +Z, so a floor needs no "
        "offset (size_mm: see assembly.collision). Prefer it for ground. "
        "Prefer primitives: MuJoCo collides with the "
        "convex hull of any mesh, so 'mesh' refuses a concave part and names "
        "its volume error, and 'hull' is how a script accepts that hull "
        "deliberately. gravity_m_s2 is a vector in m/s^2 (Earth by default); "
        "a bouncing contact needs solver_step_s=0.001 or finer and is refused "
        "without it. "
        "distance, parallel, perpendicular, angle and "
        "rack_pinion joints are refused by a dynamics run. "
        "assembly.actuator(joint, kind=...) drives one joint coordinate and "
        "is passed to assembly.dynamics(..., actuators=[...]): 'position' is "
        "a servo told where to be (control_deg plus stiffness_nmm_per_deg), "
        "'velocity' one told how fast (control_deg_per_s plus "
        "damping_nmms_per_deg), 'motor' a raw effort (control_nmm). Every "
        "control is a formula of time in seconds written as a string, the "
        "same vocabulary api.motion takes but with no initialValue. Units are "
        "in the parameter names and the wrong one is refused: a joint that "
        "slides takes control_mm, stiffness_n_per_mm and force_limit_n, and a "
        "cylindrical joint needs an explicit motion_type. "
        "assembly.joint_dynamics(joint, damping_nmms_per_deg=..., "
        "armature_kgmm2=..., friction_loss_nmm=...) goes in the same call's "
        "joint_dynamics=[...]; MuJoCo's defaults for all three are zero, so a "
        "stiff position actuator on an otherwise bare joint oscillates and "
        "does not settle. A loop closes as a connect or weld: drive its crank. "
        "A closing hinge whose axis must tilt is refused (use a ball end); "
        "a fast loop needs solver_step_s=0.0005. Closing, coupled, fixed, "
        "ball and suppressed joints cannot be driven or damped; each says why. "
        "assembly.mjcf(assembly, bodies, ...) exports that same model as one "
        "self-contained MuJoCo MJCF file instead of running it: same bodies, "
        "same actuators, same joint_dynamics, same gravity_m_s2 and "
        "solver_step_s, and nothing integrated. It carries the exact OCCT mass and inertia "
        "and a keyframe named 'solved' holding the pose the assembly solver "
        "produced -- MuJoCo's own reference pose is the one where each "
        "joint's connector frames coincide, so a reader must reset to that "
        "keyframe. Only collision geometry is exported, so a mechanism "
        "with no assembly.collision shapes is invisible in MuJoCo's viewer. "
        "assembly.task(model, actions=[...], reward=[...], "
        "episode_seconds=..., control_hz=...) turns one assembly.mjcf value "
        "into a trainable RL task and writes one JSON "
        "bundle beside that model's file; two tasks may share one model. "
        "The observation space is declared on the model, not the task: "
        "assembly.mjcf(..., observations=[assembly.observation(target, kind, "
        "name=...)]) writes each channel into the exported file as a MuJoCo "
        "sensor, so stock MuJoCo computes the observation vector. The kinds "
        "are 'position'/'velocity' on a joint, 'component_position'/"
        "'component_orientation'/'component_linear_velocity'/"
        "'component_angular_velocity'/'centre_of_mass'/"
        "'centre_of_mass_velocity'/'centroidal_angular_momentum' on a "
        "component, 'tracked_position' (then optionally 'tracked_velocity') "
        "on a body a 'position_tracker' sensor reads, and "
        "'actuator_force' on an actuator, which a 'load_sensor' grounds "
        "(lib.servo(sku).load_sensor on a bus servo). Values reach a trainer "
        "in this API's units (degrees, mm, N*mm) via a bundled scale. A vector channel expands to suffixed scalar "
        "names: name='hand' on a component_position is hand_x, hand_y and "
        "hand_z, the names a reward writes. "
        "assembly.reward(expression, weight=...) terms are summed and a "
        "policy maximises the total; a cost is a positive quantity with a "
        "negative weight. An expression names the task's channels and may "
        "call abs, asin/arcsin, arctan, cos, sin, exp, sqrt and tanh. "
        "assembly.termination(expression, above=...) or below=... ends an "
        "episode early, which tells a failure from a horizon. "
        "assembly.randomise(target, 'mass'|'damping'|'armature'|"
        "'friction_loss', scale=[low, high]) varies one property per "
        "episode; a mass draw scales the inertia with it. "
        "assembly.reset_variation(component, tilt_degrees=[low, high], "
        "height_mm=[low, high], angular_velocity_dps=[low, high], "
        "linear_velocity_mm_s=[low, high]) starts "
        "each episode somewhere else, and assembly.disturbance(component, "
        "newtons=[low, high], direction='horizontal'|'vertical', "
        "azimuth_degrees=[low, high], "
        "at_seconds=[low, high], duration_s=..., sustained=False) pushes it "
        "while the episode runs -- one entry is one event, and "
        "sustained=True acts for the whole episode, as wind does. Both go to api.task as lists, like a randomisation. "
        "A reset variation moves the floating base RIGIDLY (a drawn tilt, "
        "a lift, a spin), never joint angles; a tilt that does not clear "
        "the floor at the declared lift is refused, with the millimetres. "
        "linear_velocity_mm_s is a stumble: a speed with its direction drawn. "
        "A disturbance's "
        "force acts at the component's centre of mass in the world frame, and "
        "azimuth_degrees=[low, high] narrows a horizontal push to an arc "
        "where 0 degrees is WORLD +X, anticlockwise seen from above "
        "(omitted: the whole circle; refused on a vertical push); work out "
        "which world axis is forward first. "
        "assembly.goal(name, kind='value'|'speed'|'point'|'phase', ...) in "
        "api.task(goals=[...]) is what each episode ASKS for -- a commanded "
        "speed, a point its tip can reach -- drawn per episode, observed by "
        "the policy and named by a reward like a channel; frame=base holds "
        "a point in base's frame; a phase (period_seconds=T) is a clock, "
        "name_sin and name_cos. "
        "actions=[...] names assembly.actuator values, and each one's range "
        "is derived from the mechanism or refused rather than defaulted: a "
        "motor is bounded by its torque_limit_nmm/force_limit_n and a "
        "position servo by its joint's own limits with both endpoints "
        "declared. A velocity actuator has no derivable range: a joint "
        "states no speed limit. A "
        "position servo may narrow what a policy is allowed to ask for "
        "with command_limits_degrees=[-25, 25] (command_limits_mm when it "
        "slides): both endpoints required, refused if it reaches outside "
        "the joint's own travel, and it changes only the action table: "
        "the joint keeps its full travel. Each "
        "actuator keeps its control formula, which becomes its deterministic "
        "action when no policy is driving. "
        "assembly.policy(task, weights='walk.cxpolicy', sha256='<64 hex>') "
        "declares a trained control policy for one task. Training does not "
        "run in the engine and cannot: it needs JAX on a GPU. The trainer is "
        "training/cadex_train.py in the repository, it runs on a machine that "
        "has one, and the .cxpolicy file it writes is brought back with "
        "put_asset like any other asset -- so weights= names a file in the "
        "project assets directory. sha256 is required and never inferred: a "
        "policy is the one part of a project that cannot be rebuilt from the "
        "script, so the script carries which bytes it meant and the engine "
        "refuses anything else, naming the digest it observed. Before "
        "publishing, the engine checks the policy against the task it claims "
        "-- the bundle's digest, the model that bundle references, the "
        "observation channels in order, the action table, and the output map "
        "the task's action ranges imply -- and re-evaluates the witness the "
        "trainer recorded with its own forward pass: a network it reads "
        "differently is refused rather than run. "
        "assembly.rollout(policy, frames_per_second=..., seed=...) plays one "
        "trained policy against its own task and produces a simulation trace "
        "-- the same output api.simulation and api.dynamics produce, so a "
        "script has exactly one of the three and a rollout cannot sit beside "
        "assembly.motion. The policy it names must also be returned as an "
        "output, because an unpublished policy is one the engine has not "
        "verified. The model is reloaded from the file the task bundle names, "
        "so the rollout runs the exact model the policy's digest attests to. "
        "frames_per_second must divide the task's control_hz exactly and "
        "defaults to it, which is one frame per control step; the refusal "
        "lists the rates that task can be played at. seed draws the task's "
        "assembly.randomise entries for this one episode, and without it "
        "nothing is randomised."
    )
    return listing


def _library_listing() -> dict[str, Any]:
    """The parts-library section of describe_api (ADR-181).

    Generated from the same runtime class the worker stages as ``lib``, so
    the browsable catalog and the callable surface cannot drift apart.
    """

    from cadex_library_api import library_listing

    listing = library_listing()
    listing["part_classes"] = _library_part_classes()
    return listing


def _library_part_classes() -> list[dict[str, Any]]:
    """What a lib generator hands back, and what can be called on it (ADR-619).

    ``lib.qdd(...)`` returns a ``QddPart`` whose ``.actuator``,
    ``.joint_dynamics`` and ``.bay`` are the calls a design needs, and the
    library section listed only the generators: six audited sessions guessed
    at those methods or read them out of a refusal. Generated from the
    classes themselves -- every public class of ``cadex_library_api`` that a
    generator returns or that is a library part -- so the listing cannot
    drift from what a script can call.
    """

    import cadex_library_api as library

    def summary(text: Any) -> str:
        head = str(text or "").strip().split("\n\n", 1)[0]
        return " ".join(head.split())

    module_classes = {
        name: cls
        for name, cls in vars(library).items()
        if isinstance(cls, type) and cls.__module__ == library.__name__
    }
    #: class name -> the public calls annotated as returning it.
    returned_by: dict[str, list[str]] = {}
    for owner_name, owner in sorted(module_classes.items()):
        prefix = "lib" if owner is library.LibraryAPI else owner_name
        for name, member in sorted(vars(owner).items()):
            if name.startswith("_") or not callable(member):
                continue
            annotation = _inspect.signature(member).return_annotation
            label = annotation if isinstance(annotation, str) else getattr(annotation, "__name__", "")
            if label in module_classes:
                returned_by.setdefault(str(label), []).append(f"{prefix}.{name}")

    classes: list[dict[str, Any]] = []
    for name, cls in sorted(module_classes.items()):
        # Every public class but the API itself and its error is something a
        # call hands a script (BoardMounting is what BoardPart.mounting()
        # returns, unannotated).
        if name.startswith("_") or cls is library.LibraryAPI or issubclass(cls, Exception):
            continue
        attributes = sorted(
            {
                slot
                for klass in cls.__mro__
                for slot in getattr(klass, "__slots__", ())
                if not slot.startswith("_")
            }
        )
        methods = []
        for method_name in sorted(dir(cls)):
            if method_name.startswith("_"):
                continue
            member = getattr(cls, method_name)
            if not callable(member) or isinstance(member, type):
                continue
            signature = _inspect.signature(member)
            parameters = list(signature.parameters.values())
            if parameters and parameters[0].name == "self":
                signature = signature.replace(parameters=parameters[1:])
            methods.append(
                {
                    "name": method_name,
                    "signature": str(signature),
                    "description": summary(_inspect.getdoc(member)),
                }
            )
        classes.append(
            {
                "name": name,
                "description": summary(_inspect.getdoc(cls)),
                "returned_by": returned_by.get(name, []),
                "attributes": attributes,
                "methods": methods,
            }
        )
    return classes


def describe_project_api() -> dict[str, Any]:
    """The exact authoring contract for THE project script.

    Serves both the xscript.project.describe_api tool and core.inspect
    scope='api'.
    """

    pack = contracts.PROJECT_PACK
    return {
        "ok": True,
        "domain": pack.domain,
        "engine": pack.engine,
        "program_schema": pack.program_schema,
        "instructions": pack.instructions,
        "source_globals": [
            "sketcher",
            "part",
            "partdesign",
            "mesh",
            "assembly",
            "params",
            "num",
            "nets",
            "wire",
            "boards",
            "board",
            "term",
            "mounts",
            "mount_set",
            "mount",
            "cage",
            "section_cage",
            "ring",
            "lib",
        ],
        "domains": _capability_api_listing(),
        "library": _library_listing(),
        "connections": {
            "nets": (
                "USE THIS for any harness of two or more wires. A harness "
                "built from bare part.cable/part.bundle calls is READ-ONLY in "
                "the wiring editor — nothing outside the script text names a "
                "row, so the user cannot rewire, change a gauge or toggle a "
                "joint without spending a chat turn, and converting it later "
                "costs another one. "
                "nets(ports={'esp': esp_t, ...}, wires={'sda': wire(...), "
                "...}) declares the harness as a table; callable at most once "
                "per script. ports maps a lower_snake_case name to the "
                "TerminalSet part.terminals/mesh.terminals returned; wires "
                "maps a lower_snake_case row name to one wire(...). Iterate "
                "it with .items() and build each row with part.cable / "
                "part.bundle / part.solder as usual — w.a and w.b are real "
                "terminals, so the harness operations are unchanged."
            ),
            "wire": (
                "wire(a, b, gauge=..., solder=False, enabled=True, avoid=(), "
                "label='') declares one connection. Endpoints are "
                "'<port>.<terminal>' strings validated against the declared "
                "ports. a/b/gauge/solder/enabled are the editable columns; "
                "avoid and label are declaration-only and stay in the script, "
                "as does every other routing argument."
            ),
            "values": (
                "Stored rows from xscript.project.set_params(nets=...) replace "
                "the declared table wholesale — that is what lets the wiring "
                "editor add and delete connections. A stored row naming a "
                "port the script no longer declares is dropped, not refused."
            ),
        },
        "boards": {
            "boards": (
                "USE THIS to state where a wire attaches. boards({'fc': "
                "board(...), ...}) declares the project's boards and their "
                "terminals as a table; callable at most once per script, and "
                "the result is a mapping of TerminalSet, so it goes straight "
                "into nets(ports=b) and b['fc']['sda'] is an ordinary "
                "terminal. A board declared here draws as a node in the "
                "wiring editor whether or not anything is wired to it — a "
                "terminal set that is merely assigned to a variable reaches "
                "the canvas as nothing at all."
            ),
            "board": (
                "board(component, terminals=[term(...)], units='mm') is the "
                "editable form. header=/holes=/pads= with names= are the "
                "part.terminals forms, kept: a header is expanded to explicit "
                "rows at declaration, and a selector board's rows are derived "
                "from the shape on every run and are read-only in the editor. "
                "units='m' states what THIS declaration's numbers are in; the "
                "stored row is millimetres either way."
            ),
            "term": (
                "term(name, origin=..., axis=..., hole_dia=None, depth=None) "
                "declares one terminal in the board's own frame. origin is "
                "where the wire lands and axis is the direction it is drilled "
                "into the body, so the wire leaves back along -axis. hole_dia "
                "present means a hole, absent means a pad; depth is optional "
                "and descriptive."
            ),
            "values": (
                "Stored rows from xscript.project.set_params(boards=...) "
                "replace the declared table wholesale, exactly as the "
                "connection rows do — that is what lets the editor add and "
                "delete terminals, and what lets a viewport pick write a row "
                "with no chat turn. A stored row naming a board the script no "
                "longer declares is dropped, not refused."
            ),
        },
        "mounts": {
            "mounts": (
                "USE THIS to state where one component bolts to another. "
                "mounts({'skin': mount_set(shell, [mount(...)]), ...}) "
                "declares the project's mounts as a table; callable at most "
                "once per script. A mount is a terminal row plus a ROLL, so "
                "the frame is fully determined rather than only aimed, plus "
                "the fastener and the clearance the mating half needs."
            ),
            "mount_set": (
                "mount_set(component, [mount(...)], units='mm') declares one "
                "component's mounts. units='m' states what THIS declaration's "
                "numbers are in; the stored row is millimetres either way."
            ),
            "mount": (
                "mount(name, origin=..., axis=..., roll=..., fastener=None, "
                "clearance=None) declares one mount in the component's own "
                "frame. origin is where the two parts meet, axis is the "
                "direction the other part approaches along — so two mating "
                "mounts face each other — and roll is the mount's own 'up', "
                "which is what makes the frame a frame. A roll along the axis "
                "is refused: it fixes no rotation about it."
            ),
            "mate": (
                "part.mate(shape, m['leg']['root'], m['skin']['hip_l'], "
                "flip=False, offset=0.0) places shape so its mount lands on "
                "the other's, face to face and rolls aligned. It booleans the "
                "two afterwards and REFUSES a non-zero common volume, naming "
                "the cubic millimetres: two parts that overlap are colliding, "
                "not mated. Pass check_interference=False only when the "
                "overlap is the point."
            ),
            "values": (
                "Stored rows from xscript.project.set_params(mounts=...) "
                "replace the declared table wholesale, exactly as the board "
                "rows do. A stored row naming a component the script no "
                "longer declares mounts for is dropped, not refused."
            ),
        },
        "cages": {
            "cage": (
                "USE THIS for an organic body -- a torso, a limb, a head. "
                "cage({'torso': section_cage([ring(...), ...])}) declares the "
                "shape as a table of cross-sections; callable at most once "
                "per script. part.loft_cage(c['torso']) lofts it. The user "
                "can grab a ring in the viewport and drag it, so a silhouette "
                "stops costing a chat turn -- which is the whole reason to "
                "spell a section table this way rather than as literals."
            ),
            "section_cage": (
                "section_cage(rings, axis=(1,0,0), origin=(0,0,0), "
                "up=(0,0,1), units='mm') declares one cage: the rings are "
                "perpendicular to axis and stationed at their position along "
                "it from origin, and up fixes which way a ring's height "
                "points. A CURVED spine is part.sweep(scale_law=...) instead."
            ),
            "ring": (
                "ring(position, half_width, half_height, roll=0.0, "
                "exponent=2.0) is one section. The EXPONENT is the "
                "superellipse power: 2.0 is an ellipse, 4.0 already reads as "
                "a muscle, 8.0 as a rounded box. It is the cheapest way to "
                "make a limb look like a limb rather than a tube, and it "
                "costs a parameter rather than an operation."
            ),
            "values": (
                "Stored rows from xscript.project.set_params(cages=...) "
                "replace a cage's rings wholesale, exactly as the other "
                "tables do. A ring has no name -- its identity is its place "
                "in its cage's order -- and rows naming a cage the script no "
                "longer declares are dropped, not refused."
            ),
        },
        "parameters": {
            "params": (
                "params(name=num(...), ...) declares the script's slider "
                "parameters; callable at most once per script. Returns an "
                "immutable value object with attribute access (p.width). "
                "Parameter names are lower_snake_case, at most 64 of them."
            ),
            "num": (
                "num(default, unit='', min=None, max=None, step=None, "
                "label='', description='') declares one finite numeric "
                "parameter control. Declared min/max are a promise: the user "
                "rebuilds at any in-range value without review, so the script "
                "must stay valid across the whole range."
            ),
            "values": (
                "Stored values from xscript.project.set_params override "
                "defaults and are clamped to [min, max]. Only declared "
                "parameters may be set."
            ),
        },
        "result_contract": (
            "Assign result to a dict. Every kept value must be a key: keys "
            "become the stable published output names, values must come from "
            "the sketcher/part/partdesign/mesh/assembly APIs (assembly.solve "
            "diagnostics included). Outputs may mix domains. A script with "
            "an assembly returns exactly one assembly.assembly(...) value and "
            "exactly one assembly.solve(<that assembly>) value, and every "
            "component and joint that assembly lists, each under a key of its "
            "own and once: a component or joint kept only in a Python list is "
            "not returned. Assign each one where you create it "
            "(`result['hip_' + tag] = j_hip`), or loop a list into result "
            "(`for i, j in enumerate(joints): result['joint_' + str(i)] = j`)."
        ),
        "mutation_selection": {
            "write_script": "Replace the complete script source.",
            "edit_script": (
                "Apply exact replacements; every old string must occur "
                "exactly once in the current source."
            ),
            "set_params": (
                "Values-only RFC 7396 patch of declared parameters, and/or a "
                "full replacement row list for the connections declared with "
                "nets(...) or the terminals declared with boards(...); the "
                "source is untouched and re-executed with the new values."
            ),
        },
        "revision_rule": (
            "Guard every mutation with expected_revision equal to the working "
            "revision from core.inspect scope='script' or the previous write "
            "result; use an empty string only when no script exists yet. A "
            "refused candidate is rolled back: the previous accepted revision "
            "stays live and stays the working revision, and edit_script edits "
            "that accepted source, never the refused one. So until a "
            "write_script is accepted there is nothing to edit -- resend the "
            "whole corrected source with write_script."
        ),
    }
