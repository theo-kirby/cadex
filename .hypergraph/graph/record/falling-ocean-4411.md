---
node_id: 4d7112d4-5caa-535f-b2ca-2538cd988dd4
slug: falling-ocean-4411
title: Serve current Reed work on the persistent operator dashboard
created_at: '2026-09-12T21:18:09+00:00'
parents:
- simple-raven-5405
summary: ''
artifacts:
- docs/probes/operator-review/evidence.json
---
## What

Moved the persistent private-network port 8765 dashboard from ot4-carriage to the active independent Reed working copy, ot5-biped-copy29, and changed fresh visits to open current work (ADR-299). Added browser regressions, a reusable read-only persistent-server probe, operating/status documentation and a landed roadmap item.

## Why

Advances D10 under crisp-sun-1239, following the owner directive simple-raven-5405 and the critic's requested immediate acceptance check. Confirmed .ouroboros/runs/ot5/loop.log line 139: 2026-09-12T21:07:35+00:00 charter reloaded before iteration 37: c661528473bd. The independent copy is the most recent actual working project; prior product-agent revision requests produced no new walk attempt. No quota retry, cache audit, substitute design, new training or reconcile was performed.

## Method

Inspected the existing listener and confirmed it served ot4-carriage. Stopped that review process and launched the documented systemd-run user service cadex-operator-review with Restart=on-failure, the same Tailscale address and port 8765, and the Reed copy. This service remains detached from the actor and browser tests. The command in docs/probes/operator-review/README.md uses portable environment-relative paths. It is a transient user service, not a reboot installation.

The browser selects the newest running/pending record with fresh starting/training telemetry, otherwise the last record in the reader's oldest-first ordering (record time, then run name), regardless of success. No runs opens accepted geometry. Untouched pages follow on polls; deliberate selections and observed video playback pin the view. Current run names the live target and returns to following. Existing identity, stale/error, geometry, video and artifact readers are unchanged.

Regression browser tests cover fresh active-training priority over a newer failure, selection after failure, fresh visits to the newest failure, stale telemetry not taking active priority, historical identity preservation, return to current, and real browser playback retaining its video element when a newer failed attempt appears. Tests for accepted-view behavior now explicitly select that view. The real persistent probe command is PYTHONPATH=cli:cli/tests pixi run python docs/probes/operator-review/verify.py <private-url>:8765/ <operator-projects>/ot5-biped-copy29 copy100. The probe never starts or stops a server. Compact output is committed as docs/probes/operator-review/evidence.json and retained project-locally as evidence/operator37.json.

## Result

The shared operator page now opens copy100, completed at revision 25d9b6ab7472b968a3a72691ca44113ea86beda85802af3e22d9270952cb71fc, with the recorded 100 mm foot parameter, loaded model, reward curve and playable/downloadable saved video. Video SHA-256 is 2308fe3baa4d0a5a2256a37deadfa798256ab6cca978ff8daeacc56c76a2ab24. Historical probe3-final remains selectable at its own revision, polling preserves the selection, and Current run returns to copy100. Nine retained runs remain visible. Server remains active on the original private-network port, including after browser exit.

This is same-machine headless Chromium over the private address, not a second-device test or new GPU experiment. D10's immediate obsolete-project acceptance check now passes; its persistent-URL experiment-start/completion evidence remains open, as does D9 product-agent revision authorship. No new dependency, protocol/payload/engine/shell change, full build, state/plan/generated-view edit or charter edit.

Validation: initial focused reader/lifecycle run had 30 passed, 1 skipped and two failures caused by old accepted-default assumptions (including the copy fixture compiled before its update). Accepted-specific assertions now explicitly select accepted. Focused current-selection/playback/accepted-identity regressions: 3 passed in 7.22 s. Full engine suite: 2103 passed, 54 skipped in 284.33 s. No build required for the CLI static-page change.

Final full CLI gate with CADEX_REVIEW_HOST set to the private address: 373 passed in 359.20 s, no skips. The persistent private-address probe passes again after both suites, byte-identical to the committed compact evidence; systemctl reports the operator server active. git diff --check passes. Hypergraph export/check and commit close this unit; no generated views or state nodes were edited.

Dispatch closed: 1 unit — serve current Reed work on the persistent dashboard and preserve historical review

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 89b2a34f7777bf9e34450c8c8a34075bb8b1dae6

## State Impact

- target: crisp-sun-1239 — D10 immediate acceptance passes: persistent port 8765 serves Reed copy29/copy100 with current-attempt default, historical/playback preservation and private-address browser evidence; real experiment-spanning persistent-URL evidence remains open.
