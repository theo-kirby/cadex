---
node_id: 46ce9a05-0d5a-5003-aa11-b7edcb87a90b
slug: sunny-walrus-5847
title: Durable resumed repair walk stops at usage-credit refusal
created_at: '2026-09-08T07:38:10+00:00'
parents:
- twilight-snow-9071
summary: ''
---
## What

Ran exactly one bounded `cadex walk --resume` repair attempt on the durable
`nt3-leg` project, outside this repository. The design leg stopped on a provider
usage-credit refusal. No retry, wait for credits, provider switch, paid fallback,
GUI launch or remote execution followed.

## Why

Advances the charter criterion **The walk exists and is tested headlessly**
(crisp-reef-5607), specifically the remaining live-conversation repair-turn
measurement, and the review-driven iterate in calm-peak-5247. Short item 1's
ADR-246 formatter fix was already committed and accepted at d1231083; this is
short item 2, following twilight-snow-9071.

The overseer asked for reconciliation first, but this work dispatch explicitly
forbids reconciliation without exception. The reversible assumption was to leave
state and plan untouched, consume the pending records as evidence, and execute
the selected single repair attempt. Reconciliation remains the maintainer's work.

## Method

Read the durable project's current script metadata, baseline PROGRESS.md,
ARCHITECTURE.md, DECISIONS.md, clearance and inventory reports, actuator and
sensor notes, and stored agent session before dispatch. Initial project status
was clean at b244f26, revision 417d0fdf3286, digest e6395e3e49c4. Rechecked the
qualified payload's CadexScriptedRuntime.py SHA256:
602164e85c399ad203517eb269ec81bca549dc07b72d303659c1cffffe1dc6df.

Used the documented command shape, with absolute --project and --out paths
resolved locally (no machine paths retained here):

```sh
JAX_PLATFORMS=cpu <training-venv>/bin/python <existing-process-tree-monitor> \
  ./cadex walk --resume --engine build/engine/cadex-engine-0.0.0-macos-arm64 \
  --project <durable-project> --out <durable-project>/runs/repair-i187 \
  --prompt <review-driven-repair-prompt> --trainer-python <training-venv>/bin/python \
  --iterations 1 --envs 4 --seed 0 --timeout 600 --json
```

PYTHONPATH, CADEX_ENGINE_ROOT and CADEX_MODULE_DIR were unset. Used the existing
nt3_monitor.py: process-tree RSS sampled every 0.2 s, 2.9 GiB / 850 s limits,
TERM then KILL on cutoff. The training interpreter was the repository's ignored
.venv per training/SETUP.md. Local ignored logs are
build/lifecycle/nt3-i187-leg.json and nt3-i187-leg.err.

The single prompt named docs/clearance.md, docs/inventory.md, docs/actuators.md,
docs/sensors.md and DECISIONS.md, without supplying measured answers. It asked
for one justified geometry correction and a closing DECISION line, preserving
separately placed purchased hardware, task/reward expressions and weights,
observation/action definitions and units, rollout horizon and walk policy
convention. It forbade treating intentional face contacts as automatic defects
or claiming print-fit qualification for the boss. No operator script edits.

## Result

**Design: blocked by provider, exit 1, 3.72 s.** Exact error:
"You're out of usage credits. Switch to another model, or manage usage credits at
claude.ai/settings/usage?from=cc_cli_limit_message, to continue."
The outer envelope reported the same error prefixed by
"the design turn was not accepted (leg design, exit 1)".
Monitor exit 1 in 3.9086 s, peak tree RSS 432,635,904 bytes, cutoff null.

**Training, declaration, verification/rollout and review: unreached.** There is
no new reward, clearance measurement, inventory, view, section or bound-agreement
result to compare. The baseline remains 0.8530453495479725 total_reward,
45 pairs / 9 offending zero-volume contacts / 0 unknown, and six catalog
instances. Four-view/XZ inspection and the 1e-3 mm agreement checker were not
rerun against old artifacts and presented as repair evidence.

**Actual stored-conversation resumption is not established.** The design argv
contains --resume; the persisted session id is unchanged. There is no reported
fresh-session fallback, but the provider refusal is no successful second design
turn. No geometry correction was chosen or accepted.

**Portable output-label verification is unreached.** No new PROGRESS.md row or
project commit was created, so the accepted formatter fix retains its earlier
regression/toy-walk evidence only. The old baseline row and subject still contain
the historical absolute label; no history rewrite was attempted.

**Project cleanliness check failed:** HEAD is still b244f26, but agent.json and
script.json are modified. The diff is only agent updated_at plus restored
accepted_attempt/latest_candidate attempt identifiers and script updated_at;
accepted revision, digest and parameters are unchanged. Script source, domain
notes, progress and decisions are unchanged. These runtime metadata changes are
preserved as evidence; no operator restore or synthetic accepted-run commit was
made. The next authorized visit must account for that dirty metadata baseline.

No repository product source changed, so no zone pytest suite or build was
warranted; the bounded runtime attempt is this experiment's gate. Hypergraph
export/check are the record gate. No checkpoint, rollout, project artifact or
machine path enters the repository. The pending tail grows by this record and
must be handled by the separate maintainer, not this actor.

Next: return scheduling to the controller on the quota finding. The successful
same-session repair, comparable reward/review measurements, live portable-label
check and clean project end state remain missing before this repair-turn claim
can be ticked. Do not automatically retry or switch providers. The existing
charter claims for remote/GUI modes and second mechanism are not reclassified by
this failed design attempt.
Dispatch closed: 1 unit — bounded durable resumed repair attempt refused for usage credits; downstream verification unreached.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: d1231083f2fded54aec1b5cd6aaaee38b2da46a9

## State Impact

- target: crisp-reef-5607 — One durable --resume repair attempt refused at design for usage credits; actual resumption and live portable-label verification remain unproven, with no retry
- target: calm-peak-5247 — Repair training and review were unreached; durable project retains baseline model and notes but runtime metadata in agent.json and script.json is dirty
