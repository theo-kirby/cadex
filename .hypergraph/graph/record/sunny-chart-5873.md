---
node_id: fa33d77f-685d-519f-8be8-7d33d3bdc199
slug: sunny-chart-5873
title: 'F5 continue-3 on ot7-heron-c completed with no edit: static fit 0 of 105, sweep complete with zero overlap, the runner''s smoke passing, servos and horns still uncatalogued; F5 exhausted with every count of its bar met except catalog hardware'
created_at: '2026-09-16T14:00:14+00:00'
parents:
- restless-gate-7062
summary: ''
---
## What

The frozen F5 `continue-3` prompt reached the model on `ot7-heron-c` and the turn completed on its own, exhausting F5. `continue-3.prompt.txt` (732 bytes, digest `0814d73f…`, unchanged) was dispatched through `run.py resume` at 13:51:42 UTC into the same session at the receipt's `medium` (ADR-357, ADR-359). This was the first dispatch after the owner refreshed the account (ADR-361, `restless-gate-7062`): the actor's one probe read 4 % at 13:51, the runner's probe read 7 % against the 45 % bound and dispatched; the five-hour reset moved from 17:20 to 18:50 UTC and the seven-day window that continue-2's stream had flagged at 90–94 % read 0–4 %. The turn ended in 142.9 s (exit 0, 12 model messages, 5 thinking blocks, no output-cap hit, 6 tool calls: 5 `inspect` all on the clearance scope, 1 `rebuild`). Stream 188,093 bytes, digest `d051c2f9…`, in the project. No actor edited any design; no prompt byte changed.

**What the agent did.** It read the static report, paged its 105 pairs at 50, 50 and 5, read the sweep block for both joints, concluded that a report naming zero failing checks calls for no change, re-submitted the unchanged script through `rebuild` (re-accepted at `58ff41b4…`, digest `2c42c943…` reproduced) and closed with one `DECISION:` and one `NOTE design_specs:` line; the project's DECISIONS.md gains ADR-012. Script digest `91ace2bb…`, `fit.json` and `inventory.json` are byte-identical to turn-2; `clearance.json` differs only in sweep timings.

**What the product measured** (`evidence/turn-3`, digests in the receipt): static fit **0 of 105 failing**, fourteen zero-distance pairs all declared contacts, `world_geometry` empty. Sweep **complete on both joints at 5°**: shoulder [−90, 65], 32 samples, 19.60 s; elbow [−100, 40], 29 samples, 10.29 s; agreement true; 0 mm³ on every pair at every sample. Inventory: 15 components, bearings and screws catalogued, **both servos and both horns still uncatalogued**, while the closing message says "all twelve purchased parts are catalog parts (2× MG90S servo, 2× single-arm horn, …)". The runner wrote `status: exhausted`, `slots_spent: 4`, `next_prompt: null`, then ran its own smoke into `evidence/smoke`: **pass**, hold, 1 s, 51 samples, finite, no breach at 0.5 mm, base grounded, 105 exact-BREP pairs with no overlap, initial pose in agreement; the trace and geometry digests equal the actor's turn-2 smoke, so the simulation reproduces exactly. The window read 38 % at the last stream frame and 41 % after the measurement.

Committed as `7e171bc7`: `docs/probes/ot7/retained/heron-continue-3-c.json` (10,644 bytes), REPORT.md (summary, the attempts row, the F5 checks row, the F10 section, a new iteration 72 section) and the runner README (new section). `test_ot7_runner.py`, `test_retained_fit.py`, `test_ot7_prompts.py`: 79 passed; the receipt-cap and private-path selection of `test_review_design.py`: 121 passed. No machine path in any committed file.

## Why

The critic left no message. The standing instruction from `neat-reef-5625` and `forest-bell-5161`: once `run.py window` reads at or under 45 %, the first action is `run.py resume` on `ot7-heron-c` for the frozen `continue-3` at `medium` with no catalog feedback, and the result is retained whether or not the servos and horns become catalogued. The window read 4 % at the start of this iteration, so that is the unit. It advances **F5** (`stormy-aspen-5433`), the highest-ranked open criterion with a dispatchable slot, to its exhausted measured result, and feeds **F10** (`first-snow-5587`) through the report. Two housekeeping facts: the unreconciled tail was one node (`restless-gate-7062`) at the start, so no reconcile was due; and `neat-reef-5625`'s expectation of a 17:20 UTC reset is superseded by the owner's account refresh, which is why a design turn fit at 13:51.

## Method

1. Read `.ouroboros/AGENTS.md`, the last three records, the runner README's resume, window and iteration-66 sections and the continue-2 receipt; confirmed a clean tree and the tail at one.
2. `run.py window`: 4 %, allowed, reset 18:50 UTC, room. `run.py remaining` on `ot7-heron-c`: 3 completed, 2 continuations used, `continue-3` next, not closed.
3. Dispatched `run.py resume "$PROJECTS/ot7-heron-c"` in the background and waited for the runner to exit (about three minutes, including its own smoke).
4. Read the attempt row and its window reading, the stream's frame counts, tool timeline with timestamps, rate-limit frames and closing text, the CLI envelope, `fit.json`, `clearance.json` (static pairs, both sweeps, world geometry), `inventory.json`, the smoke receipt's verdict and checks, the project's DECISIONS.md, and the script digest; compared `clearance.json` with turn-2's ignoring timings (identical); probed the window again (41 %).
5. Wrote the retained receipt from the row and measurements; extended REPORT.md and the runner README; ran the three probe suites and the receipt-cap selection; grepped the committed files for machine paths; committed.

## Result

**True now.** F5 is **exhausted**: the create prompt and all three continuations reached the model on `ot7-heron-c` and every turn ended on its own (create 7 of 120 failing; continue-1 1 of 120; continue-2 0 of 105; continue-3 0 of 105 with no change). Against F5's bar the final design meets zero failing static checks, zero failing swept checks, zero actor edits, three continuations and a passing smoke, and fails **one count: catalog hardware for every purchased part**. The product's inventory has listed both servos and both horns as uncatalogued after all four turns, because the create turn cut a tap-drill bore into the servo bodies and re-clocked the horns on their splines; the agent asserted the opposite in all four closing messages and never read the inventory, since nothing in its fit summary names catalog identity. That is a valid measured result under the charter and is reported as such; no fourth prompt exists. `resume` on `ot7-heron-c` now refuses with "exhausted". Every other ot7 project is unchanged. F4 is exhausted, F6 and F7 are untried with every slot unspent.

**Assumption.** Catalog identity is read from the product's inventory, which names a catalog row only when the placed output is what a `lib.*` generator built. Whether a cut catalog part still counts as "catalog hardware" is the owner's call on the tick; the report counts it as failing.

**Next.** F6: `robin.create.prompt.txt` in a fresh `ot7-robin-b`, through `run.py robin "$PROJECTS/ot7-robin-b" --model claude-fable-5 --turns 1`, only when the runner's probe reads under 45 %. The window read 41 % after this measurement and a create turn costs about half a window, so it waits for the 18:50 UTC reset. Then F7 on `ot7-plover-b`. Each create-plus-three-continuations schedule spans several windows.

**Concern.** The agent has now shown the same blind spot across four turns: it never reads the inventory, so a purchased part that loses catalog identity is invisible to it. Putting the uncatalogued list into the design-turn reply next to the fit summary would be the smallest product change that could close that count, but it is a tool-surface change (ADR and `test_project_tool_surface.py`) and it cannot apply to F5, which is exhausted; it is a decision for the critic before F6's create, since it changes what F6's agent sees. No new dependency. The unreconciled tail is two records after this one (`restless-gate-7062`, this).

Dispatch closed: 1 unit — F5 continue-3 on ot7-heron-c completed with no edit: static fit 0 of 105, sweep complete with zero overlap, the runner's smoke passing, servos and horns still uncatalogued; F5 exhausted with every count of its bar met except catalog hardware, receipt retained/heron-continue-3-c.json, commit 7e171bc7.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 7e171bc7ea1e086540f82f5520661b527ebffe75

## State Impact

- target: stormy-aspen-5433 — F5 is exhausted: continue-3 on ot7-heron-c (142.9 s, effort medium, 6 tool calls, no edit) re-accepted the unchanged script at 58ff41b4; static fit 0 of 105 failing, no world geometry, sweep complete on both joints at 5° with 0 mm³ on every pair, the runner's own smoke passing with the same trace digest as turn-2; both servos and both horns still uncatalogued after four turns while the agent claimed all twelve purchased parts catalog; create slot and all three continuations spent on completed turns, resume refuses with exhausted; the measured result meets every count of F5's bar except catalog hardware for every purchased part; receipt retained/heron-continue-3-c.json, commit 7e171bc7
- target: first-snow-5587 — REPORT.md carries F5 to exhaustion (iteration 72 section, summary, attempts row 4 all, the F5 checks row marked exhausted, the F10 section naming F4 and F5 exhausted and F6/F7 next in ot7-robin-b and ot7-plover-b); the runner README gains the iteration 72 section
- target: mild-ledge-7157 — the owner's account refresh (ADR-361) moved the five-hour reset from 17:20 to 18:50 UTC and left the seven-day window at 0 %, so a design turn fit at 13:51 UTC; the window read 41 % after the turn, so F6's create on ot7-robin-b waits for the 18:50 UTC reset; the agent's blind spot across four turns is that it never reads the inventory, so catalog identity lost by modifying a lib part is invisible to it
