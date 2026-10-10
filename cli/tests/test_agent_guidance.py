# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The guidance any agent driving Cadex is given (ADR-446, ADR-538).

One text: ``cadex guidance`` prints it, and ``cadex mcp`` sends a brief
that fits a client's cap and tells the agent to read it. It carries the engine's
own guidance verbatim, with the tool names filled in, and says nothing
that only held while Cadex ran its own agent.
"""
import io
import json
import re
from pathlib import Path

import pytest

from cadex_cli import mcp
from cadex_cli.__main__ import main
from cadex_cli.guidance import (
    BRIEF_LIMIT, CADEX_COMMAND, GUIDANCE_FILE, OVERLAY, TOOL_NAMES, agent_guidance, brief, instructions,
    style_guidance, style_summary, styles,
)
from cadex_cli.session import read_agent_state, write_agent_budgets
from cadex_cli.studio import ENGINE_MODULE_DIR


def test_the_overlay_carries_the_engines_guidance_verbatim():
    guidance = agent_guidance(ENGINE_MODULE_DIR, TOOL_NAMES)
    assert guidance in OVERLAY and '{{' not in OVERLAY
    assert guidance.startswith('YOU SEE YOUR WORK WITH `look`')
    # The situation stays around it: the parametric rule before, the CLI,
    # asset and project-docs rules after.
    assert OVERLAY.index('BUILD IT PARAMETRIC') < OVERLAY.index(guidance)
    assert OVERLAY.index(guidance) < OVERLAY.index('THE CLI COVERS WHAT THE TOOLS DO NOT')
    assert OVERLAY.index(guidance) < OVERLAY.index('A FILE THE PERSON HANDS YOU')


def test_the_guidance_is_for_an_agent_with_a_shell_and_files():
    """ADR-538: the agent is the person's own, so nothing tells it it has no
    shell, that nobody is watching, or to speak in closing-line conventions
    the CLI used to scrape."""

    text = instructions()
    for gone in ('You have no shell', 'NOBODY IS WATCHING', 'DECISION:', 'NOTE <subject>',
                 'leave_note', 'cadex -p', 'next turn'):
        assert gone not in text, gone
    for needed in ('DECISIONS.md', '--wait', 'read-only', 'cadex app'):
        assert needed in text, needed


def test_a_placeholder_this_client_does_not_fill_is_refused(tmp_path):
    source = (Path(ENGINE_MODULE_DIR) / GUIDANCE_FILE).read_text(encoding='utf-8')
    (tmp_path / GUIDANCE_FILE).write_text(source + 'Then {{render_views}}.\n', encoding='utf-8')
    with pytest.raises(RuntimeError, match='render_views'):
        agent_guidance(tmp_path, TOOL_NAMES)
    (tmp_path / GUIDANCE_FILE).write_text('no marker here\n', encoding='utf-8')
    with pytest.raises(RuntimeError, match='marker|guidance'):
        agent_guidance(tmp_path, TOOL_NAMES)


def test_mcp_sends_a_brief_that_fits_and_points_at_the_whole(capsys):
    """Claude Code cuts a server's instructions at 2,048 characters by
    default, so ``cadex mcp`` sends a brief that fits and names the command
    that prints the whole guidance, which ``cadex guidance`` does."""

    assert main(['guidance']) == 0
    assert capsys.readouterr().out == instructions()

    class Host:
        def instructions(self):
            return brief('/p/bracket')

    stream = io.StringIO()
    mcp.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}}, Host(), stream)
    sent = json.loads(stream.getvalue())['result']['instructions']
    assert len(sent) <= BRIEF_LIMIT < 2048
    assert f'`{CADEX_COMMAND} guidance --project /p/bracket`' in sent
    assert '--project /p/bracket --wait' in sent and 'style' not in sent
    assert Path(CADEX_COMMAND).is_file()
    chose = brief('/p/bracket', style='printed-legged-robot')
    assert len(chose) <= BRIEF_LIMIT and 'design style `printed-legged-robot`' in chose


STYLE = 'printed-legged-robot'
#: The kinds of machine and the looks the base never assumes (ADR-560).
NOT_IN_THE_BASE = ('biped', 'quadruped', 'hexapod', 'humanoid', 'legged', 'mascot',
                   'look engineered', 'looks engineered', 'small printed robot')
#: How a project's name reads; no text an agent is given names one (ADR-560).
PROJECT_NAME = (r'biped-sts|ball-plate|excavator-mini|biped-new|biped-mg90|quad-qdd|mg-legs|\bhex\d|\bot\d+\b|\borun\d|'
                r'\bsweep-|digestbug|\blark\b|\bwren\b|cadex-projects')


def _style_lines(style):
    """Every rule line of a style, as the agent reads it."""
    return [line for line in style_guidance(style).splitlines() if len(line) > 40]


def test_the_base_guidance_names_no_kind_of_machine_as_the_default():
    base = instructions().lower()
    assert base == OVERLAY.lower()
    for word in NOT_IN_THE_BASE:
        assert re.search(r'\b' + re.escape(word) + r's?\b', base) is None, word
    assert 'form follows function' in base


def test_no_style_text_appears_unless_the_project_chose_one(tmp_path, capsys):
    assert STYLE in styles()
    for style in styles():
        for line in _style_lines(style):
            assert line not in OVERLAY, line
    # A project with no agent.json, and one with budgets but no style, get the base alone.
    assert main(['guidance', '--project', str(tmp_path)]) == 0
    assert capsys.readouterr().out == OVERLAY
    write_agent_budgets(tmp_path, {'timeout_seconds': 900})
    assert main(['guidance', '--project', str(tmp_path)]) == 0
    assert capsys.readouterr().out == OVERLAY


def test_a_project_chooses_a_style_and_its_guidance_carries_it(tmp_path, capsys):
    assert main(['style', '--project', str(tmp_path), '--json']) == 0
    listed = json.loads(capsys.readouterr().out)
    about = {name: style_summary(name) for name in styles()}
    assert listed['style'] == {'chosen': '', 'available': styles(), 'about': about}
    # A bare report says what each style is for, so an agent can choose the
    # one its brief names (ADR-625).
    assert [f'{name}: {text}' for name, text in about.items()] == listed['notes']
    assert 'creature' in about and 'animal' in about['creature']
    for name in ('gantry-machine', 'vehicle', 'product'):
        assert name in about and 'provisional' not in about[name], name

    assert main(['style', '--project', str(tmp_path), STYLE, '--json']) == 0
    assert json.loads(capsys.readouterr().out)['style']['chosen'] == STYLE
    assert read_agent_state(tmp_path).style == STYLE
    assert main(['guidance', '--project', str(tmp_path)]) == 0
    text = capsys.readouterr().out
    assert text == instructions(STYLE) and text.startswith(OVERLAY)
    for line in _style_lines(STYLE):
        assert line in text[len(OVERLAY):]
    # Storing a budget keeps the style; the brief cadex mcp sends names it.
    assert write_agent_budgets(tmp_path, {'memory_limit_mb': 4096}).style == STYLE

    assert main(['style', '--project', str(tmp_path), 'crane-yard', '--json']) != 0
    capsys.readouterr()
    assert read_agent_state(tmp_path).style == STYLE

    assert main(['style', '--project', str(tmp_path), '--clear', '--json']) == 0
    capsys.readouterr()
    assert read_agent_state(tmp_path).style == ''
    assert main(['guidance', '--project', str(tmp_path)]) == 0
    assert capsys.readouterr().out == OVERLAY


#: What a brief says, and the one style whose sentence it should land on
#: (ADR-653). The overlay names each family by example; `cadex style
#: --json`'s `about` is what the agent matches.
BRIEFS = {
    'animal': 'creature', '3D printer': 'gantry-machine', 'CNC': 'gantry-machine',
    'laser cutter': 'gantry-machine', 'liquid handler': 'gantry-machine',
    'mower': 'vehicle', 'tractor': 'vehicle', 'loader': 'vehicle', 'rover': 'vehicle',
    'appliance': 'product', 'instrument': 'product',
}


def test_the_style_choice_lands_each_kind_of_brief_on_one_style():
    """The overlay tells the agent how to match a brief, and each family it
    names by example lands on exactly one style's sentence."""

    about = {name: style_summary(name) for name in styles()}
    text = " ".join(OVERLAY.split())
    choose = _rule(text, "CHOOSE THE STYLE THE BRIEF NAMES", 2200)
    for word, style in BRIEFS.items():
        assert [name for name, said in about.items() if word in said] == [style], word
    for example in ('an animal or a character', 'a printer, a CNC or a liquid handler',
                    'a mower, a tractor, a loader or a rover', 'appliance or instrument',
                    'When two fit', 'a robot mower is a vehicle first', 'choose none',
                    'provisional', 'the measurement wins'):
        assert example in choose, example


def test_a_placeholder_line_is_dropped_before_the_agent_reads_it():
    """ADR-654: a guidance line that is wholly an HTML comment marks a
    placeholder for maintainers; the paragraph after it reaches the agent,
    the comment never does."""

    body = agent_guidance(ENGINE_MODULE_DIR, TOOL_NAMES)
    assert '<!--' not in body and '<!--' not in instructions(STYLE)
    assert '\nCOVERS AND PANELS.' in body and '\nMOTION PARTS.' in body


def test_a_stored_style_the_engine_does_not_carry_is_refused_not_dropped(tmp_path, capsys):
    (tmp_path / 'agent.json').write_text(json.dumps(
        {'schema': 'cadex-cli-agent-v1', 'style': 'gone-style'}), encoding='utf-8')
    assert main(['guidance', '--project', str(tmp_path)]) != 0
    assert 'gone-style' in capsys.readouterr().err


def test_no_text_an_agent_is_given_names_a_project():
    texts = {'base': OVERLAY, 'brief': brief('/p', style=STYLE)}
    texts.update({style: style_guidance(style) for style in styles()})
    for name, text in texts.items():
        found = re.findall(PROJECT_NAME, text, re.I)
        assert not found, (name, found)


#: A project directory's name, as distinct from a run's (``ot10``, ``orun1``):
#: the read-only projects and the run families' scratch copies.
PROJECT_DIR = (r'biped-sts|ball-plate|excavator-mini|biped-new|biped-mg90|quad-qdd|mg-legs|\bhex\d|\bot\d+-|\borun\d-|'
               r'\bsweep-|digestbug|cadex-projects')
REPO = Path(__file__).resolve().parents[2]


def test_no_guidance_file_names_a_project_and_the_doc_lost_look_engineered():
    """Every file the guidance is made of -- the engine's base and styles, the
    CLI's module, and the doc they are cited from -- names no project, and the
    doc no longer asks for a machine that looks engineered (ADR-560)."""

    files = [REPO / 'cli/cadex_cli/guidance.py', REPO / 'docs/DESIGN-LANGUAGE.md',
             ENGINE_MODULE_DIR / 'CadexAgentGuidance.md',
             *sorted(ENGINE_MODULE_DIR.glob('CadexAgentStyle.*.md'))]
    for path in files:
        text = path.read_text(encoding='utf-8')
        found = re.findall(PROJECT_DIR, text, re.I)
        assert not found, (path.name, found)
    doc = (REPO / 'docs/DESIGN-LANGUAGE.md').read_text(encoding='utf-8').lower()
    assert re.search(r'looks? engineered', doc) is None


def test_the_mcp_server_instructions_follow_the_projects_style(tmp_path):
    """What ``cadex mcp`` sends at ``initialize`` reads the project's
    ``agent.json``: no style named when none is chosen, the chosen one when
    it is, and the command it sends the agent to prints exactly that."""

    from argparse import Namespace
    from cadex_cli.__main__ import McpSession

    session = McpSession.__new__(McpSession)
    session.args = Namespace(project=str(tmp_path))
    plain = session.instructions()
    assert 'style' not in plain and f'guidance --project {tmp_path.resolve()}' in plain
    assert main(['style', '--project', str(tmp_path), STYLE]) == 0
    chosen = session.instructions()
    assert f'design style `{STYLE}`' in chosen and len(chosen) <= BRIEF_LIMIT


def test_the_training_lessons_are_in_the_base_and_reach_every_project():
    # ADR-565: training practice the reference legged robot learned the hard
    # way, phrased for any task, so it is in the base with no style chosen.
    text = " ".join(instructions().split())
    for rule in ("TRAIN SO A GOOD POLICY CAN BE KEPT", "Set checkpoint_every on any run",
                 "never by taking the last iteration",
                 "Never tighten action_filter_alpha on a warm start",
                 "start cold after any change to the model"):
        assert rule in text, rule


def test_the_reward_shaping_lessons_are_for_any_task():
    # ADR-586: what a balancing table and a reaching arm taught, for any
    # task with no style chosen -- a slope where episodes start, signed
    # progress for a repeated motion, and stopping a reward revision that
    # moves nothing. (Counting laps by hand from traces gave way to the
    # motion predicates, ADR-587, ADR-596.)
    text = " ".join(instructions().split())
    for rule in ("SHAPE A REWARD THE POLICY CAN CLIMB", "needs a slope where episodes start",
                 "pays signed progress along it",
                 "stop revising the reward", "set command_slew_deg from the first run"):
        assert rule in text, rule


def _rule(text, head, length=4000):
    start = text.index(head)
    return text[start:start + length]


def test_a_motion_is_stated_as_a_predicate_with_its_reason():
    # ADR-596: the motion predicates (ADR-587) reach every project as a
    # rule -- turns and laps for going round, distance from a point with no
    # goal declared, an early end failing -- with the reason it exists.
    text = " ".join(instructions().split())
    rule = _rule(text, "STATE THE MOTION AS A PREDICATE", 1600)
    for claim in ("rocks on a short arc", "body=<component>", "centre=<component>",
                  "bound `turns`", "rocking out and back reads about 0", "`laps`",
                  "`final_distance_mm`", "`mean_distance_mm`", "These need no goal",
                  "never declare a goal only to get a distance", "is unmeasured and fails"):
        assert claim in rule, claim
    assert "count it in the evaluation's traces" not in text


def test_the_sensor_rule_grounds_position_and_load_on_real_parts():
    # ADR-596: choosing a sensor -- a tracker on the reader's mount with its
    # datasheet, out of range as a termination, load only from an actuator
    # that reports it, a goal in the moving base's frame, and privileged
    # when no part on the market would measure it.
    text = " ".join(instructions().split())
    # Since ADR-650 the datasheet arguments are describe_api's to give
    # (assembly.sensor's own docstring); the rule keeps the principle.
    rule = _rule(text, "CHOOSE A SENSOR A REAL PART COULD BE", 1200)
    for claim in ("cannot run on the machine", "declare its datasheet figures", '"position_tracker"',
                  '"tracked_position"', "terminated on its `_in_range` flag",
                  ".load_sensor(actuator", "only on an actuator that reports effort",
                  "frame=base", "it is privileged", 'role="privileged"'):
        assert claim in rule, claim


def test_the_linkage_rule_says_when_to_close_a_chain_and_how_it_is_proved():
    # ADR-596: when a closed chain beats serial joints and why, how a loop
    # is declared and driven, and what is refused. Since ADR-621 the sweep
    # drives a loop from its limited joints and a planar revolute loop is
    # accepted per linkage.
    text = " ".join(instructions().split())
    rule = _rule(text, "CLOSE A LINKAGE WHERE THE BUILT MACHINE WOULD HAVE ONE", 2000)
    for claim in ("A serial stand-in for a linkage is a different machine",
                  "the actuator should stay on the frame", "choose serial joints when",
                  "dead point", "A loop closes with an ordinary joint", "equality constraint",
                  "over-constrained", "ball joint", "parallel revolute pins is accepted",
                  "drives the loop from its limited joints", "the smoke check"):
        assert claim in rule, claim


def test_the_checkpoint_rule_says_what_it_does_and_what_it_costs():
    # ADR-577: a rule, not a ritual. The agent is told what a checkpoint
    # buys and what it costs since ADR-576 (one compile, then about one
    # iteration each), and no longer to set it on every run or because
    # someone is watching.
    text = " ".join(instructions().split())
    start = text.index("TRAIN SO A GOOD POLICY CAN BE KEPT")
    rule = text[start:text.index("Choose the policy to keep", start)]
    for claim in ("What it does:", "witness-checked policy", "a stopped run still leaves one",
                  "plays each checkpoint in the dashboard's viewport", "What it costs:",
                  "compiles the witness rollout once", "about one training iteration",
                  "leave it off only for a run you will throw away"):
        assert claim in rule, claim
    assert "on every run" not in rule and "watching" not in rule


def test_the_style_s_foot_thigh_and_roll_rules_reach_a_project_that_chose_it(tmp_path, capsys):
    # ADR-566: the three rules the fresh-session check found too loose reach
    # the agent through `cadex guidance --project`, and never the base.
    assert main(['style', '--project', str(tmp_path), STYLE]) == 0
    capsys.readouterr()
    assert main(['guidance', '--project', str(tmp_path)]) == 0
    chosen = " ".join(capsys.readouterr().out.split())
    base = " ".join(instructions().split())
    for rule in ('COMPACT IS MEASURED', 'an eighth wide is a good start', 'A SPRAWLED LEG',
                 'MEASURE WHERE THE FEET MEET', 'bracket it outward from the standing pose'):
        assert rule in chosen and rule not in base, rule
