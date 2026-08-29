# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The mount table: ``mounts(...)``, ``mount_set(...)``, ``mount(...)`` and
``part.mate`` (ADR-126).

`test_boards.py`'s subject, one table over: `CadexBoards` said where a
**wire** attaches, `CadexMounts` says where a **component** bolts. It is the
same four properties the editor depends on — canonical millimetres in the
component's own frame whatever the declaration was written in, stored rows
that *replace* the declared table, drift dropped rather than raised on, and a
viewport measurement converted exactly once — plus the two things a terminal
row does not carry: a roll, and the fastener/clearance the mating half reads.

`CadexMounts` imports nothing from FreeCAD, so all of this runs on plain
numbers and opaque component stand-ins. The kernel half — the placement and
the interference refusal — is at the bottom and skips without an engine.
"""

from __future__ import annotations

import math
import tempfile

import pytest

from CadexMounts import (
    MAX_MOUNTS,
    MOUNT_FIELDS,
    MountError,
    MountSet,
    MountsCollector,
    canonical_mount_rows,
    declared_groups,
    declared_mount_rows,
    effective_mounts,
    mate_matrix,
    mount,
    mount_set,
    prune_mount_rows,
    row_frame,
    row_from_world,
)

SKIN = "SKIN-SHAPE"
LEG = "LEG-SHAPE"


def _skin(**overrides):
    rows = overrides.pop("rows", None) or [
        mount("hip_l", origin=(-40, 30, 120), axis=(0, 1, 0), roll=(0, 0, 1),
              fastener="m3", clearance=2.0),
        mount("hip_r", origin=(-40, -30, 120), axis=(0, -1, 0), roll=(0, 0, 1)),
    ]
    return mount_set(SKIN, rows, **overrides)


def _leg(**overrides):
    rows = overrides.pop("rows", None) or [
        mount("root", origin=(0, 0, 0), axis=(0, -1, 0), roll=(0, 0, 1)),
    ]
    return mount_set(LEG, rows, **overrides)


def _table(overrides=None, placement=None):
    collector = MountsCollector(overrides, placement)
    return collector, collector({"skin": _skin(), "leg": _leg()})


def _row(component: str, name: str, **overrides):
    row = {
        "component": component,
        "name": name,
        "origin": [1.0, 2.0, 3.0],
        "axis": [0.0, 0.0, 1.0],
        "roll": [1.0, 0.0, 0.0],
    }
    row.update(overrides)
    return row


# --------------------------------------------------------------------------
# declaration
# --------------------------------------------------------------------------


def test_a_declared_mount_is_looked_up_by_name() -> None:
    _collector, table = _table()
    assert sorted(table.names) == ["leg", "skin"]
    assert isinstance(table["skin"], MountSet)
    assert sorted(table["skin"].names) == ["hip_l", "hip_r"]
    handle = table["skin"]["hip_l"]
    assert handle.name == "hip_l"
    assert handle.component == SKIN
    assert handle.row["fastener"] == "m3"
    assert handle.row["clearance"] == 2.0


def test_a_mount_is_named_not_numbered() -> None:
    _collector, table = _table()
    with pytest.raises(MountError) as caught:
        table["skin"][0]
    assert "named, not numbered" in str(caught.value)


def test_an_unknown_name_says_what_there_is() -> None:
    _collector, table = _table()
    with pytest.raises(MountError) as caught:
        table["skin"]["ankle"]
    assert caught.value.details["available"] == ["hip_l", "hip_r"]
    with pytest.raises(MountError) as caught:
        table["nothing"]
    assert caught.value.details["available"] == ["skin", "leg"]


def test_the_spec_cache_is_json_and_flat() -> None:
    """What script.json holds: no component object, no marker, no nesting."""

    import json

    collector, _table_value = _table()
    encoded = json.loads(json.dumps(collector.specs))
    assert list(encoded) == ["mounts"]
    entry = encoded["mounts"][0]
    assert entry["name"] == "skin"
    row = entry["mounts"][0]
    assert set(row) == set(MOUNT_FIELDS) - {"component"}


def test_a_metre_declaration_is_stored_in_millimetres() -> None:
    """``units=`` is declaration-time convenience and nothing more."""

    collector = MountsCollector()
    table = collector({
        "leg": mount_set(
            LEG,
            [mount("root", origin=(0.012, 0.0, 0.03), axis=(0, 0, 1),
                   roll=(1, 0, 0), clearance=0.002)],
            units="m",
        )
    })
    row = table["leg"]["root"].row
    assert row["origin"] == pytest.approx([12.0, 0.0, 30.0])
    assert row["clearance"] == pytest.approx(2.0)
    # ...and a direction is a direction in either system.
    assert row["axis"] == [0.0, 0.0, 1.0]


def test_the_roll_is_what_a_terminal_row_does_not_have() -> None:
    """An axis fixes two rotations of three. The third is the point."""

    row = mount("a", origin=(0, 0, 0), axis=(0, 0, 1), roll=(1, 0, 0))
    assert row["roll"] == [1.0, 0.0, 0.0]
    # A roll that is merely near-perpendicular is projected, not refused:
    # a caller may hand over "up" without doing the arithmetic first.
    slanted = mount("b", origin=(0, 0, 0), axis=(0, 0, 1), roll=(1, 0, 0.3))
    assert slanted["roll"] == pytest.approx([1.0, 0.0, 0.0])


def test_a_roll_along_the_axis_is_refused() -> None:
    with pytest.raises(MountError) as caught:
        mount("a", origin=(0, 0, 0), axis=(0, 0, 1), roll=(0, 0, 2))
    assert "fixes no rotation" in str(caught.value)


def test_a_fastener_is_a_designation_not_a_sentence() -> None:
    assert mount("a", origin=(0, 0, 0), axis=(0, 0, 1), roll=(1, 0, 0),
                 fastener="m4x0.7")["fastener"] == "m4x0.7"
    assert mount("a", origin=(0, 0, 0), axis=(0, 0, 1), roll=(1, 0, 0),
                 fastener=None)["fastener"] is None
    with pytest.raises(MountError):
        mount("a", origin=(0, 0, 0), axis=(0, 0, 1), roll=(1, 0, 0),
              fastener="an m3 cap screw, 8 mm long")


def test_the_table_is_immutable_and_callable_once() -> None:
    collector, table = _table()
    with pytest.raises(MountError):
        table.anything = 1
    with pytest.raises(MountError) as caught:
        collector({"skin": _skin()})
    assert "once" in str(caught.value)


def test_two_mounts_on_one_component_may_not_share_a_name() -> None:
    with pytest.raises(MountError) as caught:
        mount_set(SKIN, [
            mount("hip", origin=(0, 0, 0), axis=(0, 0, 1), roll=(1, 0, 0)),
            mount("hip", origin=(1, 0, 0), axis=(0, 0, 1), roll=(1, 0, 0)),
        ])
    assert "looked up by name" in str(caught.value)


def test_a_row_must_be_declared_with_mount() -> None:
    with pytest.raises(MountError) as caught:
        mount_set(SKIN, [{"name": "hip", "origin": [0, 0, 0]}])
    assert "not a mount(...)" in str(caught.value)


def test_a_group_must_be_declared_with_mount_set() -> None:
    with pytest.raises(MountError) as caught:
        MountsCollector()({"skin": {"component": SKIN}})
    assert "mount_set" in str(caught.value)


def test_the_table_is_bounded() -> None:
    rows = [
        mount(f"m{index:02d}", origin=(index, 0, 0), axis=(0, 0, 1),
              roll=(1, 0, 0))
        for index in range(MAX_MOUNTS + 1)
    ]
    with pytest.raises(MountError) as caught:
        mount_set(SKIN, rows)
    assert str(MAX_MOUNTS) in str(caught.value)


def test_names_are_lower_snake_case_on_both_halves() -> None:
    with pytest.raises(MountError):
        mount("Hip Left", origin=(0, 0, 0), axis=(0, 0, 1), roll=(1, 0, 0))
    with pytest.raises(MountError):
        MountsCollector()({"Skin": _skin()})


# --------------------------------------------------------------------------
# the stored half
# --------------------------------------------------------------------------


def test_a_stored_row_may_not_smuggle_an_unknown_column() -> None:
    with pytest.raises(MountError) as caught:
        canonical_mount_rows([_row("skin", "hip_l", torque=3.0)], what="v")
    assert "unrecognised keys" in str(caught.value)


def test_a_world_frame_row_is_only_admitted_where_it_is_expected() -> None:
    row = _row("skin", "hip_l", frame="world")
    assert canonical_mount_rows([row], what="v", allow_world=True)[0]["frame"] == "world"
    with pytest.raises(MountError):
        canonical_mount_rows([row], what="v")


def test_no_stored_rows_means_the_declared_table_stands() -> None:
    collector, _value = _table()
    assert effective_mounts(collector.specs, []) == declared_mount_rows(
        collector.specs)
    assert len(declared_mount_rows(collector.specs)) == 3


def test_stored_rows_replace_the_declared_table_wholesale() -> None:
    """A full list, not a patch — which is what lets the editor delete one."""

    collector, _value = _table()
    stored = [_row("skin", "hip_l"), _row("skin", "extra")]
    effective = effective_mounts(collector.specs, stored)
    assert [row["name"] for row in effective] == ["hip_l", "extra"]
    assert not [row for row in effective if row["component"] == "leg"]


def test_a_row_naming_a_dropped_component_is_pruned_not_raised_on() -> None:
    """ADR-120's drift rule. Raising here would wedge the editor forever the
    moment the AI renamed a component."""

    collector, _value = _table()
    stored = [_row("skin", "hip_l"), _row("gone", "orphan")]
    kept = prune_mount_rows(canonical_mount_rows(stored, what="v"),
                            collector.specs)
    assert [row["component"] for row in kept] == ["skin"]
    # ...and through the front door too.
    assert [row["name"] for row in effective_mounts(collector.specs, stored)] == [
        "hip_l"
    ]


def test_an_override_is_still_validated() -> None:
    collector, _value = _table()
    with pytest.raises(MountError):
        effective_mounts(collector.specs, [_row("skin", "hip_l", axis=[0, 0, 0])])


def test_the_collector_applies_the_overrides_to_the_geometry() -> None:
    """What the script sees is what the editor stored, not what it declared."""

    moved = _row("skin", "hip_l", origin=[1.0, 2.0, 3.0])
    collector = MountsCollector([moved])
    table = collector({"skin": _skin(), "leg": _leg()})
    assert table["skin"]["hip_l"].row["origin"] == [1.0, 2.0, 3.0]
    # The declared hip_r is gone: a stored list replaces, it does not merge.
    assert table["skin"].names == ("hip_l",)


def test_declared_groups_reads_the_cache_back() -> None:
    collector, _value = _table()
    groups = declared_groups(collector.specs)
    assert sorted(groups) == ["leg", "skin"]
    assert [row["name"] for row in groups["skin"]["mounts"]] == ["hip_l", "hip_r"]


# --------------------------------------------------------------------------
# the world-frame round trip
# --------------------------------------------------------------------------


def test_a_world_row_lands_in_the_components_own_frame() -> None:
    """A viewport pick is measured in the only frame a click has."""

    placement = (
        1.0, 0.0, 0.0, 5.0,
        0.0, 1.0, 0.0, 7.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    )
    row = _row("skin", "picked", origin=[15.0, 7.0, 2.0], frame="world")
    carried = row_from_world(row, placement)
    assert carried["origin"] == pytest.approx([10.0, 0.0, 2.0])
    assert "frame" not in carried


def test_a_world_row_carries_its_roll_too() -> None:
    """The one thing a board row does not have to carry, and the reason a
    mount frame stays a frame across the conversion."""

    # A quarter turn about +Z: world +X came from the component's +Y.
    placement = (
        0.0, -1.0, 0.0, 0.0,
        1.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    )
    row = _row("skin", "picked", origin=[0.0, 0.0, 0.0],
               axis=[0.0, 0.0, 1.0], roll=[1.0, 0.0, 0.0], frame="world")
    carried = row_from_world(row, placement)
    assert carried["axis"] == pytest.approx([0.0, 0.0, 1.0])
    assert carried["roll"] == pytest.approx([0.0, -1.0, 0.0])


def test_the_collector_converts_a_world_row_exactly_once() -> None:
    placement = (
        1.0, 0.0, 0.0, 5.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    )
    picked = _row("skin", "hip_l", origin=[15.0, 0.0, 0.0], frame="world")
    collector = MountsCollector([picked], lambda component: placement)
    table = collector({"skin": _skin(), "leg": _leg()})
    assert table["skin"]["hip_l"].row["origin"] == pytest.approx([10.0, 0.0, 0.0])
    # ...and it is reported, so the store can write the converted row back.
    assert len(collector.converted) == 1
    assert collector.converted[0]["origin"] == pytest.approx([10.0, 0.0, 0.0])
    assert "frame" not in collector.converted[0]


def test_a_world_row_with_no_placement_to_invert_says_so() -> None:
    collector = MountsCollector([_row("skin", "hip_l", frame="world")], None)
    with pytest.raises(MountError) as caught:
        collector({"skin": _skin()})
    assert "world coordinates" in str(caught.value)


# --------------------------------------------------------------------------
# the mate
# --------------------------------------------------------------------------


def _apply(matrix, point):
    return [
        sum(matrix[row * 4 + column] * point[column] for column in range(3))
        + matrix[row * 4 + 3]
        for row in range(3)
    ]


def _direction(matrix, vector):
    return [
        sum(matrix[row * 4 + column] * vector[column] for column in range(3))
        for row in range(3)
    ]


def test_a_frame_is_orthonormal_and_right_handed() -> None:
    origin, x_axis, y_axis, z_axis = row_frame(
        _row("skin", "hip", axis=[0, 0, 1], roll=[1, 0, 0.4]))
    for vector in (x_axis, y_axis, z_axis):
        assert math.sqrt(sum(v * v for v in vector)) == pytest.approx(1.0)
    assert sum(a * b for a, b in zip(x_axis, z_axis)) == pytest.approx(0.0)
    assert sum(a * b for a, b in zip(x_axis, y_axis)) == pytest.approx(0.0)
    # x cross y == z, which is what "right-handed" means in numbers.
    cross = [
        x_axis[1] * y_axis[2] - x_axis[2] * y_axis[1],
        x_axis[2] * y_axis[0] - x_axis[0] * y_axis[2],
        x_axis[0] * y_axis[1] - x_axis[1] * y_axis[0],
    ]
    assert cross == pytest.approx(z_axis)
    assert origin == [1.0, 2.0, 3.0]


def test_mating_brings_the_origins_together_and_opposes_the_axes() -> None:
    source = _row("leg", "root", origin=[0, 0, 0], axis=[0, 0, 1], roll=[1, 0, 0])
    target = _row("skin", "hip", origin=[10, 20, 30], axis=[1, 0, 0],
                  roll=[0, 0, 1])
    matrix = mate_matrix(source, target)

    assert _apply(matrix, [0, 0, 0]) == pytest.approx([10.0, 20.0, 30.0])
    # The source's own axis ends up opposing the target's: face to face.
    assert _direction(matrix, [0, 0, 1]) == pytest.approx([-1.0, 0.0, 0.0])
    # ...and the rolls agree, which is the whole reason a mount has one.
    assert _direction(matrix, [1, 0, 0]) == pytest.approx([0.0, 0.0, 1.0])


def test_a_mate_is_a_rigid_motion_not_a_mirror() -> None:
    """Reversing one axis alone would turn a left bracket into a right one."""

    source = _row("leg", "root", origin=[3, 1, 4], axis=[0, 1, 0], roll=[0, 0, 1])
    target = _row("skin", "hip", origin=[-2, 5, 9], axis=[0.6, 0.8, 0],
                  roll=[0, 0, 1])
    matrix = mate_matrix(source, target)
    columns = [
        [matrix[row * 4 + column] for row in range(3)] for column in range(3)
    ]
    determinant = (
        columns[0][0] * (columns[1][1] * columns[2][2] - columns[1][2] * columns[2][1])
        - columns[0][1] * (columns[1][0] * columns[2][2] - columns[1][2] * columns[2][0])
        + columns[0][2] * (columns[1][0] * columns[2][1] - columns[1][1] * columns[2][0])
    )
    assert determinant == pytest.approx(1.0)
    # Distances survive it.
    left = _apply(matrix, [3, 1, 4])
    right = _apply(matrix, [3, 1, 14])
    assert math.dist(left, right) == pytest.approx(10.0)


def test_flip_turns_the_part_about_the_mating_axis() -> None:
    source = _row("leg", "root", origin=[0, 0, 0], axis=[0, 0, 1], roll=[1, 0, 0])
    target = _row("skin", "hip", origin=[0, 0, 0], axis=[0, 0, -1], roll=[1, 0, 0])
    plain = mate_matrix(source, target)
    flipped = mate_matrix(source, target, flip=True)
    assert _direction(plain, [1, 0, 0]) == pytest.approx([1.0, 0.0, 0.0])
    assert _direction(flipped, [1, 0, 0]) == pytest.approx([-1.0, 0.0, 0.0])
    # Both still put the origins together.
    assert _apply(plain, [0, 0, 0]) == pytest.approx([0.0, 0.0, 0.0])
    assert _apply(flipped, [0, 0, 0]) == pytest.approx([0.0, 0.0, 0.0])


def test_offset_moves_along_the_targets_axis() -> None:
    source = _row("leg", "root", origin=[0, 0, 0], axis=[0, 0, 1], roll=[1, 0, 0])
    target = _row("skin", "hip", origin=[0, 0, 0], axis=[0, 1, 0], roll=[0, 0, 1])
    matrix = mate_matrix(source, target, offset=5.0)
    assert _apply(matrix, [0, 0, 0]) == pytest.approx([0.0, 5.0, 0.0])


def test_mating_a_mount_to_itself_is_the_identity_turned_around() -> None:
    """A sanity anchor: the same frame, mated to itself, is a half turn."""

    row = _row("skin", "hip", origin=[0, 0, 0], axis=[0, 0, 1], roll=[1, 0, 0])
    matrix = mate_matrix(row, row)
    assert _direction(matrix, [0, 0, 1]) == pytest.approx([0.0, 0.0, -1.0])
    assert _direction(matrix, [1, 0, 0]) == pytest.approx([1.0, 0.0, 0.0])


# --------------------------------------------------------------------------
# against a live kernel
# --------------------------------------------------------------------------

MATE_SOURCE = """
skin = part.box(60, 40, 20, origin=[0, 0, 0], label="skin")
peg = part.cylinder(4, 25, origin=[0, 0, 0], label="peg")

m = mounts({
    "skin": mount_set(skin, [
        mount("socket", origin=(30, 20, 20), axis=(0, 0, 1), roll=(1, 0, 0),
              fastener="m4", clearance=1.0),
    ]),
    "peg": mount_set(peg, [
        mount("foot", origin=(0, 0, 0), axis=(0, 0, -1), roll=(1, 0, 0)),
    ]),
})

placed = part.mate(peg, m["peg"]["foot"], m["skin"]["socket"], label="placed")
result = {"skin": skin, "placed": placed}
"""

#: The same model with the peg seated 5 mm INTO the skin: an interference,
#: and the number is what the refusal has to say.
CLASH_SOURCE = MATE_SOURCE.replace(
    'm["skin"]["socket"], label="placed")',
    'm["skin"]["socket"], offset=-5.0, label="placed")',
)


def _live():
    from test_cadexd_lifecycle import FREECADCMD

    return FREECADCMD is not None


@pytest.mark.skipif(not _live(), reason="No FreeCADCmd binary available.")
def test_a_mate_places_the_part_and_refuses_an_overlap() -> None:
    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()
        client.request(
            "open_project", {"project_root": tempfile.mkdtemp(prefix="cadexd-mate-")}
        )
        written = client.request(
            "write_script", {"source": MATE_SOURCE, "expected_revision": ""}
        )
        assert written["ok"] is True, written

        # The peg's foot sits on the skin's top face at (30, 20, 20), and the
        # peg stands up out of it: mating opposed the two axes.
        probe = client.request(
            "resolve_pin",
            {"output": "placed",
             "selection": {"element_type": "face", "expected_count": 0}},
        )
        faces = ((probe.get("observed") or {}).get("available")) or []
        centres = [face["center_mm"] for face in faces if face["center_mm"]]
        assert centres, faces
        assert min(centre[2] for centre in centres) == pytest.approx(20.0, abs=1e-6)
        assert max(centre[2] for centre in centres) == pytest.approx(45.0, abs=1e-6)
        assert all(
            abs(centre[0] - 30.0) < 5.0 and abs(centre[1] - 20.0) < 5.0
            for centre in centres
        )

        client.request(
            "open_project", {"project_root": tempfile.mkdtemp(prefix="cadexd-clash-")}
        )
        refused = client.request(
            "write_script", {"source": CLASH_SOURCE, "expected_revision": ""}
        )
        assert refused["ok"] is False, refused
        message = str(refused.get("error") or "")
        assert "overlap" in message, message
        # pi * 4^2 * 5 = 251.3 mm3 of peg inside the skin, and the refusal
        # says the number rather than showing a picture.
        assert "251" in message, message
        observed = (refused.get("observed") or {}).get("details", {}).get("observed")
        assert observed["interference_mm3"] == pytest.approx(
            math.pi * 16.0 * 5.0, rel=1e-3)
        assert observed["target_mount"] == "socket"
        assert observed["clearance_mm"] == 1.0
    finally:
        _stop(client)
