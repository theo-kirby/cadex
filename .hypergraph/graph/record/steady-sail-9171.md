---
node_id: 57b0f732-ff36-505b-a356-644d79792d50
slug: steady-sail-9171
title: Owner switched ot7 to Opus; resume preserves model history (ADR-384)
created_at: '2026-09-17T16:21:55+00:00'
parents:
- modest-banner-8771
- modest-dune-5265
summary: ''
artifacts:
- docs/probes/ot7/retained/opus-restart-availability.json
---
## What

Switched ot7's actor, critic, reporter and disabled roles to claude-opus-5
at the owner's explicit request after Fable exhausted credits on the refreshed
account. Kept the original restart deadline. Fixed the evidence runner's
resume command to honor an explicit model override (ADR-384).

## Why

The manual account refresh passed its small availability probe, but the next
Fable actor turn failed with out-of-usage-credits. The owner then requested
Opus. Merely changing the loop configuration would leave Robin's next
product turn on Fable: resume ignored --model and reused its attempt receipt.

## Method

Stopped the loop while it was in provider backoff. Both a no-tool call
requesting claude-opus-5 and the runner window probe succeeded; the latter
reported status allowed, room true, five-hour usage 6% and weekly usage 50%.
Changed all configured models and put the new owner directive ahead of the
historical Fable directive. Resume now uses an explicit override, records
model_changes and each turn's requested model, and assigns the previous
receipt model to legacy completed turns before changing the current model.
Omitting --model still preserves the receipt model. No design, parameter,
accepted revision or frozen prompt was edited.

## Result

The configuration and collector can now continue Robin on Opus while retaining
its Fable create turn as historical evidence. The comparison must report the
mixed-model attempt. Three continuation slots remain; Plover follows. The
new regression checks the actual dispatched model sequence, legacy receipt
history, prompt identity, continuation count and persistence of the override.
The focused runner suite passed: 82 tests. This record prepares the restart;
it does not claim a completed Opus design turn.

Full CLI verification passed: `pixi run python -m pytest cli/tests` — 832
passed, 1 skipped in 531.46 seconds. No engine or protocol change was made;
the engine baseline from the preceding launch remains applicable.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: d7ca570a89b6013672fffc6750811c0c68aaa3d8

## State Impact

- target: mild-ledge-7157 — owner supersedes Fable-only directive with Opus for every role and product turn; existing deadline retained, no change to frozen prompts or completed outcomes
- target: narrow-dune-9454 — resume supports the owner-authorized Opus continuation of Robin with its Fable create preserved and no additional slot allowance; three frozen continuations remain
