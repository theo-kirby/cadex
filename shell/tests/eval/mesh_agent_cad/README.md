# Part Design mode eval harness

Measures how well the Mesh agent's **Part Design** mode produces printable,
manifold CAD parts, end-to-end through a real `claude -p` backend.

> **This costs real API money and takes ~5-10 minutes per case.** It lives
> outside `tests/python/` on purpose: it is run by hand when tuning the CAD
> prompt overlay or the `mesh_cad` library, never in CI/CMake. The CI-safe
> mock tests are in `tests/python/bl_mesh_agent_cad.py`.

## Requirements

- A logged-in Claude Code install (`claude` on PATH or in a default location).
- A Mesh Blender build.

## Usage

```sh
tests/eval/mesh_agent_cad/runner.py --blender <path/to/blender>

# Just the flagship case, on a cheaper model:
tests/eval/mesh_agent_cad/runner.py --blender <path> \
    --cases two_stage_reduction --model claude-sonnet-4-6
```

The runner spawns one headless Blender per case
(`blender --background --factory-startup --python eval_blender.py -- --case <id>`),
each of which runs a single chat turn in `PART_DESIGN` mode with a 600 s
timeout and a 40-tool-call cap, then scores the resulting scene **locally**
(no LLM judging) and writes `results/<case>.json`. Afterwards the runner
aggregates `results/scorecard.json` and `results/scorecard.md`.

## Rubric (100 points per case)

| points | criterion |
|---|---|
| 15 | the turn completes (no backend error/timeout) |
| 15 | re-running `model.rebuild()` reproduces the same parts (determinism) |
| 30 | fraction of parts that are manifold, watertight, self-intersection-free |
| 15 | mesh part count within the case's expected range |
| 15 | fraction of the case's required parameter ids declared |
| 5  | assembly fits the case's bbox envelope, no undersized/degenerate parts |
| 5  | `export_stl` smoke test succeeds |

Per-case results include the rubric breakdown, per-part geometry stats, the
final model script, the tool-call count, wall time and the transcript tail —
enough to diagnose *why* a case lost points without rerunning it.

## Cases

See `cases.py`. `two_stage_reduction` (2-stage gear reduction plus
counterbored backplate) is the flagship scenario the mode was built around;
the others cover gears, brackets, enclosures with fits, press-fit features,
nut pockets and small clips.

## Workflow for prompt/library tuning

1. Get a baseline: run all cases, keep `results/` (e.g. copy to
   `results-baseline/`).
2. Change the `CAD_OVERLAY` text in `modes.py` and/or `mesh_cad` ergonomics
   in `cad_api.py`.
3. Re-run and diff the scorecards. The mock tests keep the overlay's worked
   example honest (it is extracted from the overlay and executed verbatim);
   this harness tells you whether the change actually helps the model.
