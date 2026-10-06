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
    style_guidance, styles,
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
PROJECT_NAME = (r'biped-sts|biped-mg90|quad-qdd|mg-legs|\bhex\d|\bot\d+\b|\borun\d|'
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
    assert listed['style'] == {'chosen': '', 'available': styles()}

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
