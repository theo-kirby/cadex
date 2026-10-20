---
run: orun12
machine: sb1x
started: 2026-10-19T20:13:55
ended: 2026-10-20T11:44:35+00:00
hours: 10.9
state: killed
iterations: 21
commits: 30
criteria_ticked: 0
criteria_closed: 0
criteria_total: 9
merged: no
branch: ouroboros/orun12
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun12

21 iterations in 10.9h on `sb1x`, killed (-). Branch `ouroboros/orun12`, not merged.

## The numbers

| | |
|---|---|
| iterations | 21 (changed 21, recorded 0) |
| commits | 30 — 51 files changed, 4890 insertions(+), 23 deletions(-) |
| criteria | **this run ticked 0**; 0 of 9 checked at the tip |
| reverts | 0 |
| verdicts | continue 21 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5, scribe claude:claude-opus-5-5 |
| usage | claude seven_day 54% -> 58% (+4 this run); claude five_hour 24% -> 22% (-2 this run) |

## What landed

- orun12 P2: every rotary count so far read the engine's tie-break (910cdb5a: 173/208 strides land a pair in one 20 ms frame); on the heel5 clip no_tap 1.03, every_stride 0.98, overreach 279 mm, flight 0.26 s already pass 10/10; the clip's 21 ms fore lag and zero hind lag cannot read rotary; 2/21 on both pairs is refused at 0.70 m (RH knee/ankle at a stop) and reachable at 0.65 m; legs.py counts tied strides; p2_lag.py, clip_lag.py
- orun12 Q2/O3: the right hind paw in the right forearm swaps sides under the mirror (8.5 mm R -> 8.3 mm L; every >5 mm pair swaps), so it is the policy's; fore-rod solref is already 2x timestep, nothing stiffer; heel7-s1 at 25: heels 0.10/0.13, pin snaps 0.2%/0.7% (was ~10%); q2a-s1 (heel5c task, pin_damp 3.0, forearm panel capsules, 7ccbf80f) queued cold for 200
- orun12 Q2/O9: the P1 policy 910cdb5a fails Q2 — fore rod loops 2.71/2.86 mm, 6 real-mesh pairs over 5 mm (right hind paw 8.5 mm into the right forearm panel on 10/10 seeds; wrist in chest 6.3 mm, was 18.4); no blow-up; a warm dynamics fine-tune is refused by the trainer (ADR-736)
- orun12 P1/O2a: heel5c-s1's final policy (910cdb5a) passes P1 on both hind legs: hock_down 10/10 each (0.60/0.61), hock_at_toeoff LH 9/10, RH 8/10, 8/10 seeds both; 2.91 m/s, 0/10 gallop_spec; the 3 failing toe-offs are the first after the settle; toeoff.py; heel7-s1 timed at 950 s to iteration 10
- orun12 P1/O2a: heel5c-s1 at 50 puts both heels past 0.40 (0.44/0.51; LH 9/10, RH 10/10 seeds) but toe-off fails (0.82/0.95, LH 0/10, RH 4/10), 0/10 at 3.22 m/s; mirror swaps the lower heel (0.47/0.43), so the 14% spread is the policy's
- orun12 P1/O2a: heel5c-s1 at 25 puts the right heel down on 10/10 seeds (0.48, toe-off 0.93, 2/10 at 1.0) but the left falls to 0.35/0.74 (27% apart), 0/10 at 3.15 m/s; heel7-s1 (heel_pitch + flat_feet + pin_damp 3.0, de868f8f) queued behind it
- orun12 P1/O2a: heel6-s1 at 75/100 (flat_feet alone) is 0/10, heels 0.17/0.11 -> 0.19/0.23, toe-off 0.00/0.33, metatarsus 23/17 deg at 3.20 m/s; the dead-end rule does not fire, but heel5-s1 (0.37/0.36) dominates it on every heel measure, rotary 8/148; not extended; heel5c-s1 started
- orun12 P1/O2a: heel6-s1 at 50 is off its toes (metatarsus 32/33 deg) but heels 0.08/0.10, behind heel5-s1-50's 0.19/0.18; Q2 pin candidate measured: the paw pin is overdamped free (zeta 1.53), its snaps are floor-forced at load/damping, pin_damp 3.0 holds 1 N*m to 321 deg/s; not launched
- orun12 P1/O2a: heel6-s1 at 25 stands on its toes (heels 0.03/0.05, metatarsus 71/60 deg) without heel_pitch; the hind paw pin flaps >900 deg/s on 8-15% of frames and overruns its stops by 13-14 deg on every v07 policy; heel5c-s1 (heel5-s1 continued to ~200 on its restored task 816db7e7) queued behind heel6-s1
- orun12 P1/O2a: heel5-s1 at 100 lays both heels down 0.37/0.36 (3% apart, toe-off 0.84/0.57, 3/2 mm, metatarsus 11/10 deg) at 3.21 m/s, 0/10 but the closest to P1 yet and still climbing; flat 50-75; heel6-s1 timed at 953 s to iteration 10
- orun12 P1/O2a: heel5-s1 at 50 has heels 0.19/0.18 (spread 7%, 11/8 mm, metatarsus 18/18 deg) at 2.99 m/s, the best heel yet, so heel_pitch earns its place and the run goes on to 100; heel6-s1 re-queued at budget_s 9,700
- orun12 P1/O2a: ADR-780 flat_feet lays the clip's hind paw flat while its heel is held (metatarsus 7.5 deg, not 18-22); heel6-s1 (feline-v07 d3b4e838, heel3-s1's task + flat clip) queued behind heel5-s1, timed at 67 s/it
- orun12 P1/O2a: right heel held up by the knee, not the hock (engine stance frames); heel4-s1 stopped at 50 (0.14/0.07), track_ankle cut; heel5-s1 pays metatarsus pitch (feline-v07 44411418), launched
- orun12 P1/O2a: heel3-s1 75/100 judged, 0/10; left heel climbs to 0.27 (toe-off 0.33, 4 mm), right falls to 0.02 (36 mm) at 3.38 m/s; heel4-s1 timed at 67.5 s/it, budget 9,000 s holds
- orun12 P1/O2a: heel3-s1 25/50 judged (heels 0.07/0.07, 0.17/0.07; 3.02 m/s); stance hock 21-41 deg off the clip's heel-down angle on every policy; heel4-s1 adds track_ankle (feline-v07 5bcadba8), queued
- orun12 P1/O2a: heel2-s1 stopped at 75 (heels 0.00/0.00 at 3.04 m/s); heel3-s1 pays the heel in clip stance, speed capped at 2 m/s (feline-v07 ac32d3b0)
- orun12 O3/Q1: mirror_policy.py judges a policy's mirror image; the hind asymmetry swaps sides on all 30 seed pairs (policy-learned, sim symmetric)
- orun12 O9: chest box meets the fore legs (feline-v07 ee2168d2); o9-s1 queued behind heel2-s1
- orun12 O9: trace_check.py replays evaluation traces on the real meshes; v07-g1 fails O9 (fore leg 18 mm into the torso, fore rod 2.70 mm)
- orun12 P1/Q1: clip held the heel on 0.4 of stance (the bar); heel_from 0.2 screen heel2-s1; model and hind clip mirror
- orun12 B1: v07-g1 judged at every checkpoint, 0/10; per-leg probe legs.py

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

The owner stopped orun12 at iteration 22, about 11 h into its 24 h. That counts the restart after iteration 6, when the owner added O2a to put the heel first.

- **A reference clip does not bring the heel down by itself.**
  - v07-g1 lifted both heels by iteration 75.
  - Clips asking for 0.8 of stance with the heel down (heel2) or a flat paw (ADR-780 `flat_feet`, heel6) did not lay it down either.
  - Paying for heel contact helped only one leg (heel3).
  - **What worked was paying for a flat metatarsus pitch (`heel_pitch`, heel5).** Continued to 105 iterations, heel5c-s1 (910cdb5a) passed P1 on 8 of 10 seeds, with the heel down for 0.60 / 0.61 of stance.
- **The heel cost speed:** 3.22 m/s → 2.91 m/s. The run never reached S1.
- **The owner's still shows a problem the loop missed.** In `heel5c-final-heels.png` the paws are folded up with the toes in the air while the heels are down. The next charter should require the paw flat, toes down, in stance, and check for it.
- **Asymmetry was the policy's, not the robot's.** The mirror tests (`mirror.py`, `mirror_policy.py`) settled every left/right question in one iteration each. They are worth keeping as standard checks.
- **The footfall order never read as rotary.** The clip lands each pair 21 ms apart, which the engine's 20 ms frame reports as tied. Rotary needs a clip with real pair lag.
- **Q2 was still open at the stop:**
  - the right hind paw is 8.5 mm into the right forearm (a policy habit);
  - the front rod loops are open by up to 2.9 mm.
- **The trainer runs at about 67 s per iteration at 4096–8192 envs on v07**, against 30 s on v06. The push-rod loops make each step heavier.
- **At the stop:**
  - heel7-s1 was stopped at iteration 94;
  - the queued q2a-s1 was cancelled;
  - the uncommitted iteration-22 `queue_run.py --after/--build` option was kept.
