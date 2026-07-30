# SPDX-License-Identifier: LGPL-2.1-or-later

"""Pure-Python coverage for the project worker's FreeCAD-free machinery."""

from __future__ import annotations

from pathlib import Path

import pytest

from cadex_domain_api import DomainValue
import cadex_project_api as project_api
import cadex_project_worker as project_worker


def _value(domain: str, operation: str = "box", output_type: str = "solid"):
    return DomainValue(
        domain=domain,
        operation=operation,
        output_type=output_type,
        arguments=(1.0, 2.0, 3.0),
        properties={},
    )


# -- parameter vocabulary ---------------------------------------------------


def test_num_spec_carries_control_fields() -> None:
    spec = project_api.num(
        100, unit="mm", min=10, max=500, step=1, label="Width", description="d"
    )
    assert spec["default"] == 100.0
    assert spec["min"] == 10.0
    assert spec["max"] == 500.0
    assert spec["step"] == 1.0
    assert spec["unit"] == "mm"
    assert spec["label"] == "Width"


def test_num_rejects_bad_bounds() -> None:
    with pytest.raises(project_api.ProjectParameterError):
        project_api.num(1, min=10, max=5)
    with pytest.raises(project_api.ProjectParameterError):
        project_api.num(1, min=2)
    with pytest.raises(project_api.ProjectParameterError):
        project_api.num(1, step=0)
    with pytest.raises(project_api.ProjectParameterError):
        project_api.num(float("nan"))
    with pytest.raises(project_api.ProjectParameterError):
        project_api.num(True)


def test_params_collects_specs_and_applies_overrides() -> None:
    collector = project_api.ParamsCollector({"width": 250.0})
    values = collector(
        width=project_api.num(100, unit="mm", min=10, max=500),
        height=project_api.num(20),
    )
    assert values.width == 250.0
    assert values.height == 20.0
    assert [spec["name"] for spec in collector.specs] == ["width", "height"]
    assert collector.specs[0]["default"] == 100.0
    assert collector.specs[0]["unit"] == "mm"


def test_params_clamps_stored_values_into_declared_range() -> None:
    collector = project_api.ParamsCollector({"width": 9999.0})
    values = collector(width=project_api.num(100, min=10, max=500))
    assert values.width == 500.0


def test_params_is_single_shot_and_validates_names() -> None:
    collector = project_api.ParamsCollector({})
    collector(width=project_api.num(1))
    with pytest.raises(project_api.ProjectParameterError):
        collector(other=project_api.num(1))
    fresh = project_api.ParamsCollector({})
    with pytest.raises(project_api.ProjectParameterError):
        fresh(BadName=project_api.num(1))
    fresh2 = project_api.ParamsCollector({})
    with pytest.raises(project_api.ProjectParameterError):
        fresh2(width=123)


def test_param_values_are_immutable() -> None:
    values = project_api.ParamsCollector({})(width=project_api.num(1))
    with pytest.raises(TypeError):
        values.width = 2
    with pytest.raises(AttributeError):
        _ = values.missing


# -- result grouping --------------------------------------------------------


def test_group_result_by_domain_partitions_in_order() -> None:
    result = {
        "body": _value("partdesign", "body"),
        "profile": _value("sketcher", "sketch", "sketch"),
        "plate": _value("part"),
    }
    grouped = project_worker._group_result_by_domain(result)
    assert list(grouped) == list(project_api.EVALUATION_ORDER)
    assert list(grouped["partdesign"]) == ["body"]
    assert list(grouped["sketcher"]) == ["profile"]
    assert list(grouped["part"]) == ["plate"]
    assert grouped["assembly"] == {}


def test_group_result_rejects_foreign_domains() -> None:
    with pytest.raises(ValueError, match="unsupported domain"):
        project_worker._group_result_by_domain({"x": _value("techdraw")})


def test_group_result_rejects_non_domain_values() -> None:
    with pytest.raises(TypeError):
        project_worker._group_result_by_domain({"x": 42})


# -- inline component sources ----------------------------------------------


def test_inline_source_token_is_deterministic() -> None:
    payload = _value("part").to_payload()
    token_a = project_api.inline_source_token(payload)
    token_b = project_api.inline_source_token(dict(payload))
    assert token_a == token_b
    assert token_a.startswith("src-")
    other = project_api.inline_source_token(_value("part", "cylinder").to_payload())
    assert other != token_a


def test_resolve_inline_sources_requires_declared_partdesign_output(tmp_path) -> None:
    payload = _value("partdesign", "body").to_payload()
    token = project_api.inline_source_token(payload)
    with pytest.raises(ValueError, match="also be returned as an output"):
        project_worker._resolve_inline_sources(tmp_path, {token: payload}, {})


def test_resolve_inline_sources_requires_declared_part_output(tmp_path) -> None:
    payload = _value("part").to_payload()
    token = project_api.inline_source_token(payload)
    with pytest.raises(ValueError, match="also be returned as an output"):
        project_worker._resolve_inline_sources(tmp_path, {token: payload}, {})


def test_resolve_inline_sources_reuses_declared_artifacts(tmp_path) -> None:
    payload = _value("partdesign", "body").to_payload()
    token = project_api.inline_source_token(payload)
    artifact = tmp_path / "outputs" / "output-000.brep"
    artifact.parent.mkdir()
    artifact.write_bytes(b"fake-brep")
    key = project_worker._canonical_json(payload)
    index = {
        key: {
            "name": "body",
            "artifact_path": "outputs/output-000.brep",
        }
    }
    entries, component_sources = project_worker._resolve_inline_sources(
        tmp_path, {token: payload}, index
    )
    assert component_sources == {token: "body"}
    assert len(entries) == 1
    entry = entries[0]
    assert entry["document_uid"] == project_api.INLINE_SOURCE_UID
    assert entry["object_name"] == token
    assert entry["artifact_path"] == "outputs/output-000.brep"
    assert entry["brep_sha256"] == project_worker._file_sha256(artifact)
    assert entry["label"] == "body"


# -- digest -----------------------------------------------------------------


def _digest_outputs(tmp_path: Path) -> list[dict]:
    artifact = tmp_path / "outputs" / "output-000.brep"
    artifact.parent.mkdir(exist_ok=True)
    artifact.write_bytes(b"solid-bytes")
    return [
        {
            "name": "body",
            "domain": "partdesign",
            "type": "solid",
            "artifact_kind": "brep",
            "artifact_path": "outputs/output-000.brep",
            "definition": {"a": 1},
        },
        {
            "name": "asm",
            "domain": "assembly",
            "type": "assembly",
            "definition": {"b": 2},
        },
    ]


def test_project_digest_is_stable_under_output_order(tmp_path) -> None:
    outputs = _digest_outputs(tmp_path)
    forward = project_worker.compute_project_digest(tmp_path, outputs)
    backward = project_worker.compute_project_digest(tmp_path, outputs[::-1])
    assert forward == backward
    assert len(forward) == 64


def test_project_digest_tracks_artifact_bytes(tmp_path) -> None:
    outputs = _digest_outputs(tmp_path)
    before = project_worker.compute_project_digest(tmp_path, outputs)
    (tmp_path / "outputs" / "output-000.brep").write_bytes(b"different")
    after = project_worker.compute_project_digest(tmp_path, outputs)
    assert before != after


def _trace_output(tmp_path: Path) -> dict:
    """One simulation output that retained a trace, as the worker writes it."""

    artifact = tmp_path / "outputs" / "assembly-simulation-trace.json"
    artifact.parent.mkdir(exist_ok=True)
    artifact.write_bytes(b'{"schema":"cadex-assembly-simulation-trace-v1"}')
    return {
        "name": "sim",
        "domain": "assembly",
        "type": "simulation",
        "artifact_kind": "assembly_simulation_json",
        "artifact_path": "outputs/assembly-simulation-trace.json",
        "definition": {"operation": "simulation"},
    }


def test_a_retained_trace_reaches_the_project_digest(tmp_path) -> None:
    """The change ADR-068 is (ADR-064 decided it, on M3's evidence).

    Before this, a simulation was "everything else": its digest entry was the
    graph that produced it, not the numbers that came out. Two projects whose
    scripts matched but whose traces came from different solver versions had
    the same digest, and `open_project` asserts digest equality — so the
    difference passed in silence.
    """

    outputs = [*_digest_outputs(tmp_path), _trace_output(tmp_path)]
    before = project_worker.compute_project_digest(tmp_path, outputs)
    (tmp_path / "outputs" / "assembly-simulation-trace.json").write_bytes(
        b'{"schema":"cadex-assembly-simulation-trace-v1","moved":true}'
    )
    after = project_worker.compute_project_digest(tmp_path, outputs)
    assert before != after, "the trace's own bytes must reach the digest"


def test_the_graph_that_asked_for_a_trace_still_reaches_the_digest(tmp_path) -> None:
    """Bytes were **added**, not substituted, and this is why it matters.

    A trace artifact is a rendering of the output, not the whole of it: the
    simulation also carries settings that a reader can change without moving
    a single frame — a label being the obvious one. Substituting the bytes
    for the recipe would have made those edits invisible to the digest,
    which is a regression dressed as a simplification. Keeping both makes the
    change strictly monotonic.
    """

    outputs = [*_digest_outputs(tmp_path), _trace_output(tmp_path)]
    before = project_worker.compute_project_digest(tmp_path, outputs)
    outputs[-1]["definition"] = {"operation": "simulation", "end_time_s": 2.0}
    assert project_worker.compute_project_digest(tmp_path, outputs) != before

    # ...and a change that moves no frame at all is still visible.
    outputs[-1]["definition"] = {"operation": "simulation", "label": "renamed"}
    assert project_worker.compute_project_digest(tmp_path, outputs) != before


def test_any_retained_artifact_reaches_the_digest_by_existing(tmp_path) -> None:
    """The rule is keyed on having bytes, not on a roster of known kinds.

    This is the property that makes the rule worth having: an output kind
    invented later joins the project digest by writing a file, rather than by
    someone remembering to add it to a list here. Asserted with a kind this
    tree does not define, because a test using a real one could not tell the
    general rule from a special case.
    """

    artifact = tmp_path / "outputs" / "something.bin"
    artifact.parent.mkdir(exist_ok=True)
    artifact.write_bytes(b"first")
    outputs = [
        {
            "name": "thing",
            "domain": "assembly",
            "type": "some_future_type",
            "artifact_kind": "some_future_kind",
            "artifact_path": "outputs/something.bin",
            "definition": {"operation": "future"},
        }
    ]
    before = project_worker.compute_project_digest(tmp_path, outputs)
    artifact.write_bytes(b"second")
    assert project_worker.compute_project_digest(tmp_path, outputs) != before


def test_a_mesh_is_still_identified_by_its_vertices_and_not_its_bytes(
    tmp_path,
) -> None:
    """The one exception, and the reason it is one (ADR-016).

    The native set operations re-triangulate coplanar regions
    non-deterministically while the vertex set stays exact, so hashing a
    mesh's bytes would flap the digest on identical geometry. Rewriting the
    .ply must change nothing; changing the fingerprint must change everything.
    """

    artifact = tmp_path / "outputs" / "output-002.ply"
    artifact.parent.mkdir(exist_ok=True)
    artifact.write_bytes(b"ply-one")
    outputs = [
        {
            "name": "hull",
            "domain": "mesh",
            "type": "mesh",
            "artifact_kind": "mesh",
            "artifact_path": "outputs/output-002.ply",
            "geometry_sha256": "c" * 64,
            "definition": {"operation": "from_shape"},
        }
    ]
    before = project_worker.compute_project_digest(tmp_path, outputs)
    artifact.write_bytes(b"ply-two-retriangulated")
    assert project_worker.compute_project_digest(tmp_path, outputs) == before

    outputs[0]["geometry_sha256"] = "d" * 64
    assert project_worker.compute_project_digest(tmp_path, outputs) != before


def test_an_approximating_mesh_still_falls_back_to_its_definition(tmp_path) -> None:
    """A decimate tree carries no fingerprint, and must not gain one by bytes.

    Its result is run-dependent by construction, so its bytes are the last
    thing that should identify it — which is exactly the trap the inverted
    rule would have walked into if `mesh` were not excluded as a *kind*
    rather than by the presence of a fingerprint.
    """

    artifact = tmp_path / "outputs" / "output-003.ply"
    artifact.parent.mkdir(exist_ok=True)
    artifact.write_bytes(b"decimated-one")
    outputs = [
        {
            "name": "lite",
            "domain": "mesh",
            "type": "mesh",
            "artifact_kind": "mesh",
            "artifact_path": "outputs/output-003.ply",
            "definition": {"operation": "decimate", "reduction": 0.5},
        }
    ]
    before = project_worker.compute_project_digest(tmp_path, outputs)
    artifact.write_bytes(b"decimated-two-different-run")
    assert project_worker.compute_project_digest(tmp_path, outputs) == before

    outputs[0]["definition"] = {"operation": "decimate", "reduction": 0.9}
    assert project_worker.compute_project_digest(tmp_path, outputs) != before


def test_an_output_with_no_artifact_is_still_its_recipe(tmp_path) -> None:
    outputs = _digest_outputs(tmp_path)
    before = project_worker.compute_project_digest(tmp_path, outputs)
    outputs[1]["definition"] = {"b": 3}
    assert project_worker.compute_project_digest(tmp_path, outputs) != before


def test_project_digest_rounds_placements_below_tolerance(tmp_path) -> None:
    outputs = _digest_outputs(tmp_path)
    outputs[1]["solved_placement_matrix"] = [1.0, 0.0, 0.25, 5.0]
    base = project_worker.compute_project_digest(tmp_path, outputs)
    outputs[1]["solved_placement_matrix"] = [1.0 + 4.9e-10, 0.0, 0.25, 5.0]
    noisy = project_worker.compute_project_digest(tmp_path, outputs)
    assert base == noisy
    outputs[1]["solved_placement_matrix"] = [1.001, 0.0, 0.25, 5.0]
    moved = project_worker.compute_project_digest(tmp_path, outputs)
    assert moved != base


# -- script store -----------------------------------------------------------


def test_script_store_round_trip(tmp_path) -> None:
    from CadexProject import CadexProjectScriptStore

    store = CadexProjectScriptStore(tmp_path)
    assert store.read_source() == ""
    assert store.read_state()["working_revision"] == ""

    state = store.write(
        source="result = {}",
        state_updates={"working_revision": "a" * 64, "param_values": {"w": 3.0}},
    )
    assert state["working_revision"] == "a" * 64
    assert state["updated_at"]
    assert store.read_source() == "result = {}"
    reloaded = store.read_state()
    assert reloaded["param_values"] == {"w": 3.0}
    assert reloaded["accepted_revision"] == ""


def test_script_store_rejects_unknown_state_fields(tmp_path) -> None:
    from CadexProject import CadexProjectScriptStore

    store = CadexProjectScriptStore(tmp_path)
    with pytest.raises(ValueError):
        store.write(state_updates={"bogus": 1})
    with pytest.raises(ValueError):
        store.write(state_updates={"schema": "x"})


def test_script_store_artifacts_dir_requires_hex_revision(tmp_path) -> None:
    from CadexProject import CadexProjectScriptStore

    store = CadexProjectScriptStore(tmp_path)
    path = store.artifacts_dir("ab12" * 16)
    assert path.parent == store.artifacts_root
    with pytest.raises(ValueError):
        store.artifacts_dir("not-hex!")
    with pytest.raises(ValueError):
        store.artifacts_dir("")


def test_project_script_revision_is_content_addressed() -> None:
    import types, sys as _sys

    from CadexScriptedDomains import project_script_revision

    base = project_script_revision(
        source="result = {}", param_specs=[], param_values={}
    )
    assert len(base) == 64
    assert base == project_script_revision(
        source="result = {}", param_specs=[], param_values={}
    )
    assert base != project_script_revision(
        source="result = {}", param_specs=[], param_values={"w": 1.0}
    )
    assert base != project_script_revision(
        source="result = {'a': 1}", param_specs=[], param_values={}
    )
