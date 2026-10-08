---
node_id: 33108d6e-97da-5fc5-ba04-35283c474e07
slug: peaceful-orchard-2220
title: P1. The ball-plate, rebuilt as built
created_at: '2026-10-07T17:58:13+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun5: **P1. The ball-plate, rebuilt as built.** On a scratch copy (`orun5-ball-plate`) the ball is a free sphere rolling on the plate by contact, read by an S1 touch panel, no sliders or hidden bead; the centring task trains and passes its spec with distance from centre measured by M1 (no point goal); the circle task's spec bounds M1 laps so rocking fails it — trained to a pass if time allows, else the record shows the predicate failing rocking and passing circling; pushrods (L1) optional. The human owns the checkbox [rec: honest-bay-2056].

**Centring passes; the circle half is evidenced on the charter's *otherwise* branch** [rec: smooth-stream-7287] [rec: dusty-canyon-3027]. The run's must-have — a real ball on a real plate, read by a grounded sensor, trains centring to a pass — is evidenced, on noise-free evaluation readings. Every clause of the criterion now has evidence; the human owns the checkbox.

- **Rig** (revision `6e2cd359`, accepted): free steel sphere on the panel glass, read by a `position_tracker` with a resistive-panel datasheet (±80 × ±80 mm × ball height ±3 mm, 0.25 mm, 100 Hz, 0.5 mm noise). Spec: M1 `final_distance_mm ≤ 8`, `mean_distance_mm ≤ 15` about the plate centre, no point goal [rec: long-isle-5502] [rec: dusty-meadow-8719]. Since ADR-590 the actor reads the tracker's position, its differenced velocity `bd` and the two STS3215 encoders; the ball's world velocity stays privileged to critic and reward [rec: smooth-stream-7287].
- **Physics checked**: in C MuJoCo the ball rests 4.5 µm into the glass; MJX `framepos` with a reference body matches C MuJoCo to 1e-5 [rec: long-isle-5502].
- **Trained** (seed 12, 700 iterations, 256 envs, 326 s on the 5090): best **1.13** reward/step at iteration 535, up from the 0.62 plateau without a velocity, below 1.33 (true velocity in the actor) and the reference's 1.41; episodes reach the 300-step horizon from ~iteration 270. Best checkpoint declared `policy_centre` [rec: smooth-stream-7287].
- **Evaluated**: `cadex evaluate` passes the M1 spec **8/8 seeds** (policy `9cb0a64c6ca1`, evaluation `71e1646bdacd-9cb0a64c6ca1`): final 1.20–2.64 mm (bound 8), mean 3.11–6.41 mm (bound 15), all to the horizon through the start kick and mid-episode shove. Hero and seed-9001 filmstrip in `docs/probes/orun5/` [rec: smooth-stream-7287].
- **Circle predicate** (commit `401ba5bd`): `task_circle` rolls the ball anticlockwise round a 40 mm circle with spec `completed ≥ 1`, `mean_distance_mm` in [30, 50] and **`laps ≥ 2`** (ADR-587), no point goal. On the rig's own exported MJCF a scripted tracker (a PD law, not a policy) gives: **rocking** ±25 mm across the circle's top — turns −0.005, laps 0, mean 45.7 mm — **fails, by `went_round` only** (it passes the radius bound, the reference project's rocking failure); **circling** — turns +3.005, laps 3, mean 42.8 mm — **passes** all three. Plot `docs/probes/orun5/m1-rock-vs-circle.png`, probe `docs/probes/orun5/circle_predicate.py` [rec: dusty-canyon-3027].
- **Circle trained to 7/8, not a pass** (8 frozen seeds 9101–9108, noise-free; circle-1..9 fail `on_circle` on radius or `went_round`, circle-10/11 only on the start kick):
  - circle-1, -2, -4, -5, unsigned-1 circulate (3–11 laps) at 16–29 mm mean radius against the 30 mm floor; closest circle-5 (28.1–29.2 mm, 6/8 completed) [rec: dusty-canyon-3027].
  - **circle-6** (warm from circle-5, σ narrowed 0.24 → 0.08, commit `e6bfd17a`): 0/8, **laps 0 on 8/8** (turns −0.39..+0.80), 24.2–27.1 mm, all completed. circle-1..5's circulation came from exploration noise, not the deterministic mean; as a side result the laps bound fails a *trained* rocker 8/8, not only the scripted one [rec: flat-hawk-9763].
  - **circle-7** (warm from the passing centring policy by ADR-597's curriculum step, its first use; commit `7232131a`): 0/8, **laps 3–4 on 8/8**, 12.0–17.2 mm — the first circle policy whose mean goes round on every seed; radius is not reached under this reward [rec: bold-wind-5086].
  - **circle-9** (warm from circle-7 by ADR-597; off-radius `tanh` scale 10 → 25 mm so it no longer saturates, weight −0.8 → −1.6, alive 1.6 → 2.4; commit `bd433547`): 0/8, laps 3–4 on 8/8, **20.6–24.0 mm** — reweighting moved the radius ~7 mm, not to the bound. Closest by mean so far, with circulation held [rec: damp-orchard-1989].
  - **circle-10** (new task `task_circle_phase`, **cold** — the ADR-598 phase goal adds two inputs and ADR-161 refuses a warm start across it; period 3.5 s, reward follows the clock's point on the 40 mm circle; 1500 it, GPU 696 s; commit `3ffabb2b`): best **5/8**, final **6/8**. Every seed that reaches the horizon passes every predicate (2–3 laps, 33.4–35.6 mm); every failure is the start kick throwing the ball to the rim at 0.30–0.36 s [rec: tidy-badger-2182].
  - **circle-11** (`task_circle_catch`, warm from circle-10 by ADR-597, reward-only: near-point term gated off beyond 48 mm plus a radial catch term; 800 it, GPU 382 s; commit `0d3dd298`): best and final each **7/8** (2–3 laps, 33.8–35.7 mm). Seed 9101 now holds; **9102** still reaches the rim at 0.28–0.30 s — kicked out at ~250 mm/s, braked to ~140 mm/s by 62.5 mm, the ±10° command range cannot stop it in time. Kick and spec unchanged; no hero rendered [rec: glad-valley-4220].
  - **Circle iteration stops at 7/8**, per the critic. The circle task is **not a spec pass** (8/8 required); P1's circle half stands on the charter's *otherwise* branch — the predicate fails rocking and passes circling, and 7 of 8 frozen seeds pass every predicate [rec: glad-valley-4220].
  - Scratch project's accepted script declares `policy_circle` (circle-9), `policy_circle_phase`/`_final` (circle-10) and `policy_circle_catch`/`_final` (circle-11); policies in `assets/`, nothing committed [rec: damp-orchard-1989] [rec: tidy-badger-2182] [rec: glad-valley-4220].
- **Not done**: a noisy-readings evaluation of the centring policy (engine evaluations draw no tracker noise, training saw 70.7 mm/s velocity noise); scratch policies are uncommitted, in the project's `runs/` and `assets/` [rec: smooth-stream-7287] [rec: dusty-canyon-3027].

## Negative knowledge

- [scope: orun5-ball-plate circle task | confidence: medium | evidence: tidy-badger-2182, glad-valley-4220] A phase-led circling policy reaches for the circle along with the start kick instead of first catching the ball (circle-9 survived the same kicks 8/8); a state-gated catch term recovers one of two lost seeds but not 9102, which the ±10° command range cannot brake in time [rec: tidy-badger-2182] [rec: glad-valley-4220].
- [scope: xscript reward expressions | confidence: high | evidence: glad-valley-4220] A reward cannot name episode time — reward names are declared channels only, and only control formulas see `time` — so an "early-episode" term must be gated on state (or on a phase goal's channels) [rec: glad-valley-4220].

- [scope: orun5-ball-plate centring | confidence: high | evidence: long-isle-5502] A world-frame position reading learns fast only because the ball sits ~50 mm above the pivot, giving tilt a zero-lag handle; the panel-frame reading sees tilt only through the double integrator. Not a bug [rec: long-isle-5502].
- [scope: orun5-ball-plate centring | confidence: high | evidence: long-isle-5502, smooth-stream-7287] Without a grounded velocity the grounded actor plateaus at 0.62 reward/step; the missing input was the velocity, not noise, termination or z band (bisected) [rec: long-isle-5502] [rec: smooth-stream-7287].
- [scope: cadex smoke on rigs with a free payload | confidence: high | evidence: long-isle-5502, smooth-stream-7287] `cadex smoke` fails rigs with a free payload: `support` treats the ball as a free base needing a floor, and `components` counts its 7.5 µm contact penetration against a 1e-6 mm³ threshold. Still open [rec: long-isle-5502] [rec: smooth-stream-7287].
- [scope: evaluation rigs with a free payload | confidence: medium | evidence: dusty-meadow-8719] `evaluation_rig` reads a lone free ball as the base; two free bodies are refused [rec: dusty-meadow-8719].
- [scope: an agent editing a project's script with `cadex script --set` | confidence: high | evidence: dusty-canyon-3027] A failed set restores the accepted revision, silently discarding the edit; a stale policy declaration whose task digest changed is enough to fail it, which cost one circle training run (circle-3). Drop such a policy in the same set and pass `--replace` [rec: dusty-canyon-3027].
- [scope: orun5-ball-plate tracker z band | confidence: high | evidence: long-isle-5502] The ball hops off the glass by up to 3.4 mm under violent random tilts, reading out of range as a real panel would [rec: long-isle-5502].

- [scope: orun5-ball-plate circle task | confidence: high | evidence: flat-hawk-9763] Narrowing exploration σ on a circling policy removes the circling rather than fixing its radius: the circulation lived in the noise, not the mean [rec: flat-hawk-9763].
- [scope: orun5-ball-plate circle task | confidence: medium | evidence: bold-wind-5086, damp-orchard-1989] Off-radius reward reweighting in one curriculum step moves the circling mean's radius (12–17 → 20.6–24.0 mm) but does not reach the 30–50 mm bound [rec: bold-wind-5086] [rec: damp-orchard-1989].
- [scope: training launched from a shell | confidence: high | evidence: damp-orchard-1989] A trainer launched from a shell with `CUDA_VISIBLE_DEVICES=` (the suites' GPU-hiding habit) inherits it and runs on the CPU (circle-8 and -9); circle-8 was killed by its 570 s budget at iteration 779 with no checkpoint and left no policy [rec: damp-orchard-1989].

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-p1-ball-plate-rebuilt-as)
- dusty-meadow-8719 — M1 lets P1's spec bound distance without a point goal
- long-isle-5502 — rig rebuilt on a free ball and tracker; grounded centring plateaus at 0.62
- smooth-stream-7287 — with the tracker's grounded velocity, centring trains to 1.13 and passes its M1 spec 8/8 seeds
- dusty-canyon-3027 — circle evidence: laps ≥ 2 fails a rocking ball and passes a circling one on the rig's MJCF; five trained circle policies circulate but none holds the 30–50 mm radius
- flat-hawk-9763 — circle-6: narrowed σ turns circling into rocking, laps 0 on 8/8; circulation came from noise
- bold-wind-5086 — circle-7: warm from centring by ADR-597 goes round 3–4 laps on 8/8 at 12–17 mm; phase reward not expressible (defect 12)
- damp-orchard-1989 — circle-9: unsaturated doubled off-radius cost reaches 20.6–24.0 mm, 0/8; phase goal next
- tidy-badger-2182 — circle-10: ADR-598 phase-led reward, cold, passes 6/8 at 33–36 mm; failures are the start kick
- glad-valley-4220 — circle-11: warm state-gated catch passes 7/8; 9102 lost to the kick; circle iteration stops
