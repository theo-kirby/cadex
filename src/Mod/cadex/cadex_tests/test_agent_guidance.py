# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The agent guidance is engine data every front end pastes in (ADR-446).

``CadexAgentGuidance.md`` is read, not imported: by the CLI from the engine it
resolved and by the shell from its bundled payload. These tests pin what both
readers rely on -- one marker line and a closed set of tool placeholders --
and that the payload ships the file.
"""
from __future__ import annotations

from pathlib import Path
import re

MODULE_DIR = Path(__file__).resolve().parents[1]
SOURCE = MODULE_DIR / 'CadexAgentGuidance.md'
MARKER = '<!-- guidance -->\n'
#: Every placeholder a client must fill. Adding one is a change to every client.
PLACEHOLDERS = {'look', 'inspect', 'write_script', 'edit_script', 'set_params', 'rebuild'}


def _body():
    head, marker, body = SOURCE.read_text(encoding='utf-8').partition(MARKER)
    assert marker and head.startswith('<!--') and head.rstrip().endswith('-->')
    return body


def test_the_guidance_uses_only_the_declared_placeholders():
    assert set(re.findall(r'\{\{(\w+)\}\}', _body())) == PLACEHOLDERS


def test_the_guidance_carries_the_design_language_and_the_proof_rules():
    body = _body()
    for heading in ('YOU SEE YOUR WORK WITH `{{look}}`', 'FIT IS MEASURED, NOT PRINTED',
                    'DESIGN IT; DO NOT ONLY MAKE IT FIT', 'CONCEPT FIRST', 'PARTS FIRST',
                    'PLACE THEM', 'STRUCTURE THAT CARRIES THEM', '5. FINISH',
                    'REFINE WITH `{{look}}`', 'A ROBOT IS A COMPLETE MACHINE',
                    'GROUND WHAT THE POLICY READS', 'A WALKING TASK PAYS FOR WALKING',
                    'WHEN A CALL IS REFUSED'):
        assert heading in body, heading
    # Nothing that only one front end can do: no CLI subcommand, no shell tool.
    assert 'cadex ' not in body.replace('Cadex ', '')
    for shell_only in ('render_views', 'viewport_screenshot', 'inspect_model', 'rebuild_model'):
        assert shell_only not in body



def test_the_guidance_checks_the_rest_contacts_after_an_mjcf_export():
    # The shell's overlay asked for the collision shapes and the t=0 contact
    # line after assembly.mjcf; the engine's guidance carries it for every
    # front end (docs/SHELL-PARITY.md section 4, ADR-521).
    body = _body()
    assert '`{{inspect}} scope=contacts` after an `assembly.mjcf` export' in body
    assert 'the pose every simulation starts from' in body
    assert 'fix its `offset` before you train on it' in body


def test_the_payload_ships_the_guidance():
    cmake = (MODULE_DIR / 'CMakeLists.txt').read_text(encoding='utf-8')
    assert '    CadexAgentGuidance.md\n' in cmake
