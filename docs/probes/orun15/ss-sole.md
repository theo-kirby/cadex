# orun15 P1: ss-sole, the second hind stands nearer the body (`hind_place`)

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 13).
Follows `hlk8-mirror.md`: on hlk8-sole-50 the fold belongs to whichever
hind lands second (U 0.29 on the second, 0.02 on the first, swapped by the
mirror), and the second hind lands about 340 mm past the fore prints
against the first's 8 mm. The critic asked for a lever on that stance;
the clip's is refused, so the screen trains a term on it.

## The clip lever: refused

- The first lever was the clip (O7: the clip carries the gait). hlk8-sole's
  clip has RH landing first (`hind_lag` 0.15) and LH second, and stands
  both stances 120 mm forward of their standing places (`stance_shift_mm`,
  ADR-777). The plan stood the second hind, LH, further back.
- **The generator refuses every LH shift under 120 mm** (stride 700 mm,
  swing 40 mm, `j_hip_l`, `j_knee_l` and `j_pawpin_l` at a stop): it
  misses LH's swing target by 13.2 mm at 0 (stride phase 0.619), 8.9 at
  30 and 11.4 at 45 (0.571), 1.7 at 60, 3.3 at 90, 3.4 at 75 and 1.4 at
  105 (0.524). Each refusal is about 20 s; no revision was accepted. The
  scripts are `~/orun15-queue/orun15-ss*.py`.
- A side effect: the first queued try set the stored `fore_sync_w` back
  to 2 (project commit `61f30ea`) before its script was refused, so the
  project's accepted revision is fl-sole's script with `fore_sync` w2
  until ss-sole's build replaces it.

## The term (O7: scored per step before launch)

`place_term.py` (this directory) reads where each hind paw stands, as the
trainer reads it: the paw's subtree centre of mass (`phl_x`, with its
claws and spring) ahead of the whole model's (`com_x`, the chest frame's
subtree), + 311 mm (`hind_reach`'s standing place). The candidate
**`hind_place`**: per hind, on the floor × max(0, place − 150) / 50,
averaged over the two hinds; weight −10, a literal (the 64-parameter cap).

```
pixi run python docs/probes/orun15/place_term.py \
    ~/cadex-projects/leo/runs/hlk8-sole/train/cat_model-model.xml \
    $E/hlk8-sole-50 $E/hlk8-sole-50m $E/k8-sole-50 $E/fl-sole-50
```

| evaluation | leg | place at touch-down mm (median, p90) | on U frames (frames) | on F/R frames (frames) | `hind_place` a step | its share on U frames |
|---|---|---|---|---|---|---|
| hlk8-sole-50 | LH (second) | +208 (+236) | +194 (387) | +91 (849) | 0.082 | 0.73 |
| hlk8-sole-50 | RH (first) | +133 (+199) | +109 (17) | +78 (842) | 0.016 | 0.03 |
| hlk8-sole-50m | LH (first) | +141 (+216) | +194 (20) | +83 (850) | 0.026 | 0.13 |
| hlk8-sole-50m | RH (second) | +209 (+238) | +199 (385) | +92 (892) | 0.085 | 0.73 |
| k8-sole-50 | LH | +174 (+208) | +163 (139) | +60 (1002) | 0.030 | 0.47 |
| k8-sole-50 | RH | +122 (+163) | +129 (191) | +22 (753) | 0.004 | 0.79 |
| fl-sole-50 | LH (second) | +197 (+227) | +195 (239) | +73 (1096) | 0.059 | 0.75 |
| fl-sole-50 | RH (first) | +133 (+184) | +132 (23) | +87 (795) | 0.013 | 0.06 |

- **The second hind stands 65–75 mm further forward than the first** at
  touch-down on every split policy, and the mirror moves the difference
  with the role. Its U frames sit at +194 to +199, its flat ones at
  +73 to +92.
- The term charges the folded leg 0.059–0.085 a step, three quarters of
  it on U frames, and the first hind 0.013–0.016. At −10 a U frame at
  +194 costs about 4.4 (averaged over both legs), about `paw_fold`'s
  cost of a 25° fold; hlk8-sole-50 as it stands would pay 0.49 a step.
- **Its blind spot:** k8-sole-50's RH (hinds tied) folds at +129, under
  the 150 mm threshold; the term is for the second hind's long reach, not
  every fold.
- **Its cost early in a cold run:** hlk8-sole-25, the cold shuffle at
  0.69 m/s, stands both hinds far forward the whole stance (touch-down
  LH +287, RH +256 mm; F/R frames +276 / +242), so the term charges it
  1.20 a step (12 at −10, against `alive`'s 4). It will push a cold
  policy's hinds back from the first iterations, not only at speed;
  whether that costs the gallop is what +25 shows.
- **Its risk:** `overreach` asks each hind to land at or past the fore
  prints; the first hind passes at +8 mm from a +133 mm place, so a
  second hind pulled under +150 should still clear it, but the median
  overreach will fall.

## The screen

- `~/orun15-queue/orun15-hp.py` is `orun15-hlk8.py` (hlk8-sole's script,
  project commit `e11bd4f`) plus the `hind_place` block (13 lines) after
  `hind_lag`: 22 terms, the model leo-v04.2's, `fore_sync` w2 as stored.
- Cold, 50 iterations, 4,096 envs, seed 0, `budget_s` 4,600
  (hlk8-sole's). Queued 22:36:44 with `docs/probes/orun13/queue_run.py
  ~/cadex-projects/leo ss-sole 4600 50 ... --envs 4096 --seed 0 --after
  fl-sole --build ~/orun15-queue/orun15-hp.py`, in its own
  `MemoryMax=30G` scope (`~/orun15-queue/ss-sole.log`).
- **Built** 22:40:17, accepted revision **`29298667`** (3.5 min). The
  bundled `cat_model-model.xml` is byte-identical to hlk8-sole's (model
  `b2bb0efe`, leo-v04.2), so no clearance pass is needed; the
  `gallop-task.json` differs from hlk8-sole's only in its reward list,
  `hind_place` (w −10) added, 22 terms against 21.
- **Launched** 22:40:20. **Timed:** iteration 10 at 22:57:07, 923 s of
  trainer wall time (16.8 min, hlk8-sole's too); the trainer's ETA then was
  3,272 s more, so about 4,200 s in all, inside the 4,600 s budget. +25
  falls near 23:25 and 50 near 23:55. Reward per step 13.5 at 10 (it
  falls from 20.0 as episodes lengthen, 45 → 84 steps).

## Keep rule (written before launch)

Judged at 25 and 50 against hlk8-sole at the same checkpoint:

- the second hind's U under 0.2;
- the first hind's U no worse than hlk8-sole's + 0.03;
- rotary on at least 5 of 10 seeds (`p2_lag.py`, as fixed below);
- speed at least 90% of hlk8-sole-50's 2.17 m/s (1.95) at 50.

**Stop at 25** if the second hind's median touch-down place has not
moved back from hlk8-sole-25's (+287 mm for LH, its second hind), or the
second hind's U is above hlk8-sole-25's (LH 0.01) by more than 0.10.

## p2_lag.py's rotary count (fixed this iteration)

`docs/probes/orun13/p2_lag.py` called a seed rotary when more than half
of *all* its strides were rotary, so tied strides (two first landings in
one 20 ms frame) and unordered ones (a paw landing twice, a tap) counted
against the order. Ties are a lag fault, read in the `together` columns
and by O3's 40 ms; taps are `no_tap`'s. It now calls a seed rotary when
more than half of its **ordered** strides (rotary or transverse) are
rotary, over at least 5 of them, and reads `–` below that; the old count
is still printed as "of all strides".

| evaluation | rotary seeds, ordered strides (new) | under 5 ordered | all strides (old) | hinds together | fores together |
|---|---|---|---|---|---|
| hlk8-sole-25 | 9/10 | 1 | 9/10 | 0.00 | 0.00 |
| hlk8-sole-50 | 10/10 | 0 | 9/10 | 0.10 | 0.20 |
| hlk8-sole-50m | 10/10 | 0 | **0/10** | 0.05 | 0.19 |
| fl-sole-25 | 3/10 | 7 | 0/10 | 0.00 | 0.05 |
| fl-sole-50 | **10/10** | 0 | **4/10** | 0.26 | 0.00 |

- The mirror (hlk8-sole-50m) now reads as the original does, as
  `legs.py` did (119 of 131 ordered strides rotary).
- **fl-sole-50's verdict rested on the old count.** Under the new one its
  rotary clause passes (10/10, every ordered stride RH-first rotary but
  one), and its hind clause sits on the line: the per-seed hind lag is
  0.095 of a ~0.42 s stride (40 ms) on 7 seeds, 0.100 on one, 0.050 and
  0.072 on two, with the hinds in one frame on 0.26 of strides. Its keep
  rule passes on its letter at the 40 ms line. It still cost RH's heel
  (0.36 → 0.08) and the taps (no_tap 1.54 → 1.63), which its rule did not
  name; that, not the rotary count, is the case against keeping it.
  `fl-sole.md` is frozen and not edited.

## Judged at 25 (`ss-sole-25`, 10 seeds, CPU; iteration 14)

+25's checkpoint `73b56cf3`, judged on its own bundle (`29298667`), with
the commands of `hlk8-sole.md` and `place_term.py` above.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH | at toe-off LH / RH | **U LH / RH** | floor pitch ° in stance LH / RH | on-ground F / R / T / U, LH | heel mm in stance LH / RH | stride mm LH / RH | touch-down place mm LH / RH | `hind_place` a step | hind lag / together | LH leads | rotary seeds (ordered) | pin p95 °/s LH / RH (swing) | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hlk8-sole-25 | 0/10 | 0.48 / 0.69 / 0.85 | 0.13 / 0.35 | 0.00 / 0.05 | 0.01 / 0.19 | +1.3 / +0.9 | 0.13 / 0.85 / 0.01 / 0.01 | 7 / 2 | 93 / 131 | +287 / +256 | 1.203 | 0.333 / 0.00 | RH first | 9/10 | 208 / 129 (140 / 99) | 2.13 (j_spine) | 0.00 | 2.0 |
| **ss-sole-25** | 0/10 | 0.84 / 0.96 / 1.20 | 0.01 / 0.15 | 0.00 / 0.02 | **0.03 / 0.12** | **−89.6** / +1.1 | 0.00 / 0.09 / **0.87** / 0.03 | **73** / 14 | 244 / 186 | **+34 / +115** | 0.005 | 0.140 / 0.15 | 0.78 | **3/10** (2 under 5) | 497 / 396 (246 / 204) | 1.51 (j_wrist_l) | 0.00 | 2.0 |

- **The term did what it charges**: both hinds stand far nearer the body
  from the start (touch-down +34 / +115 mm against +287 / +256), and it
  pays 0.005 a step, nothing. The cold shuffle did not collapse: 0.96 m/s,
  longer strides (244 / 186 mm), episodes 553 steps at 25 (hlk8-sole 1,078).
- **But LH found the cheap way under it: it stands on the tip of its paw.**
  On 0.87 of its on-ground frames it is on its toes with the paw's floor
  pitch at −89.6° (pin −0.8°, on its flat stop): the metatarsus and paw
  stand vertical, the heel 73 mm up. That is not O2a's digitigrade (toe
  bulbs and pads down, the pin toes-up of the metatarsus); it is a stilt.
  The heel share fell on both legs (0.01 / 0.15 from 0.13 / 0.35).
- The order fell apart: the hinds lie 0.140 of the stride apart and in one
  frame on 0.15 of strides, LH now leads (0.78), and only 3 of 10 seeds
  read rotary over ordered strides (hlk8-sole-25 9/10). No flight.
- O6: worst drive `j_wrist_l` 1.51 × rated RMS, peak margin 0.00. O9: loop
  gap max 2.0 mm; pins p95 497 / 396 °/s, no swing over 900, no flapping.

## Verdict at 25: stopped (dead end, cold)

With LH leading, RH is the second hind. Its place moved back (+256 →
+115), but **its U is 0.12, above hlk8-sole-25's second-hind 0.01 by
0.11, over the rule's 0.10**: the stop rule fires, by a hundredth. The
stilted LH and the lost rotary order are the larger case against running
it on. Stopped at 25 (23:16:54, `loop.request_stop`, state `stopped`).

A cold run lets the charge shape the stance before there is a gallop to
protect, and the cheapest stance under it is a vertical paw. The critic's
fallback is the warm retry, already queued before the judge:

## ssw-sole: the same task, warm from hlk8-sole-50

- ss-sole's bundle (revision `29298667`, 22 terms), `--init-from`
  hlk8-sole-50 (`4ac25fff`) across the one task change, with
  `--init-from-parent-task` (hlk8-sole's bundle) and
  `--init-from-task-change` (the trainer logged "the task changed in
  ['reward']"), `--critic-warmup 5`, `--learning-rate 3e-5`, 4,096 envs,
  seed 0, 50 iterations, `budget_s` 4,600.
- `docs/probes/orun13/queue_run.py` gained `--parent-task` and
  `--task-change` for this (the loop's `init_from_parent_task` /
  `init_from_task_change` settings).
- Queued 23:02:38, **launched 23:17:41** when ss-sole stopped
  (`~/orun15-queue/ssw-sole.log`); reward per step 33.0 at 0
  (hlk8-sole-50 ended at 30.5 without the term).
- **Keep rule (written before its first checkpoint):** judged at 25 and
  50 against hlk8-sole-50: the second hind's U under 0.2 (from 0.29), the
  first hind's no worse than 0.05, rotary on at least 5 of 10 seeds,
  each hind's heel share at least 0.3, no hind on its toe tip (floor pitch
  in stance within ±30°), and at least 1.95 m/s at 50. **Stop at 25** if
  the second hind's U is not below 0.25 or its median touch-down place
  has not moved back from +208 mm.
