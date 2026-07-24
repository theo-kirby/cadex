# SPDX-License-Identifier: LGPL-2.1-or-later

"""Pure control-resolution helpers of the Parameters panel (no Qt required).

The panel module keeps its slider-metadata helpers Qt-free at module scope so
sliders can be reasoned about headlessly: declared project-script specs
(``params``/``num``) resolved to slider controls, gap-filling bands around
the current value, bound widening, row-model assembly, and the integer
slider scaling round-trip.
"""

from __future__ import annotations

import math

import pytest

import CadexParametersPanel as panel


class TestSpecControl:
    def test_declared_fields_win(self) -> None:
        spec = {
            "name": "bowl_diameter",
            "label": "Bowl Ø",
            "unit": "mm",
            "min": 40.0,
            "max": 200.0,
            "step": 5.0,
            "description": "Outer diameter.",
        }
        control = panel.spec_control(spec, 120.0)
        assert control["label"] == "Bowl Ø"
        assert control["unit"] == "mm"
        assert control["min"] == 40.0
        assert control["max"] == 200.0
        assert control["step"] == 5.0
        assert control["description"] == "Outer diameter."

    def test_missing_bounds_bracket_positive_value(self) -> None:
        control = panel.spec_control({"name": "width"}, 80.0)
        assert control["min"] <= 0.0
        assert control["max"] >= 240.0
        assert control["step"] > 0
        assert control["min"] <= 80.0 <= control["max"]
        assert control["label"] == "Width"
        assert control["unit"] == ""

    def test_zero_value_gets_usable_range(self) -> None:
        control = panel.spec_control({"name": "offset"}, 0.0)
        assert control["min"] <= 0.0 <= control["max"]
        assert control["min"] < control["max"]
        assert control["step"] > 0

    def test_negative_value_brackets_value(self) -> None:
        control = panel.spec_control({"name": "depth"}, -20.0)
        assert control["min"] <= -20.0
        assert control["max"] >= 0.0
        assert control["min"] < control["max"]

    def test_bounds_widen_to_include_current_value(self) -> None:
        spec = {"name": "width", "min": 10.0, "max": 50.0}
        low = panel.spec_control(spec, 2.0)
        assert low["min"] <= 2.0
        assert low["max"] == 50.0
        high = panel.spec_control(spec, 400.0)
        assert high["min"] == 10.0
        assert high["max"] >= 400.0

    def test_label_falls_back_to_titled_name(self) -> None:
        control = panel.spec_control({"name": "blade_count"}, 6.0)
        assert control["label"] == "Blade Count"

    def test_invalid_declared_step_falls_back(self) -> None:
        control = panel.spec_control({"name": "width", "step": 0.0}, 10.0)
        assert control["step"] > 0

    def test_degenerate_declared_range_is_padded(self) -> None:
        control = panel.spec_control({"name": "width", "min": 10.0, "max": 10.0}, 10.0)
        assert control["min"] < 10.0 < control["max"]

    def test_bounds_land_on_step_grid(self) -> None:
        control = panel.spec_control({"name": "width", "step": 2.0}, 33.0)
        assert control["min"] / 2.0 == pytest.approx(round(control["min"] / 2.0))
        assert control["max"] / 2.0 == pytest.approx(round(control["max"] / 2.0))
        assert control["min"] <= 33.0 <= control["max"]


class TestParameterRows:
    def test_rows_follow_declaration_order(self) -> None:
        parameters = {
            "specs": [
                {"name": "width", "default": 30.0},
                {"name": "height", "default": 12.0},
            ],
            "values": {},
        }
        rows = panel.parameter_rows(parameters)
        assert [row["name"] for row in rows] == ["width", "height"]
        assert rows[0]["value"] == 30.0
        assert rows[1]["value"] == 12.0

    def test_stored_value_wins_over_default(self) -> None:
        parameters = {
            "specs": [{"name": "width", "default": 30.0, "min": 10.0, "max": 90.0}],
            "values": {"width": 55.0},
        }
        (row,) = panel.parameter_rows(parameters)
        assert row["value"] == 55.0
        assert row["control"]["min"] == 10.0
        assert row["control"]["max"] == 90.0

    def test_malformed_entries_are_skipped(self) -> None:
        parameters = {
            "specs": [
                "not-a-dict",
                {"default": 5.0},  # no name
                {"name": "ok", "default": 5.0},
            ],
            "values": {"ok": True},  # bool stored value is ignored
        }
        rows = panel.parameter_rows(parameters)
        assert [row["name"] for row in rows] == ["ok"]
        assert rows[0]["value"] == 5.0

    def test_empty_parameters_give_no_rows(self) -> None:
        assert panel.parameter_rows({}) == []
        assert panel.parameter_rows({"specs": [], "values": {}}) == []


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
