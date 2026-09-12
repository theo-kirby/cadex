---
node_id: 151f7ab8-8a5b-5d38-9de7-3ed71d8ef10e
slug: crisp-sun-1239
title: Live headless project review — the ot5 charter (ADR-284)
created_at: '2026-09-12T14:51:03+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

**Owner-directed work for run `ot5` (ADR-284): make a headless Cadex project observable while work happens and reviewable afterward** [rec: dusty-peak-9330]. The deliverable is a live web dashboard, served from this machine over its private network, showing one selected project's model, design specs, training curves, run history and playable/downloadable policy videos — and a proof of the whole file lifecycle on a **fresh, agent-designed parametric biped**: create, save, reopen, train, record, review, revise, retrain and revisit earlier results [rec: lucky-comet-0031].

The owner's fixed choices, made in conversation and not open to actor interpretation [rec: dusty-peak-9330] [rec: lucky-comet-0031]:

- **Inspection only, one project per server.** The agent keeps authoring and training through the CLI; the script and project records stay authoritative; browser state is not project state. No training controls, chat editor, multi-project catalog, accounts or public hosting. The dashboard observes artifacts and the public protocol and never imports engine internals [rec: dusty-peak-9330] [rec: lucky-comet-0031].
- **Measured gait, not walking success, is the gate.** A poor gait is a valid measured result; skipped training or missing recording is not [rec: dusty-peak-9330] [rec: lucky-comet-0031].
- **mg-legs is retired from the active charter and the acceptance workflow** (its history stays on `late-pond-2851`). The biped is built in a fresh project outside this checkout, without importing the old mechanism, checkpoints or project history. Historical records and the separate cdx-rl tree are not deletion targets [rec: dusty-peak-9330] [rec: lucky-comet-0031].
- **Headless only**, one training run at a time on this machine with an explicit timeout (≤ 2 h, ≤ 20 GB), the existing offboard training environment, and the existing private network — no tunnel, no cloud [rec: lucky-comet-0031].
- **A historical view must not rebuild an old run with today's script and present it as the original**; reading a project cannot re-accept changed geometry [rec: lucky-comet-0031].

**Launch baseline, green** (2026-09-12, at `ed6ce8d8`): engine suite 2102 passed / 54 skipped in 325.28 s; CLI suite 301 passed in 293.03 s; both harnesses authenticated, preflight ready, the RTX 5090 machine available, Hypergraph 0.0.13 matching the project. The preflight's 99 % Codex weekly-usage warning is historical usage, not a fresh measurement; the Claude fallback stays configured [rec: hidden-reef-8369].

The eleven done criteria D1–D11 are child state nodes. The latest operator directive adds shared neural-whoop viewport/video appearance to the persistent-dashboard obligation; keep the current dashboard serving first, then implement and visually compare that environment. Reconcile judgement: group the new gaps here with the existing criteria; the directive expands the frontier without reopening previously evidenced D1–D8 [rec: simple-raven-5405] [rec: modest-dawn-3706].

**D10 immediate acceptance passes:** persistent port 8765 serves Reed copy29/copy100 with current-attempt defaults, historical/playback preservation and private-address browser evidence. The server stayed active after tests. Real experiment-spanning persistent-URL evidence remains open; D11 visual comparison is newly required and unproven [rec: falling-ocean-4411] [rec: modest-dawn-3706].

## Negative knowledge

None yet.

## Provenance

- dusty-peak-9330 — the owner redirected ot5 to live headless project review and lifecycle recording; ADR-284; the fixed choices and what is already there versus to be built
- hidden-reef-8369 — the launch baseline: green engine and CLI suites, harnesses authenticated, GPU box available (declared no state impact; folded here as context only)
- lucky-comet-0031 — the ot5 operator directive: the charter verbatim, the nine criteria declared as gaps
- simple-raven-5405 — adds persistent current-project dashboard criterion D10
- falling-ocean-4411 — current Reed operator dashboard acceptance passes; real experiment-spanning evidence remains open
- modest-dawn-3706 — adds shared neural-whoop visual-reference criterion D11
