# hex2 — gaps observed

Second unassisted attempt. Identical prompt and flags to hex1; one change:
`CADEX_EFFORT=medium` (hex1 ran at the default `high` and stalled in four
consecutive 32k-token thinking passes — see `../hex1-notes/GAPS.md`).
Launched 2026-09-25 from `main` @ `4289ef0f`. Observe only.

## Log
- **18:52 — same first two failures as hex1, reproduced exactly**: `import`
  then `repr` rejected by the xscript sandbox; plus a new one, guessing a
  `lib.servo.horn` style name. Deterministic, so the authoring contract
  (`describe_api`) is not telling the agent what the sandbox forbids.
- **18:53–19:01 — API guessing, recovered each time**: `getattr` blocked;
  `inspect` pointer `/facts/bounding_box` doesn't exist (asked twice);
  `ServoPart.horn()` called with wrong arity. Recoverable, but every one is a
  round-trip the contract could have prevented.
- **19:01 — the whole-script guard caught a drop** (script would have removed
  `horn_body`, `servo_body`). Guard worked as designed — not a gap, noted as a
  good behaviour.
- **19:05 — first real design (12 KB) rejected**: `assembly.component source
  must be a part or partdesign value created in this script`. Agent's reading
  of how catalog servos enter an assembly was wrong; the contract didn't say.
- **19:05 — a failed candidate can't be edited.** `edit_script` targets the
  accepted source, not the rejected candidate, so the fix needs a full 12 KB
  resend ("The failed candidate isn't the editable source — I'll rewrite in
  full"). Each full rewrite cost ~10 min of model time (19:05 → 19:15).
- **19:15 — second full design rejected**: `An Assembly program must return
  exactly one assembly and one solver_diagnostics output`. Another structural
  rule discovered by failing.
- **19:16–19:18 — two more assembly-shape rules found by failing**: every
  listed component returned exactly once; component links must be returned.
- **19:18 — task pre-check caught reset variation driving 4.12 mm into the
  floor.** Good behaviour: the product rejected an unbuildable task before
  training. Agent fixed it by raising reset drop height to 5–9 mm.
- **19:22 — first accepted hexapod design**: 38 components (floor, body plate,
  6 × {hip servo, hip horn, knee servo, knee horn, femur, tibia}) plus the
  `walk_forward` task. ~30 min and ~7 full-script writes from the prompt.
- **19:33–19:55 — fixing fit via targeted edits (good), then a suspected
  engine defect.** Setting `hip_pitch=48` — inside the parameter's own
  declared range (40–48) — fails deterministically with "The MJCF exported for
  assembly output 'hexapod' changed body_pos by 1 relative; the accepted
  maximum is 1e-05" (DOMAIN_CANDIDATE_FAILED, stage mjcf_model). 47 is
  accepted. A *relative* change of exactly 1 smells like a pose sign/frame bug
  in export verification (cf. the weld inverse-pose bug on salty-isle-4063),
  not a design problem. Agent first mis-diagnosed it as a nondeterministic
  settle and retried (3 × ~2.7 min), then bisected correctly. **Needs a repro
  on the engine side after the run.**
- **Rebuild cost: ~2.7 min per candidate** on 38 components / 12 swept joints,
  so every design round-trip is minutes. Dominant cost of the design phase.
- **Watch tooling gap (mine, and the product's):** the walk log writes an
  accepted-revision line only when the *next* event starts it, so a tail on
  stderr misses acceptances. No stable, line-per-event progress stream.
- **20:08 — design leg finished, 1h16m after the prompt.** Final `6a8ebe73`:
  38 components, 12× MG90S + 12 horns all catalogued, sweep pass on 12
  joints, 24/24 welds touching; static fit reports "1 failing of 703", which
  the agent explains as the documented floor/world-geometry advisory row.
  **Presentation gap:** the one-line verdict says `fit fail` while the agent
  (correctly, if its reading holds) says 0 intersections — a user sees "fail".
  Verify that row after the run.
- **Task is ambitious from step 0**: +X COM velocity reward, lateral/height
  penalties, mass randomisation, tilted/lifted/moving starts AND mid-episode
  shoves, all in the first task. No curriculum. Watch whether PPO learns
  anything at all; if not, that's a "task authoring" gap, not a trainer one.
- **Modelling omissions stated by the agent**: servo tab screws not modelled;
  2-DoF legs (hip yaw + knee lift) as the prompt asked.
- **20:09–20:14 — train leg spent ~5 min rebuilding/exporting before the GPU
  started.** Training started 20:14:12 UTC on `gpu`.
- **20:34 — training ETA ~3.5 h** for 2000 × 2048 on a 5090 (~6.9 s/iter,
  trainer's own `eta_s` 12693). Episode cap 500 steps (10 s at 50 Hz).
  At iter 147: reward/step −2.1 → +4.8, mean episode 198 steps (up from
  ~40 early) — it is learning *something*; whether that's walking or
  lurching forward before falling is unknown until the rollout.
- **No mid-training look at behaviour.** Only scalar curves until the walk's
  rollout at the end; nothing renders a checkpoint while it trains, so a
  degenerate gait costs the full 3.5 h to discover.
- **21:09 — iter 502: reward/step climbing (+8.65) but episode length flat
  at ~190–245 steps since iter ~40** (of a 500 cap). The policy earns more
  per step without surviving longer — consistent with lunging forward faster
  and still collapsing (`com_z < 25.5` mm, 13 mm below stance) around 4 s.
  Nothing in the product surfaces "reward up, survival flat" as a warning;
  you have to read two curves against each other.

## Owner observations (21:30, while training)

- **O1. The printed parts look bad** — boxes and bars, sharp edges, no
  fillets, spheres stuck on bars, no design language. Close-ups in
  `shots/` (iso, front_low, top, leg_close). Confirmed and extended:
  - **The design agent cannot see its work.** Its tool surface
    (`cli/cadex_cli/tools.py` CLI_TOOL_OPS) has no render/look op; hex2's
    turn used inspect×26, write×13, edit×10, describe×4, rebuild×1 and
    never saw an image. `cadex render` exists, but only as a subcommand.
  - Rotational rather than mirror symmetry: every knee servo sits on the
    same side of its leg.
  - Hip servo cases hang below the plate; belly clearance is small.
  - The floor is a design component, so the viewer's Fit frames the floor
    and the robot looks tiny.
- **O2. There is no brain, power, driver or sensors.** The catalog already has
  an ESP32, a Pi Zero 2 W and a PCA9685, but nothing was used — the prompt
  didn't ask and the contract doesn't expect a complete robot. It has no battery
  or regulator, and the catalog has no IMU or battery family.
- **O2b. Observations aren't grounded in sensors.** The task observes joint
  q/dq, COM position and COM velocity. The MG90S has no position feedback, and
  nothing on board measures COM velocity, so the policy trains on state the
  real robot can't have.

## Outcome of walk1 (finished ~03:25 UTC, 2026-09-26)

- **Training completed 2000/2000** (13,303 s ≈ 3.7 h). Final reward/step
  ~12.2, mean training episode still ~215 of 500 steps — flat since iter 40.
  Best checkpoint e0b37d84; witness agrees to 1.65e-7.
- **Declare and rollout legs passed; review leg FAILED: "render: triangle
  budget exceeded".** Same 100k-triangle cap fixed on hex/fixes (ADR-406) —
  the bug cost this run its review, not just `cadex render`.
- **The seed-0 rollout does not walk. It tumbles.** Full 500 steps untripped
  (termination only checks com_z), total reward 3,492 (forward +5,053,
  lateral −986, height −576). Body plate over 10 s: x 0 → 5,089 mm, y to
  +1,115 mm, **yaw swinging through ±170° repeatedly, pitch to −64° and
  +55°, roll to −50°, z bouncing 7 → 74 mm.** 5 m in 10 s is 0.5 m/s for a
  ~20 cm robot on MG90S — it is flipping and lunging along +X, which is
  what a +X COM-velocity reward with only a COM-height termination pays for.
  Gaps:
  1. **The task has no orientation term or termination** (upright, heading),
     so rolling over is free as long as the COM stays above 25.5 mm.
  2. **Plausibility check missing:** nothing flags 0.5 m/s, ±170° yaw
     swings or a 74 mm body jump as physically suspicious for this machine.
  3. **Hypothesis to check:** servo speed limits (MG90S ~0.1 s/60°) may not
     be enforced on the position actuators, which would make lunges cheap.
  4. **Nobody watched it.** The walk's only behavioural readout is total
     reward; there was no video (review leg died), and a human reading
     "reward 3,492, not terminated" would call it a success.
