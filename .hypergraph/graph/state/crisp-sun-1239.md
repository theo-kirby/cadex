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

**The exhaustion-policy clean-project repeat on the third fresh biped, `ot5-lark`, is complete: Lark has D1–D11 evidence of its own.** Created by the product agent in one `cadex -p` turn (238 mm, 0.596 kg, eight solids, six joints, twenty parameters, one task) naming no earlier project or mechanism; the repeat exposed and fixed two review defects (ADR-311 reader, ADR-312 tessellation on every CLI modelling write) [rec: honest-rain-3132] [rec: soft-forest-5662]. `lark1` reached bounded training, checkpoint publication and final review [rec: upright-tide-4795]. The product agent then made the review-driven change (torso 70→45 mm, project ADR-004), `lark2` retrained it and all four policies were compared on declared seeds 0–9 — both 45 mm policies survive all ten, one seed per design, no gait (ADR-313) [rec: brave-water-4060]. D7 was proved on the whole-project copy `ot5-lark-copy85`, edited and restored with the original unavailable and reviewed identically on two servers, the original's 1,852 files byte-identical (ADR-314) [rec: warm-falcon-0420]; that copy is now the working project on port 8765. D8 was completed there: a real attempt SIGINT-interrupted at iteration 5 and shown failed with guidance, a successful 40-update retry, its verified playable video, and the original byte-identical after the copy's retraining (ADR-315) [rec: scarlet-ocean-2381]. The Lark probe drivers are now project-agnostic and their receipts test-guarded in `cli/tests`.

**Lark's lifecycle report now rests on Lark receipts alone, and the exhaustion policy's bounded-operation rung has begun.** The last Lark-only limit the report named — D4 real encoder-failure isolation — was closed during the real `lark98` GPU run on the persistent dashboard (ADR-320) [rec: quiet-pebble-5566]. With D1–D11 carrying evidence, the critic directed work to the long-term rung "bounded telemetry, disk use and visible missing artifacts": ADR-321 bounded the dashboard's run-list poll (summary telemetry per run, histories and verified checkpoints per selected run, keyed DOM rebuilds, a 63-run browser regression) [rec: dusty-fjord-4501], and ADR-322 added per-run retained-artifact disk use to the run detail and Artifacts panel with missing and refused artifacts named and shared references counted once [rec: civic-nest-8285]. Each was deployed to the persistent Lark dashboard by restart with no trainer active and re-verified over the private address; no training was launched for either. The remaining rungs of that kind, as the records name them: keying the artifacts table, a served project-wide `runs/` total (not served because it would put a walk of every run into the two-second poll), and compact or paged run lists if a project nears a hundred runs [rec: civic-nest-8285] [rec: dusty-fjord-4501].

**Wren's lifecycle is complete through a real encoder failure and recovery.** The product-agent 110→90 mm revision, bounded retraining and seeds 0–4 comparison closed its authorship gap [rec: red-jasper-1884]; its D1–D11 report discloses unequal training budgets [rec: crisp-stream-4743]; `wren71-final` has matched-pose viewport/capture parity against the reference [rec: terse-walrus-5414]; and `wren79` supplied real D4 failure/recovery evidence [rec: sweet-anchor-6246].

**Gates.** On commit `ca78d935`: CLI 437 passed / 1 skipped, engine 2110 passed / 53 skipped [rec: warm-falcon-0420]. On commit `2fbe6940`: CLI 438 passed / 1 skipped; engine unchanged from the pre-launch run with no engine change [rec: scarlet-ocean-2381]. Iteration 84's own suite runs were cut off before a summary; its 16 evidence-guard tests pass on its tree [rec: brave-water-4060]. After `lark98`, sequentially: CLI 448 passed / 1 skipped, engine 2110 passed / 53 skipped [rec: quiet-pebble-5566]; then CLI 451 passed / 1 skipped with no engine change (ADR-321) [rec: dusty-fjord-4501] and 458 passed / 1 skipped (ADR-322) [rec: civic-nest-8285].

Reconcile judgement: keep `open`. D1–D11 now have evidence across Reed, Wren and Lark, each with a product-agent revision; gait remains poor everywhere and no whole-goal declaration or owner checkbox edit has been made. Iterations 80, 81 and 84 committed without records and were backfilled by the following iteration [rec: honest-rain-3132] [rec: soft-forest-5662] [rec: brave-water-4060]. Remaining limits repeated on every record: same-machine private-address browser checks, not a second device; one training seed per design; no new D11 similarity claim on Lark. The three work records after the D6 restart (`quiet-pebble-5566`, `dusty-fjord-4501`, `civic-nest-8285`) were folded by this pass, which the last of them named as the next scheduled iteration [rec: civic-nest-8285].

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
- upright-tide-4795 — Lark's first bounded training, checkpoint publication and final review
- brave-water-4060 — backfill of iteration 84: Lark's product-agent revision, lark2 retraining and declared-seed comparison (ADR-313); its own suite runs cut off
- warm-falcon-0420 — D7 proved on Lark's working copy, now the served project; gates green on ca78d935 (ADR-314)
- scarlet-ocean-2381 — D8 completed on Lark's working copy with a verified retry video; Lark has D1–D11 evidence (ADR-315)
- quiet-pebble-5566 — ADR-320: Lark's last Lark-only lifecycle limit (D4 encoder-failure isolation) closed on the persistent dashboard; suites green
- dusty-fjord-4501 — ADR-321: bounded-operation rung begun with the run-list poll bound, deployed to the persistent dashboard
- civic-nest-8285 — ADR-322: per-run disk use with missing/refused artifacts named, deployed; names the reconcile pass as next
