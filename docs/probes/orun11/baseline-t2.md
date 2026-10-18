# orun11 baseline: t2-g4 and t2-g5 on ADR-774's heel and footfall metrics

Verified against source: 2026-10-18.

The owner's runs of 2026-10-18 on `orun10-cat` (accepted revision
`2729c141`), re-read with `footfall_probe.py` from the traces their
evaluations already wrote (10 seeds, 1001–1010, the gallop spec's
conditions). Nothing was replayed. Every figure is the **median over the 10
seeds** of that seed's value. Heel = the hock drive's case (`c_qdd_hock_*`,
a 40 mm sphere on the AK60's axis). t2-g4's model carries no collision
shape on the case, so its case could not touch the floor; its heights are
read with t2-g5's sphere borrowed (`--heel-shapes-from`).

```
pixi run python docs/probes/orun11/footfall_probe.py \
  ~/cadex-projects/orun10-cat/runs/t2-g5/train/cat_model-model.xml \
  ~/cadex-projects/orun10-cat/evaluations/t2-g5-000200
```

## Hock and sole (P1)

| checkpoint | hock down, share of stance L / R | hock down at toe-off L / R | hock median stance height L / R (mm) | sole flat (≤ 8°) L / R |
|---|---|---|---|---|
| t2-g4 it 50  | 0 / 0 | 0 / 0 | 84 / 86 | 0.81 / 0.69 |
| t2-g4 it 100 | 0 / 0 | 0 / 0 | 85 / 84 | 0.75 / 0.71 |
| t2-g5 it 50  | 0 / 0.003 | 0 / 0 | 77 / 78 | 0.47 / 0.33 |
| t2-g5 it 100 | 0 / 0 | 0 / 0 | 84 / 87 | 0.79 / 0.70 |
| t2-g5 it 150 | 0 / 0 | 0 / 0 | 70 / 83 | 0.15 / 0.19 |
| t2-g5 it 200 | **0.09** / 0 | **0.11** / 0 | **29** / 85 | 0.59 / 0.87 |

P1 asks ≥ 0.40 down and down at every toe-off, on both legs. The best
checkpoint, t2-g5 at 200, gets the left hock down in 9% of stance and the
right never, 85 mm off the floor. The free paw pin lets the sole lie flat
(59–87% of stance) without the hock coming down.

## Footfalls (P2)

| checkpoint | stride Hz (LH) | touchdowns Hz LF / RF / LH / RH | hind overreach L / R (mm) | pair lag fore / hind | top 2 s speed, median / best (m/s) | worst RMS / rated, peak |
|---|---|---|---|---|---|---|
| t2-g4 it 50  | 2.38 | 4.83 / 4.83 / 2.44 / 2.44 | 239 / 348 | 0 / 0.048 | 3.65 / 3.66 | 1.89, 1.00 |
| t2-g4 it 100 | 2.38 | 4.78 / 4.78 / 2.33 / 2.33 | 302 / 393 | 0 / 0.048 | 3.79 / 3.81 | 1.88, 1.00 |
| t2-g5 it 50  | 2.41 | 3.11 / 3.17 / 2.67 / 3.83 | −122 / −4 | 0.048 / 0.079 | 2.30 / 2.39 | 1.74, 1.00 |
| t2-g5 it 100 | 2.38 | 2.44 / 4.28 / 2.44 / 2.44 | 149 / 358 | 0.27 / 0.011 | 3.13 / 3.18 | 2.01, 1.00 |
| t2-g5 it 150 | 3.03 | 2.40 / 2.89 / 3.27 / 3.42 | −58 / −63 | 0.049 / 0.090 | 2.17 / 2.37 | 1.57, 1.00 |
| t2-g5 it 200 | 2.38 | 2.44 / 3.11 / 2.94 / 2.33 | 300 / 363 | 0.049 / 0 | 3.20 / 3.23 | 1.96, 1.00 |

- **Taps.** t2-g4's fore paws land twice a stride (4.8 Hz against 2.38),
  the owner's 4.74 against 2.37. t2-g5 at 200 has LF on the clock and RF
  at 3.1 Hz, with LH tapping too (2.94), as the owner found ("one paw at
  the clip's 2.37 Hz, the other at 3.2").
- **Overreach.** Where the gallop holds (t2-g4, t2-g5 at 100 and 200), the
  hinds land 150–390 mm ahead of the last fore print on their side.
- **Lag.** Both pairs land almost together, 0–0.09 of a stride, the clip's
  0.05 (LH 0 / RH 0.05, RF 0.5 / LF 0.55). The fore pair's 0.27 at t2-g5
  it 100 is RF's mid-swing taps landing between LF's strides.
- **Drives.** Every checkpoint has a drive at its peak (1.00) and the worst
  drive at 1.6–2.0 times its rated RMS.

The orun11 gallop spec (`~/cadex-projects/orun11-cat`, ADR-774) holds
`heel_down_stance_share_min ≥ 0.4`, `heel_down_at_toeoff_share_min ≥ 1.0`,
`touchdown_rate_ratio_max ≤ 1.1`, `touchdown_rate_ratio_min ≥ 0.9` and
`hind_overreach_mm_min ≥ 0`. Seeds of 10 passing each, read from these
traces:

| checkpoint | hock_down | no_tap | every_stride | overreach |
|---|---|---|---|---|
| t2-g4 it 50  | 0 | 0 | 10 | 10 |
| t2-g4 it 100 | 0 | 0 | 10 | 10 |
| t2-g5 it 50  | 0 | 1 | 9 | 0 |
| t2-g5 it 100 | 0 | 0 | 10 | 10 |
| t2-g5 it 150 | 0 | 4 | 3 | 1 |
| t2-g5 it 200 | 0 | 0 | 10 | 10 |
