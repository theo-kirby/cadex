# SPDX-License-Identifier: LGPL-2.1-or-later

"""Spanning-tree extraction (docs/MUJOCO.md M2, phase 3).

Our assembly graph is a constraint graph and may contain loops; MuJoCo is a
kinematic tree plus equality constraints. Picking the tree -- and deciding
which joints become closures -- is the single hardest piece of M2, and it is
pure graph algebra: no mujoco, no FreeCAD, no geometry beyond the connector
frames being well formed.

What this file is really guarding is *determinism*. ``open_project``
re-executes the accepted script and asserts digest equality, so a tree that
depends on dict iteration order is a project that breaks on reopening rather
than a model that is merely odd. ``component_outputs`` and ``joint_outputs``
in the worker are ``id()``-keyed, and ``id()`` varies per run, so every
ordering here has to be explicit and total.
"""

from __future__ import annotations

import pytest

import CadexDynamics as dyn


IDENTITY = list(dyn.IDENTITY_MATRIX)


def _component(name: str, *, grounded: bool = False, flexible: bool = False) -> dict:
    return {"name": name, "grounded": grounded, "flexible": flexible}


def _joint(
    name: str,
    kind: str,
    first: str,
    second: str,
    *,
    suppressed: bool = False,
    first_frame=None,
    second_frame=None,
) -> dict:
    return {
        "name": name,
        "kind": kind,
        "suppressed": suppressed,
        "connectors": [
            {"component": first, "local_matrix": list(first_frame or IDENTITY)},
            {"component": second, "local_matrix": list(second_frame or IDENTITY)},
        ],
    }


def _chain() -> tuple[list[dict], list[dict]]:
    """base -> arm -> forearm -> hand, grounded at the base."""

    components = [
        _component("base", grounded=True),
        _component("arm"),
        _component("forearm"),
        _component("hand"),
    ]
    joints = [
        _joint("shoulder", "revolute", "base", "arm"),
        _joint("elbow", "revolute", "arm", "forearm"),
        _joint("wrist", "ball", "forearm", "hand"),
    ]
    return components, joints


def test_a_chain_becomes_a_chain() -> None:
    tree = dyn.extract_tree(*_chain())
    assert [body["name"] for body in tree["bodies"]] == [
        "base",
        "arm",
        "forearm",
        "hand",
    ]
    assert [body["parent"] for body in tree["bodies"]] == [
        None,
        "base",
        "arm",
        "forearm",
    ]
    assert [body["depth"] for body in tree["bodies"]] == [0, 1, 2, 3]
    assert [body["mujoco_joints"] for body in tree["bodies"]] == [
        [],
        ["hinge"],
        ["hinge"],
        ["ball"],
    ]
    assert tree["closures"] == []
    assert tree["maximum_depth"] == 3


def test_the_parent_and_child_connector_frames_are_kept_apart() -> None:
    """Which frame belongs to which side is the whole model, twice over."""

    parent_frame = dyn.matrix_from_rotation_translation(
        [1, 0, 0, 0, 1, 0, 0, 0, 1], (11.0, 0.0, 0.0)
    )
    child_frame = dyn.matrix_from_rotation_translation(
        [1, 0, 0, 0, 1, 0, 0, 0, 1], (0.0, 22.0, 0.0)
    )
    components = [_component("base", grounded=True), _component("arm")]
    # Declared with the *child* first, so a translator that trusted the
    # connector order rather than the tree direction would swap them.
    joints = [
        _joint(
            "hinge",
            "revolute",
            "arm",
            "base",
            first_frame=child_frame,
            second_frame=parent_frame,
        )
    ]
    tree = dyn.extract_tree(components, joints)
    arm = tree["bodies"][1]
    assert arm["parent"] == "base"
    assert dyn.matrix_translation_mm(arm["parent_local_matrix"]) == [11.0, 0.0, 0.0]
    assert dyn.matrix_translation_mm(arm["child_local_matrix"]) == [0.0, 22.0, 0.0]


def test_breadth_first_keeps_the_tree_shallow() -> None:
    """Depth is what costs: it is the chain pose error accumulates along."""

    components = [_component("hub", grounded=True)] + [
        _component(f"spoke{index}") for index in range(4)
    ]
    joints = [
        _joint(f"pin{index}", "revolute", "hub", f"spoke{index}") for index in range(4)
    ]
    tree = dyn.extract_tree(components, joints)
    assert tree["maximum_depth"] == 1
    assert all(body["parent"] == "hub" for body in tree["bodies"][1:])


def test_the_tree_is_the_same_on_every_run() -> None:
    """No set iteration, no id() ordering, no dict-insertion luck."""

    components, joints = _chain()
    components.append(_component("shroud"))
    joints.append(_joint("clip", "fixed", "arm", "shroud"))
    joints.append(_joint("loop", "revolute", "hand", "shroud"))
    first = dyn.extract_tree(components, joints)
    for _repeat in range(5):
        again = dyn.extract_tree(components, joints)
        assert [body["name"] for body in again["bodies"]] == [
            body["name"] for body in first["bodies"]
        ]
        assert [body["parent"] for body in again["bodies"]] == [
            body["parent"] for body in first["bodies"]
        ]
        assert [item["joint"] for item in again["closures"]] == [
            item["joint"] for item in first["closures"]
        ]


def test_a_loop_closes_on_the_last_joint_that_reaches_it() -> None:
    """A four-bar: three tree edges and one connect closure."""

    components = [
        _component("ground", grounded=True),
        _component("crank"),
        _component("coupler"),
        _component("rocker"),
    ]
    joints = [
        _joint("a", "revolute", "ground", "crank"),
        _joint("b", "revolute", "crank", "coupler"),
        _joint("c", "revolute", "coupler", "rocker"),
        _joint("d", "revolute", "rocker", "ground"),
    ]
    tree = dyn.extract_tree(components, joints)
    assert tree["tree_joint_count"] == 3
    # Breadth-first, so ground reaches both the crank and the rocker
    # directly and the coupler hangs off the crank: the closure is 'c', not
    # the last joint written. The tree is two deep rather than three, which
    # is the point of preferring breadth.
    assert [item["joint"] for item in tree["closures"]] == ["c"]
    assert tree["maximum_depth"] == 2
    closure = tree["closures"][0]
    assert closure["closure_kind"] == "connect"
    assert closure["constrained_dof"] == 3
    # The evidence says what a connect lets go, rather than hiding it.
    assert "planar" in closure["note"]


def test_a_fixed_joint_closes_a_loop_as_a_weld() -> None:
    components = [
        _component("ground", grounded=True),
        _component("left"),
        _component("right"),
    ]
    joints = [
        _joint("a", "revolute", "ground", "left"),
        _joint("b", "revolute", "ground", "right"),
        _joint("bridge", "fixed", "left", "right"),
    ]
    tree = dyn.extract_tree(components, joints)
    assert [item["closure_kind"] for item in tree["closures"]] == ["weld"]
    assert tree["closures"][0]["constrained_dof"] == 6


def test_a_fixed_tree_edge_attaches_a_body_with_no_joint() -> None:
    components = [_component("base", grounded=True), _component("bracket")]
    tree = dyn.extract_tree(components, [_joint("weld", "fixed", "base", "bracket")])
    assert tree["bodies"][1]["mujoco_joints"] == []
    assert tree["bodies"][1]["parent"] == "base"
    assert tree["closures"] == []


def test_a_sliding_loop_closure_is_refused_with_the_reorder_to_make() -> None:
    """A tendon is real design work; M3's, not M2's."""

    components = [
        _component("ground", grounded=True),
        _component("crank"),
        _component("slide"),
    ]
    joints = [
        _joint("a", "revolute", "ground", "crank"),
        _joint("b", "revolute", "ground", "slide"),
        _joint("c", "slider", "crank", "slide"),
    ]
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.extract_tree(components, joints)
    assert excinfo.value.reason == "unclosable_loop_joint"
    # The advice names the joints that did reach both components, because
    # "reorder your joints" is not actionable when breadth-first search
    # reached both of them more directly than this joint ever could.
    assert excinfo.value.observed["reached_by"] == ["a", "b"]
    assert "'a'" in excinfo.value.correction and "'b'" in excinfo.value.correction


def test_two_joints_on_one_pair_take_the_earlier_one_into_the_tree() -> None:
    """The case where reordering genuinely is the fix, so the advice is true."""

    components = [_component("ground", grounded=True), _component("carriage")]
    revolute = _joint("spin", "revolute", "ground", "carriage")
    slider = _joint("travel", "slider", "ground", "carriage")
    with pytest.raises(dyn.DynamicsError):
        dyn.extract_tree(components, [revolute, slider])
    tree = dyn.extract_tree(components, [slider, revolute])
    assert tree["bodies"][1]["mujoco_joints"] == ["slide"]
    assert [item["joint"] for item in tree["closures"]] == ["spin"]


def test_a_cylindrical_loop_closure_is_refused_too() -> None:
    components = [
        _component("ground", grounded=True),
        _component("crank"),
        _component("barrel"),
    ]
    joints = [
        _joint("a", "revolute", "ground", "crank"),
        _joint("b", "revolute", "ground", "barrel"),
        _joint("c", "cylindrical", "crank", "barrel"),
    ]
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.extract_tree(components, joints)
    assert excinfo.value.reason == "unclosable_loop_joint"


@pytest.mark.parametrize("kind", ["distance", "parallel", "perpendicular", "angle"])
def test_every_placement_only_joint_is_refused_by_name(kind: str) -> None:
    components = [_component("base", grounded=True), _component("arm")]
    joints = [_joint("shoulder", "revolute", "base", "arm"), _joint("hold", kind, "base", "arm")]
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.extract_tree(components, joints)
    assert excinfo.value.reason == "placement_only_joint"
    assert "'hold'" in str(excinfo.value) and kind in str(excinfo.value)


def test_a_suppressed_joint_is_not_an_edge_at_all() -> None:
    """FreeCAD's solver ignored it, so the tree may not lean on it."""

    components = [_component("base", grounded=True), _component("arm")]
    joints = [_joint("shoulder", "revolute", "base", "arm", suppressed=True)]
    tree = dyn.extract_tree(components, joints)
    assert tree["bodies"][1]["attachment"] == "free"
    assert tree["closures"] == []
    # ...including the placement-only kinds, which are refused only when live.
    suppressed_angle = dyn.extract_tree(
        components,
        [
            _joint("shoulder", "revolute", "base", "arm"),
            _joint("hold", "angle", "base", "arm", suppressed=True),
        ],
    )
    assert suppressed_angle["bodies"][1]["attachment"] == "tree"


def test_a_component_no_joint_reaches_falls() -> None:
    components = [_component("base", grounded=True), _component("dropped")]
    tree = dyn.extract_tree(components, [])
    assert tree["bodies"][1]["attachment"] == "free"
    assert tree["bodies"][1]["mujoco_joints"] == ["free"]


def test_an_island_hangs_off_one_free_body_rather_than_several() -> None:
    components = [
        _component("base", grounded=True),
        _component("floater"),
        _component("passenger"),
    ]
    joints = [_joint("link", "revolute", "floater", "passenger")]
    tree = dyn.extract_tree(components, joints)
    assert [body["attachment"] for body in tree["bodies"]] == [
        "grounded",
        "free",
        "tree",
    ]
    assert tree["bodies"][2]["parent"] == "floater"


def test_a_second_grounded_component_stays_grounded() -> None:
    """A grounded body may never become another body's child.

    FreeCAD fixes it to the world; hanging it off a moving parent would give
    it degrees of freedom the solve says it does not have.
    """

    components = [
        _component("bed", grounded=True),
        _component("column", grounded=True),
        _component("head"),
    ]
    joints = [
        _joint("tie", "fixed", "bed", "column"),
        _joint("lift", "slider", "column", "head"),
    ]
    tree = dyn.extract_tree(components, joints)
    assert [body["attachment"] for body in tree["bodies"]] == [
        "grounded",
        "grounded",
        "tree",
    ]
    assert tree["bodies"][2]["parent"] == "column"
    # The joint between two grounded components is not a closure: it is
    # already satisfied, permanently, and adding a constraint row for it
    # would only give the solver something to work on.
    assert tree["closures"] == []
    assert [item["joint"] for item in tree["static_joints"]] == ["tie"]


def test_an_ungrounded_assembly_is_refused() -> None:
    components = [_component("arm"), _component("forearm")]
    joints = [_joint("elbow", "revolute", "arm", "forearm")]
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.extract_tree(components, joints)
    assert excinfo.value.reason == "no_grounded_component"


def test_a_flexible_component_is_refused_rather_than_assumed_rigid() -> None:
    """One component is one body, asserted rather than hoped for."""

    components = [_component("base", grounded=True), _component("gearbox", flexible=True)]
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.extract_tree(components, [])
    assert excinfo.value.reason == "flexible_component"


def test_gears_and_belts_are_never_tree_edges() -> None:
    """They relate two hinges other joints provide; they attach nothing."""

    components = [
        _component("case", grounded=True),
        _component("pinion"),
        _component("wheel"),
    ]
    joints = [
        _joint("a", "revolute", "case", "pinion"),
        _joint("b", "revolute", "case", "wheel"),
        _joint("mesh", "gears", "pinion", "wheel"),
    ]
    tree = dyn.extract_tree(components, joints)
    assert tree["tree_joint_count"] == 2
    assert tree["closures"] == []
    assert [item["name"] for item in tree["couplings"]] == ["mesh"]
    # ...and a gear pair alone leaves both wheels unattached rather than
    # quietly welding them together.
    alone = dyn.extract_tree(components, [joints[2]])
    assert [body["attachment"] for body in alone["bodies"]] == [
        "grounded",
        "free",
        "free",
    ]


def test_a_screw_attaches_nothing_and_only_couples() -> None:
    """FreeCAD says so itself, and M2's plan had it one joint too generous.

    ``AssemblyObject::isJointTypeConnecting`` returns false for screw,
    rack-and-pinion, gears and belt: its own solver will not use them to
    locate a part. A screw constrains the twist between two components a
    slider and a revolute have already placed.
    """

    components = [
        _component("body", grounded=True),
        _component("nut"),
        _component("shaft"),
    ]
    joints = [
        _joint("guide", "slider", "body", "nut"),
        _joint("spin", "revolute", "body", "shaft"),
        _joint("thread", "screw", "nut", "shaft"),
    ]
    tree = dyn.extract_tree(components, joints)
    assert tree["bodies"][1]["mujoco_joints"] == ["slide"]
    assert tree["bodies"][2]["mujoco_joints"] == ["hinge"]
    assert tree["tree_joint_count"] == 2
    assert tree["closures"] == []
    assert [item["name"] for item in tree["couplings"]] == ["thread"]


def test_a_cylindrical_tree_edge_is_a_slide_and_a_hinge() -> None:
    components = [_component("base", grounded=True), _component("piston")]
    tree = dyn.extract_tree(
        components, [_joint("bore", "cylindrical", "base", "piston")]
    )
    assert tree["bodies"][1]["mujoco_joints"] == ["slide", "hinge"]


def test_a_joint_naming_an_absent_component_is_refused() -> None:
    components = [_component("base", grounded=True)]
    joints = [_joint("hinge", "revolute", "base", "ghost")]
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.extract_tree(components, joints)
    assert excinfo.value.reason == "malformed_graph"


def test_a_joint_connecting_a_component_to_itself_is_refused() -> None:
    components = [_component("base", grounded=True)]
    joints = [_joint("hinge", "revolute", "base", "base")]
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.extract_tree(components, joints)
    assert excinfo.value.reason == "malformed_graph"


def test_every_native_joint_type_is_in_the_table() -> None:
    """The table and the API's vocabulary may not drift apart."""

    from cadex_assembly_api import _JOINT_TYPES

    assert set(dyn.JOINT_TABLE) == set(_JOINT_TYPES)
