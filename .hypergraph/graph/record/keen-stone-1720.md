---
node_id: d515d93b-effa-5bc0-9c25-e153925a4486
slug: keen-stone-1720
title: 'Ouroboros run: ot8 [01d0a92c] — operator directive'
created_at: '2026-09-20T18:45:21+00:00'
parents:
- odd-banner-6071
summary: ''
---
## What

Operator directive: an Ouroboros loop starts on this repo. Every work node of the run descends from this node.

## Why

The charter (the operator's goal document), verbatim:

# Goal: finish the unassisted-design evidence

Verified against source: 2026-09-20. Operator charter for ot8, following the
owner's request to review and merge ot7 and start the next run. The selected
scope is a bounded follow-up on ot7's remaining gaps. The human owns this
file; unattended roles never edit it. ot7's charter and outcomes remain in
git history and `docs/probes/ot7/REPORT.md`; this run does not rewrite them.

## Mission

Make the remaining unassisted-design claims reviewable against accepted
artifacts. First establish the new experiment's prompts and slot accounting,
then measure an arm whose purchased hardware retains catalog identity, a
biped whose accepted MJCF passes the shipped smoke command, and the cause
of the balancer's failed holding smoke. Preserve the difference between fit,
support, and controlled behavior. A wheel balancer that needs feedback is a
measured control requirement, not permission to hide the failure with a
grounded base, extra supports, a weakened tolerance, or a shorter rollout.

No training or dashboard work is authorized. Keep the existing Opus-only
configuration, a 48-hour ceiling, and the two-accepted-done stop.

## Done criteria

Each criterion requires a record with measured evidence. The human owns
checkboxes; a bounded experiment can close with a clearly reported negative
result. Never claim the requested design succeeded merely because its
experiment finished.

- [ ] **G1. The follow-up has a frozen, bounded experiment contract.**
  `docs/probes/ot8/README.md` identifies the ot7 baselines, freezes prompts
  before any product turn, lists success and failure bars, and allocates one
  initial product prompt plus at most three continuations per design. The
  report distinguishes ot8 from ot7 and every failed, void, interrupted or
  unreached call. Reuse the ot7 runner where practical; any minimal extension
  has tests for slot accounting and preserving prior evidence.
- [ ] **G2. The arm's catalog-provenance gap has a bounded measured outcome.**
  In a fresh ot8 project, run the original Heron create prompt with today's
  product instructions. Measure static fit, swept fit, inventory and an
  ordinary accepted-artifact smoke after each relevant turn. Success means
  zero failing static and swept checks, every purchased component placed as
  an unmodified catalog part, zero actor design edits, and a passing smoke.
  Otherwise report the exact remaining defects after the allowed turns.
  Compare with ot7's two modified servos and two modified horns.
- [ ] **G3. The biped's smoke is measured against its accepted artifacts.**
  Work on a new independent copy of ot7-plover-e. A product-agent turn may
  explicitly rebuild and accept the unchanged design with the fixed engine;
  the actor may not change its script, parameters, or accepted state. Run
  ordinary `cadex smoke` against that pin, without the re-export probe's
  substituted bundle. Record accepted digest, MJCF digest, fit, inventory,
  smoke and a fresh-process reopen. Success requires matching accepted
  evidence and a passing smoke; report any bounded failure without hiding it.
- [ ] **G4. The balancer's failed smoke has an actionable measured diagnosis.**
  On an independent ot8 copy of Robin, reproduce the ordinary holding smoke
  and distinguish geometry/export mismatch, a design defect, and missing
  feedback control using published measurements and the MJCF/task contract.
  If a design defect is actionable, use only the frozen product prompts and
  allowed turns to repair it and remeasure. If the required behavior needs
  feedback outside this charter, record the exact missing control contract
  and stop that experiment. A no-feedback inverted pendulum need not pass;
  never call it a success or silently introduce training or a controller.
- [ ] **G5. The regression floor still holds.** Both full suites and the
  packaged lifecycle gate pass at the final code revision. Reopen copies of
  the retained ot6/ot7 designs used by this run and verify their accepted
  pins and artifacts remain intact. Explain every measured difference. The
  ADR-398 repeated-restore retention regressions stay green.
- [ ] **G6. A closing report carries every outcome and is accepted by the critic.**
  `docs/probes/ot8/REPORT.md` contains one row per experiment with prompts,
  turns, model, accepted identities, static/swept fit, inventory, smoke,
  before/after comparisons and remaining defects. Link G1-G5 evidence.
  Separate achieved success bars from exhausted or control-blocked outcomes.
  Write this last, reconcile, and claim done without ticking owner boxes.

## Horizon ladder

- **short-term:**
  1. Freeze the ot8 experiment contract and prompts; verify product access.
  2. Close the biped accepted-artifact smoke measurement on an independent copy.
  3. Run the arm experiment with catalog identity visible to the product agent.
  4. Diagnose the balancer with the same published checks and preserved receipts.
- **medium-term:**
  1. Compare arm hardware identity, static fit and motion fit with ot7.
  2. Establish the biped's accepted MJCF, reopen and smoke as one evidence chain.
  3. Separate the balancer's mechanical feasibility from its control requirement.
  4. Run regressions and publish the closing comparison.
- **long-term:**
  1. Park printability checks: wall thickness, screw engagement and connected mounts.
  2. Park trained behavior: a balancing controller, reaching and walking rewards.
  3. Keep every gate green and every changed behavior documented. Parked work
     is not authorization to expand this run after its bounded experiments.

## Constraints

**Standing:** obey AGENTS.md and licensing/process/sandbox boundaries. No
replacement engine or shell. Training stays offboard. Never commit secrets,
machine paths, private hostnames, build outputs, full transcripts or traces.
Committed receipts are at most 16 KB and images at most 200 KB. Keep full
evidence project-local and cite paths plus digests. Never hand-edit STATE.md,
PLAN.md, ROADMAP.md or state nodes. Accepted-state guards remain in force.

**This run:**

- All roles and product calls use `claude-opus-5`, with no model fallback.
- The actor never edits a test design's source, parameters or accepted state.
  An unchanged copy may be prepared mechanically; changes and reacceptance
  come only from a product-agent turn. Preserve all prior projects read-only.
- Use external projects named `ot8-*` under the established projects root.
  Every experiment has a new identity; ot7's exhausted slots stay exhausted.
- Freeze initial and continuation prompts before any design turn. Continuation
  prompts name no specific part, dimension or defect. They direct the agent
  to its measured fit, inventory and smoke evidence. At most three per design.
- Usage-limit calls are void and spend no slot. Interrupted/unreached calls
  retain their evidence and cannot masquerade as design failures or successes.
  Verify product-model access and window headroom before each design turn.
- When provider capacity blocks the next turn, do not manufacture tooling or
  waiting records. Keep the existing receipt, return no change, and let the
  runner back off. Probe again only after a reset or evidence of restored access.
- No role starts, stops or restarts the loop, or signals its process.
- No policy training, reward redesign, hand-authored feedback controller,
  dashboard/service edits, visual changes, unrelated catalog expansion or
  inherited-tree removals. Smoke rollouts stay bounded to five minutes.
- A design may fail. Do not ground a free robot, add stabilizers, suppress
  required joints, weaken tolerances, or shorten its declared smoke to make
  a result pass. An explicit measured blocker is an acceptable outcome.
- Fix product defects only when a reproduced failure blocks these experiments
  or violates an existing contract; pin each with a meaningful regression.

## Question policy

Resolve routine reversible choices autonomously, with code as truth and docs
updated alongside behavior. Work on the highest-ranked unblocked criterion.
Never guess a measurement. If closing a design success bar requires training
under the current no-training constraint, record that boundary and finish the
bounded diagnosis; do not spend the run repeatedly rediscovering it. A new
objective requires an owner revision.

## Exhaustion policy

`report_done`. After G1-G5 have evidence, write G6, reconcile and claim done.
Two consecutive critic acceptances stop the run. Do not repeat an exhausted
experiment, invent another mechanism or advance parked work to fill time.
A negative design result counts as evidence only after its allowed relevant
turns are exhausted, or a reproduced out-of-scope control requirement
justifies ending that experiment. Provider refusal alone proves neither.

## Quality bar

- `pixi run test-engine` and `pixi run python -m pytest cli/tests`. Engine
  protocol/payload changes also rebuild and stage, then run
  `CADEX_ENGINE_ROOT=<payload> pixi run python -m pytest
  src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`.
- Each fix has a regression that fails before the fix. Distinguish actual
  passes from skips and do not call an unavailable measurement a pass.
- Record every unit causally with State Impact; removals and direction changes
  earn ADRs. One logical change per commit, critic rejects fixed forward.
- Preserve old evidence and list every attempted experiment, including failures.

## Reconcile

Every five work iterations or three unreconciled records, perform the
reconcile pass: fold impacts, advance the high-water mark, regenerate views,
export and check. Separate maintainer/planner roles stay off; the critic
names the next unit. Unattended roles never edit this charter.

**Done criteria as gaps** (one open state node each; work closes them through declared impacts):

- [gap] gap-g1-follow-up-has-frozen: **G1. The follow-up has a frozen, bounded experiment contract.** `docs/probes/ot8/README.md` identifies the ot7 baselines, freezes prompts before any product turn, lists success and failure bars, and allocates one initial product prompt plus at most three continuations per design. The report distinguishes ot8 from ot7 and every failed, void, interrupted or unreached call. Reuse the ot7 runner where practical; any minimal extension has tests for slot accounting and preserving prior evidence.
- [gap] gap-g2-arm-s-catalog-provenance: **G2. The arm's catalog-provenance gap has a bounded measured outcome.** In a fresh ot8 project, run the original Heron create prompt with today's product instructions. Measure static fit, swept fit, inventory and an ordinary accepted-artifact smoke after each relevant turn. Success means zero failing static and swept checks, every purchased component placed as an unmodified catalog part, zero actor design edits, and a passing smoke. Otherwise report the exact remaining defects after the allowed turns. Compare with ot7's two modified servos and two modified horns.
- [gap] gap-g3-biped-s-smoke-measured: **G3. The biped's smoke is measured against its accepted artifacts.** Work on a new independent copy of ot7-plover-e. A product-agent turn may explicitly rebuild and accept the unchanged design with the fixed engine; the actor may not change its script, parameters, or accepted state. Run ordinary `cadex smoke` against that pin, without the re-export probe's substituted bundle. Record accepted digest, MJCF digest, fit, inventory, smoke and a fresh-process reopen. Success requires matching accepted evidence and a passing smoke; report any bounded failure without hiding it.
- [gap] gap-g4-balancer-s-failed-smoke: **G4. The balancer's failed smoke has an actionable measured diagnosis.** On an independent ot8 copy of Robin, reproduce the ordinary holding smoke and distinguish geometry/export mismatch, a design defect, and missing feedback control using published measurements and the MJCF/task contract. If a design defect is actionable, use only the frozen product prompts and allowed turns to repair it and remeasure. If the required behavior needs feedback outside this charter, record the exact missing control contract and stop that experiment. A no-feedback inverted pendulum need not pass; never call it a success or silently introduce training or a controller.
- [gap] gap-g5-regression-floor-still-holds: **G5. The regression floor still holds.** Both full suites and the packaged lifecycle gate pass at the final code revision. Reopen copies of the retained ot6/ot7 designs used by this run and verify their accepted pins and artifacts remain intact. Explain every measured difference. The ADR-398 repeated-restore retention regressions stay green.
- [gap] gap-g6-closing-report-carries-every: **G6. A closing report carries every outcome and is accepted by the critic.** `docs/probes/ot8/REPORT.md` contains one row per experiment with prompts, turns, model, accepted identities, static/swept fit, inventory, smoke, before/after comparisons and remaining defects. Link G1-G5 evidence. Separate achieved success bars from exhausted or control-blocked outcomes. Write this last, reconcile, and claim done without ticking owner boxes.

## Method

Ouroboros iterations on branch `ouroboros/ot8`: orient, one dispatched unit, record, commit; a reconcile pass folds the tail on pressure; with the planner on, a bet follows each reconcile.

## Result

Directive recorded. Work follows as child nodes.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot8
- commit: 8c9b1b34dd2a505fb8d514025a35f489199b0602

## State Impact

- target: NEW gap-g1-follow-up-has-frozen — Charter gap, status open: **G1. The follow-up has a frozen, bounded experiment contract.** `docs/probes/ot8/README.md` identifies the ot7 baselines, freezes prompts before any product turn, lists success and failure bars, and allocates one initial product prompt plus at most three continuations per design. The report disting. Flip to working only when the criterion is verifiably met.
- target: NEW gap-g2-arm-s-catalog-provenance — Charter gap, status open: **G2. The arm's catalog-provenance gap has a bounded measured outcome.** In a fresh ot8 project, run the original Heron create prompt with today's product instructions. Measure static fit, swept fit, inventory and an ordinary accepted-artifact smoke after each relevant turn. Success means zero faili. Flip to working only when the criterion is verifiably met.
- target: NEW gap-g3-biped-s-smoke-measured — Charter gap, status open: **G3. The biped's smoke is measured against its accepted artifacts.** Work on a new independent copy of ot7-plover-e. A product-agent turn may explicitly rebuild and accept the unchanged design with the fixed engine; the actor may not change its script, parameters, or accepted state. Run ordinary `c. Flip to working only when the criterion is verifiably met.
- target: NEW gap-g4-balancer-s-failed-smoke — Charter gap, status open: **G4. The balancer's failed smoke has an actionable measured diagnosis.** On an independent ot8 copy of Robin, reproduce the ordinary holding smoke and distinguish geometry/export mismatch, a design defect, and missing feedback control using published measurements and the MJCF/task contract. If a de. Flip to working only when the criterion is verifiably met.
- target: NEW gap-g5-regression-floor-still-holds — Charter gap, status open: **G5. The regression floor still holds.** Both full suites and the packaged lifecycle gate pass at the final code revision. Reopen copies of the retained ot6/ot7 designs used by this run and verify their accepted pins and artifacts remain intact. Explain every measured difference. The ADR-398 repeat. Flip to working only when the criterion is verifiably met.
- target: NEW gap-g6-closing-report-carries-every — Charter gap, status open: **G6. A closing report carries every outcome and is accepted by the critic.** `docs/probes/ot8/REPORT.md` contains one row per experiment with prompts, turns, model, accepted identities, static/swept fit, inventory, smoke, before/after comparisons and remaining defects. Link G1-G5 evidence. Separate. Flip to working only when the criterion is verifiably met.
