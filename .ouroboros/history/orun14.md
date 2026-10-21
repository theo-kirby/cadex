---
run: orun14
machine: sb1x
started: 2026-10-21T05:24:19
ended: 2026-10-21T17:34:38+00:00
hours: 7.7
state: killed
iterations: 14
commits: 26
criteria_ticked: 0
criteria_closed: 0
criteria_total: 12
merged: 95a3c2a18b8381ed301e922e65accfd74c03f75e
branch: ouroboros/orun14
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun14

14 iterations in 7.7h on `sb1x`, killed (-). Branch `ouroboros/orun14`, merged as `95a3c2a1`.

## The numbers

| | |
|---|---|
| iterations | 14 (changed 14, recorded 0) |
| commits | 26 — 38 files changed, 3730 insertions(+), 28 deletions(-) |
| criteria | **this run ticked 0**; 0 of 12 checked at the tip |
| reverts | 0 |
| verdicts | continue 14 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5, scribe claude:claude-opus-5-5 |
| usage | claude seven_day 67% -> 70% (+3 this run); claude five_hour 28% -> 11% (-17 this run) |

## What landed

- orun14 P1: tr-sole judged at 25 and 50 (2.40 m/s, U 0.34/0.63, rotary 0/10): the trailing clip took some of the fold off, not most; fold_term.py; fd-sole (paw_fold w -10) stopped unjudged at the owner's stop
- orun14 P1: hw-sole judged at 50 (0/10, 1.46 m/s, heels 0.20/0.24, U 0.19/0.58, rotary 10/10): not kept; tr-sole (ADR-785 trailing paw, swing pin <= 8.4 deg) built 32890126 and launched
- orun14 P1 (ADR-785): trail_feet lays a flat foot flat only while it is down; leo v03's sole clip swing pin 57.7/56.0 -> 8.4/7.4 deg (clip_trail.py)
- orun14 O1: leo-v03.1 write-up, owner note says the change was not built
- orun14 P1: hw-sole judged at 25 (0.49 m/s, heels 0.02/0.01 on flat paws, U 0.05/0.04): keep rule fails on heel, runs to 50; leo-v03.1 (pin toes-up stop 60 -> 30) written up and refused at build: the sole clip folds the pin to 56-58 deg in early swing (pin_cap.py)
- orun14 P1: hw-sole's first ten iterations timed (985 s, as ps-sole)
- orun14 P1: ps-sole judged at 50 (2.60 m/s, heels 0.37/0.19 on paws folded toes-up, U 0.86/0.78, RH pin on its 60 deg stop): not kept; LH-first strides are transverse because the fores keep the clip's LF-first while the hinds reverse (lead_order.py); hw-sole (heel_pitch w20) launched
- orun14 P1: s1-sole judged at 50 (2.80 m/s, heels 0.17/0.08 on toes-up paws, U 0.51/0.81): not kept; ps-sole judged at 25 (0.96 m/s, heels 0.03/0.17, U 0.18/0.38): fails at 25, runs to 50; 74 s/iteration; paw_flat offset on the sole clip checked
- orun14 P1: s1-sole judged at 25 (1.02 m/s, heels 0.06/0.06, LH U 0.41, pin +34 toes-up): keep rule fails; runs to 50; ps-sole (sole clip under p1-flat's task) queued and building; 69.3 s/iteration
- orun14 Q2/O1: the front wrist at peak is the carpus stop yielding up to 26 deg in stance (wrist_peak.py); a stiff carpus stop written up before its build
- orun14 P1: s1-sole built d5192106 and launched; its bundled clip has heel, pad and toe on the floor, _META +5.8
- orun14 P1: p1-flat judged at 50 (1.46 m/s, heels 0.31/0.52, flight every stride, rotary 10/10; U 0.22/0.38 fails its keep rule, not kept); s1-sole (ADR-784 sole clip on h1-meta's task) building
- ADR-784: flat_feet="sole" lays a held-heel foot at its sole's level pitch
- orun14 P1: p1-flat judged at 25 (0.41 m/s, heels 0.00/0.01, RH U 0.23: keep rule fails), runs on to 50 while the next screen's generator change is built; the clip's hind stance holds heel and toe with the pad 4-13 mm in the floor (clip_pad.py); rod gap > 2 mm only with the wrist at peak (rod_gap.py); 4c9de98d's clearance baseline pair by pair
- orun14 P1: h1-meta judged at 25 (0.73 m/s, heels 0.07/0.04, floor pitch +1.3/+2.3 vs g1-free-25's +0.7/+1.9, U share 0.13/0.15 vs 0.02/0.03) and stopped under O8; p1-flat's build 4c9de98d checked (14 static / 12 sweep pairs, baseline) and launched
- orun14 P1: g1x-free judged at 75 (2.85 m/s, heels 0.36/0.18 but the paw more toes-up: U 0.84/0.80, floor pitch +42.0/+29.0) and stopped early under O8; h1-meta launched, p1-flat building
- orun14 rh-mirror.md: name footfall_metrics
- orun14 O5: mirror tests on g1-free-50 (rh-mirror.md): the model mirrors (27 diffs, all cosmetic panels); the mirrored policy swaps RH's 5.5 Hz double contact, short stride and low heel share to LH, so the asymmetry is the policy's; no_tap/every_stride read on the LH stride clock
- orun14 P1: paw_floor.py floor pitch fixed (forward = normal to the pin axis; g1-free-50 reads +32.8/+25.7 toes-up of the floor, not +146/+78); paw_flat.py (floor pitch from channels: pin toes-up - _META + 1.9, within 2 deg of the pad-to-toe line); p1-flat (pin encoders to the actor, paw_flat w10) queued behind h1-meta
- orun14 P1: heel_meta.py (heel_pitch's metatarsus on v03: flat at +6, not +4.5); g1-free judged at 50 (2.24 m/s, heels 0.30/0.16 but paws toes-up on the pin, overreach 10/10); g1x-free runs by its rule; h1-meta (cubic heel_pitch at +6) built e62efb91 and queued
- orun14: paw_floor.py (free paw pin: floor pitch, pin angle, toe-off roll, pin rate); clip read; g1-free judged at 25 (0.53 m/s, heels 0.02/0.02 on flat paws), g1x-free queued
- orun14 B1: leo v03 bundle bc287c9c (g4-peak's 18 terms, roll_brake off on the free paw), stand and clip checked, g1-free launched (69 s/it)

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

(unwritten)

## What this taught

- **A free paw pin folds toes-up at speed.** Every slow policy on v03 stood flat, and every fast one (2.2–2.9 m/s) folded the paw 20–45° toes-up of the floor in stance (U 0.34–0.86).
- **The fold is not taught by the gait reference.** ADR-785's trailing paw cut the clip's swing pin from 57° to 8°, but tr-sole-50 still folded (U 0.34/0.63). Once the paw passes 15°, `paw_flat` pays nothing and gives no pull back toward flat, so folding is free speed. `paw_fold`, a contact-gated penalty on floor pitch, was checked on the logged runs but never trained.
- **Owner call at the stop:** give the pin a soft toes-down return spring (leo v04) rather than fight the fold with reward terms.
