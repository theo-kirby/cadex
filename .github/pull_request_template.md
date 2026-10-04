<!--
One logical change per pull request (AGENTS.md, Methodology). The contract
this repository enforces is AGENTS.md; CONTRIBUTING.md has the licensing
rules.
-->

## Outcome
<!-- What a user, or the agent driving Cadex, can now do or no longer does. -->

## Risk
<!-- What could break, and where: the engine, the dashboard, the agent
bindings, the cadexd protocol, the payload, or inherited FreeCAD code
(src/App, src/Base: call that out). -->

## Test evidence
<!-- Paste what you ran and what it said. At least:
- src/Mod/cadex/: pixi run test-engine
- cli/: pixi run python -m pytest cli/tests (its engine-needing half skips
  without a built engine; say whether it ran)
- C++/CMake: pixi run build-release, ctest diffed against
  build/ctest_baseline_failures.txt
- protocol or payload: the packaged gate against a staged payload
Report failures honestly. -->

## Checklist
- [ ] A removal or direction change has a `docs/DECISIONS.md` entry.
- [ ] Docs that describe the changed behaviour are updated, with their `Verified against source:` date.
- [ ] `docs/ROADMAP.md` checkboxes are updated if a work item landed.
- [ ] The work is recorded in the record graph (`hypergraph-record`), and `hypergraph check` exits 0.
- [ ] New files carry `SPDX-License-Identifier: LGPL-2.1-or-later`; no GPL code, prebuilt library, secret or machine path is added.
