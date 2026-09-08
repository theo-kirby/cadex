---
node_id: 5942d18b-40ef-52a0-b8f4-bc1308ef5888
slug: vast-ledge-4610
title: Offline refusal isolates restore bookkeeping and unchanged-session timestamp churn
created_at: '2026-09-08T07:47:17+00:00'
parents:
- gentle-wind-1003
summary: ''
---
## What

Diagnosed the refused walk's tracked metadata changes with a real local engine
and a controlled offline provider executable. Restore alone accounts for the
script metadata diff. A refusal carrying the unchanged session/model adds an
avoidable agent timestamp rewrite. No product fix was made in this unit.

## Why

Short item 1 of gentle-wind-1003: independently verifiable maintenance of the
charter's **The walk exists and is tested headlessly** criterion and its
project-as-codebase/file-lifecycle invariant (crisp-reef-5607, calm-peak-5247).
The dirty durable project is evidence, not authorization to reset it. The
reversible assumption is to preserve truthful restore bookkeeping and narrow
any correction to unchanged CLI-owned session state. The overseer's reconcile
request belongs to the separate maintainer; this work dispatch forbids it.

## Method

Read STATE.md, the actor and record skills, the graph contract, VISION, the
previous refusal record, and the durable nt3-leg `git diff -- agent.json
script.json` read-only. It matches sunny-walrus-5847: only agent updated_at and
script accepted_attempt (id/staging), latest_candidate.attempt_id and updated_at.
No command opened that durable project through Cadex or wrote to it.

Ran `pixi run python /tmp/nt3_refusal_diag.py` against a disposable temporary
project using the existing explicit payload
`build/engine/cadex-engine-0.0.0-macos-arm64`. No stage refresh or build.
CadexScriptedRuntime.py SHA256 remained
602164e85c399ad203517eb269ec81bca549dc07b72d303659c1cffffe1dc6df.
Child CLI environment omitted PYTHONPATH, CADEX_ENGINE_ROOT and CADEX_MODULE_DIR.

Reproduction recipe (all project paths are disposable):

1. Accept a script through ordinary `cadex script --set <source> --project P
   --engine E --json`: `p = params(width=num(30.0, unit="mm", min=10.0,
   max=90.0, step=1.0))` then
   `result = {"plate": part.box(p.width, 20.0, 6.0)}`.
2. Seed agent.json with write_agent_state(session_id="offline-session-188",
   model="sonnet"); set its fixture timestamp to 2000-01-01T00:00:00Z to
   distinguish writes without a clock wait. Commit the fixture. Baseline clean.
3. Open once via CadexdClient(resolve_engine(E)), open_project(P, restore=True),
   then shutdown. Snapshot again; no provider or CLI session write in this leg.
4. Run the ordinary `cadex walk --resume --prompt <offline refusal> --project P
   --engine E --out P/runs/refused --claude <fake-executable> --model sonnet
   --json`. The executable emits an assistant text frame saying
   `Controlled offline usage-credit refusal`, followed by a result frame with
   is_error=true, the same session_id and result text, and exits 1. It cannot
   contact a provider. The assistant frame models the no-fallback path observed
   in the durable attempt.
5. Compare parsed script.json and agent.json, SHA256 of every tracked file,
   git status and HEAD at baseline, restore-only and refused-walk boundaries.
   Assert accepted revision/digest/parameter values and source/doc bytes remain
   equal; assert the new accepted staging directories contain outputs.

The first fixture emitted only a result frame; it also reproduced the writes,
with the existing ClaudeTurn.run fallback invoking the offline fake again
because _model_spoke requires an assistant frame. Repeated the experiment on a
fresh disposable project with the assistant frame above to isolate the intended
path. Neither fixture invoked a real provider. Both diagnostic scripts exited 0.
Temporary script, snapshots and log remain local, not committed project assets.

Write-site trace at repo commit 103d7799:

- cli/cadex_cli/__main__.py:511 _engine_session opens/restores before creating
  ClaudeTurn. cadexd.py:423 reruns the stored source through the write lifecycle.
- CadexScriptedRuntime.py:1941 validation persists latest_candidate; :1977
  accept_project_candidate persists accepted_attempt and accepted candidate.
  CadexScriptStore.py:193 write stamps updated_at. These occur before refusal.
- CadexScriptedRuntime.py:721 reads accepted_attempt.staging to locate the live
  accepted bundle; it is not merely an arbitrary historical label. Acceptance
  also records history and prunes artifacts. Preserving an old locator by
  blanket metadata rollback would require a separate artifact-lifetime proof.
- cli/cadex_cli/__main__.py:697 writes any returned session_id before testing
  result.ok. session.py:93 write_agent_state unconditionally timestamps and
  atomically replaces agent.json, even when session_id and model are unchanged.
  docs/CLI.md section 5 describes session identity persistence, with no promised
  last-attempt timestamp semantics.

## Result

Final fixture: script acceptance exit 0; restore ok=true; refused walk exit 1,
only design in legs, 0.68 seconds, review empty, exact controlled refusal in the
outer error. No training, policy declaration, rollout or review was reached.

Accepted revision 54656f3c6e09 and digest 8eeaaa3825e5 stayed equal throughout.
Parameter overrides stayed {}; width's declared default remained 30 mm. The
entire parsed script state differed only at these four paths on each restore:
accepted_attempt.attempt_id, accepted_attempt.staging,
latest_candidate.attempt_id, updated_at. Attempt suffixes advanced from
d699ea6160a2 to 2d613c48b0dd to 69916db8f403. Timestamps advanced from
07:45:30Z to 07:45:31Z to 07:45:32Z on 2026-09-08. The initial staging parent
is the pre-discovery revision; accepted_revision was already the final revision
at baseline. Both restored accepted artifact directories existed with outputs.

Restore-only preserved agent.json byte-for-byte and dirtied only script.json.
Refused design preserved agent session_id/model but changed updated_at from the
fixture date to 2026-09-08T07:45:32Z, leaving agent.json plus script.json dirty.
All other tracked files were byte-identical, including script.py,
ARCHITECTURE.md, DECISIONS.md and PROGRESS.md. HEAD stayed d175c95537bf throughout;
no failure commit or progress row appeared. The walk created its empty output
directory, which Git does not track.

Finding: a clean Git status after an unsuccessful walk is not the correct
invariant when opening has successfully regenerated the accepted artifacts.
The script writes represent truthful acceptance of that restore, not evidence
that the refused provider edited geometry. No engine fix or rollback is
justified by this experiment.

Smallest safe correction boundary for the conditional next unit: suppress
write_agent_state's replacement when an existing valid stored session_id/model
already equal the returned values. Retain the stored timestamp for that no-op;
persist changed identity/model even on failure because a failed turn can still
create a resumable conversation. Do not gate all persistence on result.ok, ignore
tracked metadata, commit failures automatically or roll back pre-existing changes.
The correction needs changed-session/model and successful accepted-turn coverage,
plus docs/CLI.md and the project scaffold explaining timestamp semantics. This
unit only establishes the boundary; it does not implement or certify that fix.

Verification: two bounded local diagnostic runs passed their assertions, with
real restore and ordinary walk/ClaudeTurn orchestration, and no provider access.
No repository Python, regression, protocol or payload changed, so no zone pytest
suite or build was required or run. Hypergraph export/check is the record gate.
No ADR/removal or ROADMAP implementation checkbox applies to this finding-only
unit. The unreconciled tail grows to two records; reconciliation stays separate.

Next: short item 2 may now address the demonstrated redundant agent write only.
Actual stored-conversation resumption, successful live repair, downstream
training/review and live output-label verification remain explicitly unproven;
the controller owns scheduling any future live attempt. This diagnosis does not
close that remaining evidence requirement or promote a Later criterion.
Dispatch closed: 1 unit — offline refusal diagnosis separates required restore metadata from redundant unchanged-session timestamp writes.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 103d7799a1a3a7bee6dd0179672f4b3a8a764409

## State Impact

- target: calm-peak-5247 — Offline refusal preserves accepted source, revision, digest, parameters and project history; restore legitimately refreshes attempt locators while unchanged session identity causes a redundant agent timestamp write; narrow CLI-only correction identified, not implemented
- target: crisp-reef-5607 — Real local restore plus controlled offline walk refusal diagnosed without provider access; successful live resumption, downstream repair and output-label evidence remain unproven
