---
node_id: d99ca1d9-fea9-5e8e-8c2d-ff49de2f7986
slug: grand-ember-9404
title: Launch three fresh Codex Astra creature designs for comparison
created_at: '2026-10-09T16:56:39+00:00'
parents:
- golden-flame-1650
summary: ''
---
## What

At the owner’s request, closed all six cfix Claude Code / Opus design sessions and launched three fresh Codex CLI / GPT-6-Astra projects: castra-deinonychus, castra-heron and castra-leopard, one of each animal.

## Why

The owner wants to compare how Codex and Astra handle the same creature-design task after the creature fixes, instead of Claude Code and Opus.

## Method

Copied each cfix animal’s design-only kickoff brief verbatim into a fresh project. Codex CLI v0.162.0 launches in separate cadex tmux windows with model gpt-6-astra, medium reasoning, approval never, danger-full-access, and a project-specific Cadex MCP stdio server. Launch metadata and exact prompts live in each project. Local AGENTS.md prohibits reading other projects, previous transcripts, baselines, ratings or repository probes, and editing the product repository. These are instruction-level boundaries: a bubblewrap isolation probe failed with uid-map Permission denied, so there is no enforced read isolation. Fresh folder trust was accepted for the files created for this authorized launch. No design hints or previous designs were provided. All three read cadex guidance --project . successfully.

## Result

All three tmux sessions display GPT-6-Astra medium and are actively working. Design quality and completion remain unmeasured; the intended follow-up is to inspect and compare their final designs. The previous cfix projects and artifacts remain intact. Their sessions had paused at Claude’s usage limit with unfinished designs; closing them cancelled their scheduled continuation. This is an experimental harness change rather than a product behavior change.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: c27f3e609ab2b4d2f1aaaea4b366d40833bfe57b

## State Impact

- target: NEW codex-astra-creature-comparison — open: three fresh design-only runs launched with the same briefs as cfix; outcomes await inspection and comparison
