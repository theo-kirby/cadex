---
node_id: 4c854910-b138-5fb7-9b9a-7d7ae61123e9
slug: light-path-5130
title: 'orun2 R1: prune the frontier to live work — supersede stale ot7/ot10/orun1 criteria, replace the plan with the orun2 ladder'
created_at: '2026-10-03T15:49:48+00:00'
parents:
- even-clover-8953
summary: ''
---
## What

R1's last piece: the state graph's frontier is pruned to live work. One record supersedes, each with its reason, the stale open criteria of closed runs — ot7 F4, F5, F6, F7, F10; ot10 A5, A7; orun1 C1 — corrects the two live nodes that still describe shell surfaces (`late-pond-2851`'s Training panel, `round-glacier-2865`'s Phase 12), and replaces the three plan bets (short `young-crane-9546`, medium `strong-birch-7412`, long `late-valley-7350`), which still named a shell client and the pre-orun2 missions, with the orun2 horizon ladder. No code or doc changed; the change is the declared impacts below.

## Why

The critic's message for this iteration: write one record whose impacts supersede each stale node, replace the short plan with the orun2 ladder, then reconcile. Charter R1 asks that "the state graph's frontier lists only live work", naming exactly ot7 F4–F7, F10; ot10 A5, A7; orun1 C1, "and anything else the shell made moot".

**Deviation, stated:** I did not reconcile. This iteration's dispatch forbids the hypergraph-reconcile skill, `hypergraph update` and state writes in a work iteration "no exceptions", and that instruction outranks the critic's request. The tail is now three records (careful-rain-8917, even-clover-8953, this one), which meets the charter's "three unreconciled records" reconcile trigger; the next reconcile pass folds all three, and STATE.md regenerating clean after that pass is what completes R1's frontier clause.

Per-node reasons (each verified against `.ouroboros/RUNS.md` and `.ouroboros/history/`):
- **ot7 F4–F7, F10** — ot7 ended and was archived (172 iterations, merged `fa75c531`, 0 of 10 ticked by the owner). F4, F5 and F6 already read "exhausted"; F7's last verdict was taken outside the accepted pin; F10's report (`docs/probes/ot7/REPORT.md`) exists and claimed done. No later charter re-opened them, and the design bar they measured was replaced by ot10's rubric, then orun1's owner-calibrated judge (ADR-478) and design-language rewrite (ADR-479–484).
- **ot10 A5, A7** — ot10 ended and was archived (merged `d8f69d6c`, 0 of 11 ticked). Both are scored "under A1's frozen rubric", which orun1 retired (ADR-479–484: "ot10 rubric retired"); the judge they depend on no longer stands. The design bar moves to the shelved base-plus-styles charter that runs after orun2.
- **orun1 C1** — orun1 was killed by the owner at iteration 33 "for scope rather than progress" (history/orun1.md "What this taught") and archived (merged `3e345fd2`). Its closing report was never the owner's ask; the follow-on is the shelved base-plus-styles charter.
- **late-pond-2851** — says `--progress` "lights the shell's Training panel" and calls ADR-169's curve "the shell's first plot"; the shell is deleted (ADR-498). Training visibility is the dashboard's (D2/D3), and the curve field itself is unchanged.
- **round-glacier-2865** — "Phases 11 and 12 — replacing the engine and the shell with our own": Phase 12 (the Rust shell) is superseded by ADR-500 ("a desktop app that copies the dashboard"), and Phase 13b's shell half is closed (careful-rain-8917).
- **The plan** — `young-crane-9546` (rollout-pose clearance, section plane) names "the shell client" as a same-PR obligation and cites the ot4 missions; medium and long cite the walk coverage and North-Star missions of ot4. None is an orun2 rung. The planner role is off this run ("the critic names the next unit"), so the ladder below is a copy of the charter's horizon ladder, ordered by what has landed.

Not superseded, judged live: `shady-rose-6292` (one prompt to a walking robot — the product's end goal), `late-pond-2851` (training loop, W1 step 7 uses it), `brave-stone-9609` (parts library), `round-glacier-2865` (inherited-tree reduction, the charter's long-term rung 3). The superseded nodes' clearance and section-plane ideas are not lost: they stay readable in their records (lively-grove-8186, dry-falcon-5463) and can be re-promoted after orun2.

## Method

Read STATE.md's frontier; read each target state node's `## Current`; confirmed run outcomes in `.ouroboros/RUNS.md`, `.ouroboros/history/orun1.md`; grepped live open nodes for `shell`/`Blender` (hits only in `late-pond-2851` and `round-glacier-2865`); confirmed view-qualified impact syntax (`plan/<slug>`) in `.claude/skills/hypergraph-record/SKILL.md` and the `views: plan` block in `.hypergraph/config.yml`. Minted with `hypergraph new record`, then `hypergraph export` and `hypergraph check`.

## Result

What is true now: the record graph declares every stale frontier node superseded with its reason, and the plan's three bets replaced with the orun2 ladder. STATE.md still shows them open until the next reconcile folds this record — that is the only R1 step left, and it is a reconcile pass, not a work unit.

Concerns for the next iteration:
- **Reconcile is due** (three unreconciled records). Whoever reconciles must set the eight criteria to `superseded` with the reasons above, rewrite the two live nodes' shell sentences, rewrite the three plan nodes, and mark `eager-sea-3906` (R1) as having its evidence complete pending the owner's tick.
- After that, **D1** is next per the critic: `./cadex` with no project serves the dashboard over a projects directory, a `pixi run app` (or equivalent) one-command path on linux, then re-run `docs/probes/orun2/measure_d1.sh` for the after numbers.
- No code changed, so no suites were run; no new dependency.

Dispatch closed: 1 unit — R1 frontier pruning declared: 8 stale criteria superseded, 2 shell sentences corrected, plan replaced with the orun2 ladder (reconcile deferred: forbidden in a work iteration)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 5dc4ec9c126d81db4ba132e6e44b85106f34c07b

## State Impact

- target: polished-forest-0215 — superseded: ot7 ended and is archived (merged fa75c531); F4 was already exhausted, and no later charter re-opened it; the design bar it measured was replaced by orun1's owner-calibrated judge (ADR-478) and design language (ADR-479–484)
- target: stormy-aspen-5433 — superseded: ot7 ended and is archived (merged fa75c531); F5 was already exhausted; no later charter re-opened it
- target: narrow-dune-9454 — superseded: ot7 ended and is archived (merged fa75c531); F6 was already exhausted; no later charter re-opened it
- target: rapid-grove-9687 — superseded: ot7 ended and is archived (merged fa75c531); F7's last verdict stands as recorded; no later charter re-opened it
- target: first-snow-5587 — superseded: ot7 ended and is archived (merged fa75c531); F10's report docs/probes/ot7/REPORT.md exists and claimed done; the owner did not tick it and no later run carries it
- target: loyal-fountain-8709 — superseded: ot10 ended and is archived (merged d8f69d6c); A5 is scored under ot10's frozen rubric, which orun1 retired (ADR-479–484); the design bar moves to the shelved base-plus-styles charter after orun2
- target: rough-vale-0587 — superseded: ot10 ended and is archived (merged d8f69d6c); A7 depends on ot10's retired rubric (ADR-479–484); the design bar moves to the shelved base-plus-styles charter after orun2
- target: gentle-bramble-6120 — superseded: orun1 was stopped by the owner at iteration 33 for scope, not progress, and archived (merged 3e345fd2); its follow-on is the shelved base-plus-styles charter, not a closing report
- target: late-pond-2851 — the shell's Training panel is gone with the shell (ADR-498): --progress and the ADR-169 curve field are unchanged and are now read by the dashboard; drop the 'lights the shell's Training panel' and 'the shell's first plot' phrasing
- target: round-glacier-2865 — Phase 12 (replacing the shell with our own) is superseded by ADR-500: a desktop app, if ever built, copies the dashboard; Phase 13b's shell half is closed; Phase 11 stays unscheduled by decision
- target: eager-sea-3906 — frontier pruning declared (this record): the last R1 piece; once reconciled, every R1 item has evidence, pending the owner's tick
- target: plan/young-crane-9546 — replace with the orun2 short rungs: 1. D1, one command from clone to dashboard (./cadex with no project serves the dashboard over a projects dir; a pixi app task; re-run measure_d1.sh for the after numbers). 2. D2 write paths through the CLI's own code (params with p50/p95 beside the raw-NDJSON bar, prompt turns with live transcript, comments and part-picks, accept/reject/restore), each browser-tested against a real engine, writes token- or same-origin-gated on 127.0.0.1. 3. D2 inspection: section, exploded and collision views, rollout playback, STEP/STL export and concept-sheet download. Supersedes the rollout-pose clearance and section-plane bets (ot4 missions, named a shell client)
- target: plan/strong-birch-7412 — replace with the orun2 medium rungs: 1. A1, the agent's non-blocking channel to the dashboard (flag, question; answers reach the next turn) pinned at the tool surface with an ADR; collision_view's t=0 contact report folded into inspect or a tool; agent timeout and memory budgets stored in the project config with CLI overrides. 2. D3, runs as first-class (CLI turns and Ouroboros runs, iterations, verdicts, criteria, artifacts), orun1's probes as the fixture. 3. The headless blueprint composer after D2's write paths, re-derived without copying shell code, with a test
- target: plan/late-valley-7350 — replace with the orun2 long rungs: 1. W1's full walk on an orun2-* copy of a robot project, the parity ledger complete, then C1's closing report. 2. The dashboard design pass against docs/DASHBOARD.md. 3. Further subtraction of anything that served only the shell, each with an ADR. 4. Every gate green, every doc true, STATE.md reconciled
