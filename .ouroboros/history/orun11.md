---
run: orun11
machine: sb1x
started: 2026-10-18T18:35:07
ended: 2026-10-19T07:17:22+00:00
hours: 8.2
state: killed
iterations: 10
commits: 15
criteria_ticked: 0
criteria_closed: 0
criteria_total: 7
merged: 1f0ab418e4050828dd7e74516e87dd7b59aa54fe
branch: ouroboros/orun11
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun11

10 iterations in 8.2h on `sb1x`, killed (-). Branch `ouroboros/orun11`, merged as `1f0ab418`.

## The numbers

| | |
|---|---|
| iterations | 10 (changed 10, recorded 0) |
| commits | 15 — 32 files changed, 3666 insertions(+), 98 deletions(-) |
| criteria | **this run ticked 0**; 0 of 7 checked at the tip |
| reverts | 0 |
| verdicts | continue 10 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5, scribe claude:claude-opus-5-5 |
| usage | claude seven_day 45% -> 49% (+4 this run); claude five_hour 6% -> 11% (+5 this run) |

## What landed

- orun11 iteration 10: ADR-778 the gait generator eases a heel into and out of its hold; orun11-cat rebuilt (158a8c12), push-off unchanged
- orun11 iteration 9: trim1-s1 judged 0/10 (RH hock never down); AK80-9 hocks built (2c5a51e6), every verdict and M1's static check pass; hock80-s1 training
- orun11 iteration 8: why one hind lays down — the hock's AK60-6 buckles at peak on the down leg; the up leg reverses its foot
- orun11 iteration 7: turnbuckle trimmed 10 deg (ca32a9b4), M1 static check passes; heel1-s1 judged 0/10, 3.51 m/s, RH hock never down; trim1-s1 training
- orun11 rung 8: j_tail1-j_tail7 swept with the bound raised (117-128 s each); no common volume on any pair
- orun11 rung 8: ADR-777 assembly.gait declares a plantigrade stance; plantigrade clip on orun11-cat (07a92830); heel1-s1 training
- orun11 rung 7: hind hip flexion -45 and knee -60 cleared on orun11-cat (d6fe5680); rod1-s1 judged 0/10, right hock down 0.45
- orun11 rung 6: ADR-776 gait generator holds leg loop closures; eq1-s1 judged 0/10; no plantigrade clip reachable in the hind limits
- orun11 M1: rod A built on orun11-cat (4cd04aaf), fit/sweep/mounting pass; ADR-775 loop closures beside touch sites
- orun11 M1: three coupled hind-foot linkages sketched; a rod from the shank picked (pin = 60 - 0.6 hock within 1.4 deg)
- evaluation: heel stance, every landing's rate, hind overreach and pair lag (ADR-774)

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

The owner stopped orun11 at iteration 11, 8.2 h into its 24 h, and then had the foot redesigned by hand as feline v06 (ADR-779).

- **A coupled foot did not give a plantigrade gait.** The rod tied the paw to the hock, and M1's static check passed (iteration 7). But five cold screens (eq1, rod1, heel1, trim1, hock80) each laid at most one hind hock down. The other leg reversed its foot or buckled at the hock's peak. P1 was 0/10 every time, and speed held near 3.5 m/s. Moving from the AK60-6 to the AK80-9 hock (iteration 9) did not change that by hock80-s1's iteration 100.
- **Front-paw tapping returned with the plantigrade clip.** Fore touchdowns ran at about 2x the hind stride on every heel-clip screen (heel1, trim1, hock80), against 1.26x on rod1's toe clip.
- **The owner rejected the mechanism, not the measuring.** The heel and footfall metrics (ADR-774), and the gait generator's plantigrade stance and heel ease (ADR-776 to ADR-778), carry over to feline v06. The rod and its loop closures do not. A linkage that couples two joints the policy needs separately removes freedom the gait used. The replacement is a rigid metatarsus, a sprung paw hinge at rest at the standing angle, and a rubber shoe under the hock drive.
- **The loop picked hardware fixes before checking for asymmetry.** One leg always lay down and the other never did. A mirrored-leg test or a symmetric screen would have separated a clip or model asymmetry from a torque shortfall before a drive swap.
