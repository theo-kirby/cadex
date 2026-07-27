# SPDX-License-Identifier: LGPL-2.1-or-later

"""Preview CI: the project worker answers a pose-only change with placements.

``mode: "preview"`` is a read-only oracle (ADR-055). It execs the script,
decides whether the change was pose-only by comparing every non-assembly
output's canonical definition against a baseline, and if it was, runs the
native assembly solve and returns the solved placements — no BREP export, no
tessellation, no digest, no publication, and **no write to the project
store**.

That last one is the invariant the whole design rests on, so it is asserted
the strongest way available: a real accepted store is built through the real
pipeline, its complete file list and mtimes are snapshotted, a burst of
previews runs, and the snapshot must be byte-identical afterwards. Every
accepted byte still comes from a cold ``--safe-mode`` run.

Skipped when no FreeCADCmd binary is available (pure-python CI).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
_FREECADCMD_CANDIDATES = (
    REPO_ROOT / ".pixi" / "envs" / "default" / "bin" / "FreeCADCmd",
    REPO_ROOT / "build" / "release" / "bin" / "FreeCADCmd",
)


def _packaged_engine():
    """Resolve a packaged engine payload from ``CADEX_ENGINE_ROOT`` (ADR-023).

    A source tree that passes proves nothing about a payload, and the preview
    path is exactly the kind of change that can pass in one and fail in the
    other: it reaches across four staged worker modules, and the payload
    stages them by filename.
    """

    root = os.environ.get("CADEX_ENGINE_ROOT", "").strip()
    if not root:
        return None, None
    manifest_path = Path(root) / "cadex-engine.json"
    if not manifest_path.is_file():
        raise AssertionError(
            f"CADEX_ENGINE_ROOT={root!r} has no cadex-engine.json; the "
            "payload's manifest is its discovery contract (ADR-020)."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    binary = base.joinpath(*str(manifest["freecadcmd"]).split("/"))
    module_dir = base.joinpath(*str(manifest["module_dir"]).split("/"))
    assert binary.is_file(), binary
    assert module_dir.is_dir(), module_dir
    return binary, module_dir


_PACKAGED_BINARY, _PACKAGED_MODULE_DIR = _packaged_engine()
CADEX_ROOT = _PACKAGED_MODULE_DIR or Path(__file__).resolve().parent.parent
FREECADCMD = _PACKAGED_BINARY or next(
    (candidate for candidate in _FREECADCMD_CANDIDATES if candidate.is_file()), None
)

_DRIVER = r"""
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

import FreeCAD as App

cadex_root = Path(sys.argv[-1])
sys.path.insert(0, str(cadex_root))

from CadexScriptedDomainPublication import publish_project_candidate
from CadexScriptedRuntime import (
    accept_project_candidate,
    capture_project_state,
    execute_candidate,
    prepare_project_candidate,
    validate_project_result,
)
import cadex_project_worker
import cadex_rebuild

# `reach` is a joint offset: it moves a solved component and changes no
# geometry, which is exactly the class of parameter a preview serves.
# `width` feeds part.box, so it changes `plate`'s definition and must be
# refused — a placement-only reply for it would be a lie.
SCRIPT = '''
p = params(reach=num(12, unit="mm", min=0, max=30, step=1),
           width=num(40, unit="mm", min=10, max=90, step=1))
plate = part.box(p.width, 20, 4)
arm = part.box(30, 6, 6)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin", offset=[p.reach, 0, 4]),
                   assembly.connector(swing, "origin"))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag}
'''


def snapshot(root):
    '''Every file under the store, with its size and mtime_ns.'''
    return {
        str(path.relative_to(root)): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


root = Path(tempfile.mkdtemp(prefix="cadex-preview-store-"))
scratch = Path(tempfile.mkdtemp(prefix="cadex-preview-scratch-"))
report = {}
try:
    document = App.newDocument("PreviewSeed")
    service = cadex_rebuild._RebuildService(root, document)
    captured = capture_project_state(
        service,
        "xscript.project.write_script",
        {"source": SCRIPT, "expected_revision": ""},
    )
    prepared = prepare_project_candidate(captured)
    execution = execute_candidate(prepared, cancellation_check=None)
    assert execution.get("ok") is True, execution
    validated = validate_project_result(prepared, execution)
    publication = publish_project_candidate(service, prepared, validated)
    accept_project_candidate(prepared, publication, validated)
    App.closeDocument(document.Name)

    # The accepting run's own request is the preview request's template: same
    # source, same api_contracts, same inputs. Only `mode`, `param_values`
    # and `baseline` differ, which is the point -- a preview is the same
    # program at different values, not a different program.
    template = json.loads(
        (Path(prepared["staging"]) / "request.json").read_text(encoding="utf-8")
    )

    def preview(values, baseline=None):
        request = dict(template)
        request["mode"] = "preview"
        request["param_values"] = dict(values)
        if baseline is not None:
            request["baseline"] = baseline
        started = time.monotonic()
        answer = cadex_project_worker._run_preview(request, scratch)
        answer["_seconds"] = round(time.monotonic() - started, 4)
        return answer

    before = snapshot(root)

    # (1) The generation load: no baseline yet, so nothing to compare and
    # nothing previewable -- but the fingerprints come back, which is how a
    # baseline is acquired at all.
    baseline_run = preview({"reach": 12, "width": 40})

    baseline = {"definitions_fingerprint": baseline_run["definitions_fingerprint"]}

    # (2) A pose-only change: the joint offset moves, the geometry does not.
    posed = preview({"reach": 25, "width": 40}, baseline)

    # (3) The same again, to show the memo is kept across previews of one
    # generation: `plate` and `arm` are unchanged and must not be rebuilt.
    from cadex_part_worker import _SHAPE_MEMO
    memo_after_posed = len(_SHAPE_MEMO)
    posed_again = preview({"reach": 8, "width": 40}, baseline)
    memo_after_again = len(_SHAPE_MEMO)

    # (4) A shape change: refused, and refused before any shape is built.
    shaped = preview({"reach": 12, "width": 55}, baseline)

    # (5) The same request through the worker's own entry point, so `mode`
    # is honoured at the request-file boundary and not only by a direct call.
    dispatch_dir = Path(tempfile.mkdtemp(prefix="cadex-preview-dispatch-"))
    dispatch_request = dict(template)
    dispatch_request["mode"] = "preview"
    dispatch_request["param_values"] = {"reach": 30, "width": 40}
    dispatch_request["baseline"] = baseline
    (dispatch_dir / "request.json").write_text(
        json.dumps(dispatch_request), encoding="utf-8"
    )
    import os as _os
    _os.environ[cadex_project_worker.REQUEST_ENV] = str(dispatch_dir / "request.json")
    _os.environ[cadex_project_worker.RESULT_ENV] = str(dispatch_dir / "result.json")
    dispatch_code = cadex_project_worker.main()
    dispatched = json.loads(
        (dispatch_dir / "result.json").read_text(encoding="utf-8")
    )
    dispatched["_exit_code"] = dispatch_code
    shutil.rmtree(dispatch_dir, ignore_errors=True)

    after = snapshot(root)

    report = {
        "ok": True,
        "baseline_run": baseline_run,
        "posed": posed,
        "posed_again": posed_again,
        "shaped": shaped,
        "dispatched": dispatched,
        "memo_after_posed": memo_after_posed,
        "memo_after_again": memo_after_again,
        "store_unchanged": before == after,
        "store_file_count": len(before),
        "store_added": sorted(set(after) - set(before)),
        "store_touched": sorted(
            name for name in set(before) & set(after) if before[name] != after[name]
        ),
        "scratch_entries": sorted(
            str(path.relative_to(scratch)) for path in scratch.rglob("*")
        ),
    }
finally:
    shutil.rmtree(root, ignore_errors=True)
    shutil.rmtree(scratch, ignore_errors=True)

print("PREVIEW-CI " + json.dumps(report, sort_keys=True))
"""


def _run_driver(tmp_path: Path) -> dict:
    driver = tmp_path / "preview_ci_driver.py"
    driver.write_text(_DRIVER, encoding="utf-8")
    cadex_root = CADEX_ROOT
    completed = subprocess.run(
        [
            str(FREECADCMD),
            "-c",
            (
                "import sys; sys.argv = ['driver', "
                f"{str(cadex_root)!r}]; "
                f"exec(open({str(driver)!r}).read())"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=900,
        env={**os.environ, "PYTHONHASHSEED": "0"},
        check=False,
    )
    marker = next(
        (
            line
            for line in completed.stdout.splitlines()
            if line.startswith("PREVIEW-CI ")
        ),
        None,
    )
    assert marker, (
        f"preview CI driver produced no report; exit={completed.returncode}\n"
        f"stdout:\n{completed.stdout[-4000:]}\nstderr:\n{completed.stderr[-4000:]}"
    )
    report = json.loads(marker.removeprefix("PREVIEW-CI "))
    assert report.get("ok") is True, report
    return report


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for the preview CI."
)
def test_a_pose_only_parameter_previews_as_placements(tmp_path) -> None:
    report = _run_driver(tmp_path)

    # (1) The first exec of a generation has no baseline and says so, rather
    # than guessing. Without this the first preview of every drag -- the one
    # that matters most -- would have nothing to compare against.
    baseline_run = report["baseline_run"]
    assert baseline_run["previewable"] is False, baseline_run
    assert "baseline" in baseline_run["reason"], baseline_run
    fingerprints = baseline_run["definitions_fingerprint"]
    # Non-assembly outputs only: a component's placement is an argument of
    # its own definition, so including assembly outputs would make every
    # moved component read as changed geometry.
    assert set(fingerprints) == {"plate", "arm"}, fingerprints

    # (2) The joint offset moved and the geometry did not: previewable, and
    # the solve actually ran -- `swing` is declared at [0, 0, 40] and the
    # revolute joint puts it on the connector offset instead.
    posed = report["posed"]
    assert posed["previewable"] is True, posed
    assert "reason" not in posed, posed
    assert set(posed["placements"]) == {"base", "swing"}, posed
    assert len(posed["placements"]["swing"]) == 16, posed
    swing = [round(value, 6) for value in posed["placements"]["swing"][3::4]]
    assert swing == [25.0, 0.0, 4.0, 1.0], posed
    grounded = [round(value, 6) for value in posed["placements"]["base"][3::4]]
    assert grounded == [0.0, 0.0, 0.0, 1.0], posed
    # Same definitions, so the same fingerprints -- that equality IS the
    # previewable verdict, not a separate claim.
    assert posed["definitions_fingerprint"] == fingerprints, posed

    posed_again = report["posed_again"]
    assert posed_again["previewable"] is True, posed_again
    swing_again = [round(v, 6) for v in posed_again["placements"]["swing"][3::4]]
    assert swing_again == [8.0, 0.0, 4.0, 1.0], posed_again

    # The memo persists across previews of one generation -- that is what
    # makes the second preview of a drag cheaper than the first. It must not
    # grow: `plate` and `arm` are byte-identical between the two runs, so
    # they are hits, not new entries.
    assert report["memo_after_posed"] > 0, report
    assert report["memo_after_again"] == report["memo_after_posed"], report

    # And the same answer through the worker's own entry point: `mode` is
    # honoured where the request is read, not only by a direct call.
    dispatched = report["dispatched"]
    assert dispatched["_exit_code"] == 0, dispatched
    assert dispatched["mode"] == "preview", dispatched
    assert dispatched["previewable"] is True, dispatched
    reach = [round(v, 6) for v in dispatched["placements"]["swing"][3::4]]
    assert reach == [30.0, 0.0, 4.0, 1.0], dispatched


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for the preview CI."
)
def test_a_shape_parameter_is_refused_rather_than_answered(tmp_path) -> None:
    """The honest answer for a parameter that changes geometry."""

    shaped = _run_driver(tmp_path)["shaped"]
    assert shaped["previewable"] is False, shaped
    assert shaped["placements"] == {}, shaped
    # Names what changed, so the failure is legible rather than a bare no.
    assert "plate" in shaped["reason"], shaped
    # `arm` did not change and must not be blamed for it.
    assert "arm" not in shaped["reason"], shaped


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for the preview CI."
)
def test_a_burst_of_previews_writes_nothing_to_the_project_store(tmp_path) -> None:
    """The invariant that makes a resident preview process safe.

    A preview never writes the store, never publishes, never moves a revision
    or a digest, so digest determinism, cross-revision isolation and crash
    recovery are preserved *by construction* rather than by argument. Asserted
    over the store's complete file list with sizes and mtimes, because an
    argument is exactly what this should not rest on.
    """

    report = _run_driver(tmp_path)
    assert report["store_file_count"] > 0, report
    assert report["store_added"] == [], report
    assert report["store_touched"] == [], report
    assert report["store_unchanged"] is True, report
    # And nothing was written beside the worker either: no outputs/ directory,
    # no staged artifact, no result file.
    assert report["scratch_entries"] == [], report
