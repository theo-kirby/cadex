---
node_id: fd5c0415-3fff-5fc8-bd2a-828a2cda6d8e
slug: jolly-shore-2511
title: 'S1: the search reads the space off disk and drives the CLI, one process at a time'
created_at: '2026-08-10T13:13:52+00:00'
parents:
- fair-beacon-5964
summary: ''
---
## What

S1 closed. `analysis/search.py` sweeps or optimises a project's declared
parameters against declared objectives, with no model in the loop (ADR-142,
`docs/STRUCTURAL.md` §4, ROADMAP Phase 16).

One new file and one new suite
(`src/Mod/cadex/cadex_tests/test_analysis_search.py`, 19 tests). No engine
code, no protocol change, no payload bytes, and no CLI change: it uses
`cadex params`, `--out`, `--format`, `--json` and `--wait` exactly as
`docs/CLI.md` documents them.

## Why

`docs/CLI.md` §1 and `docs/VISION.md`:151-158 describe this loop as the
reason `cli/` exists at all — an expensive model turn authors a parametric
script once, and a cheap loop sweeps its parameters while an external
simulator feeds numbers back. The outer half shipped with Phase 9. S1 is the
part that decides where to look next, and it is what turns S0's number into
the two jobs that motivated the vertical: lighter printed parts, and legs
whose mass feeds back into the dynamics.

## Method

**The design space is read off `<project>/script.json`, not asked for.**
`params()`/`num()`'s collected specs are cached there with `min`, `max`,
`step` and `unit` — which is what `inspect scope="script"` serves them out
of — so reading the bounds is a file read that needs nothing running.

**An evaluation is `./cadex params --set k=v --out DIR --json` as a
subprocess**, not an import of `cli/cadex_cli/client.py`. Importing is
allowed (`cli/` is engine-side and LGPL, so no boundary is crossed, and the
plan named it as an option the `cdx-rl` location did not have) and was still
the wrong choice: driving the CLI keeps `analysis/` importing nothing from
the engine, reporting `cadex_importable` false and holding no view on the
protocol, so S1 costs the tree none of what ADR-141 bought. It also buys
crash isolation per evaluation.

**Two caches, and they are not the same cache.** One on the parameter
vector, which skips the rebuild. One on the **`digest`**, which skips the
*objective* — two different parameter vectors can produce the same model
and the digest is the only thing that says so. `digest` rather than the
files for the reason `docs/CLI.md`:126-131 gives: STEP embeds a wall-clock
timestamp, so two exports of an identical model differ byte for byte across
a second boundary.

**One fixed grid inside a search.** This looks like it contradicts ADR-141
and is the opposite: S0's sweep exists because a single grid is not a
*measurement*, and a search does not want a measurement, it wants a
consistent **ranking**. A fixed grid gives every candidate the same
discretisation bias; a per-candidate adaptive sweep would let the
discretisation move between two designs being compared. `refine` defaults to
1 and the report always carries a `note` saying so.

Also: every design point is snapped into range and onto its declared `step`,
so a search cannot report a value a slider could not reach; the Pareto front
is computed from the evaluated set rather than produced by the search; a
constraint marks a point infeasible rather than dropping it; and a design
point the engine *refuses* is counted and carried past.

Commands:

```
pixi run python analysis/search.py plan.json --out ./sweep
pixi run python -m pytest src/Mod/cadex/cadex_tests/test_analysis_search.py
pixi run python -m pytest src/Mod/cadex/cadex_tests
```

## Result

`test_analysis_search.py` — **19 passed**. Full engine suite — **1776
passed, 22 skipped** (1757 before). Eleven of the 19 need no engine; eight
drive a **real project through the real CLI**, because the claim under test
is that the loop closes and a mock cannot fail the way the loop can. They
skip without a built engine, the bar `cli/tests` sets.

**Measured, on a three-parameter bracket.** One rebuild is **0.7 s**. A 4x4
grid over two parameters, mass against p99 von Mises with a 12 MPa cap — 16
real rebuilds and 16 FEA solves — ran end to end in **12.7 s** and produced
a five-point front:

```
wall=2.00 rib= 8.50 ->  17.11 g,  6.42 MPa
wall=2.00 rib=14.50 ->  26.04 g,  2.56 MPa
wall=2.00 rib=20.00 ->  34.22 g,  1.40 MPa
wall=5.50 rib=14.50 ->  33.85 g,  2.41 MPa
wall=5.50 rib=20.00 ->  42.04 g,  1.31 MPa
```

The physics is the physics: a deeper rib is stiffer and heavier, so mass and
peak stress genuinely conflict and the answer is a front rather than a
winner. That is the case S1 was specified for.

The two caches are pinned separately because they are separate claims. The
parameter cache: the same point twice, one rebuild — and 4.1 mm snapping to
4.0 mm is the *same* point. The digest cache: a declared-but-unused
parameter moved between two design points gives **two rebuilds, one digest
and one objective evaluation**.

The refusal path is pinned with a script whose plate thickness reaches zero
inside its own declared range: three design points, at least one refused,
zero counted as failures, and the buildable points still make a front.

**Two bugs, both caught by running the thing rather than by reading it.**

1. **The CLI's `--json` envelope is pretty-printed across the whole of
   stdout**, and this file read only the last line — which is the convention
   `analysis/`'s own tools follow, and which here parses a closing brace.
   `docs/CLI.md` §3 is unambiguous (progress to stderr, the report to
   stdout); the mistake was assuming one tree's output discipline was the
   other's. All 16 design points failed identically, which is the good
   version of getting a contract wrong.
2. `Evaluator` created each design point's scratch directory *inside* an
   output root that only `run()` created, so the class was unusable on its
   own — which is how a caller drives a single design point without writing
   a plan file. Fixed in the class rather than in the caller.

**Deliberately not built.** Optuna and pymoo are still not dependencies.
`grid` (full factorial), `random` (a Latin hypercube in four lines of numpy)
and `scipy` (differential evolution) need nothing that is not already
installed, and asking for either of the other two refuses with the reason.
Both arguments turned out to be answerable for free: Optuna's case was
ask/tell suiting a subprocess evaluator and SQLite giving a free resume —
the resume here is a JSONL you can read with `tail`; pymoo's case was a real
Pareto front — the front here is computed from the evaluated points, so
`grid` and `random` produce one with no multi-objective machinery. Which one
earns a pin is now a question a measurement can answer, which is the state
it should have been in before either was added.

**Parallel evaluation** is not built either: the project takes a lock, so
two rebuilds of one project cannot overlap and parallelism means N copies of
the project. At 0.7 s a rebuild that is 500 design points in six minutes.
The report carries per-trial wall time, which is what will say when it is
worth it.

**One property of `analysis/` was lost and is stated rather than glossed.**
`search.py` spawns a process where the other three files only read files, so
"it never spawns an engine" is now true of three files out of four.
`analysis/README.md` and ADR-142 both say so, because the tree's discipline
is what makes it auditable.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: be7ff63d8766f3cede9545152af00a5e01c06fe8

## State Impact

- target: kind-marsh-2645 — S1 closed (ADR-142): analysis/search.py sweeps or optimises a project's declared parameters with no model in the loop. Status stays working; S2 and S3 remain the open half. Claims: the design space is read off <project>/script.json rather than asked for, so the bounds need nothing running; an evaluation is ./cadex params --json as a SUBPROCESS rather than an import of cli/cadex_cli/client.py, which keeps analysis/ importing nothing from the engine and buys crash isolation per evaluation; two distinct caches, one on the parameter vector (skips the rebuild) and one on the digest (skips the objective, which is the expensive half when it is an FEA solve); the Pareto front is computed from the evaluated set, so grid and random answer a multi-objective question with no multi-objective machinery; a refused design point is counted as information about the space rather than a failure. Measured: 0.7 s a rebuild, and a 16-point grid with an FEA solve on every point in 12.7 s, giving a five-point mass-vs-stress front. 19 tests, 8 of them driving a real project through the real CLI. Negative knowledge: inside a search the stress objective runs on ONE fixed grid, not S0's refinement sweep, because a search needs a consistent ranking rather than a converged number; the CLI's --json envelope is pretty-printed across the whole of stdout, so reading only its last line parses a closing brace; and analysis/ no longer has the property that nothing in it spawns a process. Optuna and pymoo remain deliberately unpinned — both arguments for them turned out to be answerable for free.
