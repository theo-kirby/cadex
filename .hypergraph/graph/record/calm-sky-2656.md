---
node_id: 8aab1c79-30e9-5ff6-bb52-9cec4e6425b2
slug: calm-sky-2656
title: Linked-part cold restore holds with its source project absent
created_at: '2026-09-08T08:38:33+00:00'
parents:
- sleepy-meadow-2615
summary: ''
---
## What

Qualified linked-part source independence through four fresh ordinary CLI processes against the existing staged engine. A consumer cold-opens, rebuilds and exports its exact solid with its source project's recorded path absent. No product code changed.

## Why

Execute the refreshed short unit selected by [rec: sleepy-meadow-2615], serving missions 1 and 2 and maintaining charter criteria **File lifecycle** and **The walk exists and is tested headlessly**. The embedded overseer routing request has already been satisfied: git history contains maintainer commits ad90c3f8/3ce033b1 followed by planner 21b0c4b2; STATE is reconciled through empty-ledge-4581 and PLAN through sleepy-meadow-2615. Therefore follow the refreshed plan without another maintainer pass, contributor consent audit or Save-As qualification.

Existing container test test_a_container_still_reads_with_the_source_project_gone removes the source and reads container bytes, but uses a synthetic BREP fixture. The live test cold-reopens the consumer while the source remains present. Neither establishes the full source-absent real-kernel transition. ADR-138 explicitly makes the source path a hint; this experiment measures that existing promise without inventing a repair service. No criterion is reopened or newly declared complete.

## Method

At HEAD 21b0c4b2, read STATE, PLAN, the actor/record skills, Hypergraph contract, VISION, ADR-138 and its original evidence [rec: ancient-current-9419], docs/CLI.md link/export/envelope contracts, command_link/command_export, and linked-part CLI/container/live tests. The initial guessed ProjectStore and worker-test filenames were absent; actual CLI command definitions and accepted worker result.json supplied the paths used. No optional tags vocabulary exists.

Use unchanged build/engine/cadex-engine-0.0.0-macos-arm64. Create an external disposable parent T containing source.py, consumer.py and fresh projects A/B. Ordinary CLI initializes each project's Git repository and ARCHITECTURE.md, DECISIONS.md, PROGRESS.md. Exact scripts:

```python
# source.py
result = {"block": part.box(10, 20, 3)}
# consumer.py
result = {"block": part.import_part("block.cxpart")}
```

Each command is a separate subprocess, timeout 120 seconds, with --engine "$E" --json:

1. `./cadex script --set "$T/source.py" --project "$T/A"`
2. `./cadex link --from "$T/A" --output block --project "$T/B"`
3. `./cadex script --set "$T/consumer.py" --project "$T/B" --out "$T/before" --format brep`
4. After all three clients exit, rename only A to A-away. Assert the .cxpart header's source.project_root resolves to original A and that path is absent. Run `./cadex export --project "$T/B" --out "$T/after" --format brep` in a fresh process. Assert A remains absent until completion, then restore A in finally.

Read script.json and the result.json at its accepted_attempt.staging before/after (read-only); compare accepted revision/digest/contract/working revision, all output facts and linked bytes. Require a different accepted attempt after export, an actual BREP output, and identical exported BREP bytes. Assert ARCHITECTURE.md and DECISIONS.md byte equality; require PROGRESS.md to preserve its full old prefix, allowing the ordinary export row. No manual metadata changes. Stdout/stderr and before/after snapshots remain external temporary evidence; this record preserves commands, sources, identities and substantive results without committing machine paths.

Run `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 pixi run python -m pytest cli/tests/test_linked_part.py src/Mod/cadex/cadex_tests/test_linked_part_container.py -q`.

## Result

Four CLI exits **0, 0, 0, 0**, no error/failure code, all comparison assertions passed. Focused suite **25 passed in 4.29s**, zero skips.

- Source accepted revision: `f860cab9a5c2cda209eca4a39f6e00b1e45937c57c9c2c9065ff81bd81885ee9`.
- Consumer accepted/working revision before and after: `5d8d22c7feb7e1f5feca8de03af108b1ae1977e33ab4317e83182c43de531111`.
- Source and consumer accepted digest: `468055de965817ad47a89d877922ba743a724a30a9d0f1be4851935e0b3f16d4`; consumer unchanged through cold restore/export.
- Consumer linked asset SHA-256 before/after: `ad504381e4fef42726fc7beac350f7c208453f3eeceecaed8167deb8fcb55afa`. This container includes disposable source-path provenance, so another fixture root changes the container hash without changing the solid.
- Exported BREP SHA-256 before/after: `d5cdd1dc05e6413de6abe4047583ad7a99c99a623486f38e5886ba765ac65efe`.
- Both accepted worker attempts report a valid Solid, one solid, six faces, volume `599.9999999999999` mm3, bounds [0,0,0] to [10,20,3] mm. Complete facts dictionaries match, not just these summary fields. The accepted attempt changes while its revision/digest and part-solid contract remain fixed.
- Protected docs remain identical; PROGRESS.md preserves all prior content and adds one ordinary export row at the same revision/digest. Disposable A's original name is restored.

The immutable snapshot contract holds for this fixture. No mismatch warrants conditional short unit 2. Next: return to separate planning; do not repeat this qualification or expand into refresh/path-repair/catalog-identity work. Completed lifecycle criterion evidence stands and no missing walk leg is identified. This bounded standing-maintenance unit cannot tick a new charter box. No behavior/doc/scaffold change, removal ADR or ROADMAP feature checkbox applies.

Only a record is changed: no full build, full CLI/engine suite, packaged lifecycle suite, training, provider, GUI, remote dispatch or stage refresh is claimed. The real staged four-process experiment and focused tests are the evidence; hypergraph export/check and git diff --check are the recording gate. Tail becomes two records including this one; a separate maintainer owns reconciliation.

Dispatch closed: 1 unit — linked consumer cold restore and exact-solid export hold with the source path absent; no corrective product unit warranted.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 21b0c4b290a90f1caea286bdcb632432790fc347

## State Impact

- target: simple-willow-8989 — Linked consumer cold restore/export preserves accepted identity, exact solid, asset bytes and project docs with source path absent
- target: chilly-union-8972 — Four staged CLI processes qualify source-independent linked-part export; 25 focused linked-part tests pass
- target: calm-peak-5247 — Standing lifecycle qualification finds no missing walk leg; linked-part conditional correction not warranted, return to separate planning
