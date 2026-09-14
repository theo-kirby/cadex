---
node_id: d54e5a6a-6c22-5c12-af20-f8a8f6a0c36c
slug: odd-orchard-4978
title: Robin D-bore revised as an analytic prism; new revision accepted, reopen passes three times, training unblocked
created_at: '2026-09-14T02:27:25+00:00'
parents:
- kind-reef-3852
summary: ''
---
## What

Revised Robin's wheel D-bore construction as a deliberate new design revision and
proved the project reopens. The bore is now an analytic D-prism (cylinder radius
`SHAFT_R + bore_clear/2`, flat plane `bore_clear/2` beyond the catalog flat) authored
in the gearmotor's canonical frame and placed with the same (origin, direction)
transform `lib.gearmotor` applies, replacing the `part.offset` of the catalog shaft
segment that kind-reef-3852 isolated as non-reproducible. Accepted through normal
`cadex script --set` (no output dropped, no `--replace`) as revision
5ad94d65e61a04635f6157b378bbea1fbde91e89819f44790ae5063d4b2db3b7, digest
185f9ccc4f9666e1e70d2a7e7c593add297edf3b3c28c1ac4117f28f2aeba885. Receipts:
`docs/probes/ot6/robin/BORE.md`, `bore.json`, `bore-fit.json`, two end screenshots;
`fit_check.py` prose generalised to the accepted revision; ACCEPTED.md, RESTORE.md
and README.md repointed to the current result.

## Why

Advances D7 (`ready-sand-2621`), whose only blocker was that Robin could not pass
its restore digest check and so could not train. This does what the critic's message
asked: a deliberate design correction of the bore, normal acceptance, the previous
revision and failure evidence preserved, inventory and fits updated, repeated
fresh-process reopen plus section proven, dashboard on the active revision, no
training yet. It is recorded as a design correction, never as recovery of the old
identity. The stale clearance plan item was not taken.

## Method

Start: fresh headless browsers at 1400x900 and touch 400x850 showed the persistent
user unit serving Robin at revision 71709063 (24 components, 57,044 triangles).
Wrote `ot6-robin-src/bore-candidate.py` by exact single-match block replacement of
the accepted script (the wheel block, its stdout line, one header comment; both
files hashed in bore.json). The rotation matches `_alignment_quaternion`: for
direction (0, s, 0) the axis is (-s, 0, 0) at 90 degrees, so both flats face +Z.
Submitted with `cadex script --set --json` (exit 0, 6 s). Ran `fit_check.py`
(84/84, wheel/motor 0.05 mm each side, zero overlap, 139.60133 g, 276 pairs, 24
solids, no grounded component). Ran `cadex section --plane XY --offset-mm 50 --json`
three times in fresh processes: exit 0 each, digest equal to the accepted digest
(the same command exited 1 on the old revision). Diffed the retained restore
attempts' result.json key by key: only `budget/elapsed_seconds` differs. Re-ran the
fit check on the restored attempt: identical inventory, checks and mass to the
acceptance attempt's receipt. Appended the design-correction entry to the project's
DECISIONS.md; INVENTORY.md and FIT.md regenerated. End: browsers at both widths
showed revision 5ad94d65, 24 components, 56,996 triangles, solids by default, nine
proxy outlines under the labelled toggle, zero horizontal overflow; the unit stayed
active. Redacted the machine path in bore.json to `$HOME`.
`pixi run python -m pytest cli/tests/test_review_design.py -k evidence -q`: 78
passed, 16 deselected. No product code changed, no build, no new dependency.

## Result

Robin reopens: revision 5ad94d65e61a…, digest 185f9ccc4f96…, three consecutive
fresh-process restores matching. Declared diametral clearance 0.1 mm is kept (0.05 mm
radial on the round and normal to the flat, measured 0.05 mm nearest approach). Each
wheel's volume fell by 0.00104 mm³ (sharp prism corners vs the offset's rounded ones);
every other inventory row is byte-identical to the old revision. Revision 71709063
keeps its identity: script in `script_history/0002-71709063d6af.py`, accepted result,
failed section envelope and frozen replay inputs under `ot6-robin-src/`.

Concerns: the store's ordinary ADR-045 lifecycle pruned the old revision's
`script_artifacts` (git-ignored rebuild output), so `restore_probe.py` now reads the
current revision; the old evidence lives only under `ot6-robin-src/`. Three matching
reopens are evidence in this environment, not a proof for every process. The
acceptance attempt was pruned by the three restores (ATTEMPT_KEEP), which is why the
accepted attempt id now names the last restore. Assumption: the engine's offset op
remains as it is; no engine change was made or is needed for D7. No training started;
D7's next unit is Robin's bounded training run with checkpoint and final videos on
the dashboard. The unreconciled tail is now two nodes.

Dispatch closed: 1 unit — Robin's wheel D-bore revised as an analytic D-prism, accepted as a new revision, fits kept, three fresh-process reopens pass, dashboard on the new revision, training unblocked.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: dfd1cd40235ca8f47454c5db406f2c9f7c51339f

## State Impact

- target: ready-sand-2621 — Restore blocker removed by a design correction: revision 5ad94d65 replaces the nondeterministic part.offset D-bore with an analytic D-prism at the same declared 0.1 mm diametral clearance; accepted via normal script --set, 84/84 fit checks (wheel/motor 0.05 mm, zero overlap, 139.601 g, 24 solids), three fresh-process section reopens exit 0 with the accepted digest; previous revision and its failure evidence retained; dashboard serves the new revision at both widths. D7 still open: bounded training, videos and measurements are the next unit.
