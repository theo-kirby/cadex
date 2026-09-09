---
run: nt1
machine: mmini
started: 2026-09-06T00:07:32
ended: 2026-09-06T12:03:23+00:00
hours: 13.9
state: killed
iterations: 89
commits: 173
criteria_ticked: 0
criteria_closed: 0
criteria_total: 11
merged: 6a69684928d43ef659f11b4b9e0c1766eb761e3a
branch: ouroboros/nt1
mode: actor-critic
memory: hypergraph
actor: claude:claude-opus-5
---

# Run nt1

89 iterations in 13.9h on `mmini`, killed (3 failed iteration(s) in a row). Branch `ouroboros/nt1`, merged as `6a696849`.

## The numbers

| | |
|---|---|
| iterations | 89 (changed 6, recorded 14) |
| commits | 173 — 1012 files changed, 6192 insertions(+), 236663 deletions(-) |
| criteria | **this run ticked 0**; 0 of 11 checked at the tip |
| reverts | 23 |
| verdicts | continue 23, done_rejected 1, revert 23, stuck 42 |
| loop detector | no firing |
| roles | actor claude:claude-opus-5, critic codex:gpt-6-astra, maintainer claude:claude-opus-5, overseer claude:claude-opus-5, planner claude:claude-opus-5 |

## What landed

- ouroboros #87: ADR-198 — the translation subsystem disabled in the shell, the second Phase 13b disable commit
- ouroboros #87: ADR-196 — the Cycles delete commit's build and gate evidence, from iteration #86's logs
- ouroboros #86: no record
- ouroboros #84: no record
- ouroboros #83: ADR-196 — Cycles disabled in the shell, and the disable commit built and gated for the first time
- ouroboros #82: the worker computes an exploded view itself; CommandCreateView leaves the engine's authoring path (ADR-197)
- ouroboros #55: You've hit your session limit · resets 12:50pm (Europe/Madri
- engine: the INSPECTION_FAILED frame is the one tool-failure envelope (ADR-195)
- cli: compare and record — the delta in the PROGRESS.md row, and a git repository the project owns (ADR-194)
- cli: the project is a codebase — ARCHITECTURE/DECISIONS/PROGRESS scaffolded, read on every turn, appended by convention (ADR-193)
- cli: iterate is a script convention plus the curriculum pair on cadex train (ADR-192)
- cli: document and record cadex train, the offboard trainer's dispatcher (ADR-191)
- ouroboros #24: You've hit your session limit · resets 7:50am (Europe/Madrid
- cli: a trained policy comes home headlessly — cadex asset --put and put_asset in the agent's surface (ADR-190)
- cli: cadex export copies every staged non-BREP output under its staged name (ADR-189)
- docs: the lifecycle audit — which legs of the walk still need a person (MUJOCO.md §7c)
- ouroboros #19: no record
- Give a locked-out project a button back in (ADR-187)
- Hydrate the model when a file is opened (ADR-186)

## Decisions the overseer made

- #5 revert: rules fallback (overseer agent failed): same error 3x
- #6 stuck: rules fallback (overseer agent failed): no changes for 3 iterations
- #7 stuck: rules fallback (overseer agent failed): no changes for 4 iterations
- #8 revert: rules fallback (overseer agent failed): same error 3x
- #9 stuck: rules fallback (overseer agent failed): no changes for 6 iterations
- #10 stuck: rules fallback (overseer agent failed): no changes for 7 iterations
- #11 revert: rules fallback (overseer agent failed): same error 3x
- #12 stuck: rules fallback (overseer agent failed): no changes for 9 iterations
- #13 stuck: rules fallback (overseer agent failed): no changes for 10 iterations
- #14 revert: rules fallback (overseer agent failed): same error 3x
- #15 stuck: rules fallback (overseer agent failed): no changes for 12 iterations
- #16 stuck: rules fallback (overseer agent failed): no changes for 13 iterations
- #17 revert: rules fallback (overseer agent failed): same error 3x
- #18 stuck: rules fallback (overseer agent failed): no changes for 15 iterations
- #26 revert: rules fallback (overseer agent failed): same error 3x

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

The first run, and the one that showed the loop works at all: 173 commits, and a
2.8M-line inherited-tree reduction started here. But only 6 of 89 iterations
changed anything, with 42 `stuck` verdicts and 23 reverts, because a single
harness with no fallback spends most of a night waiting on its own usage window.
Codex was added as the fallback for every role because of this run.

The charter opened with 0 of 11 criteria checked, which is the honest way to
write one, and none of them closed.
