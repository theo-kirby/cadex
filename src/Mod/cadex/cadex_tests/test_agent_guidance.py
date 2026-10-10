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
                   'eyes', 'visor', 'horn cap', 'thigh', 'shin', 'femur', 'tibia',
                   # ADR-650: the animal, gait and servo-tier material left
                   # the base for the styles that need it.
                   'animal', 'creature', 'neck', 'tail', 'jaw', 'gait', 'stride', 'foot', 'feet',
                   'servo', 'qdd', 'cubemars', 'esp32', 'sts3215')
#: The base is short (ADR-650): about 2,500 words, down from about 6,000.
BASE_WORD_BUDGET = 2700
#: A provisional style is short and says so (ADR-653).
PROVISIONAL_WORD_BUDGET = 600
#: The placeholder each parallel line of work replaces, and the paragraph
#: that follows it (ADR-654).
PLACEHOLDERS_FOR: dict[str, str] = {}
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
                    'A MET CHECK IS A FLOOR, NOT THE GOAL', 'MOVING REGIONS',
                    'GROUND WHAT THE POLICY READS', 'A LEARNED MOTION PAYS FOR THE MOTION',
                    'SAY WHAT IS UNFINISHED', 'WHEN A CALL IS REFUSED'):
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


def _words(source):
    """What an agent reads of a guidance file, in words: the body less the
    maintainers' comment lines, which the client drops (ADR-654)."""
    return len(' '.join(line for line in _body(source).splitlines()
                        if not re.fullmatch(r'<!--.*-->', line.strip())).split())


def test_the_base_is_short_and_states_its_checks_as_floors():
    # ADR-650: the base keeps what holds for any machine -- the loop, the
    # measured facts, the blocks as floors, honesty about what is unfinished
    # -- and leaves how to read each block to the block's own note.
    assert _words(SOURCE) <= BASE_WORD_BUDGET
    body = ' '.join(_body().split())
    for claim in ("each says in its own `source` and `note` what it measured",
                  'is never a pass', 'A MET CHECK IS A FLOOR, NOT THE GOAL',
                  'The bar is a real product', 'how real machines of this kind are built',
                  'list it in DECISIONS.md as unfinished', 'hides a stand-in'):
        assert claim in body, claim
    # The walking task left with the legged look: the base pays any learned
    # motion, and names no stride.
    assert 'A WALKING TASK' not in body


def test_the_base_placeholders_are_all_filled():
    # ADR-654 left a marked placeholder for the panel system and the motion
    # parts; both have landed and replaced theirs (ADR-638, ADR-647).
    lines = _body().splitlines()
    for name, paragraph in PLACEHOLDERS_FOR.items():
        (at,) = [i for i, line in enumerate(lines) if line.startswith(f'<!-- placeholder: {name}.')]
        assert lines[at + 1].startswith(paragraph), name
        assert 'describe_api' in lines[at + 1], name
    assert '<!-- placeholder:' not in _body()


def test_the_motion_parts_paragraph_teaches_the_machine_joints_and_parts():
    # ADR-640..646 landed, so the motion-parts placeholder is replaced (ADR-647).
    # The panels one went the same way with ADR-633..637 (ADR-638).
    body = _body()
    assert '<!-- placeholder: motion parts' not in body
    (paragraph,) = [line for line in body.splitlines() if line.startswith('MOTION PARTS.')]
    for name in ('lib.part(sku', 'section=library_parts', '`screw` joint', '`rack_pinion` joint',
                 'assembly.coupling(', 'kind="cylinder"', 'assembly.joint_dynamics',
                 'assembly.tool(', '`workspace` block', 'stand-in'):
        assert name in paragraph, name
    (covers,) = [line for line in body.splitlines() if line.startswith('COVERS AND PANELS.')]
    for name in ('part.envelope(', 'part.panel(', 'role="panel", covers=[...]', 'fit.panels',
                 'panel.pilots', 'motion='):
        assert name in covers, name


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
                 'LEGS ARE LONG AGAINST THEIR JOINTS', 'TWO MATERIALS AND ONE SMALL ACCENT',
                 # ADR-652: the servo-tier kit left the base for this style.
                 'THE KIT', 'SERVOS SIT IN THE LINK', 'lib.servo("sts3215")',
                 'lib.board("pca9685-adafruit-rev-c")', 'servo.bay(ledge=4)', 'joint_encoder'):
        assert rule in body, rule
        assert rule not in _body(), rule


def test_what_the_base_said_of_one_family_is_in_that_family_s_style():
    # ADR-652: the animal's moving anatomy and the QDD tiers are the
    # creature's; the small wheel and gearmotor are the vehicle's.
    creature = ' '.join(_body(MODULE_DIR / 'CadexAgentStyle.creature.md').split())
    vehicle = _body(MODULE_DIR / 'CadexAgentStyle.vehicle.md')
    for rule in ("A machine in an animal's form moves like one", 'rigid_appendages',
                 '"cubemars-ak70-10"', '"cubemars-ak45-10-v3"', 'qdd.mounting()'):
        assert rule in creature and rule not in _body(), rule
    for rule in ('lib.wheel("pololu-1430")', 'lib.gearmotor("pololu-2367")',
                 'tb6612-adafruit-2448', 'wheel.tyre()'):
        assert rule in vehicle and rule not in _body(), rule


#: The provisional styles (ADR-653), and a convention each must carry.
PROVISIONAL = {
    'gantry-machine': ('THE TOOL POINT IS THE SPEC', 'STIFFNESS FIRST', 'LINEAR MOTION IS BOUGHT',
                       'CABLES MOVE WITH THE AXES', 'AN ENCLOSURE HAS A JOB'),
    'vehicle': ('THE DUTY IS THE SPEC', 'THE DRIVETRAIN COMES FROM THE LOAD',
                'STEERING AND SUSPENSION ARE JOINTS', 'STABILITY IS MEASURED',
                'THE BODY COVERS A CHASSIS'),
    'product': ('THE ENCLOSURE IS DESIGNED FROM THE INSIDE',
                'IT COMES APART WHERE IT IS ASSEMBLED AND SERVICED', 'EVERY OPENING HAS A REASON'),
}


def test_the_provisional_styles_are_short_marked_and_carry_their_family_s_conventions():
    for name, rules in PROVISIONAL.items():
        source = MODULE_DIR / f'CadexAgentStyle.{name}.md'
        body = ' '.join(_body(source).split())
        assert _words(source) <= PROVISIONAL_WORD_BUDGET, name
        assert 'It is provisional' in body and 'the measurement wins' in body, name
        assert 'WHEN YOU LOOK, ALSO NAME' in body, name
        for rule in rules:
            assert rule in body and rule not in _body(), (name, rule)


def test_taste_numbers_are_starting_points_and_kept_numbers_say_why():
    # ADR-651 (owner, 2026-10-10: "we shouldnt have hard rules like that"):
    # a proportion that is taste is a starting point with a check, never a
    # bound; a number kept as law is a measured need and says why.
    legged = ' '.join(_body(MODULE_DIR / 'CadexAgentStyle.printed-legged-robot.md').split())
    for bound in ('no longer than a quarter of it', 'no wider than an eighth of it',
                  'at least 2.5 times', 'about 60% of its hip section'):
        assert bound not in legged, bound
    for start in ('is a good start', 'by the sweep, never only by eye', 'about 2.5 is a good start'):
        assert start in legged, start
    # The kept numbers carry their reason.
    assert 'because contact can begin anywhere between two samples' in legged
    assert 'four 0.4 mm perimeters' in ' '.join(_body().split())


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
STYLE_LESSONS = ('THE LOOK OF A LIMB', 'lightening window', 
                 'FEET ARE COMPACT HULLS WITH A FLAT STRIP', "never from the foot's area",
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
    # and found clear by the sweep was taken for one derived from it. Since
    # ADR-651 the number is a recorded starting point with a measured check,
    # not a bound.
    style = " ".join(_body(MODULE_DIR / 'CadexAgentStyle.printed-legged-robot.md').split())
    for rule in ('COMPACT IS MEASURED', 'against it in DECISIONS.md',
                 'about a quarter of the height long and an eighth wide is a good start',
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


#: The creature style's rules (ADR-626), one per trait the owner's north-star
#: references share (docs/DESIGN-LANGUAGE.md section 11).
CREATURE_RULES = ('THE ANATOMY IS THE JOINT LIST', 'SIZE THE ACTUATOR TO THE JOINT',
                  'THE ACTUATOR IS THE JOINT, AND IT SHOWS', 'SHELLS SIT ON THE MASSES; LINKS DO THE WORK',
                  'PANELS WRAP THE MECHANISM', 'SEGMENTS, NOT A SKIN, WHERE IT BENDS',
                  'THE CHARACTER IS A REAL SENSOR', 'TWO TONES AND ONE FUNCTIONAL ACCENT',
                  'LIKENESS BY SILHOUETTE AND PROPORTION', 'THE BAR IS A REAL PRODUCT')


def test_the_creature_style_carries_the_north_star_rules_and_not_the_legged_ones():
    body = _body(MODULE_DIR / 'CadexAgentStyle.creature.md')
    legged = _body(MODULE_DIR / 'CadexAgentStyle.printed-legged-robot.md')
    for rule in CREATURE_RULES:
        assert rule in body, rule
        assert rule not in _body() and rule not in legged, rule
    # Curved panels are allowed when they wrap the mechanism; the defect is a
    # shell sized by eye around nothing (owner, 2026-10-09).
    assert 'may curve' in body and 'grown from what it covers' in body
    assert 'never one soft skin' not in body
    # It points at the helpers and the measured blocks that back it.
    for name in ('lib.housing', 'part.envelope(over=', 'panel check', 'role="panel"', 'anatomy block', '`reason=`'):
        assert name in body, name
