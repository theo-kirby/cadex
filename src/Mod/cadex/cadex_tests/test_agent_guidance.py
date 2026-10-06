# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The agent guidance is engine data every front end pastes in (ADR-446).

``CadexAgentGuidance.md`` is read, not imported: by the CLI from the engine it
resolved and by the shell from its bundled payload. These tests pin what both
readers rely on -- one marker line and a closed set of tool placeholders --
and that the payload ships the file. The base is domain-neutral and each
style is named and optional (ADR-560): a style's file has the same shape,
and the base names no kind of machine as the default and no project.
"""
from __future__ import annotations

from pathlib import Path
import re

MODULE_DIR = Path(__file__).resolve().parents[1]
SOURCE = MODULE_DIR / 'CadexAgentGuidance.md'
MARKER = '<!-- guidance -->\n'
#: Every placeholder a client must fill. Adding one is a change to every client.
PLACEHOLDERS = {'look', 'inspect', 'write_script', 'edit_script', 'set_params', 'rebuild'}


#: Every style the engine carries (ADR-560): ``CadexAgentStyle.<name>.md``.
STYLES = sorted(MODULE_DIR.glob('CadexAgentStyle.*.md'))
#: A kind of machine, or a look, the base may never assume (ADR-560).
NOT_IN_THE_BASE = ('biped', 'quadruped', 'hexapod', 'humanoid', 'legged', 'walking leg',
                   'mascot', 'look engineered', 'looks engineered', 'small printed robot',
                   'eyes', 'visor', 'horn cap', 'thigh', 'shin', 'femur', 'tibia')
#: How a project's name reads: the reference and probe projects, the run
#: families' scratch copies, the ot5-ot11 fixtures. No guidance text names one.
PROJECT_NAME = (r'biped-sts|biped-mg90|quad-qdd|mg-legs|\bhex\d|\bot\d+\b|\borun\d|'
                r'\bsweep-|digestbug|\blark\b|\bwren\b|cadex-projects')


def _body(source=SOURCE):
    head, marker, body = source.read_text(encoding='utf-8').partition(MARKER)
    assert marker and head.startswith('<!--') and head.rstrip().endswith('-->')
    return body


def test_the_guidance_uses_only_the_declared_placeholders():
    assert set(re.findall(r'\{\{(\w+)\}\}', _body())) == PLACEHOLDERS


def test_the_guidance_carries_the_design_language_and_the_proof_rules():
    body = _body()
    for heading in ('YOU SEE YOUR WORK WITH `{{look}}`', 'FIT IS MEASURED, NOT PRINTED',
                    'DESIGN IT; DO NOT ONLY MAKE IT FIT', 'CONCEPT FIRST', 'PARTS FIRST',
                    'PLACE THEM', 'STRUCTURE THAT CARRIES THEM', '5. FINISH',
                    'REFINE WITH `{{look}}`', 'A SELF-MOVING MACHINE IS COMPLETE',
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
    for style in STYLES:
        assert f'    {style.name}\n' in cmake, style.name


def test_the_base_names_no_kind_of_machine_and_no_look_as_the_default():
    body = _body().lower()
    for word in NOT_IN_THE_BASE:
        assert re.search(r'\b' + re.escape(word) + r's?\b', body) is None, word
    assert 'form follows function' in body


def test_there_is_a_printed_legged_robot_style_and_every_style_is_well_formed():
    assert 'printed-legged-robot' in [s.name[len('CadexAgentStyle.'):-len('.md')] for s in STYLES]
    for style in STYLES:
        body = _body(style)
        assert set(re.findall(r'\{\{(\w+)\}\}', body)) <= PLACEHOLDERS, style.name
        assert body.startswith('STYLE: '), style.name
        # A style adds to the base and never restates it.
        assert 'FIT IS MEASURED' not in body and 'HOLD EVERY PART' not in body


def test_the_style_carries_what_left_the_base():
    body = _body(MODULE_DIR / 'CadexAgentStyle.printed-legged-robot.md')
    for rule in ('ONE OF TWO FINISHES', 'EXPOSED MECHANISM', 'PANELLED HARD SURFACE',
                 'NOT THE MASCOT BOX', 'NO FACE', 'JOINTS ARE FEATURES',
                 'LEGS ARE LONG AGAINST THEIR JOINTS', 'TWO MATERIALS AND ONE SMALL ACCENT'):
        assert rule in body, rule
        assert rule not in _body(), rule


def test_no_guidance_file_names_a_project():
    for source in [SOURCE, *STYLES]:
        found = re.findall(PROJECT_NAME, source.read_text(encoding='utf-8'), re.I)
        assert not found, (source.name, found)


#: What the reference legged robot taught, by the paragraph that carries it
#: (ADR-565, docs/probes/orun4/LESSONS.md). The base rules hold for any machine.
BASE_LESSONS = ('A SOLID BUILT FROM TANGENT PRIMITIVES IS MEASURED', 'SET A LIMIT FROM THE SWEEP',
                'THE SIMULATED BODY IS THE BUILT BODY', 'under its centre of mass, measured on the model',
                'Bound it on both sides', 'THE TARGET SPEED MAKES THE INTENDED MOTION THE EASY ONE',
                'CENTRE THE COMMAND RANGE ON THE REST POSE', 'PAY FOR PROGRESS ONLY WHILE UPRIGHT',
                'A CHARGE AGAINST A DEGENERATE MOTION HAS A CEILING')
STYLE_LESSONS = ('THE LOOK OF A LIMB', 'lightening window', 'ACTUATORS INSIDE THE LIMB',
                 'FEET ARE COMPACT HULLS WITH A FLAT STRIP', 'never a large or flat plate',
                 'two keels with a flat strip between them', 'HIPS WIDE ENOUGH FOR THE FEET TO PASS',
                 'inward much tighter than outward', 'THE STEP IS WHAT IS PAID')


def test_the_reference_lessons_are_in_the_base_and_the_style_they_belong_to():
    base = _body()
    style = _body(MODULE_DIR / 'CadexAgentStyle.printed-legged-robot.md')
    for rule in BASE_LESSONS:
        assert rule in base, rule
        assert rule not in style, rule
    for rule in STYLE_LESSONS:
        assert rule in style, rule
        assert rule not in base, rule
    # Lessons enter as rules, never as the reference robot's numbers made defaults.
    for number in ('160 mm/s', '52 mm', '64 mm', '0.65 kg', '8 degrees'):
        assert number not in base + style, number


def test_the_style_bounds_the_foot_scopes_the_level_thigh_and_derives_the_roll_limit():
    # ADR-566: the fresh-session check (docs/probes/orun4/FRESH-SESSION.md)
    # met every rule but these three as worded. "Compact" without a number
    # let a 72 x 40 mm slab under a 210 mm robot through; the level-thigh rule
    # was written for a sprawled leg; and an inward roll limit picked first
    # and found clear by the sweep was taken for one derived from it.
    style = " ".join(_body(MODULE_DIR / 'CadexAgentStyle.printed-legged-robot.md').split())
    for rule in ('COMPACT HAS A NUMBER', 'no longer than a quarter of it and no wider than an eighth of it',
                 'never from the foot\'s area',
                 'A SPRAWLED LEG', 'An UPRIGHT LEG under the body', 'the level-thigh rule is not for it',
                 'MEASURE WHERE THE FEET MEET', "first_contact",
                 'write both angles in DECISIONS.md'):
        assert rule in style, rule
        assert rule not in _body(), rule
    # The level thigh is only ever asked of a sprawled leg.
    assert style.index('A SPRAWLED LEG') < style.index('thigh running out level') < style.index('An UPRIGHT LEG')


def test_the_roll_limit_is_bracketed_outward_from_the_standing_pose():
    # ADR-567: the sweep's first_contact is the first contacting sample counted
    # from the range's lower limit (docs/INTEGRATION.md), so on an inward side
    # that runs negative it is the deepest contact, not the onset. The second
    # fresh session (docs/probes/orun4/FRESH-SESSION-2.md) found that reading it
    # off a range opened wide, as ADR-566 worded the style, puts the limit
    # inside the collision. The style brackets the angle outward instead.
    style = " ".join(_body(MODULE_DIR / 'CadexAgentStyle.printed-legged-robot.md').split())
    for rule in ('bracket it outward from the standing pose', 'the last clear angle',
                 'the first contact angle', 'deepest contact, not where contact starts',
                 'short of the first contact by at least two sweep steps'):
        assert rule in style, rule
        assert rule not in _body(), rule
    # The procedure that set a limit inside the collision is gone.
    assert 'inward limit opened wide' not in style
    assert 'read that joint row' not in style
