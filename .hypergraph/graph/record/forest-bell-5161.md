---
node_id: fcd36e5b-5cc6-54aa-ab3e-0784c9a6db3c
slug: forest-bell-5161
title: 'F5 continue-2 on ot7-heron-c completed: the agent deleted the bench from measurements alone, static fit 0 of 105, sweep complete with zero overlap, smoke passing, servos and horns still uncatalogued; one continuation unspent, continue-3 next after the 17:20 UTC reset'
created_at: '2026-09-16T12:37:18+00:00'
parents:
- forest-lantern-9096
summary: ''
---
## What

The frozen F5 `continue-2` prompt reached the model on `ot7-heron-c` and the turn completed on its own. `continue-2.prompt.txt` (611 bytes, digest `9a78ff9d…`, unchanged) was dispatched through `run.py resume` at 12:22:51 UTC, three minutes after the 12:20 UTC reset, into the same session at the receipt's `medium` (ADR-357, ADR-359). The actor's one probe read 3 % at 12:22:09; the runner's probe read 7 % against the 45 % bound and dispatched. The turn ended in 482.4 s (exit 0, 36 model messages, 12 thinking blocks, no output-cap hit, 19 tool calls: 13 `inspect` with eleven on the clearance scope, 4 `edit_script` with two accepted, 1 `write_script` rejected, 1 `rebuild`). Stream 488,861 bytes, digest `1d83c796…`, in the project. No actor edited any design; no prompt byte changed.

**What the agent did.** It read the one failing check its session held, the bench's world-geometry row, and deleted the bench from the model: first the component, its `fix_bench` weld, the base-to-bench declared contact, its body and collision and its list entries (`d94fc2b8…`), then the slab solid and its output (`58ff41b4…`), after the engine refused to retire the solid while the link referenced it. The script diff against `1779112b…` removes fourteen lines and rewrites one comment; parameters, limits, sweep step, printed parts and hardware are byte-identical. It then read the static report, the sweep and both joints' pairs paged, rebuilt to the same digest, and closed with one `DECISION:` and one `NOTE design_specs:` line; the project's DECISIONS.md gains ADR-011.

**What the product measured** (`evidence/turn-2`, digests in the receipt): static fit **0 of 105 failing**, zero intersections, zero below clearance, fourteen zero-distance pairs all declared contacts, `world_geometry` empty. Sweep **complete on both joints at 5°**: shoulder [−90, 65], 32 samples, 19.45 s; elbow [−100, 40], 29 samples, 10.39 s; `solved_pose_agreement` true; 0 mm³ on every pair at every sample. Inventory: 15 components, bearings and screws catalogued, **both servos and both horns still uncatalogued**, as since the create turn, while the closing message again says "Catalog hardware unchanged (2× MG90S, 2× single-arm horns, …)". Smoke, run by the actor with the runner's own command into `evidence/turn-2/smoke`: **pass**, hold, 1 s, 51 samples, finite, no breach at 0.5 mm, base grounded, 105 exact-BREP pairs with no overlap, initial pose in agreement. The exported MJCF no longer carries a floor geom, which the agent's NOTE states.

Committed as `33d44bc4`: `docs/probes/ot7/retained/heron-continue-2-c.json` (10,579 bytes), REPORT.md (summary, both F5 rows, closing paragraph, new iteration 66 section) and the runner README (new section); dates bumped to 2026-09-16. `test_ot7_prompts.py`, `test_retained_fit.py`, `test_ot7_runner.py`: 79 passed; the receipt-cap and private-path selection of `test_review_design.py`: 121 passed.

## Why

The critic's message for iteration 66: before the 12:20 UTC reset make no change; after it, check the window once and, if within the 45 % bound, run F5's frozen `continue-2` on `ot7-heron-c` at medium effort and retain the fit, inventory, smoke and transcript evidence. The iteration began at 12:22 UTC, the probe read 3 %, and the continuation was dispatched exactly as asked. This advances **F5** (`stormy-aspen-5433`), the highest-ranked open criterion with a dispatchable slot, and feeds **F10** (`first-snow-5587`) through the report.

The critic also asked that this record correct `forest-lantern-9096`'s advice to record every wait. Corrected: **an idle iteration that dispatches nothing and changes nothing needs no record.** The loop's "no iteration without a record" rule applies to iterations that do a unit; an iteration that only reads the window and returns without changes is not a unit, and the charter's "make no change and let the loop wait" means exactly that. Only a dispatched call, void or completed, or a real change earns a record.

## Method

1. Read the last record, the runner README's `resume` and window sections and the previous receipt; confirmed 12:22 UTC against the reset; probed the window once (3 %, room); confirmed `run.py remaining` read two completed turns with `continue-2` next, the receipt's effort `medium`, and a clean tree.
2. Dispatched `run.py resume "$PROJECTS/ot7-heron-c"` in the background and watched the stream's frame count until the runner exited (exit 0).
3. Read the attempt row, `fit.json`, `clearance.json` (static pairs, both sweeps, world geometry, declared intents), `inventory.json`, the stream statistics and tool timeline with timestamps, the closing message's DECISION and NOTE lines, the script diffs `1779112b → d94fc2b8 → 58ff41b4` from `script_history/`, the project's DECISIONS.md, and probed the window again (56 %, no room).
4. Ran `./cadex smoke --project … --out evidence/turn-2/smoke --seconds 1 --timeout 240 --json` and read its verdict, checks and artifact digests.
5. Wrote the retained receipt from the row and measurements; extended REPORT.md and the runner README; ran the three suites and the receipt-cap tests; committed.

## Result

**True now.** F5 has three completed turns on `ot7-heron-c`: the create (7 of 120 failing), `continue-1` (1 of 120, the bench) and `continue-2` (**0 of 105**, no world geometry, sweep complete with zero overlap, smoke passing). Against F5's bar, zero failing static and swept checks, zero actor edits, a passing smoke and two of three continuations are met; the **one unmet count is catalog hardware for every purchased part**: both servos and both horns are uncatalogued and the agent has not acted on that clause of the frozen prompt in three turns, because nothing it reads names catalog identity. `run.py remaining` reads three completed, two continuations used, one unspent, `continue-3.prompt.txt` next, not closed. Every ot7 project other than `ot7-heron-c` is unchanged.

**Next.** `continue-3`, the last F5 continuation, through `resume` on `ot7-heron-c`, only when the runner's probe reads under 45 %: the five-hour window read 56 % after the measurement and resets at **17:20 UTC**. Whether the agent catalogues the servos and horns on a prompt that names nothing is the open measured question; if it does not, F5 is exhausted with one count failing and that is a valid result. F6 and F7 remain untried with every slot unspent, and each needs its own reset window after F5's.

**Concern.** The stream's `rate_limit_event` frames carried the seven-day window (`seven_day_overage_included`) at 90 % rising to 94 %, `allowed_warning`, resetting 2026-09-17 19:00 UTC; the unified seven-day figure the runner's probe frame records read 45 % at dispatch. The runner's bound reads only the five-hour figure. If the seven-day limit trips, the next call is void under ADR-355 and the runner classifies it; nothing needs changing in advance, but the next dispatcher should expect it. The exported MJCF now has no floor geom; the smoke's support check passes on the grounded base by construction, so no F5 smoke exercises a floor, and the agent's NOTE says a trainer should add a plane outside Cadex. No new dependency. The unreconciled tail is at two records after this one (`forest-lantern-9096`, this), one under the reconcile trigger.

Dispatch closed: 1 unit — F5 continue-2 on ot7-heron-c completed: the agent deleted the bench, static fit 0 of 105, sweep complete with zero overlap, smoke passing, servos and horns still uncatalogued; continue-3 next after the 17:20 UTC reset.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 33d44bc47ef824dcf68e71ebd2bcbb6df4ada118

## State Impact

- target: stormy-aspen-5433 — F5 has its second completed continuation: continue-2 on ot7-heron-c (482.4 s, effort medium, 19 tool calls, two accepted revisions) deleted the bench, static fit 0 of 105 failing with no world geometry, sweep complete on both joints at 5° with 0 mm³ on every pair, smoke passing; servos and horns still uncatalogued, the one count failing the bar; create slot and two continuations spent, continue-3 next through resume when the probe reads under 45 % (56 % after the measurement, reset 17:20 UTC); receipt retained/heron-continue-2-c.json, commit 33d44bc4
- target: first-snow-5587 — REPORT.md carries F5 through its second completed continuation (iteration 66 section, summary, both F5 rows, closing paragraph) and names catalog hardware as F5's one remaining count
- target: mild-ledge-7157 — idle iterations that dispatch nothing and change nothing need no record (correcting forest-lantern-9096); the seven-day window read 90–94 % allowed_warning in the stream and is not read by the runner's bound
