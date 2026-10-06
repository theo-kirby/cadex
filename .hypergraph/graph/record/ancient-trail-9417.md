---
node_id: 0722731c-ab63-570f-b2e3-241efa215bc1
slug: ancient-trail-9417
title: 'G2 fresh-session proof: a fresh agent on the printed-legged-robot style'
created_at: '2026-10-06T14:11:36+00:00'
parents:
- northern-stream-2677
summary: ''
---
## What

G2's fresh-session proof (commit `f71fa77a`). A new scratch project,
`orun4-fresh-legged`, chose the `printed-legged-robot` style through
`cadex style`, which wrote it into `agent.json`. A fresh Claude Code
session (claude-opus-5-5, 2.1.290) was then asked for a small printed
two-legged robot, with no hint about feet, joints or clearance. It drove
the project through `cadex mcp` only. Its first accepted robot,
revision `29e99e01` (ordinal 6), is scored against the style's rules in
`docs/probes/orun4/FRESH-SESSION.md`, with a transcript excerpt and a
177 KB hero, `fresh-legged-first-design.png`. `LESSONS.md` links to the
proof.

## Why

This is the unit the critic named. It is G2's proof, which closes the
criterion the charter ranks highest ("if the run achieves only one
thing"). It follows ADR-565, which placed the lessons in the base and the
style. I did it as asked, with no deviation.

## Method

- **Isolation.**
  - The session started in the project directory, so no repo
    `CLAUDE.md` or memory was loaded.
  - Its only MCP server was the project's (`--strict-mcp-config`).
  - Permission deny rules blocked other projects, `docs/probes/`,
    `.hypergraph/`, `.ouroboros/`, `STATE.md` and the web.
  - The prompt, in full: "Design a small 3D-printed two-legged walking
    robot driven by hobby servos, in this Cadex project. Take it as far
    as one complete, accepted design you are satisfied with, then stop:
    do not train a policy."
- **The run.** 44 min, 82 turns, exit 0. Eleven revisions were accepted:
  1–5 were probes, and 6 is the first robot.
- **Leakage audit.** I read every Bash and Read call in the stream-json
  transcript. It read the guidance, API source, one example script, two
  short slices of `MUJOCO.md` and `XSCRIPT.md`, and the head of
  `HEADLESS-BIPED-REVIEW.md`. None of these covers keels, feet, hip
  spacing or roll limits. `DESIGN-LANGUAGE.md` appeared only as a name in
  an `ls`.
- **Scoring.** I read revision 6's source in `script_history/`, its
  `fit` block from the transcript, and the agent's own `DECISIONS.md`.
- **Render.** I copied the project to `orun4-fresh-legged-r6`, ran
  `cadex revision restore 6` (digest `ae557f80` confirmed), then `cadex
  render`.
- **What was not committed.** The transcript (kept outside the repo, in
  `/tmp`) and the projects.
- **Gates.** Docs only, no code: `test_agent_guidance`, licensing and
  `test_project_docs` passed (51 passed, 1 skipped).

## Result

**The style carried most of its rules unprompted.** Revision 6 has:

- a twin-keel sole: a box whose long edges are filleted to the keel
  radius, with a flat strip between. Its colliders are exactly a box and
  two cylinders from revision 8.
- an accent-coloured foot as its own part;
- one horn-sized cap design (horn reach + 1.6 mm, cut with
  `horn.body`, skirt 1 mm off the case, cross horn) on all eight axes;
- knee and ankle servos hung inside the limb;
- plates tapering in width and depth, with tapered windows;
- no face;
- hip roll limited 10° inward and 30° outward. The 5° sweep over all 8
  joints passes.
- The strip was centred on the measured COM by revision 9 (`foot_fwd`
  15 against COM x 15.1).

**It missed one rule outright: foot compactness.** The strip is the whole
foot: a 72 × 40 × 10 mm slab under a 210 mm robot. It reads as the
"large, flat" foot the rule forbids. "Compact", with no proportion,
did not hold.

**Partial: the hip clearance rule.** The inward roll limit was set tighter
than the outward one and checked by the sweep. It was not derived from
the angle at which the feet meet, which the agent never measured.

**The guidance is wrong for this robot in one place.** The style's "the
thigh runs out level" rule fits a sprawled leg. The agent declined it
for an upright biped, with that reason, and was right to.

**Next iteration:**

- G2's proof is recorded with one miss. Two style revisions would follow
  from it, each its own unit:
  - give foot compactness a measurable bound relative to the robot;
  - scope the level-thigh rule to sprawled legs.
- I made neither change here.
- **Defect seen in passing:** the agent reported that `cadex smoke` timed
  out in its exact-geometry stage on 64 components.
- **Tail:** two unreconciled records, this one included.
- **Projects:** `orun4-fresh-legged` and `orun4-fresh-legged-r6` exist.

Dispatch closed: 1 unit — G2 fresh-session proof: style rules carried unprompted except foot compactness; level-thigh rule found wrong for bipeds

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: f71fa77a4e607fc1bd90a8c93f50de0b934f6336

## State Impact

- target: narrow-beacon-6703 — The fresh-session proof ran (FRESH-SESSION.md, commit f71fa77a): with only guidance + style, a fresh agent's first accepted biped (rev 29e99e01) carried twin-keel strip, horn-sized caps, in-limb actuators, two-way taper and tighter inward roll limit unprompted; it missed foot compactness (72x40 mm slab) and showed the style's level-thigh rule is wrong for upright bipeds. G2 has its evidence, with one miss.
