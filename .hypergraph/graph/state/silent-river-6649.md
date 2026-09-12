---
node_id: 492e966d-5ce0-53dd-a235-18510a78f514
slug: silent-river-6649
title: D9. The fresh biped completes the whole recorded lifecycle
created_at: '2026-09-12T14:51:25+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: open

## Current

**The product-agent-authored fresh biped has trained, produced a verified rollout and retained a playable final-policy video; the full design/retraining comparison remains open.** The default product agent created Reed (`ot5-biped`) after quota refusals, with 14 declared parameters and project design/decision notes, importing no old mechanism, checkpoints or history. Probe1's bounded GPU training stored its policy but the walk failed at declaration because the fresh script lacked `policy_on` [rec: lucid-journey-6875]. ADR-289 fixes the running/failed identity defect without rewriting probe1's old record [rec: lively-gate-6535].

After product-agent repair attempts again hit quota, the actor added a playback-only switch via `cadex script --set`. The retained probe1 policy passed the engine witness check against identical model/task bytes; seed 0 fell at 0.66 seconds. Separate `probe1-playback` retains the accepted script/specs, trace, meshes and final-policy video with explicit source-run provenance. Decoding, timing, private-address browser playback across refreshes and matching download bytes passed; failed probe1 remains unchanged. This was an actor recovery, not a successful product-agent repair, completed walk, physical design change or new training [rec: amber-gate-7498].

Keep `open`: no complete lifecycle, review-driven physical design change, retraining comparison or common seed-set displacement/survival/fall measurements are claimed. The local playback switch unblocks this project's playback, but does not establish a general fresh-project prompt/walk repair [rec: amber-gate-7498].

Charter criterion: **D9. The fresh biped completes the whole recorded lifecycle** The product agent creates and documents a new biped, trains and reviews it through this system, uses that review to make a reasoned design change, and retrains; both runs have saved playable videos and measured displacement, survival and falls over the same declared episode/seed set. Evidence: the project history, a lifecycle report linking D1–D8 evidence, and the comparative results; poor gait is a valid measured result, skipped training or missing recording is not. Declared target `gap-d9-fresh-biped-completes-whole` [rec: lucky-comet-0031].

## Negative knowledge

- [scope: product-agent biped creation on this machine's `claude-fable-5` login during ot5 | confidence: high | evidence: zesty-star-7710, kind-fountain-5086, shady-bay-0771, lucid-journey-6875] Three attempts were refused on session quota before any authoring; a quoted reset time did not guarantee the next attempt succeeded, and the attempt that did succeed came after a one-word probe confirmed capacity rather than after the quoted reset.
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
