# orun17 SG/RL/O9: one probe for the speed-commanded tables

Verified against source: 2026-10-22. Frozen evidence (orun17, iteration 3).

`sg_tables.py` prints SG's table (speed against heel share, per leg), RL's
(speed against lag, fore and hind, as a share of the stride and in ms) and
O9's line per held command, each with its clause's verdict, from the same
evaluations `orun16/sg_judge.py` writes. It reuses the readings of
`orun12/legs.py`, `orun14/paw_floor.py`, `orun13/p2_lag.py` and
`orun13/spine_foot.py` (iteration 1 ran them one by one), so sgt-1 is
judged in one command:

```
R=~/cadex-projects/leo/runs/sgt-1/train; E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun17/sg_tables.py \
    $R/cat_model-model.xml $E/sgt-1-N-{700,1550,2400}
```

## What it adds over iteration 1's reading

- **Pair lag in ms, measured**: each `pair_lag` stride's folded share times
  its own period (next `start_s` less its own), not the median share over
  the median stride rate. On sg-s9-80: fore 180 / 100 / 100 ms, hind
  53 / 100 / 60 ms at 700 / 1550 / 2400 (iteration 1 estimated ~184 / ~105
  / ~112 and ~52 / ~100 / ~64).
- **Strides under 40 ms**, which a seed median hides: on sg-s9-80 at 700
  the hind pair is under 40 ms on 0.19 of strides (seed median; 26–29 ms
  and ties among 53 ms ones), though every seed's median is 53 ms.
- **U at 5°** beside `paw_floor`'s U. The charter defines U as toes-up of
  the floor "past 5°" and cites `paw_floor.py`, whose `FLAT_DEG` is 10°;
  every judged U since orun14 (hk12-s1-50's 0.16 / 0.01 included) is the
  10° one. The verdict stays on `paw_floor`'s, so numbers compare across
  runs; the 5° column is printed so the gap is visible. On sg-s9-80 at
  2400: 0.24 / 0.23 at 10°, 0.32 / 0.30 at 5°.

## Checked against iteration 1 (`sg-s9-50-80.md`, sg-s9-80)

Every number the two share matches: top speed 1.07 / 2.07 / 2.90 m/s;
heel share LH / RH 0.19 / 0.02, 0.26 / 0.21, 0.24 / 0.12; U 0.08 / 0.02,
0.18 / 0.22, 0.24 / 0.23; lift pitch and lifts toes-up; pin p95 687 / 594,
741 / 650, 749 / 453 °/s; rotary 10/10 ordered (9 / 10 / 10 of all
strides); lag share fore 0.368 / 0.250 / 0.328, hind 0.105 / 0.238 /
0.188; spine 8.5 / 28.4 / 24.4°; cable 0.22 / 0.28 / 0.46°; loops 2.8 /
3.3 / 3.4 mm; worst RMS 1.48 (`j_hock_l`) / 1.40 (`j_wrist_r`) / 1.70
(`j_spine`), peak margin 0.00. `u_at(series, 10)` equals `paw_floor`'s U
on a seed (sg-s9-80-2400 seed 1001: 0.263 / 0.259 both ways).

Its verdicts on sg-s9-80: SG fails all five clauses; RL passes rotary and
40 ms and fails both falling-share clauses; O9 passes pins, cable and
blow-up, and fails loops (Q2's deferred front rods).
