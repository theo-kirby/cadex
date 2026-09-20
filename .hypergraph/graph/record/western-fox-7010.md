---
node_id: d7d5be3f-afc4-5b15-b4c5-07a260cfe37c
slug: western-fox-7010
title: 'F4: assess original horn attachments independently of zero fit failures'
created_at: '2026-09-14T22:57:25+00:00'
parents:
- long-falcon-7461
summary: ''
---
## What

Added a fixture-backed F4 repair geometry assessment to the frozen collector. Before and after reads now retain and hash repair-assessment.json with the accepted revision, static fit, and explicit measurements for both original horn attachments.

## Why

Advances F4 (polished-forest-0215), following long-falcon-7461's real preserved-seed measurement: both 0.2 mm disconnected horn attachments pass the default clearance threshold without declared contact intent. The critic requested a frozen repair after reset, or this assessment while reset remained ahead. At 2026-09-14 22:45:59 UTC (18:45:59 New York), the documented 20:20 reset was still ahead, so this is the requested fallback. No provider call, baseline reread, pagination variant, design edit, or prompt change occurred.

## Method

The runner recomputes static fit from accepted clearance geometry and independently evaluates comp_horn_shoulder/comp_upper_arm and comp_horn_elbow/comp_forearm as contacts through the existing CLI pair classifier. Distances must be within 0.001 mm and common volume within 0.000001 mm³. Both attachment checks and static fit must pass. Missing, renamed, duplicate, errored or stale attachment evidence stays unknown. Reads must exit successfully and match accepted revision; missing world-geometry evidence cannot pass. Nonfinite values remain unknown and serialize as null in the assessment; raw evidence is retained separately.

Fixtures cover the zero-summary-failure 0.2 mm gaps, touching within tolerance with declared contact, floor geometry, 248.2 mm³ servo overlap, overlapping horns, missing/renamed/duplicate pairs, nonfinite and errored measurements, revision mismatch, unavailable reports, failed reads with leftover files, and before/after artifact hashes. The assessment does not infer replacement identities or claim that a provider completed a repair. Updated runner documentation and ADR-354's extension.

## Result

F4 now has an integrated geometry assessment that cannot treat zero static failure_count as proof of repairing the original disconnected horns. F4 remains open: no real repair turn or successful before/after repair evidence exists from this unit. Renamed or replaced attachments require separate identity/function evidence and remain unknown here. No new dependency; no engine, protocol, payload, dashboard, or acceptance behavior changes. No build or engine gate was required for this runner-only change.

Validation: `pixi run python -m pytest cli/tests -q` exited 0: 718 passed, 1 skipped in 528.12 s. The final focused run, including the added nonfinite-receipt case, passed all 33 runner tests in 0.37 s. `git diff --check` passed. The full suite started before the final receipt-normalization assertion was added; the final focused run verifies that completed runner change.

Dispatch closed: 1 unit — assess original F4 horn attachments from measured geometry.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 49d7ad17ebc8afb7d11b41f8cdcf0d95fa528ce9

## State Impact

- target: polished-forest-0215 — The frozen repair collector now retains before/after geometry assessments requiring static fit plus measured contact at both original horn attachments. Fixture tests catch unflagged 0.2 mm gaps and preserve missing or renamed evidence as unknown. No real repair ran before the provider reset; F4 remains open.
