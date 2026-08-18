---
node_id: 02698f77-914d-54bb-8952-77b49373b271
slug: neat-tower-5715
title: The section view's prompt line did not fit, and the cap did not move
created_at: '2026-08-17T16:46:25+00:00'
parents:
- grand-peak-3688
summary: ''
---
## What

A follow-up to [[grand-peak-3688]], and a correction to its `## Repo` line:
the section view landed with **no change to `modes.py`**. The sentence that
told the assistant to cut a model open when it wants to know what is inside
one was written, refused by a test, and taken back out.

## Why

`bl_mesh_agent.py::test_prompt_carries_no_api_names` caps
`modes.CADEX_OVERLAY` at **3500 characters**. The overlay was already at
**3447** — 53 characters of headroom — and the sentence was 359.

The cap could have been raised in one line. It was not, and the reason is the
standard this tree already applies to that text: the collision sentence
sitting beside it earned its place with two shipped bugs found after the fact
(ADR-087, ADR-090). The section view has caused no such bug yet, so spending
the one text every single turn pays for, on a guess, is the wrong trade. The
`section_view` tool description carries the same guidance and the model reads
that too.

## Method

Ran `./package/app/build_app.sh gate tests/python/bl_mesh_agent.py` after the
first version of the change. One failure:

```
1 FAILURE(S):
  - CADEX_OVERLAY stays small (3806 chars)
```

Reverted the `modes.py` hunk; the suite then reported `All tests passed.`

## Result

`modes.py` is unchanged by ADR-148. The overlay's remaining budget is
**53 characters**, which is worth knowing before writing another workflow
sentence into it: the next one is not a sentence, it is a decision about
which existing sentence to remove.

Also worth stating because it nearly slipped past: this suite is a *second*
gate. `pixi run gate` runs `bl_mesh_agent_cadex.py` and was green with the
overlay line in place — the prompt guard lives in `bl_mesh_agent.py`, which
has to be run separately.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: be7ff63d8766f3cede9545152af00a5e01c06fe8

## State Impact

- target: shy-crane-2573 — Correction to grand-peak-3688: ADR-148 changed nothing in modes.py. The Cadex system-prompt overlay is capped at 3500 chars by bl_mesh_agent.py and sits at 3447, so a workflow sentence for section_view did not fit and the cap was not raised -- the collision sentence beside it earned its place with two shipped bugs and this feature has none yet. Negative knowledge: 53 chars of overlay headroom remain, and the prompt guard lives in bl_mesh_agent.py, which pixi run gate does not run.
