---
run: orun17
machine: sb1x
started: 2026-10-22T17:29:44
ended: 2026-10-23T09:02:04+00:00
hours: 11.3
state: killed
iterations: 17
commits: 25
criteria_ticked: 0
criteria_closed: 0
criteria_total: 12
merged: 6235e46f156f7ccb73d63cd0b5c2b5d250d815df
branch: ouroboros/orun17
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun17

17 iterations in 11.3h on `sb1x`, killed (-). Branch `ouroboros/orun17`, merged as `6235e46f`.

## The numbers

| | |
|---|---|
| iterations | 17 (changed 17, recorded 0) |
| commits | 25 — 28 files changed, 3003 insertions(+), 9 deletions(-) |
| criteria | **this run ticked 0**; 0 of 12 checked at the tip |
| reverts | 0 |
| verdicts | continue 17 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5, scribe claude:claude-opus-5-5 |
| usage | claude seven_day 2% -> 6% (+4 this run); claude five_hour 17% -> 14% (-3 this run) |

## What landed

- orun17: the stopped iteration's REPORT.md and sg_tables.py edits, kept as left
- orun17: R1 skeleton (REPORT.md): criteria table, SG and RL tables from sgt-4-120 (915a9863), the cold SG screens side by side, terms kept and cut, no model change, hocks/wrists/j_tail2 at the clamp; SP/Q1 previews
- orun17: O6 peak margin 0.00 is real, drives at their clamp (hocks 0.20-0.34 of frames, wrists 0.13-0.20, j_tail2 0.62-0.80); sg_tables.py names them; sgt-4-120 mirror (afbc4ad2): RH 1550 heel and 2400 fold swap sides, the policy's; slow fore timing does not mirror
- orun17: sgt-4 judged at 120 (915a9863): 0.88/1.70/2.66 m/s, slow heel 0.00/0.00, fast 0.31/0.38, fast U 0.13/0.24, rotary 4/10/10, every pair >= 40 ms; LF still doubles at 700 (1.89 a stride, 0.24 within 40 ms), so sgt-5 (fore_lag w10) launched 04:24
- orun17: sgt-5-bundle.md: fore_sync is w 2
- orun17: sgt-5 fallback bundle built, not launched (89b5bb40): sgt-4's 18 terms + fore_lag w10, only reward differs, clearance at baseline; launch trigger and sgt-4 extend path written
- orun17: sgt-4 judged at 50 (23573505): 1.55/2.07/2.62 m/s, 0/10, one tip at 2400; slow heel 0.18/0.19, fast 0.07/0.21, fast U 0.49/0.22; fores at 700 still double (LF 1.80, RF 1.62 a stride, 0.62 within 40 ms) though fore_lag rose 0.201 -> 0.313; rule read at 120
- orun17: sgt-3b judged at 120 (0829e712): 0.93/1.80/2.71 m/s, slow heel 0.03/0.00, fast 0.30/0.24, RH U 0.32 at 2400; heel_sched 12:40 not kept (RH fast heel and U, 2400 by 0.02); LF still doubles at 700 (rotary 1/10); sgt-4 on GPU since 01:57
- orun17: fore_lag priced on sgt-4's clip (fore-lag-sgt4.md): at 700, sg-s9-80 +0.449 a step, sgt-1-120 +0.387, sgt-2-120 +0.312, sgt-3b-50 +0.201 (clip 0.721); single-vs-double gap 0.137, as on sgt-3b's clip; fallback w10 with a hind/heel keep rule; fore_pair.py --clip
- orun17: sgt-3b judged at 50 (8c8e365a): 1.74/2.19/2.56 m/s, heel 0.18/0.18 slow, 0.10/0.07 fast, LH U 0.39 at 2400; the fores still double at 700 (LF 1.56-2.00, RF 1.17-1.44 a stride), so sgt-4, the duty 0.35/0.3 slow stance on sgt-3b's terms (leo b09a23b5), is queued cold behind it
- orun17: the slow fore pair (fore-pair.md): the gallop_sg clip lands the 700 mm/s fores 180 ms apart; sgt-2-120 strikes each fore twice a stride (1.89-2.00 / 1.78-2.00), sg-s9-80 once (fores 180 ms apart on 10/10); a duty 0.35 / 0.3 slow stance with a 30 mm swing generates and is written as the next bundle's reference option
- orun17: sgt-2 judged at 120 (5aed59c5): slow end digitigrade (heel 0.00/0.00 at 700), fast heel 0.35/0.25, U 0.28/0.24 at 2400; paw_fold fails its keep rule and is cut; sched_pay.py: heel_sched w 12, half-width 40 gives the slow heel-down frames a slope; sgt-3b launched cold (62025a13)
- orun17: sgt-2 judged at 50 (456ddda6): 1.70/2.20/2.65 m/s, LH U 0.20/0.24/0.44 (sgt-1-50 0.36/0.35/0.60), 2/10 tip at 1550; slow reference asks heel up (+34/+53 deg), the slow heel-down is the policy's at touchdown (slow_heel.py)
- orun17: sgt-1 judged at 120 (ba117ae3): 0.95/1.78/2.73 m/s, hind lag share falls, heel 0.12-0.35 not scheduled; keep rule fails rotary 7/10 at 700 and LH U 0.27 at 2400; sgt-2 (+paw_fold) launched cold
- orun17: sgt-1-50's LH fold is the policy's (mirror swaps it); paw_fold would charge it (98% on LH's U frames), hind_overreach pays ~0 and stays cut
- orun17: sgt-1 judged at 50 (700/1550/2400): 1.64-2.74 m/s, no shape yet; LH lands reaching on a folded paw (U 0.36-0.60)
- orun17: sg_tables.py, SG/RL/O9 tables with verdicts per held command; measured pair lag in ms; checked against sg-s9-80
- orun17 B1: slow reference read (toe-bulb stance, pin unused; option not warranted), gallop_sg trimmed to 18 terms, sgt-1 launched cold
- orun17 B1: sg-s9 judged at 50 and 80 at 700/1550/2400

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

(unwritten)
## What this taught

- **Cold and long behaved as the charter asked, and four reward or reference changes still closed nothing.** sgt-1…sgt-4 were cold screens of 120 iterations, judged at 700/1550/2400 mm/s, all tracking 0.9/1.7/2.7 m/s. The heel came to follow speed (sgt-4-120: 0.00/0.00 slow, 0.31/0.38 fast), and rotary reached 4/10/10. But the slow fore still strikes twice a stride, and the fold returns at speed on one hind or the other.
- **O6 peak margin 0 is real:** hocks, wrists and `j_tail2` sit at their clamp on 0.13–0.80 of frames. The body is torque-limited at these speeds.
- **The owner stopped it at 11.3h for a diagnosis run (orun18):** a control on a stock quadruped to clear or blame the trainer, leo with style terms removed to find its ceiling, then gait style from animal motion capture rather than stacked reward terms. sgt-5 (+`fore_lag` w10) was stopped about 38 min in and never judged.
