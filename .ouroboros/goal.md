# Goal: A jaguar that sprints, turns and crosses rough ground

Verified against source: 2026-10-15. Operator charter for orun7, following
orun6 (`.ouroboros/history/orun6.md`) and the owner's in-session bound work
(cat-bound, ADR-712, ADR-713). The human owns this file; unattended roles
never edit it.

## Mission

orun6 and the session after it built the locomotion pipeline and proved it
on the panel cat:
- Brax PPO is the trainer (ADR-712).
- The procedural gait reference, tracking reward and gait-quality
  predicates are in place.
- The AK10-9 is in the catalog as a heavy tier (ADR-713).
- The heavy cat (30.1 kg, AK10-9 at the girdles and the proximal joints,
  wider joint travel) bounds with flight phases:
  - **bound-h2** reached 4.04 m/s as a half-bound;
  - **bound-h3** is a true bound at 3.74 m/s.
  Both are torque-limited: the drives run at about 2× rated and are at the
  clamp about half the time.

This run makes the cat look like a jaguar and teaches it three new skills.
It also gives Cadex the capability the last skill needs, terrain in the
world. The owner's five asks, in their order:
1. ears and a face that reads as a jaguar;
2. a thin, actuated tail;
3. a full gallop, faster than anything before;
4. turning and changing direction;
5. walking on uneven ground: bumps, step-ups, step-downs and small hills.
   Cadex cannot express that yet.

If the run achieves only one thing, it is this: **the cat, with ears and a
tail, gallops faster than 4.04 m/s on all 10 frozen seeds.**

Priority, in order: H1 (always on), A1, A2, F1, W1, R1, W2, C1.
- Build the model first (A1, A2). Any change to geometry or mass makes
  every policy retrain cold, so the look and the tail land before the
  skills are trained.
- W1 is CPU work. It proceeds while the GPU trains F1 and R1.

## Reference project

`~/cadex-projects/cat-bound` is the reference and is **read-only**.
- `script.py` has the parameters `heavy`, `widen`, `effort`, `sync` and
  `bound`, and the bound reference and spec.
- `runs/bound-s1`, `bound-h1`, `bound-h2` and `bound-h3` are the training
  story. Each has `train/eval-*.json`, `train.log` and `launch.sh`.
- bound-h3's `run.best.cxpolicy` is the **baseline** for speed and
  smoothness:
  - 3.75 m/s; duty 0.29; footfall phase error 0.024;
  - high-frequency share 0.163; effort 2.06× rated; clamp 50%.
- bound-h2's 4.04 m/s is the **speed record** F1 must beat.

The run works on `~/cadex-projects/orun7-cat`. The operator has already
copied it from cat-bound without `runs/`.

Scratch scorers from that work are in `~/orun7-progress/`:
- `track_eval.py` scores a policy on the frozen seeds;
- `phase.py` gives each paw's touchdown phase;
- `stops.py` gives the time each joint spends at its stops.
They are tools, not Cadex, and may be improved or replaced. A measurement
that matters becomes a Cadex predicate (as orun5 A3 and orun6 G2 did).

## Owner decisions

- **O1. Buildable.** Every drive, sensor and mechanism is a real,
  purchasable part, at a hobbyist's or lab's scale.
  - New ones join the library with datasheet-cited specs (peak and rated
    torque, speed, mass, dimensions), an ADR and tests, as ADR-713 did.
  - A simulated limit is the datasheet's, never stronger.
- **O2. Keep the cat's look and stature.** The owner likes this cat.
  - A1 refines the face; it does not redesign the head.
  - Panels follow the mechanism (the creature style). The ears and the tail
    are panelled to match: white panels over dark mechanism.
- **O3. Cadex stays general.**
  - Terrain, turning commands, height scans and their predicates are
    general locomotion features, right for any legged or wheeled robot.
  - Whatever is creature-specific goes in `CadexAgentStyle.creature.md` or
    in `training/`, not in the base guidance.
  - The engine never imports JAX or MJX (ADR-084).
- **O4. Sprinting may run hot.**
  - A gallop is a sprint. F1 may exceed rated RMS torque, as h2 and h3 do,
    but never the datasheet peak (the simulator enforces it).
  - Every F1 record reports each drive's RMS-to-rated ratio and clamp
    share, so the cost of the speed is visible.
  - R1 and W2 are sustained gaits and are held to rated torque.
- **O5. Policies see what the robot can sense.**
  - Proprioception and the IMU are actor observations.
  - A terrain height scan is privileged, critic only, unless a real sensor
    on the cat grounds it, and the record says which.

## Done criteria

Each criterion needs a causally parented governor record with measured
evidence. The human owns the checkboxes. Roles report results and do not
tick them.

- [ ] **H1. A live progress page the owner watches.**
  - `~/orun7-progress/site/index.html` is a self-contained static page. The
    operator already serves it on the tailnet at `/orun7/`. The page and its
    assets live only in that directory and are never committed.
  - **Every iteration ends by updating it**, accepted or not. It shows:
    - each criterion's state, with its latest evidence;
    - a timeline of iterations: what was tried, the result, and the next
      step;
    - the latest numbers;
    - visuals: before-and-after head renders, the tail, training curves,
      footfall plots, terrain renders, and stills or short looping videos
      of rollouts.
  - The page uses the dashboard's dark palette, carries a 60 s `refresh`
    meta, and shows the time it was written.
  - Failures and dead ends go on the page as plainly as successes.
- [ ] **A1. Ears and a jaguar face.**
  - Small, round ears on the skull. A jaguar's are short, rounded and set
    wide and low, not a house cat's pointed ones. Each is a white panel (or
    panels) mounted on the skull's structure, with its seam lines.
  - The face plate is remodelled so the head reads as a jaguar:
    - the eye sockets fixed first (the owner: "a little wonky");
    - then the brow, muzzle and cheek planes, as the reference needs.
    - The cameras keep a clear view: the record shows the camera's field of
      view is not occluded.
  - The project rebuilds, `cadex clearance` passes, and the joint sweep
    passes (neck and jaw included).
  - Before-and-after renders go on the page, in front, three-quarter and
    side views on the dark floor. The record names the jaguar references
    used (photos or anatomy, described, never committed), and the owner
    judges the look.
- [ ] **A2. A thin, actuated tail.**
  - The tail has 4 or 5 actuated joints, on real drives (O1). Small drives
    join the library if the catalog's smallest (the AK45-10, about 53 mm
    across) is too thick. Candidates include small QDDs and smart servos;
    the record compares them on torque, mass and diameter.
  - A jaguar's tail is long and fairly thick for a cat, tapering to the tip.
    Targets:
    - length about 0.6–0.7× the head-and-body length;
    - about 60 mm across at the root, tapering to about 30 mm;
    - mass as small as the drives allow, stated in the record.
    A deviation from a target is recorded with its reason.
  - The joint layout (pitch, yaw, or alternating) is chosen and recorded
    with its reason. Every joint is in the task's action set, so F1, R1 and
    W2 can use the tail.
  - It is panelled to match. It rebuilds, and clearance and the joint sweep
    pass over the full tail travel.
  - Renders go on the page.
- [ ] **F1. The fastest gallop yet.**
  - On the final model (A1 and A2 in it), a gallop policy passes on the 10
    frozen seeds:
    - completes, tilt ≤ 30°, heading ≤ 25°;
    - mean forward speed **> 4040 mm/s on every seed**;
    - a flight phase in every stride (duty ≤ 0.4), slip ≤ 0.3;
    - its footfall pattern within 0.1 of the named gait's reference.
  - The gait is a transverse or rotary gallop where the cat can reach it.
    If a bound or half-bound proves faster, both are measured and the faster
    one counts; the record says which, with the numbers.
  - Smoothness is no worse than the h3 baseline's: high-frequency share at
    most 0.2.
  - **Push it to its limits.** The record states the highest speed any
    policy reached, and what stopped it from going faster: torque, reach,
    stability or contact, measured. Use whatever helps, within O1: a speed
    curriculum, a better reference, stronger hocks (the hock is still on
    the AK60-6), lighter distal legs, or the tail as a balance mass.
  - Report each drive's RMS-to-rated ratio and clamp share (O4).
- [ ] **W1. Cadex has terrain in the world.**
  - A script can declare ground that is not flat:
    - bumps; step-ups and step-downs; slopes (hills);
    - a seeded random course of them, re-drawn per episode for training.
    The form is the actor's: an MJCF heightfield, placed boxes, or both,
    whichever MJX trains reliably. The record says which and why.
  - The terrain is in the exported model and the task bundle, the trainer
    trains on it, and `rollout_policy` and the dashboard show it, as
    geometry in the viewport and the rollout.
  - There is a height-scan observation channel, privileged by default (O5),
    and predicates for terrain tasks: distance made good over the course,
    falls, and the steps and slopes crossed.
  - Each piece has tests and an ADR. `describe_api`, `docs/XSCRIPT.md`,
    `docs/MUJOCO.md` and `docs/DASHBOARD.md` describe it, and
    `docs/ROADMAP.md`'s "terrain and workpieces in the world" item is
    ticked.
  - It is proved on a second, simple robot (Go1 from B1, or any small
    quadruped), not only the cat.
- [ ] **R1. The cat turns and changes direction.**
  - A policy on the final model follows a commanded forward speed and yaw
    rate, both re-sampled during the episode:
    - forward speed in about 0.5–2.5 m/s;
    - yaw rate in about ±60°/s;
    - including a reversal: a commanded 180° change of heading.
  - It passes on the 10 frozen seeds:
    - completes, tilt ≤ 30°;
    - yaw-rate tracking RMS error ≤ 20°/s outside a 0.5 s settling window
      after each command change;
    - forward-speed tracking RMS error ≤ 0.3 m/s;
    - the reversal completed (heading within 20° of the new command)
      within 3 s;
    - drives within rated RMS torque (O4).
  - New command kinds or tracking predicates the task language lacks are
    Cadex features, with tests and an ADR.
- [ ] **W2. The cat crosses rough ground.**
  - On W1's terrain, a policy on the final model crosses a randomised course
    and passes on the 10 frozen seeds. The course has:
    - bumps up to 40 mm;
    - step-ups and step-downs up to 80 mm;
    - slopes up to 15°, up and down.
  - Pass: completes with no fall, distance made good ≥ 80% of commanded,
    mean forward speed ≥ 1.0 m/s, tilt ≤ 30°, drives within rated RMS
    torque.
  - A curriculum (terrain difficulty rising with success) is allowed and
    recorded. These numbers are the owner's starting bar. If the cat clears
    them, the record states the largest step and slope it crosses.
- [ ] **C1. Closing report.**
  - `docs/probes/orun7/REPORT.md` covers:
    - A1 and A2 renders, before and after;
    - F1's speed against h2 and h3, and what limits it;
    - W1's design;
    - R1's and W2's results;
    - every ADR;
    - the remaining defects and what the next run should do.
  - Reconcile, then claim done for critic review without ticking the owner
    boxes.

## Later criteria

Not seeded. Work them only once every criterion above has evidence.

- One policy that gallops, turns and crosses terrain on command.
- Jumping onto and off blocks; crawling under a bar.
- A terrain height map from the cat's real cameras instead of a privileged
  scan.

## Horizon ladder

- **short-term:**
  1. H1's first page, then keep it current every iteration.
  2. Render the current head beside jaguar references, then name what makes
     the eye sockets read wonky and what the ears need.
  3. A1: the eye sockets, ears and face planes, rebuilt and clearance-checked.
  4. A2: the tail drive survey, any library additions, then the tail itself.
- **medium-term:**
  1. F1: retrain the bound on the final model cold to get a speed baseline,
     then push speed. Options:
     - a speed curriculum by warm start (reward-only changes are allowed);
     - a gallop reference;
     - hock drive and distal mass changes.
  2. W1: terrain in the script, the bundle, the trainer, the rollout and the
     dashboard, proved on a small robot.
  3. R1: speed and yaw-rate commands and the tracking predicates, then the
     turning policy.
- **long-term:**
  1. W2: the terrain curriculum and the rough-ground policy.
  2. Creature and base guidance:
     - how to state a terrain task;
     - when to give the critic a height scan;
     - how a tail is laid out and used.
     Every rule general, with its reason (O3).
  3. C1. Keep every gate green and every doc true, with `STATE.md`
     reconciled.

## Constraints

**Standing:**
- Obey AGENTS.md, the licensing rules and the process boundaries.
  - The repository carries no GPL or AGPL code. A fetched model or reference
    image lives outside the repo, is never vendored, and has its licence
    recorded.
  - Training stays offboard in `training/`, whose `cadex_train.py` imports
    only the standard library at module scope.
  - `CadexDynamics.py` stays unreachable from `cadexd` (ADR-102).
  - `analysis/` imports no GPL package.
- Never commit any of the following:
  - secrets or private hostnames;
  - build outputs;
  - full transcripts;
  - policy binaries, checkpoints or rollout traces;
  - fetched third-party models or images.
- Do not hand-edit `STATE.md`, `PLAN.md` or state nodes.
- **Keep earlier projects read-only:** every project in `~/cadex-projects`
  except `orun7-*`, which are this run's.

**This run:**
- **One training run at a time on the 5090.** The machine lock is the
  arbiter. The CLI suite runs with the GPU hidden
  (`CUDA_VISIBLE_DEVICES=`), so it never collides with a training job.
- **Long training does not block an iteration.**
  - An iteration may start a run detached and end; a later iteration reads
    the result. CPU work (code, tests, CAD, W1) proceeds while the GPU
    trains.
  - A cold run of the heavy cat takes about 90 minutes at 8192 envs and 600
    iterations.
  - Start every training run longer than a smoke in a scope of its own, for
    example `systemd-run --user --scope -p MemoryMax=30G ...`, so an OOM
    kills the trainer and not the loop.
- **Register every training run on the dashboard** with its policy and
  checkpoint rollouts, so the owner can watch it:
  - `runs/<name>/run.json`;
  - `retain_training_view`;
  - `cadex_cli.checkpoints.CheckpointRollouts`.
  Do it from the start, not after (the owner hit a missing model on
  bound-h1).
- **The protocol and tool surface stay a contract.**
  - Every `OP_ARG_SPECS` change updates `docs/INTEGRATION.md` in the same
    commit.
  - A tool change goes only through AGENTS.md's rule.
- **The dashboard stays read-only.**
  - Terrain rendering comes from what `/api/project` serves, with a browser
    test and `docs/DASHBOARD.md` in the same commit.
  - The actor may serve the dashboard on 127.0.0.1 for its own tests. It
    never runs `tailscale serve` and never binds a public address.
- Committed images are PNG, ≤300 KB each, under `docs/probes/orun7/`.
  Renders use the dark floor.
- No role starts, stops or restarts the loop or signals its process.

## Owner notes

- **Gates run in the foreground.** The session ends when the actor's turn
  ends. Every gate is a foreground command that finishes within the shell's
  10-minute limit. Write the record and the handoff before a long gate, then
  amend them with the result.
- **Keep the suites light.** New tests are fast unit tests where a unit test
  makes the claim, with at most one real-engine end-to-end test per
  criterion.
- **Engine limits met on cat-bound** (raise one only with an ADR stating why
  the new number is safe):
  - a reward expression holds at most 512 nodes;
  - a task holds at most 16 reward terms;
  - `num()` labels are short.
- **The trainer refuses a warm start** across changes to the model,
  observations, actions or reference. Reward-, episode- and spec-only
  changes are allowed with `--init-from-task-change` and
  `--init-from-parent-task`. A tail adds actions, so the first policy on
  the final model is cold.
- **What the bound work learned:**
  - A speed reward must pay at the episode's start speed. A narrow kernel
    at the target trained a bound on the spot (bound-h1).
  - `min(v, T)/T` paid for speed and got 4.04 m/s (bound-h2).
  - A pair-contact sync term fixed a half-bound (bound-h3).
  - The reference sets the timing only: leg reach caps a reference stride
    at about 0.6 m, and the policy chooses about 1.3–1.7 m.
- **A reward exploit is a finding, not a puzzle.** Record it. Prefer more
  reference (tracking) over another hand-written penalty.

## Question policy

- Resolve reversible choices autonomously, with the smallest measured step
  towards the highest-ranked open criterion.
- **Is it real hardware?** A drive or sensor no one sells is privileged
  (sensor) or refused (drive). When unsure, record why.
- **Base, style, or `training/`?** Apply O3.
- **Does it look right?** For A1 and A2, follow the creature style and the
  jaguar references, record the reasoning, and put the renders on the page
  for the owner. Do not stall on taste.
- Where O1–O5 and a measurement disagree, record both and follow O1–O5.
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
- Once H1, A1, A2, F1, W1, R1, W2 and C1 have evidence, write the closing
  report, reconcile and claim done. Two consecutive critic acceptances stop
  the run.
- Do not claim done while any criterion is unmet unless the run's wall-clock
  stop is near. Until then, work the highest-ranked open criterion, then the
  long-term rung.
- If the stop arrives first, report how far each criterion got and what is
  left. Do not redefine success.

## Quality bar

- At every accepted commit that touches code, run:
  - `pixi run test-engine`;
  - `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`;
  - for `training/` changes, its tests from the training venv
    (`~/cadex-train-venv`) as well.
- Python changes under `src/Mod/cadex/` need `pixi run build-engine` before
  the CLI's engine-needing tests count. For protocol or payload changes,
  rebuild and stage, then run the packaged lifecycle gate.
- Every bug fix has a test that fails without it.
- Every new library part, channel, command kind, predicate, terrain feature
  and trainer change has an ADR, starting at ADR-714.
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
