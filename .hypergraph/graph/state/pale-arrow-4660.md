---
node_id: b7ae8fe8-c13d-5153-a03a-ade36a27039f
slug: pale-arrow-4660
title: G1. The guidance is a base plus styles, and the agent can choose a style
created_at: '2026-10-06T07:42:21+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Charter criterion for run orun4: **G1. The guidance is a base plus styles, and the agent can choose a style.** `src/Mod/cadex/CadexAgentGuidance.md`, `cli/cadex_cli/guidance.py` and `docs/DESIGN-LANGUAGE.md` are restructured into a domain-neutral base and named styles. A project chooses a style through its project config (e.g. `agent.json`); `cadex guidance` and the MCP instructions carry the base plus that style only, or the base alone. Tests pin: the base names no robot type as default; no style text appears when none is chosen; no guidance file names `biped-sts` or any other project. Choosing a style needs no new tool; the tool surface changes only under AGENTS.md's rule. The human owns the checkbox. No work recorded yet; open until a causally parented record shows the criterion met with measured evidence [rec: light-mist-9160].

## Negative knowledge

None yet.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-g1-guidance-base-plus-styles)
