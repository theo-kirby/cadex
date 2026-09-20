---
node_id: 932771fc-5438-5380-be94-271e800b85fb
slug: wandering-ocean-3301
title: Switch Ouroboros Claude roles to Opus 5 (ADR-363)
created_at: '2026-09-16T14:28:29+00:00'
parents:
- restless-gate-7062
summary: ''
---
## What

Switch all Ouroboros Claude role entries from Fable 5.1 to Opus 5 at the
owner's request after a fresh Claude login.

## Why

The owner has Opus usage available and explicitly requested this model and
an account refresh.

## Method

Stopped the loop while in backoff. Probed claude-opus-5 with one no-tool
turn in a scratch directory: exit 0, result OK, modelUsage includes
claude-opus-5. Updated the four Claude role entries. Preserved Codex roles,
the original stop deadline, and product-agent experiment settings.

## Result

Opus 5 is available on the current login. ADR-363 records the change.
The existing ot7 branch continues with updated orchestration configuration
and a queued manual account refresh.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 40ea74ea08b2ece0c061c1139660d58bd81a3001

## State Impact

- target: mild-ledge-7157 — Owner selects claude-opus-5 for Ouroboros Claude roles; no-tool live probe succeeds. Codex fallback and original deadline remain; product-agent experiment settings unchanged.
