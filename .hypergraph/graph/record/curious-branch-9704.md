---
node_id: 85f031d1-9c6c-5286-be76-0bd3ebe05045
slug: curious-branch-9704
title: 'Ouroboros run: ot9 [52dd71e8] — operator directive'
created_at: '2026-09-22T17:38:45+00:00'
parents:
- odd-banner-6071
summary: ''
---
## What

Operator directive: an Ouroboros loop starts on this repo. Every work node of the run descends from this node.

## Why

The charter (the operator's goal document), verbatim:

# Goal: teach Robin to balance

Verified against source: 2026-09-22. Operator charter for ot9, following
ot8's measured control diagnosis. The human owns this file; unattended roles
never edit it. Prior projects and receipts remain read-only baselines.

## Mission

Train a policy that keeps Robin upright on its accepted design for the task's
declared eight-second episode. Install and verify the policy against its
accepted task and model, then pass ten recorded reset seeds without firing
`fallen` or exceeding 30 degrees of chassis tilt. The product agent may
revise mechanics, task and reward when measurements justify it. A completed
experiment is not a successful balance unless this behavioral bar is met.

Keep the 48-hour ceiling and two-accepted-done stop. Every Ouroboros role and
headless product-agent call uses `claude-opus-5-5`, with no model fallback.

## Done criteria

Each criterion requires a causally parented record with measured evidence.
The human owns the checkboxes; roles report results and do not tick them.

- [ ] **B1. The experiment has a frozen baseline and evaluation contract.**
  `docs/probes/ot9/README.md` names ot8 Robin's script, accepted revision,
  geometry digest, MJCF and task digests. It fixes ten evaluation seeds before
  training, the 8 s / 30 degree / no-`fallen` bar, training and evaluation
  commands, and accounting for failed, interrupted and void runs. Keep the
  same seeds across revisions and publish every result, including failures.
- [ ] **B2. Robin's policy is trained and installed on accepted artifacts.**
  At least one offboard PPO run produces a `.cxpolicy` with recorded task and
  model digests, seed, settings, checkpoint identity and training curve. Store
  it in a new `ot9-*` project, witness-verify it in the engine, accept it
  through the ordinary script path, and reopen it in a fresh process with
  the same policy and model identity. Trainer exit alone is not success.
- [ ] **B3. Robin balances across the declared evaluation set.** On each of
  ten frozen reset seeds, the accepted policy runs the full 8 s at the task's
  50 Hz control rate, stays within 30 degrees of accepted chassis attitude
  throughout, and never fires `fallen`. Report all ten trajectories'
  duration, peak tilt, minimum chassis height, termination, and policy/model
  digests. One failed seed fails this criterion; do not average it away.
- [ ] **B4. Changes remain mechanically and causally reviewable.** The final
  accepted design has zero failing static fit checks, complete passing swept
  fit for both wheel joints, and a component inventory with catalog
  provenance. Compare it with the frozen baseline. Every mechanical, task
  or reward change comes from a product-agent turn on an ot9 project and has
  a before/after measurement. No actor design edit, grounded base, added
  stabilizer, hidden joint, shorter episode or weaker tilt/fall threshold
  may satisfy B3.
- [ ] **B5. Regressions and a closing report are complete.** Both full suites,
  the packaged lifecycle gate for any engine/payload change, and a fresh
  reopen of the final ot9 project pass at the final revision. The report at
  `docs/probes/ot9/REPORT.md` lists every training and evaluation run,
  checkpoint choice, accepted identity, changed design/task/reward, failed
  attempt, achieved bar and remaining defect. Reconcile, then claim done
  for critic review without ticking owner boxes.

## Horizon ladder

- **short-term:**
  1. Freeze the baseline, ten evaluation seeds and receipt shape.
  2. Reproduce Robin's no-policy fall on an independent copy and export its
     accepted training bundle.
  3. Run a first bounded training job, install its policy and measure the
     declared episode on training-side diagnostics.
  4. Evaluate the accepted policy on frozen seeds and record all failures.
- **medium-term:**
  1. Improve policy behavior from measured failures while preserving the
     eight-second, tilt and fall requirements.
  2. If learning exposes a mechanical limit, let the product agent revise
     the mechanism and compare fit, mass, torque and behavior.
  3. Verify policy identity through export, acceptance, reopen and a fresh
     process; publish the final comparison.
- **long-term:**
  1. Repeat trained balancing on another mechanically independent design
     after Robin is proven; this is a future direction, not an ot9 bar.
  2. Extend robustness toward shove recovery and printability only after
     declared hold behavior is measured; neither substitutes for B3.
  3. Keep every gate green and every changed behavior documented.

## Constraints

**Standing:** obey AGENTS.md, licensing and process boundaries. Training stays
offboard; do not import JAX/MJX into the engine or build a replacement engine
or shell. Never commit secrets, machine paths, private hostnames, build
outputs, full transcripts, policy binaries or rollout traces. Keep full
evidence project-local and commit compact receipts with paths and digests.
Do not hand-edit STATE.md, PLAN.md, ROADMAP.md or state nodes. Preserve
accepted-state guards and the original ot7/ot8 projects.

**This run:**

- Every Ouroboros role and product-agent call through `./cadex` uses
  `claude-opus-5-5`, with no model fallback, and records its model
  explicitly.
- Only the product agent authors changes to Robin's mechanics, task and
  reward. The actor may write measurement and product tooling with regressions
  and install a trained policy through the supported CLI path. Each project
  copy has a new `ot9-*` identity; baseline projects stay read-only.
- Keep the ten evaluation seeds fixed across revisions. Record training seeds
  and any additional tuning evaluations separately; show each candidate's
  outcome on all ten, not only the winning policy's.
- Keep the eight-second episode, 50 Hz control rate, 30-degree tilt limit and
  `fallen` termination. No world fixture, stabilizer, joint suppression or
  silent tolerance change. Report known standing contact compression
  separately; do not mislabel it as a geometry intersection.
- Record each training run's planned settings and stop rule before it starts.
  Preserve failed and interrupted runs. Do not claim success from reward
  alone or from the zero-torque `cadex smoke` hold mode.
- No dashboard, visual redesign, unrelated catalog expansion or inherited
  tree removal. Fix product defects only when reproduced failures block this
  lifecycle, with a meaningful regression.
- No role starts, stops or restarts the loop or signals its process.

## Question policy

Resolve reversible choices autonomously using the smallest measured step
toward B1-B5. Code and accepted artifacts outrank docs; update docs with
behavior. If the policy misses an evaluation seed, record the failure and
diagnose it before another training or design revision. If Opus 5.5 is
unavailable, retain the receipt and wait for capacity. Never invent a
measurement or treat provider refusal as a design verdict.

## Exhaustion policy

`report_done`. After B1-B5 have evidence, write the closing report,
reconcile and claim done. Two consecutive critic acceptances stop the run.
If the 48-hour ceiling arrives first, report the highest achieved bar and
every failed seed; do not redefine success or start another mechanism. A
trained policy that misses the ten-seed bar is an honest incomplete result.

## Quality bar

- Run `pixi run test-engine` and `pixi run python -m pytest cli/tests` at
  the final revision. For protocol or payload changes, rebuild and stage,
  then run the packaged lifecycle gate. Report skips and failures as such.
- A product fix needs a regression that fails before it. Keep code changes
  coherent. Record each unit with State Impact; direction changes and
  removals also earn ADR entries.
- Measure every accepted design and policy from its own pinned artifacts.
  Preserve old evidence and list all training and evaluation attempts.

## Reconcile

Every five work iterations or three unreconciled records, fold impacts,
advance the high-water mark, regenerate views, export and check. Separate
maintainer and planner roles stay off; the critic names the next unit.
Unattended roles never edit this charter.

**Done criteria as gaps** (one open state node each; work closes them through declared impacts):

- [gap] gap-b1-experiment-has-frozen-baseline: **B1. The experiment has a frozen baseline and evaluation contract.** `docs/probes/ot9/README.md` names ot8 Robin's script, accepted revision, geometry digest, MJCF and task digests. It fixes ten evaluation seeds before training, the 8 s / 30 degree / no-`fallen` bar, training and evaluation commands, and accounting for failed, interrupted and void runs. Keep the same seeds across revisions and publish every result, including failures.
- [gap] gap-b2-robin-s-policy-trained: **B2. Robin's policy is trained and installed on accepted artifacts.** At least one offboard PPO run produces a `.cxpolicy` with recorded task and model digests, seed, settings, checkpoint identity and training curve. Store it in a new `ot9-*` project, witness-verify it in the engine, accept it through the ordinary script path, and reopen it in a fresh process with the same policy and model identity. Trainer exit alone is not success.
- [gap] gap-b3-robin-balances-across-declared: **B3. Robin balances across the declared evaluation set.** On each of ten frozen reset seeds, the accepted policy runs the full 8 s at the task's 50 Hz control rate, stays within 30 degrees of accepted chassis attitude throughout, and never fires `fallen`. Report all ten trajectories' duration, peak tilt, minimum chassis height, termination, and policy/model digests. One failed seed fails this criterion; do not average it away.
- [gap] gap-b4-changes-remain-mechanically-causally: **B4. Changes remain mechanically and causally reviewable.** The final accepted design has zero failing static fit checks, complete passing swept fit for both wheel joints, and a component inventory with catalog provenance. Compare it with the frozen baseline. Every mechanical, task or reward change comes from a product-agent turn on an ot9 project and has a before/after measurement. No actor design edit, grounded base, added stabilizer, hidden joint, shorter episode or weaker tilt/fall threshold may satisfy B3.
- [gap] gap-b5-regressions-closing-report-complete: **B5. Regressions and a closing report are complete.** Both full suites, the packaged lifecycle gate for any engine/payload change, and a fresh reopen of the final ot9 project pass at the final revision. The report at `docs/probes/ot9/REPORT.md` lists every training and evaluation run, checkpoint choice, accepted identity, changed design/task/reward, failed attempt, achieved bar and remaining defect. Reconcile, then claim done for critic review without ticking owner boxes.

## Method

Ouroboros iterations on branch `ouroboros/ot9`: orient, one dispatched unit, record, commit; a reconcile pass folds the tail on pressure; with the planner on, a bet follows each reconcile.

## Result

Directive recorded. Work follows as child nodes.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot9
- commit: bbb459fc795ea8218c87f685288b99c75290873e

## State Impact

- target: NEW gap-b1-experiment-has-frozen-baseline — Charter gap, status open: **B1. The experiment has a frozen baseline and evaluation contract.** `docs/probes/ot9/README.md` names ot8 Robin's script, accepted revision, geometry digest, MJCF and task digests. It fixes ten evaluation seeds before training, the 8 s / 30 degree / no-`fallen` bar, training and evaluation command. Flip to working only when the criterion is verifiably met.
- target: NEW gap-b2-robin-s-policy-trained — Charter gap, status open: **B2. Robin's policy is trained and installed on accepted artifacts.** At least one offboard PPO run produces a `.cxpolicy` with recorded task and model digests, seed, settings, checkpoint identity and training curve. Store it in a new `ot9-*` project, witness-verify it in the engine, accept it thro. Flip to working only when the criterion is verifiably met.
- target: NEW gap-b3-robin-balances-across-declared — Charter gap, status open: **B3. Robin balances across the declared evaluation set.** On each of ten frozen reset seeds, the accepted policy runs the full 8 s at the task's 50 Hz control rate, stays within 30 degrees of accepted chassis attitude throughout, and never fires `fallen`. Report all ten trajectories' duration, peak. Flip to working only when the criterion is verifiably met.
- target: NEW gap-b4-changes-remain-mechanically-causally — Charter gap, status open: **B4. Changes remain mechanically and causally reviewable.** The final accepted design has zero failing static fit checks, complete passing swept fit for both wheel joints, and a component inventory with catalog provenance. Compare it with the frozen baseline. Every mechanical, task or reward change. Flip to working only when the criterion is verifiably met.
- target: NEW gap-b5-regressions-closing-report-complete — Charter gap, status open: **B5. Regressions and a closing report are complete.** Both full suites, the packaged lifecycle gate for any engine/payload change, and a fresh reopen of the final ot9 project pass at the final revision. The report at `docs/probes/ot9/REPORT.md` lists every training and evaluation run, checkpoint ch. Flip to working only when the criterion is verifiably met.
