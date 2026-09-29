---
node_id: 50435fde-7344-5703-948f-7409e5d60f0a
slug: snowy-quill-0006
title: 'Ouroboros run: ot10 [96f53050] — operator directive'
created_at: '2026-09-29T06:44:35+00:00'
parents:
- rapid-spark-0680
summary: ''
---
## What

Operator directive: an Ouroboros loop starts on this repo. Every work node of the run descends from this node.

This directive supersedes `rapid-spark-0680`: the operator edited the charter; this version applies at a run start or iteration boundary.

## Why

The charter (the operator's goal document), verbatim:

# Goal: give Cadex robots a look of their own

Verified against source: 2026-09-27. Operator charter for ot10, following
hex1–hex3 (`docs/probes/hex/`) and ADR-406 to ADR-410. The human owns this
file; unattended roles never edit it.

## Mission

Make a robot that the product agent designs unassisted look like a designed
product, not a fit check that passed. hex3 is the baseline: a flat deck of
orange plates with bare boards, square servo boxes and no face
(`docs/probes/hex/shots/hex3-look_iso.png`). The target is the owner's
reference set in `reference/`. It is gitignored and local to this machine;
read `reference/README.md`, then the ten images in `reference/images/1-core/`,
before any design or render work.

In priority order:

1. **Aesthetics.** Distil the core references into Cadex's own design
   language: two materials and one accent, a shell over the skeleton, joints
   as features, soft primitives with large radii, a face, taper, and a
   presented studio render. Build what the product needs to design, see and
   present in that language, and prove it with unassisted design turns.
2. **The open hex gaps.** The agent learns the API by refusal. There is no
   rollout video. The ADR-410 alive-bonus walk has never been run end to end.

The full hex4 run belongs to the owner, not this run. This run may run
design-only product turns and bounded training probes.

Keep the 72-hour ceiling and two-accepted-done stop. Every Ouroboros role and
headless product-agent call uses `claude-opus-5-5`, with no model fallback.

## Done criteria

Each criterion needs a causally parented record with measured evidence.
The human owns the checkboxes; roles report results and do not tick them.

- [ ] **A1. Cadex has a written design language and a frozen way to judge
  it.**
  - `docs/DESIGN-LANGUAGE.md` states Cadex's own language for small printed
    servo robots: form, materials and palette, joints, face, proportion,
    printability and presentation. Each rule names the core references it
    comes from by filename only.
  - `docs/probes/ot10/README.md` freezes a scoring rubric of 5–8 traits,
    each scored 0–3 with written anchors.
  - It also freezes the measurable proxies from A3 and a numeric bar for A5,
    which must be set before any A5 probe runs.
  - It freezes the judging procedure: a fresh model call that sees the
    rubric, the reference images and the candidate renders, and nothing
    else.
  - hex3's accepted design is scored on it as the baseline.
- [ ] **A2. Cadex renders a design as a presented product.**
  - `render` and `look` produce a studio hero shot and the existing views:
    - materials per part, lit so that curvature reads;
    - a seamless backdrop and a soft contact shadow on the floor;
    - antialiased edges;
    - a low three-quarter hero angle.
  - Material comes from the design, not a fixed two-colour split (see A3).
  - hex3's accepted design renders at 1024 px in under 60 s on this
    machine, headless and on the CPU, with no display. The 60 s bounds
    drawing once the accepted revision's tessellation is acquired; the
    engine rebuild that acquires it is reported separately and is not part
    of this bar.
  - Tests pin the output shape, the limits and the refusal paths.
  - Before and after images of hex3 are committed at 300 KB or less each.
- [ ] **A3. Appearance and design quality are declared and measured.**
  - xscript can give each part an appearance role (shell, mechanism or
    accent) and a palette. This is documented in `docs/XSCRIPT.md` and
    carried into inventory, `render`, `look` and review.
  - Review and `look` report the A1 proxies, computed from the accepted
    solids and renders. At minimum:
    - the share of the hero silhouette that is purchased hardware;
    - the share of printed outside edges left sharp;
    - the number of materials.
  - Each proxy has a test that fails on a crude fixture and passes on a
    designed one.
- [ ] **A4. The product agent is taught the language, and learns less by
  refusal.**
  - The CLI overlay and API reference teach the design language as
    something to do first: a concept (silhouette, character, palette and
    face) comes before geometry, then shell over skeleton, then refinement
    using `look`.
  - The hex2/hex3 refusal classes are prevented at the source:
    - a wrong horn style name;
    - `edit_script` before any script exists;
    - more than one assembly output or diagnostics output;
    - a joint missing or listed twice.
  - Each class is prevented either by the reference the agent reads or by
    an error that names the fix. Each has a regression test.
  - A5's transcripts show none of these refusals recurring.
- [ ] **A5. Unassisted designs meet the bar on more than one body plan.**
  - Frozen cold prompts for a hexapod, a quadruped and one body plan of the
    run's choosing, with frozen flags, each get one design-only product turn
    on a new `ot10-*` project.
  - Every design is accepted with zero failing static fit checks and a
    complete, passing swept fit.
  - Every design carries its electronics, is rendered by A2, and is scored
    blind under A1's procedure.
  - Every design meets A1's bar, and each one scores above the hex3
    baseline.
  - One failing design fails this criterion. Publish every attempt and
    every score.
- [ ] **A6. A design is presented, not screenshotted.**
  - `cadex review` leads each project with its studio hero and a concept
    sheet: the hero, orthographic line views, the palette, the name and the
    key numbers (mass, servo count, size).
  - The sheet is also written as one PNG in the project's review directory.
  - `docs/REVIEW-DESIGN.md` changes in the same commit. The A5 designs'
    sheets are committed at 300 KB or less each.
- [ ] **W1. A walk can be watched.**
  - The walk review includes a rollout video (or an animated image) of the
    accepted policy on the accepted model, in A2's style.
  - It is rendered headless on this machine within a stated bound, and
    committed to the project, never to git.
  - The review dashboard plays it, and a test pins the artifact and its
    identity.
- [ ] **W2. The ADR-410 walking task is measured end to end.**
  - One A5 design goes through `cadex walk` training with the unchanged
    ADR-410 overlay and `--stop-on-collapse`. Its settings and stop rule are
    recorded before it starts.
  - The policy is installed through the supported path, and its gait
    verdict, W1 video and training curve are published.
  - The bar is `walked = true`.
  - A policy that misses it is an honest incomplete result, with a
    diagnosis and a recorded next step. Do not weaken the gait thresholds to
    pass it.
  - **Owner review of `w2-2`: it shuffles; it does not walk.** The gait
    check's `walked = true` is a false positive for gait quality. Record
    this as the owner's verdict. Say so in REPORT.md, and do not present
    W2 as a walking robot. Do not start new training to fix it this run:
    the policy design and evaluation loop is the next charter. What this
    run may do is write down, in REPORT.md, what the gait check cannot see
    (stepping, foot clearance, slip, duty factor).
- [ ] **A7 (stretch, added by the owner mid-run). The designs reach the
  reference level, not just the bar.**
  - For each of the three body plans, the latest pre-registered
    confirmation turn, at the final revision, scores **17 or more of 21**
    and **T4 (form) at 3**. It must also meet every other A5 bar item: the
    proxies, static and swept fit, and the electronics.
  - Everything is judged under A1's frozen rubric, judge and procedure,
    unchanged. Pre-register every confirmation turn before it runs, and
    publish every attempt and score, misses included.
  - The target is the gap the A5 designs show: a rounded box on legs, servo
    cases hanging outside the shell, and a form score that never reaches 3.
    Close it with product changes: the design language, the overlay, the API
    and the engine. The actor never authors robot geometry.
  - Missing this at the ceiling is an honest incomplete result.

- [ ] **A8 (added by the owner mid-run). Everything is drawn on the dark
  prototype floor.**
  - The studio hero, the concept sheet, `look`, the rollout video and every
    other presented image use the dashboard's dark scene. That is the
    `PALETTE.scene` background `#141414`, plus the prototype mat: tiles
    `#1c1c1c` / `#232323` with a `#3a3a3a` major grid line, as the review
    viewport draws it (`docs/REVIEW-DESIGN.md`).
  - Use one palette source, so the images and the viewport cannot drift
    apart.
  - Owner's reason: the robots are mostly white, and on the dark mat their
    form and their motion over the ground are easy to see. The grid makes
    foot slip and stride legible in a video.
  - Keep the contact shadow and the lighting readable on the dark floor.
  - Commit before/after images of one A5 design, plus the W2 video, at 300
    KB or less each. Tests pin the palette to the viewport's.
  - This is a presentation change: it does not re-score A5 or A7. The judge
    keeps seeing what A1 froze until a recorded decision re-scores every
    probe.

- [ ] **C1. Regressions and a closing report are complete.**
  - Both full suites pass at the final revision, plus the packaged
    lifecycle gate for any engine or payload change.
  - `docs/probes/ot10/REPORT.md` lists every probe, score, render, training
    run, failed attempt and remaining defect, with the before/after
    comparison against hex3.
  - Reconcile, then claim done for critic review without ticking the owner
    boxes.

## Horizon ladder

- **short-term:**
  1. Read the core and design-language references and write A1's language
     and rubric. Score hex3 as the baseline before touching the product.
  2. Lighting, shading, backdrop, contact shadow and antialiasing in the
     renderer, measured on hex3.
  3. Appearance roles in xscript, and the proxies in `look` and review.
  4. Close the four refusal classes, one regression each.
- **medium-term:**
  1. Rewrite the overlay's design section around concept, then shell over
     skeleton, then refinement with `look`. Run one design-only probe,
     score it, and revise from the measured gap, not by taste alone.
  2. Run all three A5 body plans. Diagnose every design that misses the bar
     before the next prompt or tool change.
  3. The concept sheet and review presentation (A6), then the rollout video
     (W1).
  4. One bounded walk training probe on the best A5 design (W2).
- **long-term:**
  1. Make the language Cadex's own rather than a copy: a recognisable
     Cadex signature (a joint cap, a face treatment, a palette) that holds
     across body plans.
  2. Close the smaller hex gaps with measured regressions: `hip_pitch`
     ranges, stalls, electronics bays shaped around their parts.
  3. Keep every gate green and every doc true. Keep `STATE.md` reconciled.

## Constraints

**Standing:**
- Obey AGENTS.md, the licensing rules and the process boundaries. `cli/` is
  LGPL: copy nothing from `shell/`.
- Training stays offboard: do not import JAX or MJX into the engine, and do
  not build a replacement engine or shell.
- Never commit secrets, machine paths, private hostnames, build outputs,
  full transcripts, policy binaries or rollout traces.
- Do not hand-edit `STATE.md`, `PLAN.md`, `ROADMAP.md` or state nodes.
- Keep earlier projects read-only: hex1–hex3 and ot7–ot9.

**This run:**
- **`reference/` is the owner's and stays gitignored.**
  - Never commit, copy, re-encode, crop or upload any reference image, or
    embed one in a doc, test, fixture, prompt or product file.
  - Cite references by filename only.
  - The product agent never sees the references. It is taught only the
    committed design language.
- **Only the product agent designs robots.**
  - The actor writes tooling, renderer, API, prompt and measurement code.
    It never authors or edits robot geometry that A5 or W2 counts.
  - Every product turn runs on a new `ot10-*` project, with its prompt,
    flags, model and `CADEX_EFFORT` recorded.
- **Freeze A1's rubric, proxies, bar and judging procedure before the first
  A5 probe.**
  - Changing any of them later is a recorded decision that re-scores every
    earlier probe, including hex3.
  - Never tune a prompt against the judge's wording.
- **Keep rendering headless, CPU-only and dependency-light.**
  - No Blender runtime, no display and no GPU requirement for `render` or
    `look`.
  - A new dependency needs an ADR and must be licence-compatible with
    `cli/`.
- **The dashboard and visual redesign are in scope this run.** This lifts
  ot9's ban. `docs/REVIEW-DESIGN.md` changes with the page.
- **GPU training is limited to W2's bounded probes.**
  - Record the settings and stop rule before each run, and keep
    `--stop-on-collapse` on.
  - Do not launch the full hex4. It is the owner's.
- **Committed images:** PNG, 300 KB or less each, under `docs/probes/ot10/`.
- No role starts, stops or restarts the loop or signals its process.

## Question policy

- Resolve reversible choices autonomously, using the smallest measured step
  towards the highest-ranked open criterion. Aesthetics outranks the walk
  gaps.
- Where the references disagree, the core tier outranks the language tier,
  and the language tier outranks the mood tier.
- Code and accepted artifacts outrank docs. Update the docs with the
  behaviour they describe.
- When a design misses the bar, record and diagnose it before the next
  prompt or tool change.
- A harness or usage limit is not an attempt: keep the receipt and wait for
  capacity.
- Never invent a score or a measurement, and never treat a provider refusal
  as a design verdict.

## Exhaustion policy

`report_done`. **Owner decision (2026-09-29): ot10 ends after A8.** The
policy design-and-evaluation loop is the next charter.
- **Finish the unit in progress.** If it is an A7 change, land it with its
  tests and record, and do not start another A7 confirmation turn.
- **Then do A8.** It is the last product work of this run.
- **Then close:**
  1. Write the W2 note on what the gait check cannot see.
  2. Write the closing report (C1). A7 goes in it as open and carried
     forward, with whatever was measured towards it.
  3. Run both suites, plus the packaged gate if the engine or payload
     changed.
  4. Reconcile, and claim done.
- **Done is judged on A1–A4, A6, A8, W1, W2 and C1.**
  - A5 is the owner's to judge from the confirmation turns, and it does not
    block done.
  - A7 is deferred by the owner, and it does not block done.
  - W2 is met as an honest measured result with the owner's shuffle
    verdict recorded, not as a walking robot.
- Two consecutive critic acceptances stop the run.
- If the 72-hour ceiling arrives first, report the highest bar reached. Do
  not redefine success.

## Quality bar

- Run `pixi run test-engine` and `pixi run python -m pytest cli/tests` at
  the final revision.
- For protocol or payload changes, rebuild and stage, then run the packaged
  lifecycle gate. Report skips and failures as such.
- A product fix needs a regression test that fails before it.
- A renderer change carries before/after images of the same accepted design
  at the same view.
- Every aesthetic claim cites a render and a score, never adjectives alone.
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

- [gap] gap-a1-cadex-has-written-design: **A1. Cadex has a written design language and a frozen way to judge it.** - `docs/DESIGN-LANGUAGE.md` states Cadex's own language for small printed servo robots: form, materials and palette, joints, face, proportion, printability and presentation. Each rule names the core references it comes from by filename only. - `docs/probes/ot10/README.md` freezes a scoring rubric of 5–8 traits, each scored 0–3 with written anchors. - It also freezes the measurable proxies from A3 and a numeric bar for A5, which must be set before any A5 probe runs. - It freezes the judging procedure: a fresh model call that sees the rubric, the reference images and the candidate renders, and nothing else. - hex3's accepted design is scored on it as the baseline.
- [gap] gap-a2-cadex-renders-design-as: **A2. Cadex renders a design as a presented product.** - `render` and `look` produce a studio hero shot and the existing views: - materials per part, lit so that curvature reads; - a seamless backdrop and a soft contact shadow on the floor; - antialiased edges; - a low three-quarter hero angle. - Material comes from the design, not a fixed two-colour split (see A3). - hex3's accepted design renders at 1024 px in under 60 s on this machine, headless and on the CPU, with no display. The 60 s bounds drawing once the accepted revision's tessellation is acquired; the engine rebuild that acquires it is reported separately and is not part of this bar. - Tests pin the output shape, the limits and the refusal paths. - Before and after images of hex3 are committed at 300 KB or less each.
- [gap] gap-a3-appearance-design-quality-declared: **A3. Appearance and design quality are declared and measured.** - xscript can give each part an appearance role (shell, mechanism or accent) and a palette. This is documented in `docs/XSCRIPT.md` and carried into inventory, `render`, `look` and review. - Review and `look` report the A1 proxies, computed from the accepted solids and renders. At minimum: - the share of the hero silhouette that is purchased hardware; - the share of printed outside edges left sharp; - the number of materials. - Each proxy has a test that fails on a crude fixture and passes on a designed one.
- [gap] gap-a4-product-agent-taught-language: **A4. The product agent is taught the language, and learns less by refusal.** - The CLI overlay and API reference teach the design language as something to do first: a concept (silhouette, character, palette and face) comes before geometry, then shell over skeleton, then refinement using `look`. - The hex2/hex3 refusal classes are prevented at the source: - a wrong horn style name; - `edit_script` before any script exists; - more than one assembly output or diagnostics output; - a joint missing or listed twice. - Each class is prevented either by the reference the agent reads or by an error that names the fix. Each has a regression test. - A5's transcripts show none of these refusals recurring.
- [gap] gap-a5-unassisted-designs-meet-bar: **A5. Unassisted designs meet the bar on more than one body plan.** - Frozen cold prompts for a hexapod, a quadruped and one body plan of the run's choosing, with frozen flags, each get one design-only product turn on a new `ot10-*` project. - Every design is accepted with zero failing static fit checks and a complete, passing swept fit. - Every design carries its electronics, is rendered by A2, and is scored blind under A1's procedure. - Every design meets A1's bar, and each one scores above the hex3 baseline. - One failing design fails this criterion. Publish every attempt and every score.
- [gap] gap-a6-design-presented-not-screenshotted: **A6. A design is presented, not screenshotted.** - `cadex review` leads each project with its studio hero and a concept sheet: the hero, orthographic line views, the palette, the name and the key numbers (mass, servo count, size). - The sheet is also written as one PNG in the project's review directory. - `docs/REVIEW-DESIGN.md` changes in the same commit. The A5 designs' sheets are committed at 300 KB or less each.
- [gap] gap-w1-walk-can-be-watched: **W1. A walk can be watched.** - The walk review includes a rollout video (or an animated image) of the accepted policy on the accepted model, in A2's style. - It is rendered headless on this machine within a stated bound, and committed to the project, never to git. - The review dashboard plays it, and a test pins the artifact and its identity.
- [gap] gap-w2-adr-410-walking-task: **W2. The ADR-410 walking task is measured end to end.** - One A5 design goes through `cadex walk` training with the unchanged ADR-410 overlay and `--stop-on-collapse`. Its settings and stop rule are recorded before it starts. - The policy is installed through the supported path, and its gait verdict, W1 video and training curve are published. - The bar is `walked = true`. - A policy that misses it is an honest incomplete result, with a diagnosis and a recorded next step. Do not weaken the gait thresholds to pass it. - **Owner review of `w2-2`: it shuffles; it does not walk.** The gait check's `walked = true` is a false positive for gait quality. Record this as the owner's verdict. Say so in REPORT.md, and do not present W2 as a walking robot. Do not start new training to fix it this run: the policy design and evaluation loop is the next charter. What this run may do is write down, in REPORT.md, what the gait check cannot see (stepping, foot clearance, slip, duty factor).
- [gap] gap-a7-stretch-added-owner-mid: **A7 (stretch, added by the owner mid-run). The designs reach the reference level, not just the bar.** - For each of the three body plans, the latest pre-registered confirmation turn, at the final revision, scores **17 or more of 21** and **T4 (form) at 3**. It must also meet every other A5 bar item: the proxies, static and swept fit, and the electronics. - Everything is judged under A1's frozen rubric, judge and procedure, unchanged. Pre-register every confirmation turn before it runs, and publish every attempt and score, misses included. - The target is the gap the A5 designs show: a rounded box on legs, servo cases hanging outside the shell, and a form score that never reaches 3. Close it with product changes: the design language, the overlay, the API and the engine. The actor never authors robot geometry. - Missing this at the ceiling is an honest incomplete result.
- [gap] gap-a8-added-owner-mid-run: **A8 (added by the owner mid-run). Everything is drawn on the dark prototype floor.** - The studio hero, the concept sheet, `look`, the rollout video and every other presented image use the dashboard's dark scene. That is the `PALETTE.scene` background `#141414`, plus the prototype mat: tiles `#1c1c1c` / `#232323` with a `#3a3a3a` major grid line, as the review viewport draws it (`docs/REVIEW-DESIGN.md`). - Use one palette source, so the images and the viewport cannot drift apart. - Owner's reason: the robots are mostly white, and on the dark mat their form and their motion over the ground are easy to see. The grid makes foot slip and stride legible in a video. - Keep the contact shadow and the lighting readable on the dark floor. - Commit before/after images of one A5 design, plus the W2 video, at 300 KB or less each. Tests pin the palette to the viewport's. - This is a presentation change: it does not re-score A5 or A7. The judge keeps seeing what A1 froze until a recorded decision re-scores every probe.
- [gap] gap-c1-regressions-closing-report-complete: **C1. Regressions and a closing report are complete.** - Both full suites pass at the final revision, plus the packaged lifecycle gate for any engine or payload change. - `docs/probes/ot10/REPORT.md` lists every probe, score, render, training run, failed attempt and remaining defect, with the before/after comparison against hex3. - Reconcile, then claim done for critic review without ticking the owner boxes.

## Method

Ouroboros iterations on branch `ouroboros/ot10`: orient, one dispatched unit, record, commit; a reconcile pass folds the tail on pressure; with the planner on, a bet follows each reconcile.

## Result

Directive recorded. Work follows as child nodes.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 54c9058d8df91d4a1f384787a4d9a0a490aefe0b

## State Impact

- target: NEW gap-a8-added-owner-mid-run — Charter gap, status open: **A8 (added by the owner mid-run). Everything is drawn on the dark prototype floor.** - The studio hero, the concept sheet, `look`, the rollout video and every other presented image use the dashboard's dark scene. That is the `PALETTE.scene` background `#141414`, plus the prototype mat: tiles `#1c1c. Flip to working only when the criterion is verifiably met.
