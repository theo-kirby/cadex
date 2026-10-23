# orun17 RL: the slow fore pair — the clip lands them 180 ms apart; the policy strikes each fore twice a stride

Verified against source: 2026-10-22. The critic's ask after `sgt-2-120.md`
(O8, the reference before the reward): sgt-2-120 lands the fores together on
0.51 of its 700 mm/s strides (26 ms median), so read the `gallop_sg`
reference's fore lag at 700 first, and if the clip itself lands them under
40 ms apart, write the reference fix. CPU only; sgt-3b holds the GPU.

```
R=~/cadex-projects/leo/runs/sgt-3b/train; E=~/cadex-projects/leo/evaluations
pixi run python docs/probes/orun16/sg_clip.py $R/gallop_sg-task.json $R/cat_model-model.xml docs/probes/orun17/slow-strides.json /tmp/o17f/out
pixi run python docs/probes/orun17/fore_pair.py ~/cadex-projects/leo/runs/sgt-2/train/cat_model-model.xml \
    $E/sg-s9-80-700 $E/sgt-1-120-700 $E/sgt-2-120-700 $E/sgt-2-50-700
pixi run python docs/probes/orun16/sg_clip.py $R/gallop_sg-task.json $R/cat_model-model.xml docs/probes/orun17/duty-schedule.json /tmp/o17f/sched
```

`fore_pair.py` (new) reads the stride the schedule picks at the judged
command (700 is stride 0; the stride's own table, period and `reset_qpos`
rows), prints the clip's contact rows, and per seed, with
`orun15/lag_term.py`'s clock and stance rule: each fore paw's touchdowns per
clip stride, its median offset from the clip's touchdown, the fore pair's
lag, the share of touchdowns within 20 and 40 ms, and the candidate
`fore_lag` term per step (`lag_term.py`'s fore form) beside the clip's own
score.

## The clip at 700: no fault

sgt-3b's bundle, stride 0 (0.35 m at 2.0 Hz, lag 0.35, duty 0.2, 25 samples
of 20 ms; the same stride sgt-1 and sgt-2 trained on):

```
LH #####....................  touchdown sample 0
LF ....#####................  touchdown sample 4
RF .............#####.......  touchdown sample 13
RH .................#####...  touchdown sample 17
```

RF lands 180 ms after LF (320 ms the other way), LH 160 ms after RH; the
fores are never down together. The order (RH, LH, LF, RF) is rotary. The
reference lands the slow fores 4.5× O3's 40 ms apart, so there is no
reference lag to fix. `fore_sync` (the only term paying the fores
together) is gated by the command's share of the range and pays 0 at 700.

## The policies at 700: the fores double their cadence

| policy | fore touchdowns a stride LF / RF (seed medians' range) | RF after LF ms, seed medians | within 40 ms, all seeds | `fore_lag` a step (clip 0.400) | per seed, `fore_lag` vs within-40 r |
|---|---|---|---|---|---|
| sg-s9-80 (27 terms) | 1.00–1.33 / 1.00–1.17 | +170..+190 (10 / 10) | **0.09** | +0.378 | −0.83 |
| sgt-1-120 (18-term trim) | 1.00–2.33 / 1.00–1.78 | +200..+210 on 4, ±20 on 6 | 0.30 | +0.314 | −0.77 |
| sgt-2-50 (+`paw_fold`) | 1.50–1.78 / 1.78–1.94 | −20..+20 (10 / 10) | 0.65 | +0.194 | +0.18 |
| sgt-2-120 | **1.89–2.00 / 1.78–2.00** | −10..+10 (10 / 10) | **0.63** | +0.245 | −0.85 |

- **The fault is a double strike, not a merged pair.** sgt-2-120 lands each
  fore paw twice in a 0.5 s stride on every seed, so one strike of each
  paw falls on the other's: the "together" strides are the extra strikes
  meeting. The hinds keep the clip exactly (one touchdown each, RH→LH
  160 ms, `hind_lag` +0.400 = the clip's, `lag_term.py`).
- **The trim brought it in.** sg-s9-80 (the 27-term task, same seed 1, same
  stride 0) kept one fore strike a stride on most seeds and its fores
  180 ms apart on all ten; the 18-term trim (sgt-1) doubled the fores on
  six seeds; sgt-2 on all ten. Of the cut terms, `fore_reach` (w3, a
  stance fore paw paid for standing ahead of the chest) is the only one
  on the fore paws; the trim also changed the heel terms, so this table
  shows coincidence, not cause.
- **Why a double strike is plausible on this clip:** at duty 0.2 each fore
  paw is down 100 ms of every 500 (five samples); the two fores together
  carry the chest 40% of the stride at 0.7 m/s. A second strike adds fore
  support where the clip has none. `fore_tap` (w −8) charges fore contact
  outside the clip's stance: a second 100 ms strike of each fore costs
  about 8 × 0.2 = 1.6 a step, against `track_speed`'s 20.
- **`fore_lag` would see it:** on sg-s9-80, sgt-1-120 and sgt-2-120 the
  per-seed term falls as the share within 40 ms rises (r −0.77 to −0.85);
  on sgt-2-50, where every seed is tied, it does not separate seeds
  (r +0.18). It pays 0.378 on the policy that keeps the lag and 0.245 on
  the one that doubles. This is a candidate only; O8 asks the reference
  and the cut first.

## A reference option for the next bundle: a longer slow stance

The generator reaches a longer duty at the slow end with a 30 mm swing
(`slow-duty-strides.json`, `duty-schedule.json`):

| stride | duty | swing mm | generated? | fore rows (stance samples) | RF after LF ms | heel held LH / RH, heel mm median LH / RH |
|---|---|---|---|---|---|---|
| sgs 0.7 m/s (now) | 0.2 | 40 | yes | 5 / 5 | 180 | 0 / 0, 37.0 / 55.5 |
| sgs | 0.25 | 40 | yes | — | 180 | 0 / 0, 35.8 / 54.9 |
| sgs | 0.3 | 40 | refused: LH misses its swing target by 1.6 mm (hip, knee, pin at a stop) | | | |
| sgs | 0.3 | 30 | yes | 8 / 7 | 180 | 0 / 0, 34.1 / 54.5 |
| sgs | **0.35** | **30** | yes | **9 / 9** | **180**, never both down | 0 / 0, 32.3 / 53.6 |
| sgs | 0.4 | 30 | refused: LH misses by 2.3 mm | | | |
| sg1 1.38 m/s | 0.25 | 40 | refused: LH misses by 1.5 mm | | | |

The whole schedule generates on one 25-sample grid with sgs at duty 0.35
and sg0 (1.0 m/s) at 0.3, both with a 30 mm swing, and sg1–sg3 unchanged
(duty 0.2, 40 mm): lags 175 / 150 / 109 / 74 / 50 ms, heels held
0 / 0 / 0.20 / 0.40 / 0.80, slow heels up 32 / 54 mm (LH / RH), the order
never crossing, IK misses ≤ 0.76 mm. The schedule's rule
(`CadexDynamics._reference_schedule_records`) checks only the sample grid
and the footfall order, not the duty, so a per-stride duty is allowed.
Duty falling with speed (0.35 → 0.3 → 0.2) is also what a cat does.

**In leo's `script.py`** this is a sixth and seventh tuple field on
`SG_STRIDES` (duty, swing), passed to `assembly.gait` in place of
`GALLOP_DUTY` and the 40 mm swing:

```
SG_STRIDES = [(0.35, 2.0, 0.35, 0.99, 0.35, 30.0), (0.5, 2.0, 0.30, 0.99, 0.30, 30.0),
              (0.6, 2.3, 0.25, 0.7, 0.2, 40.0), (0.7, 2.7, 0.20, 0.45, 0.2, 40.0), (0.8, 3.0, 0.15, 0.2, 0.2, 40.0)]
```

It is not written into the project: sgt-3b trains on the current schedule,
and its keep rule (`sgt-2-120.md`) at 50 and 120 decides the next bundle's
base. A reference change trains cold (O8). If sgt-3b keeps the fores
doubled at 700, the next bundle is this schedule on sgt-3b's terms; the
term `fore_lag` comes only if that screen still doubles the fores.

## What this does not settle

- 1550 is not a stride's speed, so `fore_pair.py` refuses it (the blended
  clock is not reproduced); `sg_tables.py` says sgt-2-120's fores are
  0 / 0 together at 1550 and 2400.
- Whether `fore_reach`'s cut caused the doubling is not tested; a longer
  stance is the reference-side fix, tried first under O8.
