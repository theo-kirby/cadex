---
run: orun9
machine: sb1x
started: 2026-10-17T09:09:16
ended: 2026-10-17T23:46:50+00:00
hours: 10.4
state: killed
iterations: 23
commits: 37
criteria_ticked: 0
criteria_closed: 0
criteria_total: 10
merged: bdaf363e98ceba737917da0bab702bc8765deca5
branch: ouroboros/orun9
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun9

23 iterations in 10.4h on `sb1x`, killed (-). Branch `ouroboros/orun9`, merged as `bdaf363e`.

## The numbers

| | |
|---|---|
| iterations | 23 (changed 23, recorded 0) |
| commits | 37 — 26 files changed, 3400 insertions(+), 53 deletions(-) |
| criteria | **this run ticked 0**; 0 of 10 checked at the tip |
| reverts | 0 |
| verdicts | continue 23 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5, scribe claude:claude-opus-5-5 |
| usage | claude seven_day 26% -> 33% (+7 this run); claude five_hour 0% -> 2% (+2 this run) |

## What landed

- orun9 stopped by the owner at iteration 24: digest, stand-from-rest evidence (scarlet-ember-6770), tail folded
- orun9 C2/B3: c1-c11b judged — waypoint 16 ends the ladder (points within_rated 7/10 at 0.970, 4 targets vs 6; turn2 9/10); nav-mode reference priced at 1/4/8/12 (go/stand 1.99/1.71/1.51/1.40x) and built at 4; b3-cat-cold (300 it) training
- orun9 C2 O8: j_wrist_r's points load is a lopsided nav-mode gait, not speed — per-leg RMS vs speed r=+0.00 (30 legs), 1.06 first 1 s vs 0.98 cruising, wrists 0.73/0.98 on points vs 0.84/0.82 on run; track_reference pays <=4/step vs waypoint 24
- orun9 B3/C2: b3-cat-ft judged at 25-150 — 0/10 everywhere, survival peaks 7/10 at 75 then collapses while trainer reward climbs; c1-c11b (waypoint 16) training
- orun9 C2: c1-c10 judged at 50/100 — points reaches 6 targets (c8: 0) but within_rated 6/10 on j_wrist_r (0.979); b3-cat-ft launched
- orun9 C2: c1-c10 launched, waypoint weight 8 -> 12 warm from c1-c8@100 (nav pays 2.15x standing at 2.5 m/s)
- orun9 B3: the cat maps onto the quadruped base's body (33 copied, 13 folded, 39 zero; 12 outputs copied, 12 zero); b3-base1@250 zero-shot tips 10/10
- orun9 B3: a fine-tune from b3-base1@250 (10/10 zero-shot) onto v0 at 3e-5 judges 0/10, 9/10, 9/10 at 25/50/75; RECIPE 3.5 names the body-block warm start
- orun9 B3: a base fine-tune at the default learning rate loses the base on its first actor update; at 3e-5 v0 walks 9/10 at 50 and 75
- orun9 B3: the probe notes the remap's normaliser defect is fixed (ADR-760)
- orun9 B2: a base remap keeps the base's normaliser weight on shared inputs, new inputs start fresh (ADR-760)
- orun9 B3: b3-base1 played zero-shot on held-out v0 walks 10/10 at base it 250 and 300 (0 fine-tune iterations vs 150 cold)
- orun9 B3: ADR-759 records the family step's measured GPU cost (8.7 s/it, six variants)
- orun9 B3: a family trains as one batch of its variants' own environments (ADR-759)
- orun9 C2: stand drift is the opening brake from the 1 m/s reference start; nav paid 1.5x standing; c1-c8 (waypoint 8, warm from c1-c7@50) launched
- orun9 B3: the randomised quadruped family (ADR-758), 7 built variants of one topology; cold v1/v7 walk 10/10 at 150; c1-c7 judged (cadence 0.8 buys no speed)
- orun9 C1: c1-c6 judged (cadence 0.6: run RMS 597 mm/s within rated, 3 m/s at 2.36-2.45); c1-c7 (0.8) launched
- orun9 C1: c1-c6 launched (trot cadence exponent 0.4 -> 0.6, warm from c1-sp2@50)
- orun9 B2: the canonical body lands (ADR-755); b1-b1 judged, biped walk 10/10 at it 100
- orun9 B1: biped stand-vs-move check (moving 2.26x standing); cold biped b1-b1 launched by the recipe
- orun9 O8: c1-sp2 judged at 50 and 100 — the sprint allowance bought no speed; run fails on speed within rated
- orun9 B1: a biped reward may name its reference's foot channels (ADR-756); a touch at exact tangency is not compared on export (ADR-757)
- orun9 O8: c1-sp2 sprint allowance (rated prices off above 2.5 m/s, peak kept) launched warm from c1-h2@100; B1 biped task written, blocked by two engine defects
- orun9 B1: cold quadruped by the recipe (b1-q1) passes its walk spec 10/10 from iteration 150; c1-h2x judged, no new clause
- orun9 O8: c1-h4 (hinge_w 4) judged at 50 and 100 on six specs, passes no clause c1-h2 did not; c1-h2x (c1-h2 extended 100 it) launched
- ... and 4 more

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

The owner stopped orun9 at iteration 24, 10.4 h into the 24 h after the restart for the page style. The clock restarted at 09:09 when the loop restarted for Ouroboros `380a635`; iteration 1 ran before that. The operator recorded iteration 24's unfinished stand measurement (`scarlet-ember-6770`), folded it, and stopped the armed c1-c12a launcher. b3-cat-cold was left training in its own scope, unjudged.

**Where each criterion ended.**
- **B1, the cold-start recipe: working.** Proven cold by `training/RECIPE.md`: the quadruped b1-q1 (`orun9-quad`) passed its walk 10/10 from iteration 150, and the biped b1-b1 (`orun9-biped`) 10/10 at 100. The biped first needed two engine fixes (ADR-756, ADR-757).
- **B2, the canonical body: working** (ADR-755; normaliser remap ADR-760). A remapped base warm start begins at +12.9 reward/step, where cold starts at about −6.
- **B3, the quadruped base: open, mixed.**
  - b3-base1 trained on the randomised family (`orun9-qfam`).
  - A fine-tune must use about a tenth of the default learning rate (3e-5), or the first actor update wipes the base. At that rate a family member walks 9/10 by iteration 50.
  - On the cat the base tips 10/10 zero-shot. Its fine-tune b3-cat-ft judged 0/10 at every checkpoint while the trainer's reward climbed.
  - The cold half on the cat (b3-cat-cold) was not judged.
- **B4: not started.**
- **C1: open.**
  - Run speed is still the binding failure: best is about 2.4 m/s against a 3 m/s command.
  - The sprint allowance (c1-sp2) and cadence above 0.6 bought no speed.
  - Standing passes 10/10 from rest on c1-c10@100. The as-spec failure is braking from the trot start, about 0.86 m/s. Whether the spec should start at rest is the owner's call (ADR-761 was decided but never written).
- **C2: open.**
  - turn2 passed 10/10 (c1-h2) and later held at 9/10.
  - points rose from 0 to 6 targets, then bound on j_wrist_r through a lopsided nav-mode gait.
  - The waypoint ladder (8/12/16) is exhausted. A nav-reference screen was built but never launched.
  - reverse stayed 0/10 throughout.
- **C3–C5, R1: not started.**

**What this taught.**
1. **O1's guaranteed B share worked.** B got about half the GPU and closed B1 and B2 in hours, where orun8 left them untouched. Keep a share rule in any charter that ranks criteria.
2. **Measure-first (O8) paid off.** One per-drive measurement named the binding drives: the hock at a stand, spine yaw in the sprint, and later the right wrist on points. It also ruled out two dead levers (sprint allowance, cadence). Weight screens at 100 iterations, judged at every checkpoint, kept each question to one or two runs.
3. **A spec can fail for its setup, not the policy.** The stand spec's trot start spent most of the drift budget on braking. Check what a failing spec's first second looks like before tuning for it.
4. **Trainer reward is not a pass.** On the cat fine-tune the reward rose while the deterministic policy collapsed. Judge checkpoints.
5. **The critic read nothing for the first half.** Calls took about 10 s with no file opened, matching report against diff. Later verdicts did cite engine metrics. A charter line that makes the critic open one cited `evaluation.json` per judged run is worth adding.
6. **Restarting the loop for a page-template change is cheap** early in a run: same run name, it continues.

**Next run.** The owner decides ADR-761 (stand from rest). Then:
- **C1 speed:** a gait or reference change, since weights and torque are ruled out.
- **C2 points:** the nav-reference screen c1-c12a, then a symmetry term.
- **B3:** judge b3-cat-cold, then retry the cat fine-tune from a base whose family covers the cat's proportions.
- **B4** on the biped.
