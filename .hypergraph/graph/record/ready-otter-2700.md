---
node_id: 592ccf8c-825e-5672-83a2-efed51a6f092
slug: ready-otter-2700
title: Unchanged CLI session identity preserves project metadata
created_at: '2026-09-08T07:54:24+00:00'
parents:
- vast-ledge-4610
summary: ''
---
## What

Suppress only the redundant CLI session-file replacement identified in
vast-ledge-4610. A stored nonempty session ID and matching model return the
existing AgentState without rewriting agent.json or advancing its timestamp.
Changed identity still persists on unsuccessful turns. ADR-247, CLI docs,
project architecture scaffold and the ROADMAP checkbox describe this behavior.

## Why

Short-horizon unit 2 and the overseer's explicit direction: maintain the
charter's **The walk exists and is tested headlessly** criterion and its
project-as-codebase/file-lifecycle invariant (crisp-reef-5607, calm-peak-5247).
The reversible boundary is the CLI-owned session writer. Engine restore
attempt locators are truthful and remain untouched by this correction. No
provider retry, durable project edit, metadata rollback or failure commit is
justified. The whole charter is not declared complete by this maintenance fix.

## Method

Changed only write_agent_state's no-op path in cli/cadex_cli/session.py;
the caller still writes returned identity before checking result.ok. Existing
read_agent_state ignores absent, unreadable and wrong-schema files, and its
empty-session default cannot trigger this no-op.

Added three real-engine controlled-refusal regressions through ordinary
main(walk): an offline executable emits assistant text and an error result,
then exits 1. Cases return unchanged identity, changed session ID, and changed
model. Each starts from an accepted disposable project, seeds a deterministic
old agent timestamp, and adds a pending user edit to DECISIONS.md and an
untracked user note. Assertions cover diagnostics, unchanged HEAD, source and
project docs, accepted revision/digest/parameter values, fresh accepted attempt
identity with existing staged outputs and matching latest candidate identity.
The unchanged case asserts byte, inode and mtime equality for agent.json;
changed cases assert persisted identity and updated timestamp.

Two success-path regressions drive command_prompt with the existing MockTurn
through a real bridge and engine, changing a plate from BRACKET to TALLER.
Accepted revision, digest and source change; unchanged session/model preserves
agent bytes, while changed model persists with a fresh timestamp. No real
provider is contacted. Tests use disposable projects and the existing local
engine; no build, stage refresh, GUI or remote dispatch.

A separate pytest plugin in a temporary directory loaded only the previous
HEAD's session writer into command_prompt, without swapping repository files.
The unchanged-session success case failed on byte equality; changed-model
success passed (1 failed / 1 passed / 14 deselected). This confirms the new
assertion detects the prior replacement. The full suite uses current source.

## Result

Targeted commands and turn-loop suites: 35 passed in 20.81 seconds.
Full required gate: `pixi run python -m pytest cli/tests -q` — 206 passed,
0 skipped, 0 failed in 223.39 seconds. Log: temporary local
`/tmp/cadex-189-cli.log` (not a committed artifact).
No engine Python, protocol, payload or shell changes; their build/gates are
not required for this CLI-only correction. git diff --check passes.

The actual live stored-conversation repair and its downstream training/review
remain unproven and parked with controller-owned scheduling. These tests prove
controlled refusal and local acceptance behavior, not provider resumption.
Next: return this finding for replanning; no additional defect is established
by this unit. The new record reaches three unreconciled records. Reconciliation
is due in the separate maintainer pass; this work dispatch explicitly forbids
reconcile, state-node edits and editing STATE.md despite the overseer's request.
Dispatch closed: 1 unit — unchanged CLI sessions no longer dirty project metadata; refusal and successful acceptance remain truthful.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 059865dece1e2aa940e6d75fc62765226ebcad65

## State Impact

- target: calm-peak-5247 — Suppressed redundant unchanged-session metadata replacement; changed identity persists on refusal, real restore attempts remain truthful, pre-existing user work and successful accepted edits are regression-tested
- target: crisp-reef-5607 — Five offline real-engine refusal and success regressions pass with all 206 CLI tests; live resumed repair and downstream evidence remain parked and unproven
