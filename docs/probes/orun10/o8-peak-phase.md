# orun10 O8: where in the stride each drive reaches its peak

Verified against source: 2026-10-17. Frozen evidence (orun10, iteration 2).

## What was measured

orun10's O8 asks for a measurement of what binds before another reward edit:
which drive reaches its peak, and in which part of the stride. The rollouts
are the sprint baselines judged in iteration 1 (`sprint-baseline.md`), 10
seeds each, re-read on the CPU:

- orun7 f1-g3 `run.best`, the 4.22 m/s gallop (orun7's model `d0401683`);
- orun9 c1-c6 at iteration 100 on this cat, the 2.74 m/s trot at a
  3.5 m/s command.

`~/orun10-progress/s2/o8_peak_phase.py` (outside the repo) places every
settled frame in its stride by the left fore's touchdowns, the ADR-771
stride clock. For each drive it counts the frames at ≥ 0.98 of the drive's
clamp, per tenth of the stride. A paw is down when its lowest collision point
is within 1 mm of the floor. That reading uses the engine's own
`CadexEvaluation.foot_series`, on the rig `CadexDynamics.evaluation_rig`
builds from each run's exported model. It writes `o8-peak-phase.json` beside
each evaluation.

The two models carry the same drives, with the same peaks and ratings. The one
exception is `j_spine_yaw`, which this cat adds. The weakest leg drive is the
hock: 9 N·m peak, 3 N·m rated. The wrist and spine have 22 N·m peak and
9 N·m rated. The girdle and the hip, knee and elbow drives have 53 N·m peak
and 18 N·m rated.

## f1-g3, 4.22 m/s gallop

Share of each tenth of the stride with the paw down, and with the drive at
≥ 0.98 of its peak:

| tenth of the stride | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| fl down | 1.00 | 0.92 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hl down | 0 | 0 | 0 | 0.86 | 1.00 | 0.59 | 0.01 | 0 | 0 | 0 |
| hr down | 0 | 0 | 0 | 0 | 0.33 | 1.00 | 1.00 | 0.65 | 0.02 | 0 |
| fr down | 0.08 | 0 | 0 | 0 | 0 | 0 | 0 | 0.24 | 1.00 | 1.00 |
| j_hock_l at peak | 0 | 0 | 0 | 0.77 | 0.99 | 0.11 | 0 | 0 | 0 | 0 |
| j_hock_r at peak | 0 | 0 | 0 | 0 | 0.30 | 1.00 | 1.00 | 0.16 | 0 | 0 |
| j_wrist_l at peak | 0.74 | 0.60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| j_elbow_l at peak | 0.63 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| j_wrist_r at peak | 0.01 | 0 | 0 | 0 | 0 | 0 | 0 | 0.06 | 0.51 | 0.92 |
| j_elbow_r at peak | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.07 | 0.90 | 0 |
| j_spine at peak | 0 | 0 | 0.89 | 0.60 | 0.02 | 0.36 | 0.59 | 1.00 | 0.96 | 0.09 |

Over all frames, the share at peak is 0.24 (hock_r), 0.18 (hock_l),
0.16/0.14 (wrist l/r), 0.09/0.08 (elbow r/l), 0.05 (shoulder_r) and 0.44
(spine). The tail servos (`j_tail2`/`j_tail3`, 1.9 N·m) are at peak 0.69 and
0.57 of the time, the tail1 drive 0.09.

- **The hocks are at peak through their whole stance.** Each hock is
  saturated in the tenths its own paw is down (hl 0.3–0.5, hr 0.5–0.7), and
  only there. The hind push-off is torque-limited at the 9 N·m drive.
- **The fore push-off is too.** Each wrist saturates across its paw's
  stance (fl 0–0.2, fr 0.8–1.0), with the elbow at the start of the same
  stance.
- **The spine is at peak in both halves of the stride.** It saturates at
  0.2–0.3, after the left fore lifts into the gathered flight, and at
  0.6–0.9, from the right hind's push-off to the right fore's stance. That is
  the flex and the extension a gallop's long stride is made of. Of its frames
  at peak, 0.27 are in flight and 0.44 on one hind paw alone.
- No girdle, hip or knee drive (53 N·m) reaches 0.98 of peak.

## c1-c6, 2.74 m/s trot-like gallop

| tenth of the stride | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| fl down | 1.00 | 1.00 | 0.99 | 0.37 | 0.02 | 0 | 0 | 0 | 0 | 0 |
| hr down | 0.76 | 1.00 | 0.73 | 0.02 | 0.01 | 0.01 | 0 | 0 | 0.01 | 0.08 |
| fr down | 0 | 0 | 0 | 0.01 | 0.52 | 1.00 | 1.00 | 0.94 | 0.25 | 0 |
| hl down | 0.01 | 0 | 0 | 0.03 | 0.34 | 0.88 | 0.98 | 0.33 | 0.01 | 0.01 |
| j_wrist_l at peak | 0.01 | 0.46 | 0.58 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| j_wrist_r at peak | 0 | 0 | 0 | 0 | 0 | 0 | 0.08 | 0.24 | 0 | 0 |

The pairs land diagonally, fl+hr and then fr+hl. The left wrist is at peak
0.10 of the time, the right wrist 0.04, both late in their own stance. The
tail servos tail2 and tail4 are at peak 0.26 and 0.17 of the time. **No hock,
spine, elbow or girdle drive reaches peak.**

## Reading

- **At 2.74 m/s the legs have margin; at 4.22 m/s every push-off drive is
  saturated.** On c1-c6 only the wrists touch peak, so its speed is capped by
  the trot clock, as iteration 1 found, and not by the drives. On f1-g3 the
  hocks, wrists and elbows are at peak through their stance, and the spine
  in both its flexion and its extension.
- **The binding drives for a faster gallop on this cat, by O2:**
  1. the hocks, at 9 N·m, the lightest leg drive, through the whole hind
     stance;
  2. the spine, at 22 N·m, which does the stride's flex and extension;
  3. the wrists, at 22 N·m, at the fore push-off.

  A faster stride asks more impulse per stance, or a longer stance at the
  same force. At peak those drives can give only the second, which is a
  longer stride from more spine and more reach, not more force.
- **The tail servos are at their 1.9 N·m peak half the time or more**, in
  every phase, on both policies. They swing the tail, not the body forward.
  They read as peak in every evaluation, so the worst drive's peak ratio
  (`effort_peak_ratio_max`) is 1.0 on every run and says nothing about the
  legs. The report has to give the leg drives' margins by name.
- This is the measurement the gallop sprint's reward is judged against. The
  first sprint (orun10 s1-g1) prices only `(tau/peak)^10`, so it may run the
  hocks at peak as f1-g3 did. Whether it finds speed beyond 4.2 m/s through a
  longer stride, not more force, is what its checkpoints will show.
