---
node_id: 6ad54565-76f1-53f2-a346-d5393008e295
slug: solemn-hill-7272
title: 'ot10 A4: overlay design section rewritten as concept, skeleton, shell, refine with look (ADR-417)'
created_at: '2026-09-27T18:49:11+00:00'
parents:
- light-tower-4418
summary: ''
---
## What

ot10 A4, the teaching half (ladder medium-1, first half): the CLI overlay's design section (`cli/cadex_cli/agent.py`, `DESIGN IT; DO NOT ONLY MAKE IT FIT`) is rewritten as four numbered steps in `docs/DESIGN-LANGUAGE.md` §8's order: (1) concept first, before any geometry: silhouette, character/face, palette and proportion, stated before the first `write_script` and repeated as `DECISION:` lines; (2) skeleton: ADR-406's enclose, one-form, mirror, proportion and printable rules; (3) shell over skeleton: shells hide hardware, radii 10–20% of smallest size, one joint cap per axis, a face on +X, taper to a distinct foot, and two materials plus one accent by appearance role; (4) refine with `look`: `hero`/`iso`/`iso_back`/`focus`, reading `measures` (P1/P2/P3) first. ADR-417 is written. `docs/CLI.md` and the stale "exists today" paragraph of `docs/DESIGN-LANGUAGE.md` are updated.

## Why

The critic named medium-1 as the next unit: the overlay rewrite, the PRINTABLE fix with a well-formedness test, and then one design-only probe. Frontier target: A4 (`odd-tree-6681`).

**Deviations, stated:**
- The critic asked for a reconcile first. This dispatch forbids reconcile in a work iteration "no exceptions", so I did not run it. The tail is now 3 unreconciled records (sweet-sage-3253, light-tower-4418, this one), which meets the charter's three-record reconcile trigger. The next iteration should be the reconcile/maintainer pass.
- I did not run the design-only probe. It is a product turn with blind scoring, which makes it a second unit, and the budget is 1 unit. It is the next work unit.
- The "cut-off" PRINTABLE sentence was never cut off. The source line `no unsupported \` is a backslash continuation, and the sentence finishes "overhang past 45 degrees, …" on the next line. ADR-416 misread a line break. I added the well-formedness test anyway. It passes on the old source too, and that result is the measured answer to the report.

## Method

- Wrote the section from `docs/DESIGN-LANGUAGE.md` §1–§8 only. I did not read the rubric anchors, to avoid tuning the prompt against the judge. Old rule names pinned by `test_the_prompt_holds_printed_parts_to_a_design_language` are kept.
- One substantive correction: the old "about 1 mm on small parts, 2-3 mm on a body" radius rule contradicted DESIGN-LANGUAGE §1 (10–20%, 4–8 mm on 40 mm).
- New tests in `cli/tests/test_turn_loop.py`:
  - `test_the_overlay_is_well_formed`: every paragraph and bullet ends in `.`, `:` or `;`, has balanced backticks and parentheses, and has no double spaces. The PRINTABLE bullet holds its full clause.
  - `test_the_design_section_runs_concept_skeleton_shell_then_look`: the four steps are in order, and each step carries its rules, roles and `look` measures.
- Ran the new tests against the previous `agent.py`: the order test fails and the well-formedness test passes (see Why).

## Result

- `pixi run test-engine`: 2229 passed, 53 skipped.
- `pixi run python -m pytest cli/tests`: 991 passed, 1 skipped.
- No engine, protocol or payload change, so the packaged gate is not required.

What is true now: the overlay teaches concept → skeleton → shell → refine with `look`, and tests pin both the order and the well-formedness. Whether the agent follows it is unmeasured until the probe runs.

For the next iterations:
1. **Reconcile.** The tail is 3 records, and the critic asked for it.
2. **One design-only probe** on a new `ot10-*` project, with the prompt, flags, model (`claude-opus-5-5`) and `CADEX_EFFORT` recorded, then blind scoring under the frozen procedure.

Still open: A2's 60 s bar, before C1.

Assumption: telling the agent to state its concept in prose before `write_script` costs no refusal. The `DECISION:` lines only land from the closing paragraph, so the concept is repeated there.

Dispatch closed: 1 unit — CLI overlay design section rewritten as concept → skeleton → shell → refine with `look` (ADR-417), with order and well-formedness tests; reconcile and the probe are deferred.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 822b7abad28a32306705736c31faca97cd9250c2

## State Impact

- target: odd-tree-6681 — The CLI overlay's design section now teaches DESIGN-LANGUAGE §8's order as four numbered steps: concept first (silhouette, face, palette, proportion, stated before write_script and landed as DECISION: lines), skeleton, shell over skeleton (roles, 10-20% radii, joint caps, face on +X, taper, two materials plus one accent), then refine with look reading its measures first (ADR-417). Tests pin the order and the overlay's well-formedness. The reported cut-off PRINTABLE sentence was a misread line continuation. Still unmeasured: whether an unassisted turn follows it, which needs the first design-only probe.
