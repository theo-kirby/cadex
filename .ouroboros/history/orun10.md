---
run: orun10
machine: sb1x
started: 2026-10-17T20:02:28
ended: 2026-10-18T09:30:21+00:00
hours: 9.3
state: killed
iterations: 18
commits: 27
criteria_ticked: 0
criteria_closed: 0
criteria_total: 8
merged: 59aebab982d3edd0aa33b8318d0a4c956b1a5b97
branch: ouroboros/orun10
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun10

18 iterations in 9.3h on `sb1x`, killed (-). Branch `ouroboros/orun10`, merged as `59aebab9`.

## The numbers

| | |
|---|---|
| iterations | 18 (changed 18, recorded 0) |
| commits | 27 — 31 files changed, 2099 insertions(+), 8 deletions(-) |
| criteria | **this run ticked 0**; 0 of 8 checked at the tip |
| reverts | 0 |
| verdicts | continue 18 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5, scribe claude:claude-opus-5-5 |
| usage | claude seven_day 34% -> 39% (+5 this run); claude five_hour 9% -> 1% (-8 this run) |

## What landed

- orun10 J1/S1: j1-c3 judged 0/10 at 25/50/75/final/best; the com_z < 250 floor never fires (com_z min 314.6 mm on 50 episodes), the chest still parks 10-20 mm short of the 300 mm face, rising at most +12 to +21 mm; the warm start from the parked hold is the wrong start. s1-g8 (cold gallop, 2.7 Hz clip, orun10-cat 961435e1) launched
- orun10 J1/S1: leap collapse becomes a world floor (com_z < 250, orun10-jump c65cf762), checked on 170 judged episodes; j1-c2 at 3e-4 lost the warm start on its first update and was stopped; j1-c3 (j1-c1 best, lr 3e-5) launched; O8 on s1-g4 final vs s1-g6 at 100: no leg drive or the spine binds at 2.4 Hz, the spine binds at 3.0 Hz (37% of frames at peak)
- orun10 J1: j1-c1 judged at 25/50/75/100/125/final(150)/best(138), 0/10 throughout; from 75 the cat parks its chest 8-53 mm short of the 300 mm face because the leap task's collapsed termination (scan_4 < -95.2) is a wall at x = 3000 unless the chest is already 230 mm up; hold earns 9.2-9.6 a step vs a 13.94 leap estimate, but every partial climb ends the episode; no_fall fails the same way (base COM share 0.21-0.23 over the ledge)
- orun10 S3/F1: s3-h1 final filmed beside s1-g4 final, seed 1001 (side-on real time + 0.2x, and from behind at 0.2x showing the wider hind track); stills on the dark floor; films outside the repo in ~/orun10-progress/s12
- orun10 S3/J1: s3-h1 judged at 25/50/75/final/best (hind passes the fore print +63 mm outside vs s1-g4's +8, lands +33 mm outside and +119 mm ahead; top speed 4.310 vs 4.486 m/s, -3.9%); j1-c1 leap task trains cold on the straight 2.5 m/s J goals (orun10-jump 07e833fb, goal-only change; leap 13.94 vs stall 6.73 / detour 4.19 per step), launched
- orun10 J1/S3: j1-s2 judged at 25/50/75/final/best9 (0/10 throughout; detours 4 -> 0, every seed now stalls at the ledge face, 1.23 m/s); s1-g4 final runs the hind track in line with the fore (-15 mm per frame, +8 mm at the pass, lands 148 mm ahead of the fore print); s3-h1 outside-hind screen launched warm from s1-g4 final on orun10-cat ccf3d180
- orun10 S1/J1: s1-g7 judged at 25/50/75/final (best 4.031 m/s at 99, below s1-g6@100's 4.072; clip length spent); per-step check shows +x progress and an off-line price pay the leap over the stall and the detour; j1-s2 launched warm from j1-s1 on orun10-jump 6abd8390
- orun10 S1/J1: per-step check shows the gallop reward already pays the fastest judged policy at every clip weight; j1-s1 judged 0/10 at 25/50/75/final (stalls at the face, detours round the ledge); s1-g7 launched cold (reference is not a curriculum key)
- orun10 S1: s1-g6 judged at 150/best142/best193/final (speed peaks at 100, 4.07 -> 3.43 m/s; clip-tracking outpays speed); clip stride reaches 750 mm at duty 0.20; j1-s1 launched
- orun10 S1/J: s1-g6 judged at 50 and 100 (3.0 Hz holds, 4.07 m/s at it 100, j_spine binds); orun10-j3 rebuilt 6 m wide; J1 screen launcher ready
- orun10 s1-g5 table: checkpoint minima; s1-g6 cold start settled
- orun10 S1/J1: s1-g5 judged (falls 4.50 -> 4.27 m/s), s1-g6 cold at 3.0 Hz; J1 zero-shot probe, J courses 6 m wide
- orun10 S1: s1-g4 judged at every checkpoint (best 4.498 m/s, 0/10, clock 2.38 Hz, still climbing); s1-g5 extends it
- orun10 S1: s1-g3 wiped at its first actor update (lr 3e-4); s1-g4 relaunched at 3e-5
- orun10 S1: s1-g1 judged on gallop_spec, every checkpoint (best 4.258 m/s at it280, 0/10); s1-g3 screen launched
- orun10 J3 probe: state only what was measured
- orun10 J3: course 14 built as orun10-j3, gap metrics on its model
- orun10 J: leap metrics (ADR-772) and the J courses in orun10-jump
- orun10 S1: O8 drive-at-peak by stride phase, and the gallop sprint task (s1-g1 training)
- orun10 S1: sprint metrics (ADR-771) and the flat sprint baseline

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

The owner stopped orun10 at iteration 19, 9.3 h into its 24 h. Every iteration was accepted and recorded, so the operator only recorded the stop. s1-g8 (cold gallop, 2.7 Hz clip) was stopped at iteration 37, unjudged. Its 25-iteration checkpoint is in `~/cadex-projects/orun10-cat/runs/s1-g8`.

**Where each criterion ended.**
- **S1, top speed: open.**
  - Best is s1-g4 final, a median of 4.486 m/s against the 5 m/s target, 0/10. It fails only on top_speed, with no falls, worst RMS 1.49× rated and peak margin 0.
  - Baselines: orun7's gallop 4.22–4.25 m/s on the earlier model, orun9's c1-c6 2.74 m/s.
  - Ruled out:
    - extending s1-g4 (s1-g5);
    - a 3.0 Hz clip (s1-g6, which peaks at 4.07 m/s, then collapses);
    - a 750 mm clip (s1-g7, 4.03 m/s);
    - down-weighting the clip.
  - O8 measured that at 2.4 Hz the spine never reaches peak; at 3.0 Hz the spine is at its 22 N·m peak in 37% of frames. 2.7 Hz is untried.
- **S2, the gallop: open, not written up.** The contact metrics exist, but nobody wrote the flight-per-stride report for s1-g4.
- **S3, the outside-hind stride: tried and measured.** s3-h1, warm from s1-g4:
  - its hind foot passes the fore print +63 mm outside (s1-g4: +8) and lands +119 mm ahead;
  - top speed 4.31 against 4.49 m/s (−3.9%);
  - filmed side-on and from behind (`docs/probes/orun10/s3-*`).
  - Nobody ticked it.
- **J1, the 30 cm ledge: open, 0/10 on every checkpoint of five lineages** (j1-s1, j1-s2, j1-c1, j1-c3; j1-c2 was wiped by lr 3e-4).
  - The leap task's `scan_4` collapse termination was a wall at the ledge face, so cold training learned to park there.
  - Replacing it with a world floor (`com_z < 250`) and warm-starting from the parked policy changed nothing: the floor never fired, and the chest still stops 10–20 mm short.
- **J2, J3, F1, R1: not started.** The J3 course (`orun10-j3`) is built. The films so far cover only S3. There is no `REPORT.md`.

**What this taught.**
1. **Making the critic check its sources worked.** From iteration 6 on, every verdict cites the `evaluation.json` it opened and confirms the numbers. orun9's critic read nothing. Keep the rule.
2. **A training termination can be the whole failure.** j1-c1's reward said "leap" (13.9 a step against a 6.7 stall), but a terrain-relative collapse check ended every partial climb. Before blaming reward or spec on a terrain task, replay its terminations against the course geometry.
3. **Removing a blocker does not undo a converged habit.** A warm start from a parked policy at lr 3e-5 stays parked. After fixing a task, train cold, or at least not from the policy that learned the workaround.
4. **Speed is a clip-and-spine problem, not torque budget or reward weights.** Each gallop clip's clock and length set the gait, and the reward already ranks the fastest policy first. The spine is the drive that binds as the clock rises.
5. **The loop under-uses the GPU between judgments.** It was idle from 03:53 to 04:28 while j1-c1's results were analysed. A charter line asking that the next screen launch before the write-up would help.
6. **Ticking criteria still needs a report.** S3 was done by any reading but stayed unticked because the scribe ticks only on a closing write-up. Ask for per-criterion closing notes early.

**Next run.**
- **S1:** judge or rerun s1-g8 (2.7 Hz). If it beats 4.49 m/s, try 2.6–2.8 Hz with a longer cycle. Otherwise the spine needs a design answer: a stronger spine drive or a stiffer passive spine, which is an owner call under O2.
- **J1:** train the `c65cf762` floor bundle cold at the default lr. First check that the run-up reaches the face fast enough, and consider a jump curriculum (10 → 20 → 30 cm) or a take-off reference clip.
- **Close the open write-ups:** S2's flight-phase report on s1-g4, and tick S3.
