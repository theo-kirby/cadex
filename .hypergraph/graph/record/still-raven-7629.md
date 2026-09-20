---
node_id: ce6baf0e-438a-5f99-bced-c66b344679b4
slug: still-raven-7629
title: 'F9: packaged restore and reopen preserve all retained designs'
created_at: '2026-09-14T21:27:40+00:00'
parents:
- keen-quill-2265
summary: ''
artifacts:
- docs/probes/ot7/retained/README.md
- docs/probes/ot7/retained/restore-open.json
---
## What

Closed F9's retained restore/open evidence using the current packaged engine on fresh copies of all three ot6 designs. Added a user-facing explanation and a compact receipt at docs/probes/ot7/retained/restore-open.json. No product or design code changed.

## Why

The critic requested the remaining F9 restore/open checks, accepted-identity preservation and comparison against pinned fixtures. This unit follows that request and advances eager-summit-3153. F4 was deferred until the provider's reported reset, with no further invocation. The contributor-only dispatch forbids reconcile; no state nodes or generated views were edited.

## Method

Copied each retained script, metadata, accepted attempt and policy assets into external cadex-projects/ot7-open-finch, ot7-open-robin and ot7-open-heron. The external reproducible probes are ot7-retained-open/evidence/restore.py and compare_rebuilt.py. Each copy was opened twice with restore=True in separate fresh CadexdClient processes against build/engine/cadex-engine-0.0.0-linux-x64. The payload's 56 top-level Python files match the current source; the receipt separately pins manifest and executable hashes. No build was needed.

Recorded replies, metadata snapshots, clearance reports and fit reports project-locally. Asserted all metadata fields except latest_candidate and updated_at remain equal, including accepted revision, digest, contract, attempt pointer and parameter values. Script and pinned result bytes stay equal. Hashed the source scripts, metadata, assets and artifacts before and after, proving no source changes. Compared all published pair numbers with the portable fixtures, then independently compared each newly generated restore candidate result.json with those fixtures. This second comparison proves rebuild measurements, rather than only readability of the pinned accepted artifact. No explicit acceptance, design edits, smoke, training or provider call occurred.

## Result

All six opens succeeded with performed=true and matches_accepted=true. Restore/reopen elapsed seconds: Finch 7.334677/7.174597; Robin 5.155880/5.104954; Heron 2.251697/2.254331. Every accepted identity field and script remains unchanged; only latest_candidate and updated_at change during ordinary restore. All 787 pairs match exactly in each published read and each rebuilt candidate: zero changed distances, volumes, added or missing pairs. There is no new defect needing a regression. Static fit remains failing at 44/39/20, with no world geometry and unavailable sweeps. Differences from ot6 remain exactly the prior contact/thread classification and ADR-353 threshold explanations; restoration success is not fit success.

Packaged lifecycle gate: 18 passed in 11.52 s. Receipt assertions and git diff --check pass; the committed receipt is 13,281 bytes and carries portable evidence paths and digests. Full suites were not rerun for this documentation/experiment unit: latest evidence remains engine 2,142 passed/53 skipped and CLI 684 passed/1 skipped from preceding units. F9's retained restore/open gap is closed; this does not claim the whole charter complete. No new dependency, direction change, historical-run rebuild or dashboard change. Next work returns to the remaining agent criteria when the provider can run. The tail is now two unreconciled records; contributor rules still prohibit reconciliation.

Dispatch closed: 1 unit — packaged restore/open and exact rebuilt-measurement comparison for all three retained designs.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 43087eff7c73ad5eb248e76950f51321131b761c

## State Impact

- target: eager-summit-3153 — Retained restore/open gap closed: six fresh packaged opens preserve accepted identity; published and rebuilt measurements match all 787 pinned pairs exactly; packaged lifecycle gate 18 passed. Static failures remain 44/39/20 and sweeps unavailable.
