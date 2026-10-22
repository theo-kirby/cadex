# orun16 SG: the slow heel lands against the clip; sg-s8's rules, written before launch

Verified against source: 2026-10-22. Frozen evidence (orun16, iteration 17).
Follows `sg-s7-25.md`, whose read named the next measurement: the clip's
heel over the slow late swing, where 0.97 of LH's and 0.79 of RH's slow
heel-down frames fall.

## The measurement: the clip is heel-up there, the policy is not

```
R=~/cadex-projects/leo/runs/sg-s7/train; E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/late_swing.py \
    $R/gallop_sg-task.json $R/cat_model-model.xml $E/sg-s7-25-{1000,1700,2400}
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/hock_land.py \
    $R/gallop_sg-task.json $R/cat_model-model.xml $E/sg-s7-25-{1000,1700,2400}
```

Heel above the paw's lowest point, mm (heel minus paw: 0 is heel-flat), by
frames from the clip's touchdown of that paw (`late_swing.py`):

| | −4 | −3 | −2 | −1 | 0 (clip touchdown) | +1 | +2 |
|---|---|---|---|---|---|---|---|
| clip sg0 LH | +25 | +25 | +25 | +27 | +30 | +33 | +36 |
| clip sg0 RH | +18 | +23 | +30 | +38 | +44 | +50 | +54 |
| sg-s7-25 at 1000 LH | −15 | −9 | +1 | +1 | +6 | +13 | +21 |
| sg-s7-25 at 1000 RH | −9 | +5 | +0 | +2 | +4 | +6 | +11 |
| sg-s7-25 at 1000 LH: paw down; heel down of those | 0.00 | 0.01; 1.00 | 0.67; 1.00 | 1.00; 0.92 | 1.00; 0.06 | 1.00; 0 | 1.00; 0 |
| sg-s7-25 at 1000 RH | 0.00 | 0.23; 0.21 | 0.81; 0.91 | 1.00; 0.53 | 1.00; 0.20 | 1.00; 0.11 | 1.00; 0.03 |

- **The clip lands the slow paw toes-first, heel well up**, at every stride
  of the schedule: heel minus paw at the clip's touchdown is +30 / +44 mm
  (sg0), +27 / +41 (sg1), +23 / +35 (sg2), +20 / +36 (sg3). Only sg1–sg3
  bring it down after touchdown (to 0 by +4, +3 and +1 samples). So the
  first branch (the clip lands heel-flat) is ruled out, and the clip's late
  swing needs no generator change.
- **The policy swings the slow heel below the paw** (−9 to −22 mm at −6..−4
  on LH, the metatarsus pitched heel-down with the toes up), lands 1–2
  frames before the clip, heel and paw together (heel down on 0.92–1.00 of
  LH's paw-down frames at −2 / −1), then rolls up onto the toes through
  stance. That is the early-contact heel `heel_gate.py` counted. At 1700
  and 2400 it does the same (LH −13 to −26 mm at −4..−2).
- **What sets it is the hock** (`hock_land.py`): the policy's `j_hock_*`
  runs 51–59° off the clip's `q_ankle_*_ref` on LH over −4..−1 (41° at
  the clip's touchdown) and 14–43° on RH (49° at touchdown), mirror-signed,
  at 1000; 37–54° and 10–41° at 1700, 34–56° and 28–41° at 2400. The only term that reads the hock in swing is `track_pose`, one
  exp over 19 joints at 900 deg² each: a 55° miss costs it about 0.15 of
  its w 1.5. No other term reads the hock, or the heel, before contact.

## The lever: `hock_land`, scored per step

The smallest lever on what puts the heel down early: track the clip's hock
where the clip has the paw in swing near the floor, at the slow end only.

    hock_land = sat01((2400 - cmd) / 1400) * sum over hinds of
        (1 - ref_h_down) * sat01((30 - ref_h_lift) / 15) * tent(q_hock - q_ankle_ref, 60) / 2,   w 6

On sg-s7-25's traces (`hock_land.py`; gate and pay a step per leg, the
clip's own hock earning the gate):

| cmd | gate LH / RH | pay LH / RH (W 60) | pay at W 20 |
|---|---|---|---|
| 1000 | 0.217 / 0.216 | 0.086 / 0.115 | 0.007 / 0.033 |
| 1700 | 0.109 / 0.108 | 0.052 / 0.077 | 0.017 / 0.032 |
| 2400 | 0 / 0 | 0 / 0 | 0 / 0 |

Landing as the clip does is worth w 6 × 0.232 = **1.39 a step at 1000**,
0.53 at 1700 and nothing at 2400. That is the size of the contact-gated
`heel_sched`'s slow contrast (+1.3), and it falls on the frames
`heel_sched` cannot see. A half-width of 20° pays almost nothing on a 50°
miss and gives no slope, so the tent is 60°. The 2400 gate is zero, so the
fast heel is left to the stance terms.

## sg-s8

sg-s7's task plus `hock_land` (w 6), 25 terms; nothing else changed.
`~/orun16-queue/orun16-sg8.py` differs from `orun16-sg7.py` only in that
term and its comment. Built with `cadex script --set` (reward only: model
and clearance unchanged; no tag). Warm from **sg-s7-25** (`5b956f7e`)
across the one-term task change, critic warm-up 5, lr 1e-4, seed 1, 4096
envs, 50 iterations, a checkpoint every 25, `budget_s` 5,000 (sg-s7 ran
~60 s an iteration after a ~10 min compile). (A `hind_scuff` w −16 script
staged as `orun16-sg8.py` in iteration 15 was never built; it is kept as
`orun16-sg8-scuff16.py`.)

**The question:** does tracking the clip's hock into the slow touchdown
take the heel out of the slow early contact, so the slow paw lands on its
toes, without costing the fast heel?

**Rule at 25** (`sg_judge.py` at 1000 / 1700 / 2400, then `legs.py`,
`paw_floor.py`, `p2_lag.py`, `hind_rhythm.py`, `heel_gate.py`,
`late_swing.py`, `hock_land.py`): run on to 50 only if
- on **both** hind legs the heel share of stance (`legs.py`) at 1000 is
  **at most 0.12** (sg-s7-25: 0.20 / 0.19);
- at 2400 neither leg's heel share falls more than 0.05 below sg-s7-25's
  (so **LH ≥ 0.20, RH ≥ 0.26**);
- rotary 8/10 at every command, and 2400's median top 2 s speed at least
  **2.4 m/s**.

Otherwise stop it as a dead end for its question and record which clause
failed. Either way, report per leg at every command the heel share, U, the
late-swing heel minus paw (`late_swing.py`) and the hock miss
(`hock_land.py`), LH's taps and the 1000 hind lag.

**Rule at 50:** sg-s7's (SG moves if both legs' heel share rises from 1000
to 2400 by at least 0.15 with 1000 at most 0.1; RL's direction holds if at
every command rotary is 8/10, each pair's lag at least 40 ms with taps
counted, and the fore and hind lag shares fall from 1000 to 2400). Extend
warm (O8) only if SG's holds.
