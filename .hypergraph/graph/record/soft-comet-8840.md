---
node_id: ef3476ed-5395-5d55-a4d5-83fe37d74ec1
slug: soft-comet-8840
title: 'W1 re-run on orun3-biped: one never-reloaded page shows designing, five live checkpoint rollouts, evaluating and the result'
created_at: '2026-10-05T15:49:46+00:00'
parents:
- tiny-bloom-2937
summary: ''
---
## What

W1 re-run on `orun3-biped`, after ADR-553 fixed gap 1. One headless Chromium page opened on `/p/orun3-biped/` before the first revision and was never reloaded: `performance` showed one navigation entry, and the `window.__w1` marker `opened-1791213535345` survived to the last screenshot. The page watched:

- two revisions accepted through a real `cadex mcp` `tools/call`;
- a 120-iteration `cadex walk` training leg on the RTX 5090, with checkpoints every 20 iterations and their rollouts;
- an `evaluate` through a second `cadex mcp` session.

Every stage the charter names showed in the overlay. Five checkpoint rollouts replaced each other in the 3D viewport while the run trained. Both suites passed afterwards. W1's evidence is complete; the owner holds the checkbox.

## Why

The critic named this unit: W1's re-run, the highest-ranked open criterion. I followed the method it gave:

- open the page once, before the first revision;
- pick `run:<run>` in `#view3d-source` when training starts;
- take a screenshot at each stage.

No deviation, except one I didn't plan: a first try at the first revision was refused (below), so the driver was restarted on a fresh page before any revision was accepted.

## Method

- **Driver.** `/tmp/orun3-w1c/drive.py` is not committed. It is solemn-fox-1118's driver with three changes:
  - It picks sources through `#view3d-source`'s `change` event, as an owner would: `revisions` right after opening, and `run:orun3-w1c` on the first poll that reads `training`. It no longer clicks a Revisions-menu row.
  - The revisions are revision 20 `set_params {policy_on: 0, foot_len: 86}` and revision 21 `set_params {foot_w: 40}`.
  - The run is `runs/orun3-w1c`.
- **Server and page.** `cadex app` served `~/cadex-projects` on 127.0.0.1:8811. The page was `browser.py` at 1280×820, dark theme, with the overlay expanded. The driver read the page once a second.
- **Walk.** `cadex walk --iterations 120 --envs 1024 --checkpoint-every 20 --allow-ungrounded --json`. That is the same reversible assumption as solemn-fox-1118: the biped's 25 ungrounded policy channels are a design job, not part of watching. The walk took the machine lock itself, which was free (`~/.cache/cadex/training.lock`, GPU idle).
- **Evaluate.** `evaluate {}` ran in a thread through a fresh `cadex mcp`, with the page read every 0.3 s.
- **First try, discarded.** `set_params {foot_len: 86}` alone was refused: "Policy output 'reed_policy' … was trained on a task bundle whose digest is …", because the walk had left `policy_on=1`. The never-reloaded page showed that call at once as an `error` activity line, `set_params values={foot_len} · failed: …`. Nothing was accepted. I restarted the driver with `policy_on: 0` in the first revision, as the last attempt did, so the page was again opened before any accepted revision.

## Result

**What is true now, measured on one never-reloaded page** (`docs/probes/orun3/w1-*.png`, each PNG ≤ 300 KB on the dark floor):

- **Idle.** At open: `idle`, "revision 19 accepted 32 min ago", run `orun3-w1b · done`.
- **Designing.**
  - About 6 s after each `set_params` returned, the page showed `designing`, with "revision 20 accepted · just now" and then "revision 21 accepted · just now".
  - The activity line showed `set_params values={policy_on,foot_len}` and then `set_params values={foot_w}`.
  - The timeline showed `revision 21 · current · 21/21 · newest` with "changed: foot_l, foot_r · against revision 20 · ghost: revision 20", and the feet were tinted (`w1-revision-a.png`, `w1-revision-b.png`).
  - **The menu and the timeline agree**: 21 rows, the newest (21) current, timeline ordinal 21.
- **Training.**
  - The page read `training` 2 s after the walk started, and the driver picked `run:orun3-w1c`.
  - **Five checkpoint rollouts replaced each other in the viewport while the run trained**, each labelled with its iteration and reward. The sequence was iteration 20 (reward 0.70753, 1/1), 40 (0.67739, 2/2), 60 (0.62213, 3/3), 80 (0.59649, 4/4) and 100 (0.6041, 5/5), every one `newest`. They landed at about 184, 282, 380, 477 and 574 s, against the walk's exit at 686 s.
  - Screenshots: `w1-training-checkpoint-1/2/3.png`. Between checkpoints the scrubber showed "1 newer checkpoint rolling out".
  - The overlay showed iteration out of 120, the ETA, the reward and loss sparklines, and the best reward.
  - Trainer wall time was 534.7 s for 120 iterations. The train leg took 652.9 s, then 1.05 s and 1.77 s for the following legs. The best reward per step was 1.168 at iteration 111.
  - The four 8 s traces are 327–328 KB each, and the iteration-100 trace is 32 KB. They are run outputs, not committed.
- **Evaluating.**
  - The first poll after the call began read `evaluating`, with the activity line `evaluate · running 2 s` in `--info` (`w1-evaluating.png`).
  - The call took about 74 s (693.9 to 768.0 s). The evaluation itself took 0.72 s (`wall_time_s`): verdict fail, `upright (5 of 5)` failing, with a film rendered for seed 1101. That is expected after 120 iterations.
  - After the call returned: `designing` (the walk had accepted revisions 22 and 23) and `evaluate · just now` (`w1-evaluated.png`).
- **Failed.** solemn-fox-1118's `w1-try-failed.png` already shows it, and this run adds the refused `set_params` as an `error` activity line on the live page.
- **Suites:** `pixi run test-engine` gave 2585 passed and 58 skipped. `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests` gave 1172 passed and 1 skipped, with the engine built, so the engine-needing tests ran. Both ran after the walk, with no training live.
- No code changed in this unit. No protocol or payload change, so no packaged gate.

**Concerns for the next iteration:**
- **The `evaluating` line names the evaluation directory.** The stage line read "evaluation dc0af1158165-d3a4… is running · 1 s", not ADR-553's "the agent's evaluate call is running". The directory-based reason won here because the evaluation directory existed early. The driver captured the stage once, at 1 s, and did not sample it again through the 74 s call. ADR-553's own tests pin that it holds for the whole call.
- **Progress stalls at each checkpoint.** Before each checkpoint (at iterations 39, 59, 79 and 99) the overlay read "no update 37–39 s". This matches the trainer stall snowy-water-3502 recorded with rollouts on or off, but this run did not measure it with rollouts off. V2's cost figure stands as recorded elsewhere.
- **The final policy is not shown on the run's scrubber.** After the walk exited, the scrubber still read `iteration 100 · 5/5 · newest` rather than adding the `final policy` stop. On a fresh page in solemn-fox-1118, the run did add `final policy · 6/6`. Not investigated in this unit; it is a candidate defect for the long-term rung.
- **Next units:**
  - C1, the closing report (`docs/probes/orun3/REPORT.md`), with these screenshots as W1's set.
  - A reconcile is due soon: the tail is tiny-bloom-2937 plus this record.
- `orun3-biped` now has revisions 20 to 23, run `orun3-w1c` with five checkpoint traces, and two evaluations. No new dependency.

Dispatch closed: 1 unit — W1 re-run on orun3-biped: one never-reloaded page showed idle, designing (2 MCP revisions, tinted timeline agreeing with the menu), training with 5 checkpoint rollouts replacing each other live, evaluating, and the result; 7 screenshots committed, suites green

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: d5067bce04b79ea11dd77a9962f3653d41dc44a5

## State Impact

- target: lucky-prairie-0215 — W1's evidence is complete pending the owner's tick: on one never-reloaded page, 2 MCP revisions (20, 21) showed designing with the tinted timeline agreeing with the menu, a 120-iteration 5090 walk showed training with 5 checkpoint rollouts (it 20–100) replacing each other live, an MCP evaluate showed evaluating from its first poll, both suites green (2585/58, 1172/1); screenshots docs/probes/orun3/w1-*.png
