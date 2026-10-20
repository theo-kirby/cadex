# Goal: feline v07, as fast as it can gallop, plantigrade and cat-like

Verified against source: 2026-10-19. Operator charter for orun12. It follows
orun11 (`.ouroboros/history/orun11.md`, merged at `1f0ab418`) and the owner's
session of 2026-10-19, which locked the cat as feline v06 (ADR-779) and then
redesigned its legs as **feline v07**. The human owns this file; unattended
roles never edit it.

## Mission

Make **feline v07** run **as fast as it can** with a gallop that looks like
a real cat's: plantigrade at the hind, rotary footfalls, a long fore reach,
the hinds landing ahead of the fore prints, a flight phase, no taps, and
both sides alike. The robot is designed. This run designs the **policy**:
the reference clip, the task, the rewards, the training, and the tuning
parameters.

If the loop achieves only one thing, it is **one policy that passes
`gallop_spec`'s form on both hind legs at the highest speed this cat can
hold**, judged by the engine and filmed.

## The robot (locked)

- **The project is `~/cadex-projects/feline-v07`**, starting at revision
  `9eaff867`. It is this run's project. Every other project in
  `~/cadex-projects` is read-only.
- **Hind leg.**
  - The hock drive, an AK80-9, sits at the knee, coaxial and inboard of the
    shin.
  - A crank and a 5.5 mm push-rod form a 35 mm parallelogram to a horn on
    the metatarsus, so the crank angle equals the hock angle.
  - The hock is a slim pin.
  - A slim PU heel sits under the metatarsus. In the plantigrade pose its
    sole is 6 mm under the paw's sole line.
  - The paw is v06's paw on its sprung hinge.
- **Front leg.**
  - The wrist drive, an AK60-6, sits at the elbow on a 5 mm spacer.
  - A 28 mm parallelogram push-rod drives the paw.
  - The front foot is always just the paw.
- **Joint names.**

  | Joint | What it is |
  |---|---|
  | `hock_*`, `wrist_*` | the drives, acting on the cranks |
  | `ankle_*`, `carpus_*` | the pins |
  | `rodtop/rodbot_*`, `frodtop/frodbot_*` | the rod ends, closed as `equality/connect` |
  | `REF_OF` | maps each drive to the reference of the pin it moves |

- **The task.**
  - The gallop task is orun11's 17-term plantigrade clip on this cat.
  - The heels are `c_heel_h*`.
  - The tail's ct3/ct4 contacts are dropped to fit the 128-channel cap.
- **The first run is `v07-g1`**, registered in `runs/v07-g1`. It trains
  from scratch for 300 iterations, with a checkpoint every 25, and started
  before this run did. It is the baseline.

## Owner decisions

- **O1. Policy only.**
  - **The loop may change:**
    - the reference clip and the gait generator's settings;
    - the observations, rewards, terminations, curricula, commands and
      disturbances;
    - the trainer's settings;
    - the declared tuning parameters: springs, damping, friction, joint
      stops, the pad and heel material, the action filter, and a joint's
      position limits.
  - **The loop may not change:** the mechanism's geometry, the drives, the
    gear ratios, the linkages, the part shapes, or the masses beyond a
    material density.
  - **If a measurement shows the mechanism limits speed or form**, record
    it with numbers in R1 and go on with the policy. The owner decides
    hardware.
- **O2. Plantigrade, or it doesn't count.** A fast gallop on the toes is not
  the goal. On each hind leg, the heel (`c_heel_h*`) must be down for at
  least 40% of that paw's stance, and at toe-off (`gallop_spec`'s
  `hock_down` and `hock_at_toeoff`).
- **O2a. The heel comes first (owner, 2026-10-19, after iteration 6).**
  - Two runs have shown the clip alone does not put the heel down:
    - v07-g1 at 100: heel down 0.00 on both legs, hovering 31 / 75 mm
      above the floor;
    - heel2-s1 at 50, on a clip holding the heel for 0.8 of stance: 0.03
      and 0.11.
  - So O5's "track, don't describe" is relaxed **for the heel**. The loop
    may add whatever makes both hind heels take weight in stance:
    - a heel-contact reward, paid while the clip says the heel is down;
    - a penalty on heel height in that phase;
    - a termination for a stance that never lays the heel down;
    - a curriculum, for example heel first at a lower speed, then raising
      speed;
    - a stronger tracking weight on the ankle pin.
  - Keep a term only if a judged run shows it moved the heel share.
  - **Until P1 passes, speed comes second.** A slower plantigrade gallop
    beats a faster one on the toes. Do not push the speed command up
    while the heel is still off the floor.
  - **Left/right symmetry work** (a mirror-symmetry term and the like)
    waits until at least one policy puts both heels down. The unfinished
    iteration-7 symmetry term is saved at
    `.ouroboros/runs/orun12/reverted/iter7-symmetry-term-wip.patch`
    (and in `git stash`) for then.
  - **Screens are slow** (about 131 s an iteration at 8192 envs). Heel
    screens may use fewer envs or fewer iterations (60–100) to get
    answers sooner, and a run that clearly is not laying the heel down by
    its first judged checkpoints may be stopped early with `train_stop`
    or the loop's stop, recorded as a dead end.
  - The queued o9-s1 run (chest box only, no heel change) was cancelled by
    the owner. Fold the chest-box fix into the next heel screen instead.
- **O3. Both sides alike.**
  - The owner saw the left hind do far better than the right on v06-g1.
  - Every judged result reports left and right separately.
  - Before a hardware or reward explanation, check asymmetry with:
    - a mirror test of the model;
    - a symmetric clip, with no hind lead;
    - mirrored seeds.
  - orun11 skipped this check and spent a drive swap.
- **O4. Torque.** Drives never exceed peak. Rated RMS is reported, not
  enforced. Every number reported carries the worst drive's RMS over rated
  and its peak margin.
- **O5. Track, don't describe.**
  - The clip carries the gait: plantigrade stance, fore reach, hind
    overreach, matched cadence, rotary lag and flight.
  - Rewards back the clip up.
  - Before adding a term, evaluate it per step on the accepted bundle.
  - Keep a term only if a judged run shows it moved its measure.
  - orun10 and orun11 measured every added rule costing speed.
- **O6. Straight lines, flat ground.** No turning, leaping or terrain.
- **O7. Short screens, many of them.**
  - A screen is 100–150 iterations. A full run is 200–300.
  - Warm-start with a critic warm-up where the actor's inputs allow.
  - After a task change that undoes a habit, train cold.
  - Extend a run only while its curve climbs.
  - Judge every checkpoint a run leaves.
- **O8. Size the budget to the model.**
  - The linkage cat steps more slowly than v06: time the first ten
    iterations of each new bundle.
  - Set `budget_s` to cover the iterations asked for, plus 20%.
- **O9. A clean simulation.**
  - The owner saw the sim "breaking" and parts passing through each other
    on v06.
  - **A judged policy shows:**
    - no NaN or blow-up;
    - push-rod loops closed within 2 mm;
    - no real-mesh interpenetration deeper than 5 mm between parts that
      do not touch in the build pose, on the evaluation traces.
  - **Tools:** the owner's offboard checks (`replay_check.py`, `meshcheck.py`,
    `selfcontact2.py`, `standtest.py`, `render_poses.py`, `render_fore.py`)
    are copied to `~/orun12-owner-scripts/`, outside the repo. Rebuild what
    you need under `docs/probes/orun12/`.

## Done criteria

Every criterion is measured with the engine's evaluation on `gallop_spec`'s
10 frozen seeds, not with the trainer's numbers. Stance and contact shares
exclude the first second. Drives always stay under peak (O4).

- [ ] **B1. The baseline is judged.**
  - Every v07-g1 checkpoint is evaluated on `gallop_spec`.
  - Its report gives:
    - each predicate's pass count and median;
    - each predicate's value per hind leg;
    - the top speed;
    - the torque margins.
  - It is compared with v06-g1's final numbers:
    - 0/10 pass;
    - 3.72 m/s best, at iteration 150;
    - a hock-down share of at most 0.12;
    - an overreach of 355–474 mm.
- [ ] **P1. Plantigrade, both legs.**
  - On one policy, on at least 8 of 10 seeds, `hock_down` and
    `hock_at_toeoff` pass for **each** hind leg.
  - The report gives the heel's stance share and median stance height per
    leg.
  - A still or trace frames show both heels on the floor.
- [ ] **P2. The feline gallop's form.** On the same policy, on at least 8
  of 10 seeds:
  - `no_tap`, `every_stride` and `overreach` pass;
  - the footfall order is rotary;
  - each stride has a flight phase, a measured time with no paw on the
    floor;
  - the median overreach, fore reach and flight time are reported.
- [ ] **Q1. Symmetric.**
  - On the P1/P2 policy, the left and right hind legs' values are within
    20% of each other for:
    - heel stance share;
    - stride length;
    - touchdown rate.
  - Any asymmetry found on the way is traced to its cause, with O3's
    checks.
- [ ] **Q2. Clean simulation.** The P1/P2 policy's evaluation traces pass
  O9:
  - no blow-up;
  - loops closed within 2 mm;
  - no new mesh interpenetration deeper than 5 mm.
- [ ] **S1. 5 m/s, plantigrade.**
  - A straight-line sprint holds at least **5 m/s** over a 2 s window on
    at least 8 of 10 seeds, without falling, by a policy that also passes
    P1, P2 and Q2. That is `gallop_spec` in full.
  - The report gives:
    - the highest 2 s average on any seed;
    - the median over the 10 seeds;
    - stride length, stride frequency and flight time;
    - what binds (drive, stride phase, margin) if it falls short.
- [ ] **S2. As fast as it goes.**
  - Past 5 m/s, keep raising the clip's speed while P1, P2 and Q2 still
    hold.
  - The run's top passing speed is recorded with what stopped the next
    step: a drive at peak, the clip failing to generate, or form lost.
- [ ] **F1. The films**, on the run's page:
  - the fastest passing gallop, side-on, at full speed and in slow motion;
  - a hind foot close up through a stride, with the heel down at
    push-off;
  - left and right side views of the same policy.
- [ ] **R1. The closing report.** `docs/probes/orun12/REPORT.md` gives:
  - each criterion with its numbers;
  - the clip and reward design, and why;
  - the terms that earned their place, and the terms that were cut;
  - what limits speed, drive by drive;
  - any hardware change the numbers argue for (O1), for the owner.

## Later criteria

Not this run's. They are for when the frontier above is empty:
- Walk to gallop: one policy on an ADR-773 speed-scheduled reference, from
  a walk of about 0.5 m/s to the fastest passing gallop, staying rotary,
  with each pair's lag falling from about 0.5 to 0.15 or less.
- The same policy decelerates back to a walk.
- The plantigrade gallop at 5.5 m/s or more.

## Horizon ladder

- **short-term:**
  1. Judge v07-g1's checkpoints (B1) as they land, once the run has
     ended. Do not stop it.
  2. Rebuild the owner's offboard checks as committed probe scripts under
     `docs/probes/orun12/`:
     - real-mesh replay of the evaluation traces, for interpenetration and
       floor sinking;
     - per-leg heel share;
     - loop gap;
     - flight time.
  3. Run O3's asymmetry checks on v07-g1's best checkpoint:
     - left vs right per predicate;
     - a mirror test of the model and the clip.
  4. Read the clip itself:
     - the heel share, overreach, flight and lag it asks for, per leg;
     - whether the generator can express a longer stride and flight.
  5. Launch the next screen before analysing the last.
- **medium-term:**
  1. Close P1 and Q1, using the clip, the tracking weights, the heel and
     pin parameters and terminations, cold where a habit must be undone.
  2. Close P2:
     - fore cadence without taps;
     - overreach;
     - flight.
  3. Raise the speed command and clip to 5 m/s (S1), then beyond (S2).
     Measure what binds at each step: stride length against frequency,
     flight, and drives at peak by phase.
  4. Close Q2 on the passing policy. Fix the model's dynamics parameters
     only (O1) if the sim misbehaves.
- **long-term:**
  1. F1's films and R1's report, kept current as each criterion closes.
  2. The later criteria.
  3. Fold what this run proves into `training/RECIPE.md`:
     - a plantigrade clip on a linkage leg;
     - budget sizing;
     - a reward set that does not fight its clip;
     - the asymmetry checks.
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
- **The mechanism is locked (O1).** In `feline-v07/script.py`, edit only:
  - the task, clip, reward, observation and success sections;
  - the declared parameters' values;
  - joint dynamics;
  - materials' densities, friction and contact parameters.

  Never edit the part geometry, the drives or the joint layout.
- **One training run at a time on the 5090.** The machine lock is the
  arbiter. The CLI suite runs with the GPU hidden (`CUDA_VISIBLE_DEVICES=`).
- **v07-g1 belongs to the owner.** Never stop it. Wait for it to finish
  before training, and use its checkpoints.
- **Long training does not block an iteration.**
  - Start runs detached through `cadex_cli.loop` (`register`,
    `retain_training_view`, `launch`), so the dashboard follows them, and
    end the iteration. A later iteration reads the result.
  - Each run gets its own scope
    (`systemd-run --user --scope -p MemoryMax=30G ...`). Never use a
    transient service: it kills the trainer.
- **Keep the GPU busy.** Launch the next screen before a long rebuild,
  analysis or write-up.
- **The protocol and tool surface stay a contract** (AGENTS.md).
  - An engine change (a predicate, a generator option) gets an ADR from
    ADR-780, and the engine and CLI suites.
- **The dashboard stays read-only.** The actor may serve it on 127.0.0.1
  for its own tests. It never runs `tailscale serve` and never binds a
  public address.
- Committed images are PNG, ≤ 300 KB each, under `docs/probes/orun12/`, on
  the dark floor. Films live outside the repo and on the run's page.
- No role starts, stops or restarts the loop or signals its process. Kill
  stray engine processes by PID, never with a broad `pkill` pattern.

## Owner notes

- **The run's page is the owner's view.** The scribe keeps it. Each
  iteration it shows:
  - each criterion's latest judged numbers, left and right;
  - the top speed so far;
  - training curves;
  - the newest films or stills.

  Every training run is registered on the dashboard.
- **Gates run in the foreground** and finish within the shell's 10-minute
  limit. A rebuild takes 12–15 minutes and goes to the background.
- **Lean suites (ADR-725).** Add a test only for a contract or a regression
  that actually happened.
- **What came before:**
  - **v06-g1** (rigid metatarsus, sprung paw, PU shoe under the hock):
    - 0/10 pass;
    - 3.72 m/s best;
    - hock-down share at most 0.12, and 0 at the end;
    - only the left hind ever put its hock down;
    - the paw pin flapped at 900°/s;
    - the claws sank 8–16 mm into the floor;
    - the left hind paw passed through the left forearm.

    v07 adds paw damping, capsules for every limb and no hind lead in the
    clip.
  - **orun11 (rod-coupled foot):**
    - 5 screens, P1 0/10;
    - one leg lay down and the other never did;
    - fore taps at about 2x the hind stride on every heel clip.
  - **orun10 and orun11 together:** every reward rule added cost speed
    (4.21 → 3.20 m/s). The best speed on any cat was 4.64 m/s, on its toes.
  - **The trainer's reward is not a pass.** Judge with the engine.
  - **Warm starts:** use `--critic-warmup` (ADR-740), and about 3e-5 for a
    fine-tune.
- **Engine caps:**
  - 32 reward terms;
  - 128 observation channels;
  - 512 nodes per reward expression.

  The heel gait reference needs `heels` to point to bodies with their own
  collision geoms.
- `./cadex params` takes a repeated `--set k=v`.

## Question policy

- Resolve reversible choices autonomously, with the smallest measured step
  towards the highest-ranked open criterion. The order is B1, **P1 (the
  heel, O2a)**, Q2, P2, Q1, S1, S2.
- If the mechanism seems to be the limit, record the evidence and keep
  working the policy (O1). Never change hardware.
- Where O1–O9 and a measurement disagree, record both and follow O1–O9.
- Code and accepted artifacts outrank docs.
- A pre-existing test failure is recorded and left alone, unless the unit's
  own change touches it.
- A harness or usage limit is not an attempt: wait for capacity.
- Never invent a measurement, never weaken a spec to pass, and never wait
  for a human.

## Exhaustion policy

`report_done`.
- Once B1, P1, P2, Q1, Q2, S1, S2, F1 and R1 have evidence, write the
  closing report and claim done. Two consecutive critic acceptances stop
  the run.
- Until then, work the highest-ranked open criterion, then the later
  criteria. Past S1, keep pushing speed while P1, P2 and Q2 hold.
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
  - per-leg heel share;
  - fore and hind touchdown rates;
  - the top speed;
  - the worst drive's RMS over rated and its peak margin;
  - the checkpoint it started from.
- **The critic checks numbers at their source.** For every judged run, it
  opens at least one cited `evaluation.json` and checks the report against
  it.
- **The critic checks the heel on film or in a trace.** A P1 claim cites
  trace frames or a still that show both heels down.

## Reconcile

- The scribe folds every five work iterations, or at three unfolded
  records:
  - impacts applied;
  - statuses set with evidence;
  - `STATE.md` rendered;
  - `ouroboros mem check` clean.
- orun10's and orun11's open claims stay open and untouched. This run's
  S1 supersedes theirs in the report only.
- Unattended roles never edit this charter.
