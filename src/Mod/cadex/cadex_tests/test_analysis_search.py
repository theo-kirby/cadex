# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The parameter search, and the loop it drives (S1, ADR-142).

``analysis/search.py`` sweeps or optimises a project's declared parameters
with no model in the loop. It is the thing `docs/CLI.md` §1 and
`docs/VISION.md`:151-158 describe as the reason `cli/` exists, so most of
this file drives it against a **real project through the real CLI** rather
than against a mock: the claim being tested is that the loop closes, and a
mock cannot fail the way the loop can.

Its placement contract -- where it lives, what it may import, and that no
GPL package enters the tree -- is asserted beside the rest of ``analysis/``
in ``test_analysis_stress.py``; this file is about behaviour.

The half that needs a built engine skips without one, the same bar
``cli/tests`` sets: a job that silently passes because it never spawned
anything is worse than a skip that says so.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[4]
ANALYSIS = ROOT / "analysis"
SEARCH = ANALYSIS / "search.py"
SHIM = ROOT / "cadex"


def _module(path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(path.stem, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def search():
    pytest.importorskip("scipy", reason="objectives reach the hex core")
    return _module(SEARCH)


def _engine_available() -> bool:
    if os.environ.get("CADEX_ENGINE_ROOT"):
        return True
    return (ROOT / "build/release/bin/FreeCADCmd").is_file()


#: A parametric bracket with three declared controls and one that moves no
#: geometry at all. ``spare`` is not an oversight: a declared parameter that
#: the shape does not depend on is ordinary -- it is how a script reserves a
#: control for a feature that is not written yet -- and it is what gives the
#: digest cache something to hit.
_BRACKET = """
p = params(
    wall=num(6.0, unit="mm", min=2.0, max=12.0, step=0.5, label="Wall"),
    rib=num(8.0, unit="mm", min=3.0, max=20.0, step=0.5, label="Rib"),
    spare=num(1.0, unit="mm", min=0.0, max=5.0, step=1.0, label="Spare"),
)

plate = part.box(60.0, 30.0, p.wall)
web = part.box(p.rib, 30.0, 40.0, origin=[0.0, 0.0, p.wall])
bracket = part.fuse([plate, web])

result = {"bracket": bracket}
"""

#: The same bracket, with a dimension that goes to zero inside the declared
#: range. ``wall`` may be 2.0, and at 2.0 the plate has no thickness -- so
#: the engine refuses. That is a region of the space the script cannot
#: build, which the search has to treat as information rather than as its
#: own failure.
_FRAGILE = """
p = params(
    wall=num(6.0, unit="mm", min=2.0, max=12.0, step=2.0, label="Wall"),
)

plate = part.box(60.0, 30.0, p.wall - 2.0)

result = {"plate": plate}
"""

_LOAD_CASE = {
    "schema": "cadex-analysis-load-case-v1",
    "material": {"name": "PLA", "youngs_modulus_mpa": 3500.0,
                 "poissons_ratio": 0.36, "yield_strength_mpa": 50.0,
                 "density_kg_m3": 1240.0},
    "supports": [{"name": "base",
                  "region": {"face": {"axis": "z", "at": "min",
                                      "depth_mm": 0.5}}}],
    "loads": [{"name": "tip",
               "region": {"face": {"axis": "z", "at": "max", "depth_mm": 2.0}},
               "force_n": [80.0, 0.0, 0.0]}],
}


def _project(tmp_path: Path, script: str, name: str = "project") -> Path:
    """One built, accepted project, through the CLI and with no AI turn.

    `cadex script --set` is the supported way to put an arbitrary script
    into a project: hand-editing `script.py` leaves `script.json` behind and
    breaks the very `cadex params` this is about.
    """

    root = tmp_path / name
    source = tmp_path / f"{name}.py"
    source.write_text(script, encoding="utf-8")
    result = subprocess.run(
        [str(SHIM), "script", "--project", str(root), "--set", str(source),
         "--json"],
        capture_output=True, text=True, check=False, timeout=600)
    if result.returncode != 0:
        pytest.skip(f"could not build a project to search "
                    f"(exit {result.returncode}): {result.stderr[-500:]}")
    return root


# ---------------------------------------------------------------------------
# The design space and the point set. No engine needed.
# ---------------------------------------------------------------------------


def test_a_value_snaps_into_range_and_onto_the_declared_step(search) -> None:
    """A design point a slider could not reach is not a design point.

    A parameter carries a `step` because a person moves it with one, so an
    optimiser's 7.3184 mm has to become a control position. Snapping also
    keeps the parameter cache from missing on two values that are the same
    position.
    """

    spec = search.ParameterSpec(name="wall", default=6.0, minimum=2.0,
                                maximum=12.0, step=0.5, unit="mm")
    assert spec.snap(7.3184) == 7.5
    assert spec.snap(7.1) == 7.0
    assert spec.snap(-100.0) == 2.0
    assert spec.snap(1e9) == 12.0
    # Idempotent, which is what makes the cache key stable.
    assert spec.snap(spec.snap(7.3184)) == spec.snap(7.3184)

    free = search.ParameterSpec("x", 1.0, None, None, None, "")
    assert free.snap(7.3184) == 7.3184
    assert not free.bounded


def test_the_design_space_is_read_off_the_project_state_file(search, tmp_path) -> None:
    """A file read, not a protocol conversation.

    ``params()``'s collected specs are cached in the project's own
    `script.json`, which is what `inspect scope="script"` serves them out
    of -- so the bounds are reachable with nothing running.
    """

    root = tmp_path / "p"
    root.mkdir()
    (root / "script.json").write_text(json.dumps({
        "param_specs": [
            {"name": "wall", "type": "num", "default": 6.0, "min": 2.0,
             "max": 12.0, "step": 0.5, "unit": "mm"},
            {"name": "label", "type": "text", "default": "x"},
        ],
    }), encoding="utf-8")

    specs = search.read_design_space(root)
    assert [spec.name for spec in specs] == ["wall"], (
        "a non-numeric control is not a search axis"
    )
    assert specs[0].minimum == 2.0 and specs[0].maximum == 12.0

    empty = tmp_path / "q"
    empty.mkdir()
    (empty / "script.json").write_text("{}", encoding="utf-8")
    with pytest.raises(search.SearchError, match="no numeric parameters"):
        search.read_design_space(empty)
    with pytest.raises(search.SearchError, match="does not exist"):
        search.read_design_space(tmp_path / "nothing")


def test_a_grid_is_full_factorial_and_refuses_an_unbounded_axis(search) -> None:
    specs = [
        search.ParameterSpec("a", 1.0, 0.0, 10.0, None, "mm"),
        search.ParameterSpec("b", 1.0, 1.0, 3.0, None, "mm"),
    ]
    points = search.grid_points(specs, 3)
    assert len(points) == 9
    assert {point["a"] for point in points} == {0.0, 5.0, 10.0}

    specs.append(search.ParameterSpec("c", 1.0, None, None, None, ""))
    with pytest.raises(search.SearchError, match="no min/max"):
        search.grid_points(specs, 3)


def test_a_latin_hypercube_puts_one_sample_in_every_stratum(search) -> None:
    """Better spread than independent uniforms, in four lines of numpy.

    The property that makes it worth the four lines: every 1/n band of every
    axis gets exactly one sample, so no axis is ever accidentally
    under-explored.
    """

    specs = [search.ParameterSpec("a", 0.0, 0.0, 1.0, None, ""),
             search.ParameterSpec("b", 0.0, 10.0, 20.0, None, "")]
    points = search.random_points(specs, 20, seed=3)
    assert len(points) == 20
    for spec in specs:
        values = np.array([point[spec.name] for point in points])
        strata = np.floor((values - spec.minimum)
                          / (spec.maximum - spec.minimum) * 20).astype(int)
        assert sorted(strata) == list(range(20))


# ---------------------------------------------------------------------------
# What the search does with the numbers it gets back.
# ---------------------------------------------------------------------------


def _trial(search, index, **objectives):
    return search.Trial(index=index, params={"x": float(index)}, ok=True,
                        digest=f"d{index}", objectives=objectives)


def test_the_pareto_front_is_the_non_dominated_set(search) -> None:
    """Computed from the evaluated points, not produced by the search.

    That is what lets `grid` and `random` answer a genuinely multi-objective
    question with none of the multi-objective machinery: the front is read
    off the points already paid for.
    """

    objectives = [
        search.Objective("mass", "min", lambda context: 0.0),
        search.Objective("stiffness", "max", lambda context: 0.0),
    ]
    trials = [
        _trial(search, 0, mass=10.0, stiffness=1.0),   # front
        _trial(search, 1, mass=20.0, stiffness=5.0),   # front
        _trial(search, 2, mass=30.0, stiffness=5.0),   # dominated by 1
        _trial(search, 3, mass=15.0, stiffness=3.0),   # front
        _trial(search, 4, mass=25.0, stiffness=0.5),   # dominated by all
    ]
    front = {trial.index for trial in search.pareto_front(objectives, trials)}
    assert front == {0, 1, 3}


def test_an_infeasible_or_failed_point_is_not_on_the_front(search) -> None:
    objectives = [search.Objective("mass", "min", lambda context: 0.0,
                                   limit=20.0, limit_kind="max")]
    good = _trial(search, 0, mass=10.0)
    over = _trial(search, 1, mass=5.0)
    over.feasible = False
    broken = search.Trial(index=2, params={}, ok=False, error="boom")
    infinite = _trial(search, 3, mass=float("inf"))
    front = search.pareto_front(objectives, [good, over, broken, infinite])
    assert [trial.index for trial in front] == [0]


def test_a_constraint_marks_a_point_infeasible_rather_than_dropping_it(search) -> None:
    """It stays in the trial log, because it is information about the space."""

    objective = search.Objective("stress", "min", lambda context: 0.0,
                                 limit=25.0, limit_kind="max")
    assert objective.satisfied(20.0)
    assert not objective.satisfied(30.0)
    assert not objective.satisfied(float("nan"))

    floor = search.Objective("margin", "max", lambda context: 0.0,
                             limit=2.0, limit_kind="min")
    assert floor.satisfied(3.0)
    assert not floor.satisfied(1.0)


def test_the_scalarisation_penalises_rather_than_returning_infinity(search) -> None:
    """An optimiser handed `inf` learns nothing about which way to move.

    So a failed or infeasible point gets a large **finite** cost, and an
    infeasible one still ranks by how good it otherwise is -- which is what
    lets a search walk back into the feasible region instead of falling off
    a cliff at its edge.
    """

    objectives = [
        search.Objective("mass", "min", lambda context: 0.0,
                         limit=20.0, limit_kind="max"),
        search.Objective("stiffness", "max", lambda context: 0.0),
    ]
    feasible = search._scalarise(objectives, {"mass": 10.0, "stiffness": 4.0}, None)
    infeasible = search._scalarise(objectives, {"mass": 30.0, "stiffness": 4.0}, None)
    worse = search._scalarise(objectives, {"mass": 60.0, "stiffness": 4.0}, None)
    missing = search._scalarise(objectives, {"mass": 10.0}, None)

    assert np.isfinite([feasible, infeasible, worse, missing]).all()
    assert feasible < infeasible < worse < missing
    # Direction is honoured: more stiffness is better.
    assert (search._scalarise(objectives, {"mass": 10.0, "stiffness": 9.0}, None)
            < feasible)
    # And a weight moves the trade.
    assert (search._scalarise(objectives, {"mass": 10.0, "stiffness": 4.0},
                              {"mass": 100.0}) > feasible)


def test_a_plan_of_another_schema_is_refused(search, tmp_path) -> None:
    with pytest.raises(search.SearchError, match="schema"):
        search.run({"schema": "nope"}, tmp_path, tmp_path / "out")


def test_an_unknown_objective_kind_is_refused_by_name(search, tmp_path) -> None:
    with pytest.raises(search.SearchError, match="Unknown objective kind"):
        search.build_objectives(
            {"objectives": [{"kind": "vibes", "name": "v"}]}, tmp_path)
    with pytest.raises(search.SearchError, match="no `objectives`"):
        search.build_objectives({}, tmp_path)


def test_the_optional_backends_refuse_with_the_reason_they_are_absent(
        search, tmp_path) -> None:
    """Optuna and pymoo are deliberately not pinned yet.

    Which of them earns a dependency is a question to settle with a
    measurement from the three backends that need nothing new, and the
    refusal says so rather than pretending the plan was malformed.
    """

    evaluator = object()
    for kind in ("optuna", "pymoo"):
        with pytest.raises(search.SearchError, match="not built"):
            search.run_search({"search": {"kind": kind}}, evaluator, [], [],
                              lambda text: None)
    with pytest.raises(search.SearchError, match="Unknown search kind"):
        search.run_search({"search": {"kind": "hope"}}, evaluator, [], [],
                          lambda text: None)


# ---------------------------------------------------------------------------
# The loop, closed, against a real project through the real CLI.
# ---------------------------------------------------------------------------


pytestmark_engine = pytest.mark.skipif(
    not _engine_available(),
    reason="no built engine; run `pixi run build-engine`")


@pytestmark_engine
def test_a_grid_search_finds_the_front_a_bracket_actually_has(
        search, tmp_path) -> None:
    """End to end: rebuild, measure, rank -- and the physics comes out right.

    A thicker rib is stiffer and heavier, so mass and peak stress genuinely
    conflict and the answer is a front rather than a winner. That is the
    case S1 was specified for.
    """

    root = _project(tmp_path, _BRACKET)
    (tmp_path / "loads.json").write_text(json.dumps(_LOAD_CASE), encoding="utf-8")
    plan = {
        "schema": search.PLAN_SCHEMA,
        "project": str(root),
        "parameters": ["wall", "rib"],
        "objectives": [
            {"name": "mass_g", "kind": "mass", "density_kg_m3": 1240.0,
             "direction": "min"},
            {"name": "stress_mpa", "kind": "stress", "load_case": "loads.json",
             "element_mm": 4.0, "refine": 1, "field": "p99_von_mises_mpa",
             "direction": "min"},
        ],
        "search": {"kind": "grid", "levels": 3},
    }
    report = search.run(plan, tmp_path, tmp_path / "out")

    assert report["trials"]["total"] == 9
    assert report["trials"]["failed"] == 0
    assert report["trials"]["feasible"] == 9
    assert report["schema"] == search.REPORT_SCHEMA

    front = report["pareto_front"]
    assert 2 <= len(front) <= 9
    # Nothing on the front dominates anything else on it.
    for a in front:
        for b in front:
            if a is b:
                continue
            assert not (a["objectives"]["mass_g"] <= b["objectives"]["mass_g"]
                        and a["objectives"]["stress_mpa"]
                        <= b["objectives"]["stress_mpa"])

    lightest = report["best"]["mass_g"]
    strongest = report["best"]["stress_mpa"]
    assert lightest["params"]["wall"] == 2.0, "the thinnest plate is the lightest"
    assert strongest["params"]["rib"] == 20.0, "the deepest rib carries the load"
    assert lightest["objectives"]["stress_mpa"] > strongest["objectives"]["stress_mpa"]
    assert lightest["objectives"]["mass_g"] < strongest["objectives"]["mass_g"]


@pytestmark_engine
def test_a_constraint_splits_the_grid_into_feasible_and_not(
        search, tmp_path) -> None:
    root = _project(tmp_path, _BRACKET)
    (tmp_path / "loads.json").write_text(json.dumps(_LOAD_CASE), encoding="utf-8")
    plan = {
        "schema": search.PLAN_SCHEMA,
        "project": str(root),
        "parameters": ["rib"],
        "objectives": [
            {"name": "mass_g", "kind": "mass", "density_kg_m3": 1240.0,
             "direction": "min"},
            {"name": "stress_mpa", "kind": "stress", "load_case": "loads.json",
             "element_mm": 4.0, "refine": 1, "field": "p99_von_mises_mpa",
             "direction": "min", "max": 3.0},
        ],
        "search": {"kind": "grid", "levels": 4},
    }
    report = search.run(plan, tmp_path, tmp_path / "out")
    assert 0 < report["trials"]["feasible"] < report["trials"]["total"], (
        "the constraint separated nothing, so it is not being applied"
    )
    for point in report["pareto_front"]:
        assert point["objectives"]["stress_mpa"] <= 3.0


@pytestmark_engine
def test_a_repeated_design_point_costs_nothing(search, tmp_path) -> None:
    """The parameter cache, which is the free one."""

    root = _project(tmp_path, _BRACKET)
    specs = search.read_design_space(root)
    objectives = search.build_objectives(
        {"objectives": [{"name": "mass_g", "kind": "mass",
                         "density_kg_m3": 1240.0}]}, tmp_path)
    evaluator = search.Evaluator(root, objectives, specs=specs,
                                 out_root=tmp_path / "out",
                                 cadex=[str(SHIM)])
    first = evaluator.evaluate({"wall": 4.0})
    assert first.ok and evaluator.rebuilds == 1
    again = evaluator.evaluate({"wall": 4.0})
    assert again is first, "a design point already evaluated was rebuilt"
    assert evaluator.rebuilds == 1
    # ...and two values that snap to the same control position are one point.
    snapped = evaluator.evaluate({"wall": 4.1})
    assert snapped is first
    assert evaluator.rebuilds == 1


@pytestmark_engine
def test_a_parameter_that_moves_no_geometry_hits_the_digest_cache(
        search, tmp_path) -> None:
    """The second cache, and the one that saves the expensive half.

    ``spare`` is declared and unused, so moving it produces a different
    parameter vector and the **same model**. The rebuild still happens --
    only the engine can say the digest is unchanged -- but the objective
    does not, and when the objective is an FEA solve that is the whole cost.
    """

    root = _project(tmp_path, _BRACKET)
    specs = search.read_design_space(root)
    counter = {"calls": 0}

    def _count(context):
        counter["calls"] += 1
        return 1.0

    objectives = [search.Objective("counted", "min", _count)]
    evaluator = search.Evaluator(root, objectives, specs=specs,
                                 out_root=tmp_path / "out",
                                 cadex=[str(SHIM)])
    first = evaluator.evaluate({"wall": 4.0, "spare": 1.0})
    second = evaluator.evaluate({"wall": 4.0, "spare": 4.0})

    assert first.ok and second.ok
    assert first.params != second.params, "the two design points are the same"
    assert first.digest == second.digest, (
        "an unused parameter moved the model's digest"
    )
    assert evaluator.rebuilds == 2, "the rebuild is not what this cache saves"
    assert second.source == "digest-cached"
    assert counter["calls"] == 1, "the objective ran twice on one model"
    assert second.objectives == first.objectives


@pytestmark_engine
def test_a_killed_run_resumes_from_its_trial_log(search, tmp_path) -> None:
    """No database and no server: a JSONL you can read with `tail`.

    A search that cannot be killed and restarted is a search nobody runs
    twice, and this is the cheapest possible version of that.
    """

    root = _project(tmp_path, _BRACKET)
    plan = {
        "schema": search.PLAN_SCHEMA,
        "project": str(root),
        "parameters": ["wall"],
        "objectives": [{"name": "mass_g", "kind": "mass",
                        "density_kg_m3": 1240.0, "direction": "min"}],
        "search": {"kind": "grid", "levels": 3},
    }
    out = tmp_path / "out"
    first = search.run(plan, tmp_path, out)
    assert first["trials"]["rebuilds"] == 3
    assert (out / search.TRIAL_LOG).is_file()

    # A second run into the same directory without --resume is refused:
    # appending would silently make the report a mixture of two searches.
    with pytest.raises(search.SearchError, match="--resume"):
        search.run(plan, tmp_path, out)

    second = search.run(plan, tmp_path, out, resume=True)
    assert second["trials"]["resumed"] == 3
    assert second["trials"]["rebuilds"] == 0, "a resumed run rebuilt anyway"
    assert second["trials"]["total"] == 3
    assert second["best"]["mass_g"]["params"] == first["best"]["mass_g"]["params"]


@pytestmark_engine
def test_a_refused_design_point_is_information_rather_than_a_failure(
        search, tmp_path) -> None:
    """A region the script cannot build is a fact about the space.

    `docs/CLI.md` gives exit 3 its own meaning for exactly this reason: a
    refused script is a modelling problem, not an infrastructure one. So the
    search records it, says how many, and carries on -- a sweep that aborted
    on the first zero-thickness plate would never map anything.
    """

    root = _project(tmp_path, _FRAGILE, name="fragile")
    plan = {
        "schema": search.PLAN_SCHEMA,
        "project": str(root),
        "objectives": [{"name": "mass_g", "kind": "mass",
                        "density_kg_m3": 1240.0, "direction": "min"}],
        "search": {"kind": "grid", "levels": 3},
    }
    report = search.run(plan, tmp_path, tmp_path / "out")

    assert report["trials"]["total"] == 3
    assert report["trials"]["refused"] >= 1, (
        "a zero-thickness plate was not refused; this test proves nothing"
    )
    assert report["trials"]["failed"] == 0, (
        "a refusal was counted as a failure"
    )
    assert report["trials"]["feasible"] >= 1, "nothing built at all"
    assert any("refused" in text for text in report["warnings"])
    assert report["pareto_front"], "the buildable points still make a front"


@pytestmark_engine
def test_the_cli_writes_one_json_line_and_a_report_file(tmp_path) -> None:
    """The output discipline every file in this tree keeps (ADR-093)."""

    pytest.importorskip("scipy")
    root = _project(tmp_path, _BRACKET)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps({
        "schema": "cadex-analysis-search-v1",
        "project": str(root),
        "parameters": ["wall"],
        "objectives": [{"name": "mass_g", "kind": "mass",
                        "density_kg_m3": 1240.0, "direction": "min"}],
        "search": {"kind": "grid", "levels": 2},
    }), encoding="utf-8")

    out = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, str(SEARCH), str(plan_path), "--out", str(out)],
        capture_output=True, text=True, check=False, timeout=900)
    assert result.returncode == 0, result.stderr[-3000:]
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1, "stdout carried more than the one JSON line"
    report = json.loads(lines[0])
    assert report["trials"]["total"] == 2
    assert json.loads((out / "report.json").read_text(encoding="utf-8")) == report


def test_a_refusal_is_an_exit_code_and_a_sentence(tmp_path) -> None:
    pytest.importorskip("scipy")
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps({"schema": "wrong"}), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SEARCH), str(plan_path), "--out", str(tmp_path / "o")],
        capture_output=True, text=True, check=False, timeout=300)
    assert result.returncode == 2
    assert result.stdout.strip() == ""
    assert "refused:" in result.stderr
