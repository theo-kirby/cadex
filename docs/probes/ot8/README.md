# ot8 — the experiment contract

Verified against source: 2026-09-20. [Cadex-new]

**This is G1**: the frozen, bounded contract every ot8 product turn runs
under, written before any of them. It names the ot7 baselines it measures
against, the prompts it may send, the bars each experiment passes or fails by,
and the ledger that says what a call cost. The closing report is
[`REPORT.md`](REPORT.md) and is written last.

ot7 ended with three designs the product agent wrote unassisted and three
things it did not establish (`docs/probes/ot7/REPORT.md`): the arm reached
zero failing fit checks with **two servos and two horns modified out of
catalog identity**; the biped's smoke passed only on a model **re-exported
outside the accepted pin** (ADR-395); and the balancer's ordinary holding
smoke **failed**, with no measured account of why. ot8 measures those three,
each as a bounded experiment with its own new identity, and reports what it
measures whether or not the design succeeds.

## The baselines

Pinned in [`baselines.json`](baselines.json), which the collector reads before
it will start a seeded attempt. The three ot7 projects stay **read-only**;
ot8 never dispatches into one, and an ot8 copy that does not reproduce its
baseline's identity exactly is refused before any prompt is sent.

| design | ot7 baseline | accepted revision | accepted digest | how ot8 uses it |
|---|---|---|---|---|
| arm | `ot7-heron-c` | `58ff41b4…` | `2c42c943…` | **comparison only.** G2 designs a new arm from an empty project; nothing is copied |
| biped | `ot7-plover-e` | `0491ead7…` | `a00d1aea…` | **seed.** G3 works on an independent copy |
| balancer | `ot7-robin-c` | `0b438561…` | `b933d905…` | **seed.** G4 works on an independent copy |

ot7's F5, F6 and F7 are exhausted and stay exhausted: their slots are spent,
their receipts stand, and no ot8 experiment re-runs one. G2, G3 and G4 are new
experiments with new identities, not retries.

## The prompts

Frozen in [`prompts/`](prompts/README.md) before any product turn and pinned
by `cli/tests/test_ot8_prompts.py`. The arm's create prompt is byte-identical
to ot7's, so the comparison is a comparison of one ask against two products.
The continuations are ot8's own, because this charter directs the agent to its
measured **fit, inventory and smoke** evidence and ot7's pointed at fit alone —
that difference is the experiment on the arm, and the report carries it.

**Each design gets one initial product prompt and at most three
continuations**, in order, and a continuation is spent only after a turn that
reached the model and ended on its own. A design that still fails after its
last allowed continuation is a measured result, reported as one, and never
prompted again under this freeze.

| design | initial prompt | continuations | project |
|---|---|---|---|
| G2 arm | `heron.create.prompt.txt` | `continue-1`, `-2`, `-3` | a new empty `ot8-heron*` |
| G3 biped | `rebuild.prompt.txt` | the same three | an independent copy, `ot8-plover*` |
| G4 balancer | `resolve.prompt.txt` | the same three | an independent copy, `ot8-robin*` |

G4's initial prompt is dispatched **only if** the actor's own no-slot
diagnosis finds an actionable design defect. If the diagnosis instead
reproduces an out-of-scope control requirement, that experiment ends there
with its measurements and spends nothing.

## The bars

Each bar is measured, not argued. A bounded experiment may close on a clearly
reported negative result; none of them closes by calling an unfinished
measurement a pass.

**G2, the arm.** *Success*: zero failing static fit checks, zero failing swept
checks, every purchased component placed as an **unmodified catalog part**,
zero actor design edits, and a passing ordinary smoke on the accepted
artifacts. *Failure*: anything else, reported as the exact remaining defects
after the allowed turns, with the inventory row that names each uncatalogued
source, beside ot7's two modified servos and two modified horns.

**G3, the biped.** *Success*: the accepted digest, MJCF digest, fit,
inventory, a fresh-process reopen and an **ordinary `cadex smoke` against the
accepted pin** all agree, and the smoke passes — with no substituted bundle
and no re-export probe. *Failure*: any of those measured and reported as it
reads. The actor may prepare the copy mechanically and may measure it; only a
product-agent turn may rebuild or re-accept it, and none may change its
script, parameters or accepted state.

**G4, the balancer.** *Success*: an actionable measured diagnosis that
distinguishes a geometry or export mismatch, a design defect, and a missing
feedback control, from published measurements and the MJCF/task contract —
and, if the cause is an actionable design defect, a repair from the frozen
prompts that remeasures clean. *Failure*: an unexplained smoke failure.
**A no-feedback inverted pendulum that topples is not a failure of this
experiment and is never reported as a success of the design.** If the
requested behaviour needs control outside this charter, the exact missing
control contract is recorded and the experiment stops there.

**What no bar may be passed with.** No design is grounded that its own script
declares free; no stabiliser or support the machine does not have is added; no
declared joint, limit or task rule is suppressed or weakened; no declared
rollout is shortened. Every frozen prompt says so in the same words
(`prompts/README.md`). A design may fail.

## The slot ledger

Every dispatch lands in exactly one column, and only the first spends anything.
The classification is the collector's, from the call's own evidence, and its
rules are ot7's unchanged.

| column | what it is | slot | project | rule |
|---|---|---|---|---|
| **completed** | reached the model and ended on its own | **spent** | continues | — |
| **failed** | a provider error the call returned on its own, with a stream | **spent** | closed | — |
| **void** | a provider usage, session or credit limit, or a turn this repository's own defect invalidated | unspent | closed; retry in a fresh suffixed project | ADR-355 |
| **interrupted** | reached the model and did not end on its own: killed at the runner's bound, a child that never launched, or a runner that died | unspent | closed; retry in a fresh suffixed project | ADR-356, ADR-388 |
| **unreached** | the CLI refused before a provider session existed; no model saw the prompt | unspent | **stays open**; the same prompt is still next in the same project | ADR-386 |

A void, interrupted or unreached call keeps all of its evidence, and that
evidence may never be reported as a design failure or a design success. The
report lists every one of them with its receipt, the way ot7's does.

## Running it

The ot7 collector is the ot8 collector (ADR-400): one `--run ot8` selects the
ot8 freeze, the `ot8-*` project prefix and the two seeded designs. Nothing
under `docs/probes/ot7/` or in an ot7 project is written by an ot8 attempt.

```bash
# G2: a new arm, its create prompt and as many continuations as the window allows
pixi run python docs/probes/ot7/runner/run.py --run ot8 heron \
  "$PROJECTS/ot8-heron" --model claude-opus-5 --turns 1
pixi run python docs/probes/ot7/runner/run.py resume "$PROJECTS/ot8-heron"

# G3 and G4: an independent copy of the baseline, then its one initial prompt
pixi run python docs/probes/ot7/runner/run.py --run ot8 plover \
  "$PROJECTS/ot8-plover" --model claude-opus-5

# a measurement that spends no slot, and the window before any dispatch
pixi run python docs/probes/ot7/runner/run.py smoke "$PROJECTS/ot8-plover"
pixi run python docs/probes/ot7/runner/run.py window --model claude-opus-5
```

A seeded attempt measures its baseline **before** it sends anything: fit,
inventory and one bounded smoke, all recorded in the receipt, with the seed
identity held equal across them. That smoke is evidence and never a gate —
G3 and G4 exist because these baselines fail it.

Receipts live in the external project under
`evidence/` (a create attempt), `evidence/g3-rebuild/` or
`evidence/g4-resolve/` (a seeded one, kept apart from the `evidence/` the copy
inherits). Committed copies land in [`retained/`](retained/), at most 16 KB
each, with full evidence left project-local and cited by path and digest.

## Access

All roles and product calls use `claude-opus-5`, with no model fallback, and
no prompt is dispatched while the five-hour window reads above 45 %. The
window is probed before every design turn and the reading is kept in the
receipt; a refused probe is not evidence of room. At the freeze the account
answered a probe on `claude-opus-5` with the five-hour window at **10 %** and
the seven-day at **16 %** ([receipt](retained/g1-window-probe.json)).

When capacity blocks the next turn, the run keeps the receipt, returns no
change and backs off. It does not manufacture tooling, waiting records or a
second mechanism to fill the time.
