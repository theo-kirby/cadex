# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The CLI's prompt carries the engine's agent guidance, with its own tool names (ADR-446)."""
from pathlib import Path

import pytest

from cadex_cli.agent import CLI_OVERLAY, CLI_TOOL_NAMES, GUIDANCE_FILE, agent_guidance
from cadex_cli.studio import ENGINE_MODULE_DIR


def test_the_overlay_carries_the_engines_guidance_verbatim():
    guidance = agent_guidance(ENGINE_MODULE_DIR, CLI_TOOL_NAMES)
    assert guidance in CLI_OVERLAY and '{{' not in CLI_OVERLAY
    assert guidance.startswith('YOU SEE YOUR WORK WITH `look`')
    # The CLI's own situation stays around it: the parametric rule before, the
    # asset and project-docs rules after.
    assert CLI_OVERLAY.index('BUILD IT PARAMETRIC') < CLI_OVERLAY.index(guidance)
    assert CLI_OVERLAY.index(guidance) < CLI_OVERLAY.index('A FILE THE CALLER HANDS YOU')


def test_a_placeholder_this_client_does_not_fill_is_refused(tmp_path):
    source = (Path(ENGINE_MODULE_DIR) / GUIDANCE_FILE).read_text(encoding='utf-8')
    (tmp_path / GUIDANCE_FILE).write_text(source + 'Then {{render_views}}.\n', encoding='utf-8')
    with pytest.raises(RuntimeError, match='render_views'):
        agent_guidance(tmp_path, CLI_TOOL_NAMES)
    (tmp_path / GUIDANCE_FILE).write_text('no marker here\n', encoding='utf-8')
    with pytest.raises(RuntimeError, match='marker|guidance'):
        agent_guidance(tmp_path, CLI_TOOL_NAMES)
