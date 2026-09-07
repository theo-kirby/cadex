---
node_id: b9afe0a3-726b-5765-a24a-efcc0a8b90a1
slug: hidden-ridge-7342
title: Stop fifth-servo qualification at mounting interface mismatch
created_at: '2026-09-07T04:06:50+00:00'
parents:
- rough-gate-7949
summary: ''
---
## What

Completed the bounded fifth-servo source audit, not a delivery. Hitec HS-311
and HS-422 do not qualify for unchanged ServoPart. Added the audit, provenance
pointer, ADR-229 and a checked audit-only ROADMAP item.

## Why

Follow plan rank 1 and rough-gate-7949, serving mission 4 and the open
ancient-tide-5930/brave-stone-9609 frontier. The overseer asks for a maintainer
and planner pass, but this dispatch explicitly forbids reconciliation and
requires a contributor record. Assume that request belongs to the separate
maintainer dispatch; leave STATE, plan and state nodes untouched. No human wait.

## Method

Read STATE, PLAN, VISION, the actor/record contracts, catalog rows and ServoPart.
Inspect exactly two manufacturer Ver2.2 PDFs, downloaded by curl and rendered
with temporary uv/PyMuPDF (pdftoppm unavailable; pixi lacks fitz). Sources,
SHA-256 identities, datums, refusals and conditional proof obligations are in
docs/FIFTH-SERVO-AUDIT.md. No third candidate or runtime edit.

Run CADEX_ENGINE_ROOT="$PWD/build/engine/cadex-engine-0.0.0-macos-arm64"
pixi run python -m pytest -q src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py
src/Mod/cadex/cadex_tests/test_library.py. Compare source and staged catalog/API
hashes at HEAD 49a28a254ed4223d823dc8bf448dcd90730fe151. No build needed.

## Result

91 passed in 15.84 s, no failures/skips. Both catalog/API hash pairs match;
this is an existing local stage with external libraries, not a portable release
or whole-payload equivalence claim. git diff --check passes.

The recipe cannot reproduce the candidates' open mounting mouths using their
stated circular drills. Output stack evidence needs further qualification;
HS-422 also has inconsistent dimension labels. No independent candidate kernel
proof was attempted. Four servo identities remain; seven powered identities
under an inclusive count leave at least one servo and three powered identities
missing, without satisfying all breadth/L3 obligations.

Next: replan before ranks 2/3; qualify further mechanical evidence and a narrow
recipe decision or a different candidate in a new bounded unit. General
headless review and rollout video remain open. One pre-existing unreconciled
record was advertised; this adds one, with no maintainer work performed.
Dispatch closed: 1 unit — record two fifth-servo qualification blockers.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 49a28a254ed4223d823dc8bf448dcd90730fe151

## State Impact

- target: ancient-tide-5930 — Fifth-servo audit inspected HS-311 and HS-422; neither qualifies for unchanged recipe. Four servo rows remain; replan before candidate proof or delivery.
- target: brave-stone-9609 — ADR-229 pins manufacturer sources and interface blockers; packaged lifecycle/library baseline passes 91 tests without runtime changes.
