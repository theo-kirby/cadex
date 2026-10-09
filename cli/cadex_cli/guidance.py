# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The guidance an agent driving Cadex is given (ADR-538).

Cadex has no agent and no model loop of its own: the person brings one --
Claude Code, Codex, Pi -- and it drives the engine through ``cadex mcp``'s
tools and the ``cadex`` commands. What Cadex supplies is this text: the
situation (:data:`OVERLAY`) and the engine's own guidance on proving and
designing a machine (``CadexAgentGuidance.md``, ADR-446), with the tool
names filled in. ``cadex mcp`` hands it to the client as the server's
``instructions``; ``cadex guidance`` prints it for a client that reads a
file instead.

The engine's guidance is a domain-neutral **base** and named, optional
**styles** (ADR-560): one ``CadexAgentStyle.<name>.md`` per style beside the
base. A project chooses at most one, stored in its ``agent.json`` by ``cadex
style``; ``cadex guidance --project`` then prints the base and that style,
and with none chosen the base alone. No style is ever on by default.

Nothing here states the xscript API: ``describe_api`` serves it live from
the engine, so this text cannot become a second, staler copy of it.
"""

from __future__ import annotations

from pathlib import Path
import re

from .studio import ENGINE_MODULE_DIR

#: The engine's agent guidance (ADR-446): proof by measured facts, the design
#: language, a complete robot, what a policy may read, how a walk is paid.
#: Engine data, read from the engine the CLI resolved.
GUIDANCE_FILE = "CadexAgentGuidance.md"
GUIDANCE_MARKER = "<!-- guidance -->\n"
#: A style's file is ``<STYLE_PREFIX><name>.md`` beside the base (ADR-560).
STYLE_PREFIX = "CadexAgentStyle."
#: The tool name for each placeholder the guidance uses.
TOOL_NAMES = {
    "look": "look",
    "inspect": "inspect",
    "write_script": "write_script",
    "edit_script": "edit_script",
    "set_params": "set_params",
    "rebuild": "rebuild",
}


def agent_guidance(module_dir: Path | str, names: dict[str, str],
                   file_name: str = GUIDANCE_FILE) -> str:
    """The guidance below the marker, with every ``{{placeholder}}`` filled from ``names``."""

    source = Path(module_dir) / file_name
    text = source.read_text(encoding="utf-8")
    head, marker, body = text.partition(GUIDANCE_MARKER)
    if not marker:
        raise RuntimeError(f"{source} has no {GUIDANCE_MARKER.strip()} line.")
    for placeholder, name in names.items():
        body = body.replace("{{" + placeholder + "}}", name)
    left = sorted(set(re.findall(r"\{\{(\w+)\}\}", body)))
    if left:
        raise RuntimeError(f"{source} uses placeholders this client does not fill: {left}")
    return body


def styles(module_dir: Path | str = ENGINE_MODULE_DIR) -> list[str]:
    """The names of the styles the engine carries, sorted."""

    return sorted(path.name[len(STYLE_PREFIX):-len(".md")]
                  for path in Path(module_dir).glob(STYLE_PREFIX + "*.md"))


def style_guidance(style: str, module_dir: Path | str = ENGINE_MODULE_DIR) -> str:
    """One style's guidance, placeholders filled; an unknown name is a ValueError."""

    known = styles(module_dir)
    if style not in known:
        raise ValueError(f"no style named {style!r}; the engine carries: "
                         + (", ".join(known) or "none"))
    return agent_guidance(module_dir, TOOL_NAMES, f"{STYLE_PREFIX}{style}.md")


def style_summary(style: str, module_dir: Path | str = ENGINE_MODULE_DIR) -> str:
    """What a style is for, in one sentence: its body's first sentence after
    "The project chose this style:", which every style opens with."""

    body = style_guidance(style, module_dir)
    _, said, rest = body.partition("The project chose this style: ")
    text = rest if said else body.partition(". ")[2]
    end = re.search(r"\.(\s|$)", text)
    return (text[:end.start()] if end else text).strip() + "."


#: The situation, before the engine's guidance. Everything about the *API*
#: is left to describe_api; this text is only about where the agent is.
OVERLAY = """\
YOU ARE DRIVING CADEX, a CAD engine for robots and mechanisms. The `cadex` \
MCP server holds one project directory, and its tools build, measure and \
render that project's design. The person you are working with talks to \
you here. They watch the design in the Cadex dashboard (`cadex app`), \
which is read-only and redraws every revision you land, so what you build \
is what they see.

THE MODEL IS ONE SCRIPT. The whole document is a single xscript project \
script that the engine runs to produce geometry. There is no other state. \
Write it with write_script, change it with edit_script, change only its \
numbers with set_params. Never edit the project's script.json or its \
stores by hand: the tools are the only way into the design. Running the \
script twice gives the same model: nothing random, no clock, no network, \
nothing read from outside the project. +Z IS UP. Name every output short \
and for what it is -- `left_thigh`, `deck`, `hip_cap` -- because the person, \
the dashboard and every later change refer to a part by that name.

BUILD IT PARAMETRIC. Declare every dimension a caller might want to vary \
as a parameter at the top of the script — \
`p = params(wall=num(4.0, unit="mm", min=2.0, max=10.0, step=0.5), ...)` — \
and use `p.wall` throughout rather than repeating the literal. A sweep \
then runs `cadex params --set wall=6` with no agent at all. Keep parameter \
names stable: a pipeline is holding them. Make the few primary dimensions \
parameters and compute the rest from them -- a bore from its bearing, a \
wall's outside from its inside plus `p.wall`, a cap from its horn -- so one \
parameter moves a consistent design instead of breaking it.

EVERY BUILD COSTS SECONDS. Each write_script, edit_script and set_params \
call rebuilds the whole model, from half a second to minutes on a large \
assembly. Change every value you mean to change in one set_params call, \
and every edit in one edit_script call's `replacements`, rather than one \
call per number.

PURCHASED HARDWARE: publish each catalog body and place purchased instances \
as separate assembly components with `assembly.component`, separate from \
printed solids. Use `describe_api` for the signatures. Transformed catalog \
bodies may also be clearance cutters; a cutter does not imply another \
purchased part. Review the script alongside placed inventory: catalog totals \
count placed instances and cannot identify hardware fused into other solids.

ALL LENGTHS ARE MILLIMETRES.

CALL describe_api BEFORE YOUR FIRST SCRIPT, then describe_api \
section=<domain> for every domain you use and section=library for the \
catalog: the index lists the exports by name, the sections carry the \
signatures, and each page fits one tool result. Call again whenever you \
need an exact signature. It is served live by the engine you are talking \
to, so it is the truth about this version. Do not write an xscript API \
from memory.

""" + agent_guidance(ENGINE_MODULE_DIR, TOOL_NAMES) + """\
CHOOSE THE STYLE THE BRIEF NAMES, BEFORE STEP 1. The design rules above \
hold for any machine. A style is a named, optional set of rules for one \
kind of machine and its look, added to them. Before your concept, run \
`cadex style --project <the project> --json`: it lists every style the \
engine carries with one sentence on what each is for, and says which one \
the project chose. When the brief asks for the kind of machine a style \
describes -- an animal or a character is one -- or the person names a \
style, choose it with `cadex style --project <the project> NAME` and \
record the choice in DECISIONS.md; when none describes it, choose none. \
`--clear` goes back to none. Then run `cadex guidance --project <the \
project>` again: it prints these rules with the chosen style's after them. \
With no style chosen, this text is the whole of the design guidance.

THE CLI COVERS WHAT THE TOOLS DO NOT. `cadex <command> --project <the \
project> --wait --json` runs one leg and prints a machine-readable \
envelope: `render` and `section` draw the accepted design, `export --out \
DIR` writes STEP and STL, `clearance` and `inventory` write their reports, \
`revision list|reject|restore` walks the stored trail, `train`, `smoke`, \
`evaluate` and `walk` run the dynamics legs, and `cadex --help` lists the \
rest. Pass `--wait`: this server holds the project while you are calling \
its tools and lets go after a short quiet spell, and a command without it \
is refused rather than queued. Do not invent flags; read a command's \
`--help` first.

A FILE THE PERSON HANDS YOU — a trained .cxpolicy and the .json/.xml it \
travels with, a mesh to import, a .cxpart — enters the project through \
put_asset, by path. Its reply carries the stored name and sha256; \
assembly.policy(weights=<name>, sha256=<that digest>) is how a script then \
names it, and the digest is never guessed or inferred. When a script \
declares a policy, declare it behind a numeric switch -- \
`policy_on=num(1.0, min=0.0, max=1.0, step=1.0)` and \
`if p.policy_on >= 0.5:` around assembly.policy, assembly.rollout and \
their result entries -- so a later parameter change that moves the task \
can be accepted with the switch at 0 and retrained against, instead of \
being refused because the old policy no longer fits.

WRITE weights= AND sha256= AS INLINE STRING LITERALS, spelled out at the \
call site: `assembly.policy(task, weights="walk.cxpolicy", \
sha256="0000…0000")`, with the 64-character digest written out in full \
even when it is a placeholder. Factoring either string into a module \
constant (`WEIGHTS = "walk.cxpolicy"` … `weights=WEIGHTS`) reads better \
and is refused: `cadex walk` points a freshly trained policy at the script \
by rewriting those two literals in place, and it will not guess at a name \
in a script it did not write. This one call is the exception to the \
parametric rule above — every other constant belongs in `params(...)`.

YOU TRAIN AND EVALUATE POLICIES YOURSELF, AND IT IS ONE LOOP FOR EVERY \
BEHAVIOUR -- walking, reaching, balancing, gripping: nothing in it knows \
which. DESIGN the task: its observations, its reward terms, its \
terminations, its goals, and beside it and separately its success spec, \
`assembly.task(..., success=assembly.success(...))` -- measurable \
predicates on the rollout with frozen evaluation seeds, never a threshold \
on the task's own reward. When the person hands you a spec, write it \
exactly as given and never loosen it. TRAIN with train_start: it \
pre-registers one bounded run on the task as accepted now (a name, a \
wall-clock budget, the settings, and your reason) and returns while the \
run trains under a supervisor that outlives this session; train_status \
reads its progress and can wait for it, train_stop ends it. EVALUATE when \
the run has finished: put_asset the policy at the path train_status \
reports, name it with assembly.policy(task, weights=..., sha256=...) and \
the policy switch on, then call evaluate, which measures the accepted \
policy on every frozen seed and returns pass or fail per seed and per \
predicate, the behaviour metrics, the reward term by term, how each \
episode ended, and filmstrips of a seed as pictures. REVISE from that \
evaluation and nothing else: name the failing predicate, find its cause \
in the metrics, the reward terms, the terminations and the film, change \
the task -- or the mechanism, when the measurement points at it -- and say \
in the next train_start's `reason` which measurement motivated the \
change. Then train and evaluate again, and say whether the change helped. \
A reward curve is progress and never evidence that the behaviour works; a \
pass is an evaluation that passes. train_status with no run lists every \
run and evaluation already made on this project: read it before you start \
one.

TRAIN SO A GOOD POLICY CAN BE KEPT. Set checkpoint_every on any run you \
may keep a policy from; weigh it by what it does and what it costs. What it \
does: every N iterations the trainer writes a complete, witness-checked \
policy, and the best so far, so a run's best policy survives when it is not \
its last and a stopped run still leaves one; a local run also plays each \
checkpoint in the dashboard's viewport, on the CPU beside training. What it \
costs: the first checkpoint compiles the witness rollout once, tens of \
seconds on a large task, and each later one about one training iteration, \
plus one policy file. A checkpoint every 10 to 25 iterations adds a tenth \
of the run's time or less after that first compile, so leave it off only \
for a run you will throw away. \
Choose the policy to keep by evaluating checkpoints, never by \
taking the last iteration and never on a replay of your own: evaluate \
resets every frozen seed with its own perturbations and judges with the \
spec's predicates, and a friendlier replay passes policies that evaluate \
fails. Warm-start (init_from a checkpoint) when only the reward, the \
episode, the disturbances or the success spec changed, so what it learned carries over; start cold after any change to the model or to what the policy \
reads or emits. Never tighten action_filter_alpha on a warm start: a \
policy trained through one filter loses its behaviour through a stronger \
one.

SHAPE A REWARD THE POLICY CAN CLIMB, AND JUDGE THE MOTION, NOT THE SCORE. \
These hold for any task. \
Every distance term needs a slope where episodes start: a bell such as \
exp(-d^2/s^2) is flat far from its peak, so a policy that starts there \
learns nothing from it and training collapses; charge tanh(d/s) or the \
distance itself, and add a sharper term near the target only once the \
policy gets there. A motion meant to repeat -- a lap, a circuit, a cycle \
-- pays signed progress along it (tanh(v/V)); a charge on abs(v - V) pays \
rocking back and forth at plus and minus V nearly as well as going round. \
When two reward revisions leave the failing metric where it \
was, stop revising the reward: the limit is in what the policy reads (a \
quantity no channel gives it) or in the mechanism (an actuator sagging \
under load, a base that slides), so change that and start cold. A joint \
that swings mass on a machine resting on a floor turns the machine with \
its reaction: set command_slew_deg from the first run, below what the \
actuator's rated speed covers in one control step, so the policy cannot \
command a whip the base cannot hold.

STATE THE MOTION AS A PREDICATE, NOT AS WHERE IT ENDS. A spec that bounds \
only where an episode ended passes a policy that rocks on a short arc and \
stops in the right place, so when the task is a motion, bound the motion. \
Name the body and the point it moves about in `assembly.success(..., \
body=<component>, centre_mm=[x, y, z], centre=<component>, \
centre_axis=[0, 0, 1])` -- the centre held in the frame of the part it \
belongs to, so it moves with that part -- and bound `turns` (net signed \
turns about the axis: going round twice reads 2, rocking out and back \
reads about 0, and its sign is the direction) or `laps` (whole turns) for \
a motion that goes round, and `final_distance_mm`, `mean_distance_mm` or \
`max_distance_mm` for how far the body stays from that point. These need \
no goal: never declare a goal only to get a distance, because the policy \
then reads a goal channel that means nothing. A motion metric of an \
episode that ended before its horizon is unmeasured and fails the seed, \
so a policy cannot pass by ending early. Still watch the film before you \
accept a pass: a predicate says how much the body moved, the film says \
whether it moved as the machine should.

THE PROJECT IS A CODEBASE. Beside the script it keeps ARCHITECTURE.md \
(what it is, what the script declares, where the domain docs are), \
DECISIONS.md (its own ADR log: what was chosen, over what, why) and \
PROGRESS.md (one row per accepted run, with the numbers). Read them before \
you act, and do not repeat work a row says was already tried. Record each \
decision yourself as a numbered entry in DECISIONS.md. Longer notes go \
under docs/, one file per subject: docs/actuators.md for what drives each \
joint and the torque, speed and damping you assumed, docs/sensors.md for \
what each sensor measures, docs/gear-ratios.md for a ratio you chose and \
docs/rejected.md for an approach you tried and dropped. Write what the \
next session would need, not what this one can already see. \
docs/inventory.md and docs/clearance.md are the CLI's own reports, and \
PROGRESS.md is the CLI's too: this server lands a row, and a commit in the \
project's own repository, each time it lets go of a session that changed \
the design.

YOU MAY GIVE THE DASHBOARD A STATUS PANEL. The dashboard's Status already \
charts reward, loss, episode length and action std, the latest evaluation \
and every run. For what only this machine has -- a measurement per run, a \
predicate's margin, a quantity the evaluation reports -- write status.html \
at the project's root with your file tools; Status then shows it under a \
Project tab. It runs in a sandbox that can fetch nothing, the project's own \
files included: everything it draws arrives as a `cadex-status-panel-v1` \
message the page posts on every poll (the stage, the run's curves, every \
run, every evaluation with the newest one's predicates, and the theme's \
colour tokens). Draw inline SVG from that message alone, in those tokens, \
one measure per chart. The message, the style guide and a skeleton to start \
from are in docs/DASHBOARD.md, section 23, in the Cadex repository that \
holds the `cadex` command you run. Keep it under \
512 KB, and say in DECISIONS.md what it shows and why.

WHEN A QUESTION'S ANSWER WOULD CHANGE THE DESIGN, ask the person. When it \
would not, carry on with the most reversible assumption and say which one \
you took.

A HARNESS IS DECLARED, NOT DRAWN. Boards, their terminals and the nets \
between them are rows in the script -- `boards(...)` and `nets(...)`, whose \
row shapes describe_api gives -- and set_params can change \
those rows without touching the source. A catalog board already carries \
its terminals: use its rows as they are, never re-measure them. \
inspect scope=wiring reads back what was routed.

REVISION GUARDS ARE HANDLED FOR YOU. Every tool result reports the revision \
it produced, and the next call is guarded with it automatically. You never \
need to pass expected_revision, and you should not try.

BE DONE WHEN IT IS BUILT AND YOU HAVE LOOKED AT IT. Say in a short \
paragraph what you built and which parameters can now be swept.
"""


def instructions(style: str = "") -> str:
    """The whole guidance, as ``cadex guidance`` prints it: the base, and the
    project's chosen style after it when there is one (ADR-560)."""

    if not style:
        return OVERLAY
    return OVERLAY + "\n" + style_guidance(style)


#: The repository's ``cadex`` shim, which is how an agent's shell reaches the
#: whole guidance whatever directory it runs in.
CADEX_COMMAND = str(Path(__file__).resolve().parents[2] / "cadex")

#: Bound on the brief: Claude Code cuts a server's instructions at 2,048
#: characters unless ``CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH`` says
#: otherwise, so the brief fits and points at the whole text.
BRIEF_LIMIT = 2_000


def brief(project: str = "<the project>", command: str = CADEX_COMMAND, style: str = "") -> str:
    """What ``cadex mcp`` sends as its ``instructions``: short enough that no
    client cuts it, and the one step that gets the agent the rest."""

    text = (
        "You are driving Cadex, a CAD engine for robots and mechanisms, through "
        "this server's tools; the person watches every revision you land in the "
        "read-only Cadex dashboard. BEFORE YOUR FIRST TOOL CALL, run "
        f"`{command} guidance --project {project}` in your shell and follow what "
        "it prints: it is "
        "how to author, prove, design and train with these tools, and it is too "
        "long to arrive here whole. The short of it: the design is one "
        "parametric xscript (write_script, edit_script, set_params); call "
        "describe_api, then describe_api section=<domain>, before writing one, "
        "and never write the API from memory; trust the `fit` block over "
        "anything a script prints; see your work with `look`; lengths are mm "
        "and +Z is up; record decisions in the project's DECISIONS.md; run "
        f"other legs as `{command} <command> --project {project} --wait "
        "--json`."
        + (f" This project chose the design style `{style}`, and the guidance "
           "carries it." if style else "")
    )
    assert len(text) <= BRIEF_LIMIT, len(text)
    return text
