# Goal: The cat's plantigrade gallop, from walk to full speed

Verified against source: 2026-10-18. Operator charter for orun11, following
orun10 (`.ouroboros/history/orun10.md`, merged at `59aebab9`) and the
owner's interactive session of 2026-10-18 on `orun10-cat` (runs t2-g1 to
t2-g5, notes below). The human owns this file; unattended roles never edit
it.

## Mission

The cat's hind foot is a paw **plus the metatarsus**, all the way up to
the hock. At speed a real cat lays that whole length on the ground, with
the hock drive itself on the floor behind the paw, and pushes off through
it. The slot in the back of the paw is there so the foot can lie flat. The
owner wants the cat to gallop like that, as fast as it can, and to get
there from a walk.

1. **The foot (M).** Replace the free paw pin with a **coupled linkage**:
   a rod or link that ties the paw's angle to the hock's, so the paw and
   metatarsus lie flat as the hock comes down for stance, and roll onto
   the toes at toe-off. The policy should get the plantigrade pose from
   the mechanism and the hock drive alone, not have to find a 96° fold of
   a free pin. On t2-g5 the hock case never reached the floor on the right
   leg and on 10 of 60 stance frames on the left.
2. **The policy design (P).** Show the policy the gait it should run,
   instead of describing it with rewards that fight the clip:
   - a reference gallop whose hind stance is plantigrade, with the hock on
     the floor at push-off;
   - front paws that reach forward and touch down once per stride, at the
     same cadence as the hind;
   - hind paws that land ahead of the front prints (the feline gallop);
   - the fewest reward terms that hold these, each one measured to pay
     for itself.
3. **Speed (S).** That gallop at **5 m/s or more**.
4. **Walk to gallop (W).** One policy that goes from an obvious
   alternating walk to the near-synchronous gallop as the speed command
   rises, always a rotary sequence, using ADR-773's speed-scheduled
   reference.

If the loop achieves one thing, it is **a plantigrade gallop: the whole
hind foot flat on the ground with the hock drive down at push-off, on both
legs, every stride**, measured and filmed.

## Reference project

- `~/cadex-projects/orun10-cat` at `2729c141` (the owner session's
  `cat14.py`) is the source:
  - the faceted-soft head;
  - AK60-6 front wrists;
  - thicker pads with round backs;
  - the free plantigrade pin (−24..+100°);
  - hock and metatarsus floor contacts;
  - the 17-term gallop task (`fore_tap`, `plantigrade`, `fore_reach`,
    `hind_overreach`, `fore_sync`, `hind_flat` and the rest).

  Copy it to `~/cadex-projects/orun11-cat` and work there. Earlier
  projects are read-only.
- **Runs t2-g1 to t2-g5** in `orun10-cat/runs/` are the baseline. The
  owner's measurement scripts live in the session scratchpad and are not
  committed; rebuild what you need as engine predicates or as scripts
  under `docs/probes/orun11/`. Their measures:
  - hind flat share and pin-at-stop;
  - hock-down share of hind stance;
  - touchdowns per second per paw;
  - hind overreach of the fore prints.
- **Speed records:**
  - **4.64 m/s:** t1-g3 iteration 75, on the cat before the paw changes.
  - **4.49 m/s:** orun10's s1-g4.
  - **3.79 m/s:** t2-g4.
  - **3.20 m/s:** t2-g5.
- ADR-773 (`36653832`) gives the speed-scheduled gait: `assembly.goal(kind="speed", ...)` and `assembly.task(..., reference=[slowest, ..., fastest])`. It has been tested only on a scratch project.
- `training/RECIPE.md` is the cold-start recipe.

## Owner decisions

- **O1. Order:** M, then P and S together, then W.
  - CPU work for a later item (clips, specs, the W schedule) may proceed
    while a run trains.
  - The gallop is not done until it is plantigrade (P1). A faster gallop
    on its toes does not count.
- **O2. The foot is a coupled linkage.**
  - One link, rod or four-bar ties the paw to the shank or the hock, so
    the hock drive alone sets the foot's pose. A compliant element is
    allowed if a measurement shows it is needed: a spring in the rod, or a
    little lost motion at toe-off.
  - It is a real, buildable part:
    - bearings or bushings at every pin;
    - rods and links sized for the push-off load;
    - every part through fit, mounting, panels and sweep.
  - An `equality/joint` coupling with no physical part is a modelling
    shortcut, not the design. Use one only to screen a ratio before the
    part exists, and say so.
- **O3. Redesign scope: the legs and the spine.**
  - Anything in the four legs or the spine that a measurement says limits
    the gallop may change: geometry, drives, gear ratios, pads.
  - orun10 found the spine at its 22 N·m peak in 37% of frames at a
    3.0 Hz clock.
  - The head, tail and body shell stay unless a leg change forces a
    mounting change.
  - Every drive is one that is sold.
- **O4. Torque.** Drives never exceed peak. Rated RMS is **reported, not
  enforced**. Every number reported carries the worst drive's RMS over
  rated and its peak margin.
- **O5. Track, don't describe.** The reference clip carries the gait:
  - plantigrade hind stance;
  - fore reach;
  - hind overreach;
  - matched fore and hind cadence;
  - the rotary lag.

  Rewards back the clip up; they do not argue with it. t2-g5 showed a
  `plantigrade` term (w4) losing to a tiptoe clip tracked at w10. Before
  adding a term, evaluate it per step on the accepted bundle (the gait
  against its absence). Keep a term only if a judged run shows it moved
  its measure.
- **O6. Straight lines, flat ground.** No turning, leaping or terrain this
  run.
- **O7. Short screens, many of them.**
  - A screen is 100–150 iterations.
  - A full run is 200–300.
  - Warm-start where the actor's inputs allow; a mechanism change trains
    cold.
  - Extend only while the curve climbs.
  - Judge every checkpoint a run leaves.
- **O8. Size the budget to the model.** t2-g5 ran out of its 7200 s at
  iteration 235 of 300, because the new floor contacts slowed each step.
  Time the first ten iterations of each new bundle, then set `budget_s` to
  cover the iterations asked for, plus a margin.

## Done criteria

Every criterion is measured on 10 frozen seeds with the engine's
evaluation, not the trainer's numbers. Drives always stay under peak (O4).
Stance and contact shares are measured over the evaluation window and
exclude the first second.

- [ ] **M1. The coupled foot is built.**
  - On `orun11-cat`, the hind paw is driven by a coupled linkage (O2).
  - It passes fit, mounting, panels and sweep across the hock's whole
    range.
  - **A static check** in the gait reference's stance pose, with the cat
    standing on flat ground, shows that at push-off:
    - the paw sole is flat (pitch within 8° of the floor);
    - the hock drive's case is within 10 mm of the floor.
  - The report gives:
    - the paw-to-hock coupling curve (paw angle against hock angle) over
      the full range;
    - the link loads at a 3× body-weight push.
- [ ] **P1. Plantigrade push-off, every stride.** On the fastest
  plantigrade gallop policy, on at least 8 of 10 seeds, for **each** hind
  leg:
  - the hock drive's case is on the floor for at least 40% of that paw's
    stance;
  - it is on the floor at the moment of toe-off or just before it.

  Measure this with an engine predicate (a new ADR if one is needed), not
  only an offboard script. Report the share and the hock case's median
  stance height for each leg.
- [ ] **P2. The feline gallop's form.** On the same policy, on 8 of 10
  seeds:
  - each front paw touches down at the hind paws' stride frequency,
    within 10%: no mid-swing tap (t2-g4 tapped at 4.74 Hz against 2.37);
  - each front paw touches down ahead of the shoulder by a measured reach;
  - the hind paws land ahead of the front paw prints, with the median
    overreach reported;
  - the footfall order is rotary.
- [ ] **S1. 5 m/s, plantigrade.**
  - A straight-line sprint that holds at least **5 m/s** over a 2 s window
    on at least 8 of 10 seeds, without falling, by a policy that also
    passes P1.
  - The report gives:
    - the highest 2 s average on any seed;
    - the median over the 10 seeds;
    - stride length, stride frequency and flight time per stride.
  - Falling short is recorded honestly, with what binds: which drive,
    which phase of the stride, and by what margin.
- [ ] **W1. Walk to gallop.**
  - **The task:** one policy, trained on an ADR-773 speed-scheduled
    reference of three or more strides, from a walk of about 0.5 m/s to
    the fastest gallop that passes P1.
  - **The test:** a command ramp from the walk to that gallop, on 8 of 10
    seeds, without falling. The policy tracks the command within 15% once
    it has settled, at every step of the schedule.
  - **The gait:**
    - the footfall order stays rotary throughout;
    - the lag within each pair falls steadily, from about 0.5 of the
      cycle at the walk (plainly alternating) to 0.15 or less at the
      gallop (nearly together);
    - the report plots each pair's lag against speed.
- [ ] **F1. The films**, on the run's page:
  - the plantigrade gallop, side-on and close on a hind foot, at full
    speed and in slow motion;
  - the walk-to-gallop ramp, side-on;
  - the coupled foot's mechanism through its range.
- [ ] **R1. The closing report.** `docs/probes/orun11/REPORT.md` gives:
  - each criterion with its numbers;
  - the foot's design and why;
  - which reward terms earned their place, and which were cut;
  - what limits speed, drive by drive;
  - what the next run should try.

## Later criteria

Not this run's; for when the frontier above is empty:
- The walk-to-gallop policy also decelerates back to a walk, still rotary.
- The plantigrade gallop at 5.5 m/s or more.
- The coupled foot used for a standing leap (orun10's J1 ledge).

## Horizon ladder

- **short-term:**
  1. Copy `orun10-cat` to `orun11-cat`.
  2. Turn the owner session's measures into engine predicates for a flat
     sprint spec:
     - hock-down share of stance;
     - paw flatness;
     - touchdown rate per paw;
     - hind overreach;
     - pair lag.
  3. Judge t2-g4 and t2-g5 on that spec as the baseline.
  4. Sketch two or three coupled-foot linkages on paper or in a scratch
     project: a rod from the shank, a four-bar off the hock housing, a
     tendon-like link. Check each one's coupling curve against the
     plantigrade pose: paw pin about +96° at metatarsus −60°, and on the
     toes at toe-off.
  5. Build the best linkage on `orun11-cat`, through every verdict and
     M1's static check.
  6. Write a gallop reference whose hind stance is plantigrade, which the
     generator can reach. Fix the generator if it cannot express the
     pose, under an ADR.
- **medium-term:**
  1. Cold screens on the coupled foot with the plantigrade clip, using the
     smallest reward set that holds the form. Cut terms that fail O5's
     test.
  2. Close P1 and P2, then push the speed command upward for S1.
  3. Measure what binds at speed (O8 of orun10: stride length against
     frequency, flight, drives at peak by phase). Change a leg or spine
     drive or ratio only when a measurement names it (O3).
  4. W1:
     - a slow walk clip and a canter clip on the same legs;
     - the speed schedule;
     - a cold run;
     - the ramp spec.
- **long-term:**
  1. F1's films and R1's report, kept current as criteria close.
  2. The later criteria.
  3. Fold what this run proves into `training/RECIPE.md`: the plantigrade
     clip, budget sizing, and a reward set that does not fight its clip.
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
  except `orun11-*`, which are this run's.

**This run:**
- **One training run at a time on the 5090.** The machine lock is the
  arbiter. The CLI suite runs with the GPU hidden
  (`CUDA_VISIBLE_DEVICES=`).
- **Long training does not block an iteration.**
  - Start a run detached through `cadex_cli.loop` (`register`,
    `retain_training_view`, `launch`), so the dashboard follows it, and
    end the iteration. A later iteration reads the result.
  - Each run goes in a scope of its own
    (`systemd-run --user --scope -p MemoryMax=30G ...`). Never use a
    transient service: it kills the trainer.
- **Keep the GPU busy.** Launch the next screen before a long rebuild,
  analysis or write-up, not after. orun10 sat idle for 35 minutes between
  judgments.
- **The protocol and tool surface stay a contract** (AGENTS.md's rules).
- **The dashboard stays read-only.** The actor may serve it on 127.0.0.1
  for its own tests. It never runs `tailscale serve` and never binds a
  public address.
- Committed images are PNG, ≤ 300 KB each, under `docs/probes/orun11/`,
  on the dark floor. Films live outside the repo and on the run's page.
- No role starts, stops or restarts the loop or signals its process. Kill
  stray engine processes by PID, never with a broad `pkill` pattern.

## Owner notes

- **The run's page is the owner's view.** The scribe keeps it. Each
  iteration it shows:
  - each criterion's latest judged numbers: hock-down share per leg,
    touchdown rates, the top speed so far;
  - training curves;
  - the newest films or stills, copied into the page's assets and never
    committed.

  Every training run is also registered on the dashboard, with its
  checkpoint rollouts.
- **Gates run in the foreground** and finish within the shell's 10-minute
  limit. A rebuild that does not goes to the background.
- **Lean suites (ADR-725).** Add a test only for a contract or a regression
  that actually happened.
- **What the owner session of 2026-10-18 learned** (t2-g1 to t2-g5):
  - A free paw pin lets the paw lie flat, but the policy uses it only half
    the time and parks it at its stops 30–90% of stance. Range is not the
    same as the pose.
  - The hock never touched the floor until floor contacts were declared on
    the hock case and metatarsus, and even then it did so on one leg only.
  - Front paws tapped once mid-swing every stride, after lifting only
    10–20 mm. A contact-timing weight of 10 did not stop it. A penalty on
    fore contact while the clip says swing (w8) brought one paw to the
    clip's 2.37 Hz; the other stayed at 3.2 Hz.
  - Each rule added made the gallop slower (4.21 → 3.79 → 3.20 m/s). That
    argues for O5: put the form in the clip.
  - **Engine caps:**
    - 32 reward terms (ADR-773);
    - 128 observation channels (`MAXIMUM_OBSERVATION_CHANNELS`);
    - 512 nodes per reward expression.

    t2-g5 dropped the tail-link contacts to fit 128.
  - `./cadex params` takes a repeated `--set k=v`, not a comma list.
- **What orun7 to orun10 learned:**
  - The trainer's reward is not a pass. Judge checkpoints with the engine.
  - Warm-start with a critic warm-up (`--critic-warmup`, ADR-740). A
    fine-tune from another policy needs a low learning rate (about 3e-5).
  - Removing a blocker does not undo a habit the policy has converged on.
    After a task or mechanism fix, train cold.
  - Speed is set by the clip's clock and stride length; the spine binds as
    the clock rises.
  - Write each criterion's closing note when it closes, not at the end.

## Question policy

- Resolve reversible choices autonomously, with the smallest measured step
  towards the highest-ranked open criterion (O1).
- **Is it real hardware?** A sensor no one sells is privileged; a drive no
  one sells is refused. A linkage part must be makeable: printed, machined
  or bought.
- If the coupled foot cannot reach both the plantigrade pose and toe-off,
  pick the linkage that gets the plantigrade push-off right (P1) and record
  what toe-off costs.
- Where O1–O8 and a measurement disagree, record both and follow O1–O8.
- Code and accepted artifacts outrank docs.
- A pre-existing test failure is recorded and left alone, unless the unit's
  own change touches it.
- A harness or usage limit is not an attempt: wait for capacity.
- Never invent a measurement, never weaken a spec to pass, and never wait
  for a human.

## Exhaustion policy

`report_done`.
- Once M1, P1, P2, S1, W1, F1 and R1 have evidence, write the closing
  report and claim done. Two consecutive critic acceptances stop the run.
- Until then, work the highest-ranked open criterion, then the later
  criteria. Past S1, keep pushing the top speed while it climbs and P1
  holds.
- If the stop arrives first, report how far each criterion got. Do not
  redefine success.

## Quality bar

- At every accepted commit that touches code, run:
  - `pixi run test-engine`;
  - `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`;
  - for `training/` changes, its tests from `~/cadex-train-venv`.
- Python changes under `src/Mod/cadex/` need `pixi run build-engine` before
  the CLI's engine-needing tests count.
- Every new channel, predicate, joint kind, generator change and trainer
  change has an ADR, starting at ADR-774 (check `docs/DECISIONS.md`).
- A judged run is reported with:
  - each spec's pass count;
  - the failing predicate's median;
  - the hock-down share per hind leg;
  - the fore and hind touchdown rates;
  - the top speed;
  - the worst drive's RMS over rated and its peak margin;
  - the checkpoint it started from.
- **The critic checks numbers at their source.** For every judged training
  run, the critic opens at least one `evaluation.json` the report cites,
  and checks its pass counts and medians against the report.
- **The critic checks the foot on film or in the trace.** A P1 claim cites
  the trace frames, or a still, showing the hock case on the floor.

## Reconcile

- The scribe folds every five work iterations, or at three unfolded
  records:
  - impacts applied;
  - statuses set with evidence;
  - `STATE.md` rendered;
  - `ouroboros mem check` clean.
- orun10's open S1, S2, J1–J3, F1 and R1 claims stay open and untouched:
  this run's S1 supersedes orun10's S1 in the report only.
- Unattended roles never edit this charter.
