#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Sweep or optimise a project's declared parameters, with no model in the
loop (S1).

`docs/CLI.md` §1 describes this use case by name and `docs/VISION.md`
:151-158 makes it the justification for `cli/` existing at all: **an
expensive model turn authors a parametric script once, and after that a
cheap loop sweeps its parameters and re-exports with no model in the loop
at all.** The outer loop has therefore shipped since Phase 9. This file is
the thing that drives it and decides where to look next.

Two facts about the repository make it small (both measured, ADR-142):

* **The design space is already machine-readable and already on disk.**
  `params()`/`num()` carry `min` / `max` / `step` / `unit`, and the collected
  specs are cached in the project's own `script.json`. So reading the bounds
  is a file read, not a protocol conversation.
* **An evaluation is a subprocess.** `./cadex params --set k=v --out DIR
  --json` is the documented, test-pinned surface, and one rebuild of a small
  parametric bracket measured **0.7 s** here.

**Why a subprocess rather than `cli/cadex_cli/client.py`.** Importing the
client is allowed -- `cli/` is engine-side and LGPL, so no boundary is
crossed -- and it was still the wrong choice. Driving the CLI keeps this
tree's whole discipline intact: `analysis/` imports nothing from the engine,
reports `cadex_importable` false, and needs no view on the protocol at all.
It also buys **crash isolation per evaluation**, which is what you want on
evaluation 173 when a rebuild segfaults rather than refuses. The cost is one
process spawn per design point, which the measurement says is noise next to
the rebuild.

**Two caches, and they are not the same cache.**

* On the **parameter vector**: a design point already evaluated is not
  rebuilt. That is the free one.
* On the **`digest`**: two *different* parameter vectors can produce the same
  model -- a dimension that rounds away, a feature that clamps -- and the
  digest is the only thing that says so. Hitting it skips the *objective*,
  which is the expensive half when the objective is an FEA solve. Compare
  `digest`, never the files: STEP embeds a wall-clock timestamp in
  `FILE_NAME`, so two exports of an identical model differ byte for byte
  across a second boundary (`docs/CLI.md`:126-131).

**One fixed grid inside a search; the sweep is for the design you ship.**
S0's refinement sweep exists because a single grid is not a *measurement*.
Inside a search it is the right thing anyway: what a search needs is a
consistent ranking, and a fixed grid gives every candidate the same bias,
where a per-candidate adaptive sweep would let the discretisation move
between two designs being compared. So `refine` defaults to 1 here and the
report says so. Re-run the winner through `cadex_stress.py` properly.

Usage::

    python analysis/search.py plan.json --out ./sweep
    python analysis/search.py plan.json --out ./sweep --resume
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Iterable, Sequence

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cadex_stress as stress  # noqa: E402

PLAN_SCHEMA = "cadex-analysis-search-v1"
REPORT_SCHEMA = "cadex-analysis-search-report-v1"
TRIAL_SCHEMA = "cadex-analysis-trial-v1"

#: The trial log, appended one JSON line at a time and read back on
#: ``--resume``. A search that cannot be killed and restarted is a search
#: nobody runs twice, and this is the cheapest possible version of that:
#: no database, no server, and readable with ``tail``.
TRIAL_LOG = "trials.jsonl"

#: What the CLI's exit codes mean (`docs/CLI.md`). 3 is the one that is not
#: an error here: a refused script is a design point outside what the model
#: can build, which is information about the space rather than a failure of
#: the search.
_EXIT_REFUSED = 3


class SearchError(RuntimeError):
    """A refusal, with a sentence a person can act on."""


# ---------------------------------------------------------------------------
# The design space, read off the project's own state file.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParameterSpec:
    """One declared numeric control, as the script declared it."""

    name: str
    default: float
    minimum: float | None
    maximum: float | None
    step: float | None
    unit: str

    @property
    def bounded(self) -> bool:
        return self.minimum is not None and self.maximum is not None

    def snap(self, value: float) -> float:
        """Clamp into the declared range and onto the declared step.

        A parameter carries a ``step`` because a person moves it with a
        slider, so a design point off that step is one the project cannot be
        put back into by hand. Snapping keeps every point the search reports
        reachable, and keeps the parameter-vector cache from missing on two
        values that are the same control position.
        """

        result = float(value)
        if self.minimum is not None:
            result = max(result, self.minimum)
        if self.maximum is not None:
            result = min(result, self.maximum)
        if self.step:
            origin = self.minimum if self.minimum is not None else 0.0
            result = origin + round((result - origin) / self.step) * self.step
            if self.minimum is not None:
                result = max(result, self.minimum)
            if self.maximum is not None:
                result = min(result, self.maximum)
        # Kill the accumulated binary noise, so the same control position
        # always writes the same string on the command line.
        return float(f"{result:.9g}")


def read_design_space(project: Path) -> list[ParameterSpec]:
    """The bounded search space, from `<project>/script.json`.

    A file read rather than a protocol conversation: the specs `params()`
    collected are cached in the project's own state, which is what
    `inspect scope="script"` serves them out of.
    """

    state_path = Path(project) / "script.json"
    if not state_path.is_file():
        raise SearchError(
            f"{state_path} does not exist, so this project has no declared "
            "parameters yet. Build the script once first -- `cadex script "
            "--set` or one `./cadex -p` turn."
        )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    specs = []
    for raw in state.get("param_specs") or []:
        if str(raw.get("type") or "num") != "num":
            continue
        specs.append(ParameterSpec(
            name=str(raw["name"]),
            default=float(raw.get("default") or 0.0),
            minimum=None if raw.get("min") is None else float(raw["min"]),
            maximum=None if raw.get("max") is None else float(raw["max"]),
            step=None if raw.get("step") is None else float(raw["step"]),
            unit=str(raw.get("unit") or ""),
        ))
    if not specs:
        raise SearchError(
            "This project declares no numeric parameters, so there is "
            "nothing to search. `params(width=num(...))` is what makes a "
            "script sweepable."
        )
    return specs


# ---------------------------------------------------------------------------
# Objectives. Each reads a finished evaluation and returns one number.
# ---------------------------------------------------------------------------


@dataclass
class Context:
    """Everything an objective is allowed to look at."""

    params: dict[str, float]
    digest: str
    out_dir: Path
    outputs: dict[str, dict[str, str]]
    envelope: dict[str, Any]

    def solid(self, name: str | None, suffix: str) -> Path:
        """One exported file, by output name and extension."""

        if name is None:
            if len(self.outputs) != 1:
                raise SearchError(
                    "This project declares more than one output, so an "
                    f"objective must name which one it reads: "
                    f"{', '.join(sorted(self.outputs))}."
                )
            name = next(iter(self.outputs))
        files = self.outputs.get(name)
        if not files:
            raise SearchError(f"The rebuild published no output named {name!r}.")
        path = files.get(suffix)
        if not path:
            raise SearchError(
                f"Output {name!r} has no {suffix!r} file. Ask the search for "
                f"`--format` including it."
            )
        return Path(path)


@dataclass
class Objective:
    """A named number, a direction, and how to get it."""

    name: str
    direction: str                       # "min" or "max"
    evaluate: Callable[[Context], float]
    limit: float | None = None           # a constraint, if declared
    limit_kind: str = ""                 # "max" or "min"

    def satisfied(self, value: float) -> bool:
        if self.limit is None or not math.isfinite(value):
            return math.isfinite(value)
        return value <= self.limit if self.limit_kind == "max" else value >= self.limit


def _volume_objective(spec: dict[str, Any]) -> Callable[[Context], float]:
    output = spec.get("output")

    def _read(context: Context) -> float:
        triangles, _ = stress.read_solid(context.solid(output, "stl"))
        return stress.mesh_volume_mm3(triangles)

    return _read


def _mass_objective(spec: dict[str, Any]) -> Callable[[Context], float]:
    density = float(spec["density_kg_m3"])
    volume = _volume_objective(spec)

    def _read(context: Context) -> float:
        return volume(context) * density * 1.0e-6   # mm^3 * kg/m^3 -> g

    return _read


def _extent_objective(spec: dict[str, Any]) -> Callable[[Context], float]:
    axis = {"x": 0, "y": 1, "z": 2}[str(spec.get("axis", "z")).lower()]
    output = spec.get("output")

    def _read(context: Context) -> float:
        triangles, _ = stress.read_solid(context.solid(output, "stl"))
        points = triangles.reshape(-1, 3)
        return float(points[:, axis].max() - points[:, axis].min())

    return _read


def _stress_objective(spec: dict[str, Any], plan_dir: Path) -> Callable[[Context], float]:
    """S0, run on this design point. The reason S1 follows S0.

    ``refine`` defaults to 1 deliberately -- see the module docstring. A
    search wants every candidate to carry the same discretisation bias so
    the *ranking* is meaningful; the convergence sweep is for the design you
    decide to ship.
    """

    case_path = (plan_dir / spec["load_case"]).resolve()
    if not case_path.is_file():
        raise SearchError(f"The load case {case_path} does not exist.")
    load_case = json.loads(case_path.read_text(encoding="utf-8"))
    if str(load_case.get("schema") or "") != stress.LOAD_CASE_SCHEMA:
        raise SearchError(
            f"{case_path.name} declares schema {load_case.get('schema')!r}, "
            f"and this reads {stress.LOAD_CASE_SCHEMA!r}."
        )
    field_name = str(spec.get("field") or "p99_von_mises_mpa")
    element_mm = spec.get("element_mm")
    refine = int(spec.get("refine") or 1)
    output = spec.get("output")

    def _read(context: Context) -> float:
        report = stress.analyse(
            context.solid(output, "stl"), load_case,
            element_mm=None if element_mm is None else float(element_mm),
            levels=refine, note=f"search: {context.digest[:12]}",
        )
        for block in ("result", "mass", "solver"):
            if field_name in report[block]:
                value = report[block][field_name]
                return float("inf") if value is None else float(value)
        raise SearchError(
            f"A stress objective asked for {field_name!r}, which is not in "
            "the report's `result`, `mass` or `solver` blocks."
        )

    return _read


def _command_objective(spec: dict[str, Any], plan_dir: Path) -> Callable[[Context], float]:
    """An external simulator, exactly as `docs/CLI.md` §1 describes it.

    The escape hatch that keeps this file from having to know about airflow
    or print time: run a program in the output directory and read one number
    out of the JSON object it prints. Its stdout is parsed and its stderr is
    not, which is the rule every other file in this tree follows.
    """

    argv = [str(token) for token in spec["command"]]
    key = str(spec.get("key") or "value")

    def _read(context: Context) -> float:
        result = subprocess.run(
            argv + [str(context.out_dir)], capture_output=True, text=True,
            cwd=str(plan_dir), timeout=float(spec.get("timeout_s") or 3600),
            check=False,
        )
        if result.returncode != 0:
            raise SearchError(
                f"{argv[0]} exited {result.returncode}: "
                f"{result.stderr.strip()[-500:]}"
            )
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            raise SearchError(f"{argv[0]} printed nothing on stdout.")
        payload = json.loads(lines[-1])
        if key not in payload:
            raise SearchError(
                f"{argv[0]} printed no {key!r}; it printed "
                f"{', '.join(sorted(payload))}."
            )
        return float(payload[key])

    return _read


_OBJECTIVE_KINDS = {
    "volume": lambda spec, plan_dir: _volume_objective(spec),
    "mass": lambda spec, plan_dir: _mass_objective(spec),
    "extent": lambda spec, plan_dir: _extent_objective(spec),
    "stress": _stress_objective,
    "command": _command_objective,
}


def build_objectives(plan: dict[str, Any], plan_dir: Path) -> list[Objective]:
    declared = plan.get("objectives") or []
    if not declared:
        raise SearchError(
            "The plan declares no `objectives`, so there is nothing to "
            "search for."
        )
    objectives: list[Objective] = []
    for spec in declared:
        kind = str(spec.get("kind") or "")
        if kind not in _OBJECTIVE_KINDS:
            raise SearchError(
                f"Unknown objective kind {kind!r}. This reads: "
                f"{', '.join(sorted(_OBJECTIVE_KINDS))}."
            )
        direction = str(spec.get("direction") or "min")
        if direction not in {"min", "max"}:
            raise SearchError(f"An objective's direction is min or max, not {direction!r}.")
        limit_kind = ""
        limit = None
        if spec.get("max") is not None:
            limit, limit_kind = float(spec["max"]), "max"
        elif spec.get("min") is not None:
            limit, limit_kind = float(spec["min"]), "min"
        objectives.append(Objective(
            name=str(spec.get("name") or kind),
            direction=direction,
            evaluate=_OBJECTIVE_KINDS[kind](spec, plan_dir),
            limit=limit,
            limit_kind=limit_kind,
        ))
    names = [objective.name for objective in objectives]
    if len(set(names)) != len(names):
        raise SearchError(f"Two objectives share a name: {names}.")
    return objectives


# ---------------------------------------------------------------------------
# Evaluating one design point.
# ---------------------------------------------------------------------------


@dataclass
class Trial:
    """One design point, and everything that came back from it."""

    index: int
    params: dict[str, float]
    ok: bool
    digest: str = ""
    objectives: dict[str, float] = field(default_factory=dict)
    feasible: bool = True
    error: str = ""
    seconds: float = 0.0
    source: str = "evaluated"    # or "cached", "digest-cached"

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": TRIAL_SCHEMA,
            "index": self.index,
            "params": self.params,
            "ok": self.ok,
            "digest": self.digest,
            "objectives": self.objectives,
            "feasible": self.feasible,
            "error": self.error,
            "seconds": self.seconds,
            "source": self.source,
        }

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> "Trial":
        return cls(
            index=int(raw["index"]), params=dict(raw["params"]),
            ok=bool(raw["ok"]), digest=str(raw.get("digest") or ""),
            objectives={key: float(value)
                        for key, value in (raw.get("objectives") or {}).items()},
            feasible=bool(raw.get("feasible", True)),
            error=str(raw.get("error") or ""),
            seconds=float(raw.get("seconds") or 0.0),
            source=str(raw.get("source") or "evaluated"),
        )


def _key(params: dict[str, float]) -> str:
    return json.dumps(params, sort_keys=True)


class Evaluator:
    """Rebuilds a project at a parameter vector and scores the result."""

    def __init__(self, project: Path, objectives: Sequence[Objective], *,
                 specs: Sequence[ParameterSpec], out_root: Path,
                 cadex: Sequence[str], engine: str | None = None,
                 formats: str = "stl", keep: bool = False, wait: bool = True):
        self.project = Path(project).resolve()
        self.objectives = list(objectives)
        self.specs = {spec.name: spec for spec in specs}
        self.out_root = Path(out_root)
        self.cadex = list(cadex)
        self.engine = engine
        self.formats = formats
        self.keep = keep
        self.wait = wait
        self.by_params: dict[str, Trial] = {}
        self.by_digest: dict[str, dict[str, float]] = {}
        self.log_path = self.out_root / TRIAL_LOG
        self.count = 0
        self.rebuilds = 0
        # Here rather than in `run`, because each evaluation makes a
        # scratch directory *inside* this one and the class is usable on its
        # own -- which is how a caller drives a single design point without
        # writing a plan file at all.
        self.out_root.mkdir(parents=True, exist_ok=True)

    # -- the trial log ----------------------------------------------------

    def resume(self) -> int:
        """Read back a killed run's trials. Returns how many were recovered."""

        if not self.log_path.is_file():
            return 0
        recovered = 0
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            trial = Trial.from_json(json.loads(line))
            self.by_params[_key(trial.params)] = trial
            if trial.digest and trial.ok:
                self.by_digest.setdefault(trial.digest, trial.objectives)
            self.count = max(self.count, trial.index + 1)
            recovered += 1
        return recovered

    def _record(self, trial: Trial) -> None:
        self.by_params[_key(trial.params)] = trial
        if trial.digest and trial.ok:
            self.by_digest.setdefault(trial.digest, trial.objectives)
        self.out_root.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(trial.to_json(), sort_keys=True) + "\n")

    # -- one design point --------------------------------------------------

    def snap(self, params: dict[str, float]) -> dict[str, float]:
        return {name: self.specs[name].snap(value)
                for name, value in sorted(params.items())}

    def evaluate(self, params: dict[str, float]) -> Trial:
        params = self.snap(params)
        cached = self.by_params.get(_key(params))
        if cached is not None:
            return cached

        index = self.count
        self.count += 1
        started = time.monotonic()
        directory = Path(tempfile.mkdtemp(prefix="cadex-search-",
                                          dir=str(self.out_root)))
        try:
            command = list(self.cadex) + [
                "params", "--project", str(self.project),
                "--out", str(directory), "--format", self.formats, "--json",
            ]
            if self.wait:
                command.append("--wait")
            if self.engine:
                command += ["--engine", self.engine]
            for name, value in params.items():
                command += ["--set", f"{name}={value:g}"]

            result = subprocess.run(command, capture_output=True, text=True,
                                    check=False, timeout=3600)
            trial = self._score(index, params, result, directory, started)
        finally:
            if not self.keep:
                shutil.rmtree(directory, ignore_errors=True)
        self._record(trial)
        return trial

    def _score(self, index: int, params: dict[str, float],
               result: subprocess.CompletedProcess[str], directory: Path,
               started: float) -> Trial:
        if result.returncode == _EXIT_REFUSED:
            # Not a failure of the search: a refused script is a region of
            # the space the model cannot build, which is information.
            return Trial(index=index, params=params, ok=False,
                         error=_refusal(result), seconds=time.monotonic() - started,
                         source="refused")
        if result.returncode != 0:
            return Trial(index=index, params=params, ok=False,
                         error=f"cadex exited {result.returncode}: "
                               f"{_refusal(result)}",
                         seconds=time.monotonic() - started, source="failed")

        # `docs/CLI.md` §3: with `--json` the whole of stdout is the
        # envelope, and it is indented across many lines -- progress goes to
        # stderr, so nothing else is in here. Reading only the last line
        # (which is what this tree's own tools emit) parses a closing brace.
        if not result.stdout.strip():
            return Trial(index=index, params=params, ok=False,
                         error="cadex printed no envelope on stdout",
                         seconds=time.monotonic() - started, source="failed")
        envelope = json.loads(result.stdout)
        digest = str(envelope.get("digest") or "")
        outputs = {str(item.get("name")): dict(item.get("files") or {})
                   for item in envelope.get("outputs") or []}

        self.rebuilds += 1
        known = self.by_digest.get(digest) if digest else None
        if known is not None:
            # Two different parameter vectors, the same model. The rebuild
            # already happened -- the objective is what this saves, and when
            # the objective is an FEA solve that is the whole cost.
            trial = Trial(index=index, params=params, ok=True, digest=digest,
                          objectives=dict(known),
                          seconds=time.monotonic() - started,
                          source="digest-cached")
            trial.feasible = self._feasible(trial.objectives)
            return trial

        context = Context(params=params, digest=digest, out_dir=directory,
                          outputs=outputs, envelope=envelope)
        scores: dict[str, float] = {}
        for objective in self.objectives:
            try:
                scores[objective.name] = float(objective.evaluate(context))
            except Exception as error:                      # noqa: BLE001
                return Trial(index=index, params=params, ok=False, digest=digest,
                             objectives=scores,
                             error=f"objective {objective.name!r}: {error}",
                             seconds=time.monotonic() - started,
                             source="objective-failed")
        trial = Trial(index=index, params=params, ok=True, digest=digest,
                      objectives=scores, seconds=time.monotonic() - started)
        trial.feasible = self._feasible(scores)
        return trial

    def _feasible(self, scores: dict[str, float]) -> bool:
        return all(objective.satisfied(scores.get(objective.name, float("nan")))
                   for objective in self.objectives)


def _refusal(result: subprocess.CompletedProcess[str]) -> str:
    """The sentence the engine refused with.

    A refusal still carries the `--json` envelope, with `error` in place of
    `notes` (`docs/CLI.md` §3), so the whole of stdout is the thing to read.
    Falls back to the tail of whichever stream has anything, because a
    refusal that arrives without an envelope is still worth reporting.
    """

    if result.stdout.strip():
        try:
            error = json.loads(result.stdout).get("error")
        except json.JSONDecodeError:
            error = None
        if error:
            return json.dumps(error) if isinstance(error, dict) else str(error)
    return (result.stderr or result.stdout).strip()[-500:]


# ---------------------------------------------------------------------------
# Where to look next.
# ---------------------------------------------------------------------------


def grid_points(specs: Sequence[ParameterSpec], levels: int) -> list[dict[str, float]]:
    """Full factorial. The honest baseline, and often the right answer.

    For three parameters at five levels that is 125 points, which at the
    measured 0.7 s a rebuild is under two minutes -- and unlike every
    cleverer thing here it tells you the shape of the whole space rather
    than a path through it.
    """

    axes = []
    for spec in specs:
        if not spec.bounded:
            raise SearchError(
                f"Parameter {spec.name!r} declares no min/max, so a grid has "
                "no range to walk. Declare bounds in `num(...)` or name only "
                "the bounded parameters in the plan."
            )
        axes.append(np.linspace(spec.minimum, spec.maximum, max(2, levels)))
    return [
        {spec.name: float(value) for spec, value in zip(specs, combination)}
        for combination in itertools.product(*axes)
    ]


def random_points(specs: Sequence[ParameterSpec], count: int,
                  seed: int) -> list[dict[str, float]]:
    """A Latin hypercube: one sample per stratum per axis, then shuffled.

    Better spread than independent uniforms at the same count, and it is
    four lines of numpy rather than a dependency.
    """

    rng = np.random.default_rng(seed)
    columns = []
    for spec in specs:
        if not spec.bounded:
            raise SearchError(f"Parameter {spec.name!r} declares no min/max.")
        strata = (np.arange(count) + rng.random(count)) / count
        rng.shuffle(strata)
        columns.append(spec.minimum + strata * (spec.maximum - spec.minimum))
    return [
        {spec.name: float(column[row]) for spec, column in zip(specs, columns)}
        for row in range(count)
    ]


def _scalarise(objectives: Sequence[Objective], scores: dict[str, float],
               weights: dict[str, float] | None) -> float:
    """One number out of several, for the search backends that need one.

    A weighted sum of the objectives in their declared direction, with a
    large finite penalty for an infeasible or failed point rather than an
    infinity -- an optimiser handed `inf` learns nothing about which way to
    move, and one handed `nan` usually stops.
    """

    total = 0.0
    for objective in objectives:
        value = scores.get(objective.name)
        if value is None or not math.isfinite(value):
            return 1.0e12
        weight = (weights or {}).get(objective.name, 1.0)
        total += weight * (value if objective.direction == "min" else -value)
        if not objective.satisfied(value):
            total += 1.0e9
    return total


def pareto_front(objectives: Sequence[Objective],
                 trials: Sequence[Trial]) -> list[Trial]:
    """The non-dominated feasible points, in plain numpy.

    Works for every backend, because it is computed from the evaluated set
    rather than produced by the search. That is what lets `grid` and
    `random` answer a genuinely multi-objective question without any of the
    multi-objective machinery: mass against peak stress against whatever
    else conflicts, all read off the points you already paid for.
    """

    usable = [trial for trial in trials
              if trial.ok and trial.feasible
              and all(math.isfinite(trial.objectives.get(objective.name, float("nan")))
                      for objective in objectives)]
    if not usable:
        return []
    matrix = np.array([
        [trial.objectives[objective.name]
         * (1.0 if objective.direction == "min" else -1.0)
         for objective in objectives]
        for trial in usable
    ], dtype=float)
    keep = []
    for index in range(len(usable)):
        others = np.delete(matrix, index, axis=0)
        if len(others) and np.any(
                np.all(others <= matrix[index], axis=1)
                & np.any(others < matrix[index], axis=1)):
            continue
        keep.append(usable[index])
    return keep


def run_search(plan: dict[str, Any], evaluator: Evaluator,
               specs: Sequence[ParameterSpec],
               objectives: Sequence[Objective],
               announce: Callable[[str], None]) -> list[Trial]:
    """Drive one of the backends and return every trial it produced."""

    search = plan.get("search") or {}
    kind = str(search.get("kind") or "grid")
    weights = search.get("weights")

    if kind == "grid":
        points = grid_points(specs, int(search.get("levels") or 5))
        announce(f"grid: {len(points)} design points")
        return [evaluator.evaluate(point) for point in points]

    if kind == "random":
        points = random_points(specs, int(search.get("count") or 50),
                               int(search.get("seed") or 0))
        announce(f"random: {len(points)} design points")
        return [evaluator.evaluate(point) for point in points]

    if kind == "scipy":
        # Zero new dependencies, and the right first thing to reach for:
        # prove the loop before adding a driver to it.
        from scipy.optimize import differential_evolution

        bounds = [(spec.minimum, spec.maximum) for spec in specs]
        if any(bound[0] is None or bound[1] is None for bound in bounds):
            raise SearchError("A scipy search needs every parameter bounded.")
        trials: list[Trial] = []

        def _cost(vector: Iterable[float]) -> float:
            point = {spec.name: float(value)
                     for spec, value in zip(specs, vector)}
            trial = evaluator.evaluate(point)
            trials.append(trial)
            return _scalarise(objectives, trial.objectives, weights)

        announce("scipy: differential evolution")
        differential_evolution(
            _cost, bounds, seed=int(search.get("seed") or 0),
            maxiter=int(search.get("iterations") or 10),
            popsize=int(search.get("population") or 8),
            polish=False, init="sobol", tol=0.0,
        )
        return trials

    if kind in {"optuna", "pymoo"}:
        raise SearchError(
            f"The {kind!r} backend is not built. It is deliberately not a "
            "dependency yet: `grid`, `random` and `scipy` need nothing that "
            "is not already installed, and which of Optuna and pymoo earns "
            "a pin is a question to settle with a measurement from those "
            "three (docs/STRUCTURAL.md S1)."
        )

    raise SearchError(
        f"Unknown search kind {kind!r}. This reads: grid, random, scipy."
    )


# ---------------------------------------------------------------------------
# The plan, the run and the report.
# ---------------------------------------------------------------------------


def _cadex_command(plan: dict[str, Any], override: str | None) -> list[str]:
    if override:
        return [override]
    declared = plan.get("cadex")
    if declared:
        return [str(declared)]
    shim = Path(__file__).resolve().parents[1] / "cadex"
    if shim.is_file():
        return [str(shim)]
    found = shutil.which("cadex")
    if found:
        return [found]
    raise SearchError(
        "No `cadex` shim found. Pass `--cadex /path/to/cadex`, or run this "
        "from a checkout that has one at the repository root."
    )


def run(plan: dict[str, Any], plan_dir: Path, out: Path, *,
        cadex: str | None = None, resume: bool = False, keep: bool = False,
        announce: Callable[[str], None] = lambda text: None) -> dict[str, Any]:
    if str(plan.get("schema") or "") != PLAN_SCHEMA:
        raise SearchError(
            f"The plan declares schema {plan.get('schema')!r}, and this "
            f"reads {PLAN_SCHEMA!r}."
        )
    project = (plan_dir / str(plan["project"])).resolve()
    every = read_design_space(project)
    chosen = plan.get("parameters")
    if chosen:
        by_name = {spec.name: spec for spec in every}
        missing = [name for name in chosen if name not in by_name]
        if missing:
            raise SearchError(
                f"The plan searches {', '.join(missing)}, which this project "
                f"does not declare. It declares: "
                f"{', '.join(sorted(by_name))}."
            )
        specs = [by_name[str(name)] for name in chosen]
    else:
        specs = every

    objectives = build_objectives(plan, plan_dir)
    formats = str(plan.get("format") or "stl")
    evaluator = Evaluator(
        project, objectives, specs=every, out_root=out,
        cadex=_cadex_command(plan, cadex), engine=plan.get("engine"),
        formats=formats, keep=keep,
    )
    out.mkdir(parents=True, exist_ok=True)
    recovered = evaluator.resume() if resume else 0
    if recovered:
        announce(f"resumed {recovered} trials from {evaluator.log_path}")
    elif evaluator.log_path.is_file():
        raise SearchError(
            f"{evaluator.log_path} already holds trials from an earlier run. "
            "Pass --resume to continue it, or point --out somewhere else. "
            "Appending a second run's trials to it silently would make the "
            "report a mixture of two searches."
        )

    started = time.monotonic()
    trials = run_search(plan, evaluator, specs, objectives, announce)
    wall = time.monotonic() - started

    # Everything ever evaluated, not only what this backend asked for: on a
    # resumed run the earlier trials are results too.
    everything = list(evaluator.by_params.values())
    front = pareto_front(objectives, everything)
    feasible = [trial for trial in everything if trial.ok and trial.feasible]
    warnings: list[str] = []
    refused = [trial for trial in everything if trial.source == "refused"]
    if refused:
        warnings.append(
            f"{len(refused)} design points were refused by the engine. Those "
            "are regions the script cannot build, not failures of the search."
        )
    failed = [trial for trial in everything
              if not trial.ok and trial.source != "refused"]
    if failed:
        warnings.append(
            f"{len(failed)} design points failed for a reason that is not a "
            f"refusal; the first is: {failed[0].error[:300]}"
        )
    if not feasible:
        warnings.append(
            "No design point satisfied every declared constraint, so there "
            "is no front to read."
        )
    if any(spec.step for spec in specs):
        warnings.append(
            "Design points are snapped onto each parameter's declared "
            "`step`, so a search cannot report a value a slider could not "
            "reach."
        )

    def _best(objective: Objective) -> dict[str, Any] | None:
        candidates = [trial for trial in feasible
                      if math.isfinite(trial.objectives.get(objective.name, float("nan")))]
        if not candidates:
            return None
        pick = (min if objective.direction == "min" else max)(
            candidates, key=lambda trial: trial.objectives[objective.name])
        return {"params": pick.params, "objectives": pick.objectives,
                "digest": pick.digest, "index": pick.index}

    return {
        "schema": REPORT_SCHEMA,
        "plan": {
            "project": str(project),
            "parameters": [
                {"name": spec.name, "min": spec.minimum, "max": spec.maximum,
                 "step": spec.step, "unit": spec.unit, "default": spec.default}
                for spec in specs
            ],
            "objectives": [
                {"name": objective.name, "direction": objective.direction,
                 "limit": objective.limit, "limit_kind": objective.limit_kind}
                for objective in objectives
            ],
            "search": plan.get("search") or {"kind": "grid"},
        },
        "trials": {
            "total": len(everything),
            "rebuilds": evaluator.rebuilds,
            "parameter_cache_hits": len(everything) - evaluator.rebuilds
            if evaluator.rebuilds <= len(everything) else 0,
            "digest_cache_hits": sum(1 for trial in everything
                                     if trial.source == "digest-cached"),
            "refused": len(refused),
            "failed": len(failed),
            "feasible": len(feasible),
            "resumed": recovered,
            "log": str(evaluator.log_path),
        },
        "best": {objective.name: _best(objective) for objective in objectives},
        "pareto_front": [
            {"params": trial.params, "objectives": trial.objectives,
             "digest": trial.digest, "index": trial.index}
            for trial in sorted(front, key=lambda trial: trial.index)
        ],
        "wall_time_s": wall,
        "warnings": warnings,
        "note": (
            "Objectives that call the stress solver ran on ONE grid, not a "
            "refinement sweep, so they rank designs against each other and "
            "are not converged numbers. Re-run the design you pick through "
            "analysis/cadex_stress.py properly."
        ),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "cadex_importable": stress._cadex_importable(),
    }


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="search.py",
        description="Sweep or optimise a project's declared parameters.")
    parser.add_argument("plan", type=Path, help=f"a {PLAN_SCHEMA} JSON file")
    parser.add_argument("--out", type=Path, required=True,
                        help="where the trial log and the report go")
    parser.add_argument("--cadex", default=None, help="path to the cadex shim")
    parser.add_argument("--resume", action="store_true",
                        help="continue the trial log already in --out")
    parser.add_argument("--keep", action="store_true",
                        help="keep each design point's exported files")
    parser.add_argument("--quiet", action="store_true")
    options = parser.parse_args(list(argv[1:]))

    def announce(text: str) -> None:
        if not options.quiet:
            print(text, file=sys.stderr)

    try:
        plan = json.loads(options.plan.read_text(encoding="utf-8"))
        report = run(plan, options.plan.resolve().parent, options.out,
                     cadex=options.cadex, resume=options.resume,
                     keep=options.keep, announce=announce)
    except (SearchError, stress.StressError) as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2

    for warning in report["warnings"]:
        print(f"warning: {warning}", file=sys.stderr)
    (options.out / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
