# Goal: The cat at full gallop, and leaping

Verified against source: 2026-10-17. Operator charter for orun10, following
orun9 (`.ouroboros/history/orun9.md`, merged at `bdaf363e`). The human owns
this file; unattended roles never edit it.

## Mission

A simpler run than the last two. The owner wants to see the cat go **as
fast as it possibly can in a straight line**, and **leap**: up onto a
ledge, off it, and from platform to platform. How it gets there is the
agent's call.

1. **Speed (S).** Gallop to the absolute maximum on the newest cat
   (`0f036864`).
   - The owner expects 5 m/s or more to be reachable.
   - orun7's gallop reached 4.15–4.20 m/s (f1-g2/f1-g3, at about 2.5×
     rated torque, on an earlier revision).
   - orun9 showed that the trot clock, not the torque, capped the cat's trot
     near 2.4 m/s.
   - A real gallop, with a flight phase and a long, fast stride, is the way
     past it.
2. **Leaping (J).** On a straight course of boxes and platforms, the cat:
   - leaps up onto a ledge and runs across it;
   - leaps off it, or over a gap to the next platform;
   - lands running.
   Ledges from 0 to 1 m tall would be the owner's dream. Find out how high
   this cat can go, and say so with numbers.

If the loop achieves one thing, it is **the fastest gallop this cat can
run**, measured and filmed.

## Reference project

- `~/cadex-projects/orun8-cat` is the source: the newest cat at `0f036864`,
  with the actor height scan (ADR-748). Copy it to
  `~/cadex-projects/orun10-cat` and work there. Earlier projects are
  read-only.
- `~/cadex-projects/orun7-cat` runs f1-g2 and f1-g3 hold orun7's gallop:
  its reference gait, reward and task. Their traces show what the gait
  looked like.
- orun8's ground (ADR-743 to ADR-747) has platforms, run-outs and a 50 cm
  box kind that trains in MJX. orun8's C4 box-ladder spec is declared in the
  memory (`royal-tree-8817`).
- `training/RECIPE.md` is the proven cold-start recipe (orun9 B1).

## Owner decisions

- **O1. Speed first, then leaping.** Take the highest-ranked open criterion.
  Leaping work on the CPU (courses, specs, reference motions) may proceed
  while a sprint trains.
- **O2. This model.** The cat stays `0f036864`, with no redesign to buy
  speed. If a drive is what limits it, record which drive, at what speed and
  by what margin, as a finding for the owner.
- **O3. Torque.**
  - Drives never exceed peak (the actuator limit).
  - Rated RMS is **reported, not enforced**, in a sprint or a leap: the
    owner wants the limit of the machine.
  - Every number reported carries the worst drive's RMS over rated and its
    peak margin.
- **O4. Separate policies are fine.** A sprint policy and a leaping policy
  may be separate files. One policy that does both is a bonus, not a
  requirement.
- **O5. Straight lines.** No turning, standing or go-to-a-point specs this
  run. Courses run along +x.
- **O6. Try the outside-hind gallop.** The owner suggests a stride where the
  hind feet swing *outside* the forefeet and land ahead of them, as a
  greyhound or cheetah does.
  - It is not mandatory, and it may not suit this body.
  - Try it on purpose and measure it: the hind-fore lateral offset at the
    pass, where the hind lands relative to the fore, and the speed.
  - Record whether it helps.
- **O7. Short screens, many of them.**
  - A screen is 100 iterations, warm-started from the best checkpoint where
    the actor's inputs allow.
  - A full run is 200–300 iterations.
  - Extend only while the curve climbs.
  - Judge every checkpoint a run leaves, not only the last.
- **O8. Measure before tuning.** Before another reward edit, measure what
  binds:
  - stride length against stride frequency;
  - flight time;
  - which drive is at peak, in which part of the stride.
  orun9 showed that one measurement can rule out several dead levers.

## Done criteria

All criteria are measured on 10 frozen seeds with the engine's evaluation
(`cadex` predicates), never by the trainer's numbers: on flat ground for S,
and on the J course for J. Drives stay under peak always (O3).

- [ ] **S1. Top speed.** A straight-line sprint where the cat holds at
  least **5 m/s**, averaged over a 2 s window, on at least 8 of 10 seeds,
  without falling.
  - The report gives the highest 2 s average reached on any seed, and the
    median over the 10 seeds, whatever they are.
  - Falling short of 5 m/s is recorded honestly, with what limits it (O8).
- [ ] **S2. It is a gallop.** The fastest S1 policy's stride has a flight
  phase every stride (all four feet off the ground), measured by the
  engine's contact metrics. The report gives:
  - flight time per stride;
  - stride length and frequency;
  - the footfall order.
- [ ] **S3. The outside-hind stride, tried.** O6's stride is trained on
  purpose, either as its own reference or as a reward term, and judged on:
  - the hind feet's lateral offset outside the forefeet at the pass;
  - where they land relative to the forefeet;
  - its top speed against S1's.
  It passes either way once it is measured and filmed. A clear result that
  it does not suit this body counts.
- [ ] **J1. Up and down.**
  - **The course:** straight, with a run-up, a ledge, a platform at least
    1 m long, and a drop back to the ground.
  - **The bar:** the cat leaps up onto and off a ledge of at least **30 cm**,
    on at least 8 of 10 seeds, and lands without falling.
- [ ] **J2. The ledge ladder.** Ledges at 20, 40, 60, 80 and 100 cm.
  - The report gives the highest ledge the cat climbs on 8 of 10 seeds,
    with:
    - the take-off speed;
    - the jump's peak height;
    - the worst drive's peak margin at take-off.
  - 1 m is about twice the withers. Say with numbers why it does or does not
    get there.
- [ ] **J3. Platform to platform.**
  - **The course:** a straight line of platforms of mixed heights (0–1 m),
    with gaps between them.
  - **The bar:** the cat crosses at least three platforms, leaping each gap
    (at least 0.5 m) without touching the ground between them, on at least
    8 of 10 seeds.
  - The report gives the widest gap cleared.
- [ ] **F1. The showcase.** Films on the run's page:
  - the fastest sprint, side-on, at full speed;
  - the outside-hind attempt (S3);
  - a leap up, across and off the highest ledge cleared;
  - a platform-to-platform run.
- [ ] **R1. Closing report.** `docs/probes/orun10/REPORT.md` gives:
  - S1–S3 and J1–J3, with every number above;
  - what limits the cat, drive by drive;
  - what the next run should try.

## Later criteria

Not this run's; for when the frontier above is empty:
- One policy that sprints and leaps on the same course.
- Leaping on rough ground (orun8's moguls and rock) at speed.

## Horizon ladder

- **short-term:**
  1. Copy `orun8-cat` to `orun10-cat`. Write a flat sprint spec: speed over
     a 2 s window, contact metrics, drives under peak. Judge orun7's f1-g3
     and orun9's fastest checkpoint on it as the baseline.
  2. O8's measurement of what caps speed today: stride length, frequency,
     flight, drives at peak.
  3. A gallop reference for the sprint on this model's legs, with a flight
     phase, and the first 100-iteration screens at a rising speed command.
  4. The J course in the engine, as orun8's box kinds:
     - a run-up, a ledge, a platform and a drop;
     - the ledge ladder;
     - gapped platforms.
- **medium-term:**
  1. S1 by screens and warm starts, pushing the commanded speed up while the
     cat keeps up.
  2. S3's outside-hind stride, screened against S1's best.
  3. J1 on a 30 cm ledge, with the height scan and a run-up speed that suits
     a leap. Then the J2 ladder upward.
  4. J3's platforms and gaps.
- **long-term:**
  1. F1's films and R1's report.
  2. The later criteria.
  3. Keep every gate green, every doc true, `STATE.md` folded, and R1
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
- Do not hand-edit `STATE.md`, `PLAN.md` or state claims.
- **Keep earlier projects read-only:** every project in `~/cadex-projects`
  except `orun10-*`, which are this run's.

**This run:**
- **One training run at a time on the 5090.** The machine lock is the
  arbiter. The CLI suite runs with the GPU hidden
  (`CUDA_VISIBLE_DEVICES=`).
- **Long training does not block an iteration.**
  - Start a run detached through `cadex_cli.loop` (`register`,
    `retain_training_view`, `launch`), so the dashboard follows it, and end
    the iteration. A later iteration reads the result.
  - Each run goes in a scope of its own
    (`systemd-run --user --scope -p MemoryMax=30G ...`). Never use a
    transient service: it kills the trainer.
- **Keep the GPU busy.** Launch the next run before a long rebuild or
  judge, not after.
- **A course is slow.** Measure the iteration time before a long run on a
  course, and use `collides_with` (ADR-739).
- **The protocol and tool surface stay a contract** (AGENTS.md's rules).
- **The dashboard stays read-only.** The actor may serve it on 127.0.0.1
  for its own tests. It never runs `tailscale serve` and never binds a
  public address.
- Committed images are PNG, ≤ 300 KB each, under `docs/probes/orun10/`, on
  the dark floor. Films live outside the repo and on the run's page.
- No role starts, stops or restarts the loop or signals its process.

## Owner notes

- **The run's page is the owner's view.** The scribe keeps it. Each
  iteration it shows:
  - each criterion's latest judged numbers (the top speed so far, the
    highest ledge so far);
  - training curves;
  - the newest films or stills, copied into the page's assets and never
    committed.
  Every training run is also registered on the dashboard, with its
  checkpoint rollouts.
- **Gates run in the foreground** and finish within the shell's 10-minute
  limit. A rebuild that does not goes to the background.
- **Lean suites (ADR-725).** Add a test only for a contract or a regression
  that actually happened.
- **What orun7 to orun9 learned:**
  - The trainer's reward is not a pass. Judge checkpoints with the engine.
  - Warm-start with a critic warm-up (`--critic-warmup`, ADR-740); the
    normaliser carries across (ADR-753). A fine-tune from another policy
    needs a low learning rate (about 3e-5), or its first update wipes it.
  - A spec can fail for its setup, not the policy (the stand spec's trot
    start). Look at a failing spec's first second before tuning for it.
  - Evaluate a new reward per step on the accepted bundle (going against
    not going) before training on it.
  - A reward that describes a gait buys its cheapest exploit. Prefer
    tracking a reference.
- **Engine limits** (raise one only with an ADR):
  - a reward expression holds at most 512 nodes;
  - a task holds at most 16 reward terms.

## Question policy

- Resolve reversible choices autonomously, with the smallest measured step
  towards the highest-ranked open criterion (O1).
- **Is it real hardware?** A sensor no one sells is privileged; a drive no
  one sells is refused. The actor's height scan is allowed.
- Where O1–O8 and a measurement disagree, record both and follow O1–O8.
- Code and accepted artifacts outrank docs.
- A pre-existing test failure is recorded and left alone, unless the unit's
  own change touches it.
- A harness or usage limit is not an attempt: wait for capacity.
- Never invent a measurement, never weaken a spec to pass, and never wait
  for a human.

## Exhaustion policy

`report_done`.
- Once S1–S3, J1–J3, F1 and R1 have evidence, write the closing report and
  claim done. Two consecutive critic acceptances stop the run.
- Until then, work the highest-ranked open criterion, then the later
  criteria. Past S1, keep pushing the top speed while it climbs.
- If the stop arrives first, report how far each criterion got. Do not
  redefine success.

## Quality bar

- At every accepted commit that touches code, run:
  - `pixi run test-engine`;
  - `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`;
  - for `training/` changes, its tests from `~/cadex-train-venv`.
- Python changes under `src/Mod/cadex/` need `pixi run build-engine` before
  the CLI's engine-needing tests count.
- Every new channel, predicate, ground kind and trainer change has an ADR,
  starting at ADR-771 (ADR-761 to ADR-769 may be taken by a branch; check `docs/DECISIONS.md`).
- A judged run is reported with:
  - each spec's pass count;
  - the failing predicate's median;
  - the top speed or ledge height;
  - the worst drive's RMS over rated and its peak margin;
  - the checkpoint it started from.
- **The critic checks numbers at their source.** For every judged training
  run, the critic opens at least one `evaluation.json` the report cites, and
  checks its pass counts and medians against the report.

## Reconcile

- The scribe folds every five work iterations, or at three unfolded
  records:
  - impacts applied;
  - statuses set with evidence;
  - `STATE.md` rendered;
  - `ouroboros mem check` clean.
- orun9's open C and B claims stay open and untouched: this run does not
  work them.
- Unattended roles never edit this charter.
