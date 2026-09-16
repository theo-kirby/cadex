---
node_id: 846d7bc5-0497-5d13-a70b-dbc2c6f2da43
slug: winter-key-1482
title: F2. Fit intent is declared and checked
created_at: '2026-09-14T17:28:04+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: working

## Current

**A weld and a declared running gap on the same pair are now themselves a failing check (ADR-379) — the checker's fifth finding [rec: glad-wing-9845].** A `clearances=` declaration on a pair an **unsuppressed** `fixed` joint welds fails as `clearance under weld` at any measured gap: the declared minimum is not consulted, because no measurement makes "one rigid body" and "a running gap" both true, so the pair fails below its minimum and above it alike. The engine publishes the welding joints on that declaration (`{"kind": "clearance", "minimum_mm": …, "joints": [...]}`) so a reader reaches the same verdict; `pair_status`, the `fit` block's note, `cadex clearance` and the review's offending pairs all carry it, and the note names the two repairs — close the gap and declare the pair with `contacts=`, or stop welding two components meant to stay apart. Removing only the declaration is not a repair: it leaves the gap, reported by ADR-370's `fit.attachments` rather than hidden behind a passing check. A `contacts=` declaration on a welded pair agrees with the joint and is unchanged; a suppressed weld raises no contradiction. Reported, never refused. This **narrows ADR-372's "an explicit declaration still wins"** — the hatch that let ot6's floating-horn defect survive F4's whole four-turn repair (`polished-forest-0215`). Evidence: the real-OCCT fixture in `test_fit_intent.py` was already Heron's shape and asserted `fit_failures == []`; it now asserts `['clearance under weld']`. Eight parametrised engine cases cover 0.0, 0.02 and 0.2 mm, an overlap, a suppressed weld and a contact declaration; nine tests are red on the old code. Engine 2,160 passed / 53 skipped, CLI 823 passed / 1 skipped, packaged lifecycle 21 passed; `build-engine` and `stage-engine` exit 0 with the line present in the staged worker. No new op, no `OP_ARG_SPECS` change, no `shell/` diff. **No retained number moves**: replayed over the twenty `clearance.json` receipts in the operator's `ot7-*` projects it fires on zero rows, because no accepted revision was built by an engine that published `joints` on a clearance intent, and `test_adr_379_moves_no_retained_number` pins that on the three committed receipts [rec: glad-wing-9845].

**The nominal-minimum rounding defect is fixed (ADR-353).** Retained Heron measurements at 0.09999999999999952 and 0.09999999999999039 mm exposed two false failures at the 0.1 mm minimum [rec: lucky-willow-8039]. Engine and CLI declared/default minima, including CLI overrides, now allow an absolute 1e-9 mm deficit. Raw measurements, overlap/contact thresholds and advisory acceptance remain unchanged. Known-answer regressions fail on the old comparisons; real OCCT static/swept-minimum fixtures preserve extrema and CLI serialization. Production sweeps still publish raw extrema, not new threshold verdicts. Only those two Heron flags disappear; 0.0999 and 0.05 mm gaps still fail. Retain `working` [rec: hidden-lodge-4550].

**F2's static fit intent and known-answer evidence are present (ADR-347), pending the owner's checkbox.** `assembly.assembly(contacts=..., clearances=...)` declares named contact pairs and minimum-clearance triples; `assembly.component(world=True)` marks environment solids. Published exact-solid measurements report overlaps, missed contact, insufficient declared/default gaps and unknown measurements. Collision planes, planar CAD faces and explicitly marked world components yield separate world-geometry findings. CLI build replies, clearance reports and API descriptions expose this advisory contract; failing fit still accepts, and accepted identity survives reopen. Legacy calls omit the new definition keys [rec: crisp-ember-0302].

Real-OCCT fixtures reproduce Heron's 248.2 mm³ buried servo tab, 0.2 mm missed horn contact and collision plane, plus rotated planar geometry, touching pairs and declared/default gap failures. `docs/XSCRIPT.md` documents the API; `docs/probes/ot7/FIT-INTENT.md` carries receipts. Engine: 2,117 passed/53 skipped; packaged lifecycle: 16 passed; packaged fit transaction: 1 passed. The full CLI telemetry failure and passing isolated retry remain recorded under F9 [rec: crisp-ember-0302].

Charter criterion: **F2. Fit intent is declared and checked.** The script API declares intended contact and intended clearance, with a minimum, between named components. The checker reports four things: any overlap on any pair, a declared contact that is not touching within tolerance, a declared clearance below its minimum, and an undeclared pair closer than the default minimum. World geometry in a design, a floor or bench plane, is reported as its own failure. Nothing is refused at acceptance. Evidence: engine tests on fixtures that reproduce Heron's three ot6 defects, each reported with the right pair and number; `docs/XSCRIPT.md` documents the declarations. Declared target `gap-f2-fit-intent-declared-checked`; a record may say "ticks F2" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609]. ADR-379's `clearance under weld` is a **fifth** finding beyond the charter's four, and it is what makes the third of those four honest rather than satisfiable by contradiction [rec: glad-wing-9845].

Reconcile judgement: `working`, unchanged. ADR-379 is a behaviour change to what "zero failing fit checks" means, landed deliberately before F6 and F7 run so their bars are judged under it; F4's and F5's exhausted results were judged under the older rule and stand as measured [rec: glad-wing-9845].

## Negative knowledge

- [scope: static world-geometry detection | confidence: high | evidence: crisp-ember-0302] A solid bench cannot be distinguished from a printable base by shape alone, so environment solids require `world=True`; grounding alone is not evidence of world geometry. Confidence: high within this API's stated contract. Contact tolerance is 0.001 mm, default gap 0.1 mm and overlap tolerance 1e-6 mm³ [rec: crisp-ember-0302].
- [scope: a `clearances=` declaration on a pair an unsuppressed `fixed` joint welds | confidence: high | evidence: glad-wing-9845] The declared minimum does not make the pair legal, and no measured gap satisfies both statements. Since ADR-379 the declaration is itself the failing check (`clearance under weld`) and the minimum is not consulted at all. Deleting the declaration is not the repair either — it uncovers the gap in `fit.attachments`.

## Provenance

- kind-dusk-1609 — ot7 directive declared the F2 criterion
- crisp-ember-0302 — static fit intent, real-kernel fixtures, advisory acceptance/reopen and verification limits

- lucky-willow-8039 — retained Heron exposed two strict-minimum rounding false positives
- hidden-lodge-4550 — ADR-353 absolute minimum-clearance slack, unchanged measurements, static/swept-minimum regressions and corrected retained verdicts
- glad-wing-9845 — ADR-379: a weld and a declared running gap on the same pair contradict each other and fail as `clearance under weld`; narrows ADR-372, moves no retained number
