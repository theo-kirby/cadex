---
node_id: bf6121bf-0560-55aa-baaf-385f3d5030d1
slug: empty-bay-8350
title: 'ot11 R1/P4 walk round 1: r1-clearance collapsed, best checkpoint fails 10/10 seeds walking backwards; round 2 cites it'
created_at: '2026-09-30T22:13:29+00:00'
parents:
- lively-ledge-7354
summary: ''
---
## What

Read and published walk round 1 (`r1-clearance`) of the supervised loop session on `ot11-quad-1`. Checked its evaluation against the frozen 13-predicate walk spec, and checked that round 2's registration cites a measurement from it. Commit `74debd53`: a README section, the receipt `retained/p4-quad-1-r1-evaluation.json`, and the seed-1101 filmstrips (252 KB and 269 KB).

## Why

The critic named R1 as the next unit and asked for exactly this: check the session is alive, record round 1's evaluation per seed and per predicate with gait metrics and the filmstrip, and check that round 2's revision cites round 1. All of it was done as asked. No GPU job was started; the session's own round 2 is the only job on the GPU.

## Method

1. `pgrep -f "rounds.py --project ot11-quad-1"` showed the session alive (pids 733499 and 733611). It still was at the end of this iteration, in turn 1.
2. Waited on the project's `loop-ledger.jsonl` until it had a `train_ended` row and an `evaluated` row.
3. Checked validity:
   - The evaluated revision `8498db6e…` has a spec block equal to `retained/walk-spec-block.txt`.
   - It differs from the registered `db1cfc96…` only in the declared policy sha256.
   - The model is `ade106a6…`, as registered.
   - The declared policy `8db0cb61…` is `runs/r1-clearance/train/walk_task.best.cxpolicy`, from iteration 273.
4. Tabulated per-seed and per-predicate values, per-foot steps, slip and clearance, reward terms and commanded speeds from `evaluations/8498db6e1ff5-8db0cb619fc4/evaluation.json`.
5. Looked at the seed-1101 overview and detail filmstrips, on the dark floor.
6. Read round 2's ledger row and registration, and diffed its script revision `9e3a1b9b…` against 0019.
7. Ran the four `cli/tests/test_ot11_*` suites: 68 passed.

## Result

**What is true now:**
- **Round 1 collapsed.** `r1-clearance` (seed 7, 1000 it × 2048 envs, 2,350 s budget, `--stop-on-collapse`) stopped at iteration 568 after 1,542 s of GPU time. The reward per step was negative throughout, so ending an episode paid.
- **Its best checkpoint fails all 10 seeds, for the right reasons:**
  - **Direction:** W3 fails 10/10, with speed ratio −1.46 to −0.05. Every seed with a value moves backwards, against commands of 61–93 mm/s.
  - **Stepping, slip and floor:** W5-share 10/10 (0.00–0.19), W6 10/10 (0.04–0.07 hip heights), W7 10/10 (slip 0.48–0.90) and W10 10/10 (−0.11 to −0.19).
  - **Turning and idle rear legs:** W4-heading fails 8/10 (up to 173°) and W9 8/10 (up to 9.5). On seed 1105 the rear feet take 2 and 3 steps and the front feet 19 and 13.
  - **Tipping:** seeds 1102, 1106, 1107 and 1110 tip, failing W1 and W2.
  - **The film matches:** it shows the trunk turning and backing away, legs splayed.
- **Round 2 cites round 1.** `r2-bounded` was registered at 22:11:59Z: seed 11, 800 it × 2048 envs, 2,380 s (within 2,400), `--stop-on-collapse`.
  - Its reason quotes round 1's W3, W7, W10 and W6 ranges and the collapse.
  - The change is reward-only: every cost is tanh-bounded; alive goes from 2 to 3; the speed Gaussian widens from 0.25 to 0.4; sink is quadratic at weight −2 below 2 mm; heading weight goes from −2 to −1.5 and yaw-rate weight from −0.3 to −0.5.
  - The spec block is still equal to the retained one.
  - It was training when this iteration ended.
- Walk GPU time so far: 1,542 s (r1), with r2 in progress.

**Concerns and notes for the next iteration:**
- R1 has no passing evaluation. This is a loop round, not a confirmation.
- The next iteration should read round 2 the same way once it has an `evaluated` ledger row (about 22:52Z plus evaluation). Start no GPU job while the session lives.
- The reconcile tail is 1 record after this one, so it is not due.
- No new dependency.

Dispatch closed: 1 unit — walk round 1 read and published: r1-clearance collapsed at iteration 568, and its best checkpoint (iteration 273) fails the frozen walk spec on 10/10 seeds, walking backwards with slip, sinking and idle rear legs; round 2 r2-bounded cites those measurements and is training.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 74debd53e7005773fd8572ae9d75d3c84f017df0

## State Impact

- target: smooth-fountain-9832 — walk round 1 r1-clearance collapsed at iteration 568 (1542 s GPU); its best checkpoint 8db0cb61 (it 273) fails the frozen 13-predicate walk spec on 10/10 seeds, moving backwards (W3 -1.46..-0.05) with W5-share/W6/W7/W10 failing on all seeds and 4 seeds tipping (commit 74debd53, retained/p4-quad-1-r1-evaluation.json); round 2 r2-bounded (seed 11, 2380 s) cites those measurements and is training
