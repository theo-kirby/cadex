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

**Lark has a finished, user-facing lifecycle report whose every D1–D11 receipt now comes from Lark or its working copy: `docs/probes/lark-fresh/LIFECYCLE.md` links those receipts, the product-agent revision and common-seed results, and the original-unavailable copy checks, and names no remaining Lark-only acceptance limit [rec: quiet-pebble-5566].** The report is linked from the Lark entry and the operator status. Its smallest open evidence gap — the current visual comparison still belonged to Wren — was closed with a current Lark reference-style comparison on the persistent private dashboard (byte-identical same-pose PNGs, decoded RGB MAE 1.428984/255; D11 holds the detail). The report explicitly preserved three Lark-only limits at publication: D6 restart during training, D4 real encoder-failure isolation and D8 missing/partial-video injection still relied on Wren receipts; original-unavailable copy editing/reopen/review is proved, but retraining happened after the original path was restored with original bytes unchanged. No second-device reachability, causal gait improvement or Lark-only repeat of every check is claimed [rec: windy-walrus-6950]. Two of those limits were then closed on Lark itself in the following units: the D8 missing/partial/failed-video probe on a disposable full copy [rec: light-orchard-1402] and the D6 dashboard restart during a real 100-iteration GPU run (`lark96-restart`) [rec: peaceful-walrus-0642]; each updated the lifecycle report's gap list. The third and last, D4 real encoder-failure isolation, was closed on Lark itself during the real `lark98` GPU run (ADR-320, `RENDER98.md`, receipt `render98-evidence.json`), removing the report's dependency on Wren evidence; the report, the Lark README, the operator README and `RENDER-FAILURE.md` were updated with it [rec: quiet-pebble-5566].

**Lark, the third fresh product-agent biped, completed the recorded lifecycle: creation, training and review (`lark1`), a product-agent design change, retraining (`lark2`) and a declared-seed comparison.** One bounded product-agent turn read `lark1`'s measured results and accepted `torso_h` 70 → 45 mm with `policy_on=0` (revision `62f4e2a0e2df…`, project ADR-004), recording its hypothesis — 0.433 kg of 0.596 kg at z = 203 mm drives the hip toppling moment, and lowering the torso cuts it about 35 percent — as a design-spec bullet. `lark2` retrained it under `lark1`'s bounds (240 × 1024, seed 0) in 718.8 s, exit 0, with checkpoint 20 published during training and a verified final video. All four retained policies were compared on Lark's declared seeds 0–9 at 8 s from their own retained models, tasks and hash-verified policies: both 45 mm policies survive all ten episodes (final mean +34.8 mm torso X, checkpoint +24.4 mm); `lark1-final` falls on every seed after a 181–197 mm lunge and `lark1-checkpoint20` on two. Consistent with the agent's balance hypothesis, but one training seed per design, and 35 mm in eight seconds is a shuffle, not a gait. Evidence: `docs/probes/lark-fresh/REVISION84.md` with test-guarded receipts (ADR-313) [rec: brave-water-4060]. `lark1` itself: 240 × 1024 seed-0 run in 1,052 s, both policies falling within a second on seed 0 [rec: upright-tide-4795].

**Wren's lifecycle report links the real GPU encoder-failure and recovery receipt and identifies `wren79-final` as current.** `docs/probes/wren-fresh/LIFECYCLE.md` traces creation, reopen, training, review, copy, interruption, product-agent revision, retraining, restart and a real render failure, with no new gait claim [rec: sweet-anchor-6246]; it carries its own missing/partial/failed video receipt [rec: fresh-timber-6139] and discloses the unequal training budgets (12 versus 240 updates) that keep the 110 mm retry versus `wren66` from being a controlled geometry comparison [rec: crisp-stream-4743]. The agent accepted `foot_len` 110→90 mm at revision `03077ee9eb82…` (project ADR-002); `wren66` published verified checkpoint and final videos; retained-model evaluations on seeds 0–4 give mean X +40.137/+42.724/+55.147 mm for `wren57-retry`, `wren66-checkpoint20` and `wren66-final`, all surviving 5/5 — standing/shuffling poses [rec: red-jasper-1884]. The earlier 85→105 mm retraining was actor-applied and gets no product-agent credit [rec: frosty-birch-2464]; the quota refusals between authored nothing [rec: smooth-pine-9795] [rec: dawn-bell-5364] [rec: calm-grove-2647].

**Reed completed the recorded lifecycle first, including the product-agent revision, retraining, comparison and test-guarded D1–D8 report** at `docs/probes/reed-lifecycle/` [rec: lucky-bramble-8274]. The agent authored shin_len 80→55 mm (project ADR-007, accepted revision `fe266d48…`); one bounded run on `ot5-biped-copy29` gave, over ten seeds, 4 falls and 6 eight-second survivors at mean forward displacement 79.1 mm — a standing shuffle [rec: fair-crow-5108]. Earlier designs on the same seeds: probe3 checkpoint20 10/10 survival at 39.352 mm while its final fell 10/10 [rec: brave-field-8478]; the actor-applied 90 mm foot edit nine falls [rec: candid-forest-9800]; copy100 fell at 0.62 s and closed D7 [rec: clever-fern-7568]. The fresh biped was created without importing old mechanisms; its first walk failed declaration without `policy_on` [rec: lucid-journey-6875] [rec: amber-gate-7498] [rec: light-brook-2640]. The 90 and 100 mm edits were disclosed actor fallbacks after quota refusals [rec: icy-pond-7346] [rec: young-cedar-2719] [rec: neat-vine-2517] [rec: dusty-oak-7376] [rec: weathered-sage-2750].

Judgement: `working`. Reed, Wren and Lark each have a complete recorded lifecycle with a product-agent revision, retraining, a same-seed comparison and a linking report; Lark's copy isolation and interrupted attempt were proved on its working copy [rec: warm-falcon-0420] [rec: scarlet-ocean-2381], and its report now exists with each of its three published Lark-only limits closed on Lark [rec: windy-walrus-6950] [rec: quiet-pebble-5566]. Gait remains poor everywhere, whole-goal completion is not claimed and checkbox edits remain the owner's.

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
- upright-tide-4795 — Lark's first trained, recorded and reviewed run with seed-0 measurements
- brave-water-4060 — backfill of iteration 84: the product agent's 70→45 mm Lark revision (project ADR-004), lark2 retraining and the four-policy comparison on declared seeds 0–9 (ADR-313)
- warm-falcon-0420 — Lark's D7 proved on its working copy, cited here for the judgement only
- scarlet-ocean-2381 — Lark's D8 proved on its working copy, cited here for the judgement only
- windy-walrus-6950 — the finished Lark lifecycle report (`LIFECYCLE.md`) linking D1–D11 receipts, with a current visual comparison and explicit Lark-only acceptance limits
- light-orchard-1402 — Lark D8 video-fault probe closes one of the report's named Lark-only limits and updates its gap list
- peaceful-walrus-0642 — Lark D6 restart-during-training closes another named limit and updates the report
- quiet-pebble-5566 — Lark D4 encoder-failure isolation closes the report's last named Lark-only limit (ADR-320); every linked receipt is Lark's
