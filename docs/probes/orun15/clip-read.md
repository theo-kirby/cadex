# orun15 rung 4: the clip asks for the rotary lag; the policy drops it

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 5).

- **The question** (critic, after `sf-sole.md`): does leo v04's gallop
  clip ask for O3's 40 ms between LH and RH, or is P2's rotary order
  already missing from the reference? sf-sole-50's hinds land together on
  0.83 of strides (`orun13/p2_lag.py`, folded lag under 0.05).
- **The tool:** `docs/probes/orun15/clip_read.py`, standard library, on
  the bundle's `reference` block and the evaluations' `touchdowns_s`.
  The clip is sfp-sole's bundle (`runs/sfp-sole/train/gallop-task.json`),
  the same `reference` block as sp-sole's and sf-sole's: the paw spring
  is not in the generator's input.

```
E=~/cadex-projects/leo/evaluations
python3 docs/probes/orun15/clip_read.py ~/cadex-projects/leo/runs/sfp-sole/train/gallop-task.json \
    $E/sp-sole-50 $E/sf-sole-50
```

## What the clip asks for

- 0.70 m at 2.40 Hz = 1.68 m/s, a 417 ms period, duty 0.2, 21 samples of
  19.8 ms.
- Touch-down after LH's: **RH −62 ms** (RH leads), LF +146 ms, RF
  +208 ms. Order RH, LH, LF, RF: rotary.
- **Hind pair lag 0.150 of the cycle = 62.5 ms; fore pair lag 0.150 =
  62.5 ms.** Both are over O3's 40 ms, by three 20 ms frames.
- Each heel is down on 4 of its paw's 5 stance samples (0.80,
  `heel_from` 0.2): the clip asks for twice P1's 0.4.
- `j_spine` and `j_spine2` each run −7.0..+7.0° (14° peak to peak a
  joint, equal on every sample).
- `track_speed` (w20) pays forward speed linearly up to 2.00 m/s; the
  clip runs at 1.68.

So **the reference carries the rotary order and the lag.** orun13's clip
(`orun13/clip_lag.md`) landed the hinds together; this one does not.

## What the policies do with it (after the first second, 10 seeds)

| evaluation | paw | clip ms after LH | policy median ms (q1 / q3) | LH touchdowns matched |
|---|---|---|---|---|
| sp-sole-50 | RH | −62 | −20 (−40 / +0) | 263 / 263 |
| sp-sole-50 | LF | +146 | +40 (+20 / +60) | 256 / 263 |
| sp-sole-50 | RF | +208 | +40 (+0 / +60) | 256 / 263 |
| sf-sole-50 | RH | −62 | **+0** (−20 / +0) | 218 / 218 |
| sf-sole-50 | LF | +146 | +40 (+20 / +60) | 215 / 218 |
| sf-sole-50 | RF | +208 | +160 (+20 / +180) | 215 / 218 |

RH lands in LH's own 20 ms frame on 0.27 of LH touchdowns on sp-sole-50
and **0.42** on sf-sole-50. The stride rate (2.50 / 2.38 Hz median) is
the clip's 2.40: the policies are on the clip's cadence but not its
phases.

The engine's own `detail.reference` reads the same: against LH, RH's
phase error is 0.11–0.15 of a cycle on every sf-sole-50 seed (the whole
0.15 lag given back on half of them), LF's 0.23–0.26 and RF's 0.10–0.13.

- **The policy, not the clip, drops the lag.** It folds the clip's
  270 ms sequence (RH to RF) into a hind pair landing together, LF 40 ms
  behind LH and RF 160 ms behind it on sf-sole-50: a half-bound with the
  fore pair split (fore lag 0.275 by `p2_lag.py`, wider than the clip's
  0.15).
- **Only `track_contact` (w10) asks for the hind lag**, and cheaply:
  landing RH with LH costs it three mismatched samples at touch-down and
  three at lift, 6 of 21 samples at 2.5 a sample (w10 over four paws),
  about 0.7 per step against a reward per step of about 30 (arithmetic on
  the clip, not scored per step on a trace). Nothing else
  in the 20 terms pays for a hind order; `fore_sync` (w2) pays the fore
  pair to be **in the same contact state**, the opposite of O3 on the
  fore pair (the fore lag is wide anyway, so it is not what binds now).
- **The policy runs faster than the clip.** sf-sole-50's 2.37 m/s and
  981 mm stride against the clip's 1.68 m/s and 700 mm: at the clip's
  cadence the policy lengthens the stride 40%, past what `track_speed`
  pays (2.0 m/s). The clip is not the gallop the policy is running.
