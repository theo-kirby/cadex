---
node_id: 65b604f8-e958-5c80-bd9c-e6c863618f0a
slug: rough-cloud-5656
title: 'ot11 P1: floor marks in the judge''s detail sheet, measured in two arms and not adopted; w2-2''s manner stays 2 on all twelve calls (ADR-461)'
created_at: '2026-09-30T13:07:56+00:00'
parents:
- old-cove-1967
summary: ''
---
## What

A bounded probe of the blind video judge's blind spot, and a dead end: floor marks in the detail sheet do not make the judge score `w2-2`'s shuffle below manner 2. Nothing frozen and nothing in the product changed (ADR-461).

- **The probe.** For the length of the probe `cli/cadex_cli/film.py` drew, on the floor of each detail frame, a light mark wherever a drawn solid had touched the floor since the episode began (within 1.0 mm of the floor plane or under it, 2 mm grid). The marks are fixed to the floor while the window follows the base. The overview, frame times, view and window were untouched.
- **Two arms, on `w2-2` seeds 1101 and 1110, three calls a seed.** A: the marked sheet, judge procedure untouched. B: the same sheet plus one sentence in the judge's instructions saying what a mark is.
- **Landed:** `docs/probes/ot11/README.md` (a new section with the rule, the table and the diagnosis), `docs/DECISIONS.md` ADR-461, four probe receipts and the patch under `docs/probes/ot11/retained/probe-marks-*`, the marked sheet of seed 1101 (243 KB PNG), and one test in `cli/tests/test_ot11_judge.py`.
- **Not landed:** the film change and the instruction sentence. Both were reverted before commit.

## Why

Target: frontier node `rough-shore-6557` (P1), on the critic's message: give the detail sheet a way to show slip, re-film `w2-2` seeds 1101 and 1110 from stored traces, re-judge, and adopt only if manner drops below 2. It did not drop, so per the message nothing frozen was changed and P3 is next.

Two things I did that the message did not spell out, both inside its bound:

- **I chose floor marks over a floor-fixed window and did not draw the window.** Between two frames 0.04 s apart a sliding foot moves about 5 pixels, in separate tiles. A mark holds the whole slide inside one frame, so it was the stronger of the two options the message named.
- **I ran a second arm (B) after arm A did not move the score.** In arm A the judge never mentioned the marks, so A alone could not tell "the marks do not show slip" from "the judge did not know what they were". The rule (two arms in this order, adoption bar, no third arm) was fixed before the first call. The rubric and the bar were not touched in either arm.

## Method

- **Film.** `_Stage.touched` read, per trace frame, each solid's vertices at or under floor + 1.0 mm and marked the 2 mm cell under each (a triangle wholly in contact marked every cell it covers). `detail` drew the cells touched up to each frame as flat lit strips in the floor, under the contact shadow.
- **Re-film.** `cadex evaluate --film-only --film 1101,1105,1110 --detail-start 5.0 --detail-step 0.04` on `ot11-w2-negative`, no new rollout. All three overview sheets came out byte for byte as before.
- **Judge.** `docs/probes/ot11/runner/judge.py`, unmodified for arm A and with the one sentence for arm B. Twelve real calls, 109 s of model time, $0.48 at list price. Every call scored; none was refused, retried or answered by another model.
- **Restore.** Code reverted with `git checkout`, then the project was filmed again with the unchanged product. All six sheets are byte for byte the ones the committed judge receipts name. The rollout video was re-encoded, so its digest in the project differs from the one in `retained/p2-w2-2-evaluation.json` (a video digest identifies a file, not a rollout, as the README already says). The retained receipt was not touched.
- **Test.** `test_the_floor_marks_probe_left_the_manner_score_where_it_was_and_changed_nothing` holds the four receipts to what the runner computes from their own calls, pins arm B's sentence by the digest the receipts carry, and asserts the film draws no marks, the instructions are the pinned ones and the contract's `decisions` list is still one entry.
- **Suites.** `pixi run test-engine`: 2439 passed, 53 skipped. `pixi run python -m pytest cli/tests`: 1212 passed, 1 skipped (one more than before: the new test). No engine, protocol, payload or CLI module changed, so the packaged gate was not run.

## Result

**All twelve calls scored manner (V2) 2.** Medians on both seeds in both arms are V1 1, V2 2, V3 0, V4 1, total 4 — the scores the last record reported.

| arm | seed | V1 | V2 | V3 | V4 | total |
|---|---|---|---|---|---|---|
| A: marks | 1101 | 1 | 2 | 0 | 1 | 4 |
| A: marks | 1110 | 1 | 2 | 0 | 1 | 4 |
| B: marks and the sentence | 1101 | 1 | 2 | 0 | 1 | 4 |
| B: marks and the sentence | 1110 | 1 | 2 | 0 | 1 | 4 |

- **Arm A:** the judge's reasons do not mention the marks.
- **Arm B:** the judge read the marks as "mostly separate prints", "clumped and smeared in places" (1101) or "elongated into short streaks that suggest some foot sliding" (1110). That is rubric level 2.
- **Why the marks do not show a shuffle.** `w2-2` does not drag a planted foot in a line. Each foot leaves the floor four to seven times a second (37 to 52 swings on seed 1101, 24 to 42 on 1110, median 0.04 s to 0.07 s airborne) and slides between lift-offs. The floor shows short dashes, and the judge read them fairly. What makes it a shuffle is W5 (3 and 1 steps by the worst foot) and W7 (60 % and 81 % of a foot's path made sliding), which are totals over the episode.

**What is true now.**
- The film, the judge procedure and the contract are exactly as they were at `81873196`. The contract's `decisions` list has one entry (ADR-454).
- The judge's manner score is not a reading of stepping or slip. W5 and W7 are. The frozen pass rule requires the predicates and the bar together, so an upright shuffle may meet the judge's bar and still cannot pass the contract.
- I still believe P1's listed parts all exist, and do not tick it.

**Concern for the next iterations.** No policy that really steps has been filmed. The judge's manner score has been seen on a shuffle and never on a walk, so whether it separates the two at all is unmeasured. The first ot11 walk policy that passes W5 and W7 is the first positive control; its judge reasons should be read against these.

**Assumptions taken.**
- "Manner drops below 2" was read as the median on both probe seeds.
- A sentence saying what the sheet shows is part of the judge procedure (`judge_procedure`, pinned), not the rubric. It names no behaviour. It was tried in arm B only and is not adopted.
- The probe receipts are committed as the runner wrote them. Arm A's carry the label `w2-2-marks` and arm B's `w2-2`; the file names tell the arms apart.

**Next unit, as the critic named it:** P3 goal sampling (task, trainer and rollout), which also unblocks W3, W4's lateral half and the reach target marker.

No new dependency. Nothing removed. The unreconciled tail is now two records (`old-cove-1967` and this one).

Dispatch closed: 1 unit — floor marks in the judge's detail sheet were measured in two arms on w2-2 seeds 1101 and 1110, manner stayed 2 on all twelve calls, and nothing frozen or shipped was changed (ADR-461).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 78cb726fd0f35566633cfd24cd1e2ef9ac5e4b01

## State Impact

- target: rough-shore-6557 — no status change; the actor still believes P1's listed parts all exist and does not tick it. A bounded probe of the judge's blind spot (ADR-461, commit 78cb726f): for the probe the detail sheet's floor kept a light mark wherever a drawn solid had touched it since the episode began (1.0 mm contact, 2 mm grid, fixed to the floor under the following window), and w2-2 seeds 1101 and 1110 were re-filmed from stored traces and judged in two arms of three calls a seed — A with the judge procedure untouched, B with one sentence in the instructions saying what a mark is. All twelve calls scored manner V2 = 2; both arms' medians on both seeds are 1, 2, 0, 1 (total 4), as before. Arm A's reasons never mention the marks; arm B's read them as mostly separate prints with some smearing, a fair reading because each foot lifts four to seven times a second and slides between lift-offs. Nothing was adopted: the film change and the sentence were reverted (kept only as docs/probes/ot11/retained/probe-marks.patch), the film, judge_procedure and frozen contract are as at 81873196, and the contract's decisions list still has one entry. The judge's manner score is not a reading of stepping or slip; W5 and W7 are, and the pass rule requires predicates and bar together. Unmeasured: no policy that really steps has been filmed, so the judge has no positive control yet. Receipts retained/probe-marks-{a,b}-w2-2-seed-*.json, held by cli/tests/test_ot11_judge.py. A floor-fixed window was not drawn.
