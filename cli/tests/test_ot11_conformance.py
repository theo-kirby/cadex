# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ot11 P1: every stored evaluation is checked against the frozen contract.

``docs/probes/ot11/runner/conformance.py`` compares the spec an evaluation
resolved with ``contract.json`` and names each difference. These pin that a
spec read straight from the contract conforms for each behaviour, that each
kind of drift is named, and that the evaluation receipt's deviations are
the ones the report explains.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import math
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PROBE = REPO / "docs" / "probes" / "ot11"
RETAINED = PROBE / "retained"
CONTRACT = json.loads((PROBE / "contract.json").read_text(encoding="utf-8"))


def _conformance():
    spec = importlib.util.spec_from_file_location("conformance", PROBE / "runner" / "conformance.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _spec(name: str) -> dict:
    data = json.loads((RETAINED / name).read_text(encoding="utf-8"))
    return copy.deepcopy(data["spec"])


SPECS = {
    "walk": "walk-spec-resolved-r22.json",
    "reach": "r2-confirm-1-evaluation.json",
    "balance": "r3-confirm-1-evaluation.json",
}


@pytest.mark.parametrize("behaviour", sorted(SPECS))
def test_a_spec_read_from_the_contract_conforms(behaviour):
    assert _conformance().deviations(_spec(SPECS[behaviour]), CONTRACT) == []


def _predicate(spec: dict, pid: str) -> dict:
    return next(p for p in spec["predicates"] if p["id"] == pid)


def _walk_threshold(spec):
    _predicate(spec, "W7")["max"] = 0.20


def _walk_metric(spec):
    _predicate(spec, "W6")["metric"] = "step_clearance_mm_min"


def _walk_dropped(spec):
    spec["predicates"] = [p for p in spec["predicates"] if p["id"] != "W9"]


def _walk_added(spec):
    spec["predicates"].append({"id": "W11", "metric": "completed", "min": 1.0, "max": None})


def _walk_seed(spec):
    spec["seeds"] = spec["seeds"][:-1] + [1111]


def _walk_episode(spec):
    spec["episode"]["episode_seconds"] = 8.0


def _walk_tilt(spec):
    spec["reset_variation"][0]["tilt_high_rad"] = math.radians(1.5)


def _walk_shove(spec):
    shove = spec["disturbance"][0]
    shove["newtons_high"] = 0.10 * spec["scale"]["weight_n"]


def _walk_shove_time(spec):
    spec["disturbance"][0]["at_high_s"] = 9.0


def _walk_goal(spec):
    spec["goal"][0]["high"] = 1.2 * spec["scale"]["hip_height_mm"]


DRIFTS = {
    "threshold": (_walk_threshold, "W7: max 0.2 != frozen 0.15"),
    "metric": (_walk_metric, "W6: metric step_clearance_mm_min != frozen step_clearance_hip_heights_min"),
    "dropped": (_walk_dropped, "W9: missing"),
    "added": (_walk_added, "W11: not in the contract"),
    "seed": (_walk_seed, "seeds "),
    "episode": (_walk_episode, "episode_seconds 8.0 != frozen 10.0"),
    "tilt": (_walk_tilt, "reset tilt_deg [0, 1.5] != frozen [0, 3]"),
    "shove force": (_walk_shove, "shove 1 force_weights [0.05, 0.1] != frozen [0.05, 0.2]"),
    "shove time": (_walk_shove_time, "shove 1 at_s [3, 9] != frozen [3, 7]"),
    "goal": (_walk_goal, "goal hip_heights_per_s [0.6, 1.2] != frozen [0.6, 1]"),
}


@pytest.mark.parametrize("name", sorted(DRIFTS))
def test_each_kind_of_drift_is_named(name):
    change, expected = DRIFTS[name]
    spec = _spec(SPECS["walk"])
    change(spec)
    found = _conformance().deviations(spec, CONTRACT)
    assert len(found) == 1 and found[0].startswith(expected), found


def test_reach_and_balance_drift_is_named():
    module = _conformance()
    reach = _spec(SPECS["reach"])
    reach["goal"][0]["joint_fraction"] = 1.0
    _predicate(reach, "Q3")["max"] = 3.0
    assert module.deviations(reach, CONTRACT) == [
        "Q3: max 3.0 != frozen 2.0", "goal joint_fraction 1.0 != frozen 0.8"]
    balance = _spec(SPECS["balance"])
    balance["disturbance"] = balance["disturbance"][:1]
    assert module.deviations(balance, CONTRACT) == ["disturbance: 1 declared, frozen 2"]


def test_the_receipt_names_every_deviation_and_the_report_explains_them():
    """Rows 1-2 are w2-2 with no goal to track; rows 20-21 are r8's stale hip digit (ADR-468)."""

    rows = json.loads((RETAINED / "ot11-evaluations.json").read_text(encoding="utf-8"))["evaluations"]
    deviating = {index: row["contract_deviations"] for index, row in enumerate(rows, 1)
                 if row["contract_deviations"]}
    assert sorted(deviating) == [1, 2, 20, 21]
    for index in (1, 2):
        assert deviating[index] == ["W3: missing", "W4-lateral: missing",
                                    "goal: 0 declared, frozen one speed command"]
    for index in (20, 21):
        assert rows[index - 1]["trained_by"].startswith("r8-stance")
        assert deviating[index] == ["goal hip_heights_per_s [0.599999, 0.999998] != frozen [0.6, 1]"]
    report = (PROBE / "REPORT.md").read_text(encoding="utf-8")
    section = report.split("## Every evaluation", 1)[1].split("## Every judge score", 1)[0]
    assert "Thirty-one of the 35 conform" in section
    assert "rows 1 and 2" in section and "rows 20 and 21" in section
