---
node_id: 941b7146-a258-5490-ad7a-f11ebd19e258
slug: simple-quartz-9812
title: Verify saved biped artifacts across engine and dashboard restart
created_at: '2026-09-12T19:09:09+00:00'
parents:
- light-brook-2640
summary: ''
artifacts:
- docs/HEADLESS-BIPED-REVIEW.md
---
## What

Exercised the fresh biped's saved real artifacts through two engine restores and a dashboard process restart, and documented the passing completed-run portion of D6 in docs/HEADLESS-BIPED-REVIEW.md. The external project contains the executable browser/protocol harness and detailed receipts; no product code changed.

## Why

This unit follows light-brook-2640's completed probe3 artifacts and advances D6, the critic's requested next lifecycle experiment. The critic requested reconciliation first, but this dispatch explicitly forbids the reconcile skill, state/view mutations and hypergraph update with no exceptions and requires one work unit. I obeyed that narrower dispatch restriction: no reconciliation, generated view edit or clearance work occurred. The critic's scheduled reconcile remains pending; its replacement plan should prioritize active-training restart during design-change retraining, copy isolation and comparative lifecycle evidence, following the active charter rather than clearance. This is the third unreconciled record and the next dispatch must explicitly authorize reconciliation if it is to perform it.

## Method

Command: PYTHONPATH=cli:cli/tests pixi run python "$PROJECT/evidence/d6-reopen.py" "$PROJECT", with PROJECT naming ot5-biped in the operator's external cadex-projects directory. Started the real cadex review CLI on loopback and used headless Chromium. Observed probe3's retained historical training model, checkpoint20 and final playback; captured displayed identities/parameters/document links/model statistics, curve counts and downloaded video digests. Started cadexd PID 1689016, restored the saved project through open_project restore=true and shut it down; repeated with PID 1689063. Stopped/restarted the dashboard on the same port, checked the original page's stale/live recovery without navigation, and compared a new page's complete observations against the originals. Recorded all retained run/asset/docs/source/decision hashes before and after. No trainer, render, policy import or authoring operation was invoked.

Initial external harness failures are retained: the video hash lives under videos[0], unmuted autoplay requires a gesture, and engine restore legitimately regenerates cache attempt metadata. Corrected the harness to read the proper schema, mute playback, and compare every manifest field except updated_at, attempt_id and staging; retained data files still require exact byte identity. These were harness corrections, not hidden product fixes. Headless accepted edits are already durable and the protocol has no separate save_project op: this verifies the previously saved acceptance, not a new authoring transaction.

Validation: the real experiment exited 0; pixi run python -m pytest cli/tests/test_review_lifecycle.py -q passed with Chromium/FFmpeg (1 passed, 7.37 seconds). Both repository and external-project git diff --check exited 0. No engine/CLI/shell code or protocol/payload changes, no new dependency, no build; the preceding unit's full engine and CLI gates remain the full-suite baseline. Detailed evidence is retained in external project commit aae6b66, including evidence/d6-reopen.py, d6-reopen-result.json, d6-reopen.log and three failed-assumption logs. Bulk artifacts remain external and project-local.

## Result

Both engine replies report performed=true, matches_accepted=true, digest 14d56ed42ef87185db899cb2485180a81f8eb0959aaf2f8356c7031760a6ebb1. Accepted revision remains a7ee956cafc8de6b1732bc83cb3f59d832a6fe46b5406f3624e88267f479fa2d; all non-cache manifest fields remain equal. All 255 checked retained files are byte-identical. Browser observations before/after match the run list, historical identities, displayed parameters/doc links and loaded model stats, each model exceeding 1000 non-background pixels. Probe3 retains 240 samples in reward/loss/episode-length curves; both checkpoint and final videos advance playback time and download at their recorded SHA-256. The original browser page recovers across server restart and a new page reopens the same saved project.

This advances D6's real completed-artifact evidence, not all of D6: restarting during actual training without stopping/duplicating the trainer remains required in the upcoming design-change retraining. No copy isolation, new design, multi-seed comparison or second-device reachability is claimed. The stale plan and three-record tail require a separately authorized reconcile dispatch; no generated view was edited here. No new dependency or demonstrated product defect.

Dispatch closed: 1 unit — verify real saved biped artifacts across engine and dashboard restart.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: af3a8e84d3077dc5113675f8eff9f4afc49f55b3

## State Impact

- target: clever-field-7845 — Real completed probe3 artifacts survive two engine restores and dashboard restart: accepted identity, 255 retained file hashes, historical models/specs, 240-point curves and matching playable video downloads. Active-training restart remains open.
