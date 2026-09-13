---
node_id: 5f540dc4-4fd2-5ed3-a1ca-c259340767b6
slug: patient-pond-3886
title: Run ot5 stopped at iteration 111; owner ticked D1–D11, closing the ot5 charter root
created_at: '2026-09-13T15:35:37+00:00'
parents:
- empty-vine-5860
summary: ''
---
## What

Run `ot5` was stopped by the operator between iterations, after iteration 111 committed (`da05952c`), and the owner ticked all eleven done criteria D1–D11 of the ot5 charter (`.ouroboros/goal.md`, ADR-284) on 2026-09-13.

## Why

The state graph had carried every criterion at `Status: working` since about iteration 50 (the last, D9 `silent-river-6649` and D11 `fair-wolf-4645`, at 2026-09-12 19:25 local), and only the owner's checkbox closes a criterion. The charter's exhaustion policy said "repeat the lifecycle", so iterations 52–111 repeated it (Wren, then Lark and its working copy) while the loop detector fired `no_frontier` for 60 iterations straight and rotated the actor four times to no effect. The evidence the owner accepted is the evidence each D node cites; three fresh bipeds (Reed, Wren, Lark) went through create → save → reopen → train → record → review → revise → retrain → revisit, and the persistent operator dashboard is live on the private address, port 8765, serving `ot5-lark-copy85`.

## Method

`ouroboros-checkup` over `.ouroboros/runs/ot5/` (iterations.jsonl, critic.jsonl, loop.log), `git diff --stat main...ouroboros/ot5`, and the status history of the eleven D state nodes via `git log` on each file. `ouroboros stop` at 2026-09-13T14:44Z with a clean tree; `ouroboros archive` wrote `.ouroboros/history/ot5.md`, whose `## What this taught` holds the operator's conclusions.

Numbers: 111 iterations in 19.4 h; 136 commits, 283 files, +47,157 / −103 lines; critic verdicts continue 101, reject 5 (all fixed forward the next iteration), looping 2, stuck 2, done_rejected 1; 0 reverts; `no_frontier` longest streak 60.

Two operational findings, both recorded in the digest: the Codex critic issued zero tool calls in its first 106 verdicts because Codex's default bubblewrap sandbox cannot start under `kernel.apparmor_restrict_unprivileged_userns=1` on this Ubuntu 24.04 host (fixed for future runs with `features.use_legacy_landlock = true` in `~/.codex/config.toml`, verified: reads work, writes are denied); and Codex's weekly window went 25 % → 100 % as critic and is blocked until 2026-09-19.

## Result

D1–D11 are ticked in the charter. The ot5 charter root `crisp-sun-1239` has no open criterion under it and leaves the frontier. `docs/probes` grew by 26.5k lines (2.9 MB) of evidence receipts and the Tailscale address appears 27 times in committed docs; both are noted for the next charter rather than reverted. The run branch is merged into `main` with a merge commit (record nodes cite SHAs; never squash).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: da05952c98cda75ee85c87f8cd64eefee03c1cf0

## State Impact

- target: crisp-sun-1239 — status open → working: the owner ticked D1–D11 on 2026-09-13 after run ot5; no criterion under this root is open. Carry the ot5 digest's lessons as negative knowledge: evidence receipts in docs/probes reached 2.9 MB against a 'compact evidence' line, and the critic ran without tools for 106 verdicts
- target: jolly-loom-0622 — owner ticked D1 on 2026-09-13 (charter checkbox); evidence unchanged
- target: shy-meadow-0959 — owner ticked D2 on 2026-09-13 (charter checkbox); evidence unchanged
- target: dawn-delta-4361 — owner ticked D3 on 2026-09-13 (charter checkbox); evidence unchanged
- target: candid-harvest-2614 — owner ticked D4 on 2026-09-13 (charter checkbox); evidence unchanged
- target: sharp-union-6036 — owner ticked D5 on 2026-09-13 (charter checkbox); evidence unchanged
- target: clever-field-7845 — owner ticked D6 on 2026-09-13 (charter checkbox); evidence unchanged
- target: cold-vale-4232 — owner ticked D7 on 2026-09-13 (charter checkbox); evidence unchanged
- target: cool-gate-3332 — owner ticked D8 on 2026-09-13 (charter checkbox); evidence unchanged
- target: silent-river-6649 — owner ticked D9 on 2026-09-13 (charter checkbox); evidence unchanged
- target: deep-clover-6012 — owner ticked D10 on 2026-09-13 (charter checkbox); evidence unchanged
- target: fair-wolf-4645 — owner ticked D11 on 2026-09-13 (charter checkbox); evidence unchanged
