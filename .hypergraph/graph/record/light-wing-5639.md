---
node_id: 019c603d-589c-5c17-8875-d5380ec87b1c
slug: light-wing-5639
title: 'Visual pass: floor, materials, wireframe, home page, Status (ADR-600..607)'
created_at: '2026-10-08T15:19:53+00:00'
parents:
- loyal-mesa-6439
summary: ''
---
## What
An owner-directed visual and dashboard pass, done in session (no Ouroboros run), ADR-600..607: the viewport never draws world floor geometry and lays the mat at its top, with a fixed 1 m grid and near/far planes that follow the camera (600); physical materials, crease-angle normals and a procedural studio reflection in the shaded viewport (601); hairline renamed wireframe, with optional faint mesh lines (602); catalog-family finish classes shared by engine renders and the browser — black-oxide/steel/brass hardware, PCB boards with chip and pads (603); the engine floor a fixed metre in every image and video (604); a home page with spotlight and project cards (605); a Status editor with four axed charts, the latest evaluation and a runs table (606); an agent-authorable status.html shown in a sandboxed iframe fed by postMessage (607).

## Why
Owner feedback after the strandbeest project: the floor z-fought and its grid layered by zoom; screws, boards and printed parts all looked the same flat plastic; the home page read as a directory; Status's tiny sparklines had no axes.

## Method
Three parallel worktree agents (viewport; engine/server materials and floor; home and Status), merged into main (merges 266d2d66, ff491cd8, d4ada595) with DASHBOARD.md and test_scene_palette.py conflicts resolved, then follow-ups in 0ba88166 (rolling-mean chart lines, axis to the reached iteration for ended runs, mesh-line default 0.12, a race-tolerant read-only browser test). Screenshots of strandbeest, biped-sts, ball-plate and excavator-mini through the live /cadex proxy and the engine's before/after heroes were inspected.

## Result
Engine suite 2696 passed / 61 skipped; CLI suite 1248 passed / 1 skipped after the follow-up (one browser test raced manifest vs mesh install under load; it now waits for the drawn width). Not done: footprints or a trail on the wireframe floor; small black-oxide bolts still read as dark dots at hero size.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 0ba8816617b052f5643f0bafd43acc1473e4f7bf

## State Impact

- target: salty-isle-4063 — engine renders use catalog finish classes and a fixed 1 m floor in every image and video (ADR-603, ADR-604)
