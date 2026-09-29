---
node_id: 011fb667-7cf6-5589-ae31-a49399ab11ba
slug: smooth-ivy-2460
title: 'ot10: joint cap goes over the horn, sized from its spec (ADR-440); hexapod-13 pre-registered'
created_at: '2026-09-29T04:04:36+00:00'
parents:
- hidden-bloom-1188
summary: ''
---
## What

A teaching change for the other half of `ot10-hexapod-12`'s diagnosed miss: the bare splined horns, T3. It adds a regression, ADR-440, and a pre-registration for A5 hexapod turn 13. The change is at commit `deccf6d9`.

The overlay's JOINTS ARE FEATURES bullet now says where the cap goes. The horn sits between the case top and the part it drives, so a disc on the far face or beside the hub leaves the horn in view. The driven part's hub is the cap:
- a disc of radius at least the horn's `.spec["arm_reach_mm"]` plus a 1.6 mm wall;
- cut with `horn.body`;
- with a skirt that reaches to within 1 mm of the case top;
- and the same disc on the servo's other face where that face shows.

Step 4's list of crude things to name now includes "a horn you can see".

## Why

The critic named this unit. It asked me to check whether the design language, the API reference, the catalog or xscript teach or offer a joint cap or horn cover, make the smallest teaching change with a regression, and pre-register hexapod-13 for the next iteration. This unit serves `loyal-fountain-8709` (A5), the highest-ranked open criterion. I did what was asked, with no deviation, and I did not run the turn. That is the next iteration's unit.

Findings:
- `docs/DESIGN-LANGUAGE.md` §3 already says "a printed cap covers the horn and its screw".
- The overlay said only that each axis "carries" a cap at least as wide as the horn. It did not say where the cap goes, and it gave no number to size it by.
- Neither the catalog nor xscript has a cap part. The horn's `.spec` carries `arm_reach_mm` (cross 10.2, single and double arm 16.0), `hub_dia_mm` and `hub_height_mm`.
- hexapod-12's accepted script did build caps: `cap_r = 12`, a `mechanism` cap at every hip and knee. But they sat at `F_hcap`, below the hip hub, and at `F_kcap`, on the far side of the knee from the horn. The horns stayed in view in the hero.

So the gap was placement, not existence. I chose teaching over a library cap part: where a cap goes depends on the design, so a generated one would be a second joint model inside the library.

## Method

- I read the hexapod-12 score, its accepted `script.py`, its hero and `iso_back` renders, `cadex_library_api._servo_horn`, `CadexCatalog.MICRO_HORNS` and `MICRO_HORN_HUB`, the overlay, and the ADR-422 face test.
- I edited `cli/cadex_cli/agent.py` (the CLI overlay).
- New tests in `cli/tests/test_turn_loop.py`:
  - `test_the_joint_cap_goes_over_the_horn_and_is_sized_from_its_spec`
  - `test_the_horn_spec_carries_the_reach_the_overlay_sizes_the_cap_from`, which checks that the named key exists and is positive on every catalog horn row.
- I stashed the overlay and ran both tests against the old overlay: both failed. With the change, both pass.
- ADR-440 is in `docs/DECISIONS.md`. The REPORT.md remaining-defect 6 now carries the placement finding.
- The README has a new section, "A5 hexapod turn 13, pre-registered", with:
  - the new project `ot10-hexapod-13`;
  - the frozen `contract.json` `a5.prompts.hexapod`;
  - `claude-opus-5-5`, `CADEX_EFFORT=medium`, no continuation;
  - a file-by-file comparison of the installed and source engine before launch;
  - T3 against hexapod-12's 1 as the extra measurement;
  - "Nothing is re-scored", with a miss counting as the twelfth.
- It is pinned by `test_a5_hexapod_turn_13_is_pre_registered_after_the_horn_cap_change` in `cli/tests/test_ot10_contract.py`.

## Result

- **The overlay now teaches cap placement and size.** A cap on a servo's far face no longer satisfies the rule as written. Two regressions pin it, and both fail on the previous overlay.
- **Unchanged:** the rubric, proxies, bar and judging procedure. Nothing is re-scored. The wording comes from DESIGN-LANGUAGE §3, not from the judge's replies.
- **Suites:**
  - CLI full suite: 1073 passed, 1 skipped (the review-host skip). That run included the turn-loop edits.
  - `test_ot10_contract.py` and `test_turn_loop.py` after the contract edit: 87 passed.
  - No engine or payload file changed, so the engine suite and the packaged gate were not re-run.
- **Next unit:** run hexapod-13 exactly as pre-registered. Use `turn.sh` from the hexapod-12 notes with a new project name. Compare the installed engine with the source first: ADR-439 changed `cli/` only, and the engine should still match. Then score it blind and publish it, hit or miss.
- **Assumption:** the overlay is not frozen by `contract.json`. Checked: no overlay hash is pinned there, and ADR-422 and ADR-428 changed it between probes the same way.
- **Nothing is broken.** Two unreconciled records came before this one, so the tail is now three, and a reconcile is due by the charter's three-record rule.

Dispatch closed: 1 unit — overlay teaches the joint cap over the horn, sized from horn .spec["arm_reach_mm"] (ADR-440, two regressions failing on the old overlay), and A5 hexapod turn 13 pre-registered for the next iteration

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: deccf6d916cb3327006e0526b61ca086b83a769d

## State Impact

- target: loyal-fountain-8709 — hexapod-12's T3 miss diagnosed as cap placement (caps on the servo's far face, horns in view); the CLI overlay now teaches the driven part's hub as the cap over the horn, radius >= horn .spec["arm_reach_mm"] + 1.6 mm, cut with horn.body (ADR-440, commit deccf6d9, two regressions failing on the old overlay); A5 hexapod turn 13 pre-registered on ot10-hexapod-13 with the frozen prompt and flags, not yet run
