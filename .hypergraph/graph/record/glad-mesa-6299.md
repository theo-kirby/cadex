---
node_id: faa24201-c419-50ab-acba-b913e96c8c17
slug: glad-mesa-6299
title: 'Bet: the second mechanism on this machine, then the stale-engine guard the green walk exposed'
created_at: '2026-09-08T14:12:57+00:00'
parents:
- wandering-jasper-6102
summary: ''
---
## What

Re-rank the short horizon onto the two criterion gaps that are left, in this
order:

1. **A second mechanism through the unchanged `cadex walk --prompt` on this
   machine** (`swift-dusk-2951`, mission 2). The gate it was blocked behind is
   open.
2. **Make the walk say when the installed engine predates the tree** (missions 1
   and 2). The green walk found this the expensive way and it is not built.
3. **Audit the GUI-attached and remote-mode documents against the shape the
   green walk actually has** (`witty-spark-2613`, mission 2) — a currency audit,
   not a rewrite of ADR-200 and ADR-201.

No new direction is proposed. No charter-derived gap is retired, blocked or
superseded.

## Why

**The short rung is spent, cleanly.** All three of its units landed: the
declaration bisect, the SIGXCPU legibility repair and the end-to-end re-run
[rec: lawful-wolf-9205] [rec: wandering-jasper-6102]. The maintainer folded both
criteria they served — `crisp-reef-5607` and `damp-moon-9297` are `working` and
off the frontier. The walk ran exit 0 in 17:43 on this machine, all four legs,
all four review eyes, `cli/tests` 217 passed with no skips
[rec: wandering-jasper-6102].

**Unit 1 is the only remaining criterion that needs a run.** `swift-dusk-2951`
carries five mechanisms of nt3 evidence and was reopened by the ot4 directive on
machine grounds alone, with the explicit gate "it cannot be re-evidenced until
one mechanism completes on this machine" [rec: humble-forest-6896]
[rec: open-hollow-2140]. One has. The swing-arm rig is this machine's first
mechanism; a second, differing in joint and actuator type, is the whole
criterion. This is evidencing, not restarting — the distinction the nt3 directive
drew and the trap nt3 fell into [rec: modest-summit-8554].

**Unit 2 is a real defect, named by the run that hit it.** `build/release` still
carried the pre-ADR-250 runtime, so the walk silently ran the previous engine
until a rebuild was forced; the record says outright that "the walk does not
check that the installed engine matches the tree, and it cost this unit a full
rebuild to notice" [rec: wandering-jasper-6102]. I checked rather than assuming:
`cli/` has no engine-versus-tree staleness notion at all, and the only "stale" in
`docs/CLI.md` is ADR-204's script-mutation guard, a different thing entirely.
This matters most for the walk, which `docs/CLI.md` calls "the one thing that is
not allowed to need a person": today it can run a stale runtime and report exit 0
either way, which makes every walk's evidence conditional on a human having
remembered to rebuild. Per the question policy, take the reversible option first
— report the mismatch in the `--json` envelope and on stderr; do not refuse until
reporting has proved insufficient.

**Unit 3 is deliberately narrow.** `witty-spark-2613`'s own reconcile judgement
says what was missing was "one clean headless walk on this run's machine", and
that the remote handoff (ADR-200) and the GUI-attached document (ADR-201) "all
still hold as written" and were not reopened [rec: humble-forest-6896]. So the
unit is emphatically **not** to re-script or re-document them; that would be
re-running a landed qualification, which the medium horizon's own negative
knowledge forbids [rec: ancient-key-7299]. What is genuinely uncertain is
currency: both documents predate ADR-249's `$CADEX_MODEL`, ADR-250's worker BLAS
pin and SIGXCPU refusal, and the four-eye review leg. Check them against the
green walk's actual invocation and artifact shape, correct what drifted, and the
criterion can be declared met on this machine with its limits stated.

**Ordering, and the credit hazard.** `five_hour` is at 72%, +43 this run, and the
walk's design leg is the expensive part — 1,014.2 s of one model turn out of a
17:43 walk [rec: wandering-jasper-6102]. So: probe the model first, per ADR-249's
mechanism; if no model has credit, take unit 2 or unit 3 — neither needs a model
in the loop — and come back to unit 1. That is what keeps a credit refusal from
costing a whole iteration, which is how nt3 lost several
[rec: silent-mist-5233] [rec: sunny-walrus-5847]. Unit 1 also goes first because
the second mechanism must run with no mechanism-specific code change, and doing
it before unit 2 touches `cli/` keeps that claim trivially true.

**No new direction, and none needed.** The allowance is one. Two criterion gaps
are open with units named by evidence rather than invented, and the frontier's
other three — reduction, catalog breadth, gait scale — are parked as standing
work or under `## Later criteria`, where only a human charter edit promotes them
[rec: modest-summit-8554]. Nothing is blocked, so nothing is retired.

## Method

Fold this bet into `short` (`young-crane-9546`), `medium` (`strong-birch-7412`)
and `long` (`late-valley-7350`): the short horizon re-ranked onto the three units
above, the medium horizon reordered now that its first two items are closed, and
the long horizon corrected where it still says this machine's only measurement is
a walk that exited 3 and still names `assembly.mjcf` returning as the thing to
prove. Both of those are now false. Advance the view's high-water mark, sync,
commit.

## Result

The plan as folded. The next actor unit is the second mechanism, with a
credit-refusal fallback that does not waste the iteration.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 1025d233a83bd355f4fde5375d07632e9a596bd1

## State Impact

- target: plan/young-crane-9546 — the short rung's three units all landed; re-rank onto the second mechanism, the stale-engine report, and the three-modes currency audit, with a credit-refusal fallback order
- target: plan/strong-birch-7412 — items 1 and 2 (crisp-reef-5607, damp-moon-9297) are closed and folded to working; reorder the remaining gaps and remove the second mechanism's block, which is now open
- target: plan/late-valley-7350 — correct two now-false claims: this machine has a clean walk baseline (17:43, 2,640 MB peak), and assembly.mjcf returning for a design-agent rig is proved rather than standing
