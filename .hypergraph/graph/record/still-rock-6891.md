---
node_id: 812b5cde-aa59-5703-bb26-34a029be3a05
slug: still-rock-6891
title: A modified purchase says what it was cut from (ADR-381)
created_at: '2026-09-17T00:15:37+00:00'
parents:
- terse-chart-0277
summary: ''
---
## What

ADR-381 (commit `d6ff4e31`): the engine names the catalog body a *modified*
purchased part was cut from, and both readers carry it.

- `_stamp_catalog_identity` (`cadex_project_worker.py`) stamps
  `catalog_derived_from` on an output that matched no catalog definition
  exactly but whose **base operand spine** holds one — `arguments[0]`
  followed down from the definition, through the single list
  `part.fuse([a, b])` passes, nearest match wins. Positional by design:
  `part.cut(base, tools)` puts the modified body first, so a catalog body on
  the spine is what the output *is*, while one reachable only as a tool is a
  clearance cutter and implies no purchase — the distinction the CLI's design
  instructions have drawn in words since ADR-243's follow-up and nothing
  measured. Written beside the definition like `catalog` itself, so no
  content digest moves.
- `inspect scope=inventory` carries it per component row and as a top-level
  `derived_catalog_sources` roll-up (`{"source_output", "family",
  "part_number"}`, sorted), so a reader that pages the component list need
  not page it to learn this.
- The build reply's advisory `inventory` block repeats it, empty list rather
  than missing key, with each row in its `note` — "servo_drilled (cut from
  servo/MG90S)" — and the repair the prompt already asks for. The system
  prompt gains one clause. `cadex inventory`'s table reads *cut from servo
  `MG90S`* instead of an em dash.
- Advisory throughout: no verdict, no refusal, no fit count moves. ADR-243's
  boundary stands off the spine (a catalog body fused in as a second operand
  is still not identified).

## Why

The criterion this advances is **F5/F6/F7's one shared unmet count, catalog
hardware for every purchased part** — F5's only failing count of six after
four turns, and the count Robin and Plover will be judged on when capacity
returns. ADR-362 put the uncatalogued list in the reply; it could not say
which name was a printed part and which was a purchased part the script had
cut. That is the specific blind spot F5 measured, and it is now closed with a
measurement rather than with another rule.

**What the critic asked, and what I did instead.** The critic asked first for
a reconcile of `terse-chart-0277` into four state nodes and a view
regeneration. This dispatch forbids reconcile in a work iteration with no
exceptions (the skill, `hypergraph update`, `new state`, `views add`, editing
`.hypergraph/graph/state/` or STATE.md), so I did not do it; the fold is still
owed and is the first thing a reconcile pass should take. The critic's second
instruction — pick a criterion and do the smallest thing that moves it, not
another attachment rule, capacity-probe cycle or waiting record — is what this
unit follows. This is not an attachment or fit rule: it adds no check and no
status.

**Availability, checked once before choosing.** `run.py window --model
claude-fable-5` at 23:53 UTC: refused in 1.667 s, exit 1, `room: false`,
`rate_limit_type seven_day_overage_included` at 100 %, `disabled_reason
org_level_disabled`, HTTP 429, "You've reached your Fable limit". No slot
spent, no prompt sent. So F6 could not be dispatched and I did not dispatch
it; the reading is not written into the report, per the standing instruction
to record only a *changed* reading.

**One line per criterion, as the critic asked.** F1, F2, F3, F8, F9: evidence
complete, waiting on the owner's checkbox — nothing an actor can add. F4, F5:
exhausted, all slots reached the model, measured results that stand. F6, F7:
blocked on an organisation-level provider setting on `claude-fable-5`, all
eight slots unspent, unblockable only by the owner or an unrefused probe. F10:
cannot be claimed while F6/F7 have unspent slots, by the charter's own
exhaustion policy. That is why this unit went to the product rather than to a
criterion's own evidence.

## Method

Read the F5 state node for the measured failure, then the producer: catalog
identity is resolved by canonical definition (`library_catalog_identity`), and
`DomainValue.to_payload()` nests an argument's whole payload, so a cut's
definition physically contains its base's definition and the join already
exists. Confirmed `part.cut`'s signature puts `base` at `arguments[0]` and
`fuse` passes one list, which is what the spine walk is written against.

Eight engine cases in `test_inventory_scope.py`: a drilled catalog body
named; the same body used *only* as a cutter not named; the nearest ancestor
winning through a transform; the `fuse` list read positionally in both orders;
the definition the digest hashes unmoved; the inventory join reporting one
derived source beside one printed part; the component row carrying it. Seven
are red on the old code (verified by stashing the two source files). The
eighth is a **real FreeCADCmd run**: one `lib.bolt("M3", 12)` drilled through
and placed, the same bolt cutting a clearance hole in a printed plate, and the
engine reports exactly one derived row for `bolt_drilled`. That one was
checked by deliberately mis-pinning the part number and watching it fail, so
it is asserting the live engine's answer and not a fixture's.

CLI: `test_inventory.py` pins the block and the rendered document,
`test_mcp_protocol.py` pins the whole path to the model on the F5 fixture
itself (the drilled servo placed twice). `fake_cadexd.inventory_value` learned
the key so the fake engine and the real one agree.

Verification: `pixi run test-engine` 2,168 passed / 53 skipped (275.95 s);
`pixi run python -m pytest cli/tests` 830 passed / 1 skipped (531.46 s);
`pixi run build-engine` and `stage-engine` clean; packaged gate
`CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest
test_cadexd_lifecycle.py` 21 passed. `docs/CLI.md`, `docs/INTEGRATION.md` and
`docs/DECISIONS.md` moved in the same commit.

## Result

The published inventory now distinguishes a printed part from a purchased
part the script modified, everywhere the agent reads it: the build reply's
`inventory` block, `inspect scope=inventory`, and the project's
`docs/inventory.md`. That is the **fourteenth** product change F6 and F7 will
run on, and the first that reaches F5's own failing count with a measurement
rather than with prose. Nothing is refused and no existing project's digest or
fit numbers move.

Concerns and assumptions the next iteration must know:

- **The rule is positional and deliberately narrow.** A catalog body fused in
  as a second operand, or used as a tool, is still unnamed (ADR-243's
  boundary). If a design modifies hardware some other way, this reports
  nothing rather than something wrong — silence here is not proof of catalog
  identity, and the ADR says so.
- **It is advisory.** Whether a cut catalog body counts as "catalog hardware
  for every purchased part" remains the owner's call on F5's tick. This does
  not re-open F5, which is exhausted and whose result stands as measured.
- **The reconcile fold of `terse-chart-0277` is still owed**, now with this
  record behind it; the tail is two nodes deep.
- **F6/F7 remain blocked** on the org-level `claude-fable-5` refusal, 21st
  consecutive refusal at 23:53 UTC on 2026-09-16, all eight slots unspent.
  Only an unrefused probe, or the owner enabling usage credits for the
  organisation, changes that.

Dispatch closed: 1 unit — ADR-381, the engine names the catalog body a
modified purchased part was cut from, closing F5's measured blind spot for F6
and F7; F6 probed and still refused, nothing dispatched, no slot spent.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: d6ff4e31b47ca2bce7e088cf0522a6d12cfef98e

## State Impact

- target: stormy-aspen-5433 — F5's one failing count, catalog hardware for every purchased part, now has a producer: the engine names the catalog body a modified output was cut from (catalog_derived_from / derived_catalog_sources, ADR-381), so the reply distinguishes a printed part from a modified purchase. F5 itself is unchanged and stays exhausted.
- target: narrow-dune-9454 — the product F6 will run on is now fourteen changes newer than F5's, ADR-381 being the first to reach F5's own failing count; the 21st window probe at 23:53 UTC was refused (org_level_disabled, 100% seven_day_overage_included), no slot spent, all four slots unspent
- target: rapid-grove-9687 — same: F7 unspent and blocked behind F6, and will run on the ADR-381 product
- target: chilly-union-8972 — cadex inventory's document and the build reply's inventory block carry derived_catalog_sources and per-row catalog_derived_from (ADR-381); docs/CLI.md documents both
