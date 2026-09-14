---
node_id: e2a9fac7-67a0-549c-b9a2-8f88e80f4fd2
slug: kind-flint-2780
title: 'F3: product swept checker measured on a Finch copy through one product-agent turn'
created_at: '2026-09-14T19:54:21+00:00'
parents:
- curious-cedar-4881
summary: ''
---
## What

The product swept checker has now been run on a copy of `ot6-finch` through
the product agent, closing the "product Finch measurement outstanding" gap
under F3. A fresh copy at `cadex-projects/ot7-finch-product-sweep` (all of
ot6-finch except `evidence/` and `runs/`) took one `./cadex -p` turn with the
committed measurement prompt `docs/probes/ot7/sweep/finch.product-sweep.prompt.txt`
(sha256 `d15a2719…`). The agent's only script edit is `sweep_step_degrees=` on
`assembly.assembly(...)`; it accepted a 5° revision (`a2fb2c07…`) whose fourth
hinge hit the shared 180 s budget and was reported `incomplete`, then, under
the prompt's one allowed coarsening, a 10° revision (`61303150…`) with
complete coverage of all four hinges in 104.4 s. The receipt is the new
"Product measurement" section of `docs/probes/ot7/sweep/README.md` (13.1 KB).
Also done first, as the critic asked: the backfill record `curious-cedar-4881`
for commit `7fb47e51`, and the CLI suite run to completion (641 passed, 1
skipped) with the slider-sweep evidence recorded there.

## Why

Targets `curious-quill-9036` (F3): its reconcile judgement named the product
Finch measurement as outstanding, and the critic's message asked for it "on a
copy through an authorized product-agent turn", preserving the no-actor-edit
constraint. The actor never touched the copy's script: the before state was
read with `cadex clearance --sweep` (status unavailable), the change came from
the agent, and the after state was read the same way (coverage complete,
committed in the project as `699f912`). No refusal occurred; the nested agent
CLI ran normally under the CLI's default model `claude-fable-5`. The critic's
first two asks (backfill record, finish the CLI run) were done before this
unit and are their own record and commit.

## Method

Found the installed engine one comment line behind the committed worker, so
ran one `pixi run build-engine` and `pixi run stage-engine` before anything
else (installed and payload copies now byte-identical to source). Ran the
engine suite, the CLI suite and the packaged lifecycle gate against `7fb47e51`.
Copied the project, wrote and hashed the measurement prompt, launched the turn
under `timeout 1800`, then read both accepted attempts' `result.json` files
directly with a script rather than trusting the reply. Compared the sweep's
first-contact set with the static fit's failing set. Copied the CLI envelope,
the stderr trace and the 236-line agent session transcript into the project's
`evidence/` and recorded their digests in the receipt.

## Result

Product checker on Finch, from the stored results: every completed hinge
reports all 406 pairs with solved-pose agreement true; 40 pairs have a first
contact and all of them at the joint's lower limit (permanent seatings and the
12 thread engagements at ≤ 7.854 mm³); no pair first touches inside any range
at 5° or 10°. Both knee shin-to-thigh pairs keep 1.0 mm minimum distance
(0.9999999999999964 at worst), 0 mm³, first contact null. This agrees with the
read-only experiment (amber-lantern-9712): the ot6 README's predicted knee
contact is absent on this revision, and the angle F3 asked for is reported as
none, not invented. Per-joint runtime at 5°: hip_l 66.2 s, knee_l 27.3 s,
hip_r 75.1 s, knee_r cut off at 11.3 s when the shared 180 s ran out; at 10°:
35.7, 16.2, 36.2, 16.3 s. The bound is enforced and reported, not skipped.
Confound: both suites were running on the same box during the 5° build (load
average 24), so those times are an upper bound on an idle machine.

One honesty finding: the agent's reply said "exactly the same 44 pairs report
a first contact" while the published sweep has 40; the other four are the
bearing-stub pairs at their designed 0.05 mm radial clearance, which fail the
static default minimum but never touch. The agent's coverage, timing and knee
numbers match the published data. This is exactly the claim-versus-measurement
gap the charter is about and is recorded in the receipt.

F3's evidence list now has every item: the known-angle engine fixtures (hinge
and slider), the Finch copy measured by the product checker with the knee
result reported (no contact within one step), per-joint runtimes recorded and
the 90 s/180 s bound enforced, and both the agent's inspect scope and
`cadex clearance --sweep` reaching the result. A record may say "ticks F3";
the caveats that stay true are that sampling is discrete, the predicted contact
angle does not exist on this revision, and non-hinge, non-slider limited joints
are reported incomplete by design. The human owns the checkbox.

Gates this iteration, all against the committed source after one build and
stage: `pixi run test-engine` 2,127 passed/53 skipped (346.72 s); CLI suite
641 passed/1 skipped (566.76 s), run to completion; packaged lifecycle 18
passed (16.59 s). No product code changed in this unit, so no ADR; the
receipt and prompt are the user-facing documents. No dependency added; no
design edited by the actor; ot6 projects untouched. F9's retained-design
failing-set comparison for Finch, Robin and Heron is still open, and the
unreconciled tail is now three records (green-river-3790, curious-cedar-4881
and this one), so a reconcile pass is due.

Dispatch closed: 1 unit — product swept checker measured on a Finch copy through one product-agent turn; knee contact absent, budget bound exercised, agent overcount recorded.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: e260153cca4f8e92daa4436e1cf3731bd62d9335

## State Impact

- target: curious-quill-9036 — Product checker run on a copy of ot6-finch by one product-agent turn (prompt d15a2719…): 5° hit the 180 s shared budget on the fourth hinge and was reported incomplete; 10° completed all four in 104.4 s. No pair first touches inside any range; both knee shin-to-thigh pairs hold 1.0 mm, 0 mm³, no contact, agreeing with the experiment. F3's evidence list is complete with the negative-angle caveat; agent reply overcounted first-contact pairs 44 vs published 40. Receipt: docs/probes/ot7/sweep/README.md.
- target: eager-summit-3153 — Fresh green gates after one build and stage against 7fb47e51: engine 2,127/53 skipped, CLI 641/1 skipped run to completion, packaged 18. Retained-design failing-set comparison still open.
