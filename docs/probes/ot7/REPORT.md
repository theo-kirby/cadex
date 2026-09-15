# ot7 closing report — measured checks, agent outcomes not yet tried

Verified against source: 2026-09-15. [Cadex-new]

**The measured-fit tools are implemented; the agent's ability to repair or
create fitting mechanisms has not yet been tried.** All six product-agent
calls dispatched before the restart ended on the provider's session limit in
two to four seconds. Under the amended charter (ADR-355) **those six calls are
void**: no model saw a prompt, none spent a create, continuation or repair
slot, and none is a design result. F4–F7 remain open with every slot unspent.
This report is written forward from the restart; it claims no design outcome
and no critic acceptance of done.

## Amendment: the restart (ADR-355)

The 2026-09-14 version of this report declared the run exhausted and its
outcome terminal and incomplete. That handoff is **superseded**: a usage-limit
call is not an attempt, so nothing was exhausted. The runner now classifies
such calls itself, spends no slot on them, keeps their evidence and stops
further dispatch from that project ([runner README](runner/README.md#void-calls-adr-355)).
The six pre-restart calls, classified by that rule from their retained
transcripts, envelopes and stderr, are in [`attempts/void-calls.json`](attempts/void-calls.json):
none was cut off mid-turn, and the six transcript digests in the table
below match it. What each design has left:

| Design / criterion | Void calls (not attempts) | Attempts that reached the model | Create or repair prompt | Continuations unspent | Retry project |
|---|---|---|---|---|---|
| Heron repair / F4 | 3 | 0 | unspent | 3 of 3 | `ot7-heron-repair-b`, a fresh copy of the seed |
| Heron arm / F5 | 1 | 0 | unspent | 3 of 3 | `ot7-heron-b` |
| Robin balancer / F6 | 1 | 0 | unspent | 3 of 3 | `ot7-robin-b` |
| Plover biped / F7 | 1 | 0 | unspent | 3 of 3 | `ot7-plover-b` |

Retries send the same frozen prompts and are dispatched only while the
product agent's harness is available; no role stops or starts the run. The
sections below are the 2026-09-14 text, kept as the record of what happened.
Where they call a refusal an attempt, a slot consumed, or the run exhausted,
this amendment supersedes them.

> *Superseded on 2026-09-15:* "Terminal outcome: incomplete. This run
> exhausted its authorized experiments without establishing F4–F7 or
> successful completion. No further dispatch, collector-slot reset, repeated
> measurement or unrelated horizon work is authorized by this handoff."

## Design outcomes as recorded on 2026-09-14

The [prompt manifest](prompts/README.md) retains frozen prompts, hashes and ot6
provenance. Creates used `claude-fable-5`, exited 1, and consumed **zero of
three continuations**. No actor edited a design. The table's "attempts" and
"collector slot consumed" wording predates ADR-355; every row is a void call.

| Design / criterion | Prompt and attempts | Completed turns / continuations used | Fit failures per dispatch; final static / swept | Inventory / smoke | ot6 comparison |
|---|---|---|---|---|---|
| Heron repair / F4 | [Frozen repair](prompts/repair.prompt.txt); three fresh-session refusals, 4.090 s, 4.020 s and 4.171 s | 0; same single repair text dispatched three times, no follow-on prompt; collector slot consumed | First: before unavailable, restored after 21. Second and third: 15 before and after. Latest measurements: 15 static failures / sweep unavailable | Baseline has 15 components; no smoke requested or run | First accepted seed `7e9eff5c…` remains unrepaired; all three original defect classes persist |
| Heron arm / F5 | [Frozen create](prompts/heron.create.prompt.txt); one refusal, 1.917 s | 0 / 0 of 3 | Unavailable for sole dispatch; final static unavailable / sweep unavailable | Inventory unavailable; smoke command exit 1, 0.114 s, no simulation | ot6 accepted Heron after three measurement-fed corrections; ot7 produced no design |
| Robin balancer / F6 | [Frozen create](prompts/robin.create.prompt.txt); one refusal, 1.868 s | 0 / 0 of 3 | Unavailable for sole dispatch; final static unavailable / sweep unavailable | Inventory unavailable; smoke command exit 1, 0.114 s, no simulation | ot6 accepted Robin with two actor script corrections; ot7 produced no design |
| Plover biped / F7 | [Frozen create](prompts/plover.create.prompt.txt); one refusal, 3.273 s | 0 / 0 of 3 | Unavailable for sole dispatch; final static unavailable / sweep unavailable | Inventory unavailable; smoke command exit 1, 0.114 s, no simulation | No product-agent biped baseline in ot6: Finch was actor-authored; ot7 produced no design |

For all three creates, there is no accepted revision. Zero pairs and zero
failures in an empty report describe absent geometry. The smoke command could
not find `script.json`; no finite-state, collision or support check ran.
The collector's exit 0 means it retained the refusal, not that a design passed.
The historical provider reset message does not authorize retries.

### Void-call receipts and transcript identity

All six calls, including both pre-collector F4 refusals, are retained below.
Each is classified void in [`attempts/void-calls.json`](attempts/void-calls.json)
by the same digest.

| Dispatch | Receipt | Transcript SHA-256 | Causal record |
|---|---|---|---|
| F4 first | [Seed and refusal](retained/repair-refusal.json) | `7f4238888d0925e0fb3a5d2810843a3d01a7103a4155b3ea0ec0a7f07f4bd455` | [lucky-willow-8039](../../../.hypergraph/graph/record/lucky-willow-8039.md) |
| F4 iteration 19 | [Second refusal](retained/repair-refusal-iteration19.json) | `5c41384de5d7c3b129467c5a63b9d6980de88507f02cd31ce7a4a6fed09cf19e` | [keen-quill-2265](../../../.hypergraph/graph/record/keen-quill-2265.md) |
| F4 iteration 39 | [Collector refusal](retained/repair-refusal-iteration39.json) | `75cedbfd888448b5568bc17abf8bd7afe36b8905ffdf34869ad95cc28465323e` | [blue-slope-0916](../../../.hypergraph/graph/record/blue-slope-0916.md) |
| F5 iteration 32 | [Arm refusal](attempts/heron-refusal.json) | `813e77ee6c0183c17e4a54dec380f83524ae4183ce763f0bfe7aab3ee9c0dedb` | [quiet-dew-5243](../../../.hypergraph/graph/record/quiet-dew-5243.md) |
| F6 iteration 33 | [Balancer refusal](attempts/robin-refusal.json) | `01566753ac81f189b21cc565b300fc00f8d63e4cf63d985989d3663b6b490674` | [keen-chart-9070](../../../.hypergraph/graph/record/keen-chart-9070.md) |
| F7 iteration 35 | [Biped refusal](attempts/plover-refusal.json) | `b5b359ec0d0f5465cd1e8520701e3d7c17285881823ed028b03e13996434ea59` | [red-hawk-4600](../../../.hypergraph/graph/record/red-hawk-4600.md) |

The repair prompt SHA-256 is
`5d846901563ddef8b278a88f46e9ccfcd1a372f1e38b475743372c20cdcb4904`.
Create hashes are in their receipts.
The [attempt narrative](attempts/README.md) retains artifact verification and
per-call accounting.

## F4: what the seed measurements actually establish

The seed was copied verbatim from ot6 project commit `14bc75f…`, first accepted
revision `7e9eff5c4ff2640fbaaedd475f7394c0aeae54ce59f6effc067cffeaca8b4475`.
Its old accepted artifact directory was missing. Before the first refused
call, static and swept reads failed. Normal product restore during that call
recreated artifacts and changed the attempt pointer while preserving script,
revision and accepted digest. Its 21-failure report is a restored measurement,
not recovered historical artifact bytes; there is no invented before report.

The later count of **15** is a checker correction, not a design improvement:
ADR-353 removed six nominal-0.1 mm numerical false positives (two bearing gaps
and four servo/tab-screw gaps), using an absolute 1e-9 mm comparison allowance.
The second refused call measured 15 before and after with accepted identity
unchanged. Only ordinary restore metadata changed. The subsequent
[read-only baseline](retained/repair-measurement.json) independently collected
105 pairs and 15 inventory components in 0.164 s with unchanged script and
metadata. [Baseline record](../../../.hypergraph/graph/record/long-falcon-7461.md).

The baseline contains eight intersections, six below-clearance pairs and one
world-geometry failure. Servo/cheek overlap is about **248.20162986795 mm³**;
`comp_base` still carries the collision plane. Both horn/link gaps are about
**0.2 mm**. Those gaps do not fail the default 0.1 mm clearance minimum because
the seed declares no contact intent. Thus even a future zero-failure static
summary alone would not prove both attachments repaired.

The later [repair collector](runner/README.md) separately requires contact
within 0.001 mm and common volume within 1e-6 mm³ for both original horn/link
pairs. Missing or renamed attachment evidence cannot pass without a functional
identity justification. Its fixtures prove the assessment, not a real repair.
[Collector record](../../../.hypergraph/graph/record/blue-sky-2193.md),
[assessment record](../../../.hypergraph/graph/record/western-fox-7010.md).
### Iteration 39: frozen collector outcome

The critic requested the still-unused collector on the preserved seed.
It dispatched the frozen prompt once in a fresh `claude-fable-5` session and
received the same provider session-limit refusal (CLI exit 1) in **4.171 s**.
There were zero completed design turns and zero actor edits. This is the
**third F4 invocation**, including the earlier 4.090 s and 4.020 s refusals.
The exclusive `evidence/f4-repair/` directory is now written. *Amended
2026-09-15:* that directory is the void call's receipt, not a consumed slot;
the repair prompt is retried on a fresh seed copy, `ot7-heron-repair-b`.

The guarded before read took **0.164 s**, preserved the seed, and measured
**105 pairs / 15 failures**. The after read took **0.164 s** and retained
byte-identical clearance, fit, inventory and attachment-assessment reports.
Both horn contacts fail before and after: shoulder **0.19999999999999732 mm**,
elbow **0.19999999999993 mm**, each with **0 mm³** common volume. The world
plane and approximately 248.2 mm³ servo overlap also persist. Swept coverage
is unavailable; no F4 smoke was requested or run.

Script hash, accepted revision/digest/attempt and parameters stayed unchanged.
Normal product restore changed only `latest_candidate` and `updated_at` in
metadata. The [portable receipt](retained/repair-refusal-iteration39.json)
retains timings, both attachment assessments, the fresh session identity and
all artifact sizes and SHA-256 digests; each listed hash was verified against
the external project. The transcript contains a rate-limit event and no tool
use. Collector exit 0 means evidence collection completed, not repair success.
No successful after-repair report exists; F4 stays open.

## Implemented checks and evidence for F1–F9

| Criterion | What exists | Evidence and limits |
|---|---|---|
| F1 | Build replies include published static fit counts and every named failing pair; `clearance` inspect is exposed; instructions distinguish stdout claims from measurements | [Implementation](../../../.hypergraph/graph/record/happy-dawn-1960.md), [complete-list correction](../../../.hypergraph/graph/record/steady-quartz-9854.md), [real pager regression](../../../.hypergraph/graph/record/tidy-journey-9462.md), [CLI contract](../../CLI.md). A script printing “no overlap” returns its measured 100 mm³ intersection. Later-page failures and read errors are pinned |
| F2 | Contact and minimum-clearance declarations; overlaps, missed contact, insufficient clearance and world geometry are advisory findings | [Known-answer fixtures](FIT-INTENT.md), [record](../../../.hypergraph/graph/record/crisp-ember-0302.md), [numerical correction](../../../.hypergraph/graph/record/hidden-lodge-4550.md), [script contract](../../XSCRIPT.md). Solid world geometry needs explicit intent; grounding alone does not imply a floor |
| F3 | Published bounded exact-solid hinge and slider sweeps, agent inspection and `cadex clearance --sweep` | [Producer](../../../.hypergraph/graph/record/misty-spark-6372.md), [consumer](../../../.hypergraph/graph/record/green-river-3790.md), [slider fixtures](../../../.hypergraph/graph/record/curious-cedar-4881.md), [Finch product measurement](../../../.hypergraph/graph/record/kind-flint-2780.md), [sweep receipt](sweep/README.md). Discrete samples, unsupported or undeclared coverage explicitly incomplete; details below |
| F4 | Three void calls (ADR-355), zero attempts; before/after fit and both attachment assessments retained | [First void call](../../../.hypergraph/graph/record/lucky-willow-8039.md), [second](../../../.hypergraph/graph/record/keen-quill-2265.md), [collector](retained/repair-refusal-iteration39.json), [classification](attempts/void-calls.json). **Open: repair prompt and all continuations unspent** |
| F5 | One void arm create, zero attempts; frozen prompt, transcript and unavailable reports retained | [Record](../../../.hypergraph/graph/record/quiet-dew-5243.md), [receipt](attempts/heron-refusal.json). **Open: create prompt and all continuations unspent** |
| F6 | One void balancer create, zero attempts; equivalent retained evidence | [Record](../../../.hypergraph/graph/record/keen-chart-9070.md), [receipt](attempts/robin-refusal.json). **Open: create prompt and all continuations unspent** |
| F7 | New frozen biped prompt; one void create, zero attempts; equivalent retained evidence | [Record](../../../.hypergraph/graph/record/red-hawk-4600.md), [receipt](attempts/plover-refusal.json). **Open: create prompt and all continuations unspent** |
| F8 | One-command bounded smoke over accepted artifacts; passing and failing known-answer fixtures | [Record](../../../.hypergraph/graph/record/lean-fountain-9707.md), [receipt](f8-smoke.json). Implementation verified; F5–F7 have no executed simulation receipts |
| F9 | Green recorded suites and packaged gate; retained ot6 copies restore/reopen, all measurement differences explained | [Closure record](../../../.hypergraph/graph/record/narrow-valley-3317.md), [regression receipt](REGRESSION.md), [restore record](../../../.hypergraph/graph/record/still-raven-7629.md). Carried evidence, not a fresh run for this report |

### F3: measured motion and the absent predicted contact

The hinge fixture reports contact at 79° versus analytic 78.522°, within
its 1° step; the slider locates −2 mm contact within 0.75 mm. Bounds are
73 poses, 2,000 pairs and 90 seconds per joint, 180 seconds per assembly.
Unsupported or missing coverage is incomplete. Samples are not continuous proof.

A separate product-agent turn on a retained Finch copy added only the sweep
step declaration. It is F3 instrumentation evidence, not a fourth fresh design
or an F7 baseline. At 5°, the fourth hinge exhausted the assembly budget;
at 10°, all four completed in 104.4 s, respectively 35.7, 16.2, 36.2 and
16.3 s. Each completed joint had 406 pairs and solved-pose agreement.
Both knee shin/thigh pairs stayed **1.0 mm apart, 0 mm³ common volume, no
contact**. The charter's predicted contact was absent on this revision.
Forty pairs first contacted at a range's lower limit; none first contacted
inside a range. The agent claimed 44, incorrectly including four 0.05 mm
bearing gaps. This discrepancy is retained as evidence against treating prose
as measurement. See the [product sweep receipt](sweep/README.md).

### F8: smoke implementation is not a design pass

`cadex smoke` preserves accepted identity and checks finite state, sampled
exact BREPs and proxy floor support under a 300-second deadline. The grounded
fixture passed 101 poses; a falling arm overlapped by **1,463.7845106574737 mm³
at 1.64 s** despite passing proxy checks; overlapping boxes measured 400 mm³.
Unavailable BREP evidence cannot pass. No fresh ot7 design ran a simulation.

## Regression and ot6 comparison

The [regression receipt](REGRESSION.md) carries engine **2,142 passed / 53
skipped**, successful build and stage, and packaged lifecycle **18 passed**.
Its CLI checkpoint was **693 passed / 1 skipped**. Later collector work ran
**718 passed / 1 skipped** in 528.12 s; the final assertion was covered by the
subsequent **33 passed** focused runner suite, rather than that already-started
full suite. [Validation record](../../../.hypergraph/graph/record/western-fox-7010.md).
No engine, CLI or packaged gate was rerun for this evidence/report unit;
skips remain unexecuted evidence.

All six retained restore/reopen checks preserved accepted identity and all
787 pair measurements. Final retained revisions have **44 Finch, 39 Robin and
20 Heron static failures**: ot6 explicitly allowed certain screw engagements,
and the old scripts lack contact declarations for seatings and small gaps.
The two final-Heron nominal-0.1 mm flags were removed by the same numerical
correction described above. These are distinct from the six flags removed
from F4's earlier seed. The complete failing sets and their explanations are
in [the retained comparison](retained/README.md) and
[restore receipt](retained/restore-open.json). Legacy sweeps remain unavailable;
compatibility does not imply fit passes.

The [ot6 report](../ot6/REPORT.md) records 55/55 custom Heron fit rules,
84/84 Robin rules and 87 Finch rules. Those custom checks and their explicit
engagement allowances differ from the new product checker. Heron's corrections
used hand-written defect feedback; Robin needed actor edits; Finch had no
model turn. ot7 supplies no new accepted mechanism against which to measure
an improvement in autonomous design. ot6 training results do not substitute
for this run's smoke receipts; no policy training occurred in ot7.

## F10 and what remains open

F1–F3 and F8 have fixture-verified checks within the limits above; F9 has
recorded regression evidence. **F4–F7 remain open and untried**: void calls
establish no geometric design outcome, and they spent nothing.

F10's requirement that the critic accepted done is **unmet**. This report
makes no done claim. What remains is the agent half of the charter, in this
order: the seeded repair on a fresh copy of the seed (F4), then the arm,
balancer and biped creates in fresh suffixed projects (F5–F7), each through
its continuations as its fit report requires, each with its smoke rollout,
and each dispatched only while the product agent's harness is available. A
design that does not reach zero failing checks within its three continuations
is a valid measured result and will be reported as such. This report is then
rewritten with one row per design.

> *Superseded on 2026-09-15:* "All scheduled collector slots are consumed.
> The run's successful-completion prerequisites are not established by the
> existing evidence. ... This run returns an incomplete outcome." The
> reconciliation the earlier handoff deferred was folded by the restart
> (`4505e21f`); the outcome is open, not terminal.
