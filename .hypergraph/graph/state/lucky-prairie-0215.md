---
node_id: 56c3b7df-f631-5bd3-a580-a8bac365847e
slug: lucky-prairie-0215
title: W1. The whole lifecycle is watchable, on a real robot
created_at: '2026-10-05T08:57:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

orun3 charter criterion: **W1. The whole lifecycle is watchable, on a real robot.** [rec: golden-snow-6627]

- On `orun3-biped`, a copy of `~/cadex-projects/ot5-biped`: 1. the agent accepts at least two new design revisions through `cadex mcp`; 2. a short `cadex walk` training leg runs on the 5090 with checkpoints on; 3. `evaluate` runs on the result. [rec: golden-snow-6627]
- The dashboard, opened before step 1 and never reloaded, shows each stage in the overlay, the revisions on the timeline, and at least three checkpoint rollouts. Screenshots are taken at each stage. Both full suites pass (packaged gate too if protocol/payload touched). [rec: golden-snow-6627]
- Declared target `gap-w1-whole-lifecycle-watchable-real`. The owner ticks the charter box; roles do not. [rec: golden-snow-6627]

**Status judgement (maintainer):** flipped to `working` because soft-comet-8840 records measured evidence for every clause; the charter box stays the owner's. The record declared "complete pending the owner's tick" rather than an explicit status flip; damp-wave-8696 names the flip as due. [rec: soft-comet-8840] [rec: damp-wave-8696]

### Evidence (the re-run) [rec: soft-comet-8840]

On one headless page opened on `/p/orun3-biped/` before the first revision and never reloaded (one navigation entry), driver an uncommitted MCP-client script:
- **Designing:** revisions 20 and 21 via real `cadex mcp` `set_params`; overlay read `designing` ≈6 s after each; timeline `revision 21 · 21/21 · newest`, feet tinted against a revision-20 ghost; the Revisions menu agreed. [rec: soft-comet-8840]
- **Training:** 120-iteration `cadex walk` (1024 envs, `--checkpoint-every 20`, `--allow-ungrounded`) on the 5090; overlay read `training` 2 s after start; with `run:orun3-w1c` picked in `#view3d-source`, **five checkpoint rollouts (it 20–100) replaced each other live**, each labelled with iteration and reward. [rec: soft-comet-8840]
- **Evaluating:** an MCP `evaluate` read `evaluating` from its first poll (activity `evaluate · running 2 s`), then `evaluate · just now`. Enabled by ADR-553 (fc86f7f8): `cadex mcp` logs each call in flight and an in-flight `evaluate` reads as `evaluating` for the whole call, tested against a real `cadex mcp` and in a browser. [rec: tiny-bloom-2937] [rec: soft-comet-8840]
- **Failed:** `w1-try-failed.png` from the first attempt, plus a refused `set_params` shown live as an `error` activity line. [rec: solemn-fox-1118] [rec: soft-comet-8840]
- Screenshots `docs/probes/orun3/w1-*.png` (≤300 KB, dark floor). Suites after the walk: test-engine 2585 passed / 58 skipped; `cli/tests` 1172 passed / 1 skipped with the engine built. No protocol/payload change. [rec: soft-comet-8840]

### First attempt gaps, now closed [rec: solemn-fox-1118]

- Gap 1 (`evaluate` invisible: activity written only on return, eval directory lived ≈0.23 s of a ≈68 s call) — fixed by ADR-553. [rec: tiny-bloom-2937]
- Gap 2 (no live checkpoint play: a Revisions-menu pick held `ckpt.chosenSource` per ADR-545) — a driver error, avoided by picking `run:<run>` in `#view3d-source`. [rec: soft-comet-8840]

### Remaining defects seen during W1 (not blocking the criterion) [rec: soft-comet-8840]

- The `evaluating` stage line named the evaluation directory rather than ADR-553's agent-call reason (sampled once, at 1 s). [rec: soft-comet-8840]
- Progress reads "no update 37–39 s" before each checkpoint (matches the trainer stall in snowy-water-3502; not measured with rollouts off here). [rec: soft-comet-8840]
- After the walk exited, the never-reloaded scrubber did not add the `final policy` stop (a fresh page did, in solemn-fox-1118). [rec: soft-comet-8840]

## Negative knowledge

- [scope: `orun3-biped` as copied from `ot5-biped` | confidence: medium | evidence: solemn-fox-1118, soft-comet-8840] Its policy channels (25) are not grounded in onboard sensors, so `cadex walk` refuses training without `--allow-ungrounded`.
- [scope: `orun3-biped` after a walk leaves `policy_on=1` | confidence: high | evidence: soft-comet-8840] A `set_params` that changes geometry is refused because the policy output was trained on a different task bundle digest; set `policy_on: 0` in the same revision.
- [scope: a short `evaluate` through `cadex mcp` with the pre-ADR-553 return-only activity log and the 2 s poll | confidence: high | evidence: solemn-fox-1118] The `evaluating` stage was not observable while the call ran (superseded by ADR-553, tiny-bloom-2937).

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-w1-whole-lifecycle-watchable-real)
- solemn-fox-1118 — first full attempt: designing/training/failed shown, evaluate invisible, live checkpoint play blocked by a menu pick
- tiny-bloom-2937 — gap 1 fixed (ADR-553): in-flight activity, evaluating for the whole MCP call
- soft-comet-8840 — W1 re-run: every stage on one never-reloaded page, five live checkpoint rollouts, suites green
- damp-wave-8696 — names the W1 flip to working as due
