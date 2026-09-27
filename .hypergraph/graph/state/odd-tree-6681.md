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
- **Still open: behaviour.** No unassisted turn has yet shown that the agent follows the overlay; that needs the first design-only probe [rec: solemn-hill-7272]. No A5 transcript yet shows that the four refusal classes do not recur [rec: light-tower-4418]. The node stays `open` until this evidence exists, and the human owns the checkbox [rec: damp-dusk-8045].

## Negative knowledge

None yet.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- light-tower-4418 — four refusal classes prevented in describe_api and named in the refusal (ADR-416)
- solemn-hill-7272 — overlay design section rewritten as concept, skeleton, shell, refine (ADR-417)
