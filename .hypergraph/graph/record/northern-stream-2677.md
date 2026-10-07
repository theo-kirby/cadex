---
node_id: 813873b1-f53d-59ca-9c22-edf2705fc904
slug: northern-stream-2677
title: 'G2 lessons placed: ledger destinations, base and style guidance carry them (ADR-565)'
created_at: '2026-10-06T13:17:11+00:00'
parents:
- terse-falcon-9243
summary: ''
---
## What

G2, second unit: every row of the orun4 lessons ledger (`docs/probes/orun4/LESSONS.md`) now has a destination with its reason, and the adopted lessons are written into Cadex's guidance as general rules (ADR-565):

- **Base, engine** (`src/Mod/cadex/CadexAgentGuidance.md`): solids built from tangent primitives are measured (L19); a joint's limit and spacing are set together from the sweep and re-read when a neighbour grows (L7, L8); new paragraph *THE SIMULATED BODY IS THE BUILT BODY*, which says contacts are unions of collision primitives and the support sits under the measured centre of mass (L3, L2); in the walking task: speed bounded on both sides (L6), a target speed that makes the intended motion the easy one (L5), command range centred on the rest pose via `command_limits_degrees` (L9), progress only while upright (L10), a ceiling on anti-degenerate charges (L12), heading charged from the first run (L13).
- **Base, CLI** (`cli/cadex_cli/guidance.py`): new paragraph *TRAIN SO A GOOD POLICY CAN BE KEPT*: checkpoints on every run, keep what `evaluate` passes, when to warm- or cold-start, never tighten `action_filter_alpha` on a warm start (L14–L17).
- **Style** (`CadexAgentStyle.printed-legged-robot.md`): the look of a limb (W2); the knee actuator inside the thigh (W1, owner to confirm); compact hull feet with a flat strip between twin keels (L1, L4); hips wide enough for the feet to pass (L7 instance, L8); *THE STEP IS WHAT IS PAID*: swing and slip terms and a common-mode hip charge (L5 instance, L11, L13 symmetry). The look-check line also names large, flat or single-keel feet and feet that meet.
- **Tool**: L18 is F1 (ADR-558), not guidance. **Not adopted**: W6 (hip yaw hypothesis).
- `docs/DESIGN-LANGUAGE.md`: the "which rule is where" table has six new rows. `docs/DECISIONS.md`: ADR-565.
- Tests: `src/Mod/cadex/cadex_tests/test_agent_guidance.py::test_the_reference_lessons_are_in_the_base_and_the_style_they_belong_to` pins each rule in its file, checks it is absent from the other, and checks that none of the reference robot's numbers became defaults. `cli/tests/test_agent_guidance.py::test_the_training_lessons_are_in_the_base_and_reach_every_project` pins the training paragraph when no style is chosen. The existing tests still pin that the base names no robot type and that no guidance file names a project.

## Why

The critic named G2 as the next unit: fill in the ledger's destinations, then write the lessons into the base and the style as general rules with tests, and leave the fresh-session proof for the unit after. That is what this unit did. G2 is the highest-ranked open criterion; F1, F2, G1 and D1 have their evidence.

## Method

Each ledger row went through the charter's question policy: would the rule be wrong for a crane, a wheeled base or a fixed arm? Rules that hold for any mechanism or any learned task went to the base. Training-tool practice went to the CLI overlay, because `train_start` and `evaluate` are CLI tools. Legged rules and taste went to the style. I checked each rule against the reference project's script and DECISIONS.md, read only. For example, the symmetry term is `(q_pitch_l + q_pitch_r)/2`, a common-mode pitch, and the command box is centred on the stance through `command_limits_degrees`. I also checked them against Cadex's API (`command_limits_degrees` in `cadex_assembly_api.py`, and the `centre_of_mass` observation kind in `CadexDynamics.OBSERVATION_KINDS`), so every rule names a mechanism that exists. No numbers from the reference were written in as defaults.

## Result

Gates, all run in the foreground with the GPU hidden after `pixi run build-engine`:
- `pixi run test-engine`: 2599 passed, 58 skipped (338 s).
- The CLI suite, run in two halves: 807 passed and 1 skipped (390 s), then 388 passed (236 s).
- The first run of the second half failed one test, `test_loop.py::test_the_loop_names_no_behaviour`, because my new training paragraph said "balance". That paragraph must name no behaviour. I reworded it ("what it learned carries over"; "loses its behaviour through a stronger one") and reran: green.

The G2 ledger is complete: 15 rows went to the base (one, W4, was already there), 9 to the style (W3 and W5 were already there), L18 is a tool fix, and W6 was not adopted. Three rows are marked *owner to confirm*: L4 (the foot rule's phrasing), L5 (the reference moved its target speed **up**, not down, so the charter's "a speed the servos can hold" reads as headroom checked), and W1 (knee placement is taste). Concern: the base's walking-task example still uses 60 mm/s as an illustration of the formula. It is not a default, but L5 warns that too low a target trains a shuffle; I left it because it shows the formula, not a value to copy. Still open in G2: the fresh-session check (an `orun4-*` scratch project with the style chosen, asked for a printed legged robot, with the transcript and render in the record). That is the next unit. There is no new dependency, and the tool surface is unchanged.

Dispatch closed: 1 unit — G2 lessons placed: ledger destinations filled, base, CLI and style guidance carry them, pinned by tests (ADR-565)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: b88a840abad4d426103eafa241aa4db33cceab36

## State Impact

- target: narrow-beacon-6703 — ledger complete with destinations; lessons written into base (engine + CLI training) and printed-legged-robot style as general rules, test-pinned (ADR-565); three rows owner to confirm; fresh-session check still open
