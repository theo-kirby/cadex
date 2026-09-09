---
node_id: 2d7d7dff-42e1-5d1f-884e-0b570e4ca0b9
slug: steady-chart-0544
title: 'Bet: dispatch the held live iterate now that capacity reopened'
created_at: '2026-09-08T21:38:48+00:00'
parents:
- fresh-clover-8521
summary: ''
---
## What

Dispatch the held live project-history iterate now that supplied capacity has
reopened, and select one new direction behind it: derive the walk review's
section offset from the accepted geometry instead of the hard-coded 3.125 mm.

## Why

The blocking condition named in `restless-cabin-9629` was a supplied signal, not
a clock: "Blocked for dispatch: supplied Claude five-hour usage remains 100%.
Only later supplied capacity signals reopen `walk --prompt ... --resume`." This
pass's signals report Claude five-hour usage at 3% (29% -> 3%, -26 this run) and
seven-day at 68%. That is the signal the plan said to wait for, so the unit is
dispatchable. Assumption written per the charter's no-waiting rule: the
five-hour figure is *usage consumed*, so 3% means capacity available. Codex
seven-day is 94% and must not be substituted for the Claude default; the walk's
provider stays the CLI default.

Dispatching it now is also what the frontier needs. The signals report the
frontier unmoved for five iterations, and the last five accepted units were all
offline CLI or documentation maintenance: the decisions-tail retention
(ADR-265, four before-failing cases, 253 CLI tests) and the ownership-instruction
correction (ADR-266, 253 CLI tests) [rec: morning-arrow-5841] [rec:
fresh-clover-8521]. Both were selected precisely because capacity was closed,
and both explicitly disclaim the thing that is still unmeasured: whether a real
provider *reads* the project's history and *uses* it to choose an iterate.
`humble-sky-8445` proves delivery and persistence; `morning-arrow-5841` proves
recent ADRs now survive the prompt budget; neither proves understanding. The
charter's lead rung is the walk run end to end with no human step, and mission 2
names "iterate: change what did not work" as the loop's closing leg. The seed
measurement is spent [rec: honest-banner-0821], so the live iterate is the only
remaining unmeasured leg of that loop, and capacity for it is perishable.

The new direction comes from source, not from invention. `cli/cadex_cli/__main__.py:1497`
calls `write_section(..., plane="XZ", offset=3.125)` — a literal — and
`docs/CLI.md:353` justifies it as "an interior cut through both reference
mechanisms", meaning the swing-arm and the carriage. On `ot4-quill` that plane
misses the geometry: every one of the five recorded runs reports an empty cut
("the XZ section at 3.125 mm still misses the quill") [rec: honest-banner-0821].
So one of the four eyes the charter asks for — "section view through a named
plane" — returns nothing for a mechanism the constant was not tuned to, which is
the second-mechanism concern applied to the review step rather than to the walk.
Deriving the offset from the accepted snapshot the render leg already acquires
replaces a magic number with a measurement and adds no flag, op or dependency.

Three candidates were weighed for the one new direction: (1) the derived section
offset; (2) first-visit scaffold failure recovery, still an unmeasured failure
hypothesis with no source evidence, unselected for the same reason as last pass;
(3) the kernel swept check over the dynamics rollout, engine-zone work already
parked on long and requiring its own justified bet [rec: strong-falcon-1463].
Select only (1): it is source-demonstrated, small, offline, and serves mission 6
directly. Do not open (2) or (3).

Ordering: the iterate runs first, against the unchanged review contract. Moving
the section offset would change `review/section/<revision>/XZ-<offset>/` and the
`section` block between the baseline runs and the iterate, putting an unrelated
difference in the comparison the iterate exists to produce. It is also the
always-dispatchable fallback if the provider refuses.

Budget: 37 iterations, 10.0 h elapsed / 38.0 h left. Two short units fit.

## Method

Unit 1 restates the parameters already dispatched in `restless-cabin-9629` and
lifts only the capacity hold. Confirm `walk.engine_source_comparison` reports
`match` before the first leg (ADR-251); rebuild with `pixi run build-engine`
first if it reports `different`, because the walk resolves the installed engine
and a stale one exits 0 anyway. Run `./cadex walk --project
/home/theo/cadex-projects/ot4-quill --prompt ... --resume` at CPU 5 x 16,
training seed 0, rollout seed 7, trainer timeout 600, leg timeout 120, under the
external process-tree watchdog at 2.9 GB — with a wall cutoff set above a design
leg's real cost, not the 850 s used for the model-free seed runs, since a design
turn has run past 1,000 s on this machine. Require the turn to actually read and
update `ARCHITECTURE.md`, `DECISIONS.md` and the project's domain notes, and to
choose its one geometry change from the review's own findings. Use fresh output
and policy names with explicit root exclusions after the default policy
negations, and verify the new paths are neither tracked nor staged. Preserve all
prior run bytes, policy hashes and script history. Verify all four review
outputs, record the measured comparison in the project's `PROGRESS.md` and the
lifecycle docs, and run the full CLI gate. A provider refusal ends the attempt
and hands over to unit 2 — no retry, no quota probe, no wait unit.

Unit 2: demonstrate the empty cut first with a regression over quill-shaped
geometry, then derive the offset from the accepted tessellation's bounding-box
centre on the section axis, keeping `cadex section --plane/--offset-mm` as the
unchanged explicit surface and reporting the derived value through the existing
`offset_mm` field. Update `docs/CLI.md` (the §353 rationale and the §386 artifact
row), `docs/MUJOCO.md` §7c, ROADMAP and an ADR in the same commit; run the full
CLI gate. No new flag, op, protocol change, engine or shell diff, and no
rewriting of the committed `docs/probes/` baselines that name `XZ-3.125`.

## Result

Planning only. Short ranks the unblocked live iterate, then the derived section
offset. Medium folds the two delivered context units and keeps the measurement
limits. Long records that context maintenance is spent and names the section
constant as a measured limit of this machine's evidence. One new direction
selected. No charter gap is deleted, retired or marked done; no charter, code,
record or state node changes. Runtime validation belongs to the actor.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 8b84cf3b7636cb899e59f134ba3b4041b6b243a7

## State Impact

- target: plan/young-crane-9546 — lift the capacity hold, rank the live iterate first and add the derived section offset
- target: plan/strong-birch-7412 — fold the two delivered context units and order the remaining lifecycle work
- target: plan/late-valley-7350 — record context maintenance as spent and the fixed section constant as a measured limit
