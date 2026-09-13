---
run: ot5
machine: sb1x
started: 2026-09-12T15:13:35
ended: 2026-09-13T14:44:55+00:00
hours: 19.4
state: killed
iterations: 111
commits: 136
criteria_ticked: 0
criteria_closed: 0
criteria_total: 11
merged: no
branch: ouroboros/ot5
memory: hypergraph
actor: claude:claude-fable-5-1
---

# Run ot5

111 iterations in 19.4h on `sb1x`, killed (limit resets in 29 min: every harness is blocked (claude, codex): every harness in the chain is blocked). Branch `ouroboros/ot5`, not merged.

## The numbers

| | |
|---|---|
| iterations | 111 (changed 109, recorded 72) |
| commits | 136 — 283 files changed, 47157 insertions(+), 103 deletions(-) |
| criteria | **this run ticked 0**; 0 of 11 checked at the tip |
| reverts | 0 |
| verdicts | continue 101, done_rejected 1, looping 2, reject 5, stuck 2 |
| loop detector | no_frontier ×31 (longest streak 60) |
| roles | actor claude:claude-fable-5-1, critic codex:gpt-6-astra |
| usage | claude seven_day 7% -> 23% (+16 this run); claude seven_day_overage_included 45%; claude five_hour 100% -> 58% (-42 this run); codex seven_day 25% -> 100% (+75 this run) |

## What landed

- List a completed run whose policy was never stored as a problem with the store command; bounded drivers store through the CLI (ADR-327)
- Name a stored policy only when the store holds it; explain a failed run whose training finished (ADR-326)
- Kill and restart the engine during real Lark training; report a killed engine's exit status (ADR-325)
- docs(lark): publish iteration 107 status — ADR-324 record, CLI suite result, persistent identity check
- ouroboros #106: no record
- ouroboros #104: no record
- Fix retained video downloads with Unicode filenames (ADR-323)
- Fix bounded review disk accounting and preserve playback on detail arrival
- review: per-run disk use in the run detail and panel, shared references sized once (ADR-322)
- review: bound the run-list poll — telemetry summary per run, histories and verified checkpoints per run (ADR-321)
- test(review): prove Lark encoder-failure isolation during real GPU training
- test(review): prove Lark training survives persistent dashboard restart
- test(review): prove Lark video fault recovery and historical playback
- docs: publish Lark lifecycle review and current visual evidence
- Show retained policy origin and declared-source disagreements in review
- Record iteration 91: finish and record the ADR-317/318 containment arc (easy-field-3407)
- ouroboros #90: no record
- ouroboros #89: no record
- Resolve video lineage from retained identities, not run names (ADR-316)
- Complete Lark's D8 on the working copy: interrupted attempt, successful retry and its video on the persistent dashboard (ADR-315)
- Prove D7 on Lark: copy served on the persistent dashboard, edited with the original unavailable (ADR-314)
- ouroboros #84: no record
- Run Lark's first bounded real GPU training on the persistent dashboard
- ouroboros #81: Backfill: iteration 80 created Lark, moved the persistent dashboard and
- ouroboros #80: no record
- ... and 60 more

## Decisions the critic made

- #45 reject: The probe invalidates its own unchanged-project assertion by creating screenshots inside the inventoried directory; sandbox startup failure prevented independent verification.
- #56 reject: The iteration explicitly violated the one-training-run-at-a-time constraint; sandbox startup failure prevented independent inspection.
- #58 looping: The refusal is honestly recorded, but another preservation audit leaves the frontier unmoved for seven iterations; sandbox startup failure prevented independent verification.
- #65 looping: The diff adds probe machinery and backfills iteration 64, but supplies no completed revision comparison while the frontier has remained unmoved for fourteen iterations; sandbox failure prevented independent inspection.
- #68 stuck: Iteration 68 produced no diff, handoff or completed unit, so it needs a concrete lifecycle redirect.
- #86 done_rejected: The supplied change advances real lifecycle evidence, but reconciliation and whole-goal verification remain; sandbox startup failure prevented independent inspection.
- #88 reject: The new reader claims project containment but checks against individual run directories, allowing external directory symlinks; independent inspection was blocked by sandbox startup failure.
- #100 reject: The supplied implementation violates its bounded-operation claim and silently presents truncated directory-reference sizes as complete; independent inspection failed because the sandbox could not start.
- #101 reject: The reconcile promotes iteration 100’s rejected bounded-operation claims without evidence that its traversal and truncation defects were fixed; independent inspection failed at sandbox startup.
- #105 stuck: Iteration 105 produced no changes or handoff; repository inspection remains unavailable because sandbox startup failed.

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

The state graph reached "every criterion has evidence" at about iteration 50 and
nothing above `working` exists for the loop to reach: only the owner's checkbox
closes a criterion, and the exhaustion policy said "repeat the lifecycle", so the
next 60 iterations repeated it (Reed, then Wren, then Lark) while the loop detector
fired `no_frontier` for 60 iterations straight and rotated the actor four times for
nothing. Fifth run in a row with zero ticked, but the first where the evidence is
actually all there -- the charter needs a closing unit and a stop, not more rungs.

The Codex critic never inspected anything for its first 106 calls: the transcripts
hold zero tool calls, because Codex's default bubblewrap sandbox cannot start on
this Ubuntu 24.04 box (`kernel.apparmor_restrict_unprivileged_userns=1`). It graded
the actor's own account of each diff and wrote "sandbox startup failure prevented
independent verification" 93 times. Fixed by `features.use_legacy_landlock = true`
in `~/.codex/config.toml` (Landlock needs no user namespace; verified read works and
writes are blocked). Also: Codex's weekly window went 25% -> 100% as the critic and
is blocked until Sep 19; the run's last hours ran with no critic second opinion.

Evidence receipts under `docs/probes` grew by 26.5k lines (2.9 MB, single JSON
files up to 1,800 lines) against a charter line that asked for compact evidence.
Say a size, or say where dumps go instead. The Tailscale address is committed 27
times; the charter forbade machine paths and said nothing about addresses.
