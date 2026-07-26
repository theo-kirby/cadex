# SPDX-License-Identifier: LGPL-2.1-or-later

"""A script that drops a parameter must not wedge ``set_params`` (ADR-039).

The store keeps ``param_specs`` (what the script declares) beside
``param_values`` (what the sliders were last set to). Rewriting the script used
to update the first and leave the second, so a value whose parameter no longer
existed stayed in the store forever -- and ``_project_param_values`` merged the
stored values into every patch and validated *every merged key*, so every later
``set_params`` failed the precondition with ``UNKNOWN_PROJECT_PARAMETER`` for a
name the caller never sent. Nothing healed it: ``write_script`` and ``rebuild``
both left ``param_values`` alone.

Two halves, tested at two levels:

- the merge rule, in-process: a stale key in the *store* is dropped, a bad key
  in the *patch* still raises;
- the persistence, through a real worker: rewriting the script prunes the
  store, the pruned store still builds the same geometry (the digest is
  unchanged, which is why pruning is safe), and the next drag succeeds.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
_FREECADCMD_CANDIDATES = (
    REPO_ROOT / ".pixi" / "envs" / "default" / "bin" / "FreeCADCmd",
    REPO_ROOT / "build" / "release" / "bin" / "FreeCADCmd",
)
FREECADCMD = next(
    (candidate for candidate in _FREECADCMD_CANDIDATES if candidate.is_file()), None
)


def _spec(name: str) -> dict[str, object]:
    return {"name": name, "type": "num", "default": 1.0, "min": 0.0, "max": 10.0}


def _state(declared: list[str], values: dict[str, float]) -> dict[str, object]:
    return {"param_specs": [_spec(name) for name in declared], "param_values": values}


def test_stale_stored_value_is_dropped_not_raised() -> None:
    """The reported failure, at the unit that produced it."""
    from CadexScriptedRuntime import _project_param_values

    # `duct_gap` is in the store and not in the script -- exactly the
    # whoop-chassis-v01 state. The patch names neither it nor anything odd.
    merged = _project_param_values(
        _state(
            ["duct_inner_d", "cam_hole_d"],
            {"duct_gap": 3.6, "duct_inner_d": 36.0},
        ),
        {"cam_hole_d": 10.2},
        "xscript.project.set_params",
    )
    assert merged == {"duct_inner_d": 36.0, "cam_hole_d": 10.2}


def test_unknown_key_in_the_patch_still_raises() -> None:
    """Asking to set an undeclared parameter is a caller error; stay loud."""
    from CadexScriptedRuntime import DomainRuntimeFailure, _project_param_values

    with pytest.raises(DomainRuntimeFailure) as caught:
        _project_param_values(
            _state(["a"], {"a": 1.0}),
            {"nope": 1.0},
            "xscript.project.set_params",
        )
    payload = dict(caught.value.payload)
    assert payload.get("failure_code") == "UNKNOWN_PROJECT_PARAMETER", payload
    assert "nope" in str(payload.get("error") or ""), payload


def test_declared_values_and_deletes_still_apply() -> None:
    """Pruning the base does not change the RFC 7396 semantics on top of it."""
    from CadexScriptedRuntime import _project_param_values

    state = _state(["a", "b"], {"a": 1.0, "b": 2.0, "gone": 9.0})
    assert _project_param_values(state, {"a": 5.0}, "t") == {"a": 5.0, "b": 2.0}
    # A null still deletes, and the stale key is gone either way.
    assert _project_param_values(state, {"b": None}, "t") == {"a": 1.0}


_DRIVER = r"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import FreeCAD as App

cadex_root = Path(sys.argv[-1])
sys.path.insert(0, str(cadex_root))

from CadexProject import CadexProjectScriptStore
from CadexScriptedDomainPublication import publish_project_candidate
from CadexScriptedRuntime import (
    DomainRuntimeFailure,
    accept_project_candidate,
    capture_project_state,
    execute_candidate,
    prepare_project_candidate,
    validate_project_result,
)
import cadex_rebuild

TWO_PARAMS = '''
p = params(a=num(30, unit="mm", min=10, max=90, step=1),
           b=num(12, unit="mm", min=4, max=40, step=1))
plate = part.box(p.a, p.b, 4)
result = {"plate": plate}
'''

ONE_PARAM = '''
p = params(a=num(30, unit="mm", min=10, max=90, step=1))
plate = part.box(p.a, 12, 4)
result = {"plate": plate}
'''

root = Path(tempfile.mkdtemp(prefix="cadex-param-prune-"))
report = {}


def run(service, tool, arguments):
    captured = capture_project_state(service, tool, arguments)
    prepared = prepare_project_candidate(captured)
    execution = execute_candidate(prepared, cancellation_check=None)
    assert execution.get("ok") is True, execution
    validated = validate_project_result(prepared, execution)
    publication = publish_project_candidate(service, prepared, validated)
    accept_project_candidate(prepared, publication, validated)
    return validated


def expected(store):
    return str(store.read_state().get("working_revision") or "")


try:
    document = App.newDocument("PruneSeed")
    service = cadex_rebuild._RebuildService(root, document)
    store = CadexProjectScriptStore(root)

    run(service, "xscript.project.write_script",
        {"source": TWO_PARAMS, "expected_revision": ""})
    run(service, "xscript.project.set_params",
        {"values": {"a": 40.0, "b": 20.0}, "expected_revision": expected(store)})
    report["values_with_both"] = dict(store.read_state().get("param_values") or {})

    # The rewrite drops `b`. Its worker still receives the stale value (the
    # prune lands in validate, after execution), so this digest is the
    # "worker saw the stale key" one.
    stale = run(service, "xscript.project.write_script",
                {"source": ONE_PARAM, "expected_revision": expected(store)})
    report["values_after_drop"] = dict(store.read_state().get("param_values") or {})
    report["specs_after_drop"] = [
        str(spec.get("name") or "")
        for spec in store.read_state().get("param_specs") or []
    ]

    # Same script again, now from the pruned store: this worker never sees `b`.
    # Equal digests are the whole safety argument for pruning.
    pruned = run(service, "xscript.project.write_script",
                 {"source": ONE_PARAM, "expected_revision": expected(store)})
    report["digest_with_stale"] = str(stale["digest"])
    report["digest_after_prune"] = str(pruned["digest"])

    # The drag that used to fail forever.
    dragged = run(service, "xscript.project.set_params",
                  {"values": {"a": 44.0}, "expected_revision": expected(store)})
    report["drag_ok"] = True
    report["values_after_drag"] = dict(store.read_state().get("param_values") or {})

    # And an undeclared name in the patch is still a precondition failure.
    try:
        prepare_project_candidate(capture_project_state(
            service, "xscript.project.set_params",
            {"values": {"nope": 1.0}, "expected_revision": expected(store)}))
    except DomainRuntimeFailure as failure:
        report["unknown_code"] = str(
            dict(failure.payload).get("failure_code") or "")
    else:
        report["unknown_code"] = "NOT-RAISED"

    report["ok"] = True
finally:
    shutil.rmtree(root, ignore_errors=True)

print("PARAM-PRUNE " + json.dumps(report, sort_keys=True))
"""


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for the prune CI."
)
def test_dropping_a_parameter_prunes_the_store_and_frees_set_params(tmp_path) -> None:
    driver = tmp_path / "param_prune_driver.py"
    driver.write_text(_DRIVER, encoding="utf-8")
    cadex_root = Path(__file__).resolve().parent.parent
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
            if line.startswith("PARAM-PRUNE ")
        ),
        None,
    )
    assert marker, (
        f"prune driver produced no report; exit={completed.returncode}\n"
        f"stdout:\n{completed.stdout[-4000:]}\nstderr:\n{completed.stderr[-4000:]}"
    )
    report = json.loads(marker.removeprefix("PARAM-PRUNE "))
    assert report.get("ok") is True, report
    assert report["values_with_both"] == {"a": 40.0, "b": 20.0}, report
    # The dropped parameter's value is gone from the store, the kept one stays.
    assert report["values_after_drop"] == {"a": 40.0}, report
    assert report["specs_after_drop"] == ["a"], report
    # Pruning is digest-neutral: the worker resolves declared parameters by
    # name and ignores every other key.
    assert report["digest_after_prune"] == report["digest_with_stale"], report
    # The drag that the stale key used to block, forever.
    assert report["drag_ok"] is True, report
    assert report["values_after_drag"] == {"a": 44.0}, report
    assert report["unknown_code"] == "UNKNOWN_PROJECT_PARAMETER", report
