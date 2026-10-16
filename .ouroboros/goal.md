# Goal: One ground, one cat, and base models for legged robots

Verified against source: 2026-10-16. Operator charter for orun8, following
orun7 (`.ouroboros/history/orun7.md`) and the owner's in-session terrain
work merged at `967e1aeb` (ADR-734 to ADR-741). The human owns this file;
unattended roles never edit it.

## Mission

orun7 and the session after it gave Cadex terrain:
- a box course is declared, drawn per episode and carried in every trace;
- the dashboard draws it;
- a warm start can step onto it;
- `collides_with` keeps MJX to the feet.

The cat ran a full 12 s on a mild course warm-started from its turning
policy (terrain-cat rough-c4). Three things are still wrong, and this run
fixes them, in the owner's priority order:

1. **The ground (G).** Today a course is boxes sitting on an infinite
   plane, painted the plane's material. It reads as objects on a floor, not
   as ground. A rollout can also run past the drawn floor onto nothing.
   The owner wants **one cohesive ground**: a single surface whose shape
   *is* the terrain (flat, then bumpy, then up onto a box, down, a slope,
   moguls, rock), flattening towards the horizon, and present wherever the
   robot goes.
2. **The cat (C).** One robust, unified policy on the newest cat model
   (`0f036864`). It must:
   - stand still and balance;
   - walk, run and gallop;
   - turn, reverse, and run to a point;
   - cross bumps, moguls and slopes;
   - jump up onto a box and down from it.
   The owner wants to watch it go from standing to walking to running across
   changing ground in one episode.
3. **Base models (B).** Stop training every legged robot from nothing.
   - **Base models:** a quadruped base and a biped base that a new
     quadruped or biped fine-tunes from (cat-like, dog-like, dinosaur,
     elephant).
   - **Recipe:** for when a cold start is unavoidable, a written,
     evidence-backed recipe that makes it quick whatever the morphology
     (inverted knees, short forelegs).
   Quadruped and biped only; hexapods and the rest come later.

If the loop achieves one thing, it is G. C stands on it, and B is the most
research-heavy, so it goes last.

## Reference project

- `~/cadex-projects/orun7-cat` is read-only. Its accepted revision
  `0f0368647796` is the newest cat:
  - one-width tail with a cap;
  - re-seated hind paws with a stiff stop (ADR-724);
  - lateral spine (A4).
- `orun8-cat` is a copy of it and is this run's to change.
- `~/cadex-projects/terrain-cat` (read-only) is the warm-start-onto-a-course
  proof. Its `script.py` shows a course, a privileged height scan, and
  height measured over the ground (`scan_4`).
- r1-t3 (`orun7-cat/runs/r1-t3`) is the best turning policy, on the older
  model `18d5657e`.
- r1-t5 was the first R1 attempt on `0f036864`. It diverged at iteration 2,
  before ADR-735's NaN guard existed.

## Owner decisions

- **O1. Ground first, then the cat, then base models.** When choosing
  between open criteria, take the highest-ranked group.
- **O2. The cat's policy may read the ground.** The actor gets a height
  scan, like a depth sensor on a real robot. Jumps and obstacles need it.
  That is a new actor input, so the unified policy cannot warm-start from
  orun7's blind policies.
- **O3. The newest model, `0f036864`.** No reverting to `18d5657e` to buy a
  warm start.
- **O4. Jumps are a ladder.** Boxes at 10, 20, 30, 40 and 50 cm. The
  criterion is clearing 20 cm up and down. The report says the highest
  height cleared. 50 cm is about the withers height and may be beyond the
  motors; say so with numbers rather than chase it.
- **O5. Physics stays on what MJX handles.** The heightfield goes
  non-finite under driven motion (`winter-bay-5176`), so trained physics
  uses primitives:
  - boxes for platforms;
  - turned boxes for slopes and rock;
  - large, mostly buried spheres or ellipsoids for smooth bumps and moguls.
  The **one cohesive surface** is the drawing of that physics (G1),
  sampled from the same geometry, so what is drawn is what the paws touch.
  A real mesh ground for physics is allowed only if a measurement shows MJX
  holds it stable at training speed.
- **O6. Short training budgets.**
  - Screens are 100–150 iterations; a full run is 200–300.
  - Extend a run by warm start only while its curve still climbs.
  - Spend the GPU on more experiments, not longer ones.
- **O7. Base models need a common body.** A policy's inputs and outputs
  are its robot's joints, in that robot's order. A base model needs a
  canonical per-family interface, for example per leg: hip abduction, hip,
  knee and ankle, plus body attitude and rates. Each robot is mapped onto
  it. A joint the robot lacks is empty. A joint the base lacks (a tail, a
  spine, a jaw) is a new output that starts at zero. The base trains on a
  randomised family (segment lengths, masses, knee directions), not on one
  robot.

## Done criteria

### H — the owner can watch

- [ ] **H1. A live progress page.** `~/orun8-progress/site/index.html` is
  served on the tailnet at `/orun8/` by the operator and never committed.
  Every iteration ends by updating it with:
  - each criterion's state;
  - the latest renders and rollout videos;
  - training curves.
  Every training run is registered on the dashboard from its start, with
  its policy and checkpoint rollouts (`run.json`, `retain_training_view`).

### G — one ground

- [ ] **G1. The ground is one surface.**
  - **The drawing:** on the dashboard and in the film, a course is drawn as
    a single continuous ground mesh whose height follows the course
    geometry, in one material. It has no separate box objects, no slab, and
    no seams at the course's edges, and it blends to flat towards the
    horizon.
  - **What it can express:** the course declares, freely mixed along its
    length:
    - flat stretches;
    - smooth bumps and moguls;
    - steps and boxes (with vertical faces that read as walls);
    - slopes up and down;
    - rock-like rough patches.
  - **It agrees with the physics:** at 1,000 random points across 10 held-out
    courses, the drawn height and the physics' ground height agree within
    5 mm.
  - **Evidence:** a browser test, a dashboard screenshot and a film frame,
    with `docs/DASHBOARD.md` and an ADR in the same commit.
- [ ] **G2. The ground never ends.**
  - **No drawn edge:** in any playback or film the robot is over drawn ground
    at every frame. The floor extends with the robot, so a 12 s episode at
    4 m/s in any direction never shows empty space. A test plays a
    synthetic trace that runs 50 m and checks it.
  - **No physics edge:** physics has no cliff at a course's extent either.
    The course runs out flat to the base plane, so running off a course is
    flat ground, not a fall.
- [ ] **G3. The new ground trains.**
  - MJX steps every new feature kind (moguls, rock, a 50 cm box) on the cat
    without going non-finite.
  - The stock-MuJoCo and MJX zero-shot tip rates of one frozen policy agree,
    as ADR-741 measured them, so MJX is not seeing a different ground.
  - The cost of an iteration on the course is measured and recorded against
    flat. If it is more than 3× flat, a fix or a reason is recorded.

### C — one cat (newest model `0f036864`, one policy file)

All C criteria are measured on the 10 frozen seeds with the engine's
evaluation (`cadex` predicates), not by the trainer's numbers. Drives stay
under peak torque always and within rated RMS except in a sprint (O3 of
orun7: a sprint may exceed rated but never peak).

- [ ] **C1. Stand, walk, run.**
  - **Standing:** commanded zero, the cat stands still and balances. It
    drifts less than 0.2 m in 10 s and survives the task's shoves.
  - **Speed tracking:** it follows a speed command re-sampled through the
    episode, from walking (≤0.5 m/s) to a run of at least 3 m/s, with RMS
    error ≤ 300 mm/s.
  - **Smooth changes:** it moves between stand, walk and run without
    falling.
- [ ] **C2. Turn, reverse, go to a point.**
  - **Turning:** it tracks yaw rates of ±60°/s.
  - **Reversal:** it makes a commanded 180° reversal, with heading error
    ≤ 20°.
  - **Targets:** it reaches a sequence of three target points 3–8 m apart,
    each within 0.3 m, in under 12 s.
  - **The tail:** it stays clear of the ground and is used in turns (orun7's
    tail predicates).
- [ ] **C3. Rough ground.** On held-out G1 courses at ≥ 1 m/s, the cat
  completes all 10 seeds over:
  - moguls up to 80 mm;
  - slopes of ±15°;
  - steps up and down of 100 mm;
  - a rock patch.
- [ ] **C4. Jumping.** On the O4 ladder, the cat jumps onto a 20 cm box,
  crosses it and jumps down, on at least 8 of 10 seeds. The report gives the
  highest box cleared, with the torque margin at take-off.
- [ ] **C5. One policy does it all.**
  - **One file:** C1–C4 pass on one `.cxpolicy`.
  - **The showcase:** an episode on one composed course, rendered as a film
    on the page, in this order:
    1. standing;
    2. walking;
    3. running;
    4. bumps;
    5. up a box;
    6. down;
    7. a slope;
    8. a turn and a reversal.

### B — base models and the cold-start recipe

- [ ] **B1. The cold-start recipe.** A recipe doc (in `training/` or
  `docs/`, decided by AGENTS.md's split) describes the steps that make a
  cold legged policy train quickly:
  - the reference gait;
  - starting episodes partway through the gait;
  - stand-first curricula;
  - terminations measured over the ground;
  - the critic warm-up;
  - budgets;
  - what to do when the knees are inverted or the legs are uneven.
  Every step cites the run that proved it. It is proven by a cold walk on
  one new quadruped and one biped (Cadex projects, not the cat), each
  reaching a walk spec on 10 seeds within 300 iterations, following the
  recipe with no step invented on the spot.
- [ ] **B2. A canonical body.** The task and the trainer have a canonical
  interface for the quadruped and biped families (O7):
  - each robot maps its joints onto it;
  - absent joints are empty;
  - extra joints are new outputs starting at zero.
  A warm start from a base model to any robot of the family is accepted,
  with `check_policy_fits` extended and an ADR.
- [ ] **B3. A quadruped base model.**
  - **Training:** it is trained on a randomised quadruped family. Each
    episode draws segment lengths, masses and knee direction across a
    stated range.
  - **The proof:** fine-tuning from it reaches the walk spec on two
    quadrupeds of different shape (the cat counts as one) in at most half
    the iterations a cold run with the B1 recipe needs.
  - **A negative result is recorded honestly.**
- [ ] **B4. A biped base model.** The same proof as B3, on one biped.
- [ ] **R1. Closing report.** `docs/probes/orun8/REPORT.md` covers:
  - G1–G3 with screenshots;
  - C1–C5 with each predicate's numbers, the highest box, and what limits
    the cat;
  - B1–B4 with the fine-tune and cold curves side by side;
  - what the next run should do.

## Later criteria

These are not this run's. They are work for when the frontier above is
exhausted, or for the next charter:
- **Obstacles.** Cones and gates: the cat weaves through a slalom or passes
  between gates without touching them.
- **Hexapod.** A hexapod base model and recipe.
- **More body shapes.** An elephant-scale or dinosaur-shaped body
  fine-tuned from a base.

## Horizon ladder

- **short-term:**
  1. Stand up H1 and copy `orun7-cat` to `orun8-cat`.
  2. G2's drawing, first: the floor extends with the robot, and a playback
     past the course stays on ground.
  3. G1's ground drawing: sample the course's top surface into one mesh
     that blends to flat, using the existing prototype material.
  4. G1's feature kinds in the engine:
     - buried spheres or ellipsoids for moguls;
     - turned boxes for rock;
     - tall boxes for jump platforms;
     - flat run-outs at the extent.
  5. G3's MJX probe of each new kind, frozen policy, stock against MJX.
- **medium-term:**
  1. C1 on `0f036864` with the actor's height scan:
     - the first cold run follows B1's draft recipe;
     - on flat, then a mild course;
     - the NaN guard is in place, so r1-t5's divergence should not recur.
  2. C2 by warm start (reward, goal and spec changes), then C3 onto G1's
     courses.
  3. C4's box ladder, then C5's composed course and film.
  4. B1's recipe written from evidence, and proven cold on a quadruped and
     a biped.
- **long-term:**
  1. B2's canonical interface, then B3's randomised quadruped base and its
     fine-tune proof, then B4.
  2. The later criteria, in their order, when the frontier above is empty.
  3. Keep every gate green, every doc true, `STATE.md` reconciled, and R1
     current.

## Constraints

**Standing:**
- Obey AGENTS.md, the licensing rules and the process boundaries.
  - The repository carries no GPL or AGPL code. A fetched model or image
    lives outside the repo and is never vendored.
  - Training stays offboard in `training/`, whose `cadex_train.py` imports
    only the standard library at module scope.
  - `CadexDynamics.py` stays unreachable from `cadexd` (ADR-102).
- Never commit any of the following:
  - secrets or private hostnames;
  - build outputs;
  - full transcripts;
  - policy binaries, checkpoints or rollout traces;
  - fetched third-party files.
- Do not hand-edit `STATE.md`, `PLAN.md` or state nodes.
- **Keep earlier projects read-only:** every project in `~/cadex-projects`
  except `orun8-*`, which are this run's.

**This run:**
- **One training run at a time on the 5090.** The machine lock is the
  arbiter. The CLI suite runs with the GPU hidden
  (`CUDA_VISIBLE_DEVICES=`).
- **Long training does not block an iteration.**
  - An iteration may start a run detached, through `cadex_cli.loop`
    (`register`, `retain_training_view`, `launch`) so the dashboard follows
    it, and end; a later iteration reads the result.
  - CPU work proceeds while the GPU trains.
  - Each training run longer than a smoke goes in a scope of its own
    (`systemd-run --user --scope -p MemoryMax=30G ...`).
- **A cat course is slow.** Measure the iteration time before committing a
  long run, and use `collides_with` (ADR-739).
- **The protocol and tool surface stay a contract** (AGENTS.md's rules).
- **The dashboard stays read-only.**
  - The ground drawing comes from what the HTTP API serves, with a browser
    test and `docs/DASHBOARD.md` in the same commit.
  - The actor may serve the dashboard on 127.0.0.1 for its own tests. It
    never runs `tailscale serve` and never binds a public address.
- Committed images are PNG, ≤300 KB each, under `docs/probes/orun8/`, on
  the dark floor.
- No role starts, stops or restarts the loop or signals its process.

## Owner notes

- **Gates run in the foreground.** Each finishes within the shell's
  10-minute limit. Write the record and the handoff before a long gate,
  then amend them.
- **Lean suites (ADR-725).** Add a test only for a contract or for a
  regression that actually happened. Verify behaviour by running the thing.
- **What orun7 and the terrain session learned:**
  - A warm start onto a course must warm the critic up first
    (`--critic-warmup`, ADR-740). Without it, episodes fell from 504 to 62
    steps in two iterations.
  - Before blaming the policy, play the frozen actor in the trainer's own
    MJX environment against stock MuJoCo. That is how ADR-741 found the
    pair cap culling bumps.
  - Measure height and collapse over the ground (`scan_4`), never over
    z = 0, on a course.
  - A box course that touches every geom costs 5× flat. `collides_with`
    the feet costs about 5× flat with 176 sphere–box pairs. Keep the box
    count down.
  - The trainer refuses a warm start across changes to the actor's
    observations, the actions or the reference.
- **Engine limits met on the cat** (raise one only with an ADR):
  - a reward expression holds at most 512 nodes;
  - a task holds at most 16 reward terms.
- **A reward exploit is a finding.** Record it. Prefer more reference
  (tracking) over another hand-written penalty.

## Question policy

- Resolve reversible choices autonomously, with the smallest measured step
  towards the highest-ranked open criterion (O1).
- **Is it real hardware?** A sensor no one sells is privileged; a drive no
  one sells is refused. The actor's height scan is allowed (O2).
- **Does it look right?** For G1, the ground should read as one landscape,
  not as objects on a floor. Record the reasoning, put screenshots on the
  page, and do not stall on taste.
- Where O1–O7 and a measurement disagree, record both and follow O1–O7.
  They are the owner's to change.
- Code and accepted artifacts outrank docs. Update the docs with the
  behaviour they describe.
- A pre-existing test failure is recorded and left alone, unless the unit's
  own change touches it.
- A harness or usage limit is not an attempt: keep the receipt and wait for
  capacity.
- Never invent a measurement, never weaken a test or a spec to pass, and
  never wait for a human.

## Exhaustion policy

`report_done`.
- Once H1, G1–G3, C1–C5, B1–B4 and R1 have evidence, write the closing
  report, reconcile and claim done. Two consecutive critic acceptances stop
  the run.
- Do not claim done while any criterion is unmet unless the run's
  wall-clock stop is near. Until then, work the highest-ranked open
  criterion, then the later criteria.
- If the stop arrives first, report how far each criterion got and what is
  left. Do not redefine success.

## Quality bar

- At every accepted commit that touches code, run:
  - `pixi run test-engine`;
  - `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`;
  - for `training/` changes, its tests from the training venv
    (`~/cadex-train-venv`) as well.
- Python changes under `src/Mod/cadex/` need `pixi run build-engine` before
  the CLI's engine-needing tests count.
- Every new ground feature, channel, command kind, predicate, interface and
  trainer change has an ADR, starting at ADR-742.
- Every iteration that changes code leaves a record.

## Reconcile

- Every five work iterations or three unreconciled records:
  - fold impacts;
  - advance the high-water mark;
  - regenerate the views;
  - export and check.
- The separate maintainer and planner roles stay off. The critic names the
  next unit.
- Unattended roles never edit this charter.
