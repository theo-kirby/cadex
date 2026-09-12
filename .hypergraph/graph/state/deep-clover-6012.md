---
node_id: 5c38ed96-b7d8-5c80-9395-fb3e153b6597
slug: deep-clover-6012
title: D10. The persistent operator dashboard stays current
created_at: '2026-09-12T21:20:29+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: working

## Current

**Persistent port 8765 has now been observed across a real experiment from start to completion and after a restart; a second-device visit is still absent.** The service serves Reed working copy `ot5-biped-copy29`, switched from the obsolete ot4-carriage project with identity verified over the private address; nine earlier runs stay selectable, historical selection survives polling, and Current run returns to current work [rec: falling-ocean-4411]. It stayed active through the shared-scene renderer update, with final/checkpoint playback, download and polling/history checks passing [rec: royal-arrow-2065].

During the shin55 retraining a fresh visit selected RUN shin55 by default before the first iteration, showed live iterations within 0.26–1.69 s of trainer commit on one navigation, played a checkpoint 20 video published while training continued, and after completion selected shin55-final with playback, download digest match, historical probe3-final and return to current. The persistent-URL check was repeated after `systemctl --user restart cadex-operator-review`, deliberately after rather than during training. The shared-scene render's overhead on GPU training was not measurable (iteration intervals 1.414 s median inside the render window against 1.438 s before and 1.341 s after); the trainer's own checkpoint publication dominates. Published status: `ot5-biped-copy29` / `shin55-final` [rec: fair-crow-5108].

Charter criterion: fresh visits select active training first, otherwise the latest attempt including failed/interrupted work, with truthful identity, available curves/videos and explicit pending/stale/failed states; preserve historical browsing and playback with a route back; keep the stable URL serving between iterations; verify and publish identity at experiment start/completion and every working-project switch. Acceptance requires persistent-URL browser evidence across a real experiment and a working-copy switch plus current-selection and historical-preservation regressions. Declared target `gap-d10-persistent-operator-dashboard-stays` [rec: simple-raven-5405].

Reconcile judgement: flip `open` → `working`. The earlier reason for `open` was the missing experiment-spanning evidence, which fair-crow-5108 supplies together with the copy switch from falling-ocean-4411 and the regressions; all evidence is same-machine Chromium, and the human owns the checkbox [rec: fair-crow-5108].

## Negative knowledge

None yet.

## Provenance

- simple-raven-5405 — operator directive introduces D10 and persistent dashboard obligations
- falling-ocean-4411 — working-copy switch to Reed and current-selection/historical regressions
- royal-arrow-2065 — service stays current through the shared-scene renderer update
- fair-crow-5108 — persistent URL observed at experiment start, during, at completion and after restart; render overhead measured
