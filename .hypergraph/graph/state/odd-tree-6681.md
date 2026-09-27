---
node_id: 0b63aa4a-2f2b-5f45-91c3-78a2ef0bf5fd
slug: odd-tree-6681
title: A4. The product agent is taught the language, and learns less by refusal
created_at: '2026-09-27T15:18:35+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot10: **A4. The product agent is taught the language, and learns less by refusal.** The CLI overlay and API reference must teach the design language as something to do first: a concept (silhouette, character, palette and face) before geometry, then shell over skeleton, then refinement with `look`. Four hex2/hex3 refusal classes must be prevented at the source, each by the reference the agent reads or by an error that names the fix, and each with a regression test. The four are a wrong horn style name, `edit_script` before any script exists, more than one assembly or diagnostics output, and a joint missing or listed twice. A5's transcripts must show none of them recurring [rec: damp-dusk-8045].

- **Refusal classes closed at the source** (ADR-416, `f3699ba7`). Horn styles are listed in the library catalog note, and a wrong style names the intended one. `revision_rule` now says a refused candidate is rolled back and `edit_script` edits only the accepted source; it no longer claims a failed candidate becomes the working revision. `NO_PROJECT_SCRIPT` explains itself and carries `required_changes`. `result_contract` states the assembly result shape. The count refusal names the missing `assembly.solve` line, and unreturned joints and components are named by label [rec: light-tower-4418].
- **Regressions:** 14 in `cadex_tests/test_authoring_refusal_classes.py`, using the real hex inputs; 12 fail on the old source [rec: light-tower-4418].
- **Overlay teaches the design order** (ADR-417, `822b7aba`). The CLI overlay's design section teaches DESIGN-LANGUAGE §8 as four numbered steps. (1) Concept first: silhouette, face, palette and proportion, stated before `write_script` and landed as DECISION: lines. (2) Skeleton. (3) Shell over skeleton: roles, 10–20% radii, joint caps, face on +X, taper, two materials plus one accent. (4) Refine with `look`, reading its measures first. Tests pin the order and the overlay's well-formedness. The reported cut-off PRINTABLE sentence was a misread line continuation, not a defect [rec: solemn-hill-7272].
- **First behavioural evidence** (the `ot10-hexapod-1` transcript): **0 of the 4** hex refusal classes recur. There were 33 other refusals. 19 were the 300 CPU-s limit, since addressed by ADR-418 on the engine node. Sandbox import/directory refusals and guessed pointers still recur [rec: soft-spark-6990].
- **Hexapod attempt 2 transcript** (`ot10-hexapod-2`): **0 of the 4** classes recur; 10 refusals in all, CPU-limit refusals 3 (down from 19). One refusal tagged horn style by `refusals.py` was a false match on an output named `horn` — really the write_script drop-outputs guard [rec: quiet-basin-1176].
- **Quadruped transcript** (`ot10-quadruped-2`): **0 of the 4** classes recur; 11 refusals [rec: western-comet-0121].
- **Still open:** three transcripts clean so far (hexapod 1 and 2, quadruped); no biped A5 transcript is recorded yet. The node stays `open` until A5's transcripts are complete, and the human owns the checkbox [rec: damp-dusk-8045] [rec: western-comet-0121].

## Negative knowledge

None yet.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- light-tower-4418 — four refusal classes prevented in describe_api and named in the refusal (ADR-416)
- solemn-hill-7272 — overlay design section rewritten as concept, skeleton, shell, refine (ADR-417)
- soft-spark-6990 — first A5 transcript: 0 of 4 refusal classes recur; 33 other refusals, 19 of them the CPU cap
- quiet-basin-1176 — hexapod attempt 2 transcript: 0 of 4 classes recur, 10 refusals, CPU 3
- western-comet-0121 — quadruped transcript: 0 of 4 classes recur, 11 refusals
