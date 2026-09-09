---
node_id: 697fb875-9b66-58fe-b602-13e2bd86386d
slug: chilly-basin-7378
title: The fresh mixed-joint walk completes every leg
created_at: '2026-09-09T04:42:09+00:00'
parents:
- sleepy-grove-5790
summary: ''
---
## What

Ran the documented headless lifecycle entry point end to end on this machine, from nothing, as the iteration's first action — and **it completed every leg**. `ot4-mix55`: the same crank-slider prompt that `ot4-mix52` failed at `train`, a second empty project, no `--resume` and no supplied script. Exit 0 in 1680.78 s through design → train → policy verify → declare → rollout → all four review calls. Then landed the evidence in `docs/CLI.md` §2 and a ticked `docs/ROADMAP.md` entry.

## Why

Advances charter criterion **The walk exists and is tested headlessly** (`crisp-reef-5607`), per the overseer's explicit instruction that the fresh walk is the first action and whatever it returns is the result. This run is the clean end-to-end evidence that criterion asked for: one documented entry point, one prompt, no human step, every artifact in the project directory.

Assumption written down rather than asked: a clearance intersection is a review finding, not a walk failure. The eyes reported 648.0 mm³ of shared volume between frame and slider at the initial solved pose and the walk still exited 0. That is the designed behaviour — clearance names the offending pair for the next design turn — and `docs/CLI.md` now says so explicitly rather than leaving a reader to infer that exit 0 means no interference.

## Method

Rebuilt and installed the engine first (`pixi run build-engine`, exit 0): the checkout's `CadexDynamics.py` differed from the install by exactly the previous iteration's ADR-281 commit. After the rebuild the file matched, and the walk's own comparison reported `match` across 56 files.

Ran from `/home/theo/cadex` into `~/cadex-projects/ot4-mix55` (created empty), under the same 0.2 s process-tree RSS monitor with a 2.9 GiB kill guard:

`JAX_PLATFORMS=cpu CADEX_MODEL=claude-opus-5 ./cadex walk --project "$P" --prompt "$PROMPT" --out "$P/runs/fresh55" --name fresh55.cxpolicy --iterations 5 --envs 16 --seed 0 --timeout 600 --leg-timeout 1800 --json`

The prompt was verified byte-identical to the one `ot4-mix52` was given, decoded out of that run's envelope, so the comparison is between two runs of the same unaided request.

## Result

**Walk: exit 0 in 1680.78 s; peak process-tree RSS 2,312,118,272 bytes; watchdog did not intervene.** Model passed to the child: `claude-opus-5`.

Per leg:

- **design — exit 0, 1649.63 s.** Accepted revision `70fd2a53…`, digest `ee279ea9…`. Four bodies, one closed loop: grounded frame (base plate, rail bar, pedestals), a crank on a revolute driven by a 300 N·mm position servo, a coupler, and a carriage grooved over the rail. The all-revolute-plus-prismatic loop was built first and refused — MbD solves it at ~1e-8 residual but reports redundant constraints and names the three rows it drops, and the engine refuses simulation output from that graph — so the turn spent them on freedoms real hardware has: a ball rod end at the crank pin, a keyed cylindrical bushing at the rail. Six project `ADR-` entries, five domain notes (`actuators`, `architecture`, `linkage-geometry`, `rejected`, `sensors`) and five `PROGRESS.md` rows landed.
- **train — exit 0, 26.71 s.** CPU, 5 iterations × 16 envs, seed 0. reward/step **−0.4055** at best iteration 4; 4,609 parameters; 5.20 s trainer wall time; 26,121-byte `fresh55.cxpolicy`.
- **policy verify — witness error 1.14e-08** against a 1e-04 tolerance over 32 samples.
- **declare — exit 0, 0.81 s.** **rollout — exit 0, 1.53 s**, total reward **−19.85** at seed 1 (on_target +19.25, tracking_error −37.11, carriage_speed −1.72, servo_effort −0.27).
- **render** — four views (front, iso, right, top), 4,756 triangles, 0.90 s. **section** — plane XZ at 0.0 mm, **4 of 4 objects cut**, status `ok`, no missed objects. **inventory** — 4 components, 0 catalogued. **clearance** — 6 pairs checked, 0 unknown, **1 intersection**: frame ∩ slider, 647.9999999999985 mm³. Motion: 74.62° largest rotation (crank), 20.32 mm largest translation (coupler), over 151 solved frames.

**The MJX geom-pair refusal (ADR-281, last iteration) never fired, because the design turn did not need it to.** Every collision shape it authored is a box or a capsule, all in contact group 1 against an empty group 0, with the written reason that the loop is carried by its joints and the shapes exist only to be visible in a viewer. That is one run of evidence that the constraint reaches an unaided turn — not a guarantee, and it is stated that way in both documents.

Validation: `JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests -q` exited 0 — **289 passed in 222.63s**. `git diff --check` clean. The commit is documentation only (`docs/CLI.md` +42, `docs/ROADMAP.md` +15); no code, test, engine or shell change, so no engine suite or shell gate was required for the zone. Local run evidence stays out of Git in `~/cadex-projects/ot4-mix55/runs/fresh55/{walk.json,walk.stderr,monitor.json}`.

**This closes the walk criterion's remaining half.** `ot4-mix52` evidenced design; this run evidences train, declare, rollout and all four eyes on top of it, from nothing, with no human step — which is what **The walk exists and is tested headlessly** asks for. What is still missing before the *charter section* is finished is the other two open criteria, not this one: **Three modes, one shape** (the remote handoff and GUI-attached modes are documented, not exercised) and **The walk holds on a second mechanism** (nt2 left it close; it wants finishing and evidencing). The tail is now three unreconciled records; the contributor did not reconcile.

Dispatch closed: 1 unit — the fresh mixed-joint walk completed every leg, exit 0 in 1680.78 s, and the evidence is in `docs/CLI.md` §2 and `docs/ROADMAP.md`.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: a21e9e0bf693e28d2d56a7b374dd644d16e1e9d5

## State Impact

- target: crisp-reef-5607 — Fresh from-nothing mixed-joint walk (ot4-mix55, claude-opus-5, same prompt as ot4-mix52) completed every leg: exit 0 in 1680.78 s, peak tree RSS 2,312,118,272 bytes, no watchdog. Design 1649.63 s (revision 70fd2a53, digest ee279ea9; four bodies, one closed loop, ball rod end and keyed cylindrical bushing replacing the over-constrained all-revolute plan; six project ADRs, five domain notes, five PROGRESS rows). Train exit 0 in 26.71 s on CPU, reward/step -0.4055, witness error 1.14e-08 against 1e-04. Declare 0.81 s, rollout total reward -19.85 at seed 1. All four eyes ran: four render views (4,756 triangles), XZ section cutting 4 of 4 objects, 4-component inventory, clearance 6 pairs with one 648.0 mm3 frame/slider intersection reported but not gating. The design and training halves are both evidenced; the criterion's evidence is complete.
- target: damp-moon-9297 — All four review calls ran inside a completed walk for the first time this run: render four views in 0.90 s, section plane XZ at 0.0 mm cutting 4 of 4 objects with no missed objects, inventory 4 components / 0 catalogued, clearance 6 pairs / 0 unknown / 1 intersection naming frame and slider at 648.0 mm3. Clearance reports and does not gate: the walk exited 0 with the intersection named, and docs/CLI.md now states that rather than leaving exit 0 to imply no interference.
- target: late-pond-2851 — ADR-281's MJX geom-pair refusal did not fire on the ot4-mix55 design turn: it authored only box and capsule collision shapes, in contact group 1 against an empty group 0, and train ran to completion in 26.71 s. One run of evidence that the constraint reaches an unaided design turn, not a guarantee.
