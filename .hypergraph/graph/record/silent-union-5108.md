---
node_id: ea46cc15-2b3f-5a32-8968-458dcc1cc929
slug: silent-union-5108
title: 'ot7 prompt freeze recorded after the fact: Heron, Robin, Plover create prompts, three continuations and the repair prompt pinned by digest (ADR-345)'
created_at: '2026-09-14T17:49:45+00:00'
parents:
- kind-dusk-1609
summary: ''
---
## What

Recovered record for commit `a024283af6` (ouroboros #2, "no record"): the ot7 prompt freeze (ADR-345). Every prompt a design turn may see in run ot7 is committed under `docs/probes/ot7/prompts/` before any design turn: Heron's and Robin's ot6 create prompts byte-identical to their ot6 receipts (F5, F6), a new biped create prompt, Plover (F7), three design-agnostic continuation prompts and one seeded-repair prompt (F4), each pinned by size and sha256 in the directory README and enforced by `cli/tests/test_ot7_prompts.py`, which also refuses a continuation or repair prompt containing a digit, a design name, or any of the ot6 part and defect words.

## Why

Iteration 2 committed the freeze but stopped without minting a record and without the full CLI suite result; the critic asked iteration 3 to recover both before starting F1. The freeze is the horizon ladder's rung 0 and a charter constraint ("Prompts are frozen ... committed before the first design turn"), so it advances F5, F6 and F7 without closing any of them: no design turn has run, and the prompts are the asks those criteria will be measured against. It also fixes the F4 repair prompt. This record carries no design evidence and claims none. Iteration 2's transcript mentioned folding the stale plan; that was not executed and is not claimed here.

## Method

- Files: `docs/probes/ot7/prompts/{heron,robin,plover}.create.prompt.txt`, `continue-{1,2,3}.prompt.txt`, `repair.prompt.txt`, `README.md`; `cli/tests/test_ot7_prompts.py`; ADR-345 in `docs/DECISIONS.md`.
- Heron's digest `bcda5af5…14e37` is `turns[0].prompt_sha256` in `docs/probes/ot6/heron/design.json`; Robin's `e20ee7ab…329b` is a byte copy of `docs/probes/ot6/robin/create.prompt.txt`. Plover is new, written in Heron's shape to the F7 line: four `lib.servo("mg90s")`, hip and knee pitch per leg, catalog horn, bearing and fasteners, five printable parts, a free base, no world geometry, declared joint limits, a standing task.
- Limits: three continuations per design in a fixed order, one repair prompt for F4; a changed byte is a new attempt; the actor never edits a design.
- Verification recovered by iteration 3: the five focused tests in `test_ot7_prompts.py` passed in iteration 2; the full CLI suite was run by iteration 3 on the `a024283af6` tree — result below.

## Result

The freeze exists and is test-pinned. F5, F6 and F7 each have their create prompt and continuation budget fixed; F4 has its one repair prompt. No design turn has been taken; nothing in F4–F7 is closed by this.

CLI suite on the `a024283af6` tree: `pixi run python -m pytest cli/tests -q -x` → 624 passed, 1 skipped in 520.71 s, exit 0 (the skip is the pre-existing environment-gated test).

Engine suite on the same tree (run by iteration 3 alongside its own F1 verification): `pixi run test-engine` → 1 failed, 2114 passed, 53 skipped. The one failure was this commit's: `test_licensing_compliance.py::test_every_source_file_declares_the_right_license` found `cli/tests/test_ot7_prompts.py` without its SPDX header. Iteration 3 added the two header lines (no other change to the file; the prompt digests are untouched) and the licensing test and the freeze test are green again.

Caveat on that run: it was started on the `a024283af6` tree and iteration 3's F1 edits under `cli/cadex_cli/` landed while it was running. Test modules were imported at collection, so in-process code was the committed version; any subprocess-spawned CLI in a late test saw the working tree. The F1 record that follows carries a clean full-suite run on its own tree.

Assumption recorded: the biped prompt is the actor's authorship (a create prompt, not a design edit), which the charter's first-unit instruction asks for explicitly.

Dispatch closed: 1 unit — the ot7 prompt freeze (ADR-345), recorded after the fact with its suite result.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: a024283af616445524e2ae4c882d00d6f0b7a4e5

## State Impact

- target: stormy-aspen-5433 — F5's create prompt is Heron's ot6 prompt, frozen at docs/probes/ot7/prompts/heron.create.prompt.txt (sha256 bcda5af5…) with three ordered continuation prompts; no design turn taken yet
- target: narrow-dune-9454 — F6's create prompt is Robin's ot6 prompt, frozen at docs/probes/ot7/prompts/robin.create.prompt.txt (sha256 e20ee7ab…) with the same three continuations; no design turn taken yet
- target: rapid-grove-9687 — F7's biped prompt, Plover, is written and frozen at docs/probes/ot7/prompts/plover.create.prompt.txt (sha256 b95f98b7…): four MG90S, hip and knee pitch per leg, catalog hardware, five printable parts, free base, no world geometry; no design turn taken yet
- target: polished-forest-0215 — F4's single repair prompt is frozen at docs/probes/ot7/prompts/repair.prompt.txt (sha256 5d846901…), design-agnostic by test; the seeded copy of ot6-heron at 7e9eff5c… is not yet made
