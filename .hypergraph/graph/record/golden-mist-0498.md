---
node_id: 0194dafd-471e-5a3b-8aa7-c71574b25af6
slug: golden-mist-0498
title: 'Bet: close the modes, then promote L2 boards and the second mechanism'
created_at: '2026-09-06T19:55:43+00:00'
parents:
- wild-marsh-9611
summary: ''
---
## What

Re-rank short after two of its three units landed. Short becomes: (1) the GUI-attached walk documented against the same project contract, the last open mode of `witty-spark-2613`; (2) the L2 boards family over `CadexCatalog`, promoted from medium because the lifecycle short units it waited on have landed; (3) the same `cadex walk` on a second repo-owned mechanism, promoted from medium as a conditional unit that starts once unit 1 lands. Medium drops the two promoted items and keeps L3, Phase 8, Phase 13b engine side and `hide_render` in that order. Long is unchanged. No gap is retired, none is marked done, and no new direction is proposed.

## Why

Short unit 1 landed: `cadex walk` is the documented headless entry point, qualified on the plate-and-arm toy through two real walks, 13 tests and ADR-199 [rec: shy-cabin-0798]; the maintainer flipped `crisp-reef-5607` to working. Short unit 2 landed: `--remote` on `cadex train` and `cadex walk` puts the train leg on the box through `remote_train.sh` with identical project-relative artifacts, offline-tested against a stand-in dispatcher, never dispatched, ADR-200 [rec: green-delta-7130]. The critic rejected the first attempt because the project-doc scaffold did not change with the walk; the fix-forward gave the scaffold a Training section pinned to `docs/CLI.md` by a test, 136 CLI tests [rec: wild-marsh-9611]. That reject is the plan's first negative knowledge: any unit that touches the walk carries the scaffold edit in the same commit, and a documentation unit states which scaffold sentence it relies on.

What is left of the lifecycle rung is the GUI-attached document [rec: wild-marsh-9611], so it stays first: it is one unit, it closes the third mode of `witty-spark-2613`, and the run's headless-only constraint makes documentation the authorised evidence [rec: empty-wolf-3962]. The evidence it should cite already exists in code: the advisory `flock` on `.cadex-cli.lock`, `agent.json` as a sibling of the engine's `script.json`, and the shipped file-lifecycle behaviour (a `.blend` beside its `.cadex` hydrates on open, a digest-moving change shows the re-accept box). The document must say when the headless caller releases the project and how the shell observes accepted changes, from that behaviour, not from a wish.

The ladder's short rung names L2 boards after the lifecycle legs, and medium made its promotion conditional on those legs landing or being blocked [rec: lone-wood-3732]. They have landed, so L2 is promoted. Its shape is fixed by L0/L1 [rec: twilight-lake-8164]: sourced rows with approximate fields labelled, generators composed as lib values, a real-kernel build in the library tests, and the packaged lifecycle gate — which is the one full build the unit may spend. ROADMAP names the members: ESP32 DevKit, Pi Zero 2 W, PCA9685, with terminal pinout rows so the wiring system lands on library parts.

The second mechanism is promoted as the third unit because it is the cheapest generality check available and needs nothing L2 does not: the entry point is unchanged, the fixture is repo-owned, training stays toy-scale within the run caps, and the comparison is defined by the metrics the toy already records (`total_reward` over the verified rollout, reward per step) [rec: shy-cabin-0798]. The audit's warning stands: a changed reward weight is not an improvement comparison, so both projects record the same metric definitions and say what is comparable [rec: fond-mesa-1562]. If the walk needs a mechanism-specific change, that is a generality defect recorded on `swift-dusk-2951`, not a fixture edit.

Budget: four iterations in half an hour, fourteen and a half hours left. Three units fit the short horizon with room; medium is promotion order, not a promise.

## Method

Read the plan view, the four record nodes since the last pass, the state nodes for the walk, the modes, the catalog and the second mechanism, the charter's constraints and quality bar, ROADMAP's Phase 17 lines and `docs/CLI.md` §5. Wrote no code and ran no gate. Minted this bet as the only record of the pass, rewrote the short and medium plan nodes under optimistic lock, advanced the plan root's mark to the record tips, synced and checked.

## Result

Short holds three ranked units: GUI-attached walk documented, L2 boards family, second mechanism through the unchanged walk. Medium holds L3, Phase 8 `src/Gui`, two Phase 13b engine-side removals, `hide_render`, in that order, with the delta measurement inside the reduction work. Long is unchanged. The plan's first negative-knowledge entry records the iteration-3 reject. Charter, record nodes, state nodes and STATE.md untouched.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 22853520be55e8a20443eb81a8ab7b40fb90c80c

## State Impact

- target: plan/young-crane-9546 — short re-ranked: GUI-attached doc first, L2 boards and the second mechanism promoted from medium
- target: plan/strong-birch-7412 — medium drops the two promoted items; L3, Phase 8, Phase 13b engine side, hide_render remain in order
