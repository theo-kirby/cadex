---
node_id: ef491e39-45d7-5b51-9ea7-2698dad20b8c
slug: tidy-banner-0293
title: 'hypergraph 0.0.8: the block that was destroyed here is now preserved'
created_at: '2026-08-09T19:54:10+00:00'
parents:
- twilight-sail-5604
summary: Upgraded to 0.0.8. The AGENTS.md block was reported and left alone rather than overwritten — the defect this repo exposed, verified fixed against the same block. The obsolete warning is retired.
---
## What

Upgraded this project's hypergraph copies to **0.0.8** — five skills, the config stamp,
and a hand-merge of the AGENTS.md block.

The block was **not** overwritten. `upgrade` reported it as `customized`, left it
untouched, and named the shipped template to merge against:

```
  customized     AGENTS.md   (local edits inside the sentinels — pass --agents-block
                              to overwrite)
upgrade: 6 item(s) refreshed to 0.0.8, 1 block(s) left alone
```

Both project-specific paragraphs survived: the clause routing `docs/DECISIONS.md`
alongside the record graph, and the epoch-marker note. I merged 0.0.8's new opening
paragraph in by hand and **deleted the warning this project was carrying**, which said
the block would be overwritten and would retire itself once the CLI here was past
0.0.7. It is, and it did.

## Why

0.0.7 destroyed exactly those two paragraphs when it was run here, and this repo is
where that defect was found. Running the fixed release against the same block is the
verification that closes it.

## Method

`uv tool install hypergraph-protocol --force --refresh` (0.0.7 → 0.0.8; a plain
`uv tool upgrade` reports "Nothing to upgrade" against a stale index cache), then
`hypergraph upgrade --dry-run` and `hypergraph upgrade` in this repo, then the merge by
hand, then `hypergraph sync`.

## Result

- 0.0.8 skills, `hypergraph_version: 0.0.8`, block intact and merged.
- `sync`: **0 violations, 0 warnings.**
- 0.0.8's stricter I1 rule — which now checks prose paragraphs, not only bullets —
  found nothing here. Three claims it flagged before release were colon lead-ins to
  cited lists, and the released rule correctly treats those as structure.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: f227062db564fe9c2cc097dfa725ef6c9e452ab2

## State Impact

- target: early-arbor-7123 — Tooling is on hypergraph 0.0.8 (five skills, config stamp). Supersedes the negative-knowledge entry saying `hypergraph upgrade` overwrites the whole AGENTS.md block: from 0.0.8 it replaces a block only while the block is still verbatim a template the project shipped, and otherwise reports it as `customized`, leaves it untouched and names the shipped template to merge against — verified here against the very block 0.0.7 destroyed, with both project-specific paragraphs surviving. `--agents-block` opts into overwriting. The standing advice is now to merge the new template by hand after an upgrade, not to restore lost paragraphs. Also worth keeping: `uv tool upgrade` alone reports "Nothing to upgrade" against a stale index cache, so a version check needs `--force --refresh` before a publish is judged to have failed.
