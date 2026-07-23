# SPDX-License-Identifier: LGPL-2.1-or-later

"""Contract tests for XScript parameter controls (slider metadata).

Controls are metadata-only: they persist in the program manifest, are excluded
from the program revision, survive value/source mutations, are pruned when an
input disappears, and are surfaced by inspection. The agent-facing tool is only
offered on production-ready domains.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import CadexScriptedRuntime as runtime
import CadexScriptedDomains as domains


PROGRAM_ID = "0123456789abcdef0123456789abcdef"


class _FakeService:
    def __init__(self, root: Path) -> None:
        self._root = str(root)

    def project_scope_snapshot(self) -> dict:
        return {"root": self._root}


def _pack() -> domains.XScriptWorkbenchPack:
    pack = domains.get_xscript_pack("PartDesignWorkbench")
    assert pack is not None
    return pack


def _write_v2_program(
    root: Path,
    *,
    inputs: dict,
    input_controls: dict | None = None,
    source: str = "result = {'Part': api.body(feature, label='Part')}",
) -> str:
    pack = _pack()
    input_schema = {
        "type": "object",
        "properties": {name: {"type": "number"} for name in inputs},
        "additionalProperties": False,
    }
    expected_outputs = [{"name": "Part", "type": "solid"}]
    revision = domains.program_revision(
        domain="partdesign",
        source=source,
        input_schema=input_schema,
        inputs=inputs,
        expected_outputs=expected_outputs,
    )
    manifest = runtime._new_manifest(pack, PROGRAM_ID, "Slider Part")
    manifest.update(
        {
            "source": source,
            "input_schema": input_schema,
            "inputs": dict(inputs),
            "expected_outputs": expected_outputs,
            "working_revision": revision,
            "accepted_revision": revision,
        }
    )
    if input_controls is not None:
        manifest["input_controls"] = input_controls
    path = runtime._manifest_path(root, "partdesign", PROGRAM_ID)
    path.parent.mkdir(parents=True, exist_ok=True)
    runtime._atomic_json(path, manifest)
    return revision


def _read_manifest(root: Path) -> dict:
    path = runtime._manifest_path(root, "partdesign", PROGRAM_ID)
    return json.loads(path.read_text(encoding="utf-8"))


def _apply(service: _FakeService, arguments: dict) -> dict:
    """Invoke the op the way the session dispatch does: failures become payloads."""
    try:
        return runtime.apply_parameter_controls(service, _pack(), arguments)
    except runtime.DomainRuntimeFailure as exc:
        return exc.payload


# ---------------------------------------------------------------------------
# apply_parameter_controls
# ---------------------------------------------------------------------------


def test_apply_persists_controls_and_keeps_revision(tmp_path: Path) -> None:
    revision = _write_v2_program(tmp_path, inputs={"radius": 4.0})
    service = _FakeService(tmp_path)
    result = _apply(
        service,
        {
            "program_id": PROGRAM_ID,
            "expected_revision": revision,
            "controls_patch": {
                "radius": {
                    "label": "Radius",
                    "unit": "mm",
                    "min": 1,
                    "max": 10,
                    "step": 0.5,
                }
            },
        },
    )
    assert result["ok"] is True
    # Metadata-only: the working revision is returned unchanged.
    assert result["working_revision"] == revision
    assert result["geometry_unchanged"] is True

    manifest = _read_manifest(tmp_path)
    assert manifest["input_controls"] == {
        "radius": {
            "label": "Radius",
            "unit": "mm",
            "min": 1.0,
            "max": 10.0,
            "step": 0.5,
        }
    }
    # The revision-defining contract is byte-for-byte unchanged by the write.
    assert manifest["working_revision"] == revision
    assert (
        domains.program_revision(
            domain="partdesign",
            source=manifest["source"],
            input_schema=manifest["input_schema"],
            inputs=manifest["inputs"],
            expected_outputs=manifest["expected_outputs"],
        )
        == revision
    )


def test_apply_merge_patch_removes_a_control_with_null(tmp_path: Path) -> None:
    revision = _write_v2_program(
        tmp_path,
        inputs={"radius": 4.0, "height": 12.0},
        input_controls={
            "radius": {"label": "Radius", "min": 1.0, "max": 10.0},
            "height": {"label": "Height", "min": 1.0, "max": 40.0},
        },
    )
    service = _FakeService(tmp_path)
    result = _apply(
        service,
        {
            "program_id": PROGRAM_ID,
            "expected_revision": revision,
            "controls_patch": {"height": None},
        },
    )
    assert result["ok"] is True
    manifest = _read_manifest(tmp_path)
    assert set(manifest["input_controls"]) == {"radius"}


def test_apply_merges_a_single_field_without_resending_the_control(
    tmp_path: Path,
) -> None:
    revision = _write_v2_program(
        tmp_path,
        inputs={"radius": 4.0},
        input_controls={
            "radius": {"label": "Radius", "unit": "mm", "min": 1.0, "max": 10.0}
        },
    )
    service = _FakeService(tmp_path)
    result = _apply(
        service,
        {
            "program_id": PROGRAM_ID,
            "expected_revision": revision,
            # Bump only max and drop only unit; other fields ride along.
            "controls_patch": {"radius": {"max": 20, "unit": None}},
        },
    )
    assert result["ok"] is True
    manifest = _read_manifest(tmp_path)
    assert manifest["input_controls"] == {
        "radius": {"label": "Radius", "min": 1.0, "max": 20.0}
    }


def test_apply_rejects_a_stale_revision(tmp_path: Path) -> None:
    _write_v2_program(tmp_path, inputs={"radius": 4.0})
    service = _FakeService(tmp_path)
    result = _apply(
        service,
        {
            "program_id": PROGRAM_ID,
            "expected_revision": "0" * 64,
            "controls_patch": {"radius": {"min": 1.0, "max": 10.0}},
        },
    )
    assert result["ok"] is False
    assert result["failure_code"] == "STALE_PROGRAM_REVISION"


def test_apply_rejects_an_empty_patch(tmp_path: Path) -> None:
    revision = _write_v2_program(tmp_path, inputs={"radius": 4.0})
    service = _FakeService(tmp_path)
    result = _apply(
        service,
        {
            "program_id": PROGRAM_ID,
            "expected_revision": revision,
            "controls_patch": {},
        },
    )
    assert result["ok"] is False
    assert result["failure_code"] == "EMPTY_CONTROLS_PATCH"


def test_apply_rejects_controls_for_an_unknown_input(tmp_path: Path) -> None:
    revision = _write_v2_program(tmp_path, inputs={"radius": 4.0})
    service = _FakeService(tmp_path)
    result = _apply(
        service,
        {
            "program_id": PROGRAM_ID,
            "expected_revision": revision,
            "controls_patch": {"nonexistent": {"min": 1.0, "max": 2.0}},
        },
    )
    assert result["ok"] is False
    assert result["failure_code"] == "UNKNOWN_CONTROL_PARAMETER"


@pytest.mark.parametrize(
    "patch",
    [
        {"radius": {"min": 5.0, "max": 2.0}},
        {"radius": {"step": 0.0}},
        {"radius": {"step": -1.0}},
        {"radius": {"min": "big"}},
        {"radius": {"unexpected": 1.0}},
    ],
)
def test_apply_rejects_invalid_control_values(tmp_path: Path, patch: dict) -> None:
    revision = _write_v2_program(tmp_path, inputs={"radius": 4.0})
    service = _FakeService(tmp_path)
    result = _apply(
        service,
        {
            "program_id": PROGRAM_ID,
            "expected_revision": revision,
            "controls_patch": patch,
        },
    )
    assert result["ok"] is False
    assert result["failure_code"] in {
        "INVALID_PARAMETER_CONTROLS",
        "UNKNOWN_CONTROL_PARAMETER",
    }


# ---------------------------------------------------------------------------
# Survival through a value mutation and pruning on read
# ---------------------------------------------------------------------------


def test_controls_survive_a_set_inputs_rebuild(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controls = {"radius": {"label": "Radius", "min": 1.0, "max": 10.0}}
    revision = _write_v2_program(
        tmp_path,
        inputs={"radius": 4.0},
        input_controls=controls,
        source="feature = api.pad(api.sketch([api.circle([0,0], inputs['radius'])]), 5)\n"
        "result = {'Part': api.body(feature, label='Part')}\n",
    )
    monkeypatch.setattr(runtime, "_freecadcmd", lambda _home: Path("/FreeCADCmd"))
    pack = _pack()
    capture = {
        "pack": pack,
        "operation": "set_inputs",
        "tool_name": "xscript.partdesign.set_inputs",
        "arguments": {
            "program_id": PROGRAM_ID,
            "expected_revision": revision,
            "patch": {"radius": 6.0},
        },
        "project_root": str(tmp_path),
        "document_name": "SliderDoc",
        "document_uid": "slider-doc",
        "document_revision": "doc-rev-1",
        "document_objects": [],
        "surface": {
            "workbench": pack.workbench,
            "engine": "xscript",
            "surface_id": pack.surface_id,
        },
        "freecad_home": str(tmp_path / "freecad-home"),
        "timeout_seconds": 30.0,
        "memory_limit_bytes": 512 * 1024 * 1024,
    }
    prepared = runtime.prepare_candidate(capture)
    try:
        persisted = _read_manifest(tmp_path)
        # The value changed and the revision advanced, but slider metadata rode
        # along untouched (it is not part of the revision contract).
        assert persisted["working_revision"] == prepared["revision"]
        assert persisted["working_revision"] != revision
        assert persisted["inputs"]["radius"] == 6.0
        assert persisted["input_controls"] == controls
    finally:
        runtime.abandon_prepared_candidate(prepared)


def test_prune_controls_drops_metadata_for_removed_inputs() -> None:
    pruned = runtime.prune_controls(
        {"radius": {"min": 1.0}, "gone": {"min": 2.0}}, {"radius": 4.0}
    )
    assert pruned == {"radius": {"min": 1.0}}


def test_inspect_surfaces_only_live_controls(tmp_path: Path) -> None:
    pack = _pack()
    adapter = domains.get_domain_adapter("partdesign")
    assert adapter is not None
    manifest = runtime._new_manifest(pack, PROGRAM_ID, "Slider Part")
    manifest.update(
        {
            "source": "result = {}",
            "inputs": {"radius": 4.0},
            "working_revision": "a" * 64,
            "input_controls": {
                "radius": {"label": "Radius", "min": 1.0, "max": 10.0},
                "removed": {"label": "Ghost", "min": 1.0, "max": 2.0},
            },
        }
    )
    result = adapter.inspect({}, manifest | {"live_state": None})
    assert result["ok"] is True
    assert set(result["program"]["input_controls"]) == {"radius"}


# ---------------------------------------------------------------------------
# clean_parameter_controls unit behaviour
# ---------------------------------------------------------------------------


def test_clean_parameter_controls_coerces_numbers_to_floats() -> None:
    cleaned = runtime.clean_parameter_controls(
        "xscript.partdesign.set_parameter_controls",
        {"radius": {"min": 1, "max": 10, "step": 2, "label": "R"}},
        {"radius": 4.0},
    )
    assert cleaned == {"radius": {"min": 1.0, "max": 10.0, "step": 2.0, "label": "R"}}


def test_clean_parameter_controls_rejects_bad_range() -> None:
    with pytest.raises(runtime.DomainRuntimeFailure) as excinfo:
        runtime.clean_parameter_controls(
            "xscript.partdesign.set_parameter_controls",
            {"radius": {"min": 9.0, "max": 1.0}},
            {"radius": 4.0},
        )
    assert excinfo.value.payload["failure_code"] == "INVALID_PARAMETER_CONTROLS"


# ---------------------------------------------------------------------------
# Surface exposure gated to production-ready domains
# ---------------------------------------------------------------------------


def test_production_domain_offers_set_parameter_controls() -> None:
    pack = _pack()
    assert pack.production_ready is True
    tool = "xscript.partdesign.set_parameter_controls"
    assert tool in pack.tool_names
    spec_names = {spec["name"] for spec in domains.domain_tool_specs(pack)}
    assert tool in spec_names


def test_non_production_domain_hides_set_parameter_controls() -> None:
    experimental = domains.XScriptWorkbenchPack(
        workbench="ExperimentalWorkbench",
        domain="experimental",
        title="Experimental",
        output_types=("solid",),
        instructions="",
        api_exports=(),
        production_ready=False,
    )
    tool = "xscript.experimental.set_parameter_controls"
    assert tool not in experimental.tool_names
    spec_names = {spec["name"] for spec in domains.domain_tool_specs(experimental)}
    assert tool not in spec_names
    # Other lifecycle operations remain available on the experimental pack.
    assert "xscript.experimental.set_inputs" in spec_names