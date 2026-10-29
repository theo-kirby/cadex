# orun21: closing report

Verified against source: 2026-10-29 (`4eedc567` plus this file). Frozen run
evidence; read it, never cite it as current. Written from what is measured so
far, per the owner's live edit; it is kept current until the run stops. C1's
checkbox belongs to the owner.

orun21 worked on the engine, the trainer and the dashboard, not on one robot.
Its proving machines were the Go1 (Playground's joystick through Cadex), leon V
and the orun9 biped, all on copies in `~/cadex-projects/orun21-lab/`. Every
number below names the probe file or ADR it comes from; the raw outputs
(`progress.json`, `goto.json`, `times.txt`, judge files) are in the lab, as
those files say.

## 1. Where each criterion stands

| criterion | state | evidence |
|---|---|---|
| M0 where the time goes | measured | `ITERATION.md` §1–§7 |
| R1 research | written, with the difference table | `RESEARCH.md` §0–§5 |
| D1 run contract | met: three bare shell runs watched launch → end | `D1-WATCH.md`, ADR-837, ADR-838 |
| D2 the rest of the dashboard | six fixed, eight listed | `DASHBOARD.md`, ADR-851 |
| P1 one route | met on leon V and the biped; the tier ADR | ADR-841–847 |
| S1 faster iterations | three sinks cut, re-timed | `ITERATION.md` §8–§9, ADR-848–850 |
| G1 a visible target | dashboard playback and its captured film; `cadex evaluate`'s studio film does not draw the targets | `G1-TARGETS.md`, ADR-839 |
| G2 go-to-point on the Go1 | **met**, 10/10 held-out | `G2-GOTO.md`, ADR-840 |
| T1 one terrain system | met: one engine source, every kind, levels, MJX heightfields | ADR-852–856 |
| T2 go-to-point on terrain | met at flat, level 0 and the maze through level 2; level 4 fails | `T2-JUDGE.md`, `T2-SCAN.md`, `T2-MAZE.md`, ADR-857–861 |
| G3 the other two | leon V concept 4/10; leon V's cut and the biped **not run** | `G3-GOTO.md`, ADR-862, ADR-863 |
| K1 the recipe | rewritten; **unticked** until the biped follows it alone | `training/RECIPE.md`, ADR-864 |
| E1, J1, X1 (beyond) | not started | — |

## 2. M0 before and after: one iteration's time

**Where the time went at the start** (`ITERATION.md` §1, 23.6 actor-and-role
hours over orun20, l4r1 and l5r1): model turns 30%, builds 27%, training 24%,
judging 8%, tests 2%, memory 2%. The actor is the iteration (critic and
scribe 4–7% of a run). Waiting on usage cost nothing in those three runs.

**The three sinks S1 took** (`ITERATION.md` §7–§8), each on the same input:

| sink | before | after | ADR |
|---|---|---|---|
| 1. the restore pass on every engine open: `cadex export` of leon V, warm | 1,844.5 s (439 s restore + 1,405 s rebuild) | **1.2 s** copy of the accepted attempt (24.5 s for STEP+STL); the 102 files byte-identical | ADR-848 |
| 2. the trainer's fixed cost: a 100-iteration Go1 screen | 125.1 s | 102.0 s cold cache; **48.5 s** on a warm compile cache for the same command | ADR-849 |
| 3. the warm rebuild: `cadex export --rebuild` of unchanged leon V | 1,093.6 s (M0) / 1,055.7 s | **226.3 s** and 230.1 s | ADR-850 |

**The two representative iterations**, re-timed after S1 on leon V at the P1
trot revision, both at 49.2 M env steps and judged by `cadex evaluate` on the
export (`ITERATION.md` §9, `orun21-lab/s1-iter/times.txt`):

| iteration | before (pre-S1, logged) | after | binding now |
|---|---|---|---|
| concept: spec change → judged policy | ~627 s (judged with film) | **327 s** without film (~539 s with 212 s of film) | training (290 s) and the judge's film |
| CAD: script edit → judged policy | ~3,473 s (58 min) | **2,031 s** (34 min) | the accept's geometry build, 1,421 s (70%) |

Both after-runs passed 10/10 on the export. The CAD row's before and after
are not the same edit: the before accept (987 s) was a task-only edit and the
after accept (1,421 s) a `panel_gap` edit reaching every frame; a task-only
edit was not re-timed after S1 (`ITERATION.md` §9).

## 3. The tier decision (ADR-846)

Three tiers became **two written models, a derived cut, one task and one
judge**:
- the **concept** (a spec, `cadex_concept.py`, 0.1 s) and the **CAD** (the
  script) are written; they answer different questions at different costs;
- the **training model is no longer a tier**: `cadex_training_model.py cut`
  derives it from each accepted export in under 1 s and refuses unless it
  passes fidelity (ADR-841);
- the export's task bundle is the **one task**, re-laid by name onto the
  concept and the cut (`cadex_relay.py`, ADR-845);
- **one judge**: `cadex evaluate --weights` on the export.

The evidence (ADR-846, ADR-847, ADR-842's bench at 8192 envs): leon V's cut
trains at 303 k env steps/s against its export's 9.4 k (32×), the biped's
cut at 651 k against 181 k (3.6×). The cut gets the export's verdict: the
biped's cut-trained walk passes 10/10, leon V's cut-trained trot 10/10 (at
checkpoints 200 and 218; 299 fails). The concept screens design but does not
stand in for the confirming retrain: leon V's E2 concept, 7.1% light, trained
a trot 0/10 on the export (within_rated 1.21–1.45), the biped's concept 7/10.
At the CAD's mass, leon V's concept passed 10/10 (`ITERATION.md` §9), but the
builder changed too, so mass alone is not shown to be the cause. The owner's
view holds with one condition: training need not touch the CAD until the
confirming retrain, and that retrain runs on the cut.

## 4. Go-to-point and terrain, per robot

**Go1** (Playground's joystick through Cadex; the reference run1 is
0.470 / 0.958 / 1.431 m/s at 0.5 / 1.0 / 1.5, 0/30 falls, 324.7 s training
for 206.4 M steps, `GO1-BASELINE.md`).

| policy | ground | pass /10 | source |
|---|---|---|---|
| g2-goto-s20 (share 0.2, 206.4 M steps, 332.9 s) | flat | **10** (reach ≤ 0.255 m, hold ≤ 0.100 m, 0 falls, walk ratio min 0.873) | `G2-GOTO.md` |
| g2-goto (share 0.5) | flat | 3 (slow walk) | `G2-GOTO.md` |
| go1-scan/run3 (scan + feet block), the policy T2 closes on | flat / level 0 | 10 / 10 | `T2-SCAN.md` |
| | level 2 / level 4 | 9 / **1** | `T2-SCAN.md` |
| | maze, levels 0 / 1 / 2 | 10 / 10 / 10, no body in a wall | `T2-SCAN.md` |
| go1-scan/run2 it 300 | maze, levels 0 / 1 / 2 | 10 / 9 / 10 | `T2-MAZE.md` |

Route A, a velocity policy under a scripted go-to-point layer (ADR-839), was
chosen from R1; the layer costs about 3% of training time against Playground's
200 M-step budget (`G2-GOTO.md`). G2's thresholds were not widened for T2.
Height-scan actors moved level 2 (blind 1/10 → 6/10, ADR-859); neither more
exposure nor swing terms moved level 4 (`cool-valley-2757`, ADR-861).

**leon V.**

| model | task | pass /10 | source |
|---|---|---|---|
| cut, trot (49.2 M steps) | the export's trot, `cadex evaluate` | **10** | ADR-847 |
| concept at 33.31 kg, trot | the same | **10** | `ITERATION.md` §9 |
| concept at 33.31 kg, go-to-point share 0.2 (206.4 M, 601.9 s) | G2's task and judge | **4** at it 900 (all 80 points reached, holds kept, 0 falls; every miss a walk leg at 0.80–0.85) | `G3-GOTO.md` |
| the same, share 0 (663.9 s) | the same | 0 | `G3-GOTO.md`, ADR-863 |
| cut, go-to-point | — | not run | |
| terrain | — | not run | |

**The biped.** It went through P1's route (concept from its CAD, cut, relay,
`cadex evaluate`: cut 10/10, concept 7/10 on b1_walk, ADR-844/846). Its D1
watch ran on the export. Go-to-point (G3) and terrain have not been run; its
export carries no servo armature (`green-wren-7528`).

## 5. What is still slow, or still wrong

- **The CAD route's accept**: 1,421 s for a whole-robot edit on leon V, 70%
  of a CAD iteration; the part cache serves only parts the edit does not
  reach, and the fits re-run (`rapid-leaf-3340`, `ITERATION.md` §9).
- **The restore on every other engine-opening command** (`params`, `render`,
  `section`, `inventory`, `link`, `asset`, `train`): 432–447 s on leon V
  (`sunny-vale-9004`). ADR-848 removed it from `export` only.
- **The judge's film**: 212 s of a judged iteration, 40% on the concept route.
- **The compile cache hits only an identical program**: a learning-rate or
  seed change recompiles (`ITERATION.md` §8).
- **The engine suite**: 130 s against the documented 34 s, untraced (§7 rank 5).
- **Slow walking under go-to-point**: the Go1 0.470 → 0.458 m/s at share 0.2
  (`kind-ridge-3238`); leon V's walk legs 0.80–0.85; the effort-scale
  hypothesis (absolute N·m torque and energy terms on a robot 2.6× the Go1's
  mass) is untested.
- **No single cut solver setting is generic** (`sandy-acorn-7218`): the cut
  searches a ladder.
- **The go-to-point judge is a probe script** (`g2_judge.py`).
- **Dashboard**: eight listed cases in `DASHBOARD.md` rows 7–14, among them
  the CAD overlay matching only the current export (`spare-willow-9655`).

## 6. Recommended next run

In order, smallest first:
1. **K1's test, unfinished here**: take the biped from its CAD to G3 by
   `training/RECIPE.md` alone, fixing the recipe wherever it is wrong or silent;
   then leon V's go-to-point on its cut (G3's second half, X1).
2. **The heavy robot's slow walk**: one screen with mass-normalised effort
   terms on leon V's concept against the share-0.2 control, the hypothesis
   `G3-GOTO.md` leaves untested.
3. **The CAD accept**: profile the fits a whole-robot edit re-runs
   (`rapid-leaf-3340`) and take the restore off the remaining commands
   (`sunny-vale-9004`).
4. **The route from an empty project** (`modest-field-9752`) with a command
   that makes a concept's first task bundle before CAD (`tiny-pine-0692`).
5. Level 4 terrain (`cool-valley-2757`) only with a new lever: neither
   exposure nor swing terms moved it.
