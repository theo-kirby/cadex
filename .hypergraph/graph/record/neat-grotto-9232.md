---
node_id: 61cb8fd2-fcb6-56a2-a41c-9d816e1461f9
slug: neat-grotto-9232
title: The section eye derives its own plane when called by hand
created_at: '2026-09-09T00:30:08+00:00'
parents:
- swift-orchard-8539
summary: ''
---
## What

`cadex section --plane XZ` with no `--offset-mm` now derives its cut plane the
way the walk has since ADR-267. The flag declared `default=0.0`, which made
`write_section`'s derived path (`offset=None`) unreachable from the command
line: a person or agent calling the eye by hand got exactly the constant that
derivation exists to replace. Explicit offsets are unchanged and still report
`offset_source: explicit` — including `--offset-mm 0`, now distinguishable
from not asking. The report note gained the three facts a hand caller could
not previously get without opening `summary.json`: the offset cut, whether it
was asked for or derived, and the objects-cut count over the object total.

Commit `5e32e043`; ADR-275; `docs/CLI.md` command row, flag table and walk
section; ROADMAP checkbox. 113 lines added, 6 removed, in `cli/` and `docs/`
only.

## Why

**Criterion: "The agent can see its work without a screen"** (`damp-moon-9297`),
the headless-review half of this run's frontier. That node names this unit
outright: "`cadex section` defaults `--offset-mm` to 0.0 (`__main__.py:213`),
so **only the walk ever derives an offset** — a person or agent calling the eye
by hand gets the constant, which is the failure ADR-267 set out to end; making
the flag optional and derived-by-default is the obvious next unit."

**The overseer's directive was to build the assembly-inventory CLI call, and
that call has shipped.** `cadex inventory` is ADR-236: wired at
`__main__.py:194`, `cli/cadex_cli/inventory.py`, real-engine tests in
`cli/tests/test_inventory.py`, documented in `docs/CLI.md`, used by the walk's
review step at `__main__.py:1578`, and it has already run against `ot4-swing2`
— `~/cadex-projects/ot4-swing2/docs/inventory.md` carries 10 components, 7
catalogued, `servo/mg90s` ×1, `bolt/m3x18-socket` ×2, `nut/m3-hex` ×2,
`bolt/m3x22-socket` ×1, `nut/m3-nyloc` ×1 and three named uncatalogued
outputs. Building it again is not available as a unit.

The stale premise is traceable: `rising-rain-0117`, the most recent record
node, closes by calling the assembly inventory and the clearance check "the
two review calls still unbuilt". `damp-moon-9297` already refuses to fold that
line, saying ADR-236, ADR-237 and its own live evidence refute it — but the
line is still in the record graph where the overseer read it. Flagged here for
the maintainer; not fixed by me, since a contributor does not write state.

So I followed the directive's intent — close the last real gap in the
headless-review criterion — rather than its stale letter, and picked the unit
that criterion names. It is token-free, `cli/`-only, and needs no provider.

## Method

`--offset-mm` takes `default=None` with help naming the derivation;
`command_section` passes it through and formats the richer note. One other
reader of `args.offset_mm` existed and the test found it: the project
commit-summary formatter raised `TypeError` on `None`, now saying `derived
offset`.

The regression extends the real-engine
`test_real_cavity_pose_offsets_and_local_artifacts`, whose rig stands at
z 5–15 mm so the old constant misses it entirely: the explicit 0.0 cut reports
`empty` at `0/1 objects cut`, and the same call with the flag omitted derives
an offset strictly inside 5–15 mm, reads `ok` at `1/1` and carries
`offset_source: derived`. It fails on the old source.

Then the eye was called by hand on the real project, both ways, through the
built engine.

## Result

**On `ot4-swing2` at accepted revision `93ed1c909276`, by hand:**

- `--plane XZ --offset-mm 0` (the old default): **`unsupported`, 2/10 objects
  cut** — a plane-contact refusal, so not a drawing at all.
- `--plane XZ`, flag omitted: **derived −9.2 mm, `ok`, 6/10 objects cut** — the
  coverage the walk was getting on this rig and a hand caller was not.

Six of ten is the honest ceiling here, not a shortfall of this change:
ADR-273 established that no single XZ plane through this mechanism reaches the
swing arm and its mount cluster together. I corrected one line of ADR-275
after measuring — I had written that the constant "cuts none of the ten
parts"; it cuts two and refuses.

`JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests`: **268 passed, no
skips**, 215.65 s. `cli/tests/test_section.py` alone: 13 passed. No engine
build, payload, protocol or `shell/` change, so no other gate applies. The
repo diff is five files, all under `cli/` and `docs/`; the two by-hand section
runs wrote and committed their artifacts inside `~/cadex-projects/ot4-swing2`
(its own repo, commits `0ea337a` and `375a248`) and nothing generated entered
this tree.

**Still missing before `damp-moon-9297` can be ticked:** nothing in the four
calls themselves — render, section, inventory and clearance all exist, are
wired into the walk's review step and are exercised live on this machine. What
the node keeps un-claimed is scope, not delivery: swept or animated clearance
(these are initial-solved-pose views and tessellation cuts), exact OCCT volume
and section validation beyond AABB consistency, GUI-attached and actual remote
qualification, and a named inventory snapshot inside the saved `review.json`
rather than the counts-and-path block ADR-254 measured. Whether that is
enough to tick is a reconcile judgement, not mine.

The unreconciled tail is 2 nodes with this one; not fat.

Dispatch closed: 1 unit — `cadex section` derives its offset when called by
hand (ADR-275), measured on ot4-swing2 at unsupported 2/10 → ok 6/10; the
overseer's inventory directive was declined as already shipped (ADR-236) with
the stale record line named.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 5e32e0437a82f8b99c7abb24f9056d3a5016a33f

## State Impact

- target: damp-moon-9297 — cadex section --plane XZ now derives its offset when --offset-mm is omitted (ADR-275, commit 5e32e043), closing the gap this node named: the derived path existed only for the walk. Measured by hand on ot4-swing2 at revision 93ed1c909276 — the old constant 0.0 reports unsupported at 2/10 objects cut, the derived -9.2 mm reports ok at 6/10. The note now carries offset, explicit-vs-derived, and objects-cut/total. cli/tests 268 passed, no skips. Also: the assembly inventory call this iteration was directed to build already ships (ADR-236) and has run against ot4-swing2 (10 components, 7 catalogued); rising-rain-0117's closing line calling inventory and clearance 'the two review calls still unbuilt' is wrong and is what the directive was read from.
- target: chilly-union-8972 — cadex section's --offset-mm is now optional (default None); omitting it selects the derived path, explicit values including 0 still report offset_source: explicit. The report note gained offset, offset_source and objects-cut/total. One other reader of args.offset_mm, the project commit-summary formatter, raised TypeError on None and was fixed in the same commit.
