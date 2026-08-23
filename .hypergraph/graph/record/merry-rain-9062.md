---
node_id: 26f9828c-dd6e-531b-a028-f8345384a2cd
slug: merry-rain-9062
title: The two cdx-rl trainer PRs land on main, with three defects fixed (ADR-159)
created_at: '2026-08-23T10:31:16+00:00'
parents:
- gilded-wind-5121
summary: ''
---
## What

The two open cdx-rl pull requests are merged into `main`, and the three
things that were wrong on arrival are fixed. ADR-159.

- **PR #7 — `--init-from-task-change REASON`.** `check_policy_fits` compares
  the task bundle's whole-file digest, which made a **curriculum**
  impossible: a walker could reach a harder shove band only from a fresh
  network. The flag skips the whole-file task digest and nothing else, and
  the differing top-level keys must be a subset of `CURRICULUM_TASK_KEYS`,
  which answers one question — does the change alter what the network reads
  or what it emits? `--init-from-parent-task` is required beside it, because
  a `.cxpolicy` header carries its task's digest rather than its content.
- **PR #8 — `--command-slew-deg`.** A cap on the per-step change of the
  **issued** command, after the action filter and before the `ctrl` write,
  reset with the episode. A different operator from the EMA, which bounds
  smoothness and does not bound rate at all. Default 0.0 is **no limit** —
  the opposite convention from the filter's alpha, where 0 freezes the
  command and is refused — and at 0.0 the emitted graph is unchanged.

## Why

The owner asked for everything open to land on `main`. Both PRs are cdx-rl's
work on the offboard trainer; neither carried a `docs/DECISIONS.md` entry or
a record node, so without this pass the state graph would have gained two
trainer features it could not see, and the ADR log would have a hole where
two decisions should be.

## Method

`gh pr merge 7 --merge` then `gh pr merge 8 --merge` (the two are stacked —
#8's branch contains #7's commit), after checking each PR's CI. Then, on
`main`, the defects:

1. **#8's failing test was real.**
   `test_zero_is_no_limit_and_not_a_frozen_command` asserted the literal
   string `command_slew_deg = 0.0` appears in `training/cadex_train.py`. It
   does not: the resolution moved into a module-level
   `resolved_command_slew_deg(options)` — deliberately, because
   `policy_header` needs the same number as `train` and the first draft read
   it as a local — and the assertion stayed pinned to the draft. It now
   reads the resolver's own body (`getattr(options, "command_slew_deg",
   0.0)` and `return value if value > 0.0 else 0.0`), which is where the
   rule lives, and keeps `slewing = command_slew_deg > 0.0` pinned as text
   because that branch is what makes 0.0 a true no-op.
2. **`resolved_command_slew_deg` was defined twice** — two identical copies
   differing only in an em-dash versus `--`, the signature of one hunk
   applied twice across a stacked rebase. The second silently won; the first
   was dead. Deleted.
3. **An unrelated engine bug the same suite run surfaced.**
   `shared_worker_bundle` treated *the existence of the content-addressed
   bundle directory* as proof it was populated
   (`if bundle.is_dir(): return bundle, entry_module`). macOS purges
   `/var/folders` by **age of file**: the staged modules go, the directory
   stays, and a `__pycache__` written later keeps the directory's own mtime
   fresh. Reproduced on this machine — three `test_tessellation.py` failures
   against three bundle directories holding nothing but `__pycache__`.

   Fixed: the reuse check now requires every member file. Because
   `os.replace` refuses a non-empty target directory, a gutted bundle is
   moved aside under a `.dead-<uuid>` name and removed before the freshly
   staged one is published — so a worker holding the old path always holds a
   valid directory, and nothing is half-replaced in place.

One thing deliberately **not** done: both PRs cite "ADR-152" and "ADR-153"
in titles, docstrings and test prose, and those are cdx-rl's numbers. In
`docs/DECISIONS.md` ADR-152 and ADR-153 are the blueprint-sheet decisions.
Rewriting the citations across two files is a bigger edit than the confusion
warrants, so ADR-159 records the collision instead.

## Result

**Merged and green.** `pixi run python -m pytest src/Mod/cadex/cadex_tests`:
**1909 passed, 45 skipped** — the 12 MJX-gated slew tests skip in the pixi
environment by design (ADR-084), as do the trainer's own.
`pixi run python -m pytest training/test_curriculum_warm_start.py`: **16
passed**. `pixi run python -m pytest cli/tests`: **83 passed**. No open pull
requests remain.

Before the bundle fix the same suite failed three tessellation tests on this
machine; `test_a_bundle_gutted_by_a_temp_sweep_is_rebuilt_rather_than_used`
now guts a real bundle, leaves behind the husk a sweep would leave
(directory plus `__pycache__`), and asserts the rebuild.

**Negative knowledge, and it is the useful part of this node.**

- A **content-addressed cache in the system temp directory cannot treat
  directory existence as proof of contents.** macOS deletes files under
  `/var/folders` by age and leaves the directory tree; anything written into
  that directory later (here, `__pycache__`) keeps it looking current. The
  failure surfaces days after the sweep, in a sandboxed worker, as an import
  error with no thread back to its cause. A machine that sat idle over a
  weekend is the whole reproduction.
- **A source-text assertion outlives the source it describes.** #8's test
  pinned a literal assignment that a refactor in the very same PR had
  replaced with a named resolver; every other assertion in the file passed.
  Assert on the thing that holds the rule, not on how it was spelled the
  first time.
- **A stacked rebase can apply one hunk twice and nothing complains.** Two
  identical function definitions in one module is legal Python: the second
  wins and the first is invisible. Neither CI nor review caught it — the
  test suite passed *through* the duplicate.

**On CI, honestly.** Both PRs showed a red "Application (macOS arm64)" check
on the *Build the shell* step, and that is this repository's standing state
rather than anything either branch did: every scheduled and push run on
`main` has failed the same way for weeks, including runs whose diff was a
reconcile commit touching only markdown. It deserves its own investigation
and did not get one here.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 86f283bd3e910293526e3192ea8f3643d0fad312

## State Impact

- target: late-pond-2851 — Two trainer flags land from cdx-rl (PRs #7 and #8, ADR-159 here; their own ADR-152/ADR-153 citations are cdx-rl's numbers and collide with this log's blueprint decisions). --init-from-task-change REASON lets --init-from cross a TASK change so a curriculum is possible at all: it skips the bundle's whole-file task digest and nothing else, with the differing top-level keys required to be a subset of CURRICULUM_TASK_KEYS (does the change alter what the network reads or emits?), and --init-from-parent-task required beside it because a .cxpolicy header carries its task's digest rather than its content. --command-slew-deg bounds the per-step change of the ISSUED command, applied after the action filter and before the ctrl write and reset with the episode -- a different operator from the EMA, which bounds smoothness and does not bound rate at all; default 0.0 is NO LIMIT (the opposite convention from the filter's alpha, where 0 freezes the command and is refused) and at 0.0 the emitted graph is unchanged, so existing policies train the same. Landed with two defects fixed on arrival: a test asserting a literal source string a refactor in the same PR had replaced with resolved_command_slew_deg(), and that resolver DEFINED TWICE from a hunk applied twice across a stacked rebase. The GPU-box blocker is untouched by this.
- target: forest-wind-0342 — Bundle staging stops trusting a directory name (ADR-159). shared_worker_bundle treated the existence of the content-addressed bundle directory as proof it was populated; macOS purges /var/folders by AGE OF FILE, so the modules go, the directory stays, and a __pycache__ written later keeps it looking fresh -- after which a sandboxed worker is handed an empty bundle and dies at import with nothing connecting it to a temp sweep days earlier. Reproduced on a real machine as three test_tessellation failures. The reuse check now requires EVERY member file, and because os.replace refuses a non-empty target a gutted bundle is moved aside under .dead-<uuid> and removed before the fresh one is published, so a worker holding the old path always holds a valid directory. New test guts a real bundle and leaves the husk a sweep leaves.
