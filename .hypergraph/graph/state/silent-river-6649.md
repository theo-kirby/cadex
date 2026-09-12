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

**The fresh biped exists and has trained once; no rollout, review, video or design change yet.** After three session-quota refusals (`create`, `retry-7`, `retry-8`), a one-word probe showed all three models answering at 12:54 local, so the smallest supported correction was no correction: the product agent authored `ot5-biped` (Reed) on the CLI's default `claude-fable-5` with no `--model` override. Accepted revision `23c6fe93f47a…`, digest `850acf23a05a…`, a 164-line script with 42 `assembly.` calls, 14 declared parameters, one task `reed_walk`, ADR-002/003 and design-specs notes in the project; the agent reported zero pose residual and feet on the ground at the keyframe. Nothing was imported from the old mechanism, its checkpoints or its history. A bounded 40 × 1024 PPO walk (`runs/probe1`) trained on the local GPU in 90 s (train leg 182 s wall, peak RSS 5.7 GB, GPU 16.7 GB), reward/step 1.211, stored `probe1.cxpolicy` (sha256 `01865c8e…`), then failed at the declare leg with exit 3 because the fresh script declares no `policy_on` switch, which the system prompt only asks for once a policy exists. Evidence: the project's own history (`~/cadex-projects/ot5-biped`, commits `04d355a`, `100dfae`, `4e68224`) and `docs/HEADLESS-BIPED-REVIEW.md` [rec: lucid-journey-6875].

Open product defect blocking the next walk: a first walk on an agent-authored project cannot finish, because the declare leg refuses without the `policy_on` switch the fresh script never declared. Fix candidates recorded: one design turn adding the switch and a placeholder policy, or making the prompt and walk agree so a fresh project needs no such turn [rec: lucid-journey-6875]. The second defect that walk exposed (a running or failed run carrying no model identity) is fixed in the CLI by ADR-289, but `probe1`'s pre-fix record is deliberately left as written [rec: lively-gate-6535]. Also noted, not investigated: the trainer's `episode_steps` telemetry reached 890, 1861 and 10240 on a 400-step task during early iterations [rec: lucid-journey-6875].

Charter criterion: **D9. The fresh biped completes the whole recorded lifecycle** The product agent creates and documents a new biped, trains and reviews it through this system, uses that review to make a reasoned design change, and retrains; both runs have saved playable videos and measured displacement, survival and falls over the same declared episode/seed set. Evidence: the project history, a lifecycle report linking D1–D8 evidence, and the comparative results; poor gait is a valid measured result, skipped training or missing recording is not. Declared target `gap-d9-fresh-biped-completes-whole` [rec: lucky-comet-0031]. Retain `open`: creation and one training probe are done; the `policy_on` fix, a completed walk, review, video, design change, retraining and the comparison remain.

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
