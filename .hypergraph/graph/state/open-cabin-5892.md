---
node_id: fd0f3448-5ee7-5993-ad82-0e2019afd1ea
slug: open-cabin-5892
title: Robin trained to balance — the ot9 charter (ADR-404)
created_at: '2026-09-22T17:39:41+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

**Owner-directed work for run `ot9` (ADR-404): train a policy that keeps Robin upright on its accepted design for the task's declared eight-second episode [rec: silver-cloud-5850] [rec: curious-branch-9704].** It follows ot8 (`ancient-vine-9908`), whose G4 measured Robin's zero-command fall as adequate actuator authority with missing feedback — a control-blocked outcome, not a design or export defect [rec: silver-cloud-5850]. ot9 is the trained-control answer to that diagnosis. Charter and configuration were committed at `c7aea2db`; the loop itself was started by the operator directive on `ouroboros/ot9` [rec: silver-cloud-5850] [rec: curious-branch-9704].

**The behavioural bar [rec: curious-branch-9704].** Install and witness-verify the policy against its accepted task and model, then pass **ten frozen reset seeds**, each running the full 8 s at the task's 50 Hz control rate without firing `fallen` or exceeding 30 degrees of chassis tilt. One failed seed fails the bar; a completed training job, a reward curve or the zero-torque `cadex smoke` hold mode is not success. A trained policy that misses the ten-seed bar is an honest incomplete result [rec: curious-branch-9704].

**Model policy [rec: shy-fjord-4367].** Every Ouroboros role and every headless product-agent call uses `claude-opus-5-5` with **no fallback**; provider unavailability means retaining the receipt and waiting, never model substitution. This superseded, before first launch, the charter's original choice of Fable 5.1 with Codex fallback for roles [rec: silver-cloud-5850] [rec: shy-fjord-4367]. The 48-hour ceiling and the two-accepted-done stop are unchanged [rec: shy-fjord-4367].

The owner's fixed choices [rec: curious-branch-9704]:

- **Only the product agent authors changes to Robin's mechanics, task and reward**, and it may make them when measurements justify it. The actor may write measurement and product tooling with regressions and install a trained policy through the supported CLI path. Each project copy has a new `ot9-*` identity; ot7/ot8 projects stay read-only baselines [rec: curious-branch-9704].
- **The ten evaluation seeds stay fixed across revisions**; training seeds and extra tuning evaluations are recorded separately, and every candidate's outcome is shown on all ten, not only the winner's [rec: curious-branch-9704].
- **No weakening**: the eight-second episode, 50 Hz rate, 30-degree limit and `fallen` termination stay; no world fixture, grounded base, stabilizer, joint suppression or silent tolerance change. Standing contact compression is reported separately and not mislabelled as a geometry intersection [rec: curious-branch-9704].
- **Every training run's settings and stop rule are recorded before it starts**; failed and interrupted runs are preserved. A missed evaluation seed is recorded and diagnosed before another training or design revision [rec: curious-branch-9704].
- Training stays offboard (no JAX/MJX in the engine); no policy binaries, rollout traces, secrets or machine paths committed — compact receipts with paths and digests. No dashboard, visual redesign, unrelated catalog expansion or inherited-tree removal; product defects fixed only when a reproduced failure blocks this lifecycle, with a regression [rec: curious-branch-9704].

Exhaustion policy `report_done`; a reconcile every five work iterations or three unreconciled records, with the separate maintainer and planner off and the critic naming the next unit [rec: curious-branch-9704]. The five done criteria B1-B5 are child state nodes: B1 `twilight-flint-8205`, B2 `tidy-arbor-3203`, B3 `early-rain-5934`, B4 `strong-arrow-1143`, B5 `true-anchor-9584`; the human owns the checkboxes [rec: curious-branch-9704].

**Run progress: all five criteria carry measured evidence and done is claimed for critic review [rec: falling-fountain-6090].** Policy r3-ppo-1 (ef71f370; seed 1001, 300 iterations) is installed in ot9-robin, engine-verified and reopened in fresh processes with the same identity [rec: candid-wood-6113]; the frozen ten-seed evaluation passed 10/10 — 8.0 s by truncation, no `fallen`, peak tilt at most 5.35 deg [rec: candid-wood-6113]. The final design is measured equal to the ot8 baseline with no mechanical, task or reward change [rec: long-glacier-5252]. Both suites and the packaged lifecycle gate are green at the final revision, ADR-405 `ae588e82`, which fixed the report's third defect (stale `accepted_geometry` in script.json) [rec: lively-eagle-0275]; `docs/probes/ot9/REPORT.md` is updated to it, and its remaining defects are a systematic ~0.84 m drift and unmeasured robustness [rec: falling-fountain-6090] [rec: lively-eagle-0275]. Done is re-claimed for critic review [rec: lively-eagle-0275]. Owner boxes are unticked [rec: falling-fountain-6090].

*Reconcile judgement*: status flipped `open` → `working` — the run has measured evidence on every criterion, and completion is the owner's and critic's call, not this pass's (the B1 precedent). The charter itself is recorded by `silver-cloud-5850` and `shy-fjord-4367`; the B1-B5 gaps, declared by `curious-branch-9704`, are parented here following the ot5-ot8 precedent [rec: curious-branch-9704].

## Negative knowledge

None yet.

## Provenance

- silver-cloud-5850 — the ot9 charter (ADR-404): train Robin under the accepted 8 s task, ten fixed reset seeds, existing 30-degree and fallen limits; committed, not launched
- shy-fjord-4367 — before first launch, claude-opus-5-5 for every role and product call with no fallback; bars unchanged
- curious-branch-9704 — the ot9 operator directive: the charter verbatim, B1-B5 declared as gaps
- candid-wood-6113 — B2 identity reopened; B3 ten-seed evaluation 10/10
- long-glacier-5252 — B4 measured, design unchanged from ot8
- falling-fountain-6090 — B5 closing report; done claimed for critic review
- lively-eagle-0275 — ADR-405 fixed REPORT defect 3; report moved to the final revision, done re-claimed
