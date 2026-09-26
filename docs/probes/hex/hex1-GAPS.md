# hex1 — gaps observed

One unassisted run: hexapod, MG90S, walk forward. Launched 2026-09-25 ~18:08 UTC
from `main` @ `4289ef0f` via `./cadex walk` (local RTX 5090 trainer).
Observe only; no code changes during the run.

## Log

- **18:08 — `cadex review` refuses a project that does not exist yet**
  ("project directory not found") though `--help` says "created if absent".
  You cannot open the dashboard before kicking off a run.
- **18:08 — the dashboard is single-project and Ouroboros-bound.** The
  persistent 8765 service only follows Ouroboros attempt receipts; a plain
  `cadex walk` needs its own `cadex review` on another port.
- **18:08 — agent's first script tried `import` and `repr`** (xscript sandbox
  rejects both). Cheap, recovered, but the authoring contract didn't prevent it.
- **18:09–18:31+ — design agent stalls in thinking, hitting the output cap.**
  After two tiny probe scripts (MG90S + horn, accepted 18:09) the model thought
  for 8 min and hit `max_tokens` (32000 output, stop_reason max_tokens, no
  tool call, no text) at 18:17, was auto-told to resume, and did it again at
  18:25. Nothing reaches the project, the log, or the dashboard in between —
  22+ minutes of silence that looks identical to "working". The whole design
  is being attempted in one head-held pass instead of incrementally.
  Two gaps: (a) the agent plans too much before writing anything;
  (b) no surface (walk log / dashboard) shows "turn alive, thinking, N
  max_tokens hits" — you had to read the Claude transcript to know.
- **18:33, 18:41 — third and fourth max_tokens hits; the walk ends itself.**
  Claude Code gave up after the fourth consecutive cap hit ("API Error:
  Claude's response exceeded the 32000 output token maximum"). Design leg
  exit 1 after 2007.68 s; walk `ok: false`, nothing trained. ~32 min spent,
  4 × 32k = ~128k output tokens of thinking, zero design produced.
- **The failure leaves nothing to resume from.** The walk envelope's
  `session_id` is empty, the project has no git commits and PROGRESS.md no
  row; the accepted revision is still the two-part probe. `--resume` has no
  conversation to continue, so a retry starts from scratch.
- **The walk's error message points at the wrong fix.** It suggests raising
  CLAUDE_CODE_MAX_OUTPUT_TOKENS, but the real defect is a turn that never
  writes anything down; a bigger cap just makes the silence longer.

## Outcome of walk1

Failed in the design leg at 18:41:53 UTC. Stages reached: API read, two
probe parts. Not reached: any hexapod geometry, assembly, task, training.
