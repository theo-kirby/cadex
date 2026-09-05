---
node_id: 30aabb8b-d3dc-503e-80bd-6cd6ae40aab1
slug: dawn-oak-0677
title: 'ADR-173: the biped is the example project — the demo card returns, provenance-clean'
created_at: '2026-08-29T21:18:02+00:00'
parents:
- wild-sea-9905
summary: ''
artifacts:
- shell/scripts/startup/mesh_agent/demo/card.png
---
## What

The landing screen's example-project card is back (ADR-173): the MG90S
biped — the ADR-170 balance-toy arc — ships as the demo in
`shell/scripts/addons_core/mesh_agent/demo/` (`biped.blend`,
`biped.cadex/`, `card.png`), and a fresh install's first click opens a
parametric robot with a trained balance policy.

## Why

ADR-171 removed the drone demo because its seven imported STLs modelled
real commercial parts with no recorded origin, and deliberately left the
landing plumbing in place "so a Cadex-authored demo can return by simply
being placed there." The biped meets the provenance bar by construction:
every solid is authored by its `script.py`, no imported mesh exists
anywhere in the project, and its one asset is the Cadex-trained
`biped-balance.cxpolicy` the script replays.

## Method

Sanitized the working project at repo-root `demo/` into the add-on the
way the drone shipped: `script.py` + `script.json` + the policy asset;
`script_history` pruned to the single accepted-revision entry
(`0045-e5fb00e65d3e.py`, history.json rewritten to one entry); no
`script_artifacts/` (the only files carrying machine paths), no
`blueprints/` cache, no `.blend1`, no transcript. `card.png` is the
biped's own overview blueprint padded to the card's 1152x720 with the
sheet margin colour `#355283` (sips pad + resample). Code: three edits in
`cadex_landing.py` (`DEMO_STEM = "biped"`, the `open_demo` success
message, the docstring). Gate:
`test_landing_degrades_without_a_demo` flipped back to
`test_landing_demo_payload_ships` — completeness, fresh-stem copy
contract, machine-path sweep over every text file in the store, an assets
whitelist of exactly the policy, and the ADR-171 installed-bundle check
kept with its sense reversed (biped present, no stale drone). Docs:
`docs/BLENDER.md` landing/demo rows, ADR-173 appended to
`docs/DECISIONS.md`.

## Result

`bl_mesh_agent.py` suite green from source and against the rebuilt bundle
(the one expected failure before `pixi run build-shell` was the
installed-bundle staleness check doing its job); `pixi run gate` green
(`ok: true`). End-to-end probe against the *installed* bundle: copied the
installed demo pair the way the landing card does, opened it, and the
restore pass re-executed the shipped script — policy replay from the
shipped `.cxpolicy` included — reproducing the accepted digest and
hydrating 48 objects (`DEMO-PROBE OK`).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 268cbee80aefa415519365d66c7d23529d1f5a5d

## State Impact

- target: shy-crane-2573 — the landing screen ships the biped example project again (ADR-173): demo/ in mesh_agent carries biped.blend + sanitized biped.cadex + card.png, DEMO_STEM is biped, and test_landing_demo_payload_ships pins completeness, sanitization and the installed bundle
- target: easy-wind-9848 — the demo card's return keeps the ADR-171 posture: the shipped biped is entirely script-authored with one Cadex-trained policy asset, so nothing of unknown origin ships; a future compliance removal remains a file deletion
