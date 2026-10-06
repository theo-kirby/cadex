---
node_id: 5dd9540d-0302-5827-a7b2-52251a67279b
slug: wandering-dune-8500
title: G2 second fresh-session proof on the revised printed-legged-robot style
created_at: '2026-10-06T16:39:12+00:00'
parents:
- nimble-garden-9555
summary: ''
---
## What

G2's second fresh-session proof, on the style as ADR-566 revised it
(commit `d3e027db`). The scratch project `orun4-fresh-legged-2` chose
`printed-legged-robot` through `cadex style`. The setup matched
`FRESH-SESSION.md`:

- a fresh `claude -p` session (claude-opus-5-5, Claude Code 2.1.290),
  isolated with `--strict-mcp-config` so its only server was `cadex mcp`;
- the same deny rules, plus the first fresh project and its transcript;
- the same verbatim prompt.

Its first accepted robot, ordinal 6, `19c0ef2d` (model `adfafa22`), is
scored in `docs/probes/orun4/FRESH-SESSION-2.md`, with excerpts and a
163 KB hero, `fresh-legged-2-first-design.png`. `LESSONS.md` summarises
the result.

## Why

The critic named this unit: a second isolated session, the same prompt
and audit, and three things recorded. The three were the foot ratios
against the ¼ and ⅛ bounds, whether the roll limit came from a measured
`first_contact`, and how the agent treated the thigh. I did it as asked.
Per the critic's instruction, I did not revise the style a second time,
although this run found a defect in it (below).

## Method

- **The session:** 107 min, 108 turns, exit 0, 21 accepted revisions.
  Ordinals 1–5 are probes and 6 is the first robot.
- **Leakage audit.** I read every Bash and Read call. They covered the
  guidance, the project's own files, help text, and slices of engine and
  CLI source on floors and smoke. None covers feet, keels or roll limits.
  - One near-leak: a `cd ~/cadex-projects; grep -l */agent.json; grep -q
    script.json` listed project names only, and nothing was opened.
- **Scoring.** I copied the project to `orun4-fresh-legged-2-r6` and ran
  `cadex revision restore 6`. The restored digest was `adfafa22`,
  matching ordinal 6. I then ran `cadex render`, which gave a standing
  height of 225.57 mm (the regulator top) and a foot of 54 × 27 mm from
  `summary.json`. The rest came from the revision's source in
  `script_history/`, the agent's `DECISIONS.md` and the transcript.
- **The `first_contact` semantics,** checked in source:
  `cadex_assembly_worker.py` sets it to the first contacting sample in
  the order low → high.
- **Gates.** Docs only, no code: `test_agent_guidance` (cli),
  `test_project_docs` and `test_licensing_compliance` gave 52 passed and
  1 skipped.

## Result

**The foot bound held, from the first robot.** The sole is 54 × 27 mm
under 225.6 mm, a ratio of 0.239 × 0.120, against the first check's 0.34 ×
0.19. The agent measured the height and recorded both ratios unprompted
(its ADR-006). It also used the ⅛ bound as a reason to drop an ankle-roll
servo. The twin-keel strip, accent foot, cross-horn caps, actuators
inside the limb, tapered windowed plates and no face all held again.

**The thigh rule held.** `knee_bend` 12° gives a lean thigh down to a
slightly bent knee, the upright case. The thigh is 66 mm and the shin
76 mm, 2.8× and 3.2× the cap, with the shin longest.

**The roll limit was derived late, and the procedure is defective.**

- Revision 6 has a chosen limit, −12/+30, which the sweep found clear.
- Later revisions followed the style unprompted: open the range to −45
  and read `first_contact`. The agent found that the reported value is
  the first contact from the range's low end, not the onset nearest
  rest. It bracketed instead. The legs met at about −12° at a 42 mm half
  span, so it widened the hips to 46. There they are clear at −15° and
  meet at −20°, so it set the limit at −10°, with both angles recorded.
- The source confirms it. Read literally, the style's procedure would have
  set −25°, inside the collision.
- **Open defect for a later unit:** `first_contact` against the
  `printed-legged-robot` HIPS rule. Either the engine reports onset
  nearest the solved pose, or the style tells the agent to bracket.
  Neither is fixed here.

**Other things the next iteration should know:**

- **Defects the agent hit.** `cadex smoke` refuses on a sub-1e-5 mm
  exact-geometry mismatch for a pair 70 mm apart, and counts threaded
  screw engagement as overlap. The earlier smoke timeout on 64+
  components recurred too.
- **Isolation gap.** A third session should also deny
  `Bash(*cadex-projects;*)`.
- **Scratch projects.** `orun4-fresh-legged-2` and
  `orun4-fresh-legged-2-r6` now exist. The transcript is in `/tmp` and
  was not committed.
- **Where G2 stands.** G2 now has a passing proof on two of its three
  named rules, the foot and the clearance spacing, and one defect in how
  the third is measured. Per the critic, the next unit is H1.
- **Tail.** One unreconciled record, this one.

Dispatch closed: 1 unit — G2 second fresh-session proof: foot inside ¼/⅛ bounds and lean thigh from the first robot; roll limit derived late, exposing a first_contact semantics defect in the style's procedure

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: d3e027db17411f62a8e182729f05db009e2decee

## State Impact

- target: narrow-beacon-6703 — Second fresh session (FRESH-SESSION-2.md, commit d3e027db) on the ADR-566 style: first robot's sole 54x27 mm under 225.6 mm (0.239 x 0.120, inside the 1/4 and 1/8 bounds, vs 0.34 x 0.19 before) and a lean thigh on an upright biped, unprompted. Inward roll limit chosen (-12) at the first robot, derived later (-10, from contact at -20 with hips widened 42->46). Open defect: first_contact is the first contacting sample from the range's low end, not the onset, so the style's HIPS procedure read literally gives a limit inside the collision for an inward roll on the negative side.
