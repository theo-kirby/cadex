---
node_id: 147a11b4-a156-53b7-80c4-c4bc5488f530
slug: odd-ridge-9607
title: Fused catalog servos fail the inventory published-output prerequisite
created_at: '2026-09-08T03:22:20+00:00'
parents:
- silent-mist-5233
summary: ''
---
## What

Established that short-plan item 2 fails its published-output prerequisite on the surviving, real-kernel pan-tilt rerun project: neither fused MG90S remains a catalog-stamped published output. Stop at this finding as the bet and overseer require; do not implement dependency-graph discovery in this dispatch.

## Why

Follows [rec: silent-mist-5233] and the second selected unit in [rec: forest-hollow-9339], serving mission 6 and charter criterion **The agent can see its work without a screen** (`damp-moon-9297`). This improves the evidence about a review limitation without reopening the already-working criterion. The two-servo design quota refusal is an external provider blocker, not a CAD failure: the previous run reported "You've hit your session limit · resets 8:30am (Europe/Madrid)". No new provider attempt was made in this unit and quota availability was not independently checked.

Assumption: follow the overseer's explicit feasibility stop, preserving existing work rather than treating a different implementation as authorization to bypass the prerequisite. No human response is needed.

## Method

Read actor and hypergraph-record skills, STATE, the hypergraph contract, VISION, the previous record, the inventory source/test implementation, and the surviving pan-tilt script and accepted artifact. `git status --porcelain=v1` and `git diff --stat` were empty on arrival. Contrary to the previous handoff's dirty-tree description, commit `997293b8` (the loop's iteration-36 commit) captured all eight inventory source/test files: 447 insertions and 9 deletions. Inspected that commit, including the library generator tally and worker report field. Preserved it unchanged. It counts generator calls and subtracts placed components; it is not the selected list of named published outputs. Its ADR-243 references have no corresponding ADR entry in the current decision log. It is not validated or accepted by this dispatch.

Read the local scratch project named `cadex-nt3-i35-pantilt` in the system temporary directory. Resolve its accepted result from `script.json` via `accepted_attempt.staging / result.json` (an initial ad-hoc probe omitted the `attempt-` prefix, failed with FileNotFoundError, and was corrected to use the stored staging field). No project writes, engine rebuild, reaccept, training, GUI launch or remote dispatch occurred.

Reproduction probe, using Python standard library:

```python
import json
from pathlib import Path
p = Path('<scratch-project>')
s = json.loads((p / 'script.json').read_text())
r = p / s['accepted_attempt']['staging'] / 'result.json'
d = json.loads(r.read_text())
outputs = d['outputs']
assert len(outputs) == 14
assert not any(o.get('catalog') for o in outputs)
assert not any(o['name'] in ('pan_servo', 'tilt_servo') for o in outputs)
print([(o['name'], o.get('type'), o.get('catalog')) for o in outputs])
print(d['component_sources'])
```

The corrected probe asserted both catalog/name absences and printed the count of 14; all passed. The existing script explicitly calls `lib.servo("mg90s", ...)` twice, passes each `.body` into `part.fuse`, and returns the fused solids. The result's `base_solid` and `yoke_solid` definitions both have operation `fuse`.

## Result

Accepted revision: `8ad39702c21c24ff7d2cc422cb1b33c94833bbcb70ea506f4be886709788c81f`; accepted digest: `ac1c9ca29dd8e7f70ca939a13a9e73e467697340279e5c1110d7faf4c43f9d52`. Accepted result SHA256: `03b65bbf9ef821a753a62a9dc13359889ef79810d21c67da9c58fb6faa618c9d`.

The 14 outputs are three solids (`base_solid`, `yoke_solid`, `head_solid`), three component links (`base`, `yoke`, `head`), two joints, an assembly, solve diagnostics, MJCF, task, policy and simulation. Zero outputs have catalog stamps; the component-source table references only the three fused/custom solids. The accepted report predates the inherited tally and has no `catalog_calls` field. Its generated `docs/inventory.md` lists three components and classifies all three source solids as not from the catalog. This is direct inspection of accepted real-kernel artifacts, not a fabricated fixture and not a fresh engine run.

The proposed scan of catalog-stamped published outputs cannot name either fused servo. Stop condition reached. No source/doc behavior change, removal or landed feature occurred in this unit, so no build, zone suite, packaged gate, ADR or ROADMAP checkbox is claimed. Existing inventory source changes remain exactly as inherited, with no verification evidence added here. Hypergraph export and check passed: 0 violations and 0 warnings. Local scratch artifacts are not committed, and no checkpoints or rollouts enter the repository.

Next: the planner needs a separate bet for catalog identity through the part program's dependency graph, including how to distinguish actually used parts from discarded or cutting-tool generator calls. Before treating `997293b8` as shipped, a subsequent authorized unit must review its semantics and supply or correct its missing docs and verification; fix forward, never revert the prior commit. Retry the bounded two-servo walk once provider quota is available. Existing closed lifecycle/review criteria remain closed; nothing else is missing to tick them on the evidence already reconciled, but this narrower fused-part diagnostic has not shipped. This node brings the unreconciled tail to three; the maintainer, not this work iteration, must reconcile.

Dispatch closed: 1 unit — fused catalog servos do not survive as published outputs, so the inventory bet stops at its feasibility gate.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 997293b878030c6d834e3f721e61d00bc7596bec

## State Impact

- target: damp-moon-9297 — Accepted pan-tilt artifact has 14 outputs and zero catalog stamps; both fused MG90S disappear as separate outputs, so the selected output-only diagnostic is infeasible. Dependency-graph work needs a separate bet; inherited generator tally remains unverified by this unit.
