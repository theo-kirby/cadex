---
node_id: 807b4084-e5f9-5759-89af-0a8bd81c1958
slug: slender-basin-4979
title: 'Prehistory: the method — agent-aided development and the ADR log'
created_at: '2026-08-09T15:16:12+00:00'
parents:
- odd-banner-6071
summary: 'How this project is worked: almost all code written by agents, with docs/DECISIONS.md as the primary memory at 115 of 248 commits.'
---
## What

How this project is actually worked, which is not derivable from the code.
`docs/DECISIONS.md` is the most-touched file in the repository by a wide margin —
**115 of 248 commits**, against 67 for `ROADMAP.md` and 45 for the busiest source
file — and it carries 136 ADRs written over 16 days.

## Why

Independent workstream branched from the record root: it spans every era rather
than following one.

## Method

Per the author: **almost all of the code has been written by agents.** The ADR
log was decided on early and was less robust at the start than it became; it
grew into the project's primary memory. The change policy in `CLAUDE.md` requires
a `docs/DECISIONS.md` entry for every removal or direction change, verified by
build and tests in the same PR, and treats removals as normal work rather than
as exceptional.

The doc set carries the same discipline: each document has a
`Verified against source:` date, provenance tags (`[FreeCAD-inherited]`,
`[Blender-inherited]`, `[VibeCAD-era]`, `[Cadex-new]`), and keeps *exists today*
separate from *target*. `ROADMAP.md` holds living status; `DECISIONS.md` holds
why; `VISION.md` is authoritative about intent.

## Result

The ADR style is load-bearing rather than decorative, and it is why the docs are
usable as evidence at all: an ADR states what was measured, what the plan got
wrong, and what it cost. Several slices carry explicit "two of this line's own
words were wrong" paragraphs, and the roadmap keeps a *declined* item (ADR-054)
with its number and its measurement attached so it can be revived rather than
re-argued.

Practical cautions for anyone reading it:
- **ADR numbering is not contiguous.** 054 was deliberately never written,
  069–072 and 111 are absent, and 060–067 plus 074 were renumbered when `MJC`
  merged. Cite by number **and** title.
- **Where code and doc disagree, the code wins** — and the doc gets fixed in the
  same PR, with its date bumped.
- `docs/history/` is superseded VibeCAD-era material. Historical context only;
  never cite it as current.

This hypergraph adoption **continues that discipline rather than replacing it**.
The ADR log stays the narrative record of decisions; the record graph is where
units of work land with a declared state impact, and the state graph is the
distilled projection an arriving agent reads first.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: NEW orientation-and-build — `docs/DECISIONS.md` is the project's primary memory, ADR numbering is not contiguous, and the doc set has a defined reading order.
