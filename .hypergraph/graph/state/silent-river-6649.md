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

**Reed has completed the recorded lifecycle, including the product-agent revision, retraining, comparison and test-guarded D1–D8 report.** [rec: lucky-bramble-8274] After a one-word capacity probe, the project's stored model (`claude-sonnet-5`) authored shin_len 80→55 mm with the 100 mm feet kept, task semantics unchanged and `policy_on` off first, recording its reasoning as project ADR-007 and a design-specs entry (accepted revision `fe266d48…`; only shin_len and policy_on changed). One bounded 240×1024 GPU run on `ot5-biped-copy29` (seed 0, no warm start) exited 0 in 850 s at reward/step 0.508, with a checkpoint 20 video published during training and a retained final policy and video; all nine prior run records stayed byte-unchanged. Ten seeds in an independent copy: 4 falls at 0.44–0.90 s, 6 eight-second survivors at 44.7–49.5 mm forward, mean duration 5.034 s and mean forward displacement 79.1 mm. Survival improved over probe3 (10 falls) and foot90 (9 falls) on the same seeds, but this is a standing shuffle, not a walking gait [rec: fair-crow-5108].

Earlier designs on the same seeds: probe3 checkpoint20 survived 10/10 at 39.352 mm mean forward displacement while its final policy fell 10/10 at ~0.50 s [rec: brave-field-8478]; the actor-applied 70→90 mm foot edit gave nine falls and one survivor, mean 1.338 s and 160.842 mm [rec: candid-forest-9800]; copy100 (90→100 mm feet) fell at 0.62 s on seed 0 and closed D7 [rec: clever-fern-7568]. The fresh biped was created by the product agent without importing old mechanisms, checkpoints or history; its first walk failed declaration without `policy_on` [rec: lucid-journey-6875] [rec: amber-gate-7498] [rec: light-brook-2640]. The 90 and 100 mm edits were disclosed actor fallbacks after quota refusals; requests revision33–35 were also refused before authorship, and the fallback work of that period (retained-video recovery, polling coordination, beyond-cache history verification) established no design revision [rec: icy-pond-7346] [rec: young-cedar-2719] [rec: neat-vine-2517] [rec: dusty-oak-7376] [rec: weathered-sage-2750].

The report at `docs/probes/reed-lifecycle/` indexes D1–D8 evidence, twelve retained run identities and served mesh counts, the four-design common-seed comparison and persistent-URL revisit. It distinguishes complete rollout views from incomplete training snapshots: probe3 4/8 meshes, shin55 5/8, probe2 unposed and probe1 absent. Reconcile judgement: `working` for Reed's demonstrated D9 lifecycle; gait remains poor, whole-goal completion is not claimed and checkbox edits remain the owner's [rec: lucky-bramble-8274].

**Wren's product-agent revision step is complete.** The agent accepted `foot_len` 110→90 mm with `policy_on=0` at revision `03077ee9eb82…`; a follow-up inspection turn supplied its rationale as project ADR-002 and design specs without changing the accepted design. That turn's exit 3 means no new acceptance, not refusal. One bounded 240×1024 seed-0 GPU run (`wren66`) exited 0 in 700.402 s, publishing a verified checkpoint video during training and a verified final video. Retained-model evaluations on seeds 0–4, eight seconds at 50 Hz, give mean X +40.137/+42.724/+55.147 mm and reward 214.882/213.622/144.877 for `wren57-retry`, `wren66-checkpoint20`, and `wren66-final`; all survive 5/5. This closes Wren's authorship gap, not a walking-gait or causal geometry claim: one training seed per design and standing/shuffling poses remain the limits [rec: red-jasper-1884].

Earlier Wren 85→105 mm retraining was actor-applied and receives no retrospective product-agent credit [rec: frosty-birch-2464]. Subsequent quota refusals authored nothing and their review fixes were not lifecycle progress [rec: smooth-pine-9795] [rec: dawn-bell-5364] [rec: calm-grove-2647]. Reconcile judgement: retain `working` for Reed's demonstrated lifecycle and Wren's now-completed product-agent revision; do not infer whole-goal completion [rec: red-jasper-1884].

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
