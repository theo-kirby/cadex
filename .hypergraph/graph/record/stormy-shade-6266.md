---
node_id: 45b1da77-7a41-5cfb-a918-1b4fb9277724
slug: stormy-shade-6266
title: Show identity-resolved policy origin and source-name disagreement in the persistent run panel (ADR-319)
created_at: '2026-09-13T09:25:14+00:00'
parents:
- easy-field-3407
summary: ''
---
## What

D4/D5: the run panel now shows the retained-byte-resolved policy origin through the existing policy_lineage reader, alongside the declared training source. It names the origin run, final/checkpoint/retained kind and checkpoint iteration, and highlights SOURCE-NAME DISAGREEMENT when the declaration differs. ADR-319 documents the new inspection-only GET /api/policy-origin/<run> route. The checkpoint list still describes its declared telemetry reference source separately. Added a headless-browser regression and strengthened the persistent video checker to assert the displayed origin and retain its text.

## Why

Bet: exposing the existing identity resolver in the operator's run panel closes the demonstrated D4/D5 provenance gap without changing project records or inferring origin from names. This follows the critic's concrete instruction and parent easy-field-3407, not the banned clearance plan. D4's policy identity and D5's interpretable historical records are the target; this is one finished UI/provenance unit, not a claim that the whole charter is done.

## Method

Used the Ouroboros actor and hypergraph-record skills, read the repository vision and recording contract. Added on-selection/request lineage lookup; ordinary two-second telemetry polling does not repeat policy hashing. Changes to the selected run's policy/training/status invalidate the lookup. Results explicitly say snapshot and offer Check again; absent origin, pending lookup and failed request are distinct. A request generation guard prevents late replies from changing a different selection. Rendering uses textContent, and the route uses the existing run-name validation and project-root-contained identity reader.

The browser regression uses playback quince and training first, resolves checkpoint iteration 2, changes the declaration to second and verifies the highlighted disagreement still names first, removes bytes and verifies explicit recheck becomes unresolved, then selects a final policy without a declared source. It verifies accepted selection, late rejected requests and successful retry of a failed lookup. Targeted command: pixi run python -m pytest cli/tests/test_review_server.py -q -k browser_policy_origin — 1 passed, 46 deselected in 2.71 s. An initial fixture typo passed the server object as URL and failed before navigation; corrected to server.url before these passes. Full suite: pixi run python -m pytest cli/tests -q -x — 446 passed, 1 skipped in 427.30 s, exit 0 (the final late-request/retry assertions also passed in the targeted run).

Restarted only the existing cadex-operator-review user service onto the patched server, leaving the same project and private URL selected. Ran PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/check_video.py "$HOME/cadex-projects/ot5-lark-copy85" lark86-retry-video "http://$(tailscale ip -4):8765/" --label origin92 — exit 0. Fresh selection RUN lark86-retry-video; origin lark86-retry, final, source_agrees true; eight components and recorded params/curves; playback preserved across three polls; download SHA256 1f53d43d1c187de363eadae51931e90d91e8a7928e25ce5ebdb70df46322ca01; 81 decoded differing frames, 8.1 encoded seconds for 8.0 simulated seconds, seed 0. Historical lark2-final selection and return to current passed. Accepted revision 7f6c23913d55184241d0b31ca0fdfddf17d3c613d0c25e17d5943af57c75661b; policy 074e22f1070c0162ac335394f7c39d0775ed6bd3a58018942d8bc79f1c59c688. Evidence stays in the working project's evidence/lark86-retry-video-origin92-check.json and -browser.png, plus evidence/origin92-panel.png inspected visually. Same-machine private-address evidence only, no second device or new training claim.

## Result

The persistent dashboard remains active on port 8765 with ot5-lark-copy85 and its latest lark86-retry-video. D4/D5 gain operator-visible provenance and a conflicting-source browser proof; D10 is reverified on the actual working project. Docs/CLI.md and the operator status document explain the behavior. No dependency, engine, shell, process protocol or payload changes; no build or engine gate needed for this CLI UI unit. No project artifacts were overwritten; only new evidence receipts were added outside the checkout. No whole-goal completion claim.

Handoff: the containment arc was already finished; this iteration implemented the critic's next provenance unit and verified real playback/download. The tail reaches three records; a separate authorized reconcile pass is due, but this dispatch explicitly forbids reconciliation or state edits. After that, I would check D11 on the current Lark copy at equivalent pose/camera against the reference: the state still cites Wren evidence, whereas the live project is Lark. Keep this within visual review, not gait research or the stale clearance plan. The origin panel deliberately reports a snapshot rather than continuously rehashing all retained policy files; Check again handles out-of-band retention changes.

Dispatch closed: 1 unit — expose identity-resolved policy origin and source-name disagreements in the persistent review dashboard.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 35b6b741cdb5b61730248819639bf776af8dc15a

## State Impact

- target: candid-harvest-2614 — D4 run panel now displays retained-byte policy origin, kind and checkpoint iteration independently of declared source; explicit disagreement, missing and failed states; real persistent final-video playback/download and displayed origin verified; CLI 446 passed, 1 skipped
- target: sharp-union-6036 — D5 historical run panel exposes conflicting declared origins without replacing the identity-resolved source; browser covers unrelated names, conflict, missing bytes, final origin without declaration, stale request isolation and retry
- target: deep-clover-6012 — Persistent port 8765 still serves ot5-lark-copy85 with lark86-retry-video default; patched server restarted and browser verifies lark86-retry final origin, history, polling playback and hash-equal download; new origin92 project-local evidence
