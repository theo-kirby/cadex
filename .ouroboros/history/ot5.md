---
run: ot5
machine: sb1x
started: 2026-09-12T12:21:01
ended: 2026-09-12T19:12:55+00:00
hours: 2.9
state: killed
iterations: 22
commits: 31
criteria_ticked: 0
criteria_closed: 0
criteria_total: 9
merged: no
branch: ouroboros/ot5
memory: hypergraph
actor: claude:claude-fable-5-1
---

# Run ot5

22 iterations in 2.9h on `sb1x`, killed (-). Branch `ouroboros/ot5`, not merged.

## The numbers

| | |
|---|---|
| iterations | 22 (changed 22, recorded 14) |
| commits | 31 — 55 files changed, 8355 insertions(+), 65 deletions(-) |
| criteria | **this run ticked 0**; 0 of 9 checked at the tip |
| reverts | 0 |
| verdicts | continue 22 |
| loop detector | no firing |
| roles | actor claude:claude-fable-5-1, critic codex:gpt-6-astra |
| usage | claude seven_day 8% -> 7% (-1 this run); claude five_hour 100%; codex seven_day 9% -> 24% (+15 this run) |

## What landed

- Document real biped engine and dashboard restart evidence
- Record successful biped retry with live checkpoint and final videos
- Retain assembled training review inputs across design changes
- Show retained training export parts in historical project review
- Record live biped checkpoint review and interrupted probe2 experiment
- Document verified fresh-biped final-policy video recovery
- Identify a run from its first record: manifest identity before training, kept through failure (ADR-289)
- Document the fresh biped's creation, first GPU probe and live dashboard observation
- Test the review dashboard across a restart under independent training telemetry
- Collect browser downloads where a snap-confined Chromium can write them
- Report final policy publication failures in review telemetry
- ouroboros: start run ot5
- Retain training histories and poll live project telemetry
- Verify fresh project review after product-agent quota refusal
- Keep the review dashboard within a narrowed browser and verify private access
- ouroboros #3: no record
- Record every walk as runs/<name>/run.json and read projects back without an engine (ADR-285)

<!-- notes: everything below this line is yours; a rewrite keeps it -->

## What this taught

(unwritten)
