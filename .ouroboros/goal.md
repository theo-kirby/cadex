# Goal: Finish the cat, and give legged robots a base model

Verified against source: 2026-10-17. Operator charter for orun9, following
orun8 (`.ouroboros/history/orun8.md`, merged at `8699109c`). The human owns
this file; unattended roles never edit it.

## Mission

orun8 made the ground: one drawn surface built from the physics shapes, a
floor that never ends, and moguls, rock, platforms, slopes and run-outs that
train in MJX (G1–G3, working). It did not finish the other two goals, and
this run picks them up:

1. **The cat (C).** One robust, unified policy on the newest cat
   (`0f036864`) that stands, balances, walks, runs, turns, reverses, runs to
   a point, crosses rough ground and jumps on and off a box, with an
   episode the owner can watch going from standing to running across
   changing ground.
   - orun8 got close on flat ground but passed nothing on all ten seeds.
   - Its best runs each failed a different bar: c1-t6 ran at 2.3–2.5 m/s
     against a 3 m/s command but over rated torque, and c1-t8 stayed within
     rated but lost speed.
   - It spent eight 150-iteration runs, each tuning one reward term.
2. **Base models (B).** Stop training every legged robot from nothing.
   - **Base models:** a quadruped base and a biped base that a new
     quadruped or biped fine-tunes from.
   - **Recipe:** for when a cold start is unavoidable, a written,
     evidence-backed recipe that makes it quick whatever the morphology.
   - orun8 spent under a tenth of its run on B. It left a recipe draft
     (`training/RECIPE.md`) and a two-foot gait reference (ADR-754).

If the loop achieves one thing, it is **C1 and C2 passing on one policy**.
B must not starve: O1 gives it a share of the GPU.

## Reference project

- `~/cadex-projects/orun8-cat` is this run's cat, at the `0f036864`
  geometry with the actor height scan (ADR-748) and the merged C1+C2 task
  (goals cmd, turn, nav, go; 11 reward terms).
  - Its working tree holds an uncommitted, never-launched c1-t9 change
    (`hinge_w` 8 → 3). Commit it or discard it on purpose.
  - Judge scripts and specs are in `~/orun8-progress/c1/` and `c2/`. The
    six specs are run, stand, shove, turn2, reverse and points.
- Checkpoints to start from (warm start keeps the normaliser, ADR-753):
  - c1-t6 (`ba432519`): the fastest, 2.3–2.5 m/s at a 3 m/s command; turn2
    3/10; over rated standing.
  - c1-t7: turn2 8/10; the waypoint reward fixed (golden-heron-9117).
  - c1-t8: within rated on every spec; run RMS 806 mm/s, stand drift
    291 mm, shove 10/10.
- `~/cadex-projects/orun8-biped` is the biped B1 started on, a copy of the
  servo biped, with the two-foot reference (ADR-754).
- Earlier quadrupeds and bipeds in `~/cadex-projects` (for example
  `quad-qdd`, `ot11-quad-1`, `biped-servo`, `biped-sts`) are read-only
  sources. Copy one to `orun9-*` to use it.

## Owner decisions

- **O1. C first, and B gets a share.**
  - Take the highest-ranked open criterion, C before B.
  - B's CPU work (B2's interface, the recipe, building and copying robots)
    proceeds while a cat run trains.
  - Once two consecutive judged cat runs pass no clause the run before did
    not, the next GPU run is a B run. Then return to C.
  - Once B2 lands, GPU runs alternate between C and B.
- **O2. The cat's policy may read the ground** (actor height scan,
  ADR-748).
- **O3. The newest model, `0f036864`.** Changing the cat's design to buy
  torque is a direction change. Record the evidence (which drive, what
  margin) and keep training on this model.
- **O4. Jumps are a ladder.** Boxes at 10, 20, 30, 40 and 50 cm. The
  criterion is clearing 20 cm up and down, and the report says the highest
  height cleared. 50 cm is about the withers and may be beyond the motors:
  say so with numbers rather than chase it.
- **O5. Physics stays on what MJX handles:** boxes, turned boxes, and
  buried spheres or ellipsoids (orun8's G courses). No heightfield
  (`winter-bay-5176`).
- **O6. Short training budgets, and more of them.**
  - A screen is 100 iterations, warm-started from the best checkpoint.
  - A full run is 200–300 iterations.
  - Extend by warm start only while the curve climbs.
  - Judge every checkpoint the run left (50, 100, …), not only the last.
- **O7. Base models need a common body.** A canonical per-family interface,
  for example per leg: hip abduction, hip, knee and ankle, plus body
  attitude and rates.
  - Each robot is mapped onto it.
  - A joint the robot lacks is empty.
  - A joint the base lacks (tail, spine, jaw) is a new output that starts
    at zero.
  - The base trains on a randomised family (segment lengths, masses, knee
    direction), not on one robot.
- **O8. Settle the torque-speed trade with measurements, not one guess per
  run.**
  - Before another reward edit, measure where each drive's RMS goes per
    spec segment on the checkpoints above.
  - Screen a change at several weights where it has one, as consecutive
    short screens.
  - A drive that cannot run 3 m/s within rated at any weighting is a
    finding to record. O3 of orun7 still holds: a sprint may exceed rated,
    never peak.

## Done criteria

### C — one cat (newest model `0f036864`, one policy file)

All C criteria are measured on the 10 frozen seeds with the engine's
evaluation (`cadex` predicates), not by the trainer's numbers. Drives stay
under peak torque always and within rated RMS except in a sprint.

- [ ] **C1. Stand, walk, run.**
  - **Standing:** commanded zero, the cat stands still and balances. It
    drifts less than 0.2 m in 10 s and survives the task's shoves.
  - **Speed tracking:** it follows a speed command re-sampled through the
    episode, from walking (≤ 0.5 m/s) to a run of at least 3 m/s, with RMS
    error ≤ 300 mm/s.
  - **Smooth changes:** it moves between stand, walk and run without
    falling.
- [ ] **C2. Turn, reverse, go to a point.**
  - **Turning:** it tracks yaw rates of ±60°/s.
  - **Reversal:** it makes a commanded 180° reversal, with heading error
    ≤ 20°.
  - **Targets:** it reaches a sequence of three target points 3–8 m apart,
    each within 0.3 m, in under 12 s.
  - **The tail:** it stays clear of the ground and is used in turns.
- [ ] **C3. Rough ground.** On held-out G courses at ≥ 1 m/s, the cat
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
    and shown on the run's page, in this order:
    1. standing;
    2. walking;
    3. running;
    4. bumps;
    5. up a box;
    6. down;
    7. a slope;
    8. a turn and a reversal.

### B — base models and the cold-start recipe

- [ ] **B1. The cold-start recipe.** `training/RECIPE.md` (orun8's
  draft) gives the steps that make a cold legged policy train quickly, each
  citing the run that proved it. It is proven by a cold walk on one new
  quadruped and one biped (Cadex projects, not the cat), each reaching a
  walk spec on 10 seeds within 300 iterations, following the recipe with no
  step invented on the spot. A step the proof changed is changed in the doc.
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

### R — the record

- [ ] **R1. Closing report.** `docs/probes/orun9/REPORT.md` covers:
  - C1–C5 with each predicate's numbers, the highest box, and what limits
    the cat (drive by drive);
  - B1–B4 with the fine-tune and cold curves side by side;
  - the torque-speed finding (O8);
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
  1. Decide c1-t9 (commit or discard `hinge_w=3`), and judge c1-t6/t7/t8's
     intermediate checkpoints on all six specs.
  2. O8's measurement: per drive, per spec segment, RMS over rated on c1-t6
     and c1-t8. Name the drive and the segment that bind.
  3. A weight screen of the effort price at 100 iterations each, warm from
     the checkpoint the measurement favours.
  4. B2's interface design and ADR, as CPU work while the screens train.
  5. Copy a quadruped and a biped for B1's proof to `orun9-*`; run B1's
     cold quadruped by the recipe as the first B GPU slot.
- **medium-term:**
  1. C1 and C2 passing on one policy, then a mild course for C3.
  2. B1 proven on the quadruped and the biped; the recipe updated.
  3. B2 in the trainer and `check_policy_fits`, with the cat mapped onto it.
  4. C3 on held-out G courses, then C4's box ladder.
- **long-term:**
  1. B3's randomised quadruped base and its fine-tune proof against B1's
     cold curve, then B4.
  2. C5's composed course and film.
  3. The later criteria, in their order, when the frontier above is empty.
  4. Keep every gate green, every doc true, `STATE.md` folded, and R1
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
  except `orun8-*` and `orun9-*`, which are this run's.

**This run:**
- **One training run at a time on the 5090.** The machine lock is the
  arbiter. The CLI suite runs with the GPU hidden
  (`CUDA_VISIBLE_DEVICES=`).
- **Long training does not block an iteration.**
  - An iteration may start a run detached, through `cadex_cli.loop`
    (`register`, `retain_training_view`, `launch`) so the dashboard follows
    it, and end; a later iteration reads the result.
  - Each training run longer than a smoke goes in a scope of its own
    (`systemd-run --user --scope -p MemoryMax=30G ...`).
- **Keep the GPU busy.** Launch the next training run before a long
  rebuild or judge, not after. A 20-minute rebuild of the cat's next
  revision happens while the current run trains.
- **A cat course is slow.** Measure the iteration time before committing a
  long run, and use `collides_with` (ADR-739). Rock and mixed courses cost
  about 5.5× flat (ADR-747).
- **The protocol and tool surface stay a contract** (AGENTS.md's rules).
- **The dashboard stays read-only.** The actor may serve it on 127.0.0.1
  for its own tests. It never runs `tailscale serve` and never binds a
  public address.
- Committed images are PNG, ≤ 300 KB each, under `docs/probes/orun9/`, on
  the dark floor.
- No role starts, stops or restarts the loop or signals its process.

## Owner notes

- **Gates run in the foreground.** Each finishes within the shell's
  10-minute limit. A rebuild that does not goes to the background, and the
  report says so.
- **The run's page is the owner's view.** The scribe keeps it. Each
  iteration it shows:
  - each criterion's state, with the latest judged numbers per spec;
  - training curves;
  - renders and rollout clips where a unit made them (stills or short
    videos copied into the page's assets, never committed).
  Every training run is also registered on the dashboard from its start,
  with its checkpoint rollouts (`run.json`, `retain_training_view`).
- **Lean suites (ADR-725).** Add a test only for a contract or for a
  regression that actually happened. Verify behaviour by running the thing.
- **What orun8 learned:**
  - Reward tuning one term per run trades one failure for another. Measure
    first (O8).
  - Cold restarts throw away progress. Change the task by warm start with a
    critic warm-up (`--critic-warmup`, ADR-740); the normaliser now carries
    across (ADR-753).
  - `points` failed because standing paid more than going. Evaluate a
    reward per step on the accepted bundle, standing against moving, before
    training on it.
  - 32 stock seeds are too few to compare rates under about 10%; use 128.
  - A task-change flag on an identical bundle is refused (c1-t4).
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
- Where O1–O8 and a measurement disagree, record both and follow O1–O8.
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
- Once C1–C5, B1–B4 and R1 have evidence, write the closing report and
  claim done. Two consecutive critic acceptances stop the run.
- Do not claim done while any criterion is unmet unless the run's
  wall-clock stop is near. Until then, work the highest-ranked open
  criterion under O1, then the later criteria.
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
- Every new channel, command kind, predicate, interface and trainer change
  has an ADR, starting at ADR-755.
- A judged training run is reported with each spec's pass count and the
  failing predicate's median, and the run it was warm-started from.
- The actor's report says what was measured. The scribe's record carries
  those numbers.

## Reconcile

- The scribe folds every five work iterations, or at three unfolded
  records: impacts applied, statuses set with evidence, `STATE.md`
  rendered, `ouroboros mem check` clean.
- **The first fold supersedes orun8's open claims.** These claims are replaced
  by this charter's criteria of the same names: C1 `gentle-star-3262`, C2
  `royal-ivy-2422`, C3 `cold-cloud-6642`, C4 `royal-tree-8817`, C5
  `tiny-oak-7862`, B1 `wild-forest-4815`, B2 `young-coast-4645`, B3
  `merry-ember-1465`, B4 `brave-sail-2650` and R1 `civic-tide-2630`. Carry
  their evidence (current text and citations) into the new gap claims, then
  mark the old ones superseded. Do not reopen the G claims, which are
  working.
- Unattended roles never edit this charter.
