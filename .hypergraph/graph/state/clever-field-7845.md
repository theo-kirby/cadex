---
node_id: c7376b1b-a383-509c-a933-2a8e3b25dcea
slug: clever-field-7845
title: D6. Save, reopen and restart preserve the project
created_at: '2026-09-12T14:51:25+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: open

## Current

**The automated fixture half of D6 exists; the real-artifact pass on the fresh biped does not.** `cli/tests/test_review_lifecycle.py` (commit `38c35f6a`) runs the real `cadex review` command against a fixture project in headless Chromium, selects a run whose telemetry an independent producer process commits every 0.3 s, stops the server with SIGINT, checks the open page reads stale with its identities and video element intact, restarts on the same port and checks the page returns to live without reloading with the same run, revision, advancing curves and a decodable, byte-identical video. A fresh page against the restarted server reads the same accepted revision, run list, historical label, parameters, telemetry and downloadable video. The producer keeps its PID, never resets its iteration sequence and is the only process carrying its marker; every project file other than its own snapshot has the same digest afterwards. No product code or dependency changed; CLI suite 353 passed, 1 skipped [rec: shady-bay-0771].

Still open, per the same record: no engine runs anywhere in the test, so "restarting the engine" is argued rather than exercised; save/reopen of a project a real walk wrote is unverified; the stale-then-live recovery time is measured only at the fixture's 0.3 s producer cadence, not a real trainer's; and the required recorded pass on the fresh biped with real training artifacts has not been run [rec: shady-bay-0771]. The biped now has an accepted revision and one stored policy (see D9, `silent-river-6649`), so that pass is no longer blocked on creation.

Charter criterion: **D6. Save, reopen and restart preserve the project** Save/reopen and restarting the dashboard and engine preserve accepted identity, specs, run history, curves and video access; restarting the dashboard during training neither stops nor duplicates that training. Evidence: an automated lifecycle test and a recorded pass on the fresh biped with real artifacts. Declared target `gap-d6-save-reopen-restart-preserve` [rec: lucky-comet-0031], introduced with no implementation claimed [rec: dusty-peak-9330]. Retain `open`: the fixture half is real, the real-artifact half is absent.

## Negative knowledge

None yet.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d6-save-reopen-restart-preserve`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- shady-bay-0771 — handoff record for the D6 restart test (commit 38c35f6a): dashboard restart under independent telemetry, and its stated limits
