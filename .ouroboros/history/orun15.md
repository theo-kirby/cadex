---
run: orun15
machine: sb1x
started: 2026-10-21T13:40:18
ended: 2026-10-22T06:25:18+00:00
hours: 12.7
state: stopped
iterations: 18
commits: 29
criteria_ticked: 0
criteria_closed: 0
criteria_total: 12
merged: 1d0f289c12768d7142653f3c773cb90af415b19f
branch: ouroboros/orun15
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun15

18 iterations in 12.7h on `sb1x`, stopped (wall clock: 12h elapsed). Branch `ouroboros/orun15`, merged as `1d0f289c`.

## The numbers

| | |
|---|---|
| iterations | 18 (changed 18, recorded 0) |
| commits | 29 — 31 files changed, 3382 insertions(+), 16 deletions(-) |
| criteria | **this run ticked 0**; 0 of 12 checked at the tip |
| reverts | 0 |
| verdicts | continue 18 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5, scribe claude:claude-opus-5-5 |
| usage | claude seven_day 71% -> 75% (+4 this run); claude five_hour 17% -> 24% (+7 this run) |

## What landed

- orun15 O5/P1: hk12-sole-50 mirror (short first hind and yaw are the policy's); hk12-s1 judged at 25/50 (U 0.16/0.01, 2.40 m/s, straight 10/10, strides 991/991): leo-v04.3 kept; st4-sole stopped, hk12-s1x continues warm
- orun15 P1: hk12-sole judged at 25 and 50 (leo-v04.3: U 0.29/0.02 -> 0.07/0.02, but 1.91 m/s, RH heel 0.20, straight 0/10; keep rule fails on two clauses); f30-sole stopped, hk12-s1 (seed 1) replicates
- orun15 P1: leo-v04.3 built (7a69ad4a, verdicts equal v04.2's, clearance 14/8 -> 14/8, 0 new) and tagged; hk12-sole cold on it, timed at ~90 s/it
- orun15 P1: leo-v04.3 written up (PAW_K 8->12, stand checked at 12: pins on the flat stop, zeta 8.4); hk12-sole queued cold (the trainer refuses a warm start across a robot change)
- orun15 P1: ssw-sole judged at 25 and stopped (warm dead end: second hind LH U 0.29->0.39, touch-down +208->+181 mm, 2.23 m/s, no stilt); place_term.py scores a stilt gate
- orun15 P1: ss-sole judged at 25 and stopped (RH U 0.12 over its rule; LH stands on its toe tip, rotary 3/10); ssw-sole warm from hlk8-sole-50 launched; queue_run.py warm-starts across a task change
- orun15 P1: ss-sole (hind_place w-10 on hlk8-sole's task, leo-v04.2, 29298667) launched 22:40 and timed; clip stance-shift lever refused at every LH shift <120 mm; p2_lag.py counts rotary over ordered strides
- orun15 P1/P2: hlk8-sole-50 mirror (LH's fold follows the second hind to land, not the side); fl-sole judged at 25 and 50 (fores split 0.41, hinds re-tie, rotary 4/10, RH heel 0.08), not kept
- orun15 P2: fl-sole timed (launched 21:07:12, ten iterations in 15.6 min, ~4,350 s of a 4,600 s budget)
- orun15 P1/P2: hlk8-sole judged at 50 (U 0.29/0.02, heels 0.44/0.36, hinds 40 ms on 10/10, 2.17 m/s), not kept: LH still folds; no_tap is LF's skip in stance (no-tap.md, fore_tap.py); clip_read.py skips seeds with no stride rate
- orun15: hlk8-sole.md, k8-sole-25's hind lag cell (0.211, from k8-sole.md)
- orun15 P1/P2: hlk8-sole judged at 25 (bcf9dbef: hinds split 0.333, together 0.00, rotary 9/10, cold shuffle 0.69 m/s, U 0.01/0.19), not stopped, runs to 50
- orun15 P1/P2: k8-sole judged at 50 (U 0.11/0.20 from 0.29/0.29 at 2.58 m/s, pin p95 854/865 deg/s): leo-v04.2 kept, hinds still tied; hlk8-sole launched 20:01, ~90 s/it over its first ten; fore_lag scored per step (hl-sole-50 0.030 of the clip's 0.286, fore_sync pays the tie 1.65 > the clip's 1.43); fl-sole (fore_sync off, fore_lag w10) built 1732bef8 and queued behind hlk8-sole
- orun15 P1: k8-sole judged at 25 (cold shuffle at 1.00 m/s, RH U 0.10 -> 0.05 against sf-sole-25, pin p95 under 300 deg/s), not stopped, runs on to 50
- orun15 P1/P2: hl-sole judged at 50: hinds split at speed (RH 40 ms ahead on 10/10 seeds, rotary 9/10, one-frame share 0.02), RH's U 0.29 -> 0.01, but LH U 0.31 and 2.12 m/s miss the keep rule by 0.02 and 0.01; term kept, policy not; fore pair now tied; hlk8-sole (hind_lag on leo-v04.2) built 1412f4af and queued behind k8-sole
- orun15 P1/P2: hl-sole judged at 25 (hinds split, lag 0.405, rotary 9/10, 0.76 m/s cold), runs on to 50; leo-v04.2 (PAW_K 4->8) written up, built 568d38a9 with verdicts and clearance unchanged, tagged; k8-sole queued behind hl-sole
- orun15 P1/P2: sfw-sole (sf-sole warm) judged at +25, U 0.25/0.29, stopped as a dead end; hind_lag scored per step (lag_term.py: sf-sole-50 0.059 of the clip's 0.282, r -0.31/-0.69 with the tied share); hl-sole (sf-sole + hind_lag w10) cold on leo v04 dd9d802f launched 17:51, ~85 s/it
- orun15 O5: the RH mirror test on sf-sole-50 and sfp-sole-50 swaps sides (the policy's lead, not the model); trained_task_sha256 differs only by the bundle's model digest (springref 10 vs 30 deg); sfw-sole (sf-sole warm +50 at 3e-5, critic warmup 5) launched on restored leo v04 b32a6ace
- orun15 P1/P2: sfp-sole (leo v04.1, preload 30 deg) judged at 25 and 50 (2.35 m/s, U 0.23/0.28, 0/10), not kept; the clip asks 62.5 ms on each pair, and the policy lands the hinds together
- orun15 P1: sf-sole judged at 25 and 50 (2.37 m/s, U 0.29/0.29, heels 0.43/0.24, overreach 10/10, rotary 0/10), not kept; paw_fold makes the fold shallower (+25->+16 deg LH), not rarer; sfp-sole running on f3482223
- orun15 P1: sf-sole (sp-sole's task + contact-gated paw_fold, scored per step on sp-sole's traces) launched on b32a6ace, 70 s/it; leo-v04.1 (paw spring preload 10->30 deg, same rate) written up, built f3482223, clearance 14/8 no new pair, tagged; sfp-sole queued behind
- orun15 B1: sp-sole judged at 25 and 50 (2.18 m/s, heels 0.41/0.26, U 0.32/0.29, rotary 0/10), not kept; the spring halves RH's fold, not LH's
- orun15 B1: leo v04 bundle e560f053 (spring in the model, no new clearance pair), stand seats the pins on their flat stops, 69 s/it; sp-sole (tr-sole's task on v04, cold, 50 it) launched

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

(unwritten)

## What this taught

- **A stiffer return spring took the stance fold out where reward terms could not.** `paw_fold` made the fold shallower, not rarer; preload (v04.1) did little; spring rate did it: 4 → 8 → 12 N·mm/deg took U from 0.29/0.29 to 0.16/0.01 at 2.40 m/s (hk12-s1-50, a second seed), no speed lost. 12 is 3× the owner's "easy" spring: the owner decides whether it stays.
- **P1's remaining wall is the heel at toe-off**: heel share ~0.32, `hock_at_toeoff` 0 on LH. **P2's is the hind pair lag**: spreading the hinds 40 ms apart (hlk8-sole) brought LH's fold back, so the fold follows the second hind to land, not the side (hlk8 mirror).
- SG and RL were never reached: P1 gates them in the criteria order. 0 criteria ticked in 12 h, the third leo run in a row.
