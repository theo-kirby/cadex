---
node_id: b7ae8fe8-c13d-5153-a03a-ade36a27039f
slug: pale-arrow-4660
title: G1. The guidance is a base plus styles, and the agent can choose a style
created_at: '2026-10-06T07:42:21+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun4: **G1. The guidance is a base plus styles, and the agent can choose a style.** `src/Mod/cadex/CadexAgentGuidance.md`, `cli/cadex_cli/guidance.py` and `docs/DESIGN-LANGUAGE.md` are restructured into a domain-neutral base and named styles. A project chooses a style through its project config (e.g. `agent.json`); `cadex guidance` and the MCP instructions carry the base plus that style only, or the base alone. Tests pin: the base names no robot type as default; no style text appears when none is chosen; no guidance file names `biped-sts` or any other project. Choosing a style needs no new tool. The human owns the checkbox [rec: light-mist-9160].

**Evidence complete, pending the owner's tick** [rec: lucky-peak-7846]. ADR-560. The implementation landed in commit `7a4205b1` without a record. The audit checked it clause by clause and did not rewrite it. It includes `CadexAgentStyle.printed-legged-robot.md`, the `style` key in `agent.json`, a `cadex style` CLI command (not a tool, so the surface is unchanged) and the guidance loader. Pins:
- The base names no robot type as the default (`NOT_IN_THE_BASE`, which includes "look engineered") [rec: lucky-peak-7846].
- With no style chosen, the output is the base alone [rec: lucky-peak-7846].
- New: `test_no_guidance_file_names_a_project_and_the_doc_lost_look_engineered`. It scans the base, the styles, `guidance.py` and `docs/DESIGN-LANGUAGE.md`. The doc's `orun1-t1-hexapod` citation was cut [rec: lucky-peak-7846].
- New: `test_the_mcp_server_instructions_follow_the_projects_style`. It drives `McpSession.instructions()` before and after `cadex style` [rec: lucky-peak-7846].

Gates: test-engine 2598 passed, 58 skipped; cli/tests 1196 passed, 1 skipped [rec: lucky-peak-7846].

Owner-revisable assumption: the MCP instructions carry base plus style **by pointer**. The ≤2,000-character brief names the style and `cadex guidance --project <p>`, because the client cuts at 2,048 characters. Run names (ot10, orun1) remain in DESIGN-LANGUAGE.md as evidence. They are runs, not projects, so the charter allows them [rec: lucky-peak-7846].

**The base carries reward-shaping lessons for any task (ADR-586, `f49be9c3`).** `guidance.py` section SHAPE A REWARD THE POLICY CAN CLIMB, from the ball-plate and excavator projects (one to four training runs each): bell-shaped costs flat at the start state collapse training; an `abs(v-V)` cost passed a rocking policy; two sharper precision terms left a ~20 mm reach floor unchanged; slew reaction skated a floor-resting base until `command_slew_deg` limited it. Pinned by `test_the_reward_shaping_lessons_are_for_any_task`; the project-name patterns were extended so no project is named [rec: wise-lodge-1163].

Judgement (maintainer): status `working` because the human owns the checkbox. The next unit is G2: fold the reference project's lessons into the base and the `printed-legged-robot` style [rec: lucky-peak-7846].

## Negative knowledge

- [scope: orun4 G1 commit 7a4205b1 | confidence: high | evidence: glad-basin-7496, lucky-peak-7846] The G1 work landed with no record node. It was real, but the graph could not see it until a later unit audited it. A commit without a record leaves the next unit unsure what is done.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-g1-guidance-base-plus-styles)
- glad-basin-7496 — flagged 7a4205b1 as unrecorded G1 work to verify, not rewrite
- lucky-peak-7846 — G1 audited against the charter; project-name and MCP-host pins added; evidence complete pending owner tick
- wise-lodge-1163 — ADR-586: base guidance gains reward-shaping lessons for any task
