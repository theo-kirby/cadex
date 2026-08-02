# SPDX-License-Identifier: LGPL-2.1-or-later

"""The units boundary, written before the feature (docs/MUJOCO.md §3.2).

FreeCAD is millimetres and kilograms-per-cubic-metre; MuJoCo integrates in
metres and kilograms and every default it ships -- gravity, contact
stiffness, solver reference values -- assumes SI. Get this wrong and a part
falls at 9810 mm/s² through the floor while looking entirely plausible on
screen, which is the highest-probability silent failure in the whole plan.

So the conversion is *one* boundary: :mod:`CadexDynamics` does every
arithmetic operation including every unit conversion, and the worker does
every FreeCAD read and nothing else. :func:`test_no_conversion_arithmetic_
outside_the_pure_module` is what keeps that true -- the factors 1000, 1e-9
and 1e-15 may be multiplied nowhere else in the assembly stack.

ADR-075 says the units boundary "gets a test before it gets a feature".
This file is that promise honoured literally: it was committed failing on
import and the module was written to make it pass.
"""

from __future__ import annotations

import math
from pathlib import Path
import re

import pytest

import CadexDynamics

MODULE_DIR = Path(__file__).resolve().parent.parent


def test_length_conversion_is_exactly_one_thousand() -> None:
    assert CadexDynamics.MM_PER_METRE == 1000.0
    assert CadexDynamics.length_m(1234.5) == 1.2345
    assert CadexDynamics.length_mm(1.2345) == 1234.5
    for value in (0.0, -37.5, 1.0e6):
        assert CadexDynamics.length_mm(CadexDynamics.length_m(value)) == pytest.approx(
            value, abs=1.0e-12
        )


def test_a_vector_of_millimetres_converts_componentwise() -> None:
    assert CadexDynamics.vector_m([10.0, -20.0, 0.5]) == [0.01, -0.02, 0.0005]
    assert CadexDynamics.vector_mm([0.01, -0.02, 0.0005]) == pytest.approx(
        [10.0, -20.0, 0.5]
    )


def test_mass_is_density_times_volume_in_si() -> None:
    """A 100 mm steel cube is 7.85 kg, and nothing else."""

    assert CadexDynamics.mass_kg(7850.0, 100.0**3) == pytest.approx(7.85, rel=1.0e-12)
    # aluminium, a 10 mm cube: 2700 * 1e-6 m³
    assert CadexDynamics.mass_kg(2700.0, 1000.0) == pytest.approx(2.7e-3, rel=1.0e-12)
    assert CadexDynamics.mass_kg(7850.0, 0.0) == 0.0


def test_inertia_scales_by_the_fifth_power_of_the_length_unit() -> None:
    """``MatrixOfInertia`` is mm⁵ at unit density; kg·m² is ρ · J · 1e-15.

    The exponent is the whole point: an inertia tensor carries mass times
    length squared, so converting mm to m divides by 1000³ for the volume
    inside the density and by 1000² for the moment arm.
    """

    tensor_mm5 = [2.0e12, 0.0, 0.0, 0.0, 3.0e12, 0.0, 0.0, 0.0, 4.0e12]
    result = CadexDynamics.inertia_kg_m2(7850.0, tensor_mm5)
    assert result == pytest.approx(
        [7850.0 * value * 1.0e-15 for value in tensor_mm5], rel=1.0e-12
    )
    # A solid 100 mm steel cube: I = m·a²/6 = 7.85 · 0.01 / 6.
    side = 100.0
    volume = side**3
    j_mm5 = volume * (side * side + side * side) / 12.0
    ixx = CadexDynamics.inertia_kg_m2(7850.0, [j_mm5, 0, 0, 0, j_mm5, 0, 0, 0, j_mm5])[0]
    assert ixx == pytest.approx(7.85 * 0.1 * 0.1 / 6.0, rel=1.0e-12)


def test_gravity_is_metres_per_second_squared() -> None:
    """The number a MuJoCo model must see, not the millimetre one."""

    gravity = CadexDynamics.DEFAULT_GRAVITY_M_S2
    assert gravity[0] == 0.0 and gravity[1] == 0.0
    assert -9.82 < gravity[2] < -9.80
    assert abs(gravity[2]) < 100.0, (
        "gravity in mm/s² would be 9810 and would look entirely plausible "
        "on screen while being a thousand times wrong."
    )


def test_density_bounds_name_their_anchors() -> None:
    """Density is required and never defaulted; the refusal has to teach."""

    assert CadexDynamics.MINIMUM_DENSITY_KG_M3 == 0.0
    assert CadexDynamics.MAXIMUM_DENSITY_KG_M3 == 30000.0
    with pytest.raises(CadexDynamics.DynamicsError) as excinfo:
        CadexDynamics.checked_density(0.0, context="body 'arm'")
    # The refusal the model reads is the message plus its correction, and
    # the worker surfaces both.
    refusal = f"{excinfo.value} {excinfo.value.correction}"
    assert "7850" in refusal and "2700" in refusal
    assert excinfo.value.reason == "density_out_of_range"
    with pytest.raises(CadexDynamics.DynamicsError):
        CadexDynamics.checked_density(30000.1, context="body 'arm'")
    with pytest.raises(CadexDynamics.DynamicsError):
        CadexDynamics.checked_density(math.nan, context="body 'arm'")
    assert CadexDynamics.checked_density(7850, context="body 'arm'") == 7850.0


# ---------------------------------------------------------------------------
# M4's conversions, written before they have a caller (docs/MUJOCO.md M4,
# phase 0). Actuators are the second predicted regression of hazard 1 and
# they are a worse one than contact was: a gain, a setpoint, an effort limit
# and an armature are four quantities whose unit depends on whether the
# joint coordinate is angular or linear, and every one of them has a wrong
# answer that runs.
# ---------------------------------------------------------------------------


def test_torque_is_newton_millimetres_at_the_surface() -> None:
    """N·mm in, N·m out -- the same thousand as every other length.

    A torque is a force times a lever arm, and only the arm carries a unit
    that changes. 8000 N·mm is 8 N·m, which is a small servo; 8000 N·m is a
    car's driveshaft, and the difference between them is a script that
    holds an arm and a script that throws it across the room.
    """

    assert CadexDynamics.torque_nm(8000.0) == pytest.approx(8.0, rel=1.0e-12)
    assert CadexDynamics.torque_nm(-1.0) == pytest.approx(-1.0e-3, rel=1.0e-12)
    assert CadexDynamics.torque_nm(0.0) == 0.0


def test_a_setpoint_in_degrees_reaches_mujoco_in_radians() -> None:
    """The 57x error, and the reason the parameter is named ``control_deg``.

    ``compiler.degree`` is False for the whole model (M2 measured what
    leaving it alone costs), so every angle this module writes is radians.
    A ``control="30"`` that meant 30 radians would run, look like physics,
    and be four and three-quarter turns out.
    """

    assert CadexDynamics.angle_radians(180.0) == pytest.approx(math.pi)
    assert CadexDynamics.angle_radians(30.0) == pytest.approx(0.5235987755982988)
    assert CadexDynamics.angle_radians(0.0) == 0.0
    assert CadexDynamics.angle_radians(-90.0) == pytest.approx(-math.pi / 2.0)


def test_an_angular_gain_carries_two_conversions_at_once() -> None:
    """N·mm per degree to N·m per radian: divide by 1000, multiply by 180/π.

    Both factors move the same way, so getting one right and the other
    wrong lands within a factor of 60 of correct -- close enough that the
    arm still holds, badly, and nobody looks again.
    """

    assert CadexDynamics.stiffness_nm_per_rad(1.0) == pytest.approx(
        180.0 / (1000.0 * math.pi), rel=1.0e-12
    )
    # 4000 N·mm/deg is 4 N·m/deg is 229.18 N·m/rad.
    assert CadexDynamics.stiffness_nm_per_rad(4000.0) == pytest.approx(
        229.1831180523293, rel=1.0e-12
    )
    # And the damping term takes exactly the same factor: N·mm·s/deg differs
    # from N·mm/deg by a second, which is SI on both sides.
    assert CadexDynamics.damping_nms_per_rad(4000.0) == pytest.approx(
        CadexDynamics.stiffness_nm_per_rad(4000.0), rel=1.0e-15
    )


def test_a_linear_gain_is_the_other_thousand() -> None:
    """N per mm to N per metre multiplies by 1000; the angular pair divides.

    The two directions are what makes a suffixed pair worth its verbosity.
    A ``stiffness=`` argument whose meaning depended on the joint's kind
    would be off by 5.7 million between the two readings of 4000.
    """

    assert CadexDynamics.stiffness_n_per_m(1.0) == pytest.approx(1000.0)
    assert CadexDynamics.stiffness_n_per_m(4000.0) == pytest.approx(4.0e6)
    assert CadexDynamics.damping_ns_per_m(2.5) == pytest.approx(2500.0)
    ratio = CadexDynamics.stiffness_n_per_m(4000.0) / CadexDynamics.stiffness_nm_per_rad(
        4000.0
    )
    assert ratio == pytest.approx(1000.0 * 1000.0 * math.pi / 180.0, rel=1.0e-12)


def test_armature_is_kilogram_millimetres_squared() -> None:
    """kg·mm² to kg·m² is 1e-6 -- the moment arm squared and nothing else.

    Unlike ``inertia_kg_m2`` there is no density in it: an armature is a
    rotor inertia the author states directly, so only the length unit
    moves.
    """

    assert CadexDynamics.armature_kg_m2(1.0) == pytest.approx(1.0e-6, rel=1.0e-12)
    assert CadexDynamics.armature_kg_m2(50.0) == pytest.approx(5.0e-5, rel=1.0e-12)
    assert CadexDynamics.armature_kg_m2(0.0) == 0.0


def test_a_linear_speed_is_a_length_per_second_and_converts_as_one() -> None:
    """mm/s to m/s is the ordinary thousand, stated so it is not re-derived."""

    assert CadexDynamics.speed_m_s(1234.5) == pytest.approx(1.2345, rel=1.0e-12)
    assert CadexDynamics.speed_m_s(-50.0) == pytest.approx(-0.05, rel=1.0e-12)


def test_every_m4_conversion_round_trips_through_a_known_physical_case() -> None:
    """One worked example end to end, because six factors invite a typo.

    A 4 N·m/deg servo holding 30° with a 120 N·mm·s/deg damper and an
    8 N·m ceiling, in the numbers MuJoCo will actually see.
    """

    assert CadexDynamics.stiffness_nm_per_rad(4000.0) == pytest.approx(229.183118)
    assert CadexDynamics.damping_nms_per_rad(120.0) == pytest.approx(6.8754935)
    assert CadexDynamics.angle_radians(30.0) == pytest.approx(0.523598775)
    assert CadexDynamics.torque_nm(8000.0) == pytest.approx(8.0)
    # The restoring torque at 1° of error: gain times error, in SI.
    torque = CadexDynamics.stiffness_nm_per_rad(4000.0) * CadexDynamics.angle_radians(1.0)
    assert torque == pytest.approx(4.0, rel=1.0e-12), (
        "4 N·m per degree of error is what 4000 N·mm/deg means, by definition"
    )


# ---------------------------------------------------------------------------
# M6: the conversions that carry numbers *out* of MuJoCo.
#
# Hazard 1's fourth instalment, and a new shape of it. Everything above
# converts a number the script wrote into the unit MuJoCo reads; these go the
# other way, and the reason that is more dangerous rather than less is who
# does the arithmetic. A reward formula is evaluated **outside the engine**,
# by a trainer holding raw ``sensordata``, so a reward written in degrees and
# evaluated in radians is a silent factor of 57 in a number nobody inspects.
#
# The answer is the M2/M4 one: every conversion is one number computed here
# and emitted into the task bundle as a per-channel ``scale``, so the trainer
# multiplies rather than converts. These tests were written before the
# functions had a caller, which is what §3.2 asks for.
# ---------------------------------------------------------------------------


def test_an_angle_leaves_mujoco_in_radians_and_reaches_the_surface_in_degrees() -> None:
    """The inverse of :func:`angle_radians`, and the factor is 57.29578.

    This is the one that matters most. Every other conversion on this
    boundary is a power of ten, so getting one wrong moves a decimal point
    and looks wrong; 180/pi does not, and a reward that is 57 times too
    large trains a policy that works and cannot be compared with anything.
    """

    assert CadexDynamics.angle_degrees(math.pi) == pytest.approx(180.0, rel=1.0e-15)
    assert CadexDynamics.angle_degrees(0.0) == 0.0
    assert CadexDynamics.angle_degrees(-math.pi / 4.0) == pytest.approx(-45.0)
    # The scale factor the bundle ships is exactly this function applied to
    # one radian, which is what lets a trainer multiply instead of convert.
    assert CadexDynamics.angle_degrees(1.0) == pytest.approx(
        57.29577951308232, rel=1.0e-15
    )
    for value in (0.0, 0.7, -2.5, 100.0):
        assert CadexDynamics.angle_radians(
            CadexDynamics.angle_degrees(value)
        ) == pytest.approx(value, abs=1.0e-12)


def test_a_speed_leaves_mujoco_in_metres_per_second() -> None:
    """m/s to mm/s -- the ordinary thousand, in the other direction."""

    assert CadexDynamics.speed_mm_per_s(1.2345) == pytest.approx(1234.5, rel=1.0e-12)
    assert CadexDynamics.speed_mm_per_s(-0.05) == pytest.approx(-50.0, rel=1.0e-12)
    for value in (0.0, 3.7, -1.0e3):
        assert CadexDynamics.speed_m_s(
            CadexDynamics.speed_mm_per_s(value)
        ) == pytest.approx(value, abs=1.0e-12)


def test_a_torque_leaves_mujoco_in_newton_metres() -> None:
    """N·m to N·mm. 8 N·m is a small servo; 8 N·mm turns nothing."""

    assert CadexDynamics.torque_nmm(8.0) == pytest.approx(8000.0, rel=1.0e-12)
    assert CadexDynamics.torque_nmm(-0.5) == pytest.approx(-500.0, rel=1.0e-12)
    for value in (0.0, 12.5, -3.25):
        assert CadexDynamics.torque_nm(
            CadexDynamics.torque_nmm(value)
        ) == pytest.approx(value, abs=1.0e-12)


def test_every_inverse_conversion_is_the_exact_inverse_of_its_forward() -> None:
    """Four pairs, checked as pairs rather than as eight separate numbers.

    A conversion and its inverse drifting apart is the failure this codebase
    keeps catching by writing the second copy down, and here the second copy
    costs one loop.
    """

    pairs = (
        (CadexDynamics.length_m, CadexDynamics.length_mm),
        (CadexDynamics.angle_radians, CadexDynamics.angle_degrees),
        (CadexDynamics.speed_m_s, CadexDynamics.speed_mm_per_s),
        (CadexDynamics.torque_nm, CadexDynamics.torque_nmm),
    )
    for forward, inverse in pairs:
        for value in (1.0, -37.5, 0.125):
            assert forward(inverse(value)) == pytest.approx(value, rel=1.0e-14)
            assert inverse(forward(value)) == pytest.approx(value, rel=1.0e-14)
        assert forward(0.0) == 0.0
        assert inverse(0.0) == 0.0


_CONVERSION_ARITHMETIC = re.compile(
    r"""
    (?:[*/]\s*(?:1000(?:\.0)?|1\.?0?e-?(?:9|15))\b)   # * 1000, / 1e-9, ...
  | (?:\b(?:1000(?:\.0)?|1\.?0?e-?(?:9|15))\s*[*/])   # 1e-15 * x
    """,
    re.VERBOSE,
)

#: The assembly stack, plus the modules that would be tempted to "just
#: convert here". :mod:`CadexDynamics` is deliberately absent: it is the one
#: place the factors are allowed to appear.
_NO_CONVERSION_MODULES = (
    "cadex_assembly_api.py",
    "cadex_assembly_worker.py",
    "CadexScriptedDomainPublication.py",
    # The live worker is the same boundary in a hurry: it reads MuJoCo state
    # in metres and emits millimetres to the shell, thirty times a second,
    # under a person watching. ADR-110 added a second such field --
    # ``applied_forces.at_mm`` beside ``position_mm`` -- and reused
    # ``vector_mm`` for it rather than spelling the factor a second time.
    # This is what keeps the third one from being written inline.
    "cadex_live_worker.py",
)

#: **Hazard 1's fifth payment** (docs/MUJOCO.md M7, ADR-084). The offboard
#: trainer is not under ``src/Mod/cadex`` and is in no payload, but it is on
#: the same boundary and pointing the other way: a policy's action vector
#: crosses *out* of a trainer and *into* ``data.ctrl``. M7's answer is M5's
#: and it is structural rather than disciplined -- the network emits in the
#: bundle's advertised units, and the only arithmetic is the ``clamp then
#: x scale`` ``evaluate_episode`` already performs. M7 added no conversion
#: site anywhere, and this is what keeps that true if one is added later.
_OFFBOARD_NO_CONVERSION_FILES = (
    Path("training") / "cadex_train.py",
)

_REPO_ROOT = MODULE_DIR.parents[2]


def _conversion_offenders(label: str, text: str) -> list[str]:
    return [
        f"{label}:{number}: {line.strip()}"
        for number, line in enumerate(text.splitlines(), start=1)
        if _CONVERSION_ARITHMETIC.search(line)
    ]


def test_no_conversion_arithmetic_outside_the_pure_module() -> None:
    offenders: list[str] = []
    for filename in _NO_CONVERSION_MODULES:
        offenders += _conversion_offenders(
            filename, (MODULE_DIR / filename).read_text(encoding="utf-8")
        )
    for relative in _OFFBOARD_NO_CONVERSION_FILES:
        path = _REPO_ROOT / relative
        assert path.is_file(), (
            f"{relative.as_posix()} is named by this grep and does not exist; "
            "the test would pass vacuously"
        )
        offenders += _conversion_offenders(
            relative.as_posix(), path.read_text(encoding="utf-8")
        )
    assert not offenders, (
        "Unit conversion escaped CadexDynamics:\n  " + "\n  ".join(offenders) + "\n"
        "The pure module does every arithmetic operation including every unit "
        "conversion; the worker does every FreeCAD read and nothing else, and "
        "the offboard trainer multiplies by the per-channel scale the bundle "
        "already computed."
    )


def test_the_pure_module_is_where_the_factors_live() -> None:
    """The converse: the grep above is worthless if nothing ever matches."""

    text = (MODULE_DIR / "CadexDynamics.py").read_text(encoding="utf-8")
    assert _CONVERSION_ARITHMETIC.search(text), (
        "CadexDynamics no longer contains the conversion arithmetic the rest "
        "of the stack is forbidden to carry; the grep test would now pass "
        "vacuously wherever the conversion moved to."
    )
