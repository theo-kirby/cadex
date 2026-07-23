# SPDX-License-Identifier: LGPL-2.1-or-later

"""assembly.delete_joint: drop one joint from an assembly's JointGroup.

Deleting a joint removes only that constraint (a mate or a grounding); the
component links and their geometry are untouched. These tests pin the
precondition guards and, by stubbing the non-rollback transaction wrapper, the
real removal handler + verifier and the remaining-joint report — with
lightweight fakes and no running FreeCAD, matching the suite's convention.
"""

from __future__ import annotations

import sys

import pytest

from tool_impl.service import assembly_delete_joint


# --- Duck-typed FreeCAD / assembly fakes -------------------------------------


class FakeJoint:
    def __init__(self, name, *, grounded=False, joint_type=None) -> None:
        self.Name = name
        self.Label = name
        self.TypeId = "App::FeaturePython"
        self.State = []
        self._valid = True
        if grounded:
            self.ObjectToGround = object()
        if joint_type is not None:
            self.JointType = joint_type

    def isValid(self) -> bool:
        return self._valid


class FakeJointGroup:
    def __init__(self, name, joints) -> None:
        self.Name = name
        self.TypeId = "Assembly::JointGroup"
        self.Group = list(joints)
        self.State = []

    def isValid(self) -> bool:
        return True

    def removeObject(self, obj):
        if obj in self.Group:
            self.Group.remove(obj)
        return [obj]


class FakeAssembly:
    def __init__(self, name, joint_group, components) -> None:
        self.Name = name
        self.Label = name
        self.TypeId = "Assembly::AssemblyObject"
        self.State = []
        self.Group = [joint_group, *components]
        self.OutList = [joint_group, *components]

    def isValid(self) -> bool:
        return True


class FakeDoc:
    def __init__(self, name, assembly, joint_group) -> None:
        self.Name = name
        self._assembly = assembly
        self._joint_group = joint_group
        self.recomputed = False

    @property
    def Objects(self):
        return [self._assembly, self._joint_group, *self._joint_group.Group]

    def getObject(self, name):
        for obj in self.Objects:
            if obj.Name == name:
                return obj
        return None

    def removeObject(self, name):
        target = None
        for obj in self._joint_group.Group:
            if obj.Name == name:
                target = obj
                break
        if target is not None:
            self._joint_group.Group.remove(target)

    def recompute(self):
        self.recomputed = True


class FakeService:
    def __init__(self, doc, assembly) -> None:
        self._doc = doc
        self._assembly = assembly

    def _active_document(self):
        return self._doc

    def _assembly_objects(self):
        return [self._assembly] if self._assembly is not None else []

    def _assembly_joint_objects(self, assembly):
        joints = []
        for child in assembly.Group:
            if getattr(child, "TypeId", "") == "Assembly::JointGroup":
                joints.extend(child.Group)
        return joints

    @staticmethod
    def _is_grounded_joint(obj):
        return getattr(obj, "ObjectToGround", None) is not None

    def _joint_summary(self, joint):
        return {
            "name": joint.Name,
            "label": joint.Label,
            "grounded": self._is_grounded_joint(joint),
            "joint_type": getattr(joint, "JointType", None),
        }


def _scene():
    grounded = FakeJoint("GroundedJoint", grounded=True)
    joint7 = FakeJoint("Joint007", joint_type="Fixed")
    joint8 = FakeJoint("Joint008", joint_type="Fixed")
    group = FakeJointGroup("JointGroup", [grounded, joint7, joint8])
    body = FakeJoint("Chassis")  # duck-typed placeholder component
    body.TypeId = "App::Link"
    assembly = FakeAssembly("Assembly", group, [body])
    doc = FakeDoc("Rover", assembly, group)
    return doc, assembly, group


# --- Preconditions -----------------------------------------------------------


class TestPreconditions:
    def test_no_active_document(self) -> None:
        result = assembly_delete_joint.run(FakeService(None, None), "Assembly", "Joint007")
        assert result["ok"] is False
        assert "No active document" in result["error"]

    def test_assembly_not_found(self) -> None:
        doc, assembly, _group = _scene()
        result = assembly_delete_joint.run(FakeService(doc, assembly), "Missing", "Joint007")
        assert result["ok"] is False
        assert "Assembly not found" in result["error"]

    def test_joint_not_in_assembly_lists_candidates(self) -> None:
        doc, assembly, _group = _scene()
        result = assembly_delete_joint.run(FakeService(doc, assembly), "Assembly", "Nope")
        assert result["ok"] is False
        names = {item["name"] for item in result["joints"]}
        assert {"Joint007", "Joint008", "GroundedJoint"} <= names


# --- Removal handler + verifier (transaction wrapper stubbed) ----------------


class TestDelete:
    @pytest.fixture(autouse=True)
    def _stub_transaction(self, monkeypatch):
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

        monkeypatch.setattr(assembly_delete_joint, "run_freecad_transaction", fake_transaction)
        yield

    def test_delete_mate_keeps_grounding(self, monkeypatch) -> None:
        doc, assembly, group = _scene()
        sys.modules["FreeCAD"].ActiveDocument = doc

        result = assembly_delete_joint.run(FakeService(doc, assembly), "Assembly", "Joint008")

        assert result["ok"] is True
        assert result["operation"] == "delete_joint"
        assert doc.getObject("Joint008") is None
        assert "Joint008" not in [j.Name for j in group.Group]
        remaining = {item["name"] for item in result["mutation"]["remaining_joints"]}
        assert remaining == {"GroundedJoint", "Joint007"}
        assert result["mutation"]["grounded_remaining"] == 1
        assert "assembly.solve" in result["next_action"]
        checks = {c["name"]: c["ok"] for c in result["transaction"]["verification"]["checks"]}
        assert checks == {
            "joint_absent": True,
            "joint_group_membership_cleared": True,
            "no_new_invalid_objects": True,
        }

    def test_delete_grounded_joint_warns_no_ground(self, monkeypatch) -> None:
        doc, assembly, group = _scene()
        sys.modules["FreeCAD"].ActiveDocument = doc

        result = assembly_delete_joint.run(
            FakeService(doc, assembly), "Assembly", "GroundedJoint"
        )

        assert result["ok"] is True
        assert doc.getObject("GroundedJoint") is None
        assert result["mutation"]["grounded_remaining"] == 0
        assert "ground one" in result["next_action"].lower()

    def test_deleted_joint_summary_is_reported(self, monkeypatch) -> None:
        doc, assembly, _group = _scene()
        sys.modules["FreeCAD"].ActiveDocument = doc

        result = assembly_delete_joint.run(FakeService(doc, assembly), "Assembly", "Joint007")

        assert result["deleted_joint"]["name"] == "Joint007"
        assert result["deleted_joint"]["grounded"] is False
