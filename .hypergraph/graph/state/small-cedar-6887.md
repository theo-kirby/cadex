---
node_id: 6b5c4bb4-cfff-5eaa-8787-a8fc467f9861
slug: small-cedar-6887
title: F1. Evaluation applies the command filter the policy was trained with
created_at: '2026-10-06T07:42:21+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Charter criterion for run orun4: **F1. Evaluation applies the command filter the policy was trained with.** The trainer writes `action_filter_alpha` into the `.cxpolicy`; the engine's rollout and evaluation read it from the policy and filter commands as the trainer does (`training/cadex_train.py`, about line 1597). The test: a policy trained with a filter is evaluated and replayed, both applying the same filter; a policy with no filter recorded behaves as today (alpha 1.0); old `.cxpolicy` files still load. Checkpoint rollouts (ADR-544) and the evaluation film use the same path. The packaged lifecycle gate passes if the change reaches the payload. The human owns the checkbox. No work recorded yet; open until a causally parented record shows the criterion met with measured evidence [rec: light-mist-9160].

## Negative knowledge

None yet.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-f1-evaluation-applies-command-filter)
