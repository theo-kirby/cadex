---
node_id: 89e8138c-59fe-5784-b31b-fdb6e9967d4d
slug: hidden-grove-0337
title: 'orun1 D3: ADR-491 servo.bay(ledge=4), the MG90S lead block was the bay'
created_at: '2026-10-03T07:14:02+00:00'
parents:
- deep-cove-1130
summary: ''
---
## What
ADR-491, commit `00fea49b`. The "lead block" that left every MG90S in hexapod trial 1 held by one screw is not in the catalog part. It came from the servo bay. `servo.bay()` gains an opt-in `ledge` (mm, default 0). With `ledge=4` the 6 mm lead room stops 4 mm under the tab-pocket floor, so the lead-side tab screw has material to thread into. The overlay (`CadexAgentGuidance.md`) and `docs/XSCRIPT.md` tell the agent to cut tabbed servos with `servo.bay(ledge=4)`.

## Why
This is the critic's first unit: check the MG90S lead block against the real part, then fix the catalog with a fail-before test and an ADR, or record it as a measurement. The critic's second item, quadruped trial 1, is a separate unit. One unit per iteration, so it is left for the next iteration. **Deviation:** the critic said "fix the catalog". The catalog was correct. `lib.servo` builds identical, drilled tabs and no block, as the real MG90S and SG90 have. The defect was in the bay (ADR-443), so the fix went there. It is also opt-in rather than a new default, for the F1 reason given below.

## Method
- Read `lib.servo` and `ServoPart.bay` in `cadex_library_api.py`. Every tabbed servo's lead-side hole lies inside the lead room, which ran from the case bottom to the tab underside (6.5 mm past the end face): SG90 3.15 mm, MG90S 3.1, MG996R 4.4, DS3218 4.75.
- First version: a 4 mm ledge as the new default. Engine suite targets passed. **But after `pixi run build-engine`** (the worker imports the installed `.pixi/envs/default/Mod/cadex`, not `src/`), a copy of the accepted hexapod (`~/cadex-projects/orun1-ledge-reopen`, from `orun1-t1-hexapod-render`) refused `open_project`: "The restore pass digest does not match the accepted digest". The reason was `recipe_comparison: the rebuild did not run the accepted recipe`. A bay is never catalogued, so its boxes sit inside the printed part's `definition`. A changed default changes the recipe of every accepted servo design, and ADR-476's recipe path does not cover that.
- Reworked it as opt-in. Re-installed it and reopened a fresh copy: restore `matches_accepted: true`, digest `2c9fe271…`, byte-identical.
- Tests: `test_library.py::test_servo_bay_leaves_a_ledge_under_the_lead_side_screw` (4 SKUs, fails on the old source: no `ledge` keyword). `test_mounting_check.py::test_a_ledged_servo_bay_gives_the_lead_side_screw_its_thread_on_the_real_kernel` measures each bolt's common volume with the block on the real kernel. Lead-side thread is **3.51 mm³ with `ledge=4` (equal to the free side) and 0.0 without**.
- `pixi run test-engine`: 2592 passed, 61 skipped. The CLI suite was not run, because no `cli/` file changed. No packaged gate was run either: no protocol or payload-structure change.

## Result
- True now: the catalog MG90S is right, and the one-screw servos came from the bay's lead room. `servo.bay(ledge=4)` lets both tab screws bite on the real kernel. Default bays and every accepted recipe are unchanged; this is measured on the hexapod copy. The installed engine (`build-engine`) carries the change and the new overlay line, so the next product turn sees it.
- **Concern, a new defect left for its own unit:** the mounting check credits a bolt that bites nothing. Without a ledge, the lead-side bolt's head comes within `MOUNT_CONTACT_MM` (0.5 mm) of the tab pocket's end wall. The check reads that as "into a printed part" and reports "2 of 2" when one shank hangs in air. D3's mounting check is therefore lenient on screws.
- **Concern, F1-class:** any change to an uncatalogued library helper's expansion (bays, `lib.*` geometry inlined into printed parts) makes accepted projects refuse to reopen. So library changes must keep default expansions byte-stable, or F1's restore path needs a rule for them. ADR-491 records this.
- Remember: Python edits under `src/Mod/cadex/` reach the worker only after `pixi run build-engine`. A dev-tree CLI run before that measures the old code.
- Next: supervised quadruped trial 1 at HEAD (`00fea49b`), as the critic asked. Tail: two unreconciled records (deep-cove-1130 and this one).

Dispatch closed: 1 unit — MG90S lead block is not in the catalog; it was the servo bay's lead room. ADR-491 adds opt-in servo.bay(ledge=4), with fail-before tests, and accepted recipes still reopen byte-identical

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: 00fea49b67574f0db9f0b68e67b0a44ca48e2d6c

## State Impact

- target: loyal-ocean-0768 — MG90S lead block checked: the catalog part has none; ADR-443's bay lead room sat over every tabbed servo's lead-side hole. servo.bay(ledge=4) (ADR-491, 00fea49b) gives that screw 3.51 mm³ of thread (0 without), opt-in so accepted recipes reopen byte-identical; open defect: mounting check credits a bolt within 0.5 mm of printed material even when its shank bites nothing
