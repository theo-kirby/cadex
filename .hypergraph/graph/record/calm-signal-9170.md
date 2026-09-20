---
node_id: e89f224d-4f74-5ec3-b012-d7669cab46e1
slug: calm-signal-9170
title: Restarted ot7 notifier after stale stopped status made it exit
created_at: '2026-09-17T15:57:04+00:00'
parents:
- modest-banner-8771
summary: ''
---
## What

Restarted ot7's exited Pushover watcher during the owner's progress check.

## Why

The owner asked whether the notifier was running after the Fable restart.
The loop was alive in provider backoff, but the watcher had exited immediately
at launch after reading the previous stopped status and terminal_sent cursor.

## Method

Read ouroboros status, the loop log, reporter cursor, watcher pid and tmux
pane. The old pane said the run was over and reported; watch.pid was absent.
Ran `ouroboros watch` against the now-live run without changing its charter,
configuration, experiments or model selection. Checked the new process and
its pane after startup.

## Result

The watcher stayed alive and logged successful Pushover sends for the Claude
limit, all harnesses limited, and the interval report. This establishes
service-reported sending, not that the owner's phone displayed them. The
model-written digest hit the same Claude limit; fixed alerts still sent.
Robin's create result is recorded separately in modest-dune-5265; this
operational repair does not advance a design criterion.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: e269c462333b03ba36ff877d386cbe7a1ab5b9d5

## State Impact

none: Operational watcher restored; no product or design criterion changed.
