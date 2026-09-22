# ot8 prompts — frozen before any design turn

Verified against source: 2026-09-20. [Cadex-new]

The ot8 charter (ADR-399, `.ouroboros/goal.md`) requires every prompt a design
turn will see to be committed before the first design turn, and it bounds the
help a design may get: **one initial product prompt plus at most three
continuations per design**, and every continuation names no specific part, no
dimension and no defect. This directory is that freeze (ADR-400).
`cli/tests/test_ot8_prompts.py` pins every file below to its digest, holds the
arm's create prompt byte-identical to ot7's — and therefore to ot6's receipt —
and refuses any other prompt here that contains a digit, a design's name, or a
part or defect word.

## The files

| file | role | bytes | sha256 |
|---|---|---|---|
| `heron.create.prompt.txt` | G2, the arm: ot7's create prompt, byte-identical | 9648 | `bcda5af55c50459968d87d4651cf0123e7f996227c6c80895365078860514e37` |
| `rebuild.prompt.txt` | G3, the biped: the first prompt on the preserved copy | 1078 | `1dbff8e3c660ddc3fffb79f3e283bd6e135d8f9caa9f8f3abc50c636788f6276` |
| `resolve.prompt.txt` | G4, the balancer: the first prompt on the preserved copy | 1612 | `016942748d359542a0b5ffdf9db0ae4e3b73b0b2ff17c0dc0c097caab01c9a3e` |
| `continue-1.prompt.txt` | first continuation, any design | 1109 | `d8faf7f15d9942d5a9cfeccf894816a664169e01c415032c9941d00cec42be6e` |
| `continue-2.prompt.txt` | second continuation, any design | 1036 | `26bb18cd1f342e65e2bd9dfd2d5d3a765b211ffaed79c3bf216d2cb8972e6348` |
| `continue-3.prompt.txt` | third and last continuation, any design | 1288 | `304e9e0412dc2296710783f296cd7758001d7bd1940a8667d26da67d3054c5c6` |

## Why the create prompt is ot7's and the continuations are not

G2 asks for "the original Heron create prompt with today's product
instructions", so `heron.create.prompt.txt` is a byte copy of ot7's, which is
a byte copy of ot6's — a changed create prompt would make the arm comparison a
comparison of two different asks. The whole difference ot8 measures on that
design is the product the same words meet.

The continuations are **not** ot7's, and that is deliberate. ot7's three
continuations direct the agent to the measured fit report and nothing else;
ot8's charter directs it to "its measured fit, **inventory** and **smoke**
evidence". The arm's open gap is exactly a gap the inventory names and the fit
report does not — ot7's arm reached zero failing fit checks with two of its
purchased parts modified out of catalog identity — so a continuation that
points only at fit cannot close it. Each ot8 continuation therefore names the
three kinds of evidence and nothing about any design, and adds the sentence
that bounds what may change (below). This difference is a reported difference,
not a hidden one: `docs/probes/ot8/REPORT.md` carries it in the arm's row.

## What the prompts may not do

All five design-agnostic prompts carry the same invariant sentence, in the
same words for every design: every purchased part stays an **unmodified
catalog part**, every other part stays a modelled printable part, nothing from
the world enters the design, nothing becomes fixed to the world that the
design declares free, no support appears that the machine does not have, and
every declared limit, task rule and rollout bound stays as the accepted design
declares it.

That sentence is the charter's "a design may fail" rule written where the
agent can read it. It is design-agnostic — it names a class of change that is
out of bounds, never a part, a number or a defect — and it is what stops the
cheap way out of a failing behaviour check: grounding a free machine, adding a
stabiliser, suppressing a joint, weakening a declared tolerance, or shortening
a declared rollout.

`resolve.prompt.txt` is the one prompt that says a behaviour check is failing,
because G4's question **is** which of two things that failure is. It names no
part, no number and no defect; it directs the agent to its own measurements;
and it gives the honest second answer an equal standing with the first —
change nothing, and state the control contract the requested behaviour would
need. A prompt that could only be satisfied by making the check pass would be
the run asking for the cheat its own charter forbids.

`rebuild.prompt.txt` asks for the one thing G3 authorises and nothing else: a
rebuild and re-acceptance of the unchanged script with the fixed engine, then
a report of what the measurements say. It forbids every edit in its own words,
and the collector holds the script identity across the turn besides.

## The limits

| design | first prompt | continuations allowed | order |
|---|---|---|---|
| G2 arm | `heron.create.prompt.txt`, in a new empty project | 3 | `continue-1`, `continue-2`, `continue-3` |
| G3 biped | `rebuild.prompt.txt`, on an independent copy of `ot7-plover-e` | 3 | the same three, in order |
| G4 balancer | `resolve.prompt.txt`, on an independent copy of `ot7-robin-c` | 3 | the same three, in order |

A continuation is spent only after a turn that reached the model and ended on
its own, and only in the order above. A design that still fails after its last
allowed continuation is a measured result, reported as such, and **never
prompted again under this freeze**. Changing any byte of any file in this
directory starts a new attempt, and every attempt is reported in
`docs/probes/ot8/REPORT.md`. The actor never edits a design: in an `ot8-*`
project every change to the script comes from a product-agent turn given one
of these prompts.
