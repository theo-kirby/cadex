---
run: orun13
machine: sb1x
started: 2026-10-20T20:55:26
ended: 2026-10-21T09:11:25+00:00
hours: 8.2
state: killed
iterations: 15
commits: 21
criteria_ticked: 0
criteria_closed: 0
criteria_total: 10
merged: no
branch: ouroboros/orun13
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun13

15 iterations in 8.2h on `sb1x`, killed (-). Branch `ouroboros/orun13`, not merged.

## The numbers

| | |
|---|---|
| iterations | 15 (changed 15, recorded 0) |
| commits | 21 — 36 files changed, 4216 insertions(+), 10 deletions(-) |
| criteria | **this run ticked 0**; 0 of 10 checked at the tip |
| reverts | 0 |
| verdicts | continue 15 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5, scribe claude:claude-opus-5-5 |
| usage | claude seven_day 62% -> 66% (+4 this run); claude five_hour 4% -> 25% (+21 this run) |

## What landed

- orun13 P1: g8-gate stopped at 25 under O8 (RH outside-clip toe-offs 0.63->0.72, 0.66 m/s, LH heels 0.04, no flight; spine at flex stop 0.29); lh_roll.py: the clip lifts heel and paw within a sample and holds its hock, LH rolls 3+ frames on 0.50 of toe-offs by driving the hock heel-up at peak; roll_brake scored per step (0.62/0.49 on roll frames, 0 on clip); g9-roll (g4-peak task + roll_brake -4, cold, 4f9f48f9) launched
- orun13 P1/O1: g7c-hock75 fails its rule at 25 (LH heels 0.42, toe-off 0.38/0.62, toes-up 0.14/0.15, RH flat on the -75 stop 0.55, loop gap 4.4 mm) and is stopped; leo-v02.1 stays rejected; hock-drive.md: the hock drive is at peak pushing the heel up, so more torque is not the toe-off lever (not built); stance_gate.py: RH's toe-off windows lie outside the clip's stance on 0.46 of toe-offs (g4-peak-50), where heel_pitch pays nothing; g8-gate (heel_pitch gated on clip stance or paw contact, cold, leo-v02 86c15551) launched
- orun13 P1/O1: g7-hock75 (leo-v02.1, hock stop -75) lifts heels to 0.46/0.41 (hock_down 6/10) at 2.60 m/s but fails its keep rule at 50 (RH toes-up 0.21, RH flat frames on the new stop 0.30, front loop gap 4.6 mm); leo-v02.1 not kept, accepted revision restored to b4680361; the stop binds together with the hock drive at peak; g7c-hock75 (warm, v02.1) runs to 25 under a written restore rule
- orun13 P1/O1: g6-swank fails its keep rule at 25 (LH heels 0.11, hock stance offset up) and at 50 is no better than g4-peak-50; leo-v02.1 widens the hind hock's heel-side stop -70 -> -75 (-80 met the shin, rejected; clearance_diff.py: 16 static / 8 swept failing pairs, as leo-v02); g7-hock75 (cold, g4-peak's task) launched
- orun13 P1: g4-peakf at 25 fails its keep rule (heels 0.46/0.19, toe-off 0.61/0.33, LH toes-up 0.27, 2.55 m/s), stopped; hind_reach.py: toes-up is not a reach limit (hock 18-29 deg from its stop, command on the joint, effort 0.15-0.25), but the hock is at peak heel-up through stance and the fast flat foot sits on its -70 stop; g6-swank (hind ankle tracked in swing only, cold, 936e27e5) launched
- orun13 P1: g5-toe at 25 (toe_stance -10) lifts heels 0.37/0.41 and toe-off 0.52/0.42 but by heel-only stance (toes-up 0.63/0.69) at 0.81 m/s, no flight; fails keep rule, stopped at 32; leo rebuilt to b4680361; g4-peakf (g4-peakc-25 warm, lr 3e-5) launched, no dip at first actor update
- orun13 P1: g4-peakc at 25 lifts heels to 0.47/0.28 and toe-off to 0.61/0.48 at 2.65 m/s but fails its keep rule (RH toes-up 0.18); stopped; toeoff_term.py: toe-offs fail by a 3-frame roll (LH) and taps (RH), landing toe frames 0-6%; g5-toe (toe_stance -10, cold, 019d8743) launched
- orun13 P1: g4-peak at 50 lays both soles flat (toes-up 0.09/0.06 from 0.32/0.87, heels 0.44/0.22) at 2.43 m/s (2.80); kept for P1; RH now a toe stance that taps (4.00 vs 2.33 Hz); foot_frames.py per-leg frame letters and flat stills; mirror augmentation not built (habit gone; clip chiral); g4-peakc warm +50 launched
- orun13 P1/O5: g3-flat-50's RH toes-up foot swaps to LH under mirror_policy (heels 0.13/0.40, toes-up 0.86/0.27 of heel-down frames): the policy's hand, not the model; heel_expr.py: heel_pitch reads both soles at +63.9 on all 21 clip samples; g4-peak at 25 fails its keep rule (heels 0.13/0.14 vs g3-flat-25 0.23/0.11) at 0.94 m/s (0.62); runs on to 50, judged against g3-flat-50 on RH toes-up
- orun13 P1: g3-flat at 50 kept (2.80 m/s, heels 0.39/0.11, overreach 10/10, stride 1130/1121, hind-paw/elbow clash gone); g2-heel5c stopped at 25 (3.03 m/s, no_tap 8/10, but heels 0.10/0.05); heel_band.py: toe stances at +8.5..+19 deg get 0.75-0.96 a frame from heel_pitch's <=10 band; g4-peak (heel_pitch peaked on the flat sole, on g3-flat's task, b4680361) launched
- orun13 B1/O5/P1: g2-heel5 at 50 gallops 2.58 m/s with flight 0.15 s and straight 10/10 but heels 0.23/0.11 (0/10); mirror tests: model mirrors, heel split and veer swap under the policy mirror (policy-handed); g3-flat at 25 flat 0.85/0.62 (from 0.55/0.65) but heels 0.23/0.11, 0.62 m/s, runs to 50; g2-heel5c warm +50 queued on e46d3273
- orun13 B1/P1: g2-heel5 at 25 moves (0.96 m/s, heels 0.24/0.57, 0/10, straight 0/10); leo's sole is flat at heel_pitch +4.5 deg (hind_flat_target.py), hind_flat retargeted two-sided; g3-flat queued on a280b070
- orun13 B1: g1-s1 at 50 shuffles in place (0.32 m/s, heels 0.09/0.21); cause: leo's task used script defaults (speed 14*v/7 m/s = 3.4/step at the clip vs heel5's 16.7); reward_terms.py; g2-heel5 launched on heel5's stored task + 62.5 ms rotary clip (e46d3273)
- orun13 B1/O3: g1-s1 at 25 stands (0.21 m/s, heels 0.47/0.20); leo probes (spine_foot.py, p2_lag.py); clip tied (hind 0, fore 21 ms), g2-lag15 queued on a 62.5 ms RH-lead rotary clip
- orun13 B1: leo v02 bundle checked (clip j_spine2 = j_spine, ±7°), stand hold 1 mm above v07 so scan_stand stays -25.2, g1-s1 screen launched at ~63 s/it

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

The owner stopped orun13 at iteration 16 (8.2 h of 12) to put a free paw pin back on leo's hind foot. Every P1 screen on the welded paw failed at the toe-off.

- **The best screens:**
  - g4-peak, with `heel_pitch` peaked on the flat sole, laid both soles flat at 2.43 m/s;
  - g7-hock75, with the hock stop widened to -75, reached heels 0.46/0.41 and passed `hock_down` on 6 of 10 seeds. Its model change was judged and not kept.
- **Why the rigid foot failed at toe-off:**
  - the hock drive sat at peak, driving the heel up through stance (`hock-drive.md`, `hind_reach.py`);
  - LH rolled onto its toes for three or more frames on half its toe-offs (`lh_roll.py`);
  - RH lifted off outside the clip's stance, where `heel_pitch` pays nothing (`stance_gate.py`).

  A welded paw makes the hock do the whole push-off.
- **Asymmetry was the policy's, not the robot's,** again: the mirror tests settled it in one iteration.
- **Setup lessons:**
  - leo's task needed heel5's stored task settings; the script's defaults shuffled in place;
  - the clip needs real pair lag (62.5 ms);
  - the trainer runs at about 63 s per iteration.
- **The O1 process worked:** a model change was written up, built, tagged, screened, rejected and restored cleanly.
