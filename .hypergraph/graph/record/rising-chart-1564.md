---
node_id: bdef12da-0a41-55cc-ad74-f08da74db7e8
slug: rising-chart-1564
title: 'Correction: the part domain went 56 -> 57 operations, not 50 -> 51'
created_at: '2026-08-09T16:53:02+00:00'
parents:
- ancient-current-9419
summary: ''
---
## What

A correction to `ancient-current-9419`. Its `## State Impact` says the part
domain went from **50 to 51** operations when `part.import_part` landed. The
real numbers are **56 to 57**.

Everything else in that node stands. This changes one count and nothing about
the design, the evidence or the result.

## Why

The count was about to be folded into `forest-wind-0342` as a state claim, and
a state claim has to be auditable against the record node it cites (SPEC I8). A
future reader comparing "51" in the record to a measured 57 in the tree could
not tell which one had drifted.

Record nodes are immutable, so this is a child node rather than an edit.

## Method

Counted the authoritative source directly — `PartDomainAPI.exported_names`
(`src/Mod/cadex/cadex_part_api.py:2947`), the hand-written ordered tuple that
must mirror `PartWorkbench`'s pack order, and the same tuple
`test_describe_project_api_is_json_safe_and_complete` walks:

```
python3 -c "…parse exported_names…"
part ops: 57 | import_part: True
```

57 with `import_part`, therefore 56 without it.

## Result

**Part domain: 56 -> 57 operations.** `import_part` sits between
`shape_from_mesh` and `repair`, which is where it belongs — it is the lossless
twin of `shape_from_mesh`, and the two read as a pair in the listing the model
sees.

No other number in `ancient-current-9419` was found wrong. The suite counts
(1,723 passed / 22 skipped engine, 80 cli, 14 payload), the shell tool count
(17, checked against `TOOL_DEFS`) and the shell diff (+541/-5 across six files)
all re-measure as stated.

## Negative knowledge

A domain's operation count has three plausible sources in this tree — the API
class, the workbench pack tuple, and the capability listing the model reads —
and quoting one from memory rather than counting it is how a wrong number gets
published. `exported_names` is the one to count.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 5ade410f356d0d5f194ebf00b7f49a69163bdc52

## State Impact

- target: forest-wind-0342 — Corrects the operation count declared by ancient-current-9419: the part domain went 56 -> 57 with part.import_part, measured from PartDomainAPI.exported_names. No other claim in that node changes.
