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

# Worker attempts are deliberately self-contained. The project bundle stages
# every capability domain plus the shared domain-worker helpers; the project
# entry module replaces cadex_domain_worker as the staged worker.py (see
# _stage_worker_bundle).
_DOMAIN_WORKER_BUNDLES: dict[str, tuple[str, ...]] = {
    "project": (
        "cadex_domain_worker.py",
        "CadexSubshapeQuery.py",
        "cadex_project_api.py",
        "cadex_sketcher_api.py",
        "cadex_sketcher_worker.py",
        "cadex_part_api.py",
        "cadex_part_worker.py",
        # The wire router (ADR-056). Staged like every other worker module —
        # by filename, not imported — so cadex_part_worker can import it
        # inside the sandbox.
        "CadexRouting.py",
        "cadex_partdesign_api.py",
        "cadex_partdesign_worker.py",
        "cadex_mesh_api.py",
        "cadex_mesh_worker.py",
        "cadex_assembly_api.py",
        "cadex_assembly_worker.py",
        "cadex_tessellation.py",
        # The resident preview worker's entry (ADR-055). In the bundle rather
        # than beside cadexd because it runs inside the same --safe-mode
        # sandbox as everything else here, out of the same content-addressed
        # directory, and must never be importable by the service.
        "cadex_preview_worker.py",
    ),
}

#: Mesh assets stageable into the isolated worker (mesh.import_file).
_ASSET_SUFFIXES = frozenset({".stl", ".obj", ".ply"})
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
    member, so an engine rebuild produces a new directory and a stale one is
    never used; identical content reuses the directory, and with it the
    ``__pycache__`` next to it.

    Built atomically -- populated under ``.tmp-<uuid>`` and ``os.replace``d
    into place -- so two workers racing on the same bundle cannot read a
    half-populated directory.
    """

    entry_module, filenames = _bundle_members(domain)
    members = (entry_module, *filenames)

    digest = hashlib.sha256()
    for name in sorted(set(members)):
        source = module_root / name
        if source.parent != module_root or not source.is_file():
            raise RuntimeError(
                f"Required XScript worker dependency {name!r} is missing."
            )
        data = source.read_bytes()
        digest.update(name.encode("utf-8"))
        digest.update(str(len(data)).encode("ascii"))
        digest.update(data)

    clean_domain = str(domain or "").strip().lower()
    root = Path(tempfile.gettempdir()) / _BUNDLE_CACHE_DIRNAME
    bundle = root / f"{clean_domain}-{digest.hexdigest()[:24]}"
    if bundle.is_dir():
        return bundle, entry_module

    root.mkdir(parents=True, exist_ok=True)
    pending = root / f".tmp-{uuid.uuid4().hex}"
    pending.mkdir(parents=True, exist_ok=False)
    try:
        for name in set(members):
            _link_or_copy(module_root / name, pending / name)
        os.replace(pending, bundle)
    except OSError:
        shutil.rmtree(pending, ignore_errors=True)
        # Lost a race with another worker, or could not publish. Either the
        # bundle is there now or the caller's next attempt rebuilds it.
        if not bundle.is_dir():
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
        if path.suffix.lower() not in _ASSET_SUFFIXES:
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
        and path.suffix.lower() in _ASSET_SUFFIXES
    ]


def store_project_asset(
    project_root: Path | str,
    source_path: str,
    name: str = "",
) -> dict[str, Any]:
    """Copy one mesh file into ``<project_root>/assets`` under a checked name.

    The engine is the sole writer of the project store
    (docs/ARCHITECTURE.md), so this is how a file the user picked outside the
    store becomes importable. Bounds are the staging bounds — same suffixes,
    same 64-file / 128 MB budget, counted *including* the incoming file, so a
    run can never be staged into a budget this write already broke.
    Overwriting an existing name is allowed: that is re-import.
    """

    from cadex_mesh_api import _asset_filename

    raw_source = str(source_path or "").strip()
    if not raw_source:
        raise ValueError("source_path must name a readable mesh file.")
    try:
        source = Path(raw_source).expanduser().resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"Could not read {raw_source!r}: {exc}") from exc
    if not source.is_file():
        raise ValueError(f"{raw_source!r} is not a regular file.")
    source_suffix = source.suffix.lower()
    if source_suffix not in _ASSET_SUFFIXES:
        raise ValueError(
            f"{source.name!r} is not one of the importable mesh formats "
            f"{sorted(_ASSET_SUFFIXES)}."
        )
    target_name = _asset_filename("put_asset", str(name or "").strip() or source.name)
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
            "PYTHONHASHSEED": "0",
            "PYTHONNOUSERSITE": "1",
            "TEMP": staging,
            "TMP": staging,
            "TMPDIR": staging,
            "CADEX_XSCRIPT_DOMAIN_REQUEST": str(Path(staging) / "request.json"),
            "CADEX_XSCRIPT_DOMAIN_RESULT": str(Path(staging) / "result.json"),
        }
    )
    if sys.platform == "win32":
        drive, tail = os.path.splitdrive(staging)
        environment["USERPROFILE"] = staging
        if drive:
            environment["HOMEDRIVE"] = drive
            environment["HOMEPATH"] = tail or "\\"
    return environment


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
    result_path = Path(str(prepared["staging"])) / "result.json"
    if not result_path.is_file():
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
                "stdout": report.get("stdout") or process.get("stdout"),
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
    # them once at open_project); the preferences fallback is preserved for
    # the interactive shell and headless rebuild (Phase 5.3).
    timeout = 0.0
    memory_mb = 0
    budgets_reader = getattr(service, "scripted_budgets", None)
    if callable(budgets_reader):
        budgets = dict(budgets_reader() or {})
        timeout = float(budgets.get("timeout_seconds") or 0.0)
        memory_mb = int(budgets.get("memory_limit_mb") or 0)
    if timeout <= 0.0 or memory_mb <= 0:
        from CadexEngineSettings import load_engine_budgets

        settings = load_engine_budgets()
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
            _raise(
                tool_name,
                "NO_PROJECT_SCRIPT",
                "precondition",
                "There is no project script to edit yet; use write_script.",
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
        try:
            param_values = _project_param_values(
                state, arguments.get("values"), tool_name
            )
        except ValueError as exc:
            _raise(tool_name, "INVALID_PROJECT_PARAMETER_VALUE", "precondition", str(exc))
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
        "accepted_revision_before": str(state.get("accepted_revision") or ""),
        "accepted_contract_before": state.get("accepted_contract"),
        "accepted_digest_before": str(state.get("accepted_digest") or ""),
        "source": source,
        "param_values": param_values,
        "param_specs_before": list(state.get("param_specs") or []),
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
    final_revision = contracts.project_script_revision(
        source=str(prepared["source"]),
        param_specs=param_specs,
        param_values=dict(prepared["param_values"]),
    )
    store = CadexProjectScriptStore(str(prepared["project_root"]))
    store.write(
        state_updates={
            "param_specs": param_specs,
            "param_values": dict(prepared["param_values"]),
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
        "validations": dict(execution.get("validations") or {}),
        "component_sources": dict(execution.get("component_sources") or {}),
        "stdout": str(execution.get("stdout") or ""),
        "budget": dict(execution.get("budget") or {}),
    }


def accept_project_candidate(
    prepared: Mapping[str, Any],
    publication: Mapping[str, Any],
    validated: Mapping[str, Any],
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
    store.write(
        state_updates={
            "accepted_revision": revision,
            "accepted_contract": contract,
            "accepted_digest": digest,
            "accepted_attempt": {
                "attempt_id": str(prepared["attempt_id"]),
                "staging": staging_relative,
                "revision": revision,
            },
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
        store.record_history(revision, source, contract)
    except OSError:
        pass
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
        payload = accept_project_candidate(prepared, publication, validated)
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
    listing["assembly"]["notes"] = (
        "In a project script assembly.component(source, ...) takes a part or "
        "partdesign value created in the same script; cross-document component "
        "references are not supported and every component source must also be "
        "a declared result output."
    )
    return listing


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
        ],
        "domains": _capability_api_listing(),
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
            "diagnostics included). Outputs may mix domains."
        ),
        "mutation_selection": {
            "write_script": "Replace the complete script source.",
            "edit_script": (
                "Apply exact replacements; every old string must occur "
                "exactly once in the current source."
            ),
            "set_params": (
                "Values-only RFC 7396 patch of declared parameters; the "
                "source is untouched and re-executed with the new values."
            ),
        },
        "revision_rule": (
            "Guard every mutation with expected_revision equal to the working "
            "revision from core.inspect scope='script' or the previous write "
            "result; use an empty string only when no script exists yet. A "
            "failed candidate becomes the working revision while the previous "
            "accepted revision stays live."
        ),
    }
