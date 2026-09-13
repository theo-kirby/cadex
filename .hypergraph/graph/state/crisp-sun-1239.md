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

**Launch baseline, green** (2026-09-12, at `ed6ce8d8`): engine suite 2102 passed / 54 skipped; CLI suite 301 passed; both harnesses authenticated, preflight ready, the RTX 5090 machine available, Hypergraph 0.0.13 matching the project [rec: hidden-reef-8369].

The eleven done criteria D1–D11 are child state nodes. The operator directive adds shared neural-whoop viewport/video appearance to the persistent-dashboard obligation [rec: simple-raven-5405] [rec: modest-dawn-3706].

**The exhaustion-policy clean-project repeat is under way on a third fresh biped, `ot5-lark`.** Created by the product agent in one `cadex -p` turn (238 mm, 0.596 kg, eight solids, six joints, twenty parameters, one task; accepted revision `753cf0cc4600…`, digest `3b704a3fc1c4…`) naming no earlier project or mechanism; it is now the persistent port 8765 project. The repeat exposed two review defects that Wren's rebuilt fixture had hidden: the reader refused a first accepted attempt staged under the pre-run revision (fixed, ADR-311, regression failed on the old source) and the agent's modelling writes retained no tessellation [rec: honest-rain-3132]; the latter is fixed by injecting the standard tessellation request on every CLI bridge modelling op (ADR-312), with Lark's accepted identity unchanged [rec: soft-forest-5662]. Lark then reached bounded training, checkpoint publication and final review (`lark1`) with the Wren experiment driver generalised to discover outputs by kind [rec: upright-tide-4795].

**Wren's lifecycle is complete through a real encoder failure and recovery.** The product-agent 110→90 mm revision, bounded retraining and seeds 0–4 comparison closed its authorship gap [rec: red-jasper-1884]; its D1–D11 report discloses unequal training budgets [rec: crisp-stream-4743]; `wren71-final` has matched-pose viewport/capture parity against the reference [rec: terse-walrus-5414]; and `wren79` supplied real D4 failure/recovery evidence [rec: sweet-anchor-6246].

Reconcile judgement: keep `open`. D1–D11 have evidence across Reed and Wren and are being repeated on Lark; Lark still lacks its revision/retrain/compare half (D9), copy isolation (D7) and an interrupted attempt (D8). Iterations 80 and 81 committed without records and were backfilled by iterations 81 and 82 [rec: honest-rain-3132] [rec: soft-forest-5662]. No whole-goal declaration or owner checkbox edit.

## Negative knowledge

None yet.

## Provenance

- dusty-peak-9330 — the owner redirected ot5 to live headless project review and lifecycle recording; ADR-284; the fixed choices and what is already there versus to be built
- hidden-reef-8369 — the launch baseline: green engine and CLI suites, harnesses authenticated, GPU box available (declared no state impact; folded here as context only)
- lucky-comet-0031 — the ot5 operator directive: the charter verbatim, the nine criteria declared as gaps
- simple-raven-5405 — adds persistent current-project dashboard criterion D10
- falling-ocean-4411 — current Reed operator dashboard acceptance passes; real experiment-spanning evidence remains open
- modest-dawn-3706 — adds shared neural-whoop visual-reference criterion D11
- kind-oak-1484 — iteration 64 visual comparison backfilled with explicit verification limits
- red-jasper-1884 — iteration 65 work recorded and Wren product-agent revision gap closed by authored, retrained and compared 90 mm design
- crisp-stream-4743 — lifecycle report states unequal budgets and remaining evidence limits
- terse-walrus-5414 — current 90 mm visual comparison resolves the report's historical-only D11 limit
- sweet-anchor-6246 — real Wren79 encoder-failure isolation and recovery during GPU training
- honest-rain-3132 — backfill of iteration 80: Lark created, persistent dashboard moved to it, ADR-311 reader fix, tessellation defect recorded
- soft-forest-5662 — backfill of iteration 81: ADR-312 standard tessellation on every CLI modelling write; Lark identity unchanged
- upright-tide-4795 — Lark's first bounded training, checkpoint publication and final review; tail due a reconcile
