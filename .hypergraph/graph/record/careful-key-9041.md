---
node_id: 6590d30a-0013-503e-835c-82d07b2476f7
slug: careful-key-9041
title: Opus 5 becomes the default model in both front ends (ADR-154)
created_at: '2026-08-20T11:54:01+00:00'
parents:
- humble-peak-6095
summary: ''
---
## What

ADR-154: the default model is **Opus 5** (`claude-opus-5`), in both front
ends — the shell's `mesh_agent.agent.DEFAULT_MODEL`, `cli`'s own copy of
that constant, the add-on's model picker, the two eval runners and
`docs/CLI.md`. Fable stays in the picker as the "most capable" option.

## Why

Owner direction, stated plainly and with no stated reason, so none is
invented here.

## Method

The shell's `EnumProperty` default now reads `agent_module.DEFAULT_MODEL`
rather than repeating the string, so the picker and the code that runs a
turn cannot disagree — the constant is the single answer to "what does
Cadex run". `cli/` keeps its **own** copy, because it may not import from
`shell/` (the GPL/LGPL boundary, ADR-061); its comment now names whose
default it follows, so the next change moves both.

The picker's Opus row had to be corrected in the same commit: it was
`claude-opus-4-8`, a previous generation, and defaulting to a stale id
would have shipped a picker whose default could not run. The Sonnet row
is a generation behind too (`claude-sonnet-4-6`) and was deliberately
left alone — one logical change, and a stale *option* is not the same
failure as a stale *default*.

## Result

`pixi run python -m pytest cli/tests` — 83 passed. The pure
`bl_mesh_agent.py` suite green. `pixi run gate` — `"ok": true`; the gate
registers the add-on, so the EnumProperty default is exercised by every
run rather than by a test written for it. Nothing pinned the old value:
no test referenced `DEFAULT_MODEL` or the model string.

Commit c855133a.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: c855133a3557f380ad804b19331f3ed1068b5545

## State Impact

- target: shy-crane-2573 — the default model is claude-opus-5 in the shell and in cli/; the add-on picker's default now reads agent_module.DEFAULT_MODEL rather than repeating the string, and cli/ keeps its own copy because it may not import from shell/. The picker's stale claude-opus-4-8 row was corrected in the same change; the equally stale Sonnet row was deliberately not.
