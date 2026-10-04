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
from pathlib import Path

import pytest

from cadex_cli import mcp
from cadex_cli.__main__ import main
from cadex_cli.guidance import (
    BRIEF_LIMIT, CADEX_COMMAND, GUIDANCE_FILE, OVERLAY, TOOL_NAMES, agent_guidance, brief, instructions,
)
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
    assert f'`{CADEX_COMMAND} guidance`' in sent and '--project /p/bracket --wait' in sent
    assert Path(CADEX_COMMAND).is_file()
