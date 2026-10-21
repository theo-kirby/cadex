# Goal: leo v03, a fast, cat-like gallop

Verified against source: 2026-10-21. Operator charter for orun14. It follows
orun13 (`.ouroboros/history/orun13.md`, merged at `4800b745`), which the owner
stopped at iteration 16 to give leo's hind paw a free pin: **leo v03**. It
keeps orun13's charter, plus two owner goals of 2026-10-21: the foot's posture
and the rotary lag both change with speed (O2a, O3a). The human owns this file; unattended roles
never edit it.

## Mission

Train **leo v03** to **gallop**: as fast as it can hold, with a gait that
reads as a real cat's:
- **its posture follows its speed:** digitigrade (on the toes, heels up)
  when slow, and closer to plantigrade (the whole foot flat in stance) the
  faster it runs (O2a);
- **always rotary**, with real lag between the paws of each pair, and that
  lag shrinking as the speed rises (O3a);
- a flight phase;
- the two-joint spine flexing and extending through the stride;
- both sides alike;
- a clean simulation.

The robot is designed, but **the loop may change it** when a measurement
shows the change makes the gallop faster or better (O1).

If the loop achieves only one thing, it is **one policy that passes P1 and P2
on leo v03 (or a measured successor) at the highest speed it can hold**,
judged by the engine and filmed. Next comes **one policy that runs across
speeds**: digitigrade and clearly rotary when slow, plantigrade with a
tighter rotary lag when fast (SG, RL).

## The robot

- **The project is `~/cadex-projects/leo`**, starting at the revision tagged
  `leo-v03` in its own git. It is this run's project. Every other project in
  `~/cadex-projects` is read-only.
- **Spine (new in v02).**
  - Two pitch joints on one AK80-9 pitch drive:
    - `j_spine`, at the chest, on the drive;
    - `j_spine2`, a lumbar joint 72 mm behind it.
  - A crossed cable (`coupling/cable_spine`, 1:1) makes `j_spine2` follow
    `j_spine`, so the spine bends ±50° in all on one action.
  - The yaw drive (`j_spine_yaw`, ±20°) sits behind the lumbar joint.
  - A saddle panel rides on the spine between the joints.
  - The gait generator bends the coupled joint with the spine (ADR-783).
    The gallop clip asks 7° a joint (14° in all), because the default 10° a
    joint left the left hind heel 2.1 mm short at a knee stop.
- **Hind leg.**
  - The thigh, knee and shin are feline v07's.
  - The hock drive works through a parallelogram push-rod to the
    metatarsus.
  - **The paw turns on a free pin (new in v03, owner 2026-10-21).**
    - `j_pawpin_*` is a plain hinge: no spring, no motor, damping 3.0
      N·mm·s/deg and 5 N·mm of friction.
    - It is seated so that the sole is flat at hock -60° with the pin at
      0.
    - It has 60° of toes-up travel relative to the metatarsus, so the heel
      can lift while the paw stays flat at push-off.
    - It stops at flat toes-down. The pad sits behind the pin, so its load
      lays the paw flat, and nothing holds it folded toes-up.
    - The heel (`c_heel_h*`) is welded to the metatarsus, its front
      trimmed 3 mm clear of the pad.
  - The gallop clip does not use `flat_feet` (ADR-780). It would hold the
    paw at its home-pose pitch, 60° toes-down at leo's hock-0 home. The
    solve's pull to pin 0 lays the paw flat when the metatarsus is
    level.
  - The claws are retracted inside the toe bulbs. At hock 0 to -40 the toe
    bulbs are the lowest point; at -60, heel, pad and toes are within 2 mm.
- **Front leg.** feline v07's wrist drive at the elbow, a 28 mm parallelogram
  push-rod to the paw, and the paw. Its toes are 7 mm shorter.
- **Not yet measured on v03:**
  - `scan_stand` (-25.2, re-measured on v02 by orun13) and the stand
    with the free paw;
  - the paw pin's speed in swing (on v06 a sprung pin flapped at
    900°/s);
  - the trainer's seconds per iteration;
  - whether the trot and bound clips still generate;
  - in plantigrade stance, the body pitches about 11° unless knee or hip
    take it up.
- **Known clearance at the start.**
  - The joint sweep fails 12–13 pairs, all of them front-leg parts against
    the chest through the shoulder and scapula.
  - 16 static pairs fail: heel/metatarsus and front crank/rod.
  - These are leo's baseline. A change may not add to them.
  - The v03 build's verdicts are recorded with its tag.
- **orun13's policies were trained on the welded paw.** Their observations
  and actions are unchanged, because the pin is passive and not observed,
  so a warm start is possible. But their habits were learned on a
  different foot: judge before trusting one.

## Owner decisions

- **O1. The model may change, for measured reasons.**
  - **Change the policy first:** the clip, task, rewards, observations,
    terminations, curricula, trainer settings and the declared tuning
    parameters.
  - **Change the model when a measurement shows it limits speed or form.**
    Examples: a joint stop the policy sits on, a drive at peak, a part the
    feet collide with, a stance the leg cannot reach, a mass that sets the
    pitch.
  - **Each model change:**
    - is written up before the build, giving the measurement and the
      expected effect;
    - rebuilds clean: every gate the build runs passes or is no worse
      than leo-v03's baseline above, and no new clearance pair fails;
    - is committed to the project's git and tagged `leo-v03.N`;
    - is judged afterwards with the same screen it was meant to fix, and
      kept only if that screen moved.
  - **Keep the owner's choices unless the numbers argue hard against
    them:**
    - linkage legs, fore and hind;
    - the plantigrade hind foot with its free, unsprung paw pin;
    - the two-joint spine on one drive;
    - the face, the panel style and the paws' look.

    Changing one of these needs a record giving the numbers, and a note in
    R1 for the owner.
- **O2. Plantigrade, flat-footed.**
  - On each hind leg, the heel (`c_heel_h*`) must be down for at least
    40% of that paw's stance, and at toe-off (`gallop_spec`'s `hock_down`
    and `hock_at_toeoff`).
  - In stance the foot is flat, toes down: no paw folded toes-up behind a
    heel. orun12's "passing" policy did exactly that.
  - At push-off the heel may lift while the paw stays flat on the floor
    (the paw turning toes-up of the metatarsus on its pin). That is the
    roll the pin is for, not a fault. A fault is a paw toes-up **of the
    floor**.
  - Check it on film or trace frames, not only the predicate.
  - orun12 learned that a clip alone does not put the heel down. A reward on
    a flat metatarsus pitch (`heel_pitch`) did. That reward is already in
    leo's gallop task. Start from it.
- **O2a. Posture follows speed (owner, 2026-10-21).**
  - **Slow: digitigrade.** The hind feet stand on the toe bulbs and the
    paw pads, heels up. The paw pin turns toes-up of the metatarsus, which
    v03's 60° of travel allows.
  - **Fast: closer to plantigrade.** The heel comes down for a growing
    share of stance, reaching P1's 0.4 at the top passing speed.
  - The heel's stance share rises with the commanded speed, not in one
    step.
  - The likely tool is a speed-scheduled reference (ADR-773, `api.gait`
    across speeds): heel hold (`heels`, `heel_from`), body drop and
    stance shift grow with speed, and the speed is a command the policy
    observes. The actor may extend the generator or the task, with an ADR
    from ADR-784.
- **O3. Real rotary lag.**
  - Each pair's paws land at least 40 ms apart, so the engine's 20 ms
    frame resolves the order.
  - orun12's clip landed them 21 ms apart, and every footfall read as
    tied.
- **O3a. Always rotary, less so as the speed rises (owner, 2026-10-21;
  orun12's walk-to-gallop criterion).**
  - At every speed the footfall order is rotary: LH, RH, RF, LF, or its
    mirror, never transverse, never a pronk.
  - The lag within each pair, as a share of the stride, is largest at the
    slow end and falls as the speed rises. The direction is from about
    0.25–0.5 slow towards 0.1–0.15 at the top, a tighter, more
    bound-like rotary gallop. It never falls below O3's 40 ms.
- **O4. Use the spine.**
  - Report the spine's angle range per stride on every judged run, and
    how long it sits at a stop.
  - The reason for v02 is that the old spine sat at its ±25° clamp about
    60% of a bound and bound up as the cadence rose. Show whether the
    two-joint spine fixes that.
  - Past about -25° of flexion the hind paws reach the fore paws. The
    hinds may land outside the fore track: orun10 measured that at about
    4% of speed.
- **O5. Both sides alike.**
  - Every judged result gives left and right separately.
  - Before blaming hardware or a reward, run the mirror tests
    (`docs/probes/orun12/mirror.py`, `mirror_policy.py`). In orun12 they
    settled each left/right question in one iteration.
- **O6. Torque.** Drives never exceed peak. Rated RMS is reported, not
  enforced. Every number reported carries the worst drive's RMS over rated
  and its peak margin.
- **O7. Track, don't describe.**
  - The clip carries the gait. Rewards back it up.
  - Evaluate a term per step on the bundle before adding it, and keep it
    only if a judged run shows it moved its measure.
  - In orun10 and orun11, every added rule cost speed.
- **O8. Short GPU runs to learn, then longer runs once confident (owner).**
  - **Learning phase:** screens of 30–80 iterations, with fewer envs
    (2048–4096) where that still answers the question. Each screen asks
    one question, and is judged on the engine at its checkpoints. A
    screen that clearly is not moving its measure by its first judged
    checkpoint is stopped early and recorded as a dead end.
  - **When confident:** a long run of 200–400 iterations, warm-started
    where the inputs allow (`--critic-warmup`; about 3e-5 for a
    fine-tune).
    - **Confident means:** the actor can name which lever moves which
      measure, from judged screens, and a screen's curve is still
      climbing with P1 holding.
    - The record of the long run says why it is warranted.
  - **Sizing:**
    - Time the first ten iterations of every new bundle, and set
      `budget_s` to the iterations asked for plus 20%.
    - feline v07 ran at about 67 s per iteration at 4096–8192 envs; leo's
      extra spine constraint may change that.
    - Extend a run only while its curve climbs.
  - **Keep the GPU busy.** Launch the next screen before a rebuild, an
    analysis or a write-up.
- **O9. A clean simulation.**
  - A judged policy shows:
    - no NaN or blow-up;
    - push-rod loops closed within 2 mm;
    - the spine cable coupling within 1°;
    - the paw pins under 900°/s at p95, with no flapping in swing;
    - no real-mesh interpenetration deeper than 5 mm between parts that
      do not touch in the build pose.
  - orun12's checks (`replay_check.py`, `meshcheck.py`, `selfcontact2.py`,
    `standtest.py`, `render_poses.py`, `render_fore.py`) are in
    `~/orun12-owner-scripts/`, with probe versions in
    `docs/probes/orun12/`. Put this run's under `docs/probes/orun14/`.
- **O10. Straight lines, flat ground.** No turning, leaping or terrain.

## Done criteria

Every criterion is measured with the engine's evaluation on `gallop_spec`'s
10 frozen seeds, not the trainer's numbers. Stance and contact shares
exclude the first second. Drives always stay under peak (O6).

- [ ] **B1. Ready to train.**
  - The gallop bundle builds on leo-v02.
  - `scan_stand` and the stand parameters are re-measured on v02.
  - The gallop clip's `j_spine2` follows `j_spine`, checked in the
    bundled clip.
  - The seconds per iteration are timed.
  - A first screen is judged and reported against:
    - orun13's g4-peak-50 on the welded paw: soles flat, heels 0.44 /
      0.22, 2.43 m/s;
    - orun13's g7-hock75: heels 0.46 / 0.41, `hock_down` 6 / 10, 2.60
      m/s;
    - orun12's heel5c-s1 on feline v07: P1 8 / 10, heels 0.60 / 0.61,
      2.91 m/s.
- [ ] **P1. Plantigrade and flat, both legs (O2).**
  - On one policy, on at least 8 of 10 seeds, `hock_down` and
    `hock_at_toeoff` pass for **each** hind leg.
  - The report gives the heel's stance share and median stance height per
    leg.
  - A still or trace frames show both feet flat, heel and toes down.
- [ ] **P2. The feline gallop's form.** On the same policy, on at least 8
  of 10 seeds:
  - `no_tap`, `every_stride` and `overreach` pass;
  - the footfall order is rotary, with each pair's lag at least 40 ms
    (O3);
  - each stride has a measured flight phase;
  - the median overreach, fore reach, lag and flight time are reported.
- [ ] **SG. Posture follows speed (O2a).**
  - **The policy:** one policy commanded at three or more speeds, from the
    slowest it can gallop to its fastest, each judged on 10 seeds.
  - **At the slowest:** digitigrade. The hind heel is down for at most
    0.1 of stance on each leg. A still shows the feet on the toes.
  - **At the fastest:** P1 holds.
  - **In between:** the heel's stance share rises with the speed, per
    leg.
  - **The report:** a table of speed against heel share, per leg.
- [ ] **RL. Rotary at every speed (O3a).** On the SG policy, at each judged
  speed:
  - the footfall order is rotary on at least 8 of 10 seeds;
  - each pair's lag is at least 40 ms;
  - the fore and hind lag, as a share of the stride, falls as the speed
    rises.
  - **The report:** a table of speed against lag, fore and hind.
- [ ] **SP. The spine works (O4).** On the P1/P2 policy, the report gives:
  - the spine's range per stride;
  - the share of time at a stop;
  - its phase against the hind footfalls;
  - a comparison with orun7's ~60% at the clamp.
- [ ] **Q1. Symmetric.** On the P1/P2 policy, the left and right hind
  legs' heel stance share, stride length and touchdown rate are within 20%
  of each other.
- [ ] **Q2. Clean simulation.** The P1/P2 policy's traces pass O9.
- [ ] **S1. 5 m/s, plantigrade.**
  - A sprint holds at least **5 m/s** over a 2 s window on at least 8 of
    10 seeds, by a policy that also passes P1, P2 and Q2. That is
    `gallop_spec` in full.
  - If it falls short, the report says what binds: the drive, the stride
    phase and the margin.
- [ ] **S2. As fast as it goes.**
  - Past 5 m/s, keep raising the clip's speed while P1, P2 and Q2 hold.
  - Record the top passing speed and what stopped the next step.
- [ ] **F1. The films**, on the run's page:
  - the fastest passing gallop, side-on, at full speed and in slow motion;
  - a hind foot close up through a stride;
  - the spine through a stride;
  - the SG policy at its slowest and fastest, side by side: the toes
    against the flat foot, and the rotary lag tightening;
  - left and right side views.
- [ ] **R1. The closing report.** `docs/probes/orun14/REPORT.md` gives:
  - each criterion with its numbers;
  - the clip and reward design;
  - the terms kept and cut;
  - every model change (O1), with its before and after;
  - what limits speed, drive by drive;
  - the hardware changes the numbers argue for that the run did not make.

## Later criteria

Not this run's. They are for when the frontier above is empty:
- Walk to gallop: one policy on an ADR-773 speed-scheduled reference, from
  a walk of about 0.5 m/s to the fastest passing gallop.
- The same policy decelerates back to a walk.
- The plantigrade gallop at 5.5 m/s or more.

## Horizon ladder

- **short-term:**
  1. B1:
     - build the bundle;
     - check the clip's paw pin and spine coupling;
     - check the stand on the free paw;
     - time ten iterations.
  2. Launch the first screen (40–60 iterations) before anything else that
     is slow. Use orun13's best task (g4-peak's, with heel5's stored
     settings and the 62.5 ms rotary clip). Train it cold, or warm from
     g4-peak-50 if the actor can say why.
  3. Adapt orun13's probes (`docs/probes/orun13/`: `foot_frames.py`,
     `lh_roll.py`, `stance_gate.py`, `hind_reach.py`, `p2_lag.py`,
     `spine_foot.py`) to the paw pin: the paw's pitch relative to the
     floor and to the metatarsus, the roll at toe-off, and the pin's speed.
     Put new ones under `docs/probes/orun14/`.
  4. Read the clip:
     - the heel share, lag, flight, overreach and spine range it asks for;
     - whether the generator reaches a 40 ms pair lag and a longer stride.
- **medium-term:**
  1. Close P1 with short screens: the clip, `heel_pitch` and the tracking
     weights, cold where a habit must be undone.
  2. Close P2:
     - real pair lag;
     - flight;
     - no taps;
     - overreach, with an outside-hind track if the paws collide.
  3. Once confident (O8), a long run on the best task. Then raise the speed
     to S1 and S2, measuring what binds at each step.
  4. Model changes where measurements show the model binds (O1). Each is
     rebuilt, tagged, re-screened and kept only if it helped.
  5. SP, Q1 and Q2 on the passing policy.
  6. SG and RL:
     - a speed-scheduled reference whose heel hold and pair lag change
       with speed;
     - a speed command;
     - a slow digitigrade screen first (it should come easily: orun12 and
       orun13 policies lifted their heels unasked);
     - then one policy across speeds, warm from the best P1/P2 policy
       where the inputs allow.
- **long-term:**
  1. F1's films and R1's report, kept current as each criterion closes.
  2. The later criteria.
  3. Fold what this run proves into `training/RECIPE.md`:
     - a plantigrade gallop on a free paw pin;
     - a coupled spine;
     - the short-screen-then-long-run budget.
  4. Keep every gate green, every doc true, `STATE.md` folded, and R1
     current.

## Constraints

**Standing:**
- Obey AGENTS.md, the licensing rules and the process boundaries.
  - The repository carries no GPL or AGPL code.
  - Training stays offboard in `training/`, whose `cadex_train.py` imports
    only the standard library at module scope.
  - `CadexDynamics.py` stays unreachable from `cadexd` (ADR-102).
- Never commit any of the following:
  - secrets or private hostnames;
  - build outputs;
  - full transcripts;
  - policy binaries, checkpoints or rollout traces;
  - fetched third-party files.
- Do not hand-edit `STATE.md`, `PLAN.md` or state claims.

**This run:**
- **The only project the run writes is `~/cadex-projects/leo`.**
  - Model edits follow O1.
  - The `leo-v02` and `leo-v03` tags are never moved or deleted. Model
    changes are tagged `leo-v03.N`.
- **One training run at a time on the 5090.** The machine lock is the
  arbiter. The CLI suite runs with the GPU hidden (`CUDA_VISIBLE_DEVICES=`).
- **Long training does not block an iteration.**
  - Start runs detached through `cadex_cli.loop` (`register`,
    `retain_training_view`, `launch`), so the dashboard follows them, and
    end the iteration. A later iteration reads the result.
  - Each run gets its own scope
    (`systemd-run --user --scope -p MemoryMax=30G ...`). Never use a
    transient service: it kills the trainer.
- **Builds.**
  - A leo build takes 12–15 minutes and goes to the background.
  - The project's `agent.json` timeout stays at most 3600 s. Over the
    CLI's cap, the build falls back to 300 s.
  - A direct `FreeCADCmd` runs under `ulimit -v 16000000`.
- **The protocol and tool surface stay a contract** (AGENTS.md).
  - An engine change (a predicate, a generator option) gets an ADR from
    ADR-784, and the engine and CLI suites.
- **The dashboard stays read-only.** The actor may serve it on 127.0.0.1
  for its own tests. It never runs `tailscale serve` and never binds a
  public address.
- Committed images are PNG, ≤ 300 KB each, under `docs/probes/orun14/`, on
  the dark floor. Films live outside the repo and on the run's page.
- No role starts, stops or restarts the loop or signals its process. Kill
  stray engine processes by PID, never with a broad `pkill` pattern.

## Owner notes

- **The run's page is the owner's view.** The scribe keeps it. Each
  iteration it shows:
  - each criterion's latest judged numbers, left and right;
  - the top speed so far;
  - the spine's range;
  - training curves;
  - the newest films or stills;
  - every model change.

  Every training run is registered on the dashboard.
- **Gates run in the foreground** and finish within the shell's 10-minute
  limit.
- **Lean suites (ADR-725).** Add a test only for a contract or a regression
  that actually happened.
- **What came before:**
  - **orun12 on feline v07:** P1 passed at 2.91 m/s via `heel_pitch`
    (heel5c-s1). But the paws folded toes-up behind the heels, the
    footfalls never read as rotary (21 ms lag), and Q2 stayed open:
    - a hind paw 8.5 mm into a forearm;
    - front rod loops open by up to 2.9 mm.
  - **orun13 on leo v02 (welded paw), 8.2 h, P1 open.** Every P1 screen
    failed at toe-off:
    - the hock drive sat at peak, driving the heel up through stance;
    - LH rolled onto its toes for three or more frames on half its
      toe-offs;
    - RH lifted off outside the clip's stance, where `heel_pitch` pays
      nothing.

    The hock-stop change (leo-v02.1) was judged and not kept. The paw pin
    is the owner's answer.
  - **Speed:**
    - the best on any cat was 4.64 m/s, on its toes (orun10);
    - every reward rule added cost speed;
    - the heel cost 3.22 → 2.91 m/s.
  - **The trainer's reward is not a pass.** Judge with the engine.
- **Engine caps:**
  - 32 reward terms;
  - 128 observation channels;
  - 512 nodes per reward expression;
  - 64 parameters per script, which leo is at, so new knobs are literals.
- `./cadex params` takes a repeated `--set k=v`.

## Question policy

- Resolve reversible choices autonomously, with the smallest measured step
  towards the highest-ranked open criterion. The order is B1, P1, P2, SG,
  RL, Q2, SP, Q1, S1, S2.
- Prefer a policy change to a model change. A model change needs a
  measurement (O1).
- Where O1–O10 and a measurement disagree, record both and follow O1–O10.
- Code and accepted artifacts outrank docs.
- A pre-existing test failure is recorded and left alone, unless the unit's
  own change touches it.
- A harness or usage limit is not an attempt: wait for capacity.
- Never invent a measurement, never weaken a spec to pass, and never wait
  for a human.

## Exhaustion policy

`report_done`.
- Once B1, P1, P2, SG, RL, SP, Q1, Q2, S1, S2, F1 and R1 have evidence, write the
  closing report and claim done. Two consecutive critic acceptances stop
  the run.
- Until then, work the highest-ranked open criterion, then the later
  criteria.
- If the stop arrives first, report how far each criterion got. Do not
  redefine success.

## Quality bar

- At every accepted commit that touches code, run:
  - `pixi run test-engine`;
  - `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`;
  - for `training/` changes, its tests from `~/cadex-train-venv`.
- Python changes under `src/Mod/cadex/` need `pixi run build-engine` before
  the CLI's engine-needing tests count.
- A judged run is reported with:
  - each spec's pass count;
  - the failing predicate's median;
  - per-leg heel share and a flat-foot check;
  - pair lag;
  - flight;
  - spine range;
  - the top speed;
  - the worst drive's RMS over rated and its peak margin;
  - the checkpoint it started from.
- **The critic checks numbers at their source.** For every judged run, it
  opens at least one cited `evaluation.json` and checks the report against
  it.
- **The critic checks the feet on film or in a trace.** A P1 claim cites
  frames showing both feet flat, heel and toes down.
- **A model change is accepted only with its build verdicts and its
  before/after screen.**

## Reconcile

- The scribe folds every five work iterations, or at three unfolded
  records:
  - impacts applied;
  - statuses set with evidence;
  - `STATE.md` rendered;
  - `ouroboros mem check` clean.
- Earlier runs' open claims stay open and untouched.
- Unattended roles never edit this charter.
