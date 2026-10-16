---
run: orun7
machine: sb1x
started: 2026-10-15T16:42:44
ended: 2026-10-16T17:05:40+00:00
hours: 20.4
state: killed
iterations: 38
commits: 28
criteria_ticked: 2
criteria_closed: 2
criteria_total: 10
merged: no
branch: ouroboros/orun7
memory: governor
actor: claude:claude-opus-5-5
---

# Run orun7

38 iterations in 20.4h on `sb1x`, killed (-). Branch `ouroboros/orun7`, not merged.

## The numbers

| | |
|---|---|
| iterations | 38 (changed 24, recorded 25) |
| commits | 28 — 32 files changed, 5895 insertions(+), 180 deletions(-) |
| criteria | **this run ticked 2**; 2 of 10 checked at the tip |
| reverts | 0 |
| verdicts | answer 1, continue 36, stuck 1 |
| loop detector | no_product ×2 (longest streak 9) |
| roles | actor claude:claude-opus-5-5, critic claude:claude-opus-5-5 |
| usage | claude seven_day 0% -> 13% (+13 this run); claude five_hour 4% -> 52% (+48 this run) |

## What landed

- dynamics: a joint's stop is as stiff as its joint_dynamics says (ADR-724)
- evaluation: appendage predicates -- ground contact, pitch against the parent, yaw against the turn command (ADR-722)
- dynamics: a commanded yaw rate, scripted goal openings, and command-tracking predicates (ADR-721)
- evaluation: footfall phase error is counted on the frame grid (ADR-719)
- terrain: predicates for distance made good, falls and steps and slopes crossed, and a held-out course per evaluation seed (ADR-718)
- terrain: a box course can be drawn from a seed, and the trainer re-draws it per episode (ADR-717)
- terrain: a course can be placed boxes, the form MJX trains on (ADR-716)
- terrain: a task can read the ground round a body, a privileged height scan (ADR-715)
- smoke: a free base on a declared course is supported by the terrain (ADR-714)
- terrain: a free base can stand on a declared course, a heightfield (ADR-714)

## Decisions the critic made

- #12 stuck: There was no diff and no unit finished; the actor only explained that a leftover watcher timed out while f1-s1 trains.
- #32 answer: No repo diff, but there was real project work: R1 training started on the A3 and A4 model, and the A3 after-check measured as failing with the cause shown (a soft joint stop). The actor asked whether to keep training running, and that needs a decision.

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

Operator notes, 2026-10-16. The owner stopped the run at 20.4 h.

**Outcome against the charter.**
- **A1 (face):** accepted by the owner.
- **F1 (gallop):** accepted by the owner. f1-g2 ran 4.15–4.17 m/s; f1-g3 met every F1 bar once ADR-719 counted footfalls on the frame grid. Its torque is about 2.5× rated.
- **A2, A3, A4 (tail, hind paw, lateral spine):** built on orun7-cat (final revision 0f036864). Their behaviour bars are measured only on the r1-t3 model.
- **R1 (turning):** r1-t3 (600 iterations, one paw revision stale) completes and stays upright, both 10/10. Tracking errors on all seeds:
  - yaw rate: 0.8–3.8°/s against a 20°/s limit;
  - speed: 44–147 mm/s against 300 mm/s.

  The tail never touched the ground. It fails two bars:
  - drives at 1.24–1.38× rated;
  - the 180° reversal was never measured, because the resampled commands never draw one. That is a task-design gap.

  The tail-yaw correlation reached 0.3 on 7 of 10 seeds. r1-t5 diverged to NaN at iteration 2 (sigma 41 at iteration 0), undiagnosed. The operator wrote the r1-t3 scores to `runs/r1-t3/train/eval-success-run.best.cxpolicy.json`.
- **W1 (terrain):** most of it is in Cadex (ADR-714 to ADR-718 and ADR-724): heightfield and box courses, a per-episode random course, a privileged height scan, and terrain predicates. Still missing: the dashboard drawing of the course and the proof on a second robot. MJX is unstable on heightfields, so boxes are the trained form.
- **W2 (rough ground) and C1 (closing report):** not started.

**What this taught.**
1. **Model changes mid-run are expensive.** The owner sent four design revisions: tail, cap and width, hind paw, lateral spine. Each landed only at an iteration boundary, and twice the actor, still on the old charter, started training on a model about to change. The operator stopped three runs (r1-t1, r1-t2, r1-t4 died by itself).
   - Settle the model before the skills, and have the owner look at stance-pose renders early.
   - To stop a training run, SIGTERM its `cadex_cli.loop` supervisor. It is recorded as an interruption.
2. **Render in the pose the part is used in.** A3's first rework was drawn in the build pose and changed only the visual mesh; the collision spheres were byte-identical. In stance the hind paw body sits about 58° from its build pose (`~/orun7-progress/hindlink.py`). The final design is a passive pin paw that self-levels; it flaps in fast swing, an open owner question.
3. **Training budgets were too long.** Curves flatten early: r1-t3 gained 85% by iteration 200 and 7% more by 475. The owner wants 200–300 iterations (screening 100–150), extended by warm start only while still climbing.
4. **A detached trainer launched inside the service unit dies with it** (r1-t4). Launch in its own `systemd-run --user --scope`.
5. **Transient API SSL failures** at iterations 35 and 36 fell back to the rules critic, and the loop recovered unaided.

**Next run.**
- R1 on the final model, at 200–300 iterations:
  - fix or diagnose r1-t5's divergence;
  - add a commanded reversal to the task;
  - add an effort term to bring the drives within rated.
- Then W1's dashboard drawing and second-robot proof.
- Then W2.
