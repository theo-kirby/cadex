# orun16 report: leo v05, a cat-like gallop across speeds

Verified against source: 2026-10-22. R1, kept current as criteria close;
not yet the closing report. Each line cites the probe note that holds its
numbers.

## Criteria so far

| criterion | state | evidence |
|---|---|---|
| B1 | met | `b1-ready.md`, `v05-s1.md`: v05-s1-50 (`41693803`, rev `15d9feb4`), pins p95 741 / 380 °/s at 2.39 m/s, heels 0.40 / 0.35, U 0.25 / 0.01 |
| SG, RL | open; sg-s1 (cold, `gallop_sg` on rev `721d10da`) stopped at 50 by its rule: heel share rises with the command (LH 0.31 → 0.91, RH 0.19 → 0.58; 1000 → 2400) and strides are rotary with lag ≥ 40 ms at 1700 / 2400, but in place (0.26 m/s at 2400); sg-s2 (rev `32dd914b`, `track_speed` a linear tent up to the command) at 25 moves forward (0.87 / 1.22 / 1.09 m/s at 1000 / 1700 / 2400; its 25 rule, 1.0 m/s at 2400, does not fire) but on its toes at every command (heel ≤ 0.06), ends early (tipped or collapsed) on 8 / 6 / 4 of 10 seeds, U ≤ 0.01; at 50 it runs 2.06 / 2.25 / 2.20 m/s at every command (overruns the slow ones) on its toes at every command (heel 0.09 / 0.12 / 0.11 LH, 0.03 / 0.05 / 0.05 RH), LH U back to 0.29; its 50 rule does not fire on the engine's shares (2400 above 1000 by 0.02 a leg), so it runs to 80; sg-s3 (rev `e732b1dd`, a `heel_tail` term: heel_pitch's cubic has no slope 22–62° off the flat where sg-s2's paws stand) queued warm behind it, launched 11:34 from sg-s2's final policy; sg-s2 at 80 tracks the command (1.51 / 2.52 / 3.02 m/s at 1000 / 1700 / 2400, leo's fastest judged; overruns by 26–51%) but the heel is not scheduled (LH 0.13 / 0.12 / 0.20, RH 0.24 / 0.31 / 0.14); rotary 10/10 with lag falling from 1700 to 2400 (fore 0.359 → 0.338, hind 0.211 → 0.187, ≥ 62 ms), but at 1000 the hinds land together (16 ms, 0/10 rotary); sg-s4's `overrun` term (w −10, 25% band) scored and written; sg-s3 at 25 stopped by its rule (2400 RH heel 0.17 < 0.2): heel_tail left the fast heel where it was (0.26 / 0.17 at 2400) and raised the slow one (0.21 / 0.32 at 1000), speed 1.48 / 2.54 / 3.09 m/s, but rotary 10/10 at every command now, hind lag 0.320 → 0.200 → 0.176 (≥ 56 ms), fore 0.353 / 0.355 / 0.286 (flat 1000 → 1700, so RL not met by the letter); sg-s4 (rev `564d0dd7`, heel_tail + overrun) launched 12:15 warm from sg-s3's 25; at 25 its rules do not fire (runs to 50): overrun bites at the slow end (1.31 / 2.39 / 2.94 m/s, 1000 from 1.48), heel still not scheduled (LH 0.14 / 0.18 / 0.19, RH 0.31 / 0.27 / 0.19), rotary 10/10 at every command, fore lag share now falls (0.280 → 0.263 → 0.229, ≥ 73 ms) but the hinds near-tie at 1000 (0.105, 52 ms; 0.211 / 0.182 at 1700 / 2400), so RL is not met on the hind pair; `heel_sched` (a metatarsus target moving with the command, paid both ways: heel-up minus heel-down pay +2.4 at 1000, −2.8…−3.2 at 2400, on sg-s3-25's and sg-s4-25's traces) scored and written for sg-s5, not built; sg-s4 at 50 (`c94393a4`) is inside its 30% speed band (1.19 / 2.13 / 2.78 m/s) with a low slow heel (LH 0.05 / 0.24 / 0.25, RH 0.24 / 0.26 / 0.20 at 1000 / 1700 / 2400: still not scheduled on RH), fore lag falling 0.320 → 0.211 → 0.179 (160 / 84 / 61 ms), but 0/10 rotary at 1000: LH taps the floor 20–40 ms mid-swing once a stride (0.99 taps a stride, from 0.37 at sg-s3-25), just after RH lands, which `p2_lag` reads as the hinds together; with the taps left out the hind lag is 0.320 → 0.204 → 0.180 (`hind_rhythm.py`); a lift-gated `hind_scuff` (w −8) charges only the taps (−0.245 a step at 1000, ~0 elsewhere), `hind_tap` cannot tell them from early landings; scored, not built; sg-s5 (rev `839a3378`, `heel_sched` D30 W30 w6 in place of heel_tail, overrun kept) launched 13:19 warm from sg-s4's final policy, 25 rule in `sg-s5-rules.md`; sg-s5 at 25 (`7b7524b6`) stopped by its rule: LH's heel follows the command (0.06 / 0.18 / 0.26 at 1000 / 1700 / 2400) but RH's runs the other way (0.39 / 0.33 / 0.29), though `heel_sched` pays RH's heel-up frames +2.45 over heel-down at 1000, as on LH; speed 1.11 / 2.02 / 2.65 m/s; LH still taps mid-swing (0.88 a stride at 1000), so the 1000 hind lag is 30 ms (180 ms without the taps; 0.360 → 0.255 → 0.180), fore 0.240 → 0.211 → 0.176; sg-s6 (rev `73f833c9`, sg-s5's task plus `hind_scuff` w −8) launched 14:20 warm from sg-s5's 25, rules in `sg-s5-25.md` | `sg-schedule.md`, `sg-reference.md`, `sg-task.md`, `sg-s1-25.md`, `sg-s1-50.md`, `sg-s2-25.md`, `sg-s2-50.md`, `sg-s2-80.md`, `sg-s3-25.md`, `heel-sched.md`, `sg-s4-25.md`, `sg-s4-50.md`, `sg-s5-rules.md`, `sg-s5-25.md` |
| P1 | open; v05-s1x (warm) stopped at +25 under O8, a dead end: RH heel 0.35 → 0.15, LH U 0.25 → 0.28, 2.27 m/s | `v05-s1.md`, `sg-task.md` |
| Q2 | open; the front rod loops open 3.0 / 3.3 mm (v05-s1-50) in fore stance with the wrist drive saturated, under ~1 kN of paw load, by loop dynamics (4 ms time constant), not softness; no solver setting at the 2 ms step closes them, and stiffer carpus/wrist stops (orun14's plan) do not; a 1 ms step does (0.45–0.53 mm) but the 2 ms policy shuffles on it, so it needs a retrain (O1 candidate, not built) | `q2-rod-solver.md` |
| P2, SP, Q1, S1, S2, F1 | open | – |

## Notes for the owner

- **`paw_fold` is in the task.** The charter says "`paw_fold` is not in
  the task", but hk12-s1's bundle, and so v05-s1's (built to be hk12-s1's
  task, as B1 asks), carries `paw_fold` at weight −10 (21 terms). It has
  not been cut: cutting it is a task change to be judged on a screen, and
  the SG task inherits it until one does (`v05-s1.md`, `sg-schedule.md`).
- **Damping 5 is kept though its screen's keep rule failed** on LH's U
  (0.25, a fold at touch-down, not in stance). v05 is the owner's model;
  a step back between 3 and 5 would be a model change (O1), `leo-v05.1`,
  judged on the touch-down split (`v05-s1.md`).
- **The generator lays a paw flat only where its heel is held**, so a
  heels-up slow stride stands its paw on the toe bulbs in the reference
  (the pin is not tracked, so no reward reads it). If the slow SG policy
  stands on its toe tips, the lever is a generator option, a heel held at
  a height with the paw flat (`sg-reference.md`).
