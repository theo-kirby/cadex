---
node_id: 1eaa4167-9b34-5f26-b48b-9ce86a65c721
slug: twilight-snow-9071
title: Walk progress and project commits record portable output labels
created_at: '2026-09-08T07:34:58+00:00'
parents:
- forest-shade-2752
summary: ''
---
## What

ADR-246 removes verbatim --out from the walk's shared progress/commit formatter.
Internal outputs are recorded relative to the project; external outputs use their
basename. CLI documentation, the project architecture scaffold and a ROADMAP
checkbox carry the convention. One CLI fix, no historical project rewrite.

## Why

Advances the charter's "The walk exists and is tested headlessly" criterion and
its project-as-codebase invariant, targeting crisp-reef-5607 and chilly-union-8972.
The durable walk recorded the operator's home path in PROGRESS.md and its project
commit subject; forest-shade-2752 and the overseer selected this repair first.
Reversible assumption: the basename is sufficient identity for an external run;
two external outputs with the same basename may share a label. No general path
scrub or export/link behavior change is authorized by this finding.

## Method

Changed only the walk branch of _progress_what: expanduser, resolve and relative_to
the report's project root, falling back to basename. Added four regressions using
real progress recording and Git commits with absolute internal/external, relative
and home-relative outputs. All four failed on the old formatter. Updated both
existing toy-walk commit assertions to expect runs/walk-1 and runs/walk-2.

Ran pixi run python -m pytest cli/tests -q -ra: 200 passed, 1 failed, no skips,
217.73 s. The sole failure was the second old absolute-path expectation at
cli/tests/test_walk.py:553; actual output was the desired runs/walk-2. Updated that
expectation, then ran pixi run python -m pytest
cli/tests/test_walk.py::test_the_walk_takes_the_toy_to_a_verified_rollout_and_iterates
-q -ra: 1 passed, no skips, 34.13 s. Engine-dependent tests and real local toy CPU
training ran; remote-mode tests use a local CPU dispatcher, not remote execution.
No engine/payload/shell changes or builds. git diff --check passed.

## Result

The four new regressions pass, and the real toy walk and warm-start iterate now
verify portable commit subjects. The full-suite failure was corrected and its
affected test rerun successfully; the remaining 200 tests passed in the full run.
The CLI's persisted run label no longer carries an absolute --out machine path.
No claim of a general path scrub, no accepted project edits, no history rewrite,
no GUI or remote dispatch. Record export/check are the final graph gate.

Next: the selected durable nt3-leg --resume review-driven repair turn remains
unexercised. It must verify this label live and measure whether the stored session
actually resumes; preserve the objective/horizon before comparing reward. This
unit does not retire a charter gap or rewrite the human-owned checkboxes. The
remote-handoff and GUI-mode implementations already have ADR-200/201 evidence;
the overseer's requested follow-ups should be assessed against that evidence.
Dispatch closed: 1 unit — portable walk output labels in progress and project history.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 66188d94c467eb733312733d01dcfb965ec02df7

## State Impact

- target: chilly-union-8972 — ADR-246 records walk output labels relative to the project or by external basename; four persisted-row/commit regressions and real toy iterate verified
- target: crisp-reef-5607 — the durable walk absolute-output-label defect is fixed; a live durable resumed repair turn remains unexercised
