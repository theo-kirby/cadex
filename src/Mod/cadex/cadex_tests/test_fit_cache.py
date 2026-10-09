# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The fit cache: a rebuild re-measures only what changed (ADR-622)."""

import pytest

import test_clearance_scope as kernel


_DRIVER = r'''
import json, os, sys
from pathlib import Path
import FreeCAD as App
import Part
sys.path.insert(0, sys.argv[-1])
ROOT = Path(ROOT_PATH)
attempt = ROOT / "script_artifacts" / "rev" / "attempt-1"
attempt.mkdir(parents=True)
os.environ["CADEX_XSCRIPT_DOMAIN_REQUEST"] = str(attempt / "request.json")
import cadex_assembly_worker as worker
D = App.newDocument('FitCache')

def link(name, shape, placement=App.Placement()):
    # Every assembly component is a link to its part, as the engine builds them.
    part = D.addObject('Part::Feature', name + '_part')
    part.Shape = shape
    component = D.addObject('App::Link', name)
    component.LinkedObject = part
    component.Placement = placement
    return component

fixed = link('fixed', Part.makeSphere(1, App.Vector(0, 12.04, 0)))
moving = link('moving', Part.makeSphere(1, App.Vector(10, 0, 0)),
              App.Placement(App.Vector(), App.Rotation(App.Vector(0, 0, 1), 20)))
near = link('near', Part.makeBox(2, 2, 2, App.Vector(-1, -5, -1)))
D.recompute()
components = {'fixed': fixed, 'moving': moving, 'near': near}
data = {'fixed': {'grounded': True}, 'moving': {'grounded': False}, 'near': {'grounded': True}}
joints = {'hinge': {'kind': 'revolute', 'suppressed': False, 'parameters': {},
  'angle_limits_degrees': [20, 90], 'length_limits_mm': None,
  'connectors': [{'component_output': 'fixed', 'local_frame': {'matrix': list(App.Matrix().A)}},
                 {'component_output': 'moving', 'local_frame': {'matrix': list(App.Matrix().A)}}]}}
STEP = {'sweep_step_degrees': 1}

def build():
    cache = worker._FitCache.open()
    rows = worker._measure_clearance(components, cache=cache)
    sweep = worker._measure_joint_sweeps(components, data, joints, rows, STEP, True, cache=cache)
    for joint in sweep['joints']:
        joint.pop('elapsed_seconds', None)
    sweep.pop('elapsed_seconds', None)
    stats = dict(hits=cache.hits, misses=cache.misses, added=len(cache.added),
                 kinds=sorted(key.split(':')[0] for key in cache.added))
    cache.save()
    return rows, sweep, stats

cold = build()
warm = build()
near.Placement = App.Placement(App.Vector(0, 0.5, 0), App.Rotation())
D.recompute()
moved = build()
shift = App.Placement(App.Vector(3, -2, 7), App.Rotation(App.Vector(1, 1, 0), 30))
for obj in components.values():
    obj.Placement = shift.multiply(obj.Placement)
D.recompute()
together = build()
store = sorted(p.name for p in (ROOT / "script_artifacts" / "fit-cache").iterdir())
os.environ.pop("CADEX_XSCRIPT_DOMAIN_REQUEST")
none = worker._FitCache.open()
print('CLEARANCE-FRAME ' + json.dumps(dict(cold=cold, warm=warm, moved=moved, together=together, store=store,
                                          detached=none.path is None)))
'''


@pytest.mark.skipif(kernel.FREECADCMD is None, reason='Needs real OCCT')
def test_a_rebuild_reads_back_exactly_what_it_measured_and_remeasures_what_moved(tmp_path, monkeypatch):
    monkeypatch.setattr(kernel, '_FRAME_DRIVER',
                        _DRIVER.replace('Path(ROOT_PATH)', 'Path(%r)' % str(tmp_path / 'project')))
    result = kernel._drive_frame(tmp_path)
    cold_rows, cold_sweep, cold_stats = result['cold']
    warm_rows, warm_sweep, warm_stats = result['warm']
    moved_rows, moved_sweep, moved_stats = result['moved']
    # The second build is the first's numbers, every digit, from the cache.
    assert warm_rows == cold_rows and warm_sweep == cold_sweep
    assert cold_stats['hits'] == 0 and cold_stats['added'] > 0
    assert warm_stats['misses'] == 0 and warm_stats['added'] == 0 and warm_stats['hits'] > 0
    # One part moved: its pairs are measured again, the rest still read back.
    assert moved_stats['hits'] > 0 and moved_stats['added'] > 0
    by_pair = {(r['first'], r['second']): r for r in moved_rows}
    before = {(r['first'], r['second']): r for r in cold_rows}
    assert by_pair['fixed', 'moving'] == before['fixed', 'moving']
    assert by_pair['fixed', 'near']['distance_mm'] != before['fixed', 'near']['distance_mm']
    # Everything moved together: no pair moved relative to its partner, so
    # every pair reads back, equal to its own measurement to rounding.
    together_rows, together_sweep, together_stats = result['together']
    assert together_stats['kinds'] == ['box', 'box', 'box'], together_stats
    exact = [r for r in moved_rows if not r.get('culled')]
    assert all(r == by_pair_r for r, by_pair_r in zip(
        [r for r in together_rows if not r.get('culled')], exact))
    # A culled row is a bound from world-aligned boxes, which turn with the
    # frame; every measured row reads back.
    measured = [[r for r in sweep['joints'][0]['pairs'] if not r.get('culled')]
                for sweep in (together_sweep, moved_sweep)]
    assert measured[0] == measured[1] and measured[0]
    assert result['store'] and all(name.startswith('fit-') for name in result['store'])
    # Outside a project run there is no store, and nothing is cached.
    assert result['detached']
    assert cold_sweep['status'] == 'complete'
