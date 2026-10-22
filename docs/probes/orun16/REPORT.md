# orun16 report: leo v05, a cat-like gallop across speeds

Verified against source: 2026-10-22. R1, kept current as criteria close;
not yet the closing report. Each line cites the probe note that holds its
numbers.

## Criteria so far

| criterion | state | evidence |
|---|---|---|
| B1 | met | `b1-ready.md`, `v05-s1.md`: v05-s1-50 (`41693803`, rev `15d9feb4`), pins p95 741 / 380 °/s at 2.39 m/s, heels 0.40 / 0.35, U 0.25 / 0.01 |
| SG, RL | open; sg-s1 (cold, `gallop_sg` on rev `721d10da`) stopped at 50 by its rule: heel share rises with the command (LH 0.31 → 0.91, RH 0.19 → 0.58; 1000 → 2400) and strides are rotary with lag ≥ 40 ms at 1700 / 2400, but in place (0.26 m/s at 2400); sg-s2 (rev `32dd914b`, `track_speed` a linear tent up to the command) training | `sg-schedule.md`, `sg-reference.md`, `sg-task.md`, `sg-s1-25.md`, `sg-s1-50.md` |
| P1 | open; v05-s1x (warm) stopped at +25 under O8, a dead end: RH heel 0.35 → 0.15, LH U 0.25 → 0.28, 2.27 m/s | `v05-s1.md`, `sg-task.md` |
| P2, SP, Q1, Q2, S1, S2, F1 | open | – |

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
