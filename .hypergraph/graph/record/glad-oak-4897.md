---
node_id: 90908191-a987-5990-8a0b-c474b48dbc87
slug: glad-oak-4897
title: 'ot10 close: W2 shuffle verdict, gait-check blind spots, closing report and final gates'
created_at: '2026-09-29T07:42:17+00:00'
parents:
- keen-comet-6140
summary: ''
---
## What

The ot10 close, steps 1–3 of the critic's list, in `docs/probes/ot10/REPORT.md` (commit `c1cdd2c0`):
- **The W2 note.** The report states the owner's verdict: `w2-2` shuffles and does not walk, so `walked = true` is a false positive for gait quality. W2 is not presented as a walking robot. A new subsection, *What the gait check cannot see*, lists what `gait_from_trace` reads and what it cannot see: stepping, foot clearance, slip and duty factor.
- **The C1 report is finished:**
  - a per-criterion status list;
  - an A7 section, open and carried forward, with the measured distance to its bar;
  - an A8 section;
  - the W1 bound paragraph now says dashboard playback of the dark video was not re-checked;
  - a final gates table at this revision.

## Why

These are the critic's steps (1), (2) and (3), and the owner's exhaustion order after A8. I did not do step (4), reconcile, or step (5), claim done after reconcile. A work iteration is forbidden to run the hypergraph-reconcile skill, so folding `keen-comet-6140` and this record falls to the maintainer or reconcile pass. The report claims done for review, conditional on that pass.

## Method

- **The gait check.** I read `gait_from_trace` (`cli/cadex_cli/walk.py`) against the probe log's `w2-2` section. Its verdict is `walked = not findings`. There are four findings: tipped past 45°, heading past 90°, terminated, and training survival under 0.90. All of them come from the free base body's placement. Travel is reported but never judged, so a robot standing still, upright, would pass. The check reads no foot and no contact.
- **Withdrawn claim.** The probe log said "the feet step rather than slide". That rested on counts of the foot centre crossing a 3 mm lift line (48–124 per foot in 10 s), which chatter also produces. The report withdraws the claim under the owner's verdict.
- **The trace.** It carries per-component placements, so foot positions are there. It carries no contacts.
- **A7 facts.** They come from the attempts table and ADR-443: highest total 16, T4 at most 2, no A7 confirmation turn pre-registered or run.
- **A8 facts.** They come from ADR-444 and `keen-comet-6140`.
- **Gates.** Both suites ran at `fc279bfe` with the report edit on top. The engine changed since the last closing run (ADR-441 to ADR-443), so I compared the staged payload with the source (57 of 57 files equal) and ran the packaged gate against it.

## Result

- `pixi run test-engine`: 2,282 passed, 53 skipped, 0 failed (425 s).
- `cli/tests`: 1,085 passed, 1 skipped, 0 failed (885 s).
- Packaged lifecycle gate: 23 passed.
- `test_ot10_report.py` and `test_ot10_contract.py`: 48 of 48.
- The skips are the four known causes: JAX/MJX offboard, no Blender runtime, the packaged-gate env var, and the private review host.

REPORT.md claims done for critic review on A1–A4, A6, A8, W1, W2 and C1, and ticks no box:
- A5 is the owner's to judge. By its letter it is not met: 7 of 18 meet the bar.
- A7 is open and carried forward.
- W2 is a measured result, carrying the owner's shuffle verdict.

Concerns:
- **The reconcile is still owed.** The next pass must fold `keen-comet-6140` and this record, then run export and check. After that, the done claim stands.
- **An older paragraph is stale.** The report's "Reconcile before done" paragraph names two records that earlier passes have since folded. It is kept as history.
- **Unverified.** The dark-floor webm's dashboard playback is still unchecked.

Dispatch closed: 1 unit — ot10 close: owner's W2 shuffle verdict and gait-check blind spots, A7/A8 in the closing report, final suites and packaged gate green

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: c1cdd2c0cbbba12b713b780698d110d7d3715f37

## State Impact

- target: southern-prairie-3683 — the closing report is finished: A7 open and carried forward, A8 section, A5 owner's to judge; final gates at fc279bfe+report: engine 2,282 passed/53 skipped, CLI 1,085 passed/1 skipped, packaged gate 23 passed; done claimed for review pending reconcile
- target: golden-garden-8501 — owner's verdict recorded in REPORT.md: w2-2 shuffles, walked=true is a gait-quality false positive; the gait check reads only the base body and cannot see stepping, foot clearance, slip or duty factor
