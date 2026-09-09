---
node_id: eb69082d-3eb8-5b08-9aee-249a26b15110
slug: square-crest-8869
title: 'Bet: finish the detach leg, then let the eyes see the motion the walk trained'
created_at: '2026-09-09T05:05:54+00:00'
parents:
- chilly-basin-7378
summary: ''
---
## What

The frontier moved, so all three horizons are re-ranked around what is actually left.

**short**, in order: (1) carry `--detach` through the walk — the last gap `witty-spark-2613` names in its own words; (2) **measure clearance over the poses the rollout actually visits, not only the accepted pose** — this pass's one new direction, promoted out of long item 7 in the smallest form that reuses what the kernel already has; (3) trim the scaffold guide back under its own prompt budget, kept but demoted and re-scoped after a correction.

**medium** drops its conditional mjx-free export check — delivered, the other way round — records that the walk criterion's evidence is complete, and keeps the charter's "run the walk whenever the short rung is empty" rule as the standing next unit rather than scheduling a walk now.

**long** promotes item 7, kernel clearance over `assembly.rollout`, from unselected to selected in exactly the bounded form short rank 2 states. That item said its promotion required a separate justified bet; this is it.

No charter gap is retired, blocked or marked done by this pass.

## Why

**Both units of the previous short are discharged, one by landing and one by being overtaken.** Unit 2 ran: `ot4-mix55`, the same crank-slider prompt into a second empty project, no `--resume` and no supplied script, **completed every leg — exit 0 in 1680.78 s**, design 1649.63 s, train 26.71 s at reward/step −0.4055, witness error 1.14e-08, rollout −19.85, all four eyes, CLI gate 289 passed [rec: chilly-basin-7378]. `crisp-reef-5607` now reads "the criterion's evidence is complete". Unit 1 did not land, and its stated motivation — carrying the MJX collision-geometry limit into prose — was taken instead by ADR-281, which refuses a model MJX cannot build at `assembly.task`, naming both geoms, both bodies and both kinds [rec: sleepy-grove-5790]. On the re-run that refusal never fired: the design turn authored only boxes and capsules, with its own written reason [rec: chilly-basin-7378].

**Medium's conditional new direction resolved before its condition could be read.** It was written as "build the mjx-free pair check only if the guide alone did not change what an unaided design turn authors". The actor built it first, in the engine rather than at export, and the walk then succeeded without triggering it. So it is delivered, not pending, and it is dropped as a conditional rather than carried [rec: sleepy-grove-5790] [rec: chilly-basin-7378].

**What is still named and open is the detach leg.** `witty-spark-2613` audited all three limbs and concluded that, read against the criterion's own wording, there is no remaining gap except one sentence it states plainly: "`--detach` still does not travel through the walk, and remains its own unit" [rec: idle-falcon-3004]. Verified in source this pass: `--detach` is added to `train_parser` only; `walk_parser` gets `_remote_flags` and nothing else, and `cadex train --remote --detach` already returns a project-local pending run locator with no policy verified or stored (ADR-278) [rec: clear-shade-1084]. It costs no model dispatch and no box.

**The new direction, and the justification long item 7 asked for.** The run that closed the walk criterion reported `1 intersection: frame ∩ slider, 648.0 mm³` — **at the initial solved pose** — and then rolled 151 solved frames with 74.62° of crank rotation and 20.32 mm of coupler travel, with clearance measured at none of them [rec: chilly-basin-7378]. That is not an oversight in the run; it is what the surface measures. `core.inspect` scope `clearance` reads the accepted revision's components "at the pose the solver put it at" — one pose. Per-frame clearance already exists in the kernel and is already ADR-242-correct — `_clearance_at_frame` re-places each prepared shape from the component's live placement inside the frame loop, and reports the *worst* approach over the whole travel rather than the first — but it exists only inside `assembly.simulation`'s trace. `assembly.rollout`, which is the motion the walk actually reviews, has no clearance surface at all; `CadexDynamics`'s only clearance is `_measure_reset_clearance`, which is about reset variation. So the eye the charter's mission 6 asks for — "clearance and intersection checks" — is measuring a mechanism that is standing still, and a mechanism that only collides while moving passes it silently. Making that eye see the motion it reviewed serves mission 6 and mission 2 at once, and it does it by reusing a measurement the kernel already performs rather than by adding an eye.

Honest accounting on the charter's "remove more than we add": this removes no lines. What it removes is a false impression — that a green clearance block says anything about the gait. If the smallest form cannot reuse `_clearance_at_frame` and `_clearance_prepare` against poses the rollout trace already carries, the unit becomes a measurement record saying so and is **dropped, not grown into a second clearance engine**.

**One correction to the plan's own text, made rather than repeated.** The previous short claimed the oversize scaffold "drops more than half of the walk's training contract before a design turn sees it". That is wrong. `_bounded(..., keep="ends")` at `PROMPT_DOC_LIMIT = 8_000` keeps a 4,000-character head and a 4,000-character tail; the template measures 8,399 characters this pass, so it elides roughly 400 characters from the middle of `## Training`, not half of it. The defect is real — the shipped scaffold exceeds its own budget on a project that has written nothing — and it is small, which is why it now ranks third rather than first.

**Budget.** 30.6 h left of the run; codex seven-day usage is at 99% and claude seven-day at 80%. Short ranks 1 and 3 spend no model dispatch at all; rank 2 is engine-zone work costing one build and the packaged gate. **No fresh walk is scheduled by this pass**: the charter's rule fires when the short rung is empty, and it is not. The last walk cost 1680.78 s and a design turn; spending another on the same prompt would re-measure a thing already measured.

## Method

One decision record, then the three horizon bodies rewritten in place: `## Current` replaced, `## Negative knowledge` preserved with one bullet added for this pass's fences and the character-count correction, `## Provenance` extended with this bet. Then the view mark, `hypergraph sync`, and one `plan:` commit. No record node, no state node and no STATE.md edit; no code.

## Result

Folded into `young-crane-9546` (short), `strong-birch-7412` (medium) and `late-valley-7350` (long).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: b45c23745ab031545269b0d2c72759a33a62ea40

## State Impact

- target: plan/young-crane-9546 — lead short with the detach-through-walk unit, add rollout-pose clearance as this pass's one new direction, demote and re-scope the scaffold trim
- target: plan/strong-birch-7412 — record the walk criterion's evidence complete, drop the delivered conditional mjx check, keep the walk-when-empty rule standing
- target: plan/late-valley-7350 — promote long item 7 (kernel clearance over assembly.rollout) from unselected to selected in its bounded form
