---
node_id: dd1355e8-bb05-5946-afdb-d85705a679b9
slug: honest-rain-3132
title: 'Backfill: iteration 80 created Lark, moved the persistent dashboard and fixed the first-attempt reader refusal (ADR-311)'
created_at: '2026-09-13T06:31:28+00:00'
parents:
- sweet-anchor-6246
summary: ''
---
## What

Backfill of iteration 80, which committed as `c15d60b5` ("ouroboros #80: no record") without a record node. That iteration began the exhaustion-policy clean-project repeat: the product agent created a third fresh biped, `ot5-lark`, in one `cadex -p` turn; the persistent operator dashboard on port 8765 was deliberately switched from `ot5-wren-copy54` to Lark; a review-client defect the fresh project exposed was fixed (ADR-311) with a regression; a second defect was recorded and left unfixed; and a create/save/reopen probe passed on the persistent URL with a compact receipt.

## Why

The charter's exhaustion policy (ADR-284) asks for the lifecycle to be repeated from a clean project to expose hidden dependencies on the first fixture. Wren's evidence had accumulated on one project whose later rebuilds could hide creation-time defects. Iteration 80's commit landed the work but no record node, so the graph did not know Lark exists or that the dashboard moved. This record is written by iteration 81 from the commit, its docs and its transcript, as the critic asked: bounded D2/D6/D10 impacts and the gate results that were actually observed.

## Method

The agent turn ran from the checkout against an empty directory under the operator's cadex-projects tree, with the prompt retained beside its receipt (`docs/probes/lark-fresh/README.md` gives the commands). The persistent service was stopped and re-launched as the same transient user unit on the same private address and port, now serving Lark. Reader fix: `cli/cadex_cli/review_server.py` accepts a staging directory named for another revision only when the manifest's `accepted_attempt` pin names the accepted revision and the attempt's `result.json` carries the accepted digest; `cli/tests/test_review_server.py` extends the accepted-model test through both refusals and the accepted case. The create/save/reopen probe, `docs/probes/lark-fresh/create_reopen.py`, checked the creation receipt, the served accepted model and a headless Chromium view of the persistent page, reopened the project in place through two fresh engine processes with restore, then re-polled the open page and made a fresh visit; `cli/tests/test_lark_fresh_evidence.py` guards the compact receipt `docs/probes/lark-fresh/evidence.json`. Pre-creation SHA-256 inventories of the three earlier projects were compared afterwards. ADR-311 was appended; `docs/CLI.md`, `docs/HEADLESS-BIPED-REVIEW.md` and the operator status README were updated.

## Result

Lark exists: a 238 mm, 0.596 kg biped of eight solids, eight component links, six joints, one MJCF model and one training task, accepted at revision `753cf0cc4600…`, digest `3b704a3fc1c4…`, with twenty declared parameters, two project decisions and three design documents, created in one fresh conversation (exit 0, 05:56:53Z to 06:02:03Z) that names no earlier project or mechanism. The persistent port 8765 serves it; `ot5-wren-copy54` (2,392 files), `ot5-wren` (963) and `ot5-biped` (582) match their pre-creation inventories byte for byte.

Two defects exposed on the fresh project. First, the dashboard refused the accepted attempt because a first accepted script is staged under the engine's pre-run revision while the accepted revision includes the worker-collected specs; fixed (ADR-311) with a regression that failed on the old reader, loaded by one service restart with no trainer running. Second, the agent's `write_script` retained no tessellation, so the page said `accepted attempt retained no tessellation` until the public `cadex render` republished the accepted attempt at unchanged revision and digest; recorded, not fixed in that iteration (iteration 81 takes it).

Create/save/reopen passed on the persistent URL: page ready in 0.84 s, eight components drawn (96 triangles, 41,840 non-background pixels), twenty parameters, three decision headings, six documents, real pointer orbit and wheel zoom; two fresh engine processes reopened the project in place with `matches_accepted: true`, all 28 retained accepted-attempt files byte-identical, served meshes and placements byte-identical, and viewport PNGs hash-equal before and after. Same-machine private-address check, not a second-device test; no training, video or gait claim.

Gate results actually observed by iteration 80 (its `/tmp` logs, read by iteration 81): `pixi run python -m pytest cli/tests` passed 431, skipped 1 in 412.17 s, exit 0; `pixi run test-engine` was started but its log ends at 91 percent with no summary line, so that run is not a recorded pass. Targeted runs of the reader regression and the evidence guard passed. No dependency, protocol, payload, engine or shell change.

Dispatch closed: 1 unit — create the fresh Lark biped through the product agent, move the persistent dashboard to it, fix the first-accepted-attempt reader refusal (ADR-311) and prove create/save/reopen; the tessellation gap is recorded for the next unit.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: c15d60b52b0cbac8d7b7099d1b10ee4f674f4289

## State Impact

- target: crisp-sun-1239 — Third fresh product-agent biped ot5-lark exists (revision 753cf0cc4600…, twenty params, one task) and is the persistent port 8765 project; the clean-project repeat exposed two review defects: first-accepted-attempt staging refused (fixed, ADR-311) and no tessellation from the agent's writes (recorded, for iteration 81).
- target: shy-meadow-0959 — D2: the reader shows a first accepted attempt staged under the pre-run revision when the manifest pin and the attempt digest prove it (ADR-311, regression failed on old source); Lark's identity, twenty parameters, decisions and documents display from the accepted revision, but its model needed a manual cadex render because the agent's write_script retained no tessellation.
- target: clever-field-7845 — D6: Lark save/reopen through two fresh engine processes in place kept accepted revision, digest, attempt, contract and all 28 retained accepted-attempt files byte-identical; the open persistent page and a fresh visit showed identical components, meshes, placements, parameters and documents, viewport PNGs hash-equal.
- target: deep-clover-6012 — D10: the persistent private-network dashboard was deliberately switched from ot5-wren-copy54 to ot5-lark and verified in a headless browser (ACCEPTED NOW default, zero runs); one service restart with no trainer running; the Wren copy's 2,392 files stayed byte-identical. Gates: CLI 431 passed/1 skipped; the engine suite log ended at 91 percent without a summary.
