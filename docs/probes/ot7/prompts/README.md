# ot7 prompts — frozen before any design turn

Verified against source: 2026-09-14. [Cadex-new]

The ot7 charter (ADR-341, `.ouroboros/goal.md`) requires every prompt a design
turn will see to be committed before the first design turn, and it bounds the
help a design may get: at most three continuation prompts per design, none of
which names a part, a number or a defect. This directory is that freeze
(ADR-345). `cli/tests/test_ot7_prompts.py` pins every file below to its digest,
holds the two ot6 create prompts byte-identical to their ot6 receipts, and
refuses a continuation or repair prompt that contains a digit, a design's
name, or a part or defect word.

## The files

| file | role | bytes | sha256 |
|---|---|---|---|
| `heron.create.prompt.txt` | F5, the arm: Heron's ot6 create prompt, unchanged | 9648 | `bcda5af55c50459968d87d4651cf0123e7f996227c6c80895365078860514e37` |
| `robin.create.prompt.txt` | F6, the balancer: Robin's ot6 create prompt, unchanged | 7650 | `e20ee7abe5818015182693a2d950b84fc62da67868d2ee42cec748ca2299329b` |
| `plover.create.prompt.txt` | F7, the biped: new in this run | 9303 | `b95f98b77ba7180140d873e3615a24a0802e9645671664c2e7277c465d8457aa` |
| `continue-1.prompt.txt` | first continuation, any design | 756 | `80d725d2961e7ca44a56fed391745d6df551741c6545a837e815ca3ae0b7f4d0` |
| `continue-2.prompt.txt` | second continuation, any design | 611 | `9a78ff9d417594db72696e1de98311b2aee05470043f496307e0a1d9b0334a78` |
| `continue-3.prompt.txt` | third and last continuation, any design | 732 | `0814d73f6874e009adfe55cb4d038a22b6632af4033fb275c5021d6a1d500e88` |
| `repair.prompt.txt` | F4, the seeded repair: the one continuation | 830 | `5d846901563ddef8b278a88f46e9ccfcd1a372f1e38b475743372c20cdcb4904` |

**Provenance of the two ot6 prompts.** Heron's digest is
`turns[0].prompt_sha256` in `docs/probes/ot6/heron/design.json`, and the bytes
are the retained `create.prompt.txt` under the operator's `ot6-heron-src`
directory. Robin's is a byte-for-byte copy of
`docs/probes/ot6/robin/create.prompt.txt`, whose digest the retained
`ot6-robin-src` copy shares. Neither was edited: the charter names "Heron's
ot6 create prompt" and "Robin's ot6 create prompt", and a changed create
prompt would make the ot6 comparison in the closing report a comparison of two
different asks.

Both ot6 prompts still say "verify ... through inspect facts and the script's
own stdout". That is deliberate and it is the point of the run: F1 changes what
the agent's tools return and what its system prompt tells it, not what the
user asked for, and F5 and F6 measure whether the product now makes the same
ask fit.

## The biped prompt

Plover is written to the charter's F7 line and in Heron's shape, because Heron
is the ot6 prompt the product agent designed from and the one whose joint
module Finch already proved buildable by hand: four `lib.servo("mg90s")`, hip
and knee pitch per leg, every joint the same servo-on-parent, horn-on-child,
bearing-opposite module with the catalog `single_arm` horn, `mr128` bearing,
`m2x6` tab screws and `m2x16` centre screws; five modelled printable parts
(pelvis, two thighs, two shins with integral soles); the pelvis as the free
base with nothing grounded; no floor, bench or plane in the design, the soles
on the environment's plane; declared hip and knee limits, which is what the
swept check (F3) reads; servo position actuators; a standing task with a
declared fall termination and a small reset variation, which is what the smoke
rollout (F8) holds; and a verification paragraph that names the measured fit
checks the tools report as the evidence, never the printout. Its name is a
bird, as every design in this project's lineage has been, and it belongs to no
earlier project.

## The continuation prompts

The three continuation prompts and the repair prompt are design-agnostic by
construction: they name no part, no number and no defect, and they ask the
agent to read the measured fit report, static and swept, and resolve every
failing check through normal acceptance. The test enforces the vocabulary:
no digit; none of `heron`, `robin`, `finch`, `plover`, `lark`, `wren`; and none
of the part and defect words `servo`, `horn`, `bearing`, `screw`, `bolt`,
`insert`, `cheek`, `tab`, `stub`, `window`, `pocket`, `slot`, `spline`,
`plane`, `floor`, `bench`, `wall`, `stage`, `overlap`, `intersect`, `gap`,
`distance`, `volume`, `mm`, `degree`, `angle`.

## The limits

| attempt | create prompt | continuations allowed | order |
|---|---|---|---|
| F5 arm | `heron.create.prompt.txt` | 3 | `continue-1`, `continue-2`, `continue-3` |
| F6 balancer | `robin.create.prompt.txt` | 3 | the same three, in order |
| F7 biped | `plover.create.prompt.txt` | 3 | the same three, in order |
| F4 seeded repair | none: the project is a copy of `ot6-heron` at revision `7e9eff5c…` | 1 | `repair.prompt.txt` |

A continuation is spent only after a turn that built and accepted with failing
fit checks still reported, and only in the order above. A design that still
fails after its last allowed continuation is a measured result, reported as
such, never prompted again under this freeze. Changing any byte of any file in
this directory starts a new attempt, and every attempt is reported in
`docs/probes/ot7/REPORT.md`. The actor never edits a design: in an `ot7-*`
project every change to the script comes from a product-agent turn given one
of these prompts.
