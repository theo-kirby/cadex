---
node_id: 1813c349-baa0-5e8a-8197-228790335f69
slug: restless-gate-7062
title: Restore actor fallback and add manual account refresh (ADR-361)
created_at: '2026-09-16T13:50:32+00:00'
parents:
- forest-bell-5161
summary: ''
---
## What

The owner restored the actor fallback to Codex and requested a manual account
refresh after login changes. ADR-361 restores Claude Fable 5.1 → Codex
gpt-6-astra. The product-agent Claude window gate and void-call rules remain.

## Why

The live loop was sleeping on a stale account limit after the owner reset
usage. The prior fallback removal was no longer the owner's preferred policy.

## Method

Added refresh and --refresh commands in the separate Ouroboros checkout,
preserving pre-existing automatic-refresh changes. A file request is consumed
at iteration boundaries or during one-second backoff polling; fresh no-tool
probes run in temporary directories. No active turn is interrupted.
Stopped ot7 during backoff to load the implementation and configuration.
Preserved its existing 48-hour deadline as September 17 at 00:25:13 Eastern.

## Result

Ouroboros full suite: 310 passed, including aliases, unsupported old runners,
fresh meters and wake during backoff. Installed executable is editable and
loads the updated source. Cadex operator instructions and ADR-361 document
the restored fallback and refresh command. The same run and branch continue;
this changes no design, frozen prompt, attempt accounting or charter.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 70a7ffa213ab7674c0f444cf503f03681ddda230

## State Impact

- target: mild-ledge-7157 — Owner restores Claude-to-Codex actor fallback; manual ouroboros refresh rechecks current logins and wakes cooldowns. Product-agent window and void-call rules remain; existing run deadline preserved.
