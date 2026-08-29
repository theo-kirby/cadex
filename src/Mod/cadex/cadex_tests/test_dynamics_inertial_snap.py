# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A coordinate that is zero by symmetry is zero, on every platform (ADR-133).

The failure this file exists for is not a physics error. It is a **digest**
error, and the chain is worth stating once because every assertion here is a
link in it:

1. ``export_mjcf`` publishes an MJCF and its sha256;
2. ``task_records`` embeds that sha256 in the task bundle;
3. the bundle is hashed whole, and *that* digest goes into a ``.cxpolicy``;
4. ``verify_policy`` refuses a policy whose recorded task digest is not the
   digest of the bundle the script just built.

So one float in the MJCF decides whether hours of GPU compute can be replayed.
Measured on this repository's own biped: `mg-legs`' pelvis centre of mass is
zero in x by symmetry, OCCT reads it as ``5.10066e-11 m`` on macOS and
``5.10087e-11 m`` on Linux, and those two numbers were the **only** difference
between the two platforms' 14 179-byte MJCF files -- which was enough to make
a policy trained on one machine unreplayable on the other.

**Why the snap is absolute.** The two readings differ in their *fifth
significant figure*, so no relative tolerance calls them equal;
``test_the_split_is_invisible_to_a_relative_tolerance`` is that stated as a
measurement rather than an argument. The reason they differ so much is
cancellation: a symmetric body's x-centroid is a difference of near-equal
sums, so a last-bit disagreement in OCCT's own per-solid readings arrives
amplified by eleven orders of magnitude.

**What this does not claim.** The snap moves centre-of-mass coordinates and
nothing else -- not mass, not the inertia tensor. A product of inertia that is
zero by symmetry has the same cancellation problem in principle, and a
nanometre is not a tolerance for kg·m². For this mechanism it does not arise:
both platforms print identical ``quat`` and ``diaginertia``. The boundary is
named here so that a future mechanism which does hit it is recognised rather
than rediscovered.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx


STEEL = 7850.0

#: The measurement, in metres, as it appears in the two MJCF files. Both are
#: `mg-legs`' pelvis ``<inertial pos>`` x-coordinate, which is zero by
#: symmetry.
PELVIS_COM_X_MACOS_M = 5.10066e-11
PELVIS_COM_X_LINUX_M = 5.10087e-11

#: The same two, in the unit ``body_inertial`` works in.
PELVIS_COM_X_MACOS_MM = PELVIS_COM_X_MACOS_M * 1000.0
PELVIS_COM_X_LINUX_MM = PELVIS_COM_X_LINUX_M * 1000.0


def _reading(centre, *, volume: float = 800_000.0) -> dict:
    """One solid, as OCCT reports it: volume, centre, COM-tensor in mm⁵.

    The tensor is a 200x100x40 box's, which makes the body physical; only the
    centre is under test.
    """

    return {
        "volume_mm3": volume,
        "center_of_mass_mm": list(centre),
        "inertia_mm5_about_com": [
            volume * (100.0**2 + 40.0**2) / 12.0, 0.0, 0.0,
            0.0, volume * (200.0**2 + 40.0**2) / 12.0, 0.0,
            0.0, 0.0, volume * (200.0**2 + 100.0**2) / 12.0,
        ],
    }


# ---------------------------------------------------------------------------
# The helper, on its own.
# ---------------------------------------------------------------------------


def test_a_coordinate_below_a_nanometre_becomes_exactly_zero() -> None:
    snapped = dyn.snap_inertial_point_mm(
        [PELVIS_COM_X_LINUX_MM, PELVIS_COM_X_MACOS_MM, 1.0e-9]
    )
    assert snapped == [0.0, 0.0, 0.0]
    # `== 0.0` is true of -0.0 too, and -0.0 is the whole bug one level down.
    assert all(math.copysign(1.0, value) > 0.0 for value in snapped)


def test_negative_symmetry_noise_does_not_become_negative_zero() -> None:
    """``to_xml`` prints ``-0`` for negative zero, which is a different file.

    So dropping the sign with the magnitude is load-bearing, not tidiness: a
    mechanism mirrored about x would otherwise put ``-0`` where its mirror
    image puts ``0`` and the two would digest differently.
    """

    snapped = dyn.snap_inertial_point_mm([-PELVIS_COM_X_LINUX_MM, -0.0, -1.0e-12])
    assert snapped == [0.0, 0.0, 0.0]
    assert [math.copysign(1.0, value) for value in snapped] == [1.0, 1.0, 1.0]


def test_a_real_coordinate_survives_bit_for_bit() -> None:
    """A snap that moved geometry would be a worse bug than the one it fixes.

    1 µm is a thousand times the tolerance and is the tightest thing anything
    here is modelled to; 30 mm is an ordinary offset.
    """

    original = [1.0e-3, -0.5, 30.123456789012345]
    assert dyn.snap_inertial_point_mm(original) == original


def test_the_boundary_is_where_the_constant_says() -> None:
    """Stated so a change to the constant fails a test rather than a digest."""

    assert dyn.INERTIAL_ZERO_TOLERANCE_MM == 1.0e-6
    tolerance = dyn.INERTIAL_ZERO_TOLERANCE_MM
    just_below = math.nextafter(tolerance, 0.0)
    assert dyn.snap_inertial_point_mm([just_below]) == [0.0]
    # The comparison is strict, so the tolerance itself is geometry.
    assert dyn.snap_inertial_point_mm([tolerance]) == [tolerance]


def test_the_split_is_invisible_to_a_relative_tolerance() -> None:
    """Why absolute. The two platform readings are not close in any relative
    sense -- they disagree from the fifth significant figure on."""

    relative = abs(PELVIS_COM_X_LINUX_MM - PELVIS_COM_X_MACOS_MM) / abs(
        PELVIS_COM_X_MACOS_MM
    )
    assert relative > 1.0e-5
    assert PELVIS_COM_X_LINUX_MM != pytest.approx(PELVIS_COM_X_MACOS_MM, rel=1.0e-9)
    # ...and absolutely, they are 2.1e-15 m apart, on a coordinate that is
    # zero. Both facts are true at once, which is the trap.
    assert abs(PELVIS_COM_X_LINUX_M - PELVIS_COM_X_MACOS_M) < 1.0e-14


# ---------------------------------------------------------------------------
# Through body_inertial, which is where the snap actually happens.
# ---------------------------------------------------------------------------


def test_the_two_platforms_publish_the_same_centre_of_mass() -> None:
    """The regression, in one assertion.

    Before ADR-133 these two ``body_inertial`` results differed, and
    everything downstream -- MJCF digest, bundle digest, policy acceptance --
    differed with them.
    """

    linux = dyn.body_inertial(
        [_reading((PELVIS_COM_X_LINUX_MM, -1.4974, 2.01431))], STEEL, context="pelvis"
    )
    macos = dyn.body_inertial(
        [_reading((PELVIS_COM_X_MACOS_MM, -1.4974, 2.01431))], STEEL, context="pelvis"
    )
    assert linux["center_of_mass_mm"] == macos["center_of_mass_mm"]
    assert linux["center_of_mass_mm"][0] == 0.0
    # The two coordinates that are *not* symmetry zeros are untouched.
    assert linux["center_of_mass_mm"][1:] == [-1.4974, 2.01431]


def test_a_mirror_pair_that_does_not_cancel_exactly_still_lands_at_zero() -> None:
    """The mechanism, rather than the symptom.

    Two solids mirrored about x whose centres disagree by one ulp -- which is
    all it takes, because OCCT reads each independently. The weighted mean is
    then a tiny non-zero instead of the zero symmetry says it is.
    """

    right = 30.0
    left = -math.nextafter(right, math.inf)
    pair = dyn.body_inertial(
        [_reading((right, 0.0, 0.0)), _reading((left, 0.0, 0.0))],
        STEEL,
        context="a mirrored pair",
    )
    assert pair["center_of_mass_mm"][0] == 0.0
    # Without the snap it would not be: the residual is real, just meaningless.
    residual = math.fsum([800_000.0 * right, 800_000.0 * left]) / 1_600_000.0
    assert residual != 0.0
    assert abs(residual) < dyn.INERTIAL_ZERO_TOLERANCE_MM


def test_a_genuinely_offset_body_keeps_its_centre_of_mass() -> None:
    """The parallel-axis case this module's own hazard 2 is about."""

    offset = dyn.body_inertial(
        [_reading((300.0, 0.0, 0.0))], STEEL, context="an offset box"
    )
    assert offset["center_of_mass_mm"][0] == 300.0
    mass = STEEL * 0.2 * 0.1 * 0.04
    assert offset["mass_kg"] == pytest.approx(mass, rel=1.0e-12)
    # The tensor is about the centre of mass, so an offset does not enter it.
    assert offset["inertia_kg_m2"][0] == pytest.approx(
        mass * (0.1**2 + 0.04**2) / 12.0, rel=1.0e-12
    )


def test_the_snap_costs_nothing_measurable_in_the_tensor() -> None:
    """The tensor is taken about the *snapped* point, and that is a choice.

    Moving the reference point by under a nanometre shifts the tensor by
    ``m·d²``. Asserted rather than argued, because "negligible" is the kind of
    word that hides a factor of a thousand.
    """

    body = dyn.body_inertial(
        [_reading((PELVIS_COM_X_LINUX_MM, 0.0, 0.0))], STEEL, context="pelvis"
    )
    mass = STEEL * 0.2 * 0.1 * 0.04
    shift = mass * (PELVIS_COM_X_LINUX_M**2)
    smallest = min(body["principal_inertia_kg_m2"])
    assert shift / smallest < 1.0e-15


# ---------------------------------------------------------------------------
# ...and out the far end, in the file that carries the digest.
# ---------------------------------------------------------------------------


def test_the_exported_mjcf_prints_a_symmetry_zero_as_zero() -> None:
    """The end of the chain: what the digest is actually taken over.

    ``to_xml`` prints about six significant figures, so a coordinate at
    5.1e-11 arrives in the file as ``5.10087e-11`` -- legible, meaningless and
    platform-specific. After the snap it is ``0``.
    """

    mujoco = pytest.importorskip("mujoco")

    noisy = fx.box_inertial(200.0, 100.0, 40.0)
    assert noisy["center_of_mass_mm"] == [0.0, 0.0, 0.0]

    components, joints, _placements = fx.build(
        [
            {"name": "base", "grounded": True, "size": (200.0, 200.0, 20.0)},
            {
                "name": "arm",
                "size": (300.0, 40.0, 20.0),
                "inertial": dyn.body_inertial(
                    [_reading((PELVIS_COM_X_LINUX_MM, -1.4974, 2.01431))],
                    STEEL,
                    context="arm",
                ),
            },
        ],
        [
            {
                "name": "hinge",
                "kind": "revolute",
                "parent": "base",
                "child": "arm",
                "parent_frame": fx.frame((0.0, 0.0, 60.0), (1.0, 0.0, 0.0), 0.0),
                "child_frame": fx.frame((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 0.0),
                "values": [0.0],
            }
        ],
    )
    built = dyn.build_model(components, joints)
    xml = dyn.export_mjcf(built)["xml"].decode("utf-8")

    assert "5.10087e-11" not in xml
    assert "e-11" not in xml
    # The two coordinates that mean something are still in the file.
    inertials = [line.strip() for line in xml.splitlines() if "<inertial" in line]
    assert any('pos="0 -0.0014974 0.00201431"' in line for line in inertials), inertials

    # And it still compiles to a model with the mass it was given.
    model = mujoco.MjModel.from_xml_string(xml)
    assert model.nbody >= 2
