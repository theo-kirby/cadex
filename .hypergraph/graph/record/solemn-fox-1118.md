---
node_id: 9df7f0ae-4ed3-51a3-98b9-b28aeb0291a0
slug: solemn-fox-1118
title: 'W1 first attempt on orun3-biped: designing, training, failed stages live; evaluate invisible on the page, live checkpoint play blocked by a menu pick'
created_at: '2026-10-05T14:51:00+00:00'
parents:
- little-cloud-9989
summary: ''
---
## What

A first full W1 attempt on `orun3-biped`. The dashboard was opened before step 1 and never reloaded (`performance` shows one navigation and the page's marker survived to the end). It covered the two revisions through `cadex mcp`, a real `cadex walk` leg on the RTX 5090 with checkpoints on, and `evaluate` through `cadex mcp`. The run produced most of W1's evidence, and it found two gaps: one in my driver, and one real defect in the product. Most of W1's evidence now exists, but W1 is **not met**. Its stage-by-stage claim fails at `evaluating`, and no checkpoint rollout was played on the live page.

## Why

The critic asked for a housekeeping reconcile first (fold sunny-oak-9772 and little-cloud-9989, move P1 to working). Then it asked for W1. **I did not run the reconcile.** This dispatch is a work iteration, and its instructions forbid the hypergraph-reconcile skill, `hypergraph update` and state-node edits "no exceptions". The tail is three records with this one (sunny-oak-9772, little-cloud-9989 and this one), which meets the charter's "three unreconciled records" trigger. So the next pass should be a reconcile, and P1 should move to working in it. I took W1, the highest-ranked open criterion and the critic's named unit.

## Method

- **Machine.** The 5090 was idle (0 %, 2 MiB) and no walk or trainer was running. The walk's train leg takes the machine slot itself (ADR-543).
- **Driver.** `/tmp/orun3-w1/drive.py` is not committed. It ran `cadex app --projects ~/cadex-projects --port 8811` on 127.0.0.1; ports 8792 to 8795 belonged to other dashboards. It held one Chromium page through `cli/cadex_cli/browser.py` at 1280×820 in the dark theme, read the overlay, timeline and checkpoint hooks once a second, and took a screenshot at each stage. It was an MCP client of `./cadex mcp --project` for the agent's calls, and it launched `./cadex walk` as a subprocess. **Assumption:** I acted as the agent through `cadex mcp`'s real `tools/call` path, sending scripted calls rather than using a model.
- **Attempt 1.**
  - Revision 14 was `set_params {policy_on:0, hip_spacing:56}`. Revision 15 was `edit_script`, adding `assembly.success([completed ≥ 1, max_tilt_deg ≤ 45], seeds 1101–1105)` so that `evaluate` has a spec.
  - Then `cadex walk --out runs/orun3-w1 --iterations 120 --envs 1024 --checkpoint-every 20` ran. Its train leg was refused at exit 3 in 1.4 s: "25 policy channel(s) name no onboard sensor that measures them …". The biped predates the grounding rule.
  - The page turned to **failed** with that reason. This is the evidence for the failed stage (`w1-try-failed.png`).
- **Attempt 2.** I used a new driver on the same project, with the page again opened before the first call.
  - Revision 16 was `set_params {foot_len:84}` and revision 17 was `set_params {foot_w:38}`.
  - Then the same walk ran with `--allow-ungrounded` as `runs/orun3-w1b`. **Assumption, reversible:** grounding 25 channels in sensors is a design job, not part of watching the lifecycle, so the short leg trains anyway, as the refusal itself offers.
  - Then `evaluate {}` ran through a fresh `cadex mcp` session.
- **The checkpoint gap, reproduced.** I made a copy, `orun3-biped-w1dbg` (since deleted), with `orun3-w1b` set back to `running` and its `progress.json` refreshed every 5 s. On a fresh page, the viewport turned to the run by itself and followed to the newest stop, labelled `final policy · 6/6 · newest`, with no JS errors. After a Revisions-menu row click it stayed on revision history, because `review.js:938` sets `ckpt.chosenSource = true` on a menu pick.

## Result

**What is true now, measured:**
- **Designing.** Both revisions showed up on the never-reloaded page within one poll. The stage was `designing` with "revision 16 accepted · just now" and then the same for revision 17. The activity line showed `set_params values={foot_len} · just now`. The timeline showed `revision 16 · current · 16/16 · newest`, with `changed: foot_l, foot_r · against revision 15 · ghost: revision 15`, the feet tinted in `--info` and the old feet ghosted (`w1-try-designing-timeline.png`).
  - The Revisions menu and the timeline agreed: 17 rows, and the newest was current.
  - Revision 14 (`hip_spacing`) read "no part changed", because the thighs only moved. That matches ADR-547's moved-is-not-changed rule.
- **Training.** The walk exited 0 in 581 s. Its legs were train 552.8 s, declare 0.8 s and rollout 1.4 s, and the trainer reported 456.4 s wall time for 120 iterations at 1024 envs.
  - The overlay turned to `training` on run `orun3-w1b` 4 s after the walk started (`w1-try-training.png`).
  - **Five checkpoint rollouts landed during training** beside their checkpoints, iterations 20 to 100. They were all `ready` in `stage.checkpoints`, with no failure. Four 8 s traces were 320 to 324 KB each, and the 0.74 s one was 36 KB.
  - The best reward per step was 1.72 at iteration 114.
  - The trainer's 3.8 s per iteration, against foot90's 1.3 s, matches the stalls snowy-water-3502 already recorded (about 460 s per run, with rollouts on or off). It is not a new rollout cost.
- **Evaluate.** It ran with verdict `fail`, 0 of 5 seeds passing: max tilt was 70 to 109°, and 4 of 5 episodes did not complete. That is expected after 120 iterations.
  - The `cadex mcp` call took about 68 s, almost all of it the session's engine build. The evaluation itself took **0.23 s** (`wall_time_s`).
- **The page was never reloaded**, from the first screenshot to the last, in each attempt. There was one navigation entry, and the `window.__w1` marker was intact.

**Why W1 is not met (the next iteration must know):**
1. **Product defect: an evaluation is invisible on the page.**
   - `project_stage` reads `evaluating` from an evaluation directory with no report yet. But that directory exists only for the last ≈0.3 s of a ≈68 s `evaluate` call, so the 2 s poll never saw it.
   - The activity log (ADR-549) writes a call only when it *returns*. So for the whole minute the activity line still showed the previous call (`set_params … foot_w`), and after the call it read `evaluate · just now` with the stage back at `designing`.
   - Suggested fix, one unit with an ADR: log a call's *start* as an in-flight activity entry. The overlay would then show `evaluate · running 40 s`, and `project_stage` would read an in-flight `evaluate` as `evaluating`. This adds no tool, argument or result field, so `test_project_tool_surface.py` stays unchanged.
2. **Driver error, not a defect: no checkpoint was played on the live page.**
   - To screenshot the revision timeline, the driver opened a revision from the Revisions menu. That counts as a hand pick (`ckpt.chosenSource`), and ADR-545 holds a hand pick for the whole visit, so the viewport stayed on revision history while five rollouts were ready.
   - On a fresh page the follow works with these same real traces.
   - For the re-run, either have the driver pick `run:<run>` in `#view3d-source` when training starts, as an owner would, or decide whether a hand pick should give way to a *new* run starting. That second option changes page behaviour and needs an ADR.
- **Screenshots kept** (PNG, dark floor, each ≤ 300 KB): `docs/probes/orun3/w1-try-designing-timeline.png` (245,693 B), `w1-try-training.png` (239,582 B) and `w1-try-failed.png` (238,781 B). They are partial evidence; W1's final set comes from the re-run.
- **Project state:** `orun3-biped` now has revisions 14 to 19, failed run `orun3-w1`, finished run `orun3-w1b` with five checkpoint traces (run outputs, not committed) and one evaluation. Its working tree had an uncommitted `evidence/foot90-walk.json` change before this unit, and I left it alone.
- **Not run:** neither suite, because no code changed. W1's "both full suites pass" still has to be measured on the final run.
- **Reconcile due:** the tail is three records (sunny-oak-9772, little-cloud-9989 and this one), and P1 should move to working.
- No new dependency.

Dispatch closed: 1 unit — W1 first full attempt on orun3-biped: designing, training, failed stages and 5 live checkpoint rollouts measured on a never-reloaded page; evaluate invisible (0.23 s of a 68 s call) and live checkpoint play blocked by the driver's menu pick, so W1 stays open

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: 7a37d67a74790e18d6d9d4e52b04d198dab985b5

## State Impact

- target: lucky-prairie-0215 — first full attempt measured on a never-reloaded page: designing (revisions 16 and 17 tinted on the timeline), training (5 checkpoint rollouts landed during a 120-iteration 5090 leg) and failed (ungrounded refusal) shown; not met: an MCP evaluate is invisible (evaluation dir lives 0.23 s of a 68 s call, activity logged only on return) and no checkpoint played live because the driver's Revisions-menu pick held the viewport
