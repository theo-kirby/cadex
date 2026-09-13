---
node_id: 492e966d-5ce0-53dd-a235-18510a78f514
slug: silent-river-6649
title: D9. The fresh biped completes the whole recorded lifecycle
created_at: '2026-09-12T14:51:25+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: working

## Current

**Lark, the third fresh product-agent biped, has a trained, recorded and reviewed first run (`lark1`); its review-driven design change, retraining and comparison remain open.** One bounded 240×1024 seed-0 GPU run on the accepted design exited 0 in 1,052 s wall clock, with checkpoint 20 published during training and a verified final video. Measured on seed 0 with the 8 s limit, both policies fall within a second: checkpoint 20 at 0.98 s (−110.8 mm torso X), the final at 0.50 s after lunging +194.3 mm forward. Reward rising while the episode estimate falls says the forward term is paid for by falling — a measured poor result, not a gait [rec: upright-tide-4795].

**Wren's lifecycle report now links the real GPU encoder-failure and recovery receipt and identifies `wren79-final` as current.** The report at `docs/probes/wren-fresh/LIFECYCLE.md` traces creation, reopen, training, review, copy, interruption, product-agent revision, retraining, restart and a real render failure; prior lifecycle and gait comparisons remain historical with no new gait claim [rec: sweet-anchor-6246]. Earlier it gained its own missing/partial/failed video receipt, closing the Wren-only D8 evidence gap [rec: fresh-timber-6139], and disclosed the unequal training budgets (12 versus 240 updates) that keep the 110 mm retry versus `wren66` from being a controlled geometry comparison [rec: crisp-stream-4743].

**Wren's product-agent revision step is complete.** The agent accepted `foot_len` 110→90 mm at revision `03077ee9eb82…` with its rationale as project ADR-002; one bounded seed-0 GPU run (`wren66`) published verified checkpoint and final videos. Retained-model evaluations on seeds 0–4 give mean X +40.137/+42.724/+55.147 mm for `wren57-retry`, `wren66-checkpoint20` and `wren66-final`, all surviving 5/5: standing/shuffling poses, one training seed per design [rec: red-jasper-1884]. The earlier 85→105 mm retraining was actor-applied and gets no product-agent credit [rec: frosty-birch-2464]; the quota refusals between authored nothing [rec: smooth-pine-9795] [rec: dawn-bell-5364] [rec: calm-grove-2647].

**Reed completed the recorded lifecycle first, including the product-agent revision, retraining, comparison and test-guarded D1–D8 report** at `docs/probes/reed-lifecycle/` [rec: lucky-bramble-8274]. The agent authored shin_len 80→55 mm (project ADR-007, accepted revision `fe266d48…`); one bounded run on `ot5-biped-copy29` gave, over ten seeds, 4 falls and 6 eight-second survivors at mean forward displacement 79.1 mm — a standing shuffle, not a walking gait [rec: fair-crow-5108]. Earlier designs on the same seeds: probe3 checkpoint20 10/10 survival at 39.352 mm while its final fell 10/10 [rec: brave-field-8478]; the actor-applied 90 mm foot edit nine falls [rec: candid-forest-9800]; copy100 fell at 0.62 s and closed D7 [rec: clever-fern-7568]. The fresh biped was created without importing old mechanisms; its first walk failed declaration without `policy_on` [rec: lucid-journey-6875] [rec: amber-gate-7498] [rec: light-brook-2640]. The 90 and 100 mm edits were disclosed actor fallbacks after quota refusals [rec: icy-pond-7346] [rec: young-cedar-2719] [rec: neat-vine-2517] [rec: dusty-oak-7376] [rec: weathered-sage-2750].

Judgement: `working`. Reed and Wren each have a complete recorded lifecycle with a product-agent revision; Lark has creation, reopen, training and review but not yet the revision/retrain/compare half, nor copy isolation (D7) or an interrupted attempt (D8). Gait remains poor everywhere, whole-goal completion is not claimed and checkbox edits remain the owner's [rec: upright-tide-4795].

Charter criterion: **D9. The fresh biped completes the whole recorded lifecycle** The product agent creates and documents a new biped, trains and reviews it through this system, uses that review to make a reasoned design change, and retrains; both runs have saved playable videos and measured displacement, survival and falls over the same declared episode/seed set. Evidence: the project history, a lifecycle report linking D1–D8 evidence, and the comparative results; poor gait is a valid measured result, skipped training or missing recording is not. Declared target `gap-d9-fresh-biped-completes-whole` [rec: lucky-comet-0031].

## Negative knowledge

- [scope: product-agent authoring on this machine's agent-CLI login during ot5 | confidence: high | evidence: zesty-star-7710, kind-fountain-5086, shady-bay-0771, lucid-journey-6875, fair-crow-5108, calm-grove-2647] Attempts were repeatedly refused on session quota before any authoring; a quoted reset time did not guarantee the next attempt succeeded, and the attempts that did succeed came after a one-word probe confirmed capacity rather than after the quoted reset.
- [scope: a first `cadex walk` on a fresh agent-authored project whose script declares no `policy_on` switch | confidence: high | evidence: lucid-journey-6875] The train leg completes and stores the policy, but the declare leg refuses (exit 3), so the walk cannot finish without a design turn or a prompt/walk change.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d9-fresh-biped-completes-whole`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- zesty-star-7710 — bounded fresh-creation refusal experiment and retained independent project history
- kind-fountain-5086 — one further product-agent retry, again quota-refused before authoring
- shady-bay-0771 — the third refusal (`retry-8`), recorded late with the D6 handoff
- lucid-journey-6875 — fresh biped authored on the default model, first GPU probe, the `policy_on` and identity defects
- lively-gate-6535 — ADR-289 fixed the identity defect in the CLI; `probe1`'s record left as written
- amber-gate-7498 — verified seed-0 rollout and separately retained final-policy playback after quota-refused product-agent repair
- light-brook-2640 — completed baseline, active/final video evidence and honest seed-0 comparison
- brave-field-8478 — ten-seed checkpoint/final baseline establishes common episode comparison with unchanged source artifacts
- candid-forest-9800 — actor-applied foot edit, bounded GPU retraining, verified video and ten-seed comparison
- clever-fern-7568 — D7 real copy lifecycle closes; further actor fallback does not establish product-agent revision authorship
- icy-pond-7346 — comparison-informed product-agent revision refused on quota; video-recovery fallback
- young-cedar-2719 — further quota refusal before authorship; measured polling fallback
- neat-vine-2517 — revision33 quota-refused before authorship; browser-poll fallback
- dusty-oak-7376 — revision34 quota-refused before authorship; shared-verification fallback
- weathered-sage-2750 — revision35 quota-refused before authorship; long-history lifecycle fallback
- fair-crow-5108 — product-agent shin55 revision (project ADR-007), bounded retraining, videos and ten-seed comparison; lifecycle report still open
- lucky-bramble-8274 — completed, test-guarded Reed lifecycle report with evidence index and explicit historical-view limits
- mild-river-8224 — Wren second lifecycle begins; provider limit and in-place restore gap remain
- sage-tower-6445 — first bounded Wren GPU experiment and retained checkpoint/final comparison, with second lifecycle unfinished
- honest-path-3451 — review-driven 105 mm foot revision and declared common-seed comparison; retraining/evaluation pending
- frosty-birch-2464 — Wren revised-foot retraining and common-seed comparison, with authorship and lifecycle limits
- smooth-pine-9795 — both product-agent revision attempts quota-refused; no geometry change or authorship
- dawn-bell-5364 — Wren copy revision retry refused before authorship; Wren-specific gap remains open
- calm-grove-2647 — bounded Wren product-agent revision again refused at the provider session limit; review-defect fallback not counted as progress
- red-jasper-1884 — Wren agent acceptance and rationale, bounded retraining, verified videos and retained-model common-seed comparison close its authorship gap
- crisp-stream-4743 — Wren lifecycle report, preserved historical/current reviews and explicit unequal training-budget limit
- fresh-timber-6139 — Wren report gains its own video-fault receipt and probe, closing the Wren-only D8 evidence gap
- sweet-anchor-6246 — Wren report links the real encoder-failure/recovery receipt and identifies wren79-final; no new gait claim
- upright-tide-4795 — Lark's first trained, recorded and reviewed run with seed-0 measurements; revision/retrain/compare still open
