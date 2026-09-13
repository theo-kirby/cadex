---
node_id: 856ff141-5497-5419-b4f4-9cfa55f647a9
slug: crimson-bell-5375
title: Wren copy edit and review with original unavailable
created_at: '2026-09-13T01:09:08+00:00'
parents:
- smooth-pine-9795
summary: ''
artifacts:
- docs/probes/wren-fresh/COPY.md
- docs/probes/wren-fresh/copy_lifecycle.py
- docs/probes/wren-fresh/copy-evidence.json
---
## What

Exercised Wren's independent whole-project copy with the original path unavailable throughout a copy-only public-CLI parameter edit, two fresh engine restores and browser review on a second server and the persistent private URL. Added the executable assertion-based lifecycle test, compact receipt and user-facing reproduction/status documentation. Port 8765 remains running on ot5-wren-copy54.

## Why

Follows smooth-pine-9795 and implements the critic's requested Wren D7 copy lifecycle instead of repeating provider probes. Advances cold-vale-4232 (D7) and deep-clover-6012 (D10). The 105→110 mm foot edit with policy disabled is solely a reversible isolation test, not a gait hypothesis or a product-agent-authored revision. D9's Wren authorship gap remains open. No retraining was requested for this bounded unit and none is credited.

## Method

Confirmed no trainer was running, copied the complete stopped-writer ot5-wren directory with `cp -R`, switched cadex-operator-review to ot5-wren-copy54 on the same private-address port 8765, and checked current identity with current.py. Ran `PYTHONPATH=cli:cli/tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python docs/probes/wren-fresh/copy_lifecycle.py "$HOME/cadex-projects/ot5-wren" "$HOME/cadex-projects/ot5-wren-copy54" "http://$(tailscale ip -4):8765/"`. The script asserts the copy contains all source files, inventories every original file, renames the source directory to an unavailable sibling, sets foot_len=110 and policy_on=0 through ./cadex params, calls render, restores the accepted copy through two fresh engine processes, starts a second real CLI review process, and checks both servers with headless Chromium. It restores the original path in finally and stops only the second server. No source path or original artifact can resolve at its former location during the edit, restores or browser checks.

Every retained run loads eight components and its recorded model revision/digest and effective foot parameter. All three curve lengths equal that run's retained progress file (19 at checkpoint 20, 240 for training/final). Both servers return identical historical model mesh hashes. All four videos play, survive polling and download with matching SHA-256; accepted view shows the changed revision, 110 mm feet, disabled policy and no substituted video; return-to-current selects wren2-final as historical. The original is inventoried again after restoration and final operator verification. Screenshots, inventories, CLI logs, restore receipts and full browser receipt stay under copy-local evidence/copy54 and evidence/copy54-restore. Compact evidence is docs/probes/wren-fresh/copy-evidence.json; COPY.md and the operator README document the live working copy and reproduction. The accepted persistent screenshot was visually inspected.

## Result

The real lifecycle passes. Original revision 26332a5955e3a044b968e3ec14eec809d2090dfe10922c4f242c1a5a12bdc477 and digest 4a3642fad859de19c197e33f6421811805c68bf06e2b7511f414acb3870cc845 are unchanged. All 1,566 original files remain byte-identical (inventory SHA-256 facfbb4ec7dbf9ab7ae4ce14e29932352de2c2e448b15e8eabad4f414e18b796). Copy accepted revision is 5b61ef31ff134f0f31b079347d9e5d3fd6aec236f12ad9c7b45910640388d7e6, digest b04439061b0278903fca11079ff0937dac12425a5a8b767e675e24542c7a4ea4. All 232 retained run/asset files (228 run files and four assets) match original bytes, inventory digest 78dfa559a74a1d7a122ffb0a2d50812d5f8eaa603daaf96a714cf53bca3fb6f7. Six run models/curves and four videos are independently reviewable. Persistent service is active on the copy after final browser verification; fresh visits select retained wren2-final, visibly HISTORICAL relative to the untrained copy edit. The copy's project DECISIONS.md explicitly records isolation-only caller authorship. Original path restored successfully.

Two first-draft assertions were wrong: original training runs use declared foot defaults rather than explicit overrides, and checkpoint snapshots retain 19 points, not 240. Fixed the probe to compare recorded defaults/overrides and each retained progress file. The failed copies remain outside the repo for audit; no project defect was inferred and no history was deleted. Evidence is same-machine private-network, not a second device. Original path unavailability is not a claim of OS-wide access denial to its renamed directory. No new Wren training, video rendering, D11 comparison, product-agent authorship, dependency, product behavior, engine/protocol/payload/shell change or build. No state/generated view edits or reconcile; tail now has three contributor records.

Verification: `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run test-engine` passed 2110 tests, 53 skipped in 262.02 s; `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m pytest cli/tests` passed 397 tests, 1 skipped in 384.60 s. Full logs are copy-local evidence/copy54/engine-tests.log and cli-tests.log. Real browser lifecycle, final current.py, compact-receipt consistency and git diff --check pass. Hypergraph export/check pass with no violations or warnings.

Dispatch closed: 1 unit — Wren independent-copy edit/reopen/browser lifecycle with original unavailable and persistent working-copy review.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 8317b607610a3d8c533627f555c2aa86ef15d375

## State Impact

- target: cold-vale-4232 — Wren whole-project copy accepts isolated 110 mm foot edit and two engine restores with original path unavailable; six retained models/curves and four videos pass on independent servers; all 1566 source files and 232 copied run/asset files unchanged. No copy retraining claimed.
- target: deep-clover-6012 — Persistent private port 8765 deliberately switched to ot5-wren-copy54 and verified at start/completion; current wren2-final remains visibly historical relative to accepted untrained 110 mm copy; server stays running.
