---
node_id: a83f8992-e37a-5c49-b09f-36ec2ae7f6be
slug: western-reef-4119
title: 'Bet: the frontier is dry — the iterate row, then the walk''s self-certifying evidence'
created_at: '2026-09-08T14:47:02+00:00'
parents:
- early-quill-3654
summary: ''
---
## What

**The charter's frontier for this run is empty**, so this pass invents. All four
of the `## Done criteria` boxes that seeded gaps are `working`: the walk exists
and is tested headlessly (`crisp-reef-5607`), the eyes (`damp-moon-9297`), three
modes (`witty-spark-2613`), and the second mechanism (`swift-dusk-2951`). The
three nodes still open on the frontier are standing work (`round-glacier-2865`)
or parked under `## Later criteria`, which the planner may not target
(`brave-stone-9609`, `late-pond-2851`).

One new direction — the allowance is one — plus three ranked units, the first
two model-free:

1. **The iterate leg, run on this machine, model-free.** `cadex walk --set` with
   no `--prompt` runs zero design turns and the whole rest of the loop, so a
   second row lands in `~/cadex-projects/ot4-carriage` for a parameter change,
   comparable with the baseline at the same 5 × 16 × seed 0.
2. **The stale-engine report, built** — the `--json` field `rare-cliff-9595`
   deliberately left free when it took the doc paragraph instead.
3. **The end-to-end prompt walk**, model-gated, once units 1 and 2 have changed
   the `cli/` underneath it.

Direction: **the walk's evidence must be self-certifying** (missions 1, 2, 6).

## Why

**The frontier ran dry, and the charter's own rule says what happens next is a
human edit.** "Promote a criterion by moving it up when the frontier lands or
blocks; that is a human edit, and it mints a new directive." The human is
asleep and `## Later criteria` is explicitly barred to me. So the honest
description of this run's state is: *the run's stated target is met, and the
backlog is locked until morning.* What is left to me is the charter's standing
work — mission 1 ("keep it working"), the long rung's standing lifecycle
maintenance, and one invented direction.

**Three directions considered; one picked.**

- **(a) The walk's evidence must be self-certifying (missions 1, 2, 6). Picked.**
  It is the only class of defect the two green walks on this machine actually
  exposed, and its first unit is named by evidence rather than invented:
  `rare-cliff-9595` reported the stale-engine hole as a `docs/CLI.md` paragraph
  and said in as many words that it "leaves the field free for whoever takes
  that unit". Verified in source rather than assumed — `cli/` has no
  engine-versus-tree staleness notion at all, and `docs/CLI.md:190` now
  documents the hole it does not close. The claim under it: `docs/CLI.md` calls
  the walk "the one thing that is not allowed to need a person", and today its
  exit 0 is conditional on someone having remembered `pixi run build-engine`.
- **(b) Mission 1's file lifecycle, made checkable on this machine. Not picked.**
  Mission 1 is the charter's first priority and this run has never touched it —
  but it cannot be *run* here. No shell build tree exists (`shell/build_darwin`
  absent, only `shell/build_files` on disk), `package/app/build_app.sh` is
  macOS-shaped, and `pixi run gate` runs against a bundle that does not exist.
  The unit would be an audit ending in "no", and the standing negative knowledge
  bars audit campaigns. Recorded as negative knowledge instead, where it is
  worth more: it is also a fact about mission 9's fleet.
- **(c) Inherited-tree reduction resumed (mission 3). Not picked.** The charter
  retired it as a target in this run's own words, and nt2 spent 40+ iterations
  there closing no criterion.

**Unit 1 is model-free and I checked that rather than hoping.** `command_walk`
loops `for index, prompt in enumerate(args.prompts)`, so with no `--prompt` there
are zero design turns; `--set NAME=VALUE` is documented in the parser as "the
iterate step. Blanks the policy switch, applies the change, and exports the new
bundle before training." That matters at this moment specifically: `five_hour`
is at **95%**, +66 this run. A unit that needs a model turn cannot be dispatched
now without risking a credit refusal, and a credit refusal costing an iteration
is how nt3 lost several.

**Unit 1 is also named as missing by the plan's own long rung**, so it is not
invention: "A second row with unchanged objective/horizon will be the first
comparable pair for this durable project, not the first iterate comparison in
the product." Both walks on this machine produced a single baseline row each.
The iterate verb is the centre of mission item 2 — "change what did not work,
update the policy, retrain, compare" — and the criterion that ticked it did so
on another machine.

**One thing I expected to find and did not, which is why it is not a unit.** I
went looking for the review step to be toothless — mission 6 says "the loop is
only as good as its review step" — and `command_clearance`
(`cli/cadex_cli/__main__.py:851`) does return `EXIT_OK` whatever
`pair_status` decided. But the offending pairs are *not* silent: they land in
`docs/clearance.md`, in `review.json` as `offending_pair_count` and
`offending_pairs` (`__main__.py:1426–1438`), and in the `PROGRESS.md` row
template (`__main__.py:1624`, documented at `project_docs.py:169`). So the only
open question is whether a design finding should *refuse*, and the question
policy's reversible option — report it — is already taken. Recorded as negative
knowledge so the next actor does not "fix" a non-problem.

## Method

Read against the source, not against the docs, for every claim above:
`cli/cadex_cli/__main__.py` (the walk parser's `--set`, `command_walk`'s prompt
loop and usage guards, `command_clearance`, the review leg's clearance block and
the PROGRESS row template), `cli/cadex_cli/clearance.py` (`pair_status`, the
`status` field), a `stale` grep over `cli/cadex_cli/`, `docs/CLI.md`,
`package/app/build_app.sh`, and `ls shell/build_*`. STATE.md's frontier and
architecture listing for the four criteria now `working`. `rare-cliff-9595` and
`early-quill-3654` for what the last two iterations left behind.

No code written, no state node touched, no charter edit, no gap retired.

## Result

`short` (`young-crane-9546`) re-ranked onto three units — the model-free iterate
row, the stale-engine report, and the model-gated end-to-end re-run — with the
credit rule restated at 95%. `medium` (`strong-birch-7412`) rewritten: its first
two items closed, so self-certifying evidence leads, then the parked gaps in the
charter's order, with the plain statement that the run's criteria are met and
promotion is the human's. `long` (`late-valley-7350`) records the frontier going
dry, the second mechanism's numbers beside the swing arm's, and the file-lifecycle
gate that does not exist on this machine.

No charter-derived gap is retired, blocked or superseded: none is blocked.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 460ebec8a23bdde8ed39925c03cb64630361cc1e

## State Impact

- target: plan/young-crane-9546 — re-rank short onto the model-free iterate row, the stale-engine report and the model-gated end-to-end re-run
- target: plan/strong-birch-7412 — rewrite medium: the two led items closed, self-certifying evidence leads, the rest parked in charter order
- target: plan/late-valley-7350 — record the dry frontier, the second mechanism's numbers, and the absent file-lifecycle gate on this machine
