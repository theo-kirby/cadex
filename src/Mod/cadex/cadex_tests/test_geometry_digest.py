# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The geometry digest, and the drift it exists to survive (ADR-389).

`part.offset` is OCCT's BRepOffset_MakeOffset, and it serializes an identical
solid to different bytes every process. `compute_project_digest` identifies a
BREP output by those bytes, so an accepted design using it could never be
reopened: the restore pass rebuilt the same model and refused it, differently
every time.

These tests pin the second opinion. The byte digest is unchanged and still
the accepted-state guard; the geometry digest is consulted only when the
bytes disagree, and only to say whether the disagreement is the serialization
or the model.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import types

import pytest

from CadexGeometryDigest import (
    project_digest,
    project_geometry_digest,
    shape_geometry_fingerprint,
    staged_geometry_digest,
)

#: The digest of :func:`_fixture_outputs` under the implementation that
#: predates this module, measured against it before the material moved here.
#: The byte digest is every stored ``accepted_digest`` in every project on
#: disk; a refactor that moves it by one bit shuts all of them.
FROZEN_PROJECT_DIGEST = (
    "6ef63cdee030cc5d4eda01a582f0bfea09e9171f4ce37296f5b34482df06b3fb"
)


def _fixture_outputs() -> list[dict]:
    return [
        {
            "name": "beta",
            "domain": "part",
            "type": "solid",
            "artifact_path": "a.brep",
            "artifact_kind": "brep",
            "definition": {"operation": "box", "arguments": [1, 2, 3]},
        },
        {
            "name": "alpha",
            "domain": "mesh",
            "type": "mesh",
            "artifact_path": "m.ply",
            "artifact_kind": "mesh",
            "geometry_sha256": "deadbeef",
            "definition": {"operation": "decimate"},
        },
        {
            "name": "gamma",
            "domain": "assembly",
            "type": "rollout",
            "artifact_path": "t.json",
            "artifact_kind": "trace",
            "definition": {"operation": "rollout"},
            "solved_placement_matrix": [1.0000000000123, 0.0, 0.0, 2.5],
        },
        {
            "name": "delta",
            "domain": "assembly",
            "type": "assembly",
            "definition": {"operation": "assemble"},
        },
    ]


def _fixture_root(tmp_path: Path) -> Path:
    (tmp_path / "a.brep").write_bytes(b"BREP-A")
    (tmp_path / "t.json").write_bytes(b'{"trace": 1}')
    return tmp_path


class _Point:
    def __init__(self, x: float, y: float, z: float) -> None:
        self.X, self.Y, self.Z = x, y, z


def _shape(vertices, lengths, areas, *, area=None, box=(0.0, 0.0, 0.0, 1.0, 1.0, 1.0)):
    """A duck-typed stand-in for the handful of members the fingerprint reads."""

    return types.SimpleNamespace(
        Vertexes=[_Point(*v) for v in vertices],
        Edges=[types.SimpleNamespace(Length=value) for value in lengths],
        Faces=[types.SimpleNamespace(Area=value) for value in areas],
        Shells=[object()],
        Solids=[object()],
        Area=sum(areas) if area is None else area,
        BoundBox=types.SimpleNamespace(
            XMin=box[0], YMin=box[1], ZMin=box[2],
            XMax=box[3], YMax=box[4], ZMax=box[5],
        ),
    )


def test_the_fingerprint_does_not_care_what_order_the_kernel_lists_things_in():
    # The measured drift: same solid, same vertices, edges and faces, in a
    # different order in the file every process.
    forward = _shape(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 2.0, 0.0)],
        [1.0, 2.0, 2.5],
        [3.0, 4.0],
    )
    shuffled = _shape(
        [(1.0, 2.0, 0.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)],
        [2.5, 1.0, 2.0],
        [4.0, 3.0],
    )
    assert shape_geometry_fingerprint(forward) == shape_geometry_fingerprint(shuffled)


@pytest.mark.parametrize(
    "changed",
    [
        pytest.param(
            {"vertices": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 2.5, 0.0)]},
            id="a vertex moved",
        ),
        pytest.param({"lengths": [1.0, 2.0, 2.6]}, id="an edge grew"),
        pytest.param({"areas": [3.0, 4.5]}, id="a face grew"),
        pytest.param({"box": (0.0, 0.0, 0.0, 1.0, 1.0, 9.0)}, id="the bounds moved"),
    ],
)
def test_the_fingerprint_moves_when_the_measurements_do(changed):
    base = {
        "vertices": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 2.0, 0.0)],
        "lengths": [1.0, 2.0, 2.5],
        "areas": [3.0, 4.0],
    }
    reference = shape_geometry_fingerprint(_shape(**base))
    assert shape_geometry_fingerprint(_shape(**{**base, **changed})) != reference


def test_the_byte_digest_is_exactly_what_it_was_before_the_material_moved(tmp_path):
    root = _fixture_root(tmp_path)
    assert project_digest(root, _fixture_outputs()) == FROZEN_PROJECT_DIGEST


def test_the_byte_digest_still_refuses_a_rewritten_brep(tmp_path):
    root = _fixture_root(tmp_path)
    before = project_digest(root, _fixture_outputs())
    (root / "a.brep").write_bytes(b"BREP-A-REORDERED")
    assert project_digest(root, _fixture_outputs()) != before


def test_the_geometry_digest_survives_the_drift_the_byte_digest_cannot(
    tmp_path, monkeypatch
):
    # One BREP artifact, serialized twice from the same solid. The bytes
    # differ; the kernel measures the same thing. This is the whole defect.
    import CadexGeometryDigest as module

    root = _fixture_root(tmp_path)
    monkeypatch.setattr(
        module, "brep_geometry_fingerprint", lambda _path: "same-solid"
    )
    before = module.project_geometry_digest(root, _fixture_outputs())
    (root / "a.brep").write_bytes(b"BREP-A-REORDERED-BY-OCCT")
    assert module.project_digest(root, _fixture_outputs()) != project_digest(
        tmp_path, []
    )
    assert module.project_geometry_digest(root, _fixture_outputs()) == before


def test_the_geometry_digest_refuses_a_changed_recipe_before_it_measures(
    tmp_path, monkeypatch
):
    # The guard the fallback must not weaken: a hand-edited script changes
    # the definition, and a BREP entry carries its definition alongside the
    # measurements for exactly this case.
    import CadexGeometryDigest as module

    root = _fixture_root(tmp_path)
    monkeypatch.setattr(
        module, "brep_geometry_fingerprint", lambda _path: "same-solid"
    )
    before = module.project_geometry_digest(root, _fixture_outputs())
    edited = _fixture_outputs()
    edited[0]["definition"] = {"operation": "box", "arguments": [1, 2, 4]}
    assert module.project_geometry_digest(root, edited) != before


def test_the_geometry_digest_still_sees_every_non_brep_definition(
    tmp_path, monkeypatch
):
    import CadexGeometryDigest as module

    root = _fixture_root(tmp_path)
    monkeypatch.setattr(
        module, "brep_geometry_fingerprint", lambda _path: "same-solid"
    )
    before = module.project_geometry_digest(root, _fixture_outputs())

    # The recipe that asked for the derived output.
    redefined = _fixture_outputs()
    redefined[2]["definition"] = {"operation": "rollout", "steps": 400}
    assert module.project_geometry_digest(root, redefined) != before

    # The pose the solver put it at.
    moved = _fixture_outputs()
    moved[2]["solved_placement_matrix"] = [1.0, 0.0, 0.0, 9.0]
    assert module.project_geometry_digest(root, moved) != before

    # ...and a mesh's vertex set, which is geometry and not a derived export.
    retriangulated = _fixture_outputs()
    retriangulated[1]["geometry_sha256"] = "cafef00d"
    assert module.project_geometry_digest(root, retriangulated) != before


def test_the_geometry_digest_forgives_a_re_exported_derived_artifact(
    tmp_path, monkeypatch
):
    # ADR-396, measured on ot7-plover-e: the ADR-393 fix made the engine
    # export a *better* MJCF for an unchanged design -- 2 of 90 outputs moved,
    # the model and the training task that pins the model's digest, with every
    # BREP artifact, every canonical definition and every solved placement
    # identical. The byte digest must refuse that and the geometry fallback
    # must accept it, or the project can never be opened again.
    import CadexGeometryDigest as module

    root = _fixture_root(tmp_path)
    monkeypatch.setattr(
        module, "brep_geometry_fingerprint", lambda _path: "same-solid"
    )
    design = _fixture_outputs() + [
        {
            "name": "epsilon",
            "domain": "assembly",
            "type": "training_task",
            "artifact_path": "task.json",
            "artifact_kind": "assembly_training_task_json",
            "definition": {"operation": "task", "model": "gamma"},
        }
    ]
    (root / "task.json").write_bytes(b'{"model": {"sha256": "one", "bytes": 11}}')
    bytes_before = project_digest(root, design)
    geometry_before = module.project_geometry_digest(root, design)

    # The same script, re-exported by an engine that fixed its exporter.
    (root / "t.json").write_bytes(b'{"trace": 1, "weld": "fixed"}')
    (root / "task.json").write_bytes(b'{"model": {"sha256": "two", "bytes": 22}}')

    assert project_digest(root, design) != bytes_before, (
        "the accepted-state guard must still see the changed export"
    )
    assert module.project_geometry_digest(root, design) == geometry_before


def test_a_retained_attempt_is_measured_from_the_result_it_kept(
    tmp_path, monkeypatch
):
    import CadexGeometryDigest as module

    staging = _fixture_root(tmp_path)
    (staging / "result.json").write_text(
        json.dumps({"ok": True, "outputs": _fixture_outputs()}), encoding="utf-8"
    )
    monkeypatch.setattr(
        module, "brep_geometry_fingerprint", lambda _path: "same-solid"
    )
    assert staged_geometry_digest(staging) == module.project_geometry_digest(
        staging, _fixture_outputs()
    )


def test_a_retained_attempt_with_no_output_list_is_not_measurable(tmp_path):
    (tmp_path / "result.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    with pytest.raises(ValueError):
        staged_geometry_digest(tmp_path)


def _attempt(root: Path, name: str, digest: str) -> dict:
    staging = root / "script_artifacts" / name
    staging.mkdir(parents=True)
    (staging / "result.json").write_text(
        json.dumps({"ok": True, "outputs": [], "digest": digest}), encoding="utf-8"
    )
    return {"staging": f"script_artifacts/{name}"}


def test_the_restore_pass_forgives_drift_and_only_drift(tmp_path, monkeypatch):
    import CadexGeometryDigest as module
    import cadexd

    accepted = _attempt(tmp_path, "accepted", "bytes-one")
    restored = _attempt(tmp_path, "restored", "bytes-two")
    measured = {"accepted": "same-model", "restored": "same-model"}
    monkeypatch.setattr(
        module,
        "staged_geometry_digest",
        lambda staging: measured[Path(staging).name],
    )

    agreed, observed, learned = cadexd._geometry_agrees(
        tmp_path, accepted, restored, ""
    )
    assert agreed is True, observed
    assert observed["restored_geometry_digest"] == "same-model"
    assert "the bytes drifted" in observed["geometry_comparison"]
    # ...and the project has learned what it measures, so the next reopen
    # needs no retained accepted attempt at all.
    assert learned == "same-model"

    measured["restored"] = "a different model"
    agreed, observed, learned = cadexd._geometry_agrees(
        tmp_path, accepted, restored, ""
    )
    assert agreed is False
    assert learned == ""
    assert observed["geometry_comparison"] == "the rebuilt model is not the accepted one"


def test_a_remembered_measurement_belongs_to_one_accepted_digest():
    import cadexd

    state = {
        "accepted_geometry": {
            "accepted_digest": "accepted-one",
            "geometry_digest": "same-model",
        }
    }
    assert cadexd._remembered_geometry(state, "accepted-one") == "same-model"
    # `rebuild` and `write_script` both re-accept. A measurement kept past the
    # model it describes would refuse the model that replaced it.
    assert cadexd._remembered_geometry(state, "accepted-two") == ""
    assert cadexd._remembered_geometry({"accepted_geometry": None}, "x") == ""
    assert cadexd._remembered_geometry({}, "x") == ""


def test_the_store_drops_a_measurement_once_its_accepted_digest_moves_on(tmp_path):
    from CadexScriptStore import CadexProjectScriptStore

    store = CadexProjectScriptStore(tmp_path)
    learned = {"accepted_digest": "accepted-one", "geometry_digest": "same-model"}
    store.write(
        state_updates={"accepted_digest": "accepted-one", "accepted_geometry": learned}
    )
    # Unrelated writes under the same accepted digest keep what was learned.
    store.write(state_updates={"working_revision": "abc"})
    assert store.read_state()["accepted_geometry"] == learned
    # A re-accept moves the digest on. The old measurement can never be read
    # again, so script.json must stop naming it (ot9 REPORT, remaining defect 3).
    store.write(state_updates={"accepted_digest": "accepted-two"})
    assert store.read_state()["accepted_geometry"] is None
    # A copy carried in from another project heals on its first write.
    state = json.loads(store.state_path.read_text(encoding="utf-8"))
    state["accepted_geometry"] = learned
    store.state_path.write_text(json.dumps(state), encoding="utf-8")
    store.write(state_updates={"working_revision": "def"})
    assert store.read_state()["accepted_geometry"] is None


def test_a_learned_geometry_digest_outlives_the_attempt_it_came_from(
    tmp_path, monkeypatch
):
    import CadexGeometryDigest as module
    import cadexd

    accepted = _attempt(tmp_path, "accepted", "bytes-one")
    restored = _attempt(tmp_path, "restored", "bytes-two")
    monkeypatch.setattr(
        module, "staged_geometry_digest", lambda _staging: "same-model"
    )
    # A pre-ADR-398 restore could collect the accepted attempt. Preserve
    # recovery through the learned digest for those existing projects.
    shutil.rmtree(tmp_path / accepted["staging"])

    agreed, observed, learned = cadexd._geometry_agrees(
        tmp_path, accepted, restored, "same-model"
    )
    assert agreed is True, observed
    assert learned == "", "nothing new was learned, so nothing is rewritten"

    agreed, _observed, _learned = cadexd._geometry_agrees(
        tmp_path, accepted, restored, "some other model"
    )
    assert agreed is False


@pytest.mark.parametrize("missing", ["accepted", "restored"])
def test_a_project_whose_evidence_is_gone_is_still_refused(tmp_path, missing):
    import cadexd

    attempts = {
        "accepted": _attempt(tmp_path, "accepted", "bytes-one"),
        "restored": _attempt(tmp_path, "restored", "bytes-two"),
    }
    (tmp_path / attempts[missing]["staging"] / "result.json").unlink()
    agreed, observed, _learned = cadexd._geometry_agrees(
        tmp_path, attempts["accepted"], attempts["restored"], ""
    )
    assert agreed is False
    assert observed["geometry_comparison"] == (
        f"the {missing} attempt kept no result to re-measure"
    )


def test_a_kernel_that_cannot_read_the_artifact_back_is_not_an_agreement(
    tmp_path, monkeypatch
):
    import CadexGeometryDigest as module
    import cadexd

    accepted = _attempt(tmp_path, "accepted", "bytes-one")
    restored = _attempt(tmp_path, "restored", "bytes-two")

    def explode(_staging):
        raise RuntimeError("BRep_API: command not done")

    monkeypatch.setattr(module, "staged_geometry_digest", explode)
    agreed, observed, _learned = cadexd._geometry_agrees(
        tmp_path, accepted, restored, ""
    )
    assert agreed is False
    assert "could not be re-measured" in observed["geometry_comparison"]
    assert "BRep_API" in observed["geometry_comparison"]


def test_an_attempt_the_state_never_named_is_refused(tmp_path):
    import cadexd

    agreed, observed, _learned = cadexd._geometry_agrees(
        tmp_path, None, {"staging": ""}, ""
    )
    assert agreed is False
    assert observed["geometry_comparison"] == (
        "the restored attempt kept no result to re-measure"
    )
