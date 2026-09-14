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
from cadex_assembly_worker import _measure_clearance, _check_fit
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
floor = box("floor_face", (500, 0, 0))
components["floor_face"].Shape = Part.makePlane(20, 20, App.Vector(500, 0, 0), App.Vector(1, 1, 1))
asm = api.assembly(list(values.values()), contacts=[(horn, link), (base, bearing), (tab, cheek)],
                   clearances=[(wide, mate, 0.5)])
body = api.body(base, density_kg_m3=1000, collision=[api.collision("plane", size_mm=[500, 500, 50])])
doc.recompute()
rows = _measure_clearance(components)
world = _check_fit(rows, components, asm.properties, {id(v): k for k, v in values.items()}, {"body": body})
print("CLEARANCE-FRAME " + json.dumps({"pairs": rows, "world": world}))
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
    assert pair('horn', 'link')['fit_failures'] == ['missed contact']
    assert pair('base', 'bearing')['fit_failures'] == []
    assert pair('near', 'other')['distance_mm'] == pytest.approx(0.05)
    assert pair('near', 'other')['fit_failures'] == ['below clearance']
    assert pair('wide', 'mate')['distance_mm'] == pytest.approx(0.4)
    assert pair('wide', 'mate')['fit_failures'] == ['below clearance']
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
