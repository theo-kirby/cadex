# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Known geometry for ot7 F2: tab burial, floating horn and world plane."""
import pytest

from test_swept_clearance import _api, _solid
import test_clearance_scope as kernel


def test_intent_contract_and_legacy_definition():
    api = _api()
    a, b = api.component(_solid()), api.component(_solid())
    assert 'world' not in a.properties
    assert 'fit_intent' not in api.assembly([a, b]).properties
    assert api.component(_solid(), world=True).properties['world'] is True
    model = api.assembly([a, b], contacts=[(b, a)])
    assert model.properties['fit_intent'][0]['kind'] == 'contact'
    assert api.assembly([a, b], clearances=[(a, b, 0.5)]).properties['fit_intent'][0]['minimum_mm'] == 0.5
    for kwargs in [dict(contacts=[(a, a)]), dict(contacts=[(a, api.component(_solid()))]),
                   dict(contacts=[(a, b)], clearances=[(b, a, 1)]),
                   dict(clearances=[(a, b, -1)]), dict(clearances=[(a, b, float('nan'))]),
                   dict(clearances=[(a, b, True)]), dict(contacts=[(a,)])]:
        with pytest.raises(ValueError):
            api.assembly([a, b], **kwargs)


_DRIVER = r'''
import json, sys
from pathlib import Path
import FreeCAD as App
import Part
sys.path.insert(0, sys.argv[-1])
from cadex_assembly_worker import _measure_clearance, _check_fit, _check_attachments
from cadex_assembly_api import AssemblyDomainAPI
import CadexScriptedDomains as domains
from cadex_domain_api import create_domain_api
pack = domains.get_xscript_pack("AssemblyWorkbench")
api = create_domain_api(pack.domain, pack.api_exports, pack.output_types)
doc = App.newDocument("FitIntent")
components = {}
values = {}

def box(name, xyz, size=(10, 10, 10)):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = Part.makeBox(*size, App.Vector(*xyz))
    components[name] = obj
    values[name] = api.component({"document_uid": "fixture", "object_name": name}, grounded=True)
    return values[name]

cheek = box("cheek", (0, 0, 0))
tab = box("servo_tab", (7.518, 0, 0)) # 2.482 * 10 * 10 = 248.2 mm³
horn = box("horn", (100, 0, 0))
link = box("link", (110.2, 0, 0)) # missed intended contact: 0.2 mm
base = box("base", (200, 0, 0))
bearing = box("bearing", (210, 0, 0)) # real touching contact
near = box("near", (300, 0, 0))
other = box("other", (310.05, 0, 0)) # undeclared 0.05 mm
wide = box("wide", (400, 0, 0))
mate = box("mate", (410.4, 0, 0)) # declared 0.5 mm, actual 0.4
mount = box("mount", (600, 0, 0))
stud = box("stud", (610, 0, 0)) # welded flush, nothing declared: 0.0 mm
floor = box("floor_face", (500, 0, 0))
components["floor_face"].Shape = Part.makePlane(20, 20, App.Vector(500, 0, 0), App.Vector(1, 1, 1))
asm = api.assembly(list(values.values()), contacts=[(base, bearing), (tab, cheek)],
                   clearances=[(wide, mate, 0.5), (horn, link, 0.05)])
# Heron's own shape: the horn is welded to its link and declared a clearance,
# so every fit check passes while nothing holds the two parts together.
joint_data = {
    "weld_horn": {"assembly_output": "asm", "kind": "fixed", "suppressed": False,
                  "connectors": [{"component_output": "horn"}, {"component_output": "link"}]},
    "weld_bearing": {"assembly_output": "asm", "kind": "fixed", "suppressed": False,
                     "connectors": [{"component_output": "base"}, {"component_output": "bearing"}]},
    "weld_suppressed": {"assembly_output": "asm", "kind": "fixed", "suppressed": True,
                        "connectors": [{"component_output": "near"}, {"component_output": "other"}]},
    "hinge": {"assembly_output": "asm", "kind": "revolute", "suppressed": False,
              "connectors": [{"component_output": "wide"}, {"component_output": "mate"}]},
    "weld_mount": {"assembly_output": "asm", "kind": "fixed", "suppressed": False,
                   "connectors": [{"component_output": "mount"}, {"component_output": "stud"}]},
}
body = api.body(base, density_kg_m3=1000, collision=[api.collision("plane", size_mm=[500, 500, 50])])
doc.recompute()
rows = _measure_clearance(components)
world = _check_fit(rows, components, asm.properties, {id(v): k for k, v in values.items()}, {"body": body},
                   joint_data, "asm")
attachments = _check_attachments(rows, joint_data, "asm")
print("CLEARANCE-FRAME " + json.dumps({"pairs": rows, "world": world, "attachments": attachments}))
'''


@pytest.mark.skipif(kernel.FREECADCMD is None, reason='Needs real OCCT')
def test_heron_defects_measured_by_real_kernel(tmp_path, monkeypatch):
    monkeypatch.setattr(kernel, '_FRAME_DRIVER', _DRIVER)
    report = kernel._drive_frame(tmp_path)
    pairs = {frozenset((r['first'], r['second'])): r for r in report['pairs']}
    def pair(a, b):
        return pairs[frozenset((a, b))]
    assert pair('cheek', 'servo_tab')['common_volume_mm3'] == pytest.approx(248.2)
    assert pair('cheek', 'servo_tab')['fit_failures'] == ['intersection']
    assert pair('horn', 'link')['distance_mm'] == pytest.approx(0.2)
    # Declared a 0.05 mm clearance, as Heron declared it, on a pair the same
    # script welds. The declaration is checked as written and 0.2 mm clears
    # it, so every fit check on this pair passes; the welding joints ride on
    # the published intent as a fact, not a verdict (ADR-380). What names
    # the floating horn is the gap under the weld, below (ADR-370).
    assert pair('horn', 'link')['fit_failures'] == []
    assert pair('horn', 'link')['intent'] == {'kind': 'clearance', 'minimum_mm': 0.05,
                                              'joints': ['weld_horn']}
    assert pair('base', 'bearing')['fit_failures'] == []
    assert pair('base', 'bearing')['intent']['kind'] == 'contact'
    # Welded flush with nothing declared: the fixed joint is the declaration
    # and 0.0 mm is what it asked for (ADR-372).
    assert pair('mount', 'stud')['distance_mm'] == 0.0
    assert pair('mount', 'stud')['fit_failures'] == []
    assert pair('mount', 'stud')['intent'] == {'kind': 'attached', 'minimum_mm': 0.0,
                                               'joints': ['weld_mount']}
    # ...and a *suppressed* weld is no weld: this pair keeps the default gap.
    assert pair('near', 'other')['distance_mm'] == pytest.approx(0.05)
    assert pair('near', 'other')['intent'] == {}
    assert pair('near', 'other')['fit_failures'] == ['below clearance']
    # A declared clearance on a pair no fixed joint welds is judged by the
    # same rule the welded one above is: its own declared minimum.
    assert pair('wide', 'mate')['distance_mm'] == pytest.approx(0.4)
    assert pair('wide', 'mate')['intent'] == {'kind': 'clearance', 'minimum_mm': 0.5}
    assert pair('wide', 'mate')['fit_failures'] == ['below clearance']
    bearing, horn_gap, mount_weld = report['attachments']
    assert mount_weld['status'] == 'touching'
    assert [item['first'] for item in report['attachments']] == ['base', 'horn', 'mount']
    assert bearing == {'first': 'base', 'second': 'bearing', 'joints': ['weld_bearing'],
                       'status': 'touching', 'distance_mm': 0.0, 'common_volume_mm3': 0.0}
    assert horn_gap['status'] == 'not touching' and horn_gap['joints'] == ['weld_horn']
    assert horn_gap['distance_mm'] == pytest.approx(0.2)
    assert report['world'] == [{'component': 'base', 'status': 'world geometry',
                                'reason': 'collision plane declared on design component'},
                               {'component': 'floor_face', 'status': 'world geometry',
                                'reason': 'surface-only plane'}]


@pytest.mark.parametrize('declared', [False, True])
@pytest.mark.parametrize('gap,failed', [
    (0.1, False), (0.09999999999999952, False),
    (0.09999999999999039, False), (0.1 - 5e-10, False),
    (0.1 - 2e-9, True), (0.0999, True), (0.05, True),
])
def test_minimum_comparison_preserves_raw_measurements(declared, gap, failed):
    from cadex_assembly_worker import _check_fit
    a, b = object(), object()
    properties = {'fit_intent': [{'first': a, 'second': b, 'kind': 'clearance',
                                  'minimum_mm': 0.1}]} if declared else {}
    row = {'first': 'a', 'second': 'b', 'distance_mm': gap, 'common_volume_mm3': 0.0}
    assert _check_fit([row], {}, properties, {id(a): 'a', id(b): 'b'}) == []
    assert row['fit_failures'] == (['below clearance'] if failed else [])
    assert row['distance_mm'] == gap and row['common_volume_mm3'] == 0.0


@pytest.mark.parametrize('kind,suppressed,gap,volume,expected', [
    # A weld fixes a relative pose; it does not require the solids to touch,
    # and a declared minimum is a floor on a distance rather than a claim
    # that the pair moves. So two rigidly separated components satisfying
    # their declared minimum fail nothing (ADR-380).
    ('clearance', False, 0.2, 0.0, []),
    ('clearance', False, 2.0, 0.0, []),
    # ...and the declared minimum is really consulted: below it, it fails.
    ('clearance', False, 0.02, 0.0, ['below clearance']),
    ('clearance', False, 0.0, 0.0, ['below clearance']),
    # Overlap is still overlap, and still named first.
    ('clearance', False, 0.0, 1.0, ['intersection', 'below clearance']),
    # A *suppressed* fixed joint is no weld, and changes none of this.
    ('clearance', True, 0.2, 0.0, []),
    ('clearance', True, 0.02, 0.0, ['below clearance']),
    # A contact declaration agrees with the weld and is checked as written.
    ('contact', False, 0.0, 0.0, []),
    ('contact', False, 0.2, 0.0, ['missed contact']),
])
def test_a_clearance_declared_on_a_welded_pair_is_judged_by_its_minimum(
        kind, suppressed, gap, volume, expected):
    """ADR-380, withdrawing ADR-379: rigidly held and apart is one design.

    A board on its standoffs is welded to the plate it stands over and is
    also meant to keep 2 mm off it. ADR-379 read that pair as a
    contradiction and failed it at every gap; it is not one, and the
    declaration is the only place the design can say how far apart.
    """

    from cadex_assembly_worker import _check_fit
    a, b = object(), object()
    intent = {'first': a, 'second': b, 'kind': kind}
    if kind == 'clearance':
        intent['minimum_mm'] = 0.05
    joint_data = {'weld': {'assembly_output': 'asm', 'kind': 'fixed',
                           'suppressed': suppressed,
                           'connectors': [{'component_output': 'a'},
                                          {'component_output': 'b'}]}}
    row = {'first': 'a', 'second': 'b', 'distance_mm': gap, 'common_volume_mm3': volume}
    assert _check_fit([row], {}, {'fit_intent': [intent]},
                      {id(a): 'a', id(b): 'b'}, {}, joint_data, 'asm') == []
    assert row['fit_failures'] == expected
    # The welding joints ride on the clearance declaration as a fact a
    # reader can join without the joint table, and on no other intent, so
    # no intent this project already published changes shape.
    if kind == 'clearance' and not suppressed:
        assert row['intent'] == {'kind': 'clearance', 'minimum_mm': 0.05,
                                 'joints': ['weld']}
    else:
        assert 'joints' not in row['intent']
    assert row['distance_mm'] == gap and row['common_volume_mm3'] == volume


_GAP_DRIVER = r'''
import json, sys
import FreeCAD as App
import Part
sys.path.insert(0, sys.argv[-1])
from cadex_assembly_worker import _measure_clearance, _measure_joint_sweeps, _check_fit
D = App.newDocument('GapSweep')
a = D.addObject('Part::Feature', 'a')
a.Shape = Part.makeBox(10, 10, 10)
b = D.addObject('Part::Feature', 'b')
components = {'a': a, 'b': b}
data = {'a': {'grounded': True}, 'b': {'grounded': False}}
joints = {'slide': {'kind': 'slider', 'suppressed': False, 'parameters': {},
    'angle_limits_degrees': None, 'length_limits_mm': [0, 1],
    'connectors': [{'component_output': name, 'local_frame': {'matrix': list(App.Matrix().A)}}
                   for name in ('a', 'b')]}}
reports = []
for gap in (0.1, 0.0999, 0.05):
    b.Shape = Part.makeBox(10, 10, 10, App.Vector(10 + gap, 0, 0))
    D.recompute()
    baseline = _measure_clearance(components)
    sweep = _measure_joint_sweeps(components, data, joints, baseline, {'sweep_step_mm': 0.5}, True)
    assert sweep['status'] == 'complete', sweep
    raw = sweep['joints'][0]['pairs'][0]
    verdicts = []
    for declared in (False, True):
        props = {'fit_intent': [{'first': a, 'second': b, 'kind': 'clearance', 'minimum_mm': 0.1}]} if declared else {}
        static = dict(baseline[0])
        extrema = {'first': 'a', 'second': 'b', 'distance_mm': raw['minimum_distance_mm'],
                   'common_volume_mm3': raw['maximum_common_volume_mm3']}
        _check_fit([static, extrema], {}, props, {id(a): 'a', id(b): 'b'})
        verdicts.append([static, extrema])
    reports.append({'gap': gap, 'sweep': sweep, 'verdicts': verdicts})
print('CLEARANCE-FRAME ' + json.dumps(reports))
'''


@pytest.mark.skipif(kernel.FREECADCMD is None, reason='Needs real OCCT')
def test_real_box_gap_static_and_swept_minima(tmp_path, monkeypatch):
    monkeypatch.setattr(kernel, '_FRAME_DRIVER', _GAP_DRIVER)
    for report in kernel._drive_frame(tmp_path):
        raw = report['sweep']['joints'][0]['pairs'][0]
        assert raw['minimum_distance_mm'] == pytest.approx(report['gap'], abs=1e-12)
        assert raw['maximum_common_volume_mm3'] == 0
        assert raw['first_contact_mm'] is None
        for static, extrema in report['verdicts']:
            expected = [] if report['gap'] == 0.1 else ['below clearance']
            assert static['fit_failures'] == extrema['fit_failures'] == expected
            assert extrema['distance_mm'] == raw['minimum_distance_mm']


def test_attachments_report_only_unsuppressed_fixed_joint_pairs():
    """A weld with a gap is named; a suppressed one, another kind, and an
    unmeasured pair each say what they are (ADR-370)."""

    from cadex_assembly_worker import _check_attachments
    rows = [{'first': 'a', 'second': 'b', 'distance_mm': 0.2, 'common_volume_mm3': 0.0},
            {'first': 'c', 'second': 'd', 'distance_mm': 0.0, 'common_volume_mm3': 5.0},
            {'first': 'e', 'second': 'f', 'distance_mm': None, 'common_volume_mm3': None,
             'error': 'No published measurement; rebuild the project.'},
            {'first': 'g', 'second': 'h', 'distance_mm': 9.0, 'common_volume_mm3': 0.0}]

    def joint(kind, first, second, suppressed=False, assembly='asm'):
        return {'assembly_output': assembly, 'kind': kind, 'suppressed': suppressed,
                'connectors': [{'component_output': first}, {'component_output': second}]}

    report = _check_attachments(rows, {
        'weld_gap': joint('fixed', 'b', 'a'),
        'weld_overlap': joint('fixed', 'c', 'd'),
        'weld_unmeasured': joint('fixed', 'e', 'f'),
        'weld_again': joint('fixed', 'a', 'b'),
        'weld_off': joint('fixed', 'g', 'h', suppressed=True),
        'weld_elsewhere': joint('fixed', 'g', 'h', assembly='other'),
        'hinge': joint('revolute', 'g', 'h'),
        'weld_missing_pair': joint('fixed', 'x', 'y'),
    }, 'asm')
    assert [(item['first'], item['second'], item['status']) for item in report] == [
        ('a', 'b', 'not touching'), ('c', 'd', 'touching'),
        ('e', 'f', 'unknown'), ('x', 'y', 'unknown')]
    # Two joints over one pair are one row naming both, in a stable order.
    assert report[0]['joints'] == ['weld_again', 'weld_gap']
    assert report[0]['distance_mm'] == 0.2
    assert report[2]['reason'] == 'No published measurement; rebuild the project.'
    assert report[3]['distance_mm'] is None
    assert _check_attachments(rows, {}, 'asm') == []


def test_welded_pair_is_not_held_to_the_undeclared_gap():
    """A fixed joint is the design declaring two components one rigid body,
    so their solids meeting is the declaration rather than a closed gap
    (ADR-372). The implication is the weakest one available: it exempts the
    pair from the default 0.1 mm and asserts nothing else."""

    from cadex_assembly_worker import _check_fit

    def joint(first, second, *, kind='fixed', suppressed=False, assembly='asm'):
        return {'assembly_output': assembly, 'kind': kind, 'suppressed': suppressed,
                'connectors': [{'component_output': first}, {'component_output': second}]}

    def check(distance, volume=0.0, *, joints=None, declared=None, error=None):
        first, second = object(), object()
        outputs = {id(first): 'a', id(second): 'b'}
        properties = {'fit_intent': [dict(declared, first=first, second=second)]} if declared else {}
        row = {'first': 'a', 'second': 'b', 'distance_mm': distance,
               'common_volume_mm3': volume, **({'error': error} if error else {})}
        assert _check_fit([row], {}, properties, outputs, None, joints or {}, 'asm') == []
        return row

    flush = check(0.0, joints={'fix_servo': joint('b', 'a')})
    assert flush['fit_failures'] == []
    assert flush['intent'] == {'kind': 'attached', 'minimum_mm': 0.0, 'joints': ['fix_servo']}
    # Two joints welding the same pair are both named, in a stable order.
    assert check(0.0, joints={'fix_b': joint('a', 'b'), 'fix_a': joint('b', 'a')},
                 )['intent']['joints'] == ['fix_a', 'fix_b']
    # Interpenetration is still a failure, and so is an unmeasured pair.
    assert check(0.0, 4.07, joints={'fix': joint('a', 'b')})['fit_failures'] == ['intersection']
    assert check(None, None, joints={'fix': joint('a', 'b')},
                 error='Component has no measurable shape')['fit_failures'] == ['unknown']
    # The author's own declaration outranks the joint, either way round
    # (ADR-372, restored by ADR-380 after ADR-379 briefly failed the
    # clearance case at every gap).
    assert check(0.2, joints={'fix': joint('a', 'b')},
                 declared={'kind': 'contact'})['fit_failures'] == ['missed contact']
    assert check(0.2, joints={'fix': joint('a', 'b')},
                 declared={'kind': 'clearance', 'minimum_mm': 0.5})['fit_failures'] == ['below clearance']
    # Rigidly separated, and meeting the minimum it declared: nothing fails.
    assert check(5.0, joints={'fix': joint('a', 'b')},
                 declared={'kind': 'clearance', 'minimum_mm': 0.5})['fit_failures'] == []
    # Nothing welds these two: the default gap is unchanged by this rule.
    for joints in ({}, {'fix': joint('a', 'b', suppressed=True)},
                   {'fix': joint('a', 'b', kind='revolute')},
                   {'fix': joint('a', 'b', assembly='other')},
                   {'fix': joint('a', 'c')}):
        assert check(0.0, joints=joints)['fit_failures'] == ['below clearance']
        assert check(0.0, joints=joints)['intent'] == {}


def test_a_running_gap_under_the_default_is_a_clearance_and_not_a_contact():
    """ADR-373: the two declarations are not interchangeable at 0.05 mm.

    ADR-372 named Finch's four bearing seats -- a thigh turning on the
    bearing it rides, 0.05 mm apart -- as a running clearance the design
    should declare, and said a design meaning it "can say so with
    `contacts=`". It cannot: the contact tolerance is 0.001 mm, so that
    declaration turns a `below clearance` row into a `missed contact` row
    rather than clearing it. The declaration that says 0.05 mm is
    `clearances=[(a, b, 0.05)]`.
    """

    from cadex_assembly_worker import _check_fit

    def check(declared=None, gap=0.05):
        first, second = object(), object()
        outputs = {id(first): 'thigh', id(second): 'bearing'}
        properties = {'fit_intent': [dict(declared, first=first, second=second)]} if declared else {}
        row = {'first': 'thigh', 'second': 'bearing',
               'distance_mm': gap, 'common_volume_mm3': 0.0}
        assert _check_fit([row], {}, properties, outputs, None, {}, 'asm') == []
        return row['fit_failures']

    # Undeclared, the seat is below the 0.1 mm default -- the row a design
    # turn is asked to repair, and the geometry is not what is wrong.
    assert check() == ['below clearance']
    # `contacts=` does not repair it; it renames the failure.
    assert check({'kind': 'contact'}) == ['missed contact']
    # The gap the design means, declared as such, clears.
    assert check({'kind': 'clearance', 'minimum_mm': 0.05}) == []
    # And still measures: a seat that closed past what was declared fails.
    assert check({'kind': 'clearance', 'minimum_mm': 0.05}, gap=0.02) == ['below clearance']
