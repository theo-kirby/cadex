# orun17 report: leo v05, a cat-like gallop across speeds

Verified against source: 2026-10-23. R1, kept current as criteria close;
not yet the closing report. Every number cites the probe note that holds
it; every judged run is the engine's evaluation on `gallop_spec`'s 10
frozen seeds (`orun16/sg_judge.py` at a held command), read by
`sg_tables.py` unless a note says otherwise.

## Criteria

| criterion | state | best evidence so far |
|---|---|---|
| B1 | met in substance (scribe's claim: working) | sg-s9 judged at 50 and 80 (`sg-s9-50-80.md`); the slow reference read sample by sample and the generator option argued not needed (`b1-trim.md`); `gallop_sg` trimmed 24 → 18 terms, sgt-1 launched cold (`b1-trim.md`) |
| SG | open, 3 of 5 clauses on sgt-4-120 | table below |
| RL | open, 2 of 4 clauses on sgt-4-120 | table below |
| P1 | open; no orun17 policy passes `hock_down` on 8 seeds | sgt-4-120 at 2400: heel 0.31 / 0.38, U (O2, past 5°) 0.18 / 0.35, at 10° 0.13 / 0.24 (`sgt-4-120.md`); single-speed v05-s1-50 (orun16): 0.40 / 0.35, U 0.25 / 0.01 |
| P2 | open; overreach fails on every SG screen | sgt-4-120 hind overreach LH / RH −166 / −434, +74 / −407, +242 / −355 mm at 700 / 1550 / 2400; `no_tap` 0/10 at 700 (LF 1.89 a stride) |
| SP | open (no P1 / P2 policy); preview below | |
| Q1 | open (no P1 / P2 policy); preview below | |
| Q2 | open; loops 2.5–2.9 mm (front rods), the rest of O9 passes; 1 ms step deferred by the owner | `sgt-4-120.md`, orun16 `q2-step-proposal.md` |
| S1, S2 | open; fastest orun17 judged 2.90 m/s (sg-s9-80 at 2400, overrunning) | `sg-s9-50-80.md` |
| F1 | open | |
| R1 | this file | |

## SG and RL on the best SG policy so far: sgt-4-120

Policy `915a9863` (sgt-4, iteration 120), cold on leo revision `b09a23b5`
(the trimmed 18 terms, `heel_sched` w 12 half-width 40, the duty 0.35 /
0.3 slow stance), seed 1, 4096 envs. Every seed to the horizon at every
command; 0/10 `gallop_spec` (top_speed by design at a held command,
`hock_down`, overreach). Source: `sgt-4-120.md`, reprinted by
`sg_tables.py` on 2026-10-23.

**SG: speed against heel share, per leg**

| command mm/s | 700 | 1550 | 2400 | clause |
|---|---|---|---|---|
| top 2 s m/s, median (min / max) | 0.88 (0.87 / 0.93) | 1.70 (1.68 / 1.72) | 2.66 (2.64 / 2.67) | |
| heel share of stance LH | **0.00** | 0.18 | 0.31 | slow ≤ 0.1 pass; rises pass; fast ≥ 0.4 fail |
| heel share of stance RH | **0.00** | 0.00 | 0.38 | slow ≤ 0.1 pass; rises fail (flat 700 → 1550); fast ≥ 0.4 fail |
| U LH / RH past 5° (O2); at 10° | 0.03 / 0.06; 0.01 / 0.00 | 0.07 / 0.07; 0.05 / 0.00 | 0.18 / **0.35**; 0.13 / 0.24 | fast U < 0.2 fail (RH) |
| heel stance height LH / RH mm | 19 / 28 | 5 / 10 | 5 / 4 | |
| floor pitch at lift LH / RH °; lifts toes-up of floor | −2.5 / +0.3; 0.00 / 0.00 | −0.4 / −3.3; 0.00 / 0.00 | −4.0 / −11.3; 0.00 / 0.00 | |

The mirrored policy (`afbc4ad2`) swaps RH's flat 1550 heel and its fast
fold to LH within 0.02: both are the policy's, not the hardware's
(`sgt-4-120-o6-mirror.md`).

**RL: speed against lag, fore and hind**

| command mm/s | 700 | 1550 | 2400 | clause |
|---|---|---|---|---|
| rotary seeds, ordered strides | 4/10, 6 undecided | 10/10 | 10/10 | ≥ 8/10 everywhere: fail (700) |
| fore lag, share of stride; ms median (lowest seed) | 0.200; 100 (100) | 0.286; 120 (110) | 0.250; 80 (80) | falls: fail |
| hind lag, share of stride; ms median (lowest seed) | 0.361; 180 (180) | 0.350; 140 (140) | 0.294; 100 (100) | falls: **pass** |
| strides under 40 ms fore / hind | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | ≥ 40 ms: **pass** |

The slow end is undecided, not transverse: LF strikes 1.89 times a stride
(1.72–2.06 by seed), its extra strike inside 40 ms of RF on 0.24 of fore
touchdowns (`fore_pair.py`, `sgt-4-120.md`). The fore share's dip at 700
is that tie. The mirror reverses the doubled paw but not the timing (lag
100 vs 40 ms, rotary 4/10 vs 1/10), so the slow fore clause reads
differently left- and right-led (`sgt-4-120-o6-mirror.md`).

**Where sgt-4-120 stands among the cold SG screens** (median top speed,
heel share LH / RH, rotary seeds, at 700 / 1550 / 2400):

| policy | revision; terms | m/s | heel LH | heel RH | rotary | note |
|---|---|---|---|---|---|---|
| sg-s9-80 (orun16) | `59bc5407`; 24 | 1.07 / 2.07 / 2.90 | 0.19 / 0.26 / 0.24 | 0.02 / 0.21 / 0.12 | 10 / 10 / 10 | overruns the slow command |
| sgt-1-120 | `59e37a18`; 18 (trim) | 0.95 / 1.78 / 2.73 | 0.12 / 0.35 / 0.26 | 0.19 / 0.26 / 0.34 | 7 / 10 / 10 | trim not kept as is; `paw_fold` back first |
| sgt-2-120 | `bd1b70be`; 19 (+`paw_fold`) | 0.88 / 1.78 / 2.73 | 0.00 / 0.37 / 0.35 | 0.00 / 0.01 / 0.25 | 9 / 10 / 10 | `paw_fold` not kept (LH U 0.28) |
| sgt-3b-120 | `62025a13`; 18 (`heel_sched` 12:40) | 0.93 / 1.80 / 2.71 | 0.03 / 0.09 / 0.30 | 0.00 / 0.31 / 0.24 | 1 / 10 / 10 | 12:40 not kept (RH fast heel, U) |
| **sgt-4-120** | `b09a23b5`; 18 (+ slow duty) | **0.88 / 1.70 / 2.66** | **0.00 / 0.18 / 0.31** | **0.00 / 0.00 / 0.38** | 4 / 10 / 10 | duty option not kept on its fore rule (LF doubles); best shape |
| sgt-5 | `89b5bb40`; 19 (+`fore_lag` w 10) | training, launched 04:24 | | | | keep rule in `fore-lag-sgt4.md` |

Sources: `sg-s9-50-80.md`, `sgt-1-120.md`, `sgt-2-120.md`,
`sgt-3b-120.md`, `sgt-4-120.md`, `sgt-5-bundle.md`.

## The clip and reward design

- **The reference** is orun16's speed-scheduled `gallop_sg` (ADR-773):
  five strides from 0.7 to 2.4 m/s, heel hold 0 → 0.8, pair lag about
  0.35 → 0.15. The slow clip lands each hind paw on its toe bulbs, heel
  35–48 mm up, pin at its flat stop; the policies do not copy it and stand
  the slow paw on the pad, heel up (`b1-trim.md`), so no heel-height
  generator option was built.
- **One reference option, applied:** the duty 0.35 / 0.3 slow stance with
  a 30 mm swing (`duty-schedule.json`, leo `da06185`, from sgt-4), for the
  slow fores, which the clip lands 180 ms apart and the policy struck
  twice (`slow-duty-strides.json`, `fore-pair.md`). It single-struck RF;
  LF still doubles.
- **Rewards** (sgt-4, 18 terms): `alive` 4, `track_speed` 20 (linear
  tent), `track_pose` 1.5, `track_lift` 1.5, `track_contact` 10,
  `near_peak` −0.5, `height_over_ground` −1, `posture` −1, `straight` −1,
  `tail` −2, `fore_tap` −8, `heel_pitch` 10, `paw_flat` 10, `fore_sync` 2,
  `hind_lag` 10, `heel_sched` 12 (contact-gated, half-width 40),
  `overrun` −10, `hind_scuff` −8. sgt-5 adds `fore_lag` 10.

## Terms kept and cut

| term | verdict | evidence |
|---|---|---|
| `outside_hind`, `fore_reach`, `hind_overreach`, `plantigrade`, `hind_flat` | cut (sgt-1), stay cut | never judged on leo, or no effect alone (`b1-trim.md`); none bore on sgt-1-120's failed clauses (`sgt-1-120.md`) |
| `paw_fold` (w −10) | cut, tried back, cut again | lowered LH's fold at 50, back by 120 (LH U 0.28 at 2400 against ≤ 0.24) (`sgt-2-120.md`) |
| `heel_sched` 12:40 (was 6) | not kept on its rule, carried by sgt-4/5 | LH fast heel up, RH down (`sgt-3b-120.md`); sgt-4 and sgt-5 still carry it, so their heel numbers read against sgt-3b's |
| `fore_lag` (w 10) | on trial in sgt-5 | priced at a 0.137-a-step single-vs-double gap at 700 (`fore-lag-sgt4.md`) |
| the rest | kept | regularisers, the clip's trackers, and terms with a judged effect on leo (`b1-trim.md`) |

## Model changes (O1)

None. No `leo-v05.N` tag exists; every orun17 build changed the script's
task or reference only and kept leo-v05's model (sgt-5's XML equals
sgt-4's, `sgt-4-120-o6-mirror.md`), so the clearance baseline is
untouched.

## What limits speed, drive by drive (O6)

Every leo policy since hk12 has a peak ratio of 1.0: the engine clamps the
effort at the drive's peak, so the margin reads 0.00 whenever a drive
saturates (`sgt-4-120-o6-mirror.md`). On sgt-4-120, the share of frames
at the clamp (seed median) and the worst RMS over rated:

| drive (clamp) | 700 | 1550 | 2400 |
|---|---|---|---|
| `j_hock_l` / `j_hock_r` (AK80-9, 22 N·m) | 0.21 / 0.32 | 0.34 / 0.31 | 0.33 / 0.20 |
| `j_wrist_l` / `j_wrist_r` (9 N·m) | 0.16 / 0.19 | 0.13 / 0.20 | 0.14 / 0.18 |
| `j_elbow_r` (53 N·m) | 0.16 | 0.12 | < 0.05 |
| `j_tail2` (1.9 N·m) | 0.69 | 0.80 | 0.62 |
| worst RMS / rated (drive) | 1.44 (`j_hock_r`) | 1.48 (`j_hock_l`) | 1.47 (`j_hock_l`) |

The hocks are the binding leg drive: at the clamp a fifth to a third of
the time and 1.44–1.48 × rated RMS, up from 0.15–0.24 on the single-speed
policies, because the heel schedule asks them to hold the metatarsus flat
under load. The spine drive, the worst on several earlier screens (up to
1.96 × rated, sgt-2-120 at 2400), sits under 0.05 at the clamp here.

## Previews on the SG policy (not criteria: no P1 / P2 policy yet)

- **Spine (SP):** sgt-4-120's two-joint spine ranges 26.5 / 25.1 / 22.9°
  a stride (both joints) at 700 / 1550 / 2400, at a stop 0.00 of the time
  at every command, cable within 0.13–0.26°; orun7's single spine sat at
  its ±25° clamp ~60% of a bound. Its phase against the hind footfalls is
  not yet measured on an orun17 policy.
- **Symmetry (Q1)** at 2400: heel 0.31 / 0.38 (LH 18% under RH), stride
  884 / 881 mm, touchdown 3.00 / 3.00 Hz: within 20% on all three.
- **Flight:** 0.62 of strides at 700 (0.060 s), 1.00 at 1550 and 2400
  (0.040 s).

## Hardware the numbers argue for, not made

- **The hock drive** saturates on every judged policy and more under the
  heel schedule; a stronger hock (or a longer hock lever) is the change a
  P1 heel at speed would be measured against. Not argued hard enough yet:
  no screen has shown the heel held back by the clamp rather than by the
  policy (the mirror puts RH's misses on the policy).
- **The front push-rod loops** (Q2): the 1 ms step, deferred by the owner.
