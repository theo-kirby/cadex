---
run: orun16
machine: sb1x
started: 2026-10-22T06:59:42
ended: 2026-10-22T21:25:14+00:00
hours: 10.3
state: killed
iterations: 19
commits: 30
criteria_ticked: 0
criteria_closed: 0
criteria_total: 12
merged: 4789694468621eb42c78f950644dac1b4b30e6cf
branch: ouroboros/orun16
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun16

19 iterations in 10.3h on `sb1x`, killed (-). Branch `ouroboros/orun16`, merged as `47896944`.

## The numbers

| | |
|---|---|
| iterations | 19 (changed 19, recorded 0) |
| commits | 30 — 45 files changed, 4621 insertions(+), 9 deletions(-) |
| criteria | **this run ticked 0**; 0 of 12 checked at the tip |
| reverts | 0 |
| verdicts | continue 19 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5, scribe claude:claude-opus-5-5 |
| usage | claude seven_day 76% -> 1% (-75 this run); claude five_hour 3% -> 13% (+10 this run) |

## What landed

- orun16 SG: sg_lag.py (left uncommitted at the owner's stop)
- orun16 SG: sg-s9 timed (69 s an iteration) and judged at 25 (rule does not fire, runs to 50): digitigrade at 700 on both legs (heel 0.01 / 0.00) but tips on 8/10 and does not follow the command (1.08 / 1.09 / 1.15 m/s); Q2's 1 ms step written up under O1 (1.81x solver cost, not built)
- orun16 SG: sg-s9 (cold, 700-2400 schedule, sg-s7's task less hock_land) launched on leo dc488631
- orun16 SG: sg-s8 judged at 25 and stopped by its rule (slow heel LH 0.34 / RH 0.23, 2400 at 2.32 m/s); the 0.7 m/s reference stands heels up as sg0; commanded 700, sg-s4-50 is digitigrade (0.07/0.10) and sg-s7-25 is not (0.22/0.33); sg-s9's rules, written before launch
- orun16 SG: sg-s8 (sg-s7's task + hock_land, warm from sg-s7-25) launched on leo 228e5a97
- orun16 SG: the sg0 clip lands the slow paw heel-up (+30/+44 mm at touchdown) while sg-s7-25 swings the heel 9-22 mm below the paw and lands heel-first (hock 41-59 deg off the clip); hock_land scored (1.39 a step at 1000, 0 at 2400); sg-s8's rules, written before launch
- orun16 SG/RL: sg-s7 judged at 25 and stopped by its rule (heel LH 0.20/0.25, RH 0.19/0.31 at 1000/2400; slow heel-down in early contact); LH taps 0.38 a stride, 1000 hind lag 140 ms, RL's clauses hold at sg-s7-25
- orun16 SG/RL: sg-s7 (contact-gated heel_sched, warm from sg-s6-25) launched on leo 6dba5e5e; tap lever scored on sg-s6-25 (net a LH tap at 1000: -6.2 at hind_scuff w -8 under sg-s7, -10.8 at w -16; a tap reset fires only on taps but ends 10/10 slow seeds by 1.17 s)
- orun16 SG: sg-s7's rules (contact-gated heel_sched on sg-s6's task, warm from sg-s6-25), written before launch
- orun16 SG: RH's heel-down frames fall before the clip's touchdown (0.63/0.68/0.96 at 1000/1700/2400), so heel_sched as built pays RH's heel up at 2400 (+1.00); contact-gated heel_sched scored (+1.22/+1.23 at 1000, -1.47/-1.35 at 2400), not built; sg-s6 judged at 25 and stopped by its rule at 26 (LH taps 0.64 a stride, 1000 hind lag 30 ms; RH heel now rises 0.27/0.34/0.42)
- orun16 SG: sg-s5 judged at 25 and stopped by its rule (LH heel follows the command 0.06/0.18/0.26, RH runs the other way 0.39/0.33/0.29; 1000 hind lag 30 ms from LH's mid-swing tap, 180 ms without); sg-s6 (sg-s5 + hind_scuff w -8, leo 73f833c9) launched warm from sg-s5-25 with its rules
- orun16 SG: sg-s4 judged at 50 (inside the speed band 1.19/2.13/2.78 m/s, slow heel low, 0/10 rotary at 1000: LH taps mid-swing once a stride, not a second rhythm; hind lag without taps 0.320->0.204->0.180); hind_scuff scored (charges only the taps), not built; sg-s5 (heel_sched) launched warm from sg-s4 final with its 25 rule
- orun16 SG: sg-s4 judged at 25 (rules do not fire, runs to 50; overrun bites at 1000: 1.31 m/s from 1.48; heel not scheduled; fore lag share now falls 0.280->0.263->0.229, hinds near-tie at 1000); heel_sched (command-scheduled metatarsus target, both ways) scored per step and written for sg-s5, not built
- orun16 SG: sg-s3 judged at 25 and stopped by its rule (2400 RH heel 0.17 < 0.2; heel_tail raised the slow heel 0.21/0.32 instead), rotary 10/10 at every command now (hind lag 0.320/0.200/0.176); sg-s4 (heel_tail + overrun) built 564d0dd7 and launched warm from sg-s3-25
- orun16 SG: sg-s2 judged at 80 — tracks the command (1.51/2.52/3.02 m/s at 1000/1700/2400, overruns 26-51%), heel not scheduled (LH 0.13/0.12/0.20, RH 0.24/0.31/0.14), rotary 10/10 with falling lag 1700->2400 but hinds tied at 1000; sg-s4's overrun term (w -10, 25% band) scored per step and written, not built under sg-s3
- orun16 SG: sg-s2 judged at 50 (2.06/2.25/2.20 m/s at 1000/1700/2400, on its toes everywhere, heel <= 0.12; 50 rule does not fire on the engine's shares, runs to 80); heel_pitch's cubic has no slope where its paws stand, so sg-s3 adds heel_tail (leo e732b1dd), queued warm behind it
- orun16 SG/Q2: sg-s2 judged at 25 (moves forward, 0.87/1.22/1.09 m/s, on its toes everywhere, U<=0.01; 25 rule does not fire, runs to 50); Q2 front rod gap is 4 ms loop dynamics under ~1 kN fore-stance load, no solver setting at the 2 ms step closes it, stiffer stops do not
- orun16 SG: sg-s2 timed (~12:05 for 80 it, inside budget)
- orun16 SG: sg-s1 judged at 50 — heel share rises with the command (LH 0.31->0.91, RH 0.19->0.58) but in place (0.26 m/s at 2400); 50 rule fired, stopped; sg-s2 (track_speed a linear tent, leo 32dd914b) launched 09:54
- orun16 SG: sg_judge.py (gallop_sg at held commands); sg-s1 judged at 25 on 1000/1700/2400 — steps in place (0.08-0.46 m/s), no lag or flight; runs on to 50
- orun16 SG: v05-s1x stopped at +25 under O8 (RH heel 0.35->0.15, LH U 0.25->0.28); gallop_sg task built on leo 721d10da, strides equal to sg_clip's; sg-s1 cold 80 it launched 08:47
- orun16 SG: schedule strides sg0-sg3 judged offline (1.00-2.40 m/s, clip heel 0->0.8, lag 0.30->0.15, 150->50 ms, order holds); v05-s1x warm +50 launched 08:11
- orun16 B1: v05-s1 judged at 25 and 50 — pins p95 741/380 deg/s (<900), 2.39 m/s, heels 0.40/0.35; LH U 0.25 is a touch-down fold; SG schedule read
- orun16 B1: leo-v05 bundle (15d9feb4) checked against hk12-s1's (damping 3->5, hock_at_toeoff out, task otherwise identical); v05-s1 cold launched 07:00:50, ~85 s/it

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

(unwritten)

## What this taught

- **A speed-commanded policy works on leo, but the heel schedule did not come from reward terms.** sg-s4 tracked the command (1.19 / 2.13 / 2.78 m/s at 1.0 / 1.7 / 2.4) with falling lag and rotary 10/10 above the slow end. Five stance heel terms (heel_tail, heel_sched, gated heel_sched, hock_land) each moved one leg or one end the wrong way. Every one ran as a warm chain judged at 25, so habits piled up: commanded at 0.7 m/s, warm sg-s7-25 sits heel-down while cold sg-s4-50 stands heels up.
- **The cold 0.7–2.4 m/s screen (sg-s9) was the first to give the shape asked for:** heel 0.01 / 0.00 at 0.7 m/s, rising to RH 0.38 at 2.4. At 25 it neither tracked speed nor stood up (tipped on 8/10 slow seeds). It was still training at the stop.
- **Charter error:** it said `paw_fold` was out of the task; hk12-s1's bundle carries it (w −10), so every v05/SG task did too. Q2's open rod loops are loop dynamics: only a 1 ms step closes them (1.8× solver cost).
