# orun12 P2: the fore lag, the cadence, and why no clip so far can be rotary

Verified against source: 2026-10-20. Frozen evidence (orun12, iteration 21).

The critic asked for the fore pair's lag and the fore/hind cadence the heel5 clip
asks for, measured per leg, and for the clip change that would set both.
`p2_lag.py` reads a bundle's clip and each judged evaluation's footfall.
`clip_lag.py` regenerates the clip with the engine's generator at other lags.
`legs.py` now counts a **tied** stride (two first landings in one 20 ms frame) on
its own line instead of ordering it.

```
R=~/cadex-projects/feline-v07/runs/heel5c-s1/train; E=~/cadex-projects/feline-v07/evaluations
pixi run python docs/probes/orun12/p2_lag.py $R/gallop-task.json $E/heel5c-s1-final $E/heel5-s1-100 $E/heel7-s1-50 $E/v07-g1-100
python3 docs/probes/orun12/legs.py $E/heel5c-s1-final $E/heel5-s1-100 $E/heel7-s1-50 $E/v07-g1-100
pixi run python docs/probes/orun12/clip_lag.py $R/gallop-task.json $R/cat_model-model.xml 0.7:0.04:0:0.05 ...
```

## What the heel5 clip asks for

The clip is a 0.70 m stride at 2.40 Hz (1.68 m/s), duty 0.2, 21 samples of 19.8 ms.

| foot | touch-down phase | stance share | touchdowns / cycle |
|---|---|---|---|
| LH | 0.000 | 0.24 | 1 |
| RH | 0.000 | 0.24 | 1 |
| LF | 0.550 | 0.19 | 1 |
| RF | 0.500 | 0.19 | 1 |

- **Fore pair lag:** 0.05 of the cycle, 21 ms. That is one sample and one
  evaluation frame.
- **Hind pair lag:** 0. The hind pair lands together.
- **Hind to fore:** 0.5 of the cycle.
- **Flights:** two a cycle, 0.099 s and 0.119 s.
- **Cadence:** one touchdown per paw per cycle, so fore and hind ask for
  the same rate.

**Its footfall order is undefined.** LH and RH land on the same sample, and RF
leads LF by one frame. A policy that tracked this clip exactly could not read as
rotary: a tied hind pair has no leading hind.

## What the policies do

Medians over the 10 frozen seeds. A pair lag is folded, as the engine folds it,
where 0 means the pair lands together. "Together" is the share of strides in
which the pair lands in the same frame. The rate is touchdowns over the left
hind's stride clock (`no_tap` takes the maximum, `every_stride` the minimum).

| evaluation (clip) | fore lag (together) | hind lag (together) | fore rate | hind rate | LH → fore | flight s (share) | rotary / ordered / tied / strides |
|---|---|---|---|---|---|---|---|
| heel5c-s1-final, 910cdb5a (heel5) | 0.000 (1.00) | 0.000 (1.00) | 1.03 | 0.98 | 0.400 | 0.260 (1.00) | 0 / 3 / 173 / 208 |
| heel5-s1-100 (heel5) | 0.000 (1.00) | 0.048 (0.70) | 1.03 | 0.98 | 0.381 | 0.240 (1.00) | 1 / 4 / 177 / 208 |
| heel7-s1-50 (flat_feet) | 0.081 (0.47) | 0.045 (0.80) | 1.94 | 0.98 | 0.049 | 0.160 (1.00) | 17 / 56 / 79 / 340 |
| v07-g1-100 (orun11 clip) | 0.000 (0.80) | 0.048 (0.90) | 1.66 | 0.98 | 0.150 | 0.200 (1.00) | 0 / 35 / 159 / 208 |

Per seed on 910cdb5a, every seed shows the same numbers:

- the fore pair lands together on every stride (together 1.00), and the hind pair on 0.94–1.00;
- fore rate 0.98–1.03;
- flight 0.260 s on every stride;
- 0 to 1 ordered strides out of 20–21.

### Findings

1. **On the heel5 clip, the fore cadence is not the problem.** On the P1 policy:
   - `no_tap` passes 10/10 (median 1.03);
   - `every_stride` passes 10/10 (0.98);
   - `overreach` passes 10/10 (279 mm);
   - every stride has a flight (0.26 s).

   The 1.6–1.9 tap ratio belongs to the other clips: heel7's flat_feet clip
   (1.94, 0/10) and v07-g1's orun11 clip (1.66). heel5c-s1 keeps the clip's
   one touchdown per cycle and gets its speed from stride length: 1.17 m at
   2.38 Hz against the clip's 0.70 m at 2.40 Hz.

2. **Every "rotary" count so far read a tie-break, not a gait.**
   `CadexEvaluation.flight_metrics` sorts a stride's first landings by time. A
   tie keeps the spec's foot order (LF before RF, LH before RH).
   - On 910cdb5a, 173 of 208 strides are tied. The old count of 54/176 (`heel5c-final.md`)
     rotary, which `mirror-policy.md` already called noise, came from the
     order of those ties.
   - heel5-s1-100's 145/181 rotary (`heel5c-25.md`) was the same tie-break.
     There, RH lands one frame before LH and the fore pair ties as LF RF, so
     the strides read RH LH LF RF.
   - With ties excluded, no judged policy has a rotary seed.

   `legs.py` now reports tied strides separately.

3. **Hold the clip and the gait is a bound.** The clip's 21 ms fore lag sits
   at the 20 ms frame, and its hind lag is zero. 910cdb5a tracks both: it
   lands each girdle's paws together, with flight. P2's rotary order needs
   lags the evaluation can resolve, at least two frames (≈ 0.1 of a 2.4 Hz
   cycle), on **both** pairs.

## The clip change

`clip_lag.py` regenerates the clip on heel5c-s1's bundle. It first checks
that its regeneration of the bundle's own clip is byte-equal (it is), then
tries each case at heel_from 0.2 and duty 0.2.

| stride m | swing m | hind lag | fore lag | reachable | stance LH RH LF RF | heel-down / stance | airborne |
|---|---|---|---|---|---|---|---|
| 0.70 | 0.04 | 0 | 0.050 | yes (today's) | 5 5 4 4 | 4/5, 4/5 | 11/21 |
| 0.70 | 0.04 | 1/21 | 2/21 | yes | 5 5 4 4 | 4/5, 4/5 | 9/21 |
| 0.70 | 0.03–0.05 | 2/21 | 2/21 | **no**: RH misses its swing by 1.1–2.8 mm, j_knee_r and j_ankle_r at a stop | | | |
| 0.70 | 0.04 | 0.1 | 0.1 | **no**: misses by 3.1 mm | | | |
| **0.65** | **0.04** | **2/21** | **2/21** | **yes** | 5 5 4 4 | 4/5, 4/5 | 8/21 |
| 0.65 | 0.04 | 2/21 | 3/21 | yes | 5 5 4 4 | 4/5, 4/5 | 7/21 |
| 0.65 | 0.04 | 0.1 | 0.1 | yes, but RH stands 4 samples to LH's 5 (heel 4/4) | 5 4 4 4 | 4/5, 4/4 | 8/21 |
| 0.60 | 0.04 | 2/21 | 2/21 | yes | 5 5 4 4 | 4/5, 4/5 | 8/21 |

**The named change** is `gallop_len` 650, `hind_lag` = `gallop_lag` = 2/21
(0.0952, 40 ms at 2.4 Hz, two frames), everything else as heel5c.

- **Order:** the offsets read LH RH RF LF, which `legs.py` classifies as
  rotary.
- **Heel:** each hind keeps 4 of its 5 stance samples heel-down, as on the
  P1 policy's clip.
- **Flight:** the clip stays airborne on 8 of 21 samples.
- **Why 2/21 and not 0.1:** the clip has 21 samples a cycle. An offset of
  0.1 falls off that grid and gives RH one stance sample fewer than LH. 2/21
  keeps both hinds at 5.
- **Speed:** the policy does not run at the clip's speed. heel5c-s1 strode
  1.17 m on a 0.70 m clip, so the 50 mm shorter clip stride should not cap
  its speed. Its 2 s top speed is the measure to watch.

**What this costs (O3).** A nonzero hind lag gives the clip a fixed lead, the
right hind landing second. The generator takes a one-cycle clip and cannot
alternate leads. That is the asymmetry the owner removed for v07, since
on v06-g1 only the leading-side hind laid its hock down. A screen on this
clip must report Q1's left and right values. It also needs the mirror test
(`mirror_policy.py`) before any handedness it shows is put down to the
model.

**Not launched this iteration.** heel7-s1 holds the GPU, with q2a-s1
queued behind it. heel7 has not yet been judged at 75 or 100.
