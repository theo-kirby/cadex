---
node_id: 0b63aa4a-2f2b-5f45-91c3-78a2ef0bf5fd
slug: odd-tree-6681
title: A4. The product agent is taught the language, and learns less by refusal
created_at: '2026-09-27T15:18:35+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run ot10: **A4. The product agent is taught the language, and learns less by refusal.** The CLI overlay and API reference must teach the design language as something to do first: a concept (silhouette, character, palette and face) before geometry, then shell over skeleton, then refinement with `look`. Four hex2/hex3 refusal classes must be prevented at the source, each by the reference the agent reads or by an error that names the fix, and each with a regression test. The four are a wrong horn style name, `edit_script` before any script exists, more than one assembly or diagnostics output, and a joint missing or listed twice. A5's transcripts must show none of them recurring [rec: damp-dusk-8045].

**Where it stands:** every item has measured evidence. The four classes are closed at the source with regressions, the overlay teaches the design order, and a mechanical census of all 14 ot10 transcripts finds **0 of 183 refused calls** in the four classes. Status is `working` because the evidence is complete. The human owns the checkbox; roles do not tick it [rec: true-grove-4773].

- **Refusal classes closed at the source** (ADR-416, `f3699ba7`). Horn styles are listed in the library catalog note, and a wrong style names the intended one. `revision_rule` says a refused candidate is rolled back and `edit_script` edits only the accepted source. `NO_PROJECT_SCRIPT` explains itself and carries `required_changes`. `result_contract` states the assembly result shape. The count refusal names the missing `assembly.solve` line, and unreturned joints and components are named by label. Regressions: 14 in `cadex_tests/test_authoring_refusal_classes.py`, using the real hex inputs; 12 fail on the old source [rec: light-tower-4418].
- **Overlay teaches the design order** (ADR-417, `822b7aba`). The overlay's design section teaches DESIGN-LANGUAGE §8 as four steps: concept first (landed as DECISION: lines before `write_script`), skeleton, shell over skeleton, then refine with `look`. Tests pin the order [rec: solemn-hill-7272].
- **Face rules made checkable** (ADR-422, `c3abb3ab`): the face spans at least half the body's width and a quarter of its height from +X, contrasts with its surround, and is checked from `right` before accepting. The regression test fails on the old overlay [rec: rustic-ivy-4753].
- **Refusal census** (`docs/probes/ot10/runner/refusals.py`, `docs/probes/ot10/refusals.json`, commit `4284a560`). It covers all 14 ot10 transcripts: the counted biped-1, quadruped-3 and hexapod-10 (7, 15 and 10 refusals), the nine failed attempts, and the two aborted turns. Each class is matched on the engine's exact refusal sentence in both the old and the ADR-416 wording, not on a keyword. The earlier `horn|style` counter false-matched an output named `horn` on hexapod-2 [rec: quiet-basin-1176]. Six contract tests in `cli/tests/test_ot10_contract.py` pin per-project counts and hold the README table equal to the JSON. They re-run the census against local transcripts when the sha256 values match (it ran on all 14 here). `cli/tests`: 1055 passed, 1 skipped [rec: true-grove-4773].
- **What remains outside A4** (183 refusals): CPU limit 44, sandbox 32, kernel 29, guessed JSON pointer 22, `Cannot retire` a linked output 15, edit replacement 10, reset variation 7, outputs dropped 3, other 21. Every `other` refusal was read by hand, and none is an A4 class. CPU limit is the largest class; A5 tracks it [rec: true-grove-4773].

## Negative knowledge

- [scope: ot10 refusal counting | confidence: high | evidence: quiet-basin-1176, true-grove-4773] A keyword counter (`horn|style`) over refusal text false-matches output names. Classify on the engine's exact refusal sentence or `failure_code` instead.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- light-tower-4418 — four refusal classes prevented in describe_api and named in the refusal (ADR-416)
- solemn-hill-7272 — overlay design section rewritten as concept, skeleton, shell, refine (ADR-417)
- soft-spark-6990 — first A5 transcript: 0 of 4 refusal classes recur; 33 other refusals, 19 of them the CPU cap
- quiet-basin-1176 — hexapod attempt 2 transcript: 0 of 4 classes recur, 10 refusals, CPU 3
- western-comet-0121 — quadruped transcript: 0 of 4 classes recur, 11 refusals
- tiny-dusk-3648 — hexapod attempt 3 transcript: 0 of 4 classes recur, 20 refusals (folded as derivable; its impact line targeted A5 only)
- rustic-ivy-4753 — ADR-422: face size, contrast and look-from-+X rules in §4 and the overlay, regression test; attempt 4 transcript 0 of 4, 14 refusals
- true-grove-4773 — mechanical A4 census over all 14 ot10 transcripts: 0 of 183 refused calls in the four classes, pinned by contract tests and published; per-transcript counts above compacted into it
