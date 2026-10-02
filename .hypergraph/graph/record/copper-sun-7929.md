---
node_id: 24ae6204-c074-53de-ac15-c7762c6db00d
slug: copper-sun-7929
title: 'ot11 R1/P4 walk round 2 evaluated: r2-bounded no collapse, 0/10, still backwards; train/eval reward gap flagged'
created_at: '2026-09-30T23:03:47+00:00'
parents:
- empty-bay-8350
summary: ''
---
## What

Read walk round 2 (`r2-bounded`) on `ot11-quad-1` the same way as round 1, and published it (commit `150988d9`). The receipt is `docs/probes/ot11/retained/p4-quad-1-r2-evaluation.json`, the section is in `docs/probes/ot11/README.md` ("Walk round 2"), and the overview and detail filmstrips of seed 1101 are 169 KB and 247 KB.

## Why

This follows the critic's instruction to the letter: once r2-bounded had an `evaluated` row, read it per seed and per predicate, check the spec block against the retained one, check that round 3's registration cites a round-2 measurement, and say plainly whether the tanh-bounded costs fixed the collapse and the backwards motion. It serves R1 and P4 (the three-round loop). No GPU job was started. The agent's session (pid 735257) was alive throughout and was not touched.

## Method

Waited on `loop-ledger.jsonl` with read-only polls until the training ended (`train_ended`, finished, 2,251.49 s, policy `1a0f0d28…`). Then waited for the `evaluated` row (report `evaluations/80ba9fb9905e-1a0f0d28a2aa/evaluation.json`) and the `r3-nochatter` `train_registered` row. Built the receipt from the ledger, `progress.json`, the evaluation and the per-seed traces, using a throwaway script outside the repo. Checked the retained spec block text is contained in `script_history/0023-80ba9fb9905e.py`, in `0025-27da07544326.py` and in `script.py`. Measured the tray's forward travel over 0–3 s from each trace, before each seed's shove. Compared the training reward per step with the evaluation's, for rounds 1 and 2.

## Result

- **Round 2: 0 of 10 seeds pass.** Run `r2-bounded` used seed 11, 800 it × 2048 envs, a 2,380 s budget and `--stop-on-collapse`. It **finished all 800 iterations without collapsing**, so the bounded costs fixed the collapse. The **backwards motion is not fixed**: W3 is −2.06 to −1.22, backing away at 114–144 mm/s against a commanded 61–93 mm/s. The body is already backing away at 119–132 mm/s in the first 3 s, before every shove, so the disturbance is not the cause.
- Per predicate:
  - W1 and W2 now pass on all 10 seeds (none tip; tilt reaches 29.998° on 1107).
  - W3, W5-steps, W5-share, W6, W7, W8-low, W9 and W10 fail on 10 of 10. The rear feet take 0 steps on nine seeds and drag (duty 0.75–0.83, slip 0.51–0.63, about 10 mm into the floor). The front feet step 8–29 times at duty 0.16–0.47. W6 and W9 are not measured where no rear step exists.
  - W4-heading fails on 5 seeds (47–82°) and W4-lateral on 1 (1109, 0.29).
- The bounded costs sit near their caps: `speed_error` 0.92–0.99 of 1.0, rear clearance 0.42–0.43 of 0.5, `sink` 0.82–0.90 of 2.0. `speed_track` earns 0.00–0.02 of 2.0.
- **The spec block is still equal to the retained one** at the evaluated revision `80ba9fb9…` and at round 3's revision `27da0754…`.
- **Round 3 cites round 2.** `r3-nochatter` uses seed 23, 800 × 2048, 2,380 s and `--stop-on-collapse`, and was registered at 23:01Z. Its reason quotes round 2's W3, W7, W5-steps and W10 ranges and a knee-chatter reading. That reading is correct: −0.10 per step at −0.03 over four knees is about 364°/s RMS. It was training when this was written.
- **Concern for the next iteration (evaluation trust, the top priority):** training and evaluation disagree in both walk rounds.
  - Round 2's evaluated policy trained at +2.48 per step and scored −1.69 to −1.21 on the evaluation seeds.
  - Round 1's best trained at −1.39 and scored −7.51 to −4.34.
  - Both move backwards in the engine, although the reward pays forward speed. The existing parity probe (`runner/obs_parity.py`) compares sensor values at forced states, not a policy rollout, so it does not settle this.
  - The proposed next unit is a rollout parity measurement. Drive the evaluated policy in the trainer's own environment with mean actions, from an evaluation seed's drawn reset and command, and compare each step's reward terms and tray velocity with the engine's trace. If they disagree, it is a P3 trainer/engine drift defect that invalidates walk-round evaluations as feedback. If they agree, the gap is sampled vs mean actions or reset draws, and the loop's feedback is sound. No cause is claimed until it is run.
- The unfolded tail is now two records (`empty-bay-8350` and this one). Reconcile is forbidden in a work iteration, so it was not run.

Dispatch closed: 1 unit — walk round 2 read and published (0/10; the collapse is fixed, the backwards motion is not; the spec block is unchanged; round 3 cites round 2; the train/evaluation gap is flagged for a rollout-parity measurement)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 150988d95382184104e6e1382d949656929e387b

## State Impact

- target: smooth-fountain-9832 — walk round 2 (r2-bounded, seed 11, 800x2048, 2251 s, finished) evaluated 0/10: W1/W2 now pass everywhere, but W3 -2.06..-1.22 (backwards 114-144 mm/s from the first second), rear feet 0 steps with 0.51-0.63 slip; spec block unchanged; round 3 r3-nochatter registered citing round 2 (receipt retained/p4-quad-1-r2-evaluation.json, commit 150988d9)
- target: late-pond-2851 — open question: walk training reward disagrees with the engine evaluation in both rounds (r2 +2.48/step trained vs -1.69..-1.21 evaluated; r1 -1.39 vs -7.51..-4.34), and both policies move backwards in the engine; a rollout-level trainer-vs-engine parity measurement on the evaluated policy is the next unit
