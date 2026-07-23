# SPDX-License-Identifier: LGPL-2.1-or-later

"""core.relink_object: repoint a live App::Link at a new target in place.

A dead assembly component link (its target deleted) is repaired by rewriting
``LinkedObject`` without deleting the link, so every joint that references the
link by name keeps its ``Reference`` intact. These tests pin the precondition
guards and, by stubbing the non-rollback transaction wrapper, the real repoint
handler + verifier and the dependent-recovery report — all with lightweight
geometry fakes (no running FreeCAD), matching the suite's convention.
"""

from __future__ import annotations

import sys

import pytest

from tool_impl.service import core_relink_object


# --- Duck-typed FreeCAD fakes ------------------------------------------------


class FakeShape:
    def __init__(self, null: bool = False) -> None:
        self._null = null

    def isNull(self) -> bool:
        return self._null


class FakeObj:
    def __init__(
        self,
        name,
        type_id,
        *,
        derived=(),
        label=None,
        linked=None,
        shape=None,
        valid=True,
        state=None,
        properties=None,
        inlist=None,
        out_recursive=None,
        document=None,
        refs=None,
    ) -> None:
        self.Name = name
        self.TypeId = type_id
        self.Label = label or name
        self.LinkedObject = linked
        self.Shape = shape
        self._valid = valid
        self.State = list(state or [])
        self.PropertiesList = list(properties or [])
        self.InList = list(inlist or [])
        self.OutListRecursive = list(out_recursive or [])
        self.Document = document
        self._derived = set(derived)
        self._refs = list(refs or [])
        self.touched = False

    def isValid(self) -> bool:
        return self._valid

    def isDerivedFrom(self, type_id: str) -> bool:
        return type_id == self.TypeId or type_id in self._derived

    def touch(self) -> None:
        self.touched = True


class FakeDoc:
    def __init__(self, name, objects) -> None:
        self.Name = name
        self.Objects = list(objects)
        self._by_name = {obj.Name: obj for obj in objects}
        self.recomputed = False
        for obj in objects:
            obj.Document = self

    def getObject(self, name):
        return self._by_name.get(name)

    def recompute(self) -> None:
        # Model FreeCAD: a link derives its shape from a live target, and a
        # dependent whose references all resolve becomes valid again.
        self.recomputed = True
        for obj in self.Objects:
            linked = getattr(obj, "LinkedObject", None)
            if linked is not None and linked.Shape is not None and not linked.Shape.isNull():
                obj.Shape = linked.Shape
                obj._valid = True
        for obj in self.Objects:
            if "Reference1" in obj.PropertiesList and obj._refs:
                if all(ref._valid for ref in obj._refs):
                    obj._valid = True


class FakeService:
    def __init__(self, doc) -> None:
        self._doc = doc

    def _active_document(self):
        return self._doc

    def _partdesign_body_for_feature(self, obj):
        return None


def _dead_link_scene():
    """A dead component link, a live chassis body, and a broken peg joint."""
    body = FakeObj("Chassis", "PartDesign::Body", shape=FakeShape(null=False), valid=True)
    link = FakeObj(
        "ChassisBody001",
        "App::Link",
        derived=("App::Link",),
        linked=None,
        shape=FakeShape(null=True),
        valid=False,
        state=["Invalid"],
        properties=["LinkedObject"],
    )
    joint = FakeObj(
        "Joint",
        "App::FeaturePython",
        label="PegJoint",
        valid=False,
        state=["Invalid"],
        properties=["Reference1", "Reference2"],
        refs=[link],
    )
    link.InList = [joint]
    doc = FakeDoc("Rover", [body, link, joint])
    return doc, body, link, joint


# --- Pure helpers ------------------------------------------------------------


class TestHelpers:
    def test_is_link_by_derivation_and_by_property(self) -> None:
        derived = FakeObj("L", "App::Link", derived=("App::Link",))
        by_prop = FakeObj("A", "Assembly::AssemblyLink", properties=["LinkedObject"])
        body = FakeObj("B", "PartDesign::Body")
        assert core_relink_object._is_link(derived) is True
        assert core_relink_object._is_link(by_prop) is True
        assert core_relink_object._is_link(body) is False

    def test_dependents_recovered_only_reports_false_to_true(self) -> None:
        before = [
            {"name": "Joint", "is_valid": False},
            {"name": "Other", "is_valid": True},
        ]
        after = [
            {"name": "Joint", "is_valid": True},
            {"name": "Other", "is_valid": True},
        ]
        recovered = core_relink_object._dependents_recovered(before, after)
        assert [item["name"] for item in recovered] == ["Joint"]

    def test_invalid_names_flags_state_and_isvalid(self) -> None:
        good = FakeObj("Good", "Part::Feature", valid=True)
        bad_state = FakeObj("BadState", "Part::Feature", valid=True, state=["Invalid"])
        bad_valid = FakeObj("BadValid", "Part::Feature", valid=False)
        doc = FakeDoc("D", [good, bad_state, bad_valid])
        assert core_relink_object._invalid_names(doc) == {"BadState", "BadValid"}

    def test_dependent_summary_flags_joints(self) -> None:
        joint = FakeObj("J", "App::FeaturePython", properties=["Reference1"])
        plain = FakeObj("P", "App::Link", properties=["LinkedObject"])
        assert core_relink_object._dependent_summary(joint)["is_joint"] is True
        assert core_relink_object._dependent_summary(plain)["is_joint"] is False


# --- Precondition guards -----------------------------------------------------


class TestPreconditions:
    def test_no_active_document(self) -> None:
        result = core_relink_object.run(FakeService(None), "L", "T")
        assert result["ok"] is False
        assert result["failure_code"] == "NO_ACTIVE_DOCUMENT"

    def test_link_not_found_lists_link_candidates(self) -> None:
        doc, _body, link, _joint = _dead_link_scene()
        result = core_relink_object.run(FakeService(doc), "Missing", "Chassis")
        assert result["failure_code"] == "LINK_NOT_FOUND"
        assert any(c["name"] == "ChassisBody001" for c in result["candidates"])

    def test_not_a_link_rejected(self) -> None:
        doc, _body, _link, _joint = _dead_link_scene()
        result = core_relink_object.run(FakeService(doc), "Chassis", "Chassis")
        assert result["failure_code"] == "NOT_A_LINK"

    def test_target_not_found(self) -> None:
        doc, _body, _link, _joint = _dead_link_scene()
        result = core_relink_object.run(FakeService(doc), "ChassisBody001", "Nope")
        assert result["failure_code"] == "TARGET_NOT_FOUND"

    def test_self_link_rejected(self) -> None:
        doc, _body, _link, _joint = _dead_link_scene()
        result = core_relink_object.run(FakeService(doc), "ChassisBody001", "ChassisBody001")
        # A link that targets itself is caught as NOT_A_LINK-safe SELF_LINK guard.
        assert result["failure_code"] == "SELF_LINK"

    def test_dependency_cycle_rejected(self) -> None:
        doc, body, link, _joint = _dead_link_scene()
        # Make the target already depend on the link -> repoint would cycle.
        body.OutListRecursive = [link]
        result = core_relink_object.run(FakeService(doc), "ChassisBody001", "Chassis")
        assert result["failure_code"] == "DEPENDENCY_CYCLE"

    def test_non_part_target_rejected(self) -> None:
        doc, _body, _link, _joint = _dead_link_scene()
        stray = FakeObj("Sketch", "Sketcher::SketchObject")
        doc.Objects.append(stray)
        doc._by_name[stray.Name] = stray
        result = core_relink_object.run(FakeService(doc), "ChassisBody001", "Sketch")
        assert result["failure_code"] == "TARGET_NOT_LINKABLE"
        assert result["target_validation"]["ok"] is False


# --- Repoint handler + verifier (transaction wrapper stubbed) ----------------


class TestRepoint:
    @pytest.fixture(autouse=True)
    def _stub_transaction(self, monkeypatch):
        """Run the real handler/verifier without FreeCAD's transaction stack."""

        def fake_transaction(name, handler, verifier=None):
            result = handler()
            verification = verifier(result) if verifier else {"ok": True, "checks": []}
            return {
                "ok": bool(verification.get("ok")),
                "result": result,
                "verification": verification,
                "document_delta": {},
                "native_diagnostics": {"captured": True, "diagnostics": []},
            }

        monkeypatch.setattr(core_relink_object, "run_freecad_transaction", fake_transaction)
        yield

    def test_repoint_recovers_dead_link_and_joint(self, monkeypatch) -> None:
        doc, _body, link, joint = _dead_link_scene()
        monkeypatch.setitem(sys.modules, "FreeCAD", sys.modules["FreeCAD"])
        sys.modules["FreeCAD"].ActiveDocument = doc

        result = core_relink_object.run(FakeService(doc), "ChassisBody001", "Chassis")

        assert result["ok"] is True
        assert result["operation"] == "relink_object"
        # The link kept its identity but now points at the live body.
        assert link.LinkedObject is doc.getObject("Chassis")
        assert link.touched is True
        assert result["link_state_after"]["linked_object"] == "Chassis"
        assert result["link_state_after"]["has_shape"] is True
        # The peg joint that referenced the link resolves again.
        assert joint._valid is True
        assert [item["name"] for item in result["dependents_recovered"]] == ["Joint"]
        checks = {c["name"]: c["ok"] for c in result["transaction"]["verification"]["checks"]}
        assert checks == {
            "link_repointed": True,
            "link_carries_shape": True,
            "no_new_invalid_objects": True,
        }

    def test_repoint_reports_before_state(self, monkeypatch) -> None:
        doc, _body, _link, _joint = _dead_link_scene()
        sys.modules["FreeCAD"].ActiveDocument = doc

        result = core_relink_object.run(FakeService(doc), "ChassisBody001", "Chassis")

        before = result["link_state_before"]
        assert before["linked_object"] is None
        assert before["linked_object_alive"] is False
        assert before["has_shape"] is False
        assert any(dep["is_joint"] for dep in before["dependents"])
