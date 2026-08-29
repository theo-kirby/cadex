---
node_id: a04a861f-6b5f-5313-91b6-18e6695f78fa
slug: sleepy-shade-1485
title: The demo .blend carried the chat transcript — scrubbed, and the gate now opens the file to check
created_at: '2026-08-29T21:28:11+00:00'
parents:
- dawn-oak-0677
summary: ''
---
## What

The shipped demo `.blend` was not sanitized — dawn-oak-6721's claim of
"no transcript, no machine paths" held for the store's text files but not
for the `.blend` itself. Scrubbed it, and pinned the gap shut in the gate.

## Why

The Operator asked whether the biped ships clean of chat logs. It did
not: `history.py` mirrors the chat transcript into a `mesh_chat.json`
text block that saves with the `.blend` (ADR-020 decision 4 — the .blend
is where a conversation lives), and `cadex_hydrate` leaves an absolute
`cadex_sidecar` cache path on every hydrated object. The payload test's
machine-path sweep only read text files in the `.cadex` store, so a
datablock container passed it while carrying the whole conversation.

## Method

Headless scrub through the built bundle: removed the `mesh_chat.json`
transcript block, a stray `model.py` text block (dev leftover), and 12
`cadex_sidecar` properties (stale by design — hydrate compares SHA, never
path, and rewrites them on open); cleared the saved `mesh_chat_input`;
walked objects/scenes/window-managers/collections/meshes plus image and
library filepaths for remaining `/Users/` strings (zero); re-saved
compressed and copied back without a `.blend1`. Verified byte-level on
the zstd-decompressed file: 0 `/Users/`, 0 transcript content (the one
remaining `mesh_chat` string is the empty `WindowManager.mesh_chat_input`
property definition). `test_landing_demo_payload_ships` now also opens
the shipped `.blend` in a fresh headless subprocess (`--python-exit-code`)
and holds it to zero text blocks, zero linked libraries and zero
`/Users/` strings in any saved property. ADR-173's text corrected before
commit; `docs/BLENDER.md` demo row updated.

## Result

Bundle rebuilt; `bl_mesh_agent.py` suite green including the new
DEMO-BLEND-CLEAN check; the open probe against the installed bundle still
restores to the accepted digest with 48 objects hydrated. Nothing is
pushed yet — the demo remains uncommitted in the working tree.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 268cbee80aefa415519365d66c7d23529d1f5a5d

## State Impact

- target: shy-crane-2573 — the shipped biped demo .blend is scrubbed (transcript text block, stray model.py block, 12 absolute cadex_sidecar paths removed) and test_landing_demo_payload_ships now subprocess-opens the shipped .blend to hold it at zero text blocks and zero machine paths
- target: easy-wind-9848 — negative knowledge: a .blend passes any text-file sanitize sweep while carrying the whole chat transcript (history.py saves it as a text block) and per-object absolute cache paths; demo sanitization must open the file, not just walk the store
