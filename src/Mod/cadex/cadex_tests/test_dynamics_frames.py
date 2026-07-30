# SPDX-License-Identifier: LGPL-2.1-or-later

"""Frame algebra for the dynamics translator (docs/MUJOCO.md M2, phase 1).

Every pose in M2 is composed rather than read: a joint anchor is the
component's *solved* placement composed with the connector's
component-local frame, because ``global_frame`` is a pre-solve snapshot
(hazard 1). Composition is therefore the primitive everything else stands
on, and it is tested here against closed forms rather than against itself.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn


def _rotation_z(degrees: float, translation=(0.0, 0.0, 0.0)) -> list[float]:
    angle = math.radians(degrees)
    return dyn.matrix_from_rotation_translation(
        [
            math.cos(angle), -math.sin(angle), 0.0,
            math.sin(angle), math.cos(angle), 0.0,
            0.0, 0.0, 1.0,
        ],
        translation,
    )


def _sample_frames() -> list[list[float]]:
    """A spread of placements, none of them axis-aligned by accident."""

    frames = [list(dyn.IDENTITY_MATRIX), _rotation_z(37.0, (12.0, -3.5, 400.0))]
    for axis, angle, translation in (
        ((1.0, 0.0, 0.0), 90.0, (0.0, 0.0, 0.0)),
        ((0.3, -0.7, 0.9), 143.0, (-500.0, 25.0, 7.5)),
        ((0.0, 1.0, 0.0), 179.5, (1.0e5, 0.0, -2.0)),
    ):
        quaternion = dyn.quaternion_from_axis_angle_wxyz(axis, math.radians(angle))
        frames.append(dyn.matrix_from_quaternion_wxyz(quaternion, translation))
    return frames


def test_composition_and_inverse_are_exact_enough_to_chain() -> None:
    for frame in _sample_frames():
        product = dyn.matrix_multiply(frame, dyn.matrix_inverse(frame))
        assert product == pytest.approx(list(dyn.IDENTITY_MATRIX), abs=1.0e-9)


def test_composition_is_associative_and_ordered() -> None:
    """``matrix_multiply(a, b)`` applies ``b`` first, in ``a``'s frame."""

    first = _rotation_z(90.0)
    second = dyn.matrix_from_rotation_translation(
        [1, 0, 0, 0, 1, 0, 0, 0, 1], (10.0, 0.0, 0.0)
    )
    # Rotate the x-translation by 90° about z: it becomes +y.
    assert dyn.matrix_translation_mm(
        dyn.matrix_multiply(first, second)
    ) == pytest.approx([0.0, 10.0, 0.0], abs=1.0e-9)
    # The other order translates first, in the world frame.
    assert dyn.matrix_translation_mm(
        dyn.matrix_multiply(second, first)
    ) == pytest.approx([10.0, 0.0, 0.0], abs=1.0e-9)

    third = _sample_frames()[3]
    assert dyn.matrix_multiply(
        dyn.matrix_multiply(first, second), third
    ) == pytest.approx(
        dyn.matrix_multiply(first, dyn.matrix_multiply(second, third)), abs=1.0e-9
    )


def test_the_frame_z_axis_is_the_worker_convention() -> None:
    """Entries 2, 6 and 10 -- the same three ``_frame_z_axis`` reads."""

    frame = _sample_frames()[2]  # 90° about +X: local +Z points along -Y.
    assert dyn.matrix_z_axis(frame) == pytest.approx([0.0, -1.0, 0.0], abs=1.0e-12)
    assert dyn.matrix_z_axis(dyn.IDENTITY_MATRIX) == [0.0, 0.0, 1.0]


def test_quaternion_matrix_round_trip_survives_every_shepperd_branch() -> None:
    for frame in _sample_frames():
        quaternion = dyn.quaternion_wxyz_from_matrix(frame)
        rebuilt = dyn.matrix_from_quaternion_wxyz(
            quaternion, dyn.matrix_translation_mm(frame)
        )
        assert rebuilt == pytest.approx(list(frame), abs=1.0e-9)


def test_a_180_degree_rotation_round_trips() -> None:
    """The branch a naive trace-only conversion divides by zero on."""

    for axis in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)):
        quaternion = dyn.quaternion_from_axis_angle_wxyz(axis, math.pi)
        frame = dyn.matrix_from_quaternion_wxyz(quaternion)
        assert dyn.rotation_angle_between(
            dyn.quaternion_wxyz_from_matrix(frame), quaternion
        ) == pytest.approx(0.0, abs=1.0e-7)


def test_quaternion_order_conversions_are_inverses() -> None:
    wxyz = dyn.quaternion_from_axis_angle_wxyz((0.2, 0.3, 0.9), 1.1)
    assert dyn.quaternion_wxyz_from_xyzw(dyn.quaternion_xyzw_from_wxyz(wxyz)) == wxyz
    # The trace field is rotation_xyzw; MuJoCo's data.xquat is wxyz. Getting
    # this backwards is a mechanism that plays with the parts tumbling.
    assert dyn.quaternion_xyzw_from_wxyz([0.0, 1.0, 0.0, 0.0]) == [1.0, 0.0, 0.0, 0.0]


def test_rotation_angle_ignores_the_quaternion_hemisphere() -> None:
    quaternion = dyn.quaternion_from_axis_angle_wxyz((0.0, 0.0, 1.0), 2.0)
    flipped = [-item for item in quaternion]
    assert dyn.rotation_angle_between(quaternion, flipped) == pytest.approx(0.0, abs=1e-7)
    assert dyn.rotation_angle_between(
        [1.0, 0.0, 0.0, 0.0], quaternion
    ) == pytest.approx(2.0, abs=1.0e-9)


def test_quaternion_rotation_matches_the_matrix() -> None:
    frame = _sample_frames()[3]
    quaternion = dyn.quaternion_wxyz_from_matrix(frame)
    vector = [3.0, -4.0, 12.0]
    rotation = dyn.matrix_rotation(frame)
    expected = [
        sum(rotation[row * 3 + column] * vector[column] for column in range(3))
        for row in range(3)
    ]
    assert dyn.quaternion_rotate_wxyz(quaternion, vector) == pytest.approx(
        expected, abs=1.0e-9
    )


def test_a_mirrored_occurrence_is_refused_rather_than_approximated() -> None:
    mirrored = dyn.matrix_from_rotation_translation(
        [-1, 0, 0, 0, 1, 0, 0, 0, 1], (0.0, 0.0, 0.0)
    )
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.checked_rigid_matrix(mirrored, context="component 'arm'")
    assert excinfo.value.reason == "mirrored_occurrence"


def test_a_scaled_occurrence_is_refused() -> None:
    scaled = dyn.matrix_from_rotation_translation(
        [2, 0, 0, 0, 2, 0, 0, 0, 2], (0.0, 0.0, 0.0)
    )
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.checked_rigid_matrix(scaled, context="component 'arm'")
    assert excinfo.value.reason == "scaled_occurrence"


def test_a_real_placement_passes_the_rigidity_check() -> None:
    for frame in _sample_frames():
        assert dyn.checked_rigid_matrix(frame, context="component 'arm'") == list(frame)


def test_a_malformed_frame_is_refused_before_it_reaches_arithmetic() -> None:
    for value in ([0.0] * 15, "identity", [float("nan")] * 16, None):
        with pytest.raises(dyn.DynamicsError) as excinfo:
            dyn.checked_rigid_matrix(value, context="component 'arm'")
        assert excinfo.value.reason == "malformed_frame"
