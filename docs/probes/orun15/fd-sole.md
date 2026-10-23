# orun15 P1: the fold screen, sf-sole: sp-sole's task plus the contact-gated `paw_fold`

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 3).
Follows `sp-sole.md`: the spring as built left sp-sole-50 folded
(U 0.32 / 0.29). This is ladder step 3's task lever. The model lever,
leo-v04.1, is in `leo-v04.1.md`.

## The term (O7: scored per step before launch)

- **`paw_fold`, weight −10.** It is orun14's fd-sole term, never trained
  (`orun14/tr-sole.md`). Per hind leg it charges
  (paw or heel down) × max(0, floor pitch − 5°) / 30, and the two legs
  are averaged.
  - The floor pitch is `paw_flat`'s observed-channel estimate: the pin
    toes-up, less the metatarsus's observed pitch, + 1.9°.
  - The gate is contact the policy observes (`ch*_down`, `kh*_down`),
    not the clip's stance, so a fold outside the clip's stance is
    charged too.
  - It is a literal, since leo is at the 64-parameter cap.
- **Scored on sp-sole's v04 traces** (`orun14/fold_term.py`, run this
  iteration on the bundle's model):

| evaluation | leg | U frames: paw down / heel only | U floor pitch ° q1 / med / q3 | U past `paw_flat`'s 15° | `fold` on F / R / T / U / swing | `fold` charges U |
|---|---|---|---|---|---|---|
| sp-sole-50 | LH | 383 / 62 | +18 / +25 / +32 | 0.86 | 0.008 / 0.002 / 0.000 / 0.676 / 0.000 | 1.00 |
| sp-sole-50 | RH | 381 / 5 | +16 / +23 / +29 | 0.79 | 0.025 / 0.007 / 0.000 / 0.602 / 0.000 | 1.00 |
| sp-sole-25 | LH | 397 / 9 | +13 / +16 / +20 | 0.57 | 0.021 / 0.006 / 0.000 / 0.403 / 0.000 | 0.99 |
| sp-sole-25 | RH | 416 / 0 | +12 / +15 / +24 | 0.53 | 0.001 / 0.007 / 0.000 / 0.498 / 0.000 | 1.00 |

  - It charges every U frame, 0.60–0.68 a frame at 50.
  - It charges at most 0.025 a frame on flat (F) or rolling (R) paws, and
    nothing on toes (T) or in swing, so it leaves O2's heel-up roll alone.
  - At weight −10, a leg folded at +25° costs about 6.7 a frame (3.4
    averaged over both legs), against `track_speed`'s 20 at full speed.
    It mirrors `paw_flat`'s +10.

## The bundle

- `~/orun15-fd.py` is the project's `script.py` at `leo-v04`, plus the
  term in place of the "stopped untrained" comment. It is not committed
  here (a project script copy).
- `cadex script --set`: accepted revision **`b32a6ace`**, digest
  `2e08b19e`, built in 3.5 min (task-only edit). The bundle task is
  `69ee341b` with 20 terms (sp-sole's 19 plus `paw_fold`).
  `cat_model-model.xml` is byte-identical to sp-sole's, so the model is
  leo v04 and nothing is tagged.

## The run

- **sf-sole:** cold, 50 iterations, 4096 envs, seed 0, unroll 20, a
  checkpoint every 25, `budget_s` 5,100 (85 s/it × 50 + 20%). Launched
  2026-10-21 14:55:31 through `orun13/queue_run.py` (`cadex_cli.loop`
  `register`, `retain_training_view`, `launch`) in its own
  `systemd-run --user --scope -p MemoryMax=30G`.
- **Timing (O8):** iteration 9 at 874 s (sp-sole: 855), about 70 s/it
  at 4096 envs. The trainer's ETA at 9 was 3,495 s for 40 more, about
  4,370 s in all, inside the 5,100 s budget. Iteration 9: 13.65
  reward/step (sp-sole: 13.73), episode 81.1 steps, σ 0.884.
- **Judging:** at 25 and 50 with `orun11/judge.py` (seeds 1001–1010) and
  `orun14/paw_floor.py`, watching LH first. LH is the leg the spring did
  not move.
- **Stop early** at 25 if LH's U has not moved below sp-sole-25's 0.13
  band at a comparable speed. If the fold term only shows at speed, U is
  read at 50.
- **Keep rule:** U under 0.2 on both legs at 50, at a speed within 10% of
  sp-sole-50 (≥ 1.96 m/s median), with the heel share no worse than
  sp-sole-50's 0.41 / 0.26 less 0.05.

## Queued behind it

**sfp-sole:** sf-sole's task (with `paw_fold`) on leo-v04.1, cold, 50
iterations, 4096 envs, `--expect-revision f3482223`
(`~/orun15-sfp-queue.log`). It starts when sf-sole frees the machine
lock. Against sf-sole the coil's preload is the one change
(`leo-v04.1.md`).
