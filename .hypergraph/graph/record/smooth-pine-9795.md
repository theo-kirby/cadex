---
node_id: 156631dc-5c53-5bc6-a470-58f74d7fc2b3
slug: smooth-pine-9795
title: Wren product-agent revision refused by provider; retained review verified
created_at: '2026-09-13T00:59:08+00:00'
parents:
- frosty-birch-2464
summary: ''
artifacts:
- docs/probes/wren-fresh/AGENT-REVISION.md
- docs/probes/wren-fresh/agent-attempt-evidence.json
---
## What

Attempted Wren's requested product-agent geometry revision with the measured comparison and all four retained policy review records. Both the stored Fable model and explicit Sonnet fallback refused at their provider session limit, before authoring a change. Added a user-facing attempt/retry report and compact receipts; verified accepted identity and all retained run files and browser reviews on the persistent operator server.

## Why

Follows frosty-birch-2464 and the critic's request to close Wren's explicit D9 product-agent revision authorship gap. The requested design change did not happen because both actual public-CLI product-agent turns exited 1 with no outputs or accepted revision. Instead of silently making another caller parameter edit, this unit records the provider-capacity dead end, gives reproducible retry instructions, and checks D5/D10 preservation. No earlier parameter edit receives retroactive product-agent credit.

## Method

Before either turn, retained script.py, script.json, agent.json, DECISIONS.md and a SHA-256 inventory of all 228 runs/ files in project-local evidence/agentrev53. Passed a 47,725-character prompt containing the complete comparative report and the four run.json/review.json inputs to `timeout --signal=TERM --kill-after=10s 900 ./cadex --project "$HOME/cadex-projects/ot5-wren" --out "$HOME/cadex-projects/ot5-wren/evidence/agentrev53/output" --json -p "$(cat "$HOME/cadex-projects/ot5-wren/evidence/agentrev53/prompt.txt")"`. Second invocation added `--model claude-sonnet-5` and used sonnet-output. Full stdout/stderr remain project-local. No model choice was changed in the Codex actor; these are product CLI provider attempts. The prompt asked the product agent to choose one geometry hypothesis, preserve task settings and history, disable the old policy and provide its actual DECISION/NOTE rationale. It specified no new dimension.

Ran current.py against the persistent private-network URL before the attempts, then a project-local adaptation of revision.py afterward: `PYTHONPATH=cli:cli/tests pixi run python "$HOME/cadex-projects/ot5-wren/evidence/agentrev53/verify.py" "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren"`. It hashes the full retained inventory, checks manifest identity/script/decisions, exercises all four review selections, model foot mesh extents and identities, eight components, curves, verified-policy video labels, playback across three explicit polls, downloads, accepted view and return-to-current. Screenshots and verifier remain project-local; accepted screenshot inspected. Compact path-free receipts are docs/probes/wren-fresh/agent-attempt-evidence.json. docs/probes/wren-fresh/AGENT-REVISION.md documents the failed design turn, retention and retry; Wren and operator READMEs link it.

## Result

Neither model authored a revision or design rationale. Both returned `You've hit your session limit` and exit 1. Wren's accepted revision remains 26332a5955e3a044b968e3ec14eec809d2090dfe10922c4f242c1a5a12bdc477, digest 4a3642fad859de19c197e33f6421811805c68bf06e2b7511f414acb3870cc845. Script, accepted identity, effective parameters and decisions are unchanged. Reopen refreshed only manifest updated_at and latest_candidate.attempt_id; candidate revision/digest/status/output count remain equal. All 228 run files match inventory digest 57a1df199d9982e3f79be79af1c41db3e0fdbd260a511dfe552e1778b7e38582. Six dashboard entries remain (two training runs, four policy reviews); four videos play/download with recorded hashes. Fresh/current/accepted selects unchanged wren2-final identity, prior revisions remain HISTORICAL, accepted policy_on remains 1 and feet remain 105 mm. No new training run was created and none is active. Port 8765 stays on Wren, service active without restart. Browser evidence is same-machine private-address, not second-device evidence.

The first verifier draft overasserted byte-identical reopen metadata; the second carried an obsolete wren1-final default from iteration 50. Corrected both probe assumptions and the complete browser check passed. No product defect was inferred. The explicit fallback persists claude-sonnet-5 in agent.json, documented for the next retry. Assumption: selecting the existing supported Sonnet model was a reversible routine response to Fable refusal; no provider stack or dependency was introduced. No engine/protocol/payload/trainer/shell behavior changed, no removal/direction change or build. D9's Wren revision gap remains open; do not start retraining and call it an agent revision. Retry through the product CLI when provider capacity is available, retaining a fresh inventory and actual rationale. The unreconciled tail now grows by this one contributor record; no state nodes or generated views were edited.

Verification: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run test-engine` passed 2110 tests, 53 skipped (260.89 s). Full CLI suite with the same bounds passed 397 tests, 1 skipped (383.10 s). Both logs retained in evidence/agentrev53. Persistent browser, compact-receipt consistency and git diff --check passed.

Dispatch closed: 1 unit — Wren product-agent revision refusal, retained-history browser verification and documented retry.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 39cbd53e33c52e2096102121731021439143625a

## State Impact

- target: silent-river-6649 — Wren product-agent revision attempted through CLI with comparison and retained reviews; Fable and Sonnet both refused at session limit, no authorship or geometry change claimed; retry documented.
- target: deep-clover-6012 — Persistent Wren dashboard remains on wren2-final after failed design turns; accepted/current/historical identity and all four video playback/download checks pass, service stays active.
- target: sharp-union-6036 — All 228 Wren run files preserved byte-for-byte across two provider-refused design turns; accepted script/digest/parameters and decisions unchanged.
