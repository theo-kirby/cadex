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

ADR-060 says the units boundary "gets a test before it gets a feature".
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
)


def test_no_conversion_arithmetic_outside_the_pure_module() -> None:
    offenders: list[str] = []
    for filename in _NO_CONVERSION_MODULES:
        text = (MODULE_DIR / filename).read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            if _CONVERSION_ARITHMETIC.search(line):
                offenders.append(f"{filename}:{number}: {line.strip()}")
    assert not offenders, (
        "Unit conversion escaped CadexDynamics:\n  " + "\n  ".join(offenders) + "\n"
        "The pure module does every arithmetic operation including every unit "
        "conversion; the worker does every FreeCAD read and nothing else."
    )


def test_the_pure_module_is_where_the_factors_live() -> None:
    """The converse: the grep above is worthless if nothing ever matches."""

    text = (MODULE_DIR / "CadexDynamics.py").read_text(encoding="utf-8")
    assert _CONVERSION_ARITHMETIC.search(text), (
        "CadexDynamics no longer contains the conversion arithmetic the rest "
        "of the stack is forbidden to carry; the grep test would now pass "
        "vacuously wherever the conversion moved to."
    )
