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

**Owner revision, 2026-10-16 (mid-run).** The owner reviewed the run at
iteration 22:
- **The face (A1) is good.**
- **The gallop (F1) is fine for now.** It is accepted as it stands
  (f1-g2: 4.15–4.17 m/s on all 10 seeds); no more F1 work this run.
- **The tail (A2) is not.** The owner: it is "too rigid and not tail
  like". It moves "up and down with the hips and slap[s] into the ground".
  A2 is rewritten below.
- **Then go straight to turning (R1) and terrain (W1, W2).**

**Owner revision 2, 2026-10-16 (iteration 26).** The owner reviewed the
reworked tail and the hind feet:
- **The tail may be one width along its length;** no taper is needed.
- **It ends in a round white cap.**
- **The hind paws are wrongly oriented for how the feet are used.** In
  every rollout the hind foot goes down flat through stance, as a real
  cat's does, and that motion is right; keep it. But the paw part was
  designed before the gait existed, so in that pose it sits wrong on the
  ground. A3 below rebuilds it.
- Both changes alter the model, so they land **before R1's first training
  run**, together, in one rebuild if possible.

**Owner revision 3, 2026-10-16 (iteration 27).** The owner watched r1-t1
train and **stopped it at iteration 98**. It is recorded as an
interruption, not an attempt. The cat has no lateral spine joint: it cannot
bend its spine sideways to turn. The owner: the spine pitch drive "is one
of the most important" joints, and for agile movement the cat must also
bend laterally at or near it. A4 below adds the joint.
- **Finish the design first:** A2's width and cap, A3's hind paws and A4's
  lateral spine, in one rebuild if possible.
- **Then continue R1's turning training** on the rebuilt model, cold.
  r1-t1's task, reward and logs remain usable as the first look at the R1
  task; its policy is stale.

**Owner revision 4, 2026-10-16 (iteration 29).** Iteration 29 started r1-t2
on revision 3b12f90b, which has no lateral spine. The owner stopped it at
iteration 4 (an interruption, not an attempt). The owner also sees **no
visible change to the hind feet**, and the operator confirmed it:
- 3b12f90b's hind-paw collision geometry is byte-identical to f1-g3's: the
  same two spheres at the same positions. The contact physics did not
  change.
- The "after" render is drawn in the build pose (the hock link vertical),
  where the foot looks as it did before.
- **The operator measured the hind paw body** (the hock link and the paw,
  one body) in f1-g3's best policy, seed 1001, using
  `~/orun7-progress/hindlink.py`. In stance it is pitched **about 58°
  (p10 53°, p90 61°) from its build pose**; in swing, about 1°. So in
  stance the whole hock-to-toe link lies down towards the ground, as a
  cat's foot does. The paw block at its end is built for a vertical link,
  so in stance it is rotated more than 50° away from flat. That is the
  owner's complaint.
- **A3's earlier sole-angle measurement (−4..+5° at mid-stance)
  contradicts this.** Re-measure in the world frame, and say which was
  wrong and why.
- **What A3 must now do:**
  - design the hind foot for the stance pose: the hock link is the
    metatarsus;
  - put the sole, pads and toes so they lie flat on the ground when that
    link is at its measured stance angle, with the ankle (hock) raised
    behind them as a cat's is;
  - move the collision geometry with the visual: pads and toes that carry
    the contact in stance;
  - render the before and after **in the measured stance pose**, not the
    build pose.
- **Do not launch any R1 training until A3 and A4 are both in the
  rebuilt model.**

**Owner revision 5, 2026-10-16 (iteration 38): shorter training runs.**
The owner watches the curves, and they flatten early. r1-t3 added 7% to its
reward per step between iterations 200 and 475, against 85% before 200.
From here on:
- **Default budget: 200–300 iterations.** Screening runs, which test a
  reward, a reference or a design, use 100–150.
- **Extend only on evidence, by warm start.** If the curve is still
  clearly climbing at the end, warm-start from the policy on the same
  bundle for another 100–200 iterations. Spend the saved GPU time on more
  experiments, not on longer plateaus.
- The record states the budget and why, and when a curve plateaued.
- r1-t3 (600 iterations, started before this revision) runs to its end.
  If the A3 paw changed after it started (accepted 0f036864), say whether
  r1-t3's model is stale for A3.

If the run achieves only one thing from here, it is this: **the cat, with a
supple, actively used tail, turns and changes direction on command, and its
tail never strikes the ground.**

Priority, in order: H1 (always on); then A2 (the rework), A3 (hind paws)
and A4 (lateral spine) together, as one design pass; then R1, W1, W2, C1.
- The tail rework lands first, and fast. It changes the model, so R1 and W2
  must train on the reworked tail, never on the current one. Keep the CAD
  rework small: the tail only, the rest of the cat untouched.
- W1 is CPU work. It proceeds while the GPU trains R1.

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
- [x] **A1. Ears and a jaguar face.** *Accepted by the owner, 2026-10-16.*
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
- [ ] **A2. A supple tail that moves like a big cat's (reworked 2026-10-16).**
  - **The first tail failed the owner's review:** 622 mm, 4 actuated joints.
    It is too rigid, it pitches with the hips, and it slaps the ground.
  - **More actuation, and a tail that can curve.**
    - At least 6 actuated joints, short segments (about 100 mm or less), so
      the tail bends along its length as a big cat's does, instead of
      swinging as a stick.
    - Both pitch and yaw near the root (lift and side sweep), and yaw along
      the length, so it can curl sideways.
    - Real drives (O1). Add thinner ones to the library if needed. A
      tendon-driven section, with its drives at the root and cables through
      the segments, is allowed if it is built from real parts and its
      simulated limits are honest.
    - The record compares the options on torque, mass and diameter.
    - Length 0.6–0.7× head-and-body. **Width (owner revision 2):** one
      width along the whole tail is fine, about the root's; no taper is
      needed.
    - **A round white cap on the tip (owner revision 2):** a domed white
      panel closing the last segment, matching the panel language.
  - **It behaves like a big cat's tail.**
    - It is carried clear of the ground. No tail segment touches the
      ground in any rollout of R1's or W2's policy. Measure it as a
      predicate (tail–ground contact share = 0), not by eye.
    - It is not slaved to the hips. Its root pitch is decoupled from the
      pelvis pitch. Measure the correlation; the record shows it falls from
      the first tail's.
    - It is used for agility. In turns and reversals (R1) it sweeps to
      balance the body, as a cheetah's or a jaguar's does: measure the tail
      yaw against the commanded yaw rate and report it.
    - It moves smoothly, not as flailing: its own command high-frequency
      share is reported.
    - How it is taught is the actor's choice: tail clearance and contact
      terms, a reference tail motion, its mass and inertia, or joint
      stiffness and damping. The record says what worked, and what was
      tried and failed.
  - It is panelled to match, and it rebuilds; clearance and the joint sweep
    pass over the full tail travel.
  - Renders and a short rollout clip of the tail in a turn go on the page.
- [ ] **A3. Hind paws shaped for how the hind feet are used (owner revision 2).**
  - **Look before changing anything.** Take stance frames from a
    galloping or bounding rollout on the current model. Measure where the
    paw meets the ground (which geometry carries the contact), the angle of
    the paw's sole to the ground, and where the hock (ankle) sits relative
    to the paw. Render the before pose, side and three-quarter, on the dark
    floor.
  - Then reshape and reorient the hind paw, and the parts around it as
    needed, so that in that measured stance pose:
    - the sole and pads lie flat on the ground;
    - the toes point forward;
    - the ankle sits where a cat's hock would over a flat-down foot.
    The paw must read as a cat's paw, not a part bolted on at an angle.
  - Do not change the gait to suit the old part: the motion is right. Keep
    the joint chain and drives unless the measurement shows a change is
    needed, and record why if one is made.
  - Measured after: in stance frames of a rollout on the rebuilt model, the
    sole's angle to the ground stays within about 15°, and the contact is
    carried by the pads, not by a panel edge or the paw's side. A
    before-and-after table and renders of the stance pose go on the page.
  - It rebuilds; clearance, the joint sweep and the mounts pass. The front
    paws are not part of this change.
- [ ] **A4. The spine bends sideways (owner revision 3).**
  - Add an actuated lateral (yaw) spine joint at or near the existing spine
    pitch joint, so the body can curve left and right in turns, as a cat's
    does. The pitch joint stays, and it keeps a strong drive.
  - A real drive (O1), sized from a measurement: the lateral torque a turn
    at R1's yaw rates and speeds asks of the spine. Use r1-t1's rollouts, or
    a quick estimate from mass and inertia. The record states the estimate
    and the drive's margin over it.
  - The layout is the actor's to choose and record: a yaw drive stacked on
    the pitch drive, a 2-DOF joint, or a yaw joint just ahead of or behind
    it. Structure, bearings and the chest and pelvis frames change as they
    need to. Panels follow the mechanism and cover the new travel; the
    belly and back seams open as the body bends.
  - Travel is chosen and recorded, with a source on cat spine lateral
    flexion, or a measured need.
  - The new joint is in the task's action set. R1's record reports its use
    in turns: lateral spine angle against the commanded yaw rate.
  - It rebuilds; clearance, the joint sweep over the full pitch × yaw travel
    and the mounts pass. Mass change stated.
- [x] **F1. The fastest gallop yet.** *Accepted by the owner as it stands,
  2026-10-16: f1-g2, 4.15–4.17 m/s on all 10 seeds. Its footfall error of
  0.100 sits on the limit, on the 50 Hz frame grid; the defect is filed. No
  further F1 work this run. The criterion text is kept for the record.*
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
    - drives within rated RMS torque (O4);
    - the reworked tail (A2): no ground contact, and it is used in the turns.
  - New command kinds or tracking predicates the task language lacks are
    Cadex features, with tests and an ADR.
- [ ] **W2. The cat crosses rough ground.**
  - On W1's terrain, a policy on the final model crosses a randomised course
    and passes on the 10 frozen seeds. The course has:
    - bumps up to 40 mm;
    - step-ups and step-downs up to 80 mm;
    - slopes up to 15°, up and down.
  - Pass: no tail–ground contact; completes with no fall, distance made good ≥ 80% of commanded,
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
  1. Keep H1 current every iteration. Show the owner's revision and the tail
     rework on the page.
  2. One design pass, before R1 trains:
     - A3: measure the hind paw in stance, then reshape it (owner revision 2);
     - A4: size and add the lateral spine joint (owner revision 3);
     - A2's single width and round white cap.
     Rebuild once, then fit, sweep and mounts.
  3. A2 rework:
     - measure the current tail (hip correlation, ground contact);
     - pick the joint layout and drives;
     - rebuild the tail, clearance-check and sweep it.
  4. R1's command kinds and tracking predicates, and the tail predicates
     (ground contact, hip correlation, yaw against yaw rate). This is CPU
     work while nothing trains.
- **medium-term:**
  1. R1: the turning policy on the reworked model, with the tail used in the
     turns.
  2. W1: draw the course in the rollout and the dashboard, and prove it on a
     small robot.
  3. W2: the terrain curriculum on the reworked cat.
- **long-term:**
  1. W2's largest step and slope, and a policy that turns on terrain.
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
- Once H1, A2, A3, A4, R1, W1, W2 and C1 have evidence (A1 and F1 are
  owner-accepted), write the closing
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
