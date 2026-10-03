---
node_id: 332e550b-eafc-508b-8fca-e63cb66ee05e
slug: sweet-brook-2725
title: 'Ouroboros run: orun1 [a9bbe06e] — operator directive'
created_at: '2026-10-02T16:59:09+00:00'
parents:
- odd-banner-6071
summary: ''
---
## What

Operator directive: an Ouroboros loop starts on this repo. Every work node of the run descends from this node.

## Why

The charter (the operator's goal document), verbatim:

# Goal: robots that look engineered, judged the way the owner judges them

Verified against source: 2026-10-02. Operator charter for orun1, following
ot11 (`.ouroboros/history/ot11.md`) and ot10 (`docs/probes/ot10/REPORT.md`).
The human owns this file; unattended roles never edit it.

## Mission

ot10 gave Cadex robots a finish: a light shell, round joints, one accent,
a studio render on the dark floor. The owner's verdict is that they now
*look finished* but are not well *designed*. The quadruped is a rounded
box with four legs, its motor pods look stuck on, and most hexapods look
bad. Servos, boards, sensors and feet are handled as things to hide or
bolt on, not as the design.

Before this run the operator measured what the owner wants instead of
writing more rules (`docs/probes/orun1/README.md`). 55 designs (7 robot
types × 8 design theses) were rated blind by the owner. The short version:
- the three Nos are all the same archetype: a soft rounded box with a
  visor face and dot eyes, over stubby limbs;
- a face costs points (47 designs had one, mean 1.43 of 3; the 8 without,
  2.00);
- the Loves read as **engineered machines**: visible structure, real
  actuators and electronics laid out with order, fasteners and panels as
  detail, no mascot face;
- "clean exposed mechanism" is the strongest thesis (2.14), "creature" and
  "the agent's own choice" the weakest;
- hexapods are the weakest type (1.14).

`docs/DESIGN-LANGUAGE.md` currently prescribes the losing archetype ("one
soft body primitive with a face"; hardware is "never an exposed case or a
bare board"). This run replaces the design language from the evidence, makes
the product design from the inside out with real parts, and proves the
result with a judge that agrees with the owner on designs it never saw.

Priority, in order:
1. A judge the owner would trust (D1).
2. The design language and the product changed (D2, D3, F1).
3. New designs that clear the bar from plain prompts (D4).

This run trains no policy. Keep the 72-hour ceiling and the
two-accepted-done stop. Every Ouroboros role and headless product-agent
call uses `claude-opus-5-5`, with no model fallback.

## Owner-revisable assumptions

The owner rated without notes and has not yet confirmed three readings.
Until this section changes, the run works to these:
- **A1. Both the face and the soft pillow-box body are out**, not only the
  face. A focal sensor (camera, range sensor, a sensor slot) may sit where
  a face was, as a real part.
- **A2. One family, two finishes.** "Engineered" covers both an exposed,
  ordered mechanism (the balancer and biped Loves) and an enclosed but
  panelled hard-surface body (the quadruped Love). The product agent picks
  per robot and says why; a soft one-piece consumer shell is no longer the
  default.
- **A3. Accent stays small and functional:** horn caps, a cradle, feet,
  a cable, a status light. Not stripes, not decoration.

## Done criteria

Each criterion needs a causally parented record with measured evidence.
The human owns the checkboxes; roles report results and do not tick them.

- [ ] **F1. A project that was accepted always reopens.**
  - Three sweep projects (`digestbug-balancer-b-motors-in-body`,
    `digestbug-balancer-d-product-shell`, `digestbug-hexapod-h-free`, in the
    projects directory beside the sweep ones) refuse to open with "The
    restore pass digest does not match the accepted digest." Rebuilding an
    accepted script gives a different digest from the one accepted.
  - Diagnose the cause, fix it in the product, and add a regression test
    that fails before the fix. Two of the three had been resumed after an
    interrupted turn; whether that matters is part of the diagnosis.
  - After the fix, all three open and render at their accepted revision,
    or the report says exactly why one cannot and what the product now does
    instead of refusing.
  - Work on copies named `orun1-*`; the originals stay read-only.
- [ ] **D1. A frozen judge agrees with the owner on designs it never saw.**
  - `docs/probes/orun1/ratings.json` is the owner's ground truth and is
    never edited. Its `dev` designs are for building the judge; its
    `heldout` designs are for measuring it.
  - Before any held-out measurement, `docs/probes/orun1/README.md` (below
    the marker) freezes a **judge version**: model (`claude-opus-5-5`),
    prompt, inputs, the comparison form (pairwise, ranking or rubric: the
    run decides), the number of calls and how they are aggregated.
  - **Inputs are images only**, rendered by the product from the design's
    project at its accepted revision on the dark prototype floor: the hero
    and any `look` views the version names. The judge never sees a thesis,
    the agent's notes, a project or file name, the owner's verdicts or
    another design's verdict.
  - **The bar, on the held-out set:**
    - pairwise order agreement of **80% or more** over every held-out pair
      whose owner verdicts differ by two levels or more (Love against Meh or
      No, Like against No);
    - every held-out Love ranked above every held-out No;
    - Kendall's tau over all held-out pairs, reported with its pair count.
  - **Each judge version is measured on the held-out set once.** A new
    version needs a recorded change motivated by dev results, never by
    held-out ones. Every version and every held-out measurement is published,
    including the failures.
  - **Baseline:** ot10's frozen judge (rubric T1–T7,
    `docs/probes/ot10/README.md`) is measured on the same held-out pairs
    with the same metric, and reported beside the new one.
  - The judge's prompt never reaches the product agent.
- [ ] **D2. The design language says what the owner rated, and the product
  teaches it.**
  - `docs/DESIGN-LANGUAGE.md` is rewritten, and the overlay the product
    agent reads (`Mod/cadex/CadexAgentGuidance.md`) with it, on A1–A3 and the
    ratings.
    - Every rule cites its evidence: sweep design ids and their verdicts, or
      the owner's words in this charter. A rule with no evidence is either
      removed or marked as the operator's or the run's own judgement.
    - The rules the ratings contradict go: the mandated face, the
      single soft body primitive, "never an exposed case or a bare board",
      "split lines are the only surface detail". Each removal is an ADR.
  - **Inside out is the procedure, not a hint:** choose the actuators,
    controller, power, battery, sensors and the cable path; place them; then
    design the structure that carries them, and only then any panels or
    covers. Feet, sensors, fasteners and cable runs are designed parts, not
    leftovers.
  - Neither the guidance nor any product prompt quotes the owner's ratings,
    shows a sweep render, or contains the judge's prompt. The agent learns
    the direction only as written rules.
  - The ot10 rubric is retired or rewritten, and an ADR says which. D1's
    frozen judge is this run's authority.
- [ ] **D3. The product can design with the parts these robots need, and
  can tell when a part is not held.**
  - The catalog gains, with a datasheet source, true dimensions, mounting
    features and a bay, as the existing servos and boards have:
    - a serial bus servo of the STS3215 class;
    - a single-board computer larger than the Pi Zero (a Pi 4 or 5 class
      board or a compute module carrier);
    - a camera module and a range sensor (time-of-flight class);
    - a wheel and tyre set and a rubber foot pad;
    - anything else the D4 transcripts show the agent reaching for and not
      finding, with the transcript cited.
  - **A mounting check.** The product reports, for every purchased part,
    which printed part holds it and by what (screws, a bay, a clip, a
    horn). A part held by nothing, or held only by being inside a shell, is
    reported. The product agent sees this report in every build reply.
    Tests pin it on a fixture that passes and one that fails.
- [ ] **D4. Plain prompts produce designs that clear the owner's bar.**
  - **Plain prompts, frozen before generation** in the README: one per type
    (quadruped, hexapod, biped, 5-axis arm, 3-axis arm, two-wheeled
    balancer, and one wildcard of the agent's choosing). Each names the
    type, its joint count, "design only" and nothing about style. The style
    must come from the product's guidance, not the prompt.
  - Each design is a fresh `orun1-*` project at the final product
    revision. It is accepted, its static and swept fit pass, its purchased
    parts are all from the catalog, and every one of them passes D3's
    mounting check.
  - **The bar, judged by D1's frozen version** that met the held-out bar:
    - each new design wins the majority of its pairwise comparisons against
      the sweep designs of the same type that the owner rated Like or Love;
    - the new hexapod is held to the same bar, with no exemption.
  - **Confirmation, not fishing.** One pre-registered confirmation turn per
    type at the final revision counts. Every earlier attempt is published.
    A second confirmation of a type needs a recorded product change between
    the two.
  - The final set (hero, concept sheet and the judge's result for each)
    is committed under `docs/probes/orun1/final/` for the owner to review.
- [ ] **C1. Regressions and a closing report are complete.**
  - Both full suites pass at the final revision, plus the packaged
    lifecycle gate for any engine or payload change.
  - `docs/probes/orun1/REPORT.md` covers:
    - F1's cause and fix;
    - every judge version and its held-out result beside the ot10
      baseline;
    - the design language diff, rule by rule, with its evidence;
    - the catalog additions;
    - every D4 attempt, its fit and mounting results and its judge results;
    - the remaining defects.
  - Reconcile, then claim done for critic review without ticking the owner
    boxes.

## Horizon ladder

- **short-term:**
  1. F1: diagnose and fix the digest bug on copies, with its regression.
  2. Measure ot10's judge on the held-out set as the baseline before
     building anything new.
  3. Build judge versions on the dev set, freeze one, and measure it on the
     held-out set (D1).
- **medium-term:**
  1. Rewrite the design language and the overlay (D2), each rule with its
     evidence.
  2. Catalog additions and the mounting check (D3).
  3. Freeze the plain prompts. Run trial designs and judge them; diagnose
     each weak one from its renders and the judge's comparisons, then change
     the product's guidance or tooling, never the prompt.
  4. Hexapods last and hardest: the worst-rated type, and the one the owner
     named.
- **long-term:**
  1. The D4 confirmation set, and the closing report.
  2. A presentation pass on the final set: concept sheets that show the
     inside-out layout (an exploded or cutaway view of where each part sits).
     This is a direction, not a bar.
  3. Keep every gate green and every doc true. Keep `STATE.md` reconciled.

## Constraints

**Standing:**
- Obey AGENTS.md, the licensing rules and the process boundaries. `cli/` is
  LGPL: copy nothing from `shell/`.
- Training stays offboard in `training/`. JAX and MJX never enter the
  engine or a payload.
- Never commit secrets, machine paths, private hostnames, build outputs,
  full transcripts, policy binaries or rollout traces.
- Do not hand-edit `STATE.md`, `PLAN.md`, `ROADMAP.md` or state nodes.
- Keep earlier projects read-only (hex, ot5–ot11, every `sweep-*` and
  `digestbug-*`). Work on copies, each under a new `orun1-*` name.

**This run:**
- **The product agent authors every design D4 counts.** The actor builds the
  guidance, the catalog, the checks, the judge and the tools. It never
  hand-edits a design, a render or a prompt that a criterion counts.
- **The owner's ratings are ground truth and are never edited.** The
  held-out set is never used to choose or tune anything.
- **No reference image enters the product or the repo.** `reference/` stays
  local and gitignored. A rule may name a reference file, as ADR-411 did; it
  may not copy or describe the image into a prompt.
- **Design turns are supervised.** Keep them inside one iteration, or under
  a supervisor that outlives the actor's session. A killed turn or a usage
  limit is an interruption, not an attempt.
- **Renders and concept sheets use the dark prototype floor** (ADR-444).
  Committed images are PNG, 300 KB or less each, under
  `docs/probes/orun1/`.
- **This run trains nothing.** Designs must still export and pass their fit
  checks, so a later run can train them.
- No role starts, stops or restarts the loop or signals its process.

## Question policy

- Resolve reversible choices autonomously, using the smallest measured step
  towards the highest-ranked open criterion.
- The judge outranks the design language, and the design language outranks
  the designs. A design that passes a judge you do not trust has not passed.
- Where A1–A3 and a measurement disagree, record both and follow A1–A3. They
  are the owner's to change.
- Code and accepted artifacts outrank docs. Update the docs with the
  behaviour they describe.
- A harness or usage limit is not an attempt: keep the receipt and wait for
  capacity.
- Never invent a measurement, never weaken a frozen threshold to pass, and
  never treat a provider refusal as a verdict.

## Exhaustion policy

`report_done`.
- Once F1, D1–D4 and C1 have evidence, write the closing report, reconcile
  and claim done. Two consecutive critic acceptances stop the run.
- Do not claim done while any criterion is unmet unless the 72-hour ceiling
  has arrived. Until then, work the highest-ranked open criterion, then the
  long-term rung.
- If the ceiling arrives first, report the highest bar reached and every
  failed attempt. Do not redefine success.

## Quality bar

- Run `pixi run test-engine` and `pixi run python -m pytest cli/tests` at
  the final revision. Run the CLI suite with the GPU hidden.
- For protocol or payload changes, rebuild and stage, then run the packaged
  lifecycle gate. Report skips and failures as such.
- A product fix needs a regression test that fails before it.
- Every design claim cites its project, its accepted revision and the
  judge version that scored it.
- Record each unit with its State Impact. Direction changes, new APIs and
  removals also earn ADR entries.

## Reconcile

- Every five work iterations or three unreconciled records:
  - fold impacts;
  - advance the high-water mark;
  - regenerate the views;
  - export and check.
- The separate maintainer and planner roles stay off; the critic names the
  next unit.
- Unattended roles never edit this charter.

**Done criteria as gaps** (one open state node each; work closes them through declared impacts):

- [gap] gap-f1-project-that-was-accepted: **F1. A project that was accepted always reopens.** - Three sweep projects (`digestbug-balancer-b-motors-in-body`, `digestbug-balancer-d-product-shell`, `digestbug-hexapod-h-free`, in the projects directory beside the sweep ones) refuse to open with "The restore pass digest does not match the accepted digest." Rebuilding an accepted script gives a different digest from the one accepted. - Diagnose the cause, fix it in the product, and add a regression test that fails before the fix. Two of the three had been resumed after an interrupted turn; whether that matters is part of the diagnosis. - After the fix, all three open and render at their accepted revision, or the report says exactly why one cannot and what the product now does instead of refusing. - Work on copies named `orun1-*`; the originals stay read-only.
- [gap] gap-d1-frozen-judge-agrees-owner: **D1. A frozen judge agrees with the owner on designs it never saw.** - `docs/probes/orun1/ratings.json` is the owner's ground truth and is never edited. Its `dev` designs are for building the judge; its `heldout` designs are for measuring it. - Before any held-out measurement, `docs/probes/orun1/README.md` (below the marker) freezes a **judge version**: model (`claude-opus-5-5`), prompt, inputs, the comparison form (pairwise, ranking or rubric: the run decides), the number of calls and how they are aggregated. - **Inputs are images only**, rendered by the product from the design's project at its accepted revision on the dark prototype floor: the hero and any `look` views the version names. The judge never sees a thesis, the agent's notes, a project or file name, the owner's verdicts or another design's verdict. - **The bar, on the held-out set:** - pairwise order agreement of **80% or more** over every held-out pair whose owner verdicts differ by two levels or more (Love against Meh or No, Like against No); - every held-out Love ranked above every held-out No; - Kendall's tau over all held-out pairs, reported with its pair count. - **Each judge version is measured on the held-out set once.** A new version needs a recorded change motivated by dev results, never by held-out ones. Every version and every held-out measurement is published, including the failures. - **Baseline:** ot10's frozen judge (rubric T1–T7, `docs/probes/ot10/README.md`) is measured on the same held-out pairs with the same metric, and reported beside the new one. - The judge's prompt never reaches the product agent.
- [gap] gap-d2-design-language-says-what: **D2. The design language says what the owner rated, and the product teaches it.** - `docs/DESIGN-LANGUAGE.md` is rewritten, and the overlay the product agent reads (`Mod/cadex/CadexAgentGuidance.md`) with it, on A1–A3 and the ratings. - Every rule cites its evidence: sweep design ids and their verdicts, or the owner's words in this charter. A rule with no evidence is either removed or marked as the operator's or the run's own judgement. - The rules the ratings contradict go: the mandated face, the single soft body primitive, "never an exposed case or a bare board", "split lines are the only surface detail". Each removal is an ADR. - **Inside out is the procedure, not a hint:** choose the actuators, controller, power, battery, sensors and the cable path; place them; then design the structure that carries them, and only then any panels or covers. Feet, sensors, fasteners and cable runs are designed parts, not leftovers. - Neither the guidance nor any product prompt quotes the owner's ratings, shows a sweep render, or contains the judge's prompt. The agent learns the direction only as written rules. - The ot10 rubric is retired or rewritten, and an ADR says which. D1's frozen judge is this run's authority.
- [gap] gap-d3-product-can-design-parts: **D3. The product can design with the parts these robots need, and can tell when a part is not held.** - The catalog gains, with a datasheet source, true dimensions, mounting features and a bay, as the existing servos and boards have: - a serial bus servo of the STS3215 class; - a single-board computer larger than the Pi Zero (a Pi 4 or 5 class board or a compute module carrier); - a camera module and a range sensor (time-of-flight class); - a wheel and tyre set and a rubber foot pad; - anything else the D4 transcripts show the agent reaching for and not finding, with the transcript cited. - **A mounting check.** The product reports, for every purchased part, which printed part holds it and by what (screws, a bay, a clip, a horn). A part held by nothing, or held only by being inside a shell, is reported. The product agent sees this report in every build reply. Tests pin it on a fixture that passes and one that fails.
- [gap] gap-d4-plain-prompts-produce-designs: **D4. Plain prompts produce designs that clear the owner's bar.** - **Plain prompts, frozen before generation** in the README: one per type (quadruped, hexapod, biped, 5-axis arm, 3-axis arm, two-wheeled balancer, and one wildcard of the agent's choosing). Each names the type, its joint count, "design only" and nothing about style. The style must come from the product's guidance, not the prompt. - Each design is a fresh `orun1-*` project at the final product revision. It is accepted, its static and swept fit pass, its purchased parts are all from the catalog, and every one of them passes D3's mounting check. - **The bar, judged by D1's frozen version** that met the held-out bar: - each new design wins the majority of its pairwise comparisons against the sweep designs of the same type that the owner rated Like or Love; - the new hexapod is held to the same bar, with no exemption. - **Confirmation, not fishing.** One pre-registered confirmation turn per type at the final revision counts. Every earlier attempt is published. A second confirmation of a type needs a recorded product change between the two. - The final set (hero, concept sheet and the judge's result for each) is committed under `docs/probes/orun1/final/` for the owner to review.
- [gap] gap-c1-regressions-closing-report-complete: **C1. Regressions and a closing report are complete.** - Both full suites pass at the final revision, plus the packaged lifecycle gate for any engine or payload change. - `docs/probes/orun1/REPORT.md` covers: - F1's cause and fix; - every judge version and its held-out result beside the ot10 baseline; - the design language diff, rule by rule, with its evidence; - the catalog additions; - every D4 attempt, its fit and mounting results and its judge results; - the remaining defects. - Reconcile, then claim done for critic review without ticking the owner boxes.

## Method

Ouroboros iterations on branch `ouroboros/orun1`: orient, one dispatched unit, record, commit; a reconcile pass folds the tail on pressure; with the planner on, a bet follows each reconcile.

## Result

Directive recorded. Work follows as child nodes.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: 0eabd770ccaff5102a77d5857fd0ab2e26c28403

## State Impact

- target: NEW gap-f1-project-that-was-accepted — Charter gap, status open: **F1. A project that was accepted always reopens.** - Three sweep projects (`digestbug-balancer-b-motors-in-body`, `digestbug-balancer-d-product-shell`, `digestbug-hexapod-h-free`, in the projects directory beside the sweep ones) refuse to open with "The restore pass digest does not match the accept. Flip to working only when the criterion is verifiably met.
- target: NEW gap-d1-frozen-judge-agrees-owner — Charter gap, status open: **D1. A frozen judge agrees with the owner on designs it never saw.** - `docs/probes/orun1/ratings.json` is the owner's ground truth and is never edited. Its `dev` designs are for building the judge; its `heldout` designs are for measuring it. - Before any held-out measurement, `docs/probes/orun1/RE. Flip to working only when the criterion is verifiably met.
- target: NEW gap-d2-design-language-says-what — Charter gap, status open: **D2. The design language says what the owner rated, and the product teaches it.** - `docs/DESIGN-LANGUAGE.md` is rewritten, and the overlay the product agent reads (`Mod/cadex/CadexAgentGuidance.md`) with it, on A1–A3 and the ratings. - Every rule cites its evidence: sweep design ids and their verd. Flip to working only when the criterion is verifiably met.
- target: NEW gap-d3-product-can-design-parts — Charter gap, status open: **D3. The product can design with the parts these robots need, and can tell when a part is not held.** - The catalog gains, with a datasheet source, true dimensions, mounting features and a bay, as the existing servos and boards have: - a serial bus servo of the STS3215 class; - a single-board compu. Flip to working only when the criterion is verifiably met.
- target: NEW gap-d4-plain-prompts-produce-designs — Charter gap, status open: **D4. Plain prompts produce designs that clear the owner's bar.** - **Plain prompts, frozen before generation** in the README: one per type (quadruped, hexapod, biped, 5-axis arm, 3-axis arm, two-wheeled balancer, and one wildcard of the agent's choosing). Each names the type, its joint count, "desi. Flip to working only when the criterion is verifiably met.
- target: NEW gap-c1-regressions-closing-report-complete — Charter gap, status open: **C1. Regressions and a closing report are complete.** - Both full suites pass at the final revision, plus the packaged lifecycle gate for any engine or payload change. - `docs/probes/orun1/REPORT.md` covers: - F1's cause and fix; - every judge version and its held-out result beside the ot10 baselin. Flip to working only when the criterion is verifiably met.
