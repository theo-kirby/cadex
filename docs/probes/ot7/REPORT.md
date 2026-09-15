# ot7 closing report — measured checks, agent outcomes not yet tried

Verified against source: 2026-09-15. [Cadex-new]

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
**F5 has had its first call that reached a model, and it was interrupted**:
iteration 55 dispatched the frozen arm create prompt on `ot7-heron-b` at 13 %
of the window, and the runner killed the turn at its 30-minute bound with no
design written: four minutes of reading, then three thinking-only messages
that each hit the 32,000-token output cap and were auto-resumed by the
harness (see [Iteration 55](#iteration-55-the-arm-create-call-interrupted-at-the-bound)).
Under decision #44 and ADR-356 that is an interrupted execution: no slot
spent, the create prompt and all three continuations unspent, retry on
`ot7-heron-c`. This report is written forward from the restart; it claims
no design outcome and no critic acceptance of done.

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
| Heron arm / F5 | 1 (pre-restart); and 1 **interrupted** call apart from it: iteration 55 on `ot7-heron-b`, killed at the runner's 30-minute bound after 68 model messages with no design written ([receipt](retained/heron-interrupted-b.json)) | 0 | unspent | 3 of 3 | `ot7-heron-c` |
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

## Implemented checks and evidence for F1–F9

| Criterion | What exists | Evidence and limits |
|---|---|---|
| F1 | Build replies include published static fit counts and every named failing pair; `clearance` inspect is exposed; instructions distinguish stdout claims from measurements | [Implementation](../../../.hypergraph/graph/record/happy-dawn-1960.md), [complete-list correction](../../../.hypergraph/graph/record/steady-quartz-9854.md), [real pager regression](../../../.hypergraph/graph/record/tidy-journey-9462.md), [CLI contract](../../CLI.md). A script printing “no overlap” returns its measured 100 mm³ intersection. Later-page failures and read errors are pinned |
| F2 | Contact and minimum-clearance declarations; overlaps, missed contact, insufficient clearance and world geometry are advisory findings | [Known-answer fixtures](FIT-INTENT.md), [record](../../../.hypergraph/graph/record/crisp-ember-0302.md), [numerical correction](../../../.hypergraph/graph/record/hidden-lodge-4550.md), [script contract](../../XSCRIPT.md). Solid world geometry needs explicit intent; grounding alone does not imply a floor |
| F3 | Published bounded exact-solid hinge and slider sweeps, agent inspection and `cadex clearance --sweep` | [Producer](../../../.hypergraph/graph/record/misty-spark-6372.md), [consumer](../../../.hypergraph/graph/record/green-river-3790.md), [slider fixtures](../../../.hypergraph/graph/record/curious-cedar-4881.md), [Finch product measurement](../../../.hypergraph/graph/record/kind-flint-2780.md), [sweep receipt](sweep/README.md). Discrete samples, unsupported or undeclared coverage explicitly incomplete; details below |
| F4 | Four void calls (ADR-355), one interrupted call (decision #44, ADR-356), and **three completed turns** on `ot7-heron-repair-d`: the repair prompt (1,461.9 s, 46 tool calls, six accepted revisions, static fit 0 of 120 pairs failing, swept complete at 5°, servo bodies uncatalogued, a bench slab added, joint ranges narrowed), `continue-1` (738.5 s, 20 tool calls, two accepted revisions, static fit 0 of 105 pairs failing, swept complete at 5° with zero common volume, both servos back to untouched catalog bodies, the bench removed, no world geometry) `continue-2` (128.7 s, 8 tool calls, no edit, the unchanged script re-accepted at the same digest after every measurement was re-read and none failed) and `continue-3` (104.9 s, 4 tool calls, no edit, the unchanged script re-accepted again, and the prompt's `DECISION:` and `NOTE design_specs:` lines written with 105 rest-pose and 210 swept checks passed, 0 failed); the collector's attachment assessment still fails on both horn-to-link pairs at 0.2 mm, declared as clearance | [First void call](../../../.hypergraph/graph/record/lucky-willow-8039.md), [second](../../../.hypergraph/graph/record/keen-quill-2265.md), [classification](attempts/void-calls.json), [interrupted call](retained/repair-timeout-b.json), [void call c](retained/repair-void-c.json), [completed turn d](retained/repair-completed-d.json), [assessment](#iteration-48-the-repair-turn-that-completed), [continue-1 on d](retained/repair-continue-1-d.json), [its assessment](#iteration-51-the-first-continuation-completed), [continue-2 on d](retained/repair-continue-2-d.json), [its assessment](#iteration-52-the-window-read-by-the-runner-then-continue-2-completed-adr-358), [continue-3 on d](retained/repair-continue-3-d.json), [its assessment](#iteration-53-the-last-continuation-completed-and-f4-exhausted). **Measured, and final: zero failing product checks after all four turns; two of three defects resolved, the horn gap declared rather than closed, and two continuations that name no failure leave the design unchanged. F4 is exhausted: no slot remains** |
| F5 | One void arm create (pre-restart) and one **interrupted** create on `ot7-heron-b` (iteration 55: killed at the 30-minute bound after 4 min of reading and three thinking-only messages that each hit the 32,000-token output cap; three probe scripts accepted, no assembly, no design); zero attempts | [Record](../../../.hypergraph/graph/record/quiet-dew-5243.md), [void receipt](attempts/heron-refusal.json), [interrupted receipt](retained/heron-interrupted-b.json), [its assessment](#iteration-55-the-arm-create-call-interrupted-at-the-bound). **Open: create prompt and all continuations unspent; retry on `ot7-heron-c` after the reset** |
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
recorded regression evidence. **F4 is exhausted with its measured result,
and F5–F7 remain open.** F4's repair prompt and all three continuations have
each been spent on a completed turn: zero failing product checks after all
four, every purchased part catalogued and no world geometry after the
second, the design left unchanged by the third and fourth, two of three
defects resolved, the horn gap declared as clearance rather than closed.
F5 has had one interrupted create call on `ot7-heron-b` (iteration 55), which
reached the model and produced no design before the bound; F6 and F7 are
untried. Void and interrupted calls establish no geometric design outcome,
and they spent nothing.

F10's requirement that the critic accepted done is **unmet**. This report
makes no done claim. What remains is the agent half of the charter, in this
order: the arm, balancer and biped creates in fresh suffixed projects
(F5–F7), each through its continuations as its fit report requires, each
with its smoke rollout, and each dispatched only when the runner's own
window reading shows room (ADR-358), the arm now on `ot7-heron-c` and after a
recorded decision on the effort level and output cap the interrupted call
measured against. A
design that does not reach zero failing checks within its three continuations
is a valid measured result and will be reported as such. This report is then
rewritten with one row per design.

> *Superseded on 2026-09-15:* "All scheduled collector slots are consumed.
> The run's successful-completion prerequisites are not established by the
> existing evidence. ... This run returns an incomplete outcome." The
> reconciliation the earlier handoff deferred was folded by the restart
> (`4505e21f`); the outcome is open, not terminal.
