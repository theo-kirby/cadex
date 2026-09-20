---
node_id: 2d9cb82c-cb59-5ea8-b516-e583ca21f401
slug: frosty-sea-6051
title: The geometry fallback stops reading derived artifact bytes, and ot7-plover-e opens (ADR-396)
created_at: '2026-09-20T02:38:40+00:00'
parents:
- fresh-dawn-0892
summary: ''
---
## What

**`ot7-plover-e` opens again, and with it every project an engine change to a
derived artifact had shut (ADR-396).** One keyword: `project_geometry_digest`
no longer reads a derived output's artifact bytes. An MJCF model, a training
task, a trace, a render is identified in that digest by its canonical
definition alone. `_entries` gained `derived_artifact_bytes`, true for
`project_digest` and false for the geometry digest, and nothing else moved.

**`project_digest` is untouched, and that is the shape of the change.** It is
every stored `accepted_digest` in every project on disk, it still carries those
bytes (ADR-068), and it still refuses the changed export — the frozen-digest
test pins it to the value it had before the material moved into this module.
The geometry digest is consulted only *after* the byte digest has already said
no, and only to answer one question: is the disagreement the serialization or
the model?

**The measurement.** On a fresh copy first, then on the project itself,
`open_project(restore=True)` returns **`ok: true` in 89.5 s** with
`matched_by: "geometry"` and `matches_accepted: true`. The byte digests are the
same two numbers that refused before — accepted `a00d1aea…`, restored
`9ef44502…` — and the geometry digests now agree at `8c09313f…` on both sides,
where before they were `a4c4cc28…` against `bb33c420…`. The accepted pin,
digest and revision are unchanged; the only state written is the learned
`accepted_geometry`, keyed on the unchanged accepted digest, and a second open
of the copy reproduced `ok: true` at 89.3 s through that remembered value.
**F7's `continue-2` and `continue-3` are spendable again** — a design turn
opens with `restore=True`, which is exactly what this project refused before a
provider session could exist.

**F9's one exception is closed.** The three retained ot6 copies, re-measured
under the ADR-396 engine with `cadex clearance` before and after a full
`open_project` restore: **406/44, 276/39 and 105/20**, with the same
clear/intersection/below breakdowns (362/12/32, 237/8/31, 85/6/14) as every
previous reading, accepted pins preserved, restores at 7.387 / 5.249 / 2.410 s,
and each `docs/clearance.md` **byte-identical** across its restore. All three
still match on bytes alone, so the fallback is never consulted for them.

Landed: the `_entries` keyword and the two docstrings, ADR-396, two engine
tests, `docs/INTEGRATION.md`'s restore paragraph, the `CadexGeometryDigest.py`
row in `docs/ARCHITECTURE.md`, a DIGEST-DRIFT.md bullet, REGRESSION.md and
REPORT.md sections, and the 5.0 KB receipt
`docs/probes/ot7/retained/adr396-reopen.json`. Commit `2750995d`.

## Why

The critic's message named this unit exactly, down to the mechanism: make the
ADR-389 geometry fallback ignore derived non-BREP artifact bytes in
`project_geometry_digest`'s `_entries`, leaving `project_digest` alone; ship a
fixture that fails on today's code; ADR it; update the digest's doc; run
`test-engine` plus the packaged gate; then re-open `ot7-plover-e` for real and
confirm the three ot6 copies still report 406/44, 276/39 and 105/20. All of
that was done, in that order, with no deviation.

Frontier: `forest-wind-0342` (the engine) carries the defect and the fix;
`mild-ledge-7157` (the ot7 charter) through F9, whose single measured exception
this closes; `rapid-grove-9687` (F7), whose two slots this makes spendable.

## Method

**The fixture before the fix.** `test_the_geometry_digest_forgives_a_re_exported_derived_artifact`
builds the plover shape in miniature: a design carrying an MJCF-like derived
artifact and a training task whose artifact pins the model's digest and byte
count, both re-written with every canonical definition, BREP fingerprint and
solved placement held fixed. It asserts the byte digest moves *and* the
geometry digest does not. Run against the pre-ADR-396 code it fails on exactly
the second assertion, `f2a18809…` against `8fb6de5c…`; the other nineteen pass.

`test_the_geometry_digest_still_sees_every_non_brep_output` asserted the
opposite of the new behaviour, so it was replaced rather than deleted:
`..._still_sees_every_non_brep_definition` keeps the three facts that still
hold — the derived output's recipe, its solved placement, and a mesh's vertex
set each move the digest. That is the guard the change must not weaken, and
naming it in a test is cheaper than trusting the argument.

**The measurement on a copy before the project.** `ot7-plover-e` was copied
without its `evidence/`, `agent.json` or git repository to
`ot7-plover-e-adr396`, and the committed `reexport_smoke.py restore` — the same
tool and the same `open_project` path iteration 170 used to record the refusal —
was run there twice before it was run on the project. The control is iteration
170's own receipt: the same tool, the same copy procedure, the same 89.4 s, and
`CADEXD_RESTORE_FAILED`. The ot6 half used `cadex clearance` for the published
read and the same restore probe for the rebuild, and compared the two
`clearance.md` files byte-for-byte rather than only their counts.

Verification: `pixi run test-engine` **2196 passed, 53 skipped in 295.61 s**
(2195 before, plus this unit's fixture); `pixi run build-engine` +
`stage-engine`, then the packaged gate
`CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest
test_cadexd_lifecycle.py` **23 passed in 18.19 s**; `pixi run python -m pytest
cli/tests` **855 passed, 1 skipped in 551.66 s**, unchanged, since no CLI code
moved. One build, as the charter allows.

## Result

**The engine node is working again on this axis, and F9's single exception is
gone.** Every project the byte digest refuses for a derived-artifact reason now
gets a second opinion that measures the model instead of the export; every
project it refuses for a design reason still fails, on a definition, before any
measurement is consulted.

**What this deliberately does not guard, stated plainly.** After this change,
the geometry fallback cannot tell two derived artifacts apart when their
definitions, BREP shapes and solved placements all match. That is the intended
trade: such a difference can only come from the engine, and forgiving the
engine version is what this digest exists for. The byte digest still sees it,
still refuses, and is still the accepted-state guard, so no accepted state is
re-blessed by this path.

**Assumption recorded.** Opening `ot7-plover-e` for real writes two things: a
rebuilt attempt (`attempt-1789871019450-44998a90b73d`) and the learned
`accepted_geometry`. Neither is a design edit — the script, the parameters, the
accepted revision `0491ead7…` and the accepted digest `a00d1aea…` are all
unchanged, and `accepted_pin_preserved` is true. The charter's
no-actor-design-edits rule is intact.

**Next.** F7's `continue-2` is dispatchable for the first time since iteration
167, subject to the product-agent window gate. F10 after F7 is exhausted or its
slots are spent.

No new dependency. The unreconciled tail is two records deep after this one, so
a reconcile is due within one more unit under the charter's
every-five-or-three rule.

Dispatch closed: 1 unit — the ADR-389 geometry fallback stops reading derived
artifact bytes, so `ot7-plover-e` opens again at `matched_by: "geometry"` with
its accepted pin untouched, F9's one exception closes with the ot6 copies
re-measured at 406/44, 276/39 and 105/20, and F7's two slots are spendable
(ADR-396).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 2750995d191c96348b6d921e85cf58cefa8bc61d

## State Impact

- target: forest-wind-0342 — The ADR-389 geometry fallback no longer reads a derived output's artifact bytes (ADR-396, commit 2750995d): project_geometry_digest identifies an MJCF model, training task, trace or render by its canonical definition alone, while project_digest still carries those bytes and still refuses. A project accepted before an engine change to a derived artifact reopens again: ot7-plover-e returns ok:true in 89.5 s with matched_by geometry, accepted digest a00d1aea and pin unchanged, against iteration 170's CADEXD_RESTORE_FAILED control. test-engine 2196 passed 53 skipped; packaged gate 23 passed on a freshly staged payload; cli/tests 855 passed 1 skipped.
- target: mild-ledge-7157 — F9's one measured exception is closed: no retained project is shut by ADR-393 any more. The three ot6 copies re-measured under the ADR-396 engine report 406/44, 276/39 and 105/20 with unchanged clear/intersection/below breakdowns, accepted pins preserved, restores matching on bytes alone at 7.387/5.249/2.410 s, and each docs/clearance.md byte-identical before and after its full open_project restore.
- target: rapid-grove-9687 — F7's continue-2 and continue-3 are spendable again: ot7-plover-e opens with restore=True, which is the precondition a design turn needs. No slot was spent in this unit and no design was edited; the accepted revision 0491ead7 and digest a00d1aea are unchanged.
