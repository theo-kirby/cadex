# Why only one hind leg lays its hock down (heel1-s1, rod1-s1)

Verified against source: 2026-10-19. orun11 iteration 8, on the critic's
ask: for the leg that stays up, compare its stance with the clip's, check
its hock and paw drive against peak, and compare its contact and tracking
with the other side's.

Read with `hind_asymmetry.py` from the judged final checkpoints'
own seed traces (nothing replayed):

```
pixi run python docs/probes/orun11/hind_asymmetry.py \
  ~/cadex-projects/orun11-cat/runs/heel1-s1/train/cat_model-model.xml \
  ~/cadex-projects/orun11-cat/evaluations/heel1-s1-final
# and the same for rod1-s1
```

*Fold* is the joint angle with the right side negated (its axes are
mirrored, `axis="0 -1 0"`), so both legs read alike; a negative hock fold
is the plantigrade direction. A stance is a run of frames with the sole
within the engine's 1 mm (`STANCE_MM`), from 1 s. "At peak" is the share of
stance frames with that drive's effort at ≥ 98 % of its force limit. The
lever is, at the last stance frame, how far ahead of the hock axis (the
centre of the case's 40 mm collision sphere, on the axis) the paw's lowest
point is along the run; negative is toes *behind* the hock. Medians over the 10 seeds; every seed
lies within a few per cent of its median (the per-seed rows are in the
script's output).

## The numbers

| measure (median of 10 seeds) | heel1-s1 LH (down) | heel1-s1 RH (up) | rod1-s1 LH (up) | rod1-s1 RH (down) |
|---|---|---|---|---|
| hock case height in stance, mm | 1.0 | 89.9 | 76.7 | 3.4 |
| case within 1 mm, share of stance | 0.50 | 0.00 | 0.07 | 0.45 |
| hock fold mid-stance, deg | −48.7 | +3.5 | −38.9 | −47.2 |
| hock fold at toe-off, deg | −46.5 | +27.6 | +10.6 | −45.7 |
| knee fold mid-stance, deg | −1.6 | −56.5 | −40.1 | −5.2 |
| hip fold mid-stance, deg | +6.7 | −11.7 | +33.5 | +1.5 |
| **hock drive at peak, share of stance** | **0.91** | 0.00 | 0.66 | **0.84** |
| hip drive at peak | 0.39 | 0.00 | 0.05 | 0.38 |
| knee drive at peak | 0.00 | 0.34 | 0.11 | 0.04 |
| hock command − position in stance, deg (fold) | +43.6 | +18.9 | +33.9 | +44.5 |
| toes ahead of the hock axis at toe-off, mm | +77.5 | **−71.9** | **−42.4** | +81.2 |
| paw force the hock's 9 N·m peak holds at that lever, N | 116 | 125 | 213 | 111 |
| stances per second | 2.39 | 2.94 | 2.44 | 2.44 |

The clips' hind stance, for comparison (fold, deg; one sample is
19.8 ms):

| clip | leg | hip | knee | hock |
|---|---|---|---|---|
| heel1-s1 (plantigrade, ADR-777) | LH, samples 0–4 | −21.8 … −26.6 → **−0.9, +3.0** | +15.1 … −2.3 → **+30.4, +29.3** | 0 … −9.1 → **−31.3, −38.5** |
| | RH, samples 2–5 | −23.0, −25.5 → **+1.1, +3.5** | +14.8, +4.4 → **+38.3, +32.3** | +0.2, −5.8 → **−25.8, −36.1** |
| rod1-s1 (digitigrade) | LH | −5.5 … +3.8 | +15.3 … +9.6 | +7.2 … +8.7 |

Bold samples are the clip's heel-down ones.

## What it shows

1. **The leg that lays down does so by buckling, not by placing the
   foot.** On both runs the down leg's hock sits at fold −47 to −49°,
   10–17° past heel1-s1's plantigrade clip (−31 to −38°) and some 55° past
   rod1-s1's digitigrade one (+7 to +9°), with the hock drive at
   its 9 N·m force limit for 84–91 % of stance, while the policy commands
   it about 44° *less* folded than it is. The policy is trying to hold
   the foot up; the hock collapses until the case lands on the floor, and
   the floor then carries the leg. The hip of the down leg is at peak too,
   38–39 % of stance.
2. **The hock drive cannot carry a stance through the paw.** With the
   toes 77–81 mm ahead of the hock axis at toe-off, the AK60-6's 9 N·m
   peak resists only **about 110–120 N at the paw**. One hind
   paw's load in this gallop is larger: the hind pair carries about half
   of the 308 N body weight over a stride, so each hind paw carries about
   a quarter, in 0.10–0.12 s of a 0.42 s stride: 0.25 × 308 × 0.42 / 0.11
   ≈ 295 N averaged over stance (an estimate from the duty, not a measured
   force: the traces carry no contact forces), about 2.5× what the hock
   holds. M1's 3× body-weight case asks more again. (The first version of
   this note gave 590 N: it put the pair's half on one paw, 2× too high.
   Corrected in orun11 iteration 9.)
3. **The leg that stays up stands with its foot reversed.** At its
   toe-off the toes are 42–72 mm *behind* the hock axis: the hock is
   carried forward over the paw, so the load's moment about the hock has
   the other sign and the metatarsus slants back under the leg. On
   heel1-s1 the RH does it with the knee folded to −56.5° (3.5° from its
   60° stop, its drive at peak 34 % of stance) and the hock *extended*
   (+3.5°, against the clip's fold) and never reaches the hock's peak; on
   rod1-s1 the LH does it with the hip at +33.5° and the knee at −40°,
   its hock still at peak 66 % of stance. Both keep the case 77–90 mm up.
   Neither resembles the clip's stance.
4. **Which leg does which is a symmetry the policy breaks, not a defect
   of one side.** The two legs' models are mirror images (same drive,
   gains `gainprm 30.08`, force range ±9 N·m, damping, limits mirrored),
   both clips are mirrored, and the two runs chose opposite legs.
5. **The plantigrade clip's heel-down is a step, not a motion.** In one
   19.8 ms sample the clip moves the hip 25–30°, the knee 33–56° and the
   hock 20–22° into the heel-down pose (1,000–2,800 °/s), and back out at
   the next. A 30 N·m/rad position servo with a 9 N·m limit moves at most
   17° before it saturates; no drive tracks that. The clip carries the
   pose but not a path to it (ADR-777's `heel_from` 0.5 switches the
   stance's IK target half-way through).
6. On heel1-s1 the up leg also touches down 2.94 times a second against
   the down leg's 2.39: it taps once in some strides.

## The cause, and the screen that tests it

The binding cause is the **hock drive's torque against the foot's
lever**: an AK60-6 (9 N·m peak, 3 N·m rated) at a hock whose toes are
~78 mm ahead of it at push-off. The plantigrade pose is reached only by
letting that drive lose, and the other leg avoids the lever by reversing
its foot. A reward term or a clip change cannot make the drive hold; the
critic's "if both legs fail" screen should change the hock.

Next screen (a mechanism change, cold, O3 and O7): a sold hock drive with
more peak, from the catalog: the AK80-9 V3 (22 N·m peak, 490 g against
the AK60-6's 380 g; holds about 280 N at a 78 mm lever) or the AK70-10
(24.8 N·m, 621 g; about 320 N). The hip and knee's AK10-9 (53 N·m) would
hold about 680 N but is the heaviest tier, far out on the leg. The
AK80-9's ~280 N is about 95% of the ~295 N estimate through the toes
alone, and the AK70-10's ~320 N covers it; the screen also measures whether
the case on the floor at push-off (the plantigrade load path the down leg
uses now) carries the rest: what it
tests is a hock that holds the foot until the case lands, on both legs,
rather than collapsing past the clip on one and reversing on the other.
A second, smaller change for the same screen or the one after: smooth the clip's heel-down so it moves
over several samples rather than one (finding 5), a generator change
that needs its ADR.
