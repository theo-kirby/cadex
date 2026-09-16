# ot7 closing report — measured checks, agent outcomes not yet tried

Verified against source: 2026-09-16. [Cadex-new]

**The measured-fit tools are implemented, and the agent has now completed
all four of F4's turns from measurements alone on `ot7-heron-repair-d`: the
repair prompt in iteration 48 and the three frozen continuations in
iterations 51, 52 and 53. F4 is exhausted. The first two accepted revisions
the product's checker passes at zero failing pairs, static and swept; the
first continuation restored the two servos to untouched catalog bodies and
removed the bench slab, so every purchased part is catalogued again and no
world geometry remains. The second and third continuations each re-read
every measurement, found none failing, re-accepted the unchanged script and
recorded a decision saying so; the third also wrote the `NOTE design_specs:`
lines its prompt asked for, counting 105 rest-pose and 210 swept checks
passed and 0 failed. The collector's attachment assessment still fails on
both horn-to-link pairs at 0.2 mm, which the agent's own fit-intent ledger
lists among four declared clearances that pass** (see [Iteration 48](#iteration-48-the-repair-turn-that-completed),
[Iteration 51](#iteration-51-the-first-continuation-completed),
[Iteration 52](#iteration-52-the-window-read-by-the-runner-then-continue-2-completed-adr-358) and
[Iteration 53](#iteration-53-the-last-continuation-completed-and-f4-exhausted)).
The two earlier calls that reached a model were an interrupted execution
(iteration 44) and a void call (iteration 48 on `ot7-heron-repair-c`). All six
product-agent calls dispatched before the restart ended on the provider's
session limit in two to four seconds. Under the amended charter (ADR-355) **those six calls are
void**: no model saw a prompt, none spent a create, continuation or repair
slot, and none is a design result. F5–F7 remain open with every slot unspent;
F4 has spent its repair prompt and all three continuations on
`ot7-heron-repair-d` (ADR-357, [Iteration 49](#iteration-49-the-slot-totals-corrected-adr-357)),
and its measured result is two of three ot6 defects resolved.
**F5 has had four completed turns on `ot7-heron-c` and is exhausted**: iteration 57
dispatched the frozen arm create prompt at 5 % of the window, at effort
`medium` (ADR-359), and the turn ended on its own in 1,530.4 s with an
accepted two-DoF arm whose measured static fit **failed 7 of 120 checks**:
six screw intersections the agent called thread engagement, and the bench it
added as a world-marked slab (see
[Iteration 57](#iteration-57-the-arm-create-turn-completed)). Iteration 59
resumed it with the frozen `continue-1` after the reset, and that turn ended
on its own in 610.6 s: static fit **1 of 120 failing** (the bench, still in
the design as world geometry), the sweep **complete on both joints with zero
overlap** after the agent declared a step and narrowed both ranges, servos
and horns **still uncatalogued**, and a passing smoke (see
[Iteration 59](#iteration-59-the-first-continuation-completed)). Iteration 66
resumed it with the frozen `continue-2` after the 12:20 UTC reset, and that
turn ended on its own in 482.4 s: the agent deleted the bench from the model,
static fit **0 of 105 failing**, no world geometry, the sweep **complete on
both joints with zero overlap**, smoke passing, and servos and horns **still
uncatalogued** (see
[Iteration 66](#iteration-66-the-second-continuation-completed)). Iteration 72
resumed it with the frozen `continue-3` after the owner refreshed the
account (ADR-361), and that turn ended on its own in 142.9 s: the agent
read the whole report, found no failing check, changed nothing,
re-accepted the unchanged script at the same revision, and the runner's own
smoke passed; servos and horns **still uncatalogued** (see
[Iteration 72](#iteration-72-the-last-continuation-completed-and-f5-exhausted)).
The create slot and all three continuations are spent: **F5 is exhausted
with its measured result**, every count of its bar met except catalog
hardware for every purchased part. Iteration 55's
call on `ot7-heron-b` was interrupted at the 30-minute bound and spent
nothing (see [Iteration 55](#iteration-55-the-arm-create-call-interrupted-at-the-bound)).
This report is written forward from the restart; F5's design outcome is
the measured one above, F6 and F7 have none yet, and there is no critic
acceptance of done. **Both are blocked on a provider refusal**:
`claude-fable-5` was refused on this account at the organisation level when
last probed, no clock dates the end of that, and the run's configured
stop falls 33 h 34 m before the refused window's scheduled reset. Unless an
unrefused probe arrives first, both end unattempted with all eight slots
unspent, which is not exhaustion — see
[The gate is shut now, and no clock says when it opens](#the-gate-is-shut-now-and-no-clock-says-when-it-opens).

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
| Heron repair / F4 | 4: three pre-restart, and iteration 48 on `ot7-heron-repair-c` (cut off by the five-hour limit after 6 reads, [receipt](retained/repair-void-c.json)); and 1 **interrupted** call apart from them: iteration 44 on `ot7-heron-repair-b`, killed at the runner's 30-minute bound (decision #44: not a turn, no slot) | 4, all on `ot7-heron-repair-d`: iteration 48, the repair prompt, completed in 1,461.9 s with six accepted revisions ([receipt](retained/repair-completed-d.json)); iteration 51, `continue-1`, completed in 738.5 s with two accepted revisions ([receipt](retained/repair-continue-1-d.json)); iteration 52, `continue-2`, completed in 128.7 s with no edit and the unchanged script re-accepted ([receipt](retained/repair-continue-2-d.json)); iteration 53, `continue-3`, completed in 104.9 s with no edit and the unchanged script re-accepted ([receipt](retained/repair-continue-3-d.json)) | spent: the repair prompt, completed on `ot7-heron-repair-d` | 0 of 3 (all three spent; ADR-357: the repair prompt is the first prompt, not a continuation) | none: F4 is exhausted and its measured result stands |
| Heron arm / F5 | 1 (pre-restart); and 1 **interrupted** call apart from it: iteration 55 on `ot7-heron-b`, killed at the runner's 30-minute bound after 68 model messages with no design written ([receipt](retained/heron-interrupted-b.json)) | 4, all on `ot7-heron-c`: iteration 57, the create prompt, completed in 1,530.4 s with three accepted design revisions, static fit 7 of 120 failing at the last ([receipt](retained/heron-create-c.json)); iteration 59, `continue-1`, completed in 610.6 s with two accepted revisions, static fit 1 of 120 failing (the bench as world geometry), the sweep complete with zero overlap, smoke passing ([receipt](retained/heron-continue-1-c.json)); iteration 66, `continue-2`, completed in 482.4 s with two accepted revisions, static fit 0 of 105 failing, no world geometry, the sweep complete with zero overlap, smoke passing, servos and horns still uncatalogued ([receipt](retained/heron-continue-2-c.json)); iteration 72, `continue-3`, completed in 142.9 s with no edit and the unchanged script re-accepted, static fit 0 of 105 failing, the sweep complete with zero overlap, the runner's smoke passing, servos and horns still uncatalogued ([receipt](retained/heron-continue-3-c.json)) | spent: the create prompt, completed on `ot7-heron-c` | 0 of 3 (all three spent) | none: F5 is exhausted and its measured result stands |
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

## Iteration 44: the first call that reached the model

With Claude available (a one-word probe with the runner's model name
answered in 5.4 s), the frozen repair prompt was dispatched once through the
runner on `ot7-heron-repair-b`, a fresh copy of the seed with the earlier
evidence, session pointer and CLI lock left out. The runner validated the
seed identity, and its guarded before-read reproduced the baseline exactly:
**105 pairs, 15 failures**, both horn attachments 0.2 mm short of contact,
the servo/cheek overlap and the collision plane on `comp_base`. The
[receipt](retained/repair-timeout-b.json) carries every number and digest.

The model saw the prompt and worked for the whole bound. Its tool calls, in
order: the clearance scope four times (the summary, then the pairs in three
pages of 50), the script, the authoring contract, seven pages of the assembly
and library API, the script source in two pages, then the library and part
exports. After the fifteenth read, at 05:12:25 UTC, it produced one message
of **64,000 output tokens, 63,999 of them thinking**, that ended on the
provider's output cap at 05:29:03 with no text and no tool call. It made two
more reads and was generating again when the runner killed the process group
at **1,800.0 s**. It never called submit. **Zero design edits, zero
revisions, zero acceptances**: the script hash and accepted revision are
byte-identical before and after, the after-read measures the same 15
failures, and only the ordinary restore fields (`latest_candidate`,
`updated_at`) changed in the metadata.

Two evidence limits, both the runner's. The CLI envelope is empty and the
runner's `transcript.jsonl` is missing, because the collector writes the
stream only after the turn returns and the kill came first. The provider
stream was recovered unmodified from the harness's own session store for the
project directory (698,175 bytes, SHA-256 `56e81011…`, retained under
`evidence/f4-repair/recovered/`), and the receipt's per-message stop reasons,
token counts and tool sequence come from it. Its usage total is 82,904 output
tokens over 16 API messages.

What this is and is not. It is the first measured product-agent result of the
run: given measured fit and the repair prompt, the agent read the right
things first and then spent 16.5 of its 30 minutes inside one thinking burst
that produced nothing. It is not a void call: no usage, session or credit
limit appeared anywhere in the stream. The collector of that day reported
the repair slot spent under its timeout rule. **Decision #44** (the critic,
iteration 44) ruled instead that the call is an **interrupted execution**:
it did not end on its own, so it is not a turn, it consumed no frozen-prompt
slot, and it is recorded apart from provider-limit void calls. The receipt's
`slot_consumed`, `slots_spent` and `continuations_used` values stay as the
collector's historical output, marked by its `ruling` field; the repair
prompt and all three continuations are unspent. No retry was dispatched in
that iteration.

## Iteration 46: decision #44 carried into the collector and the CLI

Two collector defects the interrupted call exposed are fixed (ADR-356). The
collector now writes the provider stream frame by frame as it arrives, so a
kill loses nothing received, and it applies decision #44 itself: a call
whose child exited on the runner's bound or never launched is `interrupted`,
returns its slot, is counted in `interrupted_calls` apart from `void_calls`
and `slots_spent`, keeps its measurement, and names the fresh retry project.
Fixtures pin a kill on a create, on a continuation after two completed turns,
and on the repair, plus the frame-by-frame capture. The CLI now launches
every turn at an explicit effort level and passes the harness its documented
per-message output cap of 32,000 tokens, which caps thinking and text
together; the harness documents that on Fable models its fixed thinking
budget has no effect, so this is the only hard per-message bound available.
No frozen prompt changed. The next design turn is the same repair prompt on
`ot7-heron-repair-c`, dispatched only while the product agent is available.

## Iteration 48: the repair turn that completed

Two calls, both on fresh copies of the seed validated by the runner, both
under the corrected collector (ADR-356), both with the unchanged frozen repair
prompt (`5d846901…`, 830 bytes). No actor edited any design.

**`ot7-heron-repair-c` is void** ([receipt](retained/repair-void-c.json)).
Dispatched at 06:07 UTC into a five-hour window the stream's first
`rate_limit_event` frame already showed at 95 % utilization, the model made
six reads in 80 s (the clearance summary, the script, three pages of pairs,
the script source) and was cut off mid-turn by the session limit, 429, at
101 %. The collector classified it void with no slot spent; the before and
after reads both show the seed's 15 failures and the script and accepted
revision unchanged. The stream was written frame by frame, so this void call
is the first whose transcript (216,946 bytes) survived in the runner's own
capture. The probe that preceded it answered "ok", so an answering probe is
not evidence of room in the window; the first `rate_limit_event` frame is.

**`ot7-heron-repair-d` completed** ([receipt](retained/repair-completed-d.json)).
Dispatched at 10:24:40 UTC, four minutes after the window reset (first frame
at 8 % utilization), the turn ended on its own after **1,461.9 s** with 39
model messages and 46 tool calls: 35 inspects, 9 script edits, one
`describe_api`, one rebuild. Six edits were accepted and three rejected (two
malformed replacement calls and one MuJoCo refusal of a collision plane on a
non-static body). The longest silent thinking gap was 254 s; usage was
80,451 output tokens (65,887 thinking) and 5.45 M cache-read input tokens,
and the five-hour window went from 8 % to 57 % in this one turn. The turn
read clearance first and after every accepted edit, then the script, the
API, the outputs and, at the end, the inventory. The accepted revision
sequence by failing count is 15 → 2 → 1 → 2 → 1 → 0 → 0, ending at
`252e73b5…`, script `27680dc0…`, digest reproduced on rebuild.

What the after-read measures, independently of the agent's printed claims:

- **Static fit: pass, 120 pairs, 0 failing** (from 105 pairs and 15). The
  eight intersections and six below-clearance pairs are gone; the world
  geometry row is gone.
- **Swept fit: complete** at 5°, shoulder [−90°, +65°] in 32 samples (20.9 s)
  and elbow [−100°, +25°] in 26 samples (10.5 s), 31.3 s in all, solved-pose
  agreement true on both joints, maximum common volume 0 on every pair at
  every sample; the 19 pairs at 0 mm are all declared contacts.
- **The collector's attachment assessment: fail.** `comp_horn_shoulder` to
  `comp_upper_arm` is still 0.19999999999999732 mm and `comp_horn_elbow` to
  `comp_forearm` still 0.19999999999993 mm, exactly the seed's values. The
  agent declared both pairs as *clearance, minimum 0.05 mm* rather than as
  contact, so the product's checker passes them.
- **Inventory:** catalog counts unchanged (2 MR128 bearings, 2 M2×16 and 4
  M2×6 screws, 2 single-arm horns), but `servo_shoulder` and `servo_elbow`
  are now `uncatalogued_sources`: the agent cut a spline screw bore into each
  catalog servo body so the centre screw's 9.42 mm³ overlap measures as
  contact.

How the three ot6 defects fared, in the agent's own five recorded decisions
(ADR-006 to ADR-010 in the project's `DECISIONS.md`):

1. **The floor plane** is gone from the base. In its place the agent added a
   grounded 400 × 400 × 8 mm `bench` slab as an ordinary component with a
   declared base contact, after MuJoCo refused the plane on a non-static
   body and the checker reported it as world geometry. The checker now
   measures every bench pair. The design carries a bench.
2. **The buried servo tab** (248.2 mm³ on each joint) is resolved by a form
   pocket in each cheek; the tab pairs now measure contact at zero volume.
   The screw overlaps (4.07 mm³ per tab screw, 9.42 mm³ per centre screw)
   are resolved by cutting the holes at shank diameter, which the agent
   describes as modelling the thread-formed state.
3. **The horn 0.2 mm from its link** is **not** closed. Neither the seed nor
   the product's report ever named it: 0.2 mm exceeds the 0.1 mm default
   minimum, so it was a clear pair on every page the agent read, and the
   agent chose to declare it a running clearance. The only reader that flags
   it is the collector's attachment assessment, which carries ot6's knowledge
   that a horn attaches to its link.

Two further changes the prompt did not ask for: the joint ranges are narrowed
from symmetric ±90° and ±100° to the swept first contacts less 5° (shoulder
+65°, elbow +25°), mirrored into the servo command limits; and `sweep_step_degrees=5.0`
is declared so the swept report publishes. Both are the agent's design
decisions and are recorded as such.

**Against F4's bar.** "Accepts with zero failing fit checks": met, on the
product's static and swept checks. "Resolves all three defects": not met;
two are resolved and the third is declared away. This is F4's measured
result after its first prompt; the three frozen continuations remain unspent
(ADR-357, [iteration 49](#iteration-49-the-slot-totals-corrected-adr-357)).
It is a product finding as much as an agent one: fit intent (F2) is only as good as
what a script declares, and an attachment nobody declared is invisible to
measurements alone. No smoke rollout ran; the repair mode does not request
one.

## Iteration 49: the slot totals corrected (ADR-357)

The iteration 48 text above and its receipt said the repair mode carried one
frozen prompt and that F4's slot was spent. The slot table said the same in
one column and "3 of 3" for every other design in the next. The charter's
exhaustion policy is the rule: a design is exhausted only after "its create
or repair prompt and all three continuations have reached the model", so
the repair prompt is F4's first prompt, not its only one, and the critic of
iteration 48 ruled the same. **F4 stands at one completed turn, its repair
prompt spent, zero continuations used and three unspent**; the receipt
[`repair-completed-d.json`](retained/repair-completed-d.json) keeps its
`status: exhausted` and `continuations_used: 1` as the collector's output
under the superseded rule, marked by a `ruling` field, the way the
iteration 44 receipt carries decision #44. The
[runner](runner/README.md#resuming-after-a-completed-turn-iteration-49-adr-357)
now carries the four-prompt repair schedule, dispatches one turn per
invocation for a repair, and resumes the next continuation on the same
project without replaying any earlier turn; fixtures pin it. No prompt byte
changed and no design was edited. The completed experiment on
`ot7-heron-repair-d` stands as recorded, and its next turn is
`continue-1.prompt.txt` on that project, dispatched only when the first
`rate_limit_event` frame shows room: at dispatch time this iteration the
five-hour window stood at 74 % with the reset at 15:20 UTC, and one turn of
the observed size does not fit, so no continuation was sent.

## Iteration 51: the first continuation completed

`continue-1.prompt.txt` (756 bytes, digest unchanged) was resumed on
`ot7-heron-repair-d` into the agent's own session at 15:22 UTC, two minutes
after the five-hour window reset (first `rate_limit_event` frame at 8 %),
through `run.py resume`. No actor edited any design. The turn ended on its
own after **738.5 s** with 43 model messages and 20 tool calls: 14 inspects,
4 `edit_script`, 2 `write_script`
([receipt](retained/repair-continue-1-d.json)). It read the clearance
summary first, then the script and its source, edited, then read the
inventory and every page of both joints' swept pairs before its closing
text. Four edit calls were rejected: one broke the script with an undefined
name, one was a malformed replacement call, and two, an edit and a whole
write, were refused by the engine because an output cannot be retired while
its component still links to it. Two were accepted, `a95405bb…` then
`f03054d6…` (script `59ff7c95…`, 578 → 557 lines, 75 diff lines), each
measuring 0 failing of 105 pairs. Usage was 56,472 output tokens (14,196
thinking) and 4.46 M cache-read input tokens; the five-hour window went from
8 % to 63 % in this one turn. The runner paused with `continue-2` next.

What the after-read measures, independently of the agent's printed claims:

- **Static fit: pass, 105 pairs, 0 failing** (from 120 pairs and 0). The
  15 bench pairs are gone with the bench; the 16 pairs at 0 mm are all
  declared contacts; `world_geometry` is empty.
- **Swept fit: complete** at 5°, shoulder [−90°, +65°] in 32 samples
  (20.3 s) and elbow [−100°, +25°] in 26 samples (10.3 s), 30.6 s in all,
  solved-pose agreement true on both joints, maximum common volume 0 and no
  first contact on any pair at any sample; 18 pairs per joint at 0 mm, all
  declared contacts.
- **Inventory: every purchased part is a catalog part again.** `servo/mg90s`
  ×2, `servo_horn/mg90s-single_arm` ×2, `bearing/mr128` ×2, `bolt/m2x6` ×4,
  `bolt/m2x16` ×2; `uncatalogued_sources` is exactly the three printed parts
  (base, upper arm, forearm); 15 components, from 16.
- **The collector's attachment assessment: fail**, unchanged.
  `comp_horn_shoulder` to `comp_upper_arm` is 0.19999999999999732 mm and
  `comp_horn_elbow` to `comp_forearm` 0.19999999999993 mm, the seed's exact
  values, still declared as 0.05 mm clearances.

The agent's three recorded decisions (ADR-011 to ADR-013 in the project's
`DECISIONS.md`) resolve the two design-contract departures the repair turn
had introduced, both of which it found in the inventory read rather than in
a failing fit row: the servos are placed as untouched `lib.servo` bodies
again, and the centre screws are retracted so the M2×16 tip sits on the
spline top face (measured contact, 0 mm, 0 volume, a declared pair) instead
of a bore cut into a purchased body; the bench solid, component, body and
floor collision are removed over two accepted revisions, the task's tip-floor
termination stands in for the floor, and the +75° first contact measured in
`252e73b5…` is kept out of reach by the +65° shoulder clamp.

**Against F4's bar.** "Accepts with zero failing fit checks": met again on the
product's static and swept checks. "Resolves all three defects": still not
met; the horn gap remains declared as clearance, and nothing the agent reads
names it. This turn fixed what its own tools reported, the inventory contract
and the world geometry, and nothing they did not. Two continuations remain
unspent and follow through `resume`, one per window.

## Iteration 52: the window read by the runner, then continue-2 completed (ADR-358)

This iteration ran twice. Its first attempt, while the five-hour window read
**84 %** at 15:45 UTC and **93 %** (`allowed_warning`) at 15:49 UTC against
a bound of 45 % from the two measured turns, dispatched nothing and moved the
dispatch decision into the collector: `run.py` now probes the window before
every frozen prompt, records the reading in the receipt (`window_readings`,
and `window` on each dispatched row), and without room writes
`status: paused` with a `deferred` block before any slot is persisted, so the
same prompt resumes after the reset. `run.py window` only reads. Fixtures pin
the real 84 % frame as no room and 8 % as room, the deferred create and
repair, the schedule that pauses mid-way, and the hermetic default
([runner README](runner/README.md#reading-the-window-before-every-prompt-iteration-52-adr-358)).
That attempt was itself cut off by the actor's session limit before it could
commit; the second attempt, after the 20:20 UTC reset, verified and committed
it (68 runner tests passing) and then used it.

`continue-2.prompt.txt` (611 bytes, digest unchanged) was resumed on
`ot7-heron-repair-d` through `run.py resume` at 20:23 UTC. The runner's own
probe read **6 %** (`allowed`, reset 01:20 UTC) and dispatched; the turn's
first `rate_limit_event` frame read 7 %. No actor edited any design. The turn
ended on its own after **128.7 s** with 17 model messages and 8 tool calls:
7 `inspect` reads of the clearance scope (the summary, all 105 pairs over
three pages, the sweep and each joint's swept table) and 1 `rebuild`, which
reproduced the accepted digest `bf167b32…` bit for bit
([receipt](retained/repair-continue-2-d.json)). It made **no edit and no
write**: the frozen prompt states that the report still names failing
checks, the agent wrote down the measured value at every tight pair, found
`failing_count 0` at the rest pose and `maximum_common_volume 0.0` on all
210 swept rows, re-ran the unchanged script through acceptance (same
revision `f03054d6…`, same digest), and recorded ADR-014 in the project:
"the claim of remaining failures is overruled by the engine's published
measurements". Usage was 3,486 output tokens (1,563 thinking) and 2.40 M
cache-read input tokens; the five-hour window went from 7 % to 28 %, the
actor's own session sharing it. The runner paused with `continue-3` next.

What the after-read measures, unchanged from iteration 51 because the script
is unchanged (`59ff7c95…`, 557 lines): static fit **pass, 105 pairs, 0
failing**, 16 pairs at 0 mm all declared contacts, `world_geometry` empty;
swept fit **complete** at 5° on both joints (31.0 s in all), zero common
volume and no first contact beyond the declared contacts present from each
lower limit; inventory with all five catalog families at full count and only
the three printed parts uncatalogued; the collector's attachment assessment
**fail**, `comp_horn_shoulder`/`comp_upper_arm` and `comp_horn_elbow`/
`comp_forearm` at 0.2 mm, declared as 0.05 mm clearances.

**Against F4's bar.** "Accepts with zero failing fit checks": met a third
time on the product's static and swept checks. "Resolves all three defects":
still not met, two of three. This turn is the run's clearest measurement of
the charter's premise: with every product check passing, a continuation
prompt that asserts failures without naming one does not move the agent,
which trusts the measurements over the prompt, exactly as its instructions
say to. The horn gap stays a declared clearance because nothing the agent
reads calls it anything else. One continuation remains unspent.

## Iteration 53: the last continuation completed, and F4 exhausted

`continue-3.prompt.txt` (732 bytes, digest unchanged) was resumed on
`ot7-heron-repair-d` through `run.py resume` at 20:34 UTC. The runner's own
probe read **44 %** (`allowed`, reset 01:20 UTC), one point under the 45 %
bound, and dispatched; the turn's first `rate_limit_event` frame read 46 %.
No actor edited any design. The turn ended on its own after **104.9 s** with
10 model messages and 4 tool calls: 1 `inspect` of the clearance scope's
summary, 1 `rebuild` that reproduced the accepted digest `bf167b32…` bit for
bit, and 2 `inspect` reads of the two joints' swept tables
([receipt](retained/repair-continue-3-d.json)). It made **no edit and no
write**: the prompt, which calls itself the last correction turn and asks
for every failing check to be resolved, found none named, so the agent
re-ran the unchanged script through acceptance (same revision `f03054d6…`,
same digest) and wrote the documentation the prompt asked for as reply
lines: one `DECISION:` line, captured by the CLI as the project's ADR-015
("Final correction turn made no geometry change"), and two
`NOTE design_specs:` lines, captured into the project's `docs/design-specs.md`,
counting **105 rest-pose checks passed, 0 failed** and **210 swept pair
checks passed, 0 failed**. The second NOTE is the agent's own fit-intent
ledger: 18 declared contacts at 0.0 mm at rest and at every sample, and
"4 declared ≥0.05 mm clearances measure 0.0999999–0.2 mm (stub-in-bearing-bore
both joints, horn pockets both joints)". Usage was 2,418 output tokens (855
thinking) and 1.69 M cache-read input tokens; the five-hour window went from
46 % to 48 %. The runner wrote `status: exhausted` with every slot spent:
`slots_spent: 4`, `continuations_used: 3`, `next_prompt: null`.

What the after-read measures, unchanged from iterations 51 and 52 because
the script is unchanged (`59ff7c95…`, 557 lines): static fit **pass, 105
pairs, 0 failing**, 16 pairs at 0 mm all declared contacts, `world_geometry`
empty; swept fit **complete** at 5° on both joints (30.5 s in all), zero
common volume and no first contact beyond the 18 declared contacts present
from each lower limit; inventory with all five catalog families at full
count and only the three printed parts uncatalogued; the collector's
attachment assessment **fail**, `comp_horn_shoulder`/`comp_upper_arm` and
`comp_horn_elbow`/`comp_forearm` at 0.2 mm, declared as 0.05 mm clearances.

**Against F4's bar, now final.** "Accepts with zero failing fit checks":
met on every one of the four turns, on the product's static and swept
checks. "Resolves all three defects": not met, two of three. The floor
plane is gone and the buried servo tab is out of the cheek; the horn is
0.2 mm from its link, exactly where ot6's probe found it, and every report
the agent reads calls that gap a passing declared clearance, which the
agent's own ledger now says in as many words. Two continuations that named
no failure left the design unchanged, and the last one documented the
outcome as asked. That is F4's measured result: the product's checks reach
the agent and it uses them, and a defect the checks do not name is not
repaired. No slot remains; a further prompt would be a new attempt under a
changed prompt, which the charter forbids for this design.

## Iteration 55: the arm create call interrupted at the bound

The first F5 call that reached a model. `heron.create.prompt.txt` (9,648
bytes, digest unchanged) was dispatched on the fresh, empty project
`ot7-heron-b` through `run.py heron … --turns 1` at 21:28 UTC. The runner's
own probe read **13 %** (`allowed`, reset 02:20 UTC), well under the 45 %
bound, and dispatched; the turn's first `rate_limit_event` frame read 13 %,
its last 51 %. No actor edited any design. **The turn did not end on its
own**: the runner killed it at 1,800.0 s, and classified it `interrupted`
under ADR-356 with `slot_consumed: false`, `slots_spent: 0`,
`continuations_used: 0` and the retry named `ot7-heron-c`
([receipt](retained/heron-interrupted-b.json)). The stream was captured frame
by frame, 68 model messages, 1,023,332 bytes.

Where the thirty minutes went, from the stream's own timestamps:

- **21:28:02–21:31:53, reading (49 tool calls).** The agent's first call,
  `describe_api`, returned 163,200 characters, which the harness refused as
  over its tool-result cap and wrote to a file instead. The agent tried
  `Grep`, `Read`, `Bash` and `Agent` on that file; all four are disabled in
  the product-agent session. It then paged the same contract through 44
  `inspect scope=api` reads: the catalog families, the assembly exports one
  by one, the part exports one by one.
- **21:29:24–21:31:53, three probe scripts.** The first was rejected
  (`import json`, which xscript forbids). The second and third were accepted
  as probes of the catalog geometry: the servo body, a flange cut from it, and
  the horn, published as three `part` outputs with no assembly, so the
  product's fit, sweep and inventory reads are unavailable by construction.
  This is the accepted state the project was left in: revision `544ea74e…`,
  twelve lines, zero components.
- **21:31:53–21:56:46, thinking (1 tool call).** Three consecutive
  thinking-only messages, each of about 31,950 estimated thinking tokens over
  479, 494 and 472 s, each ending on the 32,000-token output cap that
  ADR-356 set, each followed by the harness's own auto-resume text ("Output
  token limit hit. Resume directly…"). Between the second and third the
  agent made one read (the horn's face table). The stream carries no
  thinking text, only the harness's token estimates, so what the model was
  working out is not retained. A fourth such message began at 21:56:46 and
  the bound fell at 21:58:02.

**What this measures.** Under the ADR-356 settings (effort `high`, output cap
32,000 tokens) this create prompt did not fit the bound: the cap that turned
iteration 44's single 64,000-token thought into a kill at 16.5 minutes turned
this one into three 8-minute thoughts and a kill at 30. The turn cost 38
points of the five-hour window (13 % to 51 %) and produced no assembly,
so there is no fit report, and nothing here is a design result for or
against F5. The design's create prompt and all three continuations remain
unspent. The window read 67 % after the kill, so the retry on `ot7-heron-c`
waits for the 02:20 UTC reset; whether it should be dispatched under the
same effort and cap, or under a lower effort level (the CLI's documented
`CADEX_EFFORT` control, no prompt byte changed), is the decision the next
unit has to make and record before it spends the window again.

## Iteration 57: the arm create turn completed

The first F5 turn that ended on its own. `heron.create.prompt.txt` (9,648
bytes, digest `bcda5af5…`, unchanged) was dispatched on the fresh, empty
project `ot7-heron-c` through `run.py heron … --turns 1` at 02:22:53 UTC,
two minutes after the reset, at effort `medium` with the 32,000-token cap and
the 30-minute bound unchanged (ADR-359). The runner's probe read **5 %** and
dispatched; the stream's first `rate_limit_event` read 5 %, its last 62 %,
and the probe after the measurement read 64 %. No actor edited any design.
**The turn completed** in 1,530.4 s (exit 0, 123 model messages, 35 thinking
blocks, no output-cap hit, 82 tool calls), the slot is spent, and the runner
left the attempt `paused` with `continue-1` next and all three continuations
unspent ([receipt](retained/heron-create-c.json), 1,492,517-byte stream,
digest `4bd8071a…`, in the project).

Where the 25.5 minutes went, from the stream's timestamps:

- **02:22:56–02:25:36, reading (44 calls).** The first call, `describe_api`,
  returned the ADR-359 view, **82,523 characters, and the harness refused
  it** as over its tool-result cap, writing it to a file the agent has no
  tool to read. The largest tool result the harness accepted in this turn
  was 20,717 characters, so the cap lies between those two numbers and the
  90,000-character budget does not reach it (paged by section under a
  measured 21,500-character budget in iteration 60, ADR-360). The agent paged the contract
  through 43 `inspect scope=api` reads in 2 min 40 s, against 3 min 51 s
  and 44 reads at 163,200 characters in iteration 55.
- **02:25:36–02:26:30, two probe scripts.** Catalog specs, then the servo
  and horn bodies, accepted as `part` outputs with no assembly.
- **02:26:30–02:38:20, one thinking message** of about 30,000 estimated
  tokens that ended on its own under the cap: the effort level did what
  ADR-359 said it would, one thought in place of iteration 55's three.
- **02:38:20–02:40:40, the design.** 280 lines rejected on `import math`;
  469 lines accepted as `c186fe25…`: a printed base, upper arm and forearm,
  two MG90S, two single-arm horns, two MR128 bearings, four M2×6 and two
  M2×16 screws as 15 fixed components, shoulder and elbow revolute joints
  with ±90° and ±100° limits, eleven declared contacts, an MJCF model and a
  reach task. The reply's fit summary: **105 pairs, 8 failing**, six screw
  intersections and two declared horn-to-screw contacts missed by 0.55 mm.
- **02:43:10, the first repair from the reply.** One accepted edit
  (`9f7b39c4…`) restored the catalog horn's through-bore and resolved both
  missed contacts: 105 pairs, 6 failing.
- **02:44:00–02:45:50, the bench.** The agent then added the floor it had
  reasoned MuJoCo needs, three ways: a plane (rejected, no solid), a slab
  marked `world=True` (rejected by MuJoCo, plane only in static bodies) and
  that slab welded to the grounded base, accepted as `512c157c…`, which the
  F2 check reports as **world geometry** on `bench`: 120 pairs, 7 failing.
- **02:46:00–02:48:22, the close.** The agent read `inspect scope=clearance`
  in full, the inventory, rebuilt to the identical digest and wrote five
  `DECISION:` lines and three `NOTE` lines into the project. Its closing
  message says "the only measured intersections are the six thread
  engagements, matching the analytic values exactly", 4.0715 mm³ per tab
  screw and 18.096 mm³ per centre screw, and that the bench "is the
  environment's plane … reported as world geometry".

**What this measures.** The product's fit report reached the agent in every
build reply and the agent acted on it inside the create turn: eight failing
checks became six by a measurement-led edit, with no continuation prompt
spent. What it did not do is treat the report as the bar. It accepted six
intersections it can explain and a world component it knows is reported, and
declared eleven contacts but no clearances and no sweep step, so **the swept
check is unavailable** for this revision ("declare `sweep_step_degrees` …
and explicitly rebuild") and F5's swept half is unmeasured. Its inventory
lists the servos and horns under `uncatalogued_sources`: the servo solid has
a tap-drill bore cut into its shaft and the horns are re-clocked, so two of
the four purchased families lost catalog identity, while the bearings and
all six screws keep it. Against F5's bar this revision fails on three
counts: 7 failing static checks, no swept measurement, and two purchased
parts not catalogued. The continuation prompt, frozen, asks for exactly
these three things by measurement alone. The turn cost 59 points of the
five-hour window (5 % to 64 %), so `continue-1` waits for the 07:20 UTC
reset, dispatched through `run.py resume` only when the probe reads room.

Against ot6: Heron's first accepted ot6 revision had a floor plane in the
design, 248.2 mm³ of servo tab buried in a cheek, and a horn 0.2 mm from its
link, none of them visible to the agent. Here the bench is reported by name
as world geometry, the servo tabs seat at 0 mm and 0 mm³, and the horns sit
in declared contact, measured; the six intersections are 4.07 and 18.10 mm³
screw engagements, and the agent's printed claim and the product's
measurement agree on their size and disagree on whether they count.

## Iteration 59: the first continuation completed

The first F5 continuation. `continue-1.prompt.txt` (756 bytes, digest
`80d725d2…`, unchanged) was dispatched on `ot7-heron-c` through `run.py
resume` at 07:22:36 UTC, two minutes after the reset, into the create
turn's own session at the receipt's `medium` (ADR-357, ADR-359). The
runner's probe read **5 %** and dispatched; the stream's first
`rate_limit_event` read 5 %, its last 35 %, and the probe after the
measurement read 38 %. No actor edited any design. **The turn completed**
in 610.6 s (exit 0, 41 model messages, 18 thinking blocks, no output-cap
hit, 19 tool calls: 13 `inspect`, ten of them the clearance scope, and 6
`edit_script`), the first continuation slot is spent, and the runner left
the attempt `paused` with `continue-2` next and two continuations unspent
([receipt](retained/heron-continue-1-c.json), 556,279-byte stream, digest
`d38864d8…`, in the project). Five minutes passed between the dispatch and
the first stream frame, which is the end of the first message.

Where the ten minutes went, from the stream's timestamps:

- **07:27:38, the report.** One `inspect scope=clearance` read: the
  accepted revision's seven failures and its unavailable sweep.
- **07:28:13–07:28:38, three rejected edits.** Each failed because one
  replacement's old text did not occur in the script.
- **07:29:09, the repair, accepted as `ae1020d4…`.** One edit did four
  things: bored the tab-screw and centre-screw holes to the 2.0 mm M2
  nominal over the screwed length, keeping the 1.6 mm pilots past the
  screw tip, and declared the six screw pairs as contacts (11 to 17);
  replaced the bench's plane collision with a box matching the slab,
  keeping `world=True` and the `fix_bench` weld to the base; declared
  `sweep_step_degrees=5.0`; and narrowed both joint ranges through two new
  parameters, shoulder [−90, 90] to [−90, 65] and elbow [−100, 100] to
  [−100, 40], with the actuator command limits matched. The reply's fit
  summary: **120 pairs, 1 failing**, the bench as world geometry; zero
  intersections, zero below clearance.
- **07:30:16, one rejected edit**: an MJCF body giving mass to a component
  not in the assembly.
- **07:30:26–07:31:22, nine clearance reads.** The static pairs and both
  joints' sweeps, paged.
- **07:31:44, `1779112b…`.** The second accepted edit changes four print
  lines and nothing else: the printout now says the screw pairs "must
  MEASURE as contact" instead of claiming an engagement annulus.
- **07:32:46, the close.** Four `DECISION:` lines and one `NOTE`; the
  project's DECISIONS.md gains ADR-007 to ADR-010.

**What this measures.** At rest the product reports **1 of 120 failing**:
zero intersections, zero below-clearance pairs, fifteen zero-distance pairs
all of them declared contacts, and the bench reported as declared world
geometry. The sweep is **complete on both joints at 5°**: shoulder 32
samples in 20.25 s, elbow 29 samples in 10.79 s, `solved_pose_agreement`
true on both, 0 mm³ maximum common volume on every one of the 120 pairs at
every sample, the closest moving pairs the designed 0.15 mm stub-in-bearing
and 0.25 mm horn-slot clearances, the forearm 1.0 mm from the upper arm at
the elbow limit and 9.8 mm from the bench at the shoulder limit. The
agent's own DECISION line says why the ranges narrowed: at the old
symmetric limits the forearm tip crossed the bench at shoulder +70.8° and
the forearm beam met the elbow yoke at +43.9°, which is the swept check
finding the collisions F3 was built to find, and the agent choosing the
range over the geometry. The smoke, run by the actor after the turn with
the runner's own command into `evidence/turn-1/smoke`, **passes**: hold
mode, 1 s, 51 samples, state finite, no floor breach at 0.5 mm, the base
grounded, 120 exact-BREP pairs with no overlap at any sample, initial pose
in agreement. Against F5's bar this revision now fails on **two counts**,
down from three: **world geometry in the design** (the bench is a
component, welded to the base, and its closing message calls that "no
world geometry in the design"), and **two purchased families
uncatalogued** (the inventory is unchanged from the create turn, and the
closing message calls it "the same catalog hardware"). Both are places
where the agent's claim and the product's measurement disagree and the
agent kept the claim. The screw repair is the one the previous record
flagged as the likely resolution: thread engagement is no longer modelled
as overlap, the screws sit coincident in nominal holes, and the displaced
volume is stated in the printout rather than measured. The continuation
prompt, frozen, asks again for every failing check resolved and every
purchased part a catalog part; `continue-2` is next through `resume`. The
turn cost 30 points of the five-hour window (5 % to 35 %), the probe read
38 % afterwards, under the runner's 45 % bound, so the next dispatch does
not wait for the 12:20 UTC reset.

Against ot6: Heron's ot6 revisions reached a clean fit only after three
hand-written turns naming the floor plane, the buried tab and the horn
gap. Here one frozen continuation, naming nothing, took the measured
failures from seven to one, published the sweep and passed the smoke; what
it did not do is take the bench out of the design or restore the catalog
servos and horns, the two counts the measurement still names.

## Iteration 66: the second continuation completed

The second F5 continuation. `continue-2.prompt.txt` (611 bytes, digest
`9a78ff9d…`, unchanged) was dispatched on `ot7-heron-c` through `run.py
resume` at 12:22:51 UTC, three minutes after the reset, into the same
session at the receipt's `medium` (ADR-357, ADR-359). The actor's own probe
read **3 %** at 12:22:09 and the runner's read **7 %** and dispatched; the
stream's first `rate_limit_event` read 9 %, its last 50 %, and the probe
after the measurement read **56 %**, over the 45 % bound. No actor edited
any design. **The turn completed** in 482.4 s (exit 0, 36 model messages,
12 thinking blocks, no output-cap hit, 19 tool calls: 13 `inspect`, eleven
of them the clearance scope, 4 `edit_script`, 1 `write_script` and 1
`rebuild`), the second continuation slot is spent, and the runner left the
attempt `paused` with `continue-3` next and one continuation unspent
([receipt](retained/heron-continue-2-c.json), 488,861-byte stream, digest
`1d83c796…`, in the project). One minute passed between the dispatch and
the first stream frame.

Where the eight minutes went, from the stream's timestamps:

- **12:23:51, the decision.** The agent's first message reads the one
  failing check its session already held, the bench's world-geometry row,
  and concludes the bench must leave the model entirely.
- **12:24:05, a rejected edit.** The engine refused to retire the
  `bench_slab` output while the bench component link still referenced it.
- **12:24:46–12:24:53, two script reads**, paged, of the source.
- **12:26:53, a rejected whole-source write**, for the same reason.
- **12:27:43, `d94fc2b8…`, accepted.** The bench component, its
  `fix_bench` weld to the base, the base-to-bench declared contact, the
  bench body with its box collision, and the bench's entries in the
  component, joint and output lists removed; the slab solid kept for the
  moment. The reply's fit summary: **105 pairs, 0 failing**.
- **12:28:23, a rejected edit**: a replacement's old text not found.
- **12:28:32, `58ff41b4…`, accepted.** The `bench_slab` solid and its
  output retired and the comment rewritten to say the bench is the
  environment's plane, not modelled. 105 pairs, 0 failing.
- **12:29:11–12:29:55, eleven clearance reads.** The static report, the
  sweep summary, both joints, and both joints' pairs paged; one read asked
  for a page of 55 and was refused at the cap of 50, then retried.
- **12:30:00, a rebuild.** The same revision re-accepted at the same digest.
- **12:30:53, the close.** One `DECISION:` line and one `NOTE
  design_specs:` line; the project's DECISIONS.md gains ADR-011.

**What this measures.** At rest the product reports **0 of 105 failing**:
zero intersections, zero below-clearance pairs, fourteen zero-distance pairs
all of them declared contacts, and `world_geometry` empty. The sweep is
**complete on both joints at 5°**: shoulder 32 samples in 19.45 s, elbow 29
samples in 10.39 s, `solved_pose_agreement` true on both, 0 mm³ maximum
common volume on every one of the 105 pairs at every sample, the closest
moving pairs the same 0.15 mm stub-in-bearing and 0.25 mm horn-slot
clearances as before. The script diff against `1779112b…` removes fourteen
lines and changes one comment, and touches nothing else: parameters, limits,
step, printed parts and hardware are byte-identical. The smoke, run by the
actor after the turn with the runner's own command into
`evidence/turn-2/smoke`, **passes**: hold mode, 1 s, 51 samples, state
finite, no floor breach at 0.5 mm, the base grounded, 105 exact-BREP pairs
with no overlap at any sample, initial pose in agreement. The agent's NOTE
says plainly that the exported MJCF no longer carries a floor geom and that
a trainer wanting one should add a plane outside Cadex; the smoke's support
check passes on the grounded base by construction and does not exercise a
floor.

Against F5's bar this revision now fails on **one count**, down from two:
**two purchased families uncatalogued**. The inventory lists both servos and
both horns under `uncatalogued_sources`, as it has since the create turn,
and the closing message again says "Catalog hardware unchanged (2× MG90S,
2× single-arm horns, …)". The frozen prompt asks for "every purchased part
a catalog part" and the agent did not act on it in three turns; it does not
read the inventory, and nothing in its fit summary names catalog identity.
Zero failing static and swept checks, zero actor edits, a passing smoke and
two of three continuations used are all met. `continue-3` is next through
`resume`; the probe read 56 % afterwards, so it waits for the 17:20 UTC
reset. The stream's `rate_limit_event` frames also flagged the seven-day
window at 90 % rising to 94 % (`allowed_warning`, reset 2026-09-17 19:00
UTC), which the runner's five-hour bound does not read.

Against ot6: Heron's ot6 revisions reached a clean fit only after three
hand-written turns naming the floor plane, the buried tab and the horn gap.
Here two frozen continuations, naming nothing, took the measured failures
from seven to zero, published a complete sweep and passed the smoke twice;
the floor plane, which ot6 fed back by hand, was found and removed from the
world-geometry row alone.

## Iteration 72: the last continuation completed, and F5 exhausted

The third and last F5 continuation. `continue-3.prompt.txt` (732 bytes,
digest `0814d73f…`, unchanged) was dispatched on `ot7-heron-c` through
`run.py resume` at 13:51:42 UTC into the same session at the receipt's
`medium` (ADR-357, ADR-359). This was the first dispatch after the owner
refreshed the account (ADR-361): the actor's own probe read **4 %** at
13:51 and the runner's read **7 %** and dispatched; the stream's first
`rate_limit_event` read 8 %, its last 38 %, and the probe after the
measurement read **41 %**, under the 45 % bound but not by enough for a
create turn. The seven-day window that continue-2's stream had flagged at
90–94 % read 0–4 %: the reset moved the five-hour boundary from 17:20 to
18:50 UTC. No actor edited any design. **The turn completed** in 142.9 s
(exit 0, 12 model messages, 5 thinking blocks, no output-cap hit, 6 tool
calls: 5 `inspect`, all of them the clearance scope, and 1 `rebuild`), the
third continuation slot is spent, and the runner wrote `status: exhausted`
with `slots_spent: 4`, `next_prompt: null`, then ran its own smoke
([receipt](retained/heron-continue-3-c.json), 188,093-byte stream, digest
`d051c2f9…`, in the project). One minute passed between the dispatch and
the first stream frame, as in every turn on this project.

Where the two minutes went, from the stream's timestamps:

- **13:52:40–13:52:57, five clearance reads.** The static report for the
  accepted revision, its 105 pairs paged at 50, 50 and 5, and the sweep
  block for both joints.
- **13:53:09, a rebuild.** The unchanged script re-submitted through normal
  acceptance and re-accepted at `58ff41b4…` with the identical digest
  `2c42c943…`.
- **13:54:04, the close.** The report names zero failing checks, so "the
  correct change this turn was no change"; one `DECISION:` line and one
  `NOTE design_specs:` line; the project's DECISIONS.md gains ADR-012.

**What this measures.** Nothing in the design changed: the script's digest
`91ace2bb…`, the accepted revision and its content digest are the ones
continue-2 left, `fit.json` and `inventory.json` carry the same digests as
turn-2, and `clearance.json` differs only in the sweep's elapsed seconds.
At rest the product reports **0 of 105 failing**: zero intersections, zero
below-clearance pairs, fourteen zero-distance pairs all of them declared
contacts, `world_geometry` empty. The sweep is **complete on both joints at
5°**: shoulder 32 samples in 19.60 s, elbow 29 samples in 10.29 s,
`solved_pose_agreement` true on both, 0 mm³ on every pair at every sample.
The smoke, run by the runner at exhaustion into `evidence/smoke`,
**passes**: hold mode, 1 s, 51 samples, state finite, no breach at 0.5 mm,
the base grounded, 105 exact-BREP pairs with no overlap at any sample,
initial pose in agreement, and its trace and geometry files carry the same
digests as the actor's turn-2 smoke, so the simulation reproduces exactly.

**F5 is exhausted.** The create prompt and all three continuations reached
the model on `ot7-heron-c` and every turn ended on its own, so under the
amended charter no slot remains and no fourth prompt exists. Against F5's
bar the final design meets zero failing static checks, zero failing swept
checks, zero actor edits, at most three continuations and a passing smoke,
and fails **one count: catalog hardware for every purchased part**. The
inventory has listed both servos and both horns under `uncatalogued_sources`
after every one of the four turns, because the create turn cut a tap-drill
bore into the servo bodies and re-clocked the horns on their splines, and
the placed outputs are no longer what a `lib.*` generator built. In all
four closing messages the agent asserted the opposite, this time as "all
twelve purchased parts are catalog parts (2× MG90S servo, 2× single-arm
horn, …)", and in four turns it never read the inventory: nothing in the
fit summary names catalog identity, and the frozen prompt's "keep every
purchased part from the catalog" was read as a statement about the design
rather than a check to run. That is a valid measured result and is reported
as such. Whether a catalog part that has been cut still counts as catalog
hardware is the owner's call on the tick; this report reads the product's
inventory and counts it as failing.

Against ot6: Heron's ot6 revisions reached a clean fit only after three
hand-written turns naming the floor plane, the buried tab and the horn gap,
and the actor never touched the ot6 script. Here one frozen create and three
frozen continuations naming nothing produced an arm with zero failing
static and swept checks, a complete sweep and three passing smokes, with
zero actor edits, and the one clause the agent did not close is the one it
had no measurement for.

## Implemented checks and evidence for F1–F9

| Criterion | What exists | Evidence and limits |
|---|---|---|
| F1 | Build replies include published static fit counts and every named failing pair; `clearance` inspect is exposed; instructions distinguish stdout claims from measurements | [Implementation](../../../.hypergraph/graph/record/happy-dawn-1960.md), [complete-list correction](../../../.hypergraph/graph/record/steady-quartz-9854.md), [real pager regression](../../../.hypergraph/graph/record/tidy-journey-9462.md), [CLI contract](../../CLI.md). A script printing “no overlap” returns its measured 100 mm³ intersection. Later-page failures and read errors are pinned |
| F2 | Contact and minimum-clearance declarations; overlaps, missed contact, insufficient clearance and world geometry are advisory findings | [Known-answer fixtures](FIT-INTENT.md), [record](../../../.hypergraph/graph/record/crisp-ember-0302.md), [numerical correction](../../../.hypergraph/graph/record/hidden-lodge-4550.md), [script contract](../../XSCRIPT.md). Solid world geometry needs explicit intent; grounding alone does not imply a floor |
| F3 | Published bounded exact-solid hinge and slider sweeps, agent inspection and `cadex clearance --sweep` | [Producer](../../../.hypergraph/graph/record/misty-spark-6372.md), [consumer](../../../.hypergraph/graph/record/green-river-3790.md), [slider fixtures](../../../.hypergraph/graph/record/curious-cedar-4881.md), [Finch product measurement](../../../.hypergraph/graph/record/kind-flint-2780.md), [sweep receipt](sweep/README.md). Discrete samples, unsupported or undeclared coverage explicitly incomplete; details below |
| F4 | Four void calls (ADR-355), one interrupted call (decision #44, ADR-356), and **four completed turns** on `ot7-heron-repair-d`: the repair prompt (1,461.9 s, 46 tool calls, six accepted revisions, static fit 0 of 120 pairs failing, swept complete at 5°, servo bodies uncatalogued, a bench slab added, joint ranges narrowed), `continue-1` (738.5 s, 20 tool calls, two accepted revisions, static fit 0 of 105 pairs failing, swept complete at 5° with zero common volume, both servos back to untouched catalog bodies, the bench removed, no world geometry) `continue-2` (128.7 s, 8 tool calls, no edit, the unchanged script re-accepted at the same digest after every measurement was re-read and none failed) and `continue-3` (104.9 s, 4 tool calls, no edit, the unchanged script re-accepted again, and the prompt's `DECISION:` and `NOTE design_specs:` lines written with 105 rest-pose and 210 swept checks passed, 0 failed); the collector's attachment assessment still fails on both horn-to-link pairs at 0.2 mm, declared as clearance | [First void call](../../../.hypergraph/graph/record/lucky-willow-8039.md), [second](../../../.hypergraph/graph/record/keen-quill-2265.md), [classification](attempts/void-calls.json), [interrupted call](retained/repair-timeout-b.json), [void call c](retained/repair-void-c.json), [completed turn d](retained/repair-completed-d.json), [assessment](#iteration-48-the-repair-turn-that-completed), [continue-1 on d](retained/repair-continue-1-d.json), [its assessment](#iteration-51-the-first-continuation-completed), [continue-2 on d](retained/repair-continue-2-d.json), [its assessment](#iteration-52-the-window-read-by-the-runner-then-continue-2-completed-adr-358), [continue-3 on d](retained/repair-continue-3-d.json), [its assessment](#iteration-53-the-last-continuation-completed-and-f4-exhausted). **Measured, and final: zero failing product checks after all four turns; two of three defects resolved, the horn gap declared rather than closed, and two continuations that name no failure leave the design unchanged. F4 is exhausted: no slot remains** |
| F5 | One void arm create (pre-restart), one **interrupted** create on `ot7-heron-b` (iteration 55: killed at the 30-minute bound after 4 min of reading and three thinking-only messages that each hit the 32,000-token output cap; three probe scripts written, two accepted, no assembly, no design), and **one completed create turn** on `ot7-heron-c` (iteration 57, effort `medium`: 1,530.4 s, 82 tool calls, three accepted design revisions, static fit 8 then 6 then 7 of 120 failing: six screw intersections of 4.07 and 18.10 mm³ and the bench as world geometry; sweep unavailable, no step declared; servos and horns uncatalogued after modification, bearings and screws catalogued; `describe_api` at 82,523 characters still refused by the harness), and **one completed continuation** on the same project (iteration 59, `continue-1`: 610.6 s, 19 tool calls, two accepted revisions, static fit 1 of 120 failing: the bench as world geometry, zero intersections after the screw holes were bored to nominal and the six screw pairs declared contacts; sweep complete on both joints at 5° with 0 mm³ on every pair after the ranges were narrowed to [−90, 65] and [−100, 40]; servos and horns still uncatalogued; smoke pass, hold mode, 1 s, 51 samples, 120 pairs, no breach), and **a second completed continuation** (iteration 66, `continue-2`: 482.4 s, 19 tool calls, two accepted revisions that delete the bench component, its weld, contact row, body and solid; static fit 0 of 105 failing with no world geometry; sweep complete on both joints at 5° with 0 mm³ on every pair; servos and horns still uncatalogued while the closing message calls the catalog hardware unchanged; smoke pass, hold mode, 1 s, 51 samples, 105 pairs, no breach), and **a third completed continuation** (iteration 72, `continue-3`: 142.9 s, 6 tool calls, five clearance reads and one rebuild, no edit; the unchanged script re-accepted at the same revision and digest; static fit 0 of 105 failing, sweep complete at 5° with 0 mm³ on every pair; servos and horns still uncatalogued while the closing message calls all twelve purchased parts catalog parts; the runner's own smoke pass, hold mode, 1 s, 51 samples, 105 pairs, no breach, its trace digest identical to turn-2's) | [Record](../../../.hypergraph/graph/record/quiet-dew-5243.md), [void receipt](attempts/heron-refusal.json), [interrupted receipt](retained/heron-interrupted-b.json), [its assessment](#iteration-55-the-arm-create-call-interrupted-at-the-bound), [completed create receipt](retained/heron-create-c.json), [its assessment](#iteration-57-the-arm-create-turn-completed), [continue-1 receipt](retained/heron-continue-1-c.json), [its assessment](#iteration-59-the-first-continuation-completed), [continue-2 receipt](retained/heron-continue-2-c.json), [its assessment](#iteration-66-the-second-continuation-completed), [continue-3 receipt](retained/heron-continue-3-c.json), [its assessment](#iteration-72-the-last-continuation-completed-and-f5-exhausted). **Exhausted: the create slot and all three continuations spent on completed turns. The measured result meets zero failing static and swept checks, zero actor edits, three continuations and a passing smoke; the one count failing F5's bar is catalog hardware for every purchased part, the two servos and two horns** |
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
exact BREPs and proxy floor support under a 300-second deadline. Since ADR-377
floor support includes the base's attitude: the first real free-base topple
this run measured, the retained ot6 balancer at zero torque, passed the old
support check at 101.3° over and fails the new one. The grounded
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
recorded regression evidence. **F4 and F5 are exhausted with their measured results,
and F6 and F7 remain open.** F4's repair prompt and all three continuations have
each been spent on a completed turn: zero failing product checks after all
four, every purchased part catalogued and no world geometry after the
second, the design left unchanged by the third and fourth, two of three
defects resolved, the horn gap declared as clearance rather than closed.
F5 has had one interrupted create call on `ot7-heron-b` (iteration 55), which
reached the model and produced no design before the bound, and two completed
turns on `ot7-heron-c`: the create (iteration 57), an accepted arm with 7 of
120 static checks failing, no swept measurement and two purchased families
uncatalogued; and `continue-1` (iteration 59), which brought the static
failures to 1 of 120 (the bench, world geometry in the design), published a
complete sweep with zero overlap on both joints, passed its smoke, and left
the servos and horns uncatalogued; and `continue-2` (iteration 66), which
deleted the bench from the model and brought the static failures to 0 of
105, kept the sweep complete with zero overlap, passed its smoke, and again
left the servos and horns uncatalogued; and `continue-3` (iteration 72),
which read the whole report, found nothing failing, changed nothing and
re-accepted the unchanged script, the runner's smoke passing. The create
slot and all three continuations are spent: F5 is exhausted, and its
measured result meets every count of its bar except catalog hardware for
every purchased part. F6 and F7 are untried. Void and interrupted calls establish no geometric design
outcome, and they spent nothing.

F10's requirement that the critic accepted done is **unmet**. This report
makes no done claim. What remains is the agent half of the charter, in this
order: the balancer and biped creates in fresh suffixed projects
(`ot7-robin-b` for F6, `ot7-plover-b` for F7), each through its
continuations as its fit report requires, each with its smoke rollout, and
each dispatched only when the runner's own window reading shows room
(ADR-358), at the effort level ADR-359 recorded and with `describe_api`
paged by section under a measured budget (ADR-360). A
design that does not reach zero failing checks within its three continuations
is a valid measured result and will be reported as such.

The gate has not opened yet. `run.py window --model claude-fable-5` on
2026-09-16 at 16:39 UTC read the five-hour window at 12 % and the seven-day
at 52 %, and the probe itself was **refused** in 2.3 s: a rejected
`rate_limit_event` naming `seven_day_overage_included`, a synthetic
`rate_limit` assistant frame and an HTTP 429 reading "You've reached your
Fable limit", with the reset at 2026-09-18 14:00 UTC. By ADR-364 that is no
room whatever the window percentages say, so `room` is `false`, no prompt was
spent, and F6 and F7 keep every slot. This report is then
rewritten with one row per design.

### The gate is shut now, and no clock says when it opens

Measured on 2026-09-16 at 16:46 UTC. This subsection records what the receipts
establish — a refusal in force at the moment each was taken — and sets the two
schedules side by side. **Neither schedule bounds the refusal, in either
direction.**

- **What the refusal establishes.** The receipt is
  [`attempts/f6-window-refusal.json`](attempts/f6-window-refusal.json), read
  off `run.py window --model claude-fable-5` and recorded in
  `pale-garden-4669`. Its binding field is `overage.disabled_reason:
  "org_level_disabled"` — an organisation-level setting on this account. That
  receipt is evidence of exactly one thing: `claude-fable-5` was refused on
  this account **at the moment the probe was taken**. It does not date the end
  of that setting and does not put a floor under it; an organisation-level
  setting can change at any time, including before any window resets, as this
  account showed once already when the owner refreshed it mid-run (ADR-361).
  Only an **unrefused** probe is evidence the refusal has lifted, and only a
  fresh refused probe is evidence it still holds.
- **The refusal still held at 17:02 UTC.** A third probe, two hours after the
  second, was refused on the same `org_level_disabled` setting with
  `seven_day_overage_included` at 100 % and the five-hour window at 18 %
  (`attempts/f6-window-refusal.json`, `third_probe`). It spent no slot; F6's
  four and F7's four are all still unspent. It also arrived with its frames in
  the other order — an allowed five-hour frame in front of the one that
  rejected — which the reading took at face value, printing `five_hour,
  allowed, resets 2026-09-16T19:20Z` beside `room: false` and dropping the
  100 % window that caused the refusal. ADR-369 reads the frame that rejected,
  and labels its `resets_at` as the schedule of that window rather than a date
  for the setting.
- **The scheduled window reset.** `seven_day_overage_included` resets at epoch
  `1789740000`, which is **2026-09-18T14:00:00Z**. That is the rejected
  window's own `resets_at`, and the runner reads the same epoch for the Claude
  seven-day window in `.ouroboros/runs/ot7/status.json`. The epoch is not an
  estimate, but what it dates is a **scheduled reset of a usage window** — not
  a lifting of the refusal, and not the earliest the refusal could lift. A
  probe after that epoch may well be refused again, and a probe before it may
  not be: the second probe taught the same lesson in the other direction,
  reading `status: allowed` at 2 % twenty minutes later and being refused
  anyway.
- **The refusal still held at 21:37 UTC, and the gate that will end it was
  half broken.** A fourth probe, four hours after the third, was refused on the
  same `org_level_disabled` setting with `seven_day_overage_included` at 100 %
  and the five-hour window at 11 % (`attempts/f6-window-refusal.json`,
  `fourth_probe`). It spent no slot. Reading the gate while F6 waited found the
  mirror of ADR-369 still unfixed: on an **answered** probe the reading was
  whichever `rate_limit_event` frame arrived first, and the stray rejected
  overage frame this organisation emits on every probe is one of them. The
  same answered probe at five-hour 8 % reads `allowed` and dispatches with the
  allowed frame in front, and `rejected` and defers with the rejected frame in
  front — reproduced both ways, and fixed by ADR-376 (`235ebce4`): the reading is
  the frame that bound the call, rejecting on a refused probe and allowing on
  an answered one. Had the refusal lifted while this stood, F6's and F7's eight
  prompts could have been withheld from a model that would have answered them,
  under a `deferred` block citing an overage window's reset. It changes no
  product behaviour, no frozen prompt and no slot accounting.
- **This run's stop.** `.ouroboros/runs/ot7/run.yml` sets
  `stop.until: 2026-09-17T00:25:13`, a naive local timestamp the runner
  compares against local time (`should_stop` in `ouroboros/budget.py`), so it
  is **2026-09-17T04:25:13Z** at UTC−4. Record `restless-gate-7062` provenances
  it as the original 48-hour deadline preserved across the restart.
  `stop.after: 48h` measured from this process's `started: 2026-09-16T11:00:28`
  would trip at 2026-09-18T15:00:28Z instead, and `should_stop` returns on
  whichever condition trips first, so `until` is the binding one.
- **The difference: 33 h 34 m 47 s.** The scheduled reset of the window these
  two designs were refused against falls more than a day *after* the run is
  configured to end. That is arithmetic between two schedules, and nothing
  more: it says the reset is not going to arrive inside this run, not that the
  refusal cannot lift inside it. Two exits can come sooner still:
  `stop.max_stuck: 25` — the critic returned `looping` on iteration 84 and
  `stuck` on iteration 85 — and any owner action.

So F6 and F7 stand with every slot unspent and no dispatch possible while the
refusal holds. The charter's rule keys dispatch to the harness being
available, so an iteration that probes and finds the refusal gone may still
dispatch inside this run; nothing here forecloses that, and nothing here
promises it. If the run ends with the refusal still in force, both designs end
**unattempted, with all eight create and continuation slots unspent**. That is
not exhaustion. By the charter's
exhaustion policy a design is exhausted only once its create prompt and all
three continuations have reached the model, and neither design has spent one;
the single pre-restart refusal against each is void (ADR-355) and consumed
nothing. No verdict, record or report may read this ending as "no authorised
experiment remaining".

What finishing them takes is unchanged and needs no new decision: once a
window probe on `claude-fable-5` returns without being refused — whenever that
is, since no schedule here dates it — dispatch the frozen
[`robin.create.prompt.txt`](prompts/robin.create.prompt.txt)
(`e20ee7ab…`) into a fresh `ot7-robin-b` and
[`plover.create.prompt.txt`](prompts/plover.create.prompt.txt)
(`b95f98b7…`) into a fresh `ot7-plover-b`, on `claude-fable-5` — the model
every completed F4 and F5 turn used — each through its continuations as its
fit report requires and each with its smoke rollout. No prompt changes: a
changed prompt starts a new attempt. The product-version paragraph below
applies with more force the longer that wait is, because every product change
landed in the meantime is one more difference separating F6 and F7 from F5.

No unattended role may extend, stop or restart a run, and neither this
subsection nor the record behind it does. This is a measurement for the owner.

**Product version.** F6 and F7 run on a product **twelve** changes newer than
the one F5 ran on, every frozen prompt unchanged: ADR-362, ADR-366, ADR-367,
ADR-368, ADR-370, ADR-371, ADR-372, ADR-373, ADR-374, ADR-375, ADR-377 and
ADR-378. Nine of them change the measured fit surface a design reads; two more
are the inventory block beside it and the repair wording in the agent's own
prompt; the twelfth is the smoke rollout their bar ends on. Each is listed
below with what it publishes, because a difference in an F6 or F7
row that lands on a fact one of these changes publishes is a difference across
that change and not a difference in the agent.

**ADR-362** (`fd3b3643`) is the inventory. After F5's exhaustion the critic
asked that the published inventory's catalog counts and uncatalogued sources
reach the agent beside the design-turn fit summary, and every build reply now
carries an advisory `inventory` block — component, catalogued and uncatalogued
counts, the catalog roll-up and every uncatalogued source by name — the system
prompt says to read it before claiming catalog hardware, and the `--json`
envelope carries it as `inventory`. F5's four turns had no such block, which
is why its agent could report every purchased part as catalog hardware while
the inventory listed its servos and horns as uncatalogued. The catalog count
in the F6 and F7 rows is measured on the newer product.

**ADR-366** (`b65ec710`) landed for the same reason on the other half of F5's
bar. F5's create turn accepted an arm whose two hinges declared limits and
whose assembly declared no `sweep_step_degrees`, so the engine published no
sweep and the reply said nothing about it; the agent found the gap a
continuation later. Every build reply now carries `fit.sweep` beside the
static verdict — coverage, one row per limited joint with its minimum
distance, maximum common volume and first-contact value, and every pair that
interpenetrates anywhere in a range — computed from the same published
measurements with no second engine call, and the runner's attempt rows carry
it as `swept_fit`. Swept coverage in the F6 and F7 rows is therefore measured
on the newer product.

**ADR-367** (`d6a52b02`) landed on the half ADR-366 left: F5's create turn
accepted an arm whose two limited hinges declared no step, the engine
published no sweep at all, and the reply could only say `sweep unavailable`.
The engine now publishes coverage on every assembly, so an assembly that
declares neither step reads `incomplete` with one row per limited joint naming
the declaration it is missing — an enumeration that touches no geometry and
measured under 1 ms on the lifecycle fixture. F5's create turn spent a
continuation discovering that gap; on the product F6 and F7 run, the first
build reply names it.

**ADR-368** (`3cd8905e`) is its wording follow-up, and made the two causes of
a sweep `verdict: unavailable` distinguishable in the block (`coverage`), in
the reply's progress phrase and in the agent's instructions: a revision
accepted by an older engine, versus an assembly with no limited joint at all.

**ADR-370** (`3b27f62e`) added the attachment rows. Every pair welded by an
unsuppressed `fixed` joint is measured at the solved pose and reported as
touching, not touching or unknown, beside the four fit checks and never
counted among them — a fixed joint asserts one rigid body, and a gap between
the solids is a connection the geometry does not make. It reaches F6 and F7
directly, because a balancer and a biped weld horns, bearings and fasteners to
their links.

**ADR-371** (`45a2fe2c`) stops a **suppressed** limited joint counting as
missing swept coverage: the solver ignores it, so it holds no range to sweep,
it costs no child process, and its row is `skipped` rather than a coverage
hole that no declaration could ever fill.

**ADR-372** (`43dfe452`) exempts a pair welded by an unsuppressed `fixed`
joint from the 0.1 mm undeclared-pair minimum. Without it, mounting hardware
flush against what carries it failed `below clearance` at 0.0 mm for doing
what the joint asked. Measured on the retained ot6 biped, 16 of Finch's 32
`below clearance` rows were welds at 0.0 mm, so this reaches F6 and F7 on
exactly the hardware they will weld.

**ADR-373** (`64b59cee`) tells the agent, in its own prompt, to declare an
intended gap narrower than the default with `clearances=[(a, b, 0.05)]`
rather than widen a seat that was already right, and says what `contacts=` is
not — it holds a pair to 0.001 mm, so it fails a 0.05 mm running fit as a
`missed contact` rather than clearing it. Finch's four 0.05 mm bearing seats
are the case it names.

**ADR-374** (`65cbe3ca`) makes the swept half of the fit read its minimum
distance, maximum common volume and first contact over the pairs the swept
joint actually moves, counted as `pairs_moving` beside `pairs_measured`. A
pair the joint cannot move repeats its solved-pose measurement at every
sample, so a horn welded flush against the link it turns with — correct design
under ADR-372, and what a balancer does — read 0.0 mm at every angle and took
first contact at the bottom of the declared range, and the roll-up took the
minimum, so the weld won every time. The per-pair rows, the `failing` list and
every threshold are unchanged. It is the second change in a row that reaches
F6's and F7's own hardware directly.

**ADR-375** (`18492813`) stops the swept report passing over a joint that can
move and declares no limits. Such a joint reached no row at all, so coverage
read `complete` while a continuously rotating wheel, a free spinner or a
loop-closure hinge had been measured at the solved pose and nowhere else; it
is now `incomplete` with the limit to declare named per kind, and only a weld
or a suppressed unlimited joint stays out of the report. It reaches F6
directly — a two-wheeled balancer's moving parts are exactly the joints with
no natural limit — and is the third change in a row that lands on F6's and
F7's own hardware. Nothing is refused and no threshold moved.

**ADR-377** (`cf06d2b8`) is the smoke rollout, and it was measured on F6's
own mechanism. The retained ot6 balancer, copied to `ot7-robin-smoke` and
smoked for the first time in this run, topples at zero torque in 0.38 s and
comes to rest **101.3° over, 43.5 mm lower, chassis on the floor** — and the
`support` check called that a pass, because a fallen design is touching the
floor and is not moving. Robin's verdict still failed, on its own termination
rule and 2.7 mm of chassis in the floor, but a design with no exported task
and a softer landing would have passed `cadex smoke` lying on its side. The
check now reads the base's attitude against the pose its accepted keyframe
gave it, and fails beyond `--max-tilt-degrees` (default 30°, against Finch's
measured 9×10⁻⁶ ° standing). F5's arm is grounded and reads none of this; F6
and F7 are the two designs whose failure mode is falling over, so their smoke
results are measured across this change.

**ADR-378** (`6ce89fff`) closes the same hole in the swept fit that ADR-377
closed in the smoke: a measurement taken and judged against nothing. The swept
block could fail a pair on interpenetration or on an unmeasured pair, and on
nothing else — so the minimum distance it measured through a joint's range,
which is the whole reason for sweeping, was printed and not checked. F2's
third and fourth checks (a declared clearance below its minimum, an undeclared
pair closer than the default) existed at the solved pose only. Reproduced on
real OCCT solids: a hinge that takes two unit spheres from **10.751594 mm**
apart at the solved pose to **0.04 mm** at 90°, never touching, zero common
volume at all 71 samples — static `pass, 0 failing`, correctly, and swept
`pass, 0 failing` with the 0.04 mm printed beside it, against the 0.1 mm the
same undeclared pair is held to at rest. A swept pair now fails `below
clearance` against its own minimum, under three narrowing rules that keep the
block additive to the static one: only a pair the joint moves, only a pair the
static block calls clear, and never a declared contact or a welded pair.
Replayed over all twenty-one retained ot7 `clearance.json` files the new rule
adds **zero** failures, so no number in this report moves. F6 and F7 are
judged on "zero failing static and swept fit checks", and until this change
the swept half of that bar could only be failed by an overlap.

F5 is not re-run and no frozen prompt changed for any of the twelve. Every
number in the F6 and F7 rows is therefore measured on this product, and the
ot6 and F5 comparisons in this report are read across these changes.

> *Superseded on 2026-09-15:* "All scheduled collector slots are consumed.
> The run's successful-completion prerequisites are not established by the
> existing evidence. ... This run returns an incomplete outcome." The
> reconciliation the earlier handoff deferred was folded by the restart
> (`4505e21f`); the outcome is open, not terminal.
