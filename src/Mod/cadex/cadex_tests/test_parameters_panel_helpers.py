# SPDX-License-Identifier: LGPL-2.1-or-later

"""Pure control-resolution helpers of the Parameters panel (no Qt required).

The panel module keeps its slider-metadata helpers Qt-free at module scope so
sliders can be reasoned about headlessly: heuristics for undeclared
parameters, declared-over-heuristic merging, bound widening, and the integer
slider scaling round-trip.
"""

from __future__ import annotations

import math

import pytest

import CadexParametersPanel as panel


class TestHeuristicControl:
    def test_positive_length_brackets_value(self) -> None:
        control = panel.heuristic_control("mug_diameter", 80.0)
        assert control["unit"] == "mm"
        # 0.1x-3x band, nice-rounded outward onto the step grid.
        assert control["min"] == pytest.approx(5.0)
        assert control["max"] == pytest.approx(240.0)
        assert control["step"] > 0
        assert control["min"] <= 80.0 <= control["max"]
        assert control["label"] == "Mug Diameter"

    def test_zero_value_gets_usable_range(self) -> None:
        control = panel.heuristic_control("offset", 0.0)
        assert control["min"] <= 0.0 <= control["max"]
        assert control["min"] < control["max"]
        assert control["step"] > 0

    def test_negative_value_brackets_value(self) -> None:
        control = panel.heuristic_control("depth", -20.0)
        assert control["min"] <= -20.0 <= control["max"]
        assert control["min"] < control["max"]
        assert control["min"] == pytest.approx(-60.0)

    def test_angle_like_names_get_degrees(self) -> None:
        for name in (
            "handle_angle",
            "rotation",
            "tilt",
            "twist_deg",
            "taper_top",
            "bladeRotation",
        ):
            control = panel.heuristic_control(name, 15.0)
            assert control["unit"] == "°", name
            assert (control["min"], control["max"]) == (0.0, 360.0), name
            assert control["step"] == 1.0, name

    def test_count_like_names_get_integer_steps(self) -> None:
        for name in ("blade_count", "num_spokes", "teeth", "sides", "segments"):
            control = panel.heuristic_control(name, 12.0)
            assert control["min"] == 1.0, name
            assert control["step"] == 1.0, name
            assert control["max"] >= 12.0, name

    def test_count_words_do_not_hijack_length_names(self) -> None:
        # "hole_diameter" contains no count token; it must stay a length.
        control = panel.heuristic_control("hole_diameter", 6.0)
        assert control["unit"] == "mm"
        assert control["step"] != 1.0 or control["min"] != 1.0


class TestResolveControl:
    def test_declared_fields_win_per_field(self) -> None:
        declared = {"label": "Bowl Ø", "min": 40.0, "max": 200.0, "unit": "mm"}
        control = panel.resolve_control("bowl_diameter", 120.0, declared)
        assert control["label"] == "Bowl Ø"
        assert control["min"] == 40.0
        assert control["max"] == 200.0
        # Heuristic fills the undeclared step.
        assert control["step"] > 0

    def test_heuristic_fills_all_gaps_when_nothing_declared(self) -> None:
        for declared in (None, {}, "not-a-dict"):
            control = panel.resolve_control("height", 90.0, declared)
            assert set(control) >= {"label", "unit", "min", "max", "step"}
            assert control["min"] < control["max"]

    def test_bounds_widen_to_include_current_value(self) -> None:
        declared = {"min": 10.0, "max": 50.0}
        low = panel.resolve_control("width", 2.0, declared)
        assert low["min"] == 2.0
        assert low["max"] == 50.0
        high = panel.resolve_control("width", 400.0, declared)
        assert high["min"] == 10.0
        assert high["max"] == 400.0

    def test_declared_angle_step_overrides_heuristic(self) -> None:
        control = panel.resolve_control("handle_angle", 15.0, {"step": 5.0})
        assert control["step"] == 5.0
        assert control["unit"] == "°"

    def test_invalid_declared_step_falls_back(self) -> None:
        control = panel.resolve_control("width", 10.0, {"step": 0.0})
        assert control["step"] > 0

    def test_degenerate_declared_range_is_padded(self) -> None:
        control = panel.resolve_control("width", 10.0, {"min": 10.0, "max": 10.0})
        assert control["min"] < 10.0 < control["max"]


class TestSliderScaling:
    def test_round_trip_lands_on_step_grid(self) -> None:
        control = {"min": 4.0, "max": 120.0, "step": 2.0}
        for value in (4.0, 10.0, 55.3, 119.0, 120.0):
            position = panel.value_to_slider(value, control)
            back = panel.slider_to_value(position, control)
            assert control["min"] <= back <= control["max"]
            assert abs(back - value) <= control["step"] / 2.0 + 1e-9
            # Grid values survive the round trip exactly.
            grid = panel.slider_to_value(position, control)
            assert panel.slider_to_value(
                panel.value_to_slider(grid, control), control
            ) == pytest.approx(grid)

    def test_positions_clamp_to_range(self) -> None:
        control = {"min": 0.0, "max": 10.0, "step": 0.5}
        assert panel.value_to_slider(-5.0, control) == 0
        assert panel.value_to_slider(50.0, control) == panel.slider_steps(control)
        assert panel.slider_to_value(10_000, control) == 10.0

    def test_fractional_step_scaling(self) -> None:
        control = {"min": 0.5, "max": 3.0, "step": 0.1}
        assert panel.slider_steps(control) == 25
        assert panel.slider_to_value(0, control) == pytest.approx(0.5)
        assert panel.slider_to_value(25, control) == pytest.approx(3.0)
        assert panel.value_to_slider(1.7, control) == 12

    def test_slider_steps_never_zero(self) -> None:
        control = {"min": 0.0, "max": 0.5, "step": 2.0}
        assert panel.slider_steps(control) >= 1


class TestFormattingHelpers:
    def test_nice_step_returns_decade_values(self) -> None:
        for span in (0.4, 2.3, 116.0, 999.0, 5.0e4):
            step = panel.nice_step(span)
            mantissa = step / (10.0 ** math.floor(math.log10(step)))
            assert round(mantissa, 6) in (1.0, 2.0, 5.0, 10.0), span
            assert 50 <= span / step <= 200 or span / step < 50

    def test_nice_step_degenerate_span(self) -> None:
        assert panel.nice_step(0.0) == 1.0
        assert panel.nice_step(float("nan")) == 1.0

    def test_spin_decimals_match_step(self) -> None:
        assert panel.spin_decimals(1.0) == 0
        assert panel.spin_decimals(2.0) == 0
        assert panel.spin_decimals(0.5) == 1
        assert panel.spin_decimals(0.1) == 1
        assert panel.spin_decimals(0.05) == 2
        assert panel.spin_decimals(0.001) == 3

    def test_parameter_title(self) -> None:
        assert panel.parameter_title("mug_diameter") == "Mug Diameter"
        assert panel.parameter_title("bladeCount") == "Blade Count"
        assert panel.parameter_title("x") == "X"
