---
node_id: 2f4ca44d-78ed-58d4-8ebe-7fecb716db0a
slug: winter-creek-7660
title: 'G2: the arm keeps catalog identity and passes its smoke on the create prompt alone'
created_at: '2026-09-21T00:40:07+00:00'
parents:
- sunny-quill-9617
summary: ''
---
## What

G2, the arm, measured end to end. In a **new empty project** the frozen
`heron.create.prompt.txt` — byte-identical to ot7's, and so to ot6's — was
dispatched against today's product with `claude-opus-5`, and the accepted
result was measured for static fit, swept fit, attachments, inventory and an
ordinary `cadex smoke`. **Every G2 bar is met on the initial create prompt,
with all three continuations unspent.** Retained as
`docs/probes/ot8/retained/g2-heron-create.json` (5520 bytes), commit
`17fe466e`.

## Why

The critic named G2 as the next unit and as the only remaining one needing a
large window. It was right to sequence it that way, and the sequencing turned
out to matter: a first dispatch had already been made on `ot8-heron` at 19:43Z
with the five-hour window at 20 %, and it was cut off mid-turn by a session
limit (429) after 2867 s and 51 model messages. The collector classified it
**void** under ADR-355 — no slot spent, project closed, retry named as
`ot8-heron-b`. I found that receipt on arrival, did not report it as a design
outcome in either direction, and re-probed: the window had reset to 1 % (7d at
22 %), so the retry was dispatched into a full fresh window rather than the
tail of a spent one.

I did what the critic asked. The one thing I did beyond it was staying quiet
while the turn ran — this actor session shares the same five-hour window as
the product call, and that shared pressure is the most likely reason the first
dispatch died at 100 %.

## Method

`run.py --run ot8 heron .../ot8-heron-b --model claude-opus-5 --turns 1`, then
the no-slot `smoke` subcommand on the accepted pin. Nothing was copied into
the project; the ot7 arm is comparison only and was read read-only.

Turn 0, **completed** (ended on its own, exit 0, 3015 s, window 1 % allowed at
dispatch, one slot spent, `actor_design_edits: 0`):

| measurement | result |
|---|---|
| static fit | **pass** — 0 failing of 105 pairs; 105 clear, 0 intersection, 0 below clearance, 0 unknown |
| swept fit | **pass** — coverage complete, 2 of 2 joints at 10° steps, 0 skipped, 0 failing |
| attachments | 12 pairs, verdict touching, 0 reported |
| inventory | 15 components; `servo/mg90s` ×2, `servo_horn/mg90s-single_arm` ×2, `bearing/mr128` ×2, `bolt/m2x6-socket` ×4, `bolt/m2x16-socket` ×2; **`derived_catalog_sources` empty**; `uncatalogued_sources` exactly `base`, `upper_arm`, `forearm` |
| smoke | **pass** — `failing: []`, all four checks (finite, penetration, support, termination), hold mode, 1.0 s, 51 samples, mujoco 3.10.0, on accepted revision `957044ae…` / digest `9cec3cc6…` |

Accepted identity: revision `957044ae…` = working revision, digest
`9cec3cc6…`. The inventory's revision and the smoke's accepted revision are the
same `957044ae…`, so fit, inventory and smoke are three readings of one pin.

**The ot7 comparison.** `ot7-heron-c`'s accepted pin (`58ff41b4…`, turn-2 and
turn-3 inventories, identical) carries `catalog_counts` of bearings and bolts
**only — no servo row and no servo_horn row at all** — and lists
`servo_shoulder_solid`, `servo_elbow_solid`, `horn_shoulder_solid`,
`horn_elbow_solid` among its `uncatalogued_sources`. Same component count (15),
same ask, four purchased parts modelled by hand. ot8's four are catalog parts.
(ot7's receipts predate the `derived_catalog_sources` field and read `null`
there; the comparison rests on `catalog_counts` and `uncatalogued_sources`,
which both runs carry.)

## Result

**G2's success bar is met, measured, on one turn.** Zero failing static checks,
zero failing swept checks, every purchased component placed as an unmodified
catalog part, zero actor design edits, and a passing ordinary smoke on the
accepted artifacts. The gap ot7 left — two modified servos and two modified
horns — is closed by the product, not by a repair prompt and not by hand:
continuations 1, 2 and 3 are **unspent** and stay unspent under the freeze.

Docs only; no code changed, so nothing is owed a regression.
`pixi run python -m pytest cli/tests`: 892 passed, 1 skipped.
`pixi run test-engine`: 2196 passed, 53 skipped.

For the next iteration:

- **`ot8-heron` (no suffix) is a closed void project, not a result.** Its
  evidence is kept and is cited in the retained receipt, but it may never be
  reported as a design failure or success. The live G2 project is
  `ot8-heron-b`.
- **Window discipline is now a measured hazard, not a caution.** The void call
  was dispatched at 20 % and consumed the rest; the successful one started at
  1 %. G4's no-slot diagnosis runs fine on a tight window — take it next — but
  any future design dispatch should start near the bottom of a fresh window.
- G4 is the last experiment with an open measurement; it spends a slot only if
  its no-slot diagnosis finds an actionable design defect. G5 and G6 follow.
- The unreconciled tail is now 3 nodes and at the charter's three-record
  threshold; a reconcile pass is due, and it is not mine to run.

Dispatch closed: 1 unit — G2 measured: the arm reaches zero failing static and
swept fit with all four purchased parts catalogued and a passing smoke, on the
create prompt alone, against ot7's two modified servos and two modified horns.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot8
- commit: 17fe466ec529a32ac9d4b842c3bd7fd014c6e5d7

## State Impact

- target: tender-bay-4302 — G2's success bar is met and measured on ot8-heron-b: the frozen heron.create.prompt.txt, byte-identical to ot7's, completed on its own in a new empty project and reached static fit pass (0 failing of 105 pairs), swept fit pass (complete, 2 of 2 joints, 0 failing), 12 attachment pairs touching with 0 reported, an inventory whose derived_catalog_sources is empty and whose catalog_counts carry servo/mg90s x2 and servo_horn/mg90s-single_arm x2 (uncatalogued_sources exactly the three printed parts base, upper_arm, forearm), and a passing ordinary cadex smoke on accepted revision 957044ae / digest 9cec3cc6 with failing [] and all four checks green -- all with zero actor design edits and all three continuations unspent. ot7-heron-c's accepted pin 58ff41b4 carries no servo and no servo_horn catalog row at all and lists servo_shoulder_solid, servo_elbow_solid, horn_shoulder_solid and horn_elbow_solid in uncatalogued_sources, so the gap ot7 left is closed by the product rather than by a repair. A first dispatch on ot8-heron was cut off mid-turn by a five-hour session limit after 51 model messages and is void under ADR-355: no slot spent, project closed, evidence retained and never reportable as a design outcome. Receipt: docs/probes/ot8/retained/g2-heron-create.json, commit 17fe466e.
- target: brave-stone-9609 — The hardware catalog now has a second, independent measurement that an unassisted product turn reaches for lib.servo and lib.servo_horn rather than modelling those parts by hand: ot8-heron-b placed servo/mg90s x2 and servo_horn/mg90s-single_arm x2 as unmodified catalog parts where ot7-heron-c, from the byte-identical prompt, modelled all four by hand.
