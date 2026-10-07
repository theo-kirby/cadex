# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Independent synthetic rollout fixtures; real verification is in test_walk."""
import hashlib
import json
import math
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import sys
import time

import pytest

from cadex_cli.video import render, placed, stl, RENDER_SECONDS, STUDIO
import cadex_cli.video as video_module
from cadex_cli.browser import find_browser
from cadex_cli.review_record import read_run_record
from cadex_cli.review_server import serve, run_model
from test_review_server import (browser, needs_browser, _open, _mesh_run,
                                _rewrite_record, _project, REVISION_A,
                                REVISION_B, _manifest, _get, _model_state, CLI_DIR)


def _video_run(root, name='sample'):
    """A walked run whose trace moves and names its policy: renderable."""
    run = _mesh_run(root, name, revision=REVISION_A)
    record = json.loads((run / 'run.json').read_text())
    sha = hashlib.sha256((root / 'assets/gait.cxpolicy').read_bytes()).hexdigest()
    record['policy']['sha256'] = sha
    _rewrite_record(run, policy=record['policy'])
    trace_path = run / record['artifacts']['trace']
    trace = json.loads(trace_path.read_text())
    first = trace['frames'][0]
    trace['frames'] = [first] + [
        {'frame_kind': 'solver_output', 'nominal_time_s': i/10,
         'component_placements': {
             'body': {'position_mm': [i*2, 0, 0], 'rotation_xyzw': [0, 0, 0, 1]},
             'shin': {'position_mm': [i*2, 0, -40], 'rotation_xyzw': [0, 0, 0, 1]}}}
        for i in range(6)]
    trace['policy'] = {'policy_sha256': sha, 'task_sha256': record['task']['sha256'],
                       'model_sha256': hashlib.sha256((run / record['artifacts']['model_xml']).read_bytes()).hexdigest(),
                       'seed': record['rollout']['seed']}
    trace_path.write_text(json.dumps(trace))
    return run


@pytest.fixture
def video_project(tmp_path):
    root = _project(tmp_path)
    _video_run(root)
    return root


@pytest.fixture
def rendered(video_project):
    if not shutil.which('ffmpeg') or not find_browser():
        pytest.skip('FFmpeg and headless Chromium required')
    return video_project, render(video_project, 'sample')


def test_render_decodes_moving_frames_at_simulation_speed_and_retains_identity(rendered):
    root, video = rendered
    run = root / 'runs/sample'
    assert video['frames'] == 6 and video['duration_seconds'] == .6 and video['sim_seconds'] == .5
    assert video['accepted_revision'] == REVISION_A
    assert video['seed'] == 7
    decoded = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(run / video['path']),
                              '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                             capture_output=True, check=True).stdout
    size = 512*512*3
    assert len(decoded) == 6*size
    assert decoded[:size] != decoded[-size:], 'poses must move in the rendered video'
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                                               '-of', 'json', str(run / video['path'])]))
    assert probe['streams'][0]['r_frame_rate'] == '10/1'
    assert read_run_record(run, root)['videos'] == [video]
    # Record rewrites by an independently running walk cannot erase video metadata.
    _rewrite_record(run, status='running')
    assert read_run_record(run, root)['videos'] == [video]
    copy = root.parent / 'copy'
    shutil.copytree(root, copy)
    shutil.rmtree(root)
    assert (copy / 'runs/sample' / video['path']).is_file()
    assert read_run_record(copy / 'runs/sample', copy)['resolved']['videos'][0]['exists']


@pytest.mark.parametrize('style', ['scene', 'studio'])
@pytest.mark.parametrize('fault', ['policy', 'time', 'pose', 'escape', 'encoder'])
def test_render_refuses_invalid_inputs_without_touching_training(video_project, monkeypatch, fault, style):
    root = video_project
    run = root / 'runs/sample'
    path = run / 'rollout/assembly-simulation-trace.json'
    trace = json.loads(path.read_text())
    if fault == 'policy': trace['policy']['policy_sha256'] = '0'*64
    if fault == 'time': trace['frames'][2]['nominal_time_s'] = -1
    if fault == 'pose': trace['frames'][2]['component_placements'].pop('shin')
    if fault == 'escape':
        mesh = run / 'rollout/torso.stl'
        outside = root.parent / 'outside.stl'
        shutil.copyfile(mesh, outside)
        mesh.unlink()
        mesh.symlink_to(outside)
    path.write_text(json.dumps(trace))
    if fault == 'encoder':
        # Neither on PATH nor beside the interpreter (video.ffmpeg).
        import types
        from cadex_cli import video as video_module
        monkeypatch.setenv('PATH', '')
        monkeypatch.setattr(video_module, 'sys', types.SimpleNamespace(executable=str(root / 'no-bin' / 'python')))
    # A real independent process stands in for the trainer: rendering must
    # neither terminate it nor change its telemetry file. No GPU claim.
    heartbeat = run / 'train/heartbeat'
    process = subprocess.Popen([sys.executable, '-c',
        'import time,pathlib,sys\np=pathlib.Path(sys.argv[1])\n'
        'for i in range(1000):\n'
        # Atomic, as a real trainer's heartbeat must be: a truncating write
        # lets a reader see '' between the truncate and the write.
        ' t=p.with_name(p.name+\'.tmp\'); t.write_text(str(i)); t.replace(p); time.sleep(.02)',
        str(heartbeat)])
    try:
        with pytest.raises((ValueError, FileNotFoundError)):
            render(root, 'sample', style)
        before = heartbeat.read_text() if heartbeat.exists() else ''
        deadline = time.monotonic()+2
        while time.monotonic() < deadline:
            if heartbeat.exists() and heartbeat.read_text() not in ('', before): break
            time.sleep(.02)
        assert process.poll() is None and heartbeat.read_text() not in ('', before)
        status = read_run_record(run, root)
        assert status['video_render']['state'] == 'failed'
        assert status['videos'] == []
        assert not list(run.glob('*.webm')) and not list(run.glob('.video-*'))
    finally:
        process.terminate()
        process.wait(timeout=5)


def test_quaternion_placement_rotates_about_component_origin():
    import math
    tri = [[(1, 0, 0), (0, 1, 0), (0, 0, 0)]]
    result = placed(tri, {'position_mm': [10, 20, 30],
                          'rotation_xyzw': [0, 0, math.sqrt(.5), math.sqrt(.5)]})
    assert result[0][0] == pytest.approx((10, 21, 30))
    assert result[0][1] == pytest.approx((9, 20, 30))


@needs_browser
def test_capture_follows_the_subject_at_the_declared_framing_and_stamps_the_timer(rendered, browser):
    """The follow rig and the timer overlay, through the shared scene (ADR-332):
    one standoff at the declared fraction, a smoothed anchor that keeps the
    subject inside the drift budget through a whip, fixed orientation, and a
    clock pill baked bottom-left that changes with the seconds and nothing else."""
    import math
    root, video = rendered
    rig = video['framing']
    tan_v = math.tan(math.radians(55 / 2))
    assert rig['fraction'] == 0.22 and rig['smooth_frames'] == 4
    assert rig['standoff_mm'] == pytest.approx(rig['subject_height_mm'] / (2 * tan_v * 0.22))
    assert video['camera']['distance'] == pytest.approx(rig['standoff_mm'])
    assert 0 <= rig['worst_drift_ndc'] < rig['max_drift'] and 0 < rig['size_min'] <= rig['size_max']
    assert abs(rig['size_max'] - 0.22) < 0.01 and video['overlay'].startswith('timer')
    run = root / 'runs/sample'
    trace = json.loads((run / 'rollout/assembly-simulation-trace.json').read_text())
    frame = next(f for f in trace['frames'] if f.get('frame_kind') == 'solver_output')
    manifest = run_model(root, read_run_record(run, root))
    entries = [{'name': e['name'], 'placement': frame['component_placements'][e['name']],
                'positions': [v for t in stl(run / 'rollout' / (e['output'] + '.stl')) for pt in t for v in pt]}
               for e in manifest['components'] if e['name'] in frame['component_placements']]
    server, _ = serve(root, '127.0.0.1', 0)
    try:
        page = browser.page(server.url + 'capture.html')
        page.wait_for('window.cadexCapture?.available')
        page.evaluate('cadexCapture.install(' + json.dumps(entries) + '); cadexCapture.frameBounds(' + json.dumps(video['bounds']) + ')')
        # A steady walk of 12 mm (0.6 subject heights, a twentieth of one per frame): every
        # camera keeps the standoff, the target follows the subject and the horizon (yaw,
        # pitch) never moves.
        walk = [[i, 0, 10] for i in range(13)]
        steady = page.evaluate('cadexCapture.follow(' + json.dumps(walk) + ', {"subject_height_mm": 20})')
        assert steady['standoff_mm'] == pytest.approx(20 / (2 * tan_v * 0.22))
        assert all(c['distance'] == pytest.approx(steady['standoff_mm']) and c['yaw'] == 0.8 and c['pitch'] == 0.5
                   for c in steady['cameras'])
        # The end anchors sit inside the walk: the symmetric window is truncated there.
        assert 8 < steady['cameras'][-1]['target'][0] - steady['cameras'][0]['target'][0] < 12
        assert steady['worst_drift_ndc'] < 0.05 and steady['size_min'] > 0.2
        # A whip of a whole standoff in one frame stays inside the drift budget: the soft limiter.
        whip = [[0, 0, 10]] * 6 + [[steady['standoff_mm'], 0, 10]] * 6
        whipped = page.evaluate('cadexCapture.follow(' + json.dumps(whip) + ', {"subject_height_mm": 20})')
        assert 0.1 < whipped['worst_drift_ndc'] < whipped['max_drift'] == 0.26
        with pytest.raises(Exception):
            page.evaluate('cadexCapture.follow([[0, 0]], {"subject_height_mm": 20})')
        # The timer: absent at rest, then a pill bottom-left whose pixels are the only difference.
        page.evaluate('cadexCapture.setCamera(' + json.dumps(steady['cameras'][0]) + ')')
        import base64
        def shot(clock):
            path = run / f'clock-{clock}.png'
            path.write_bytes(base64.b64decode(page.evaluate(f'cadexCapture.setClock({clock}); cadexCapture.png()')))
            return subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
        rest, zero, later = shot('null'), shot(0), shot(12.5)
        assert len(rest) == len(zero) == 512 * 512 * 3
        def changed(a, b):
            rows = set()
            for i in range(0, len(a), 3):
                if a[i:i+3] != b[i:i+3]:
                    rows.add(((i // 3) // 512, (i // 3) % 512))
            return rows
        pill = changed(rest, zero)
        assert 400 < len(pill) < 512 * 512 // 16
        assert all(y > 512 * 0.8 and x < 512 * 0.3 for y, x in pill), 'the timer sits bottom-left'
        digits = changed(zero, later)
        assert digits and digits <= pill | changed(rest, later)
        assert page.evaluate('cadexCapture.modelPixels()')['count'] == page.evaluate('cadexCapture.nonBackgroundPixels()') > 0
        assert shot('null') == rest
    finally:
        server.shutdown(); server.server_close()


def _fine_stl(size, n):
    """An ASCII STL of a ``size`` mm cube whose faces are gridded ``n``×``n``: 12·n² facets."""

    def face(origin, u, v):
        for i in range(n):
            for j in range(n):
                a = [origin[k] + u[k]*i/n*size + v[k]*j/n*size for k in range(3)]
                b = [origin[k] + u[k]*(i+1)/n*size + v[k]*j/n*size for k in range(3)]
                c = [origin[k] + u[k]*(i+1)/n*size + v[k]*(j+1)/n*size for k in range(3)]
                d = [origin[k] + u[k]*i/n*size + v[k]*(j+1)/n*size for k in range(3)]
                yield (a, b, c); yield (a, c, d)
    s = size
    faces = [((0, 0, 0), (1, 0, 0), (0, 1, 0)), ((0, 0, s), (0, 1, 0), (1, 0, 0)),
             ((0, 0, 0), (0, 0, 1), (1, 0, 0)), ((0, s, 0), (1, 0, 0), (0, 0, 1)),
             ((0, 0, 0), (0, 1, 0), (0, 0, 1)), ((s, 0, 0), (0, 0, 1), (0, 1, 0))]
    lines = ['solid fine']
    for origin, u, v in faces:
        for tri in face(origin, u, v):
            lines.append('  facet normal 0 0 0\n    outer loop')
            lines.extend('      vertex %r %r %r' % tuple(p) for p in tri)
            lines.append('    endloop\n  endfacet')
    lines.append('endsolid fine')
    return '\n'.join(lines) + '\n'


def test_render_takes_a_real_tessellation_and_bounds_it_exactly(video_project):
    """A real model is tens of thousands of triangles, not Lark's 96 boxes
    (Finch's accepted revision tessellates to 95 212): the renderer takes it,
    the page loads each retained solid over the local server and reports the
    validated file's own triangle count back, and the bounds and the follow
    track are exact over every vertex at every solved pose — a rotated part's
    box is its own, not the box of its axis-aligned box — computed where the
    vertices are rather than in Python, which is what the 20 000 cap paid for."""

    if not shutil.which('ffmpeg') or not find_browser():
        pytest.skip('FFmpeg and headless Chromium required')
    root = video_project
    run = root / 'runs/sample'
    (run / 'rollout/torso.stl').write_text(_fine_stl(20.0, 48))   # 27 648 facets
    tetra = [((0, 0, 0), (8, 0, 0), (0, 8, 0)), ((0, 0, 0), (0, 0, 8), (8, 0, 0)),
             ((0, 0, 0), (0, 8, 0), (0, 0, 8)), ((8, 0, 0), (0, 0, 8), (0, 8, 0))]
    (run / 'rollout/leg.stl').write_text('solid t\n' + ''.join(
        '  facet normal 0 0 0\n    outer loop\n' + ''.join('      vertex %r %r %r\n' % p for p in tri) +
        '    endloop\n  endfacet\n' for tri in tetra) + 'endsolid t\n')
    trace_path = run / 'rollout/assembly-simulation-trace.json'
    trace = json.loads(trace_path.read_text())
    turn = [0, 0, math.sin(math.pi/8), math.cos(math.pi/8)]   # 45 degrees about Z
    for frame in trace['frames'][1:]:
        frame['component_placements']['shin'].update(rotation_xyzw=turn, position_mm=[0, 30, -40])
    trace_path.write_text(json.dumps(trace))
    meshes = {'body': stl(run / 'rollout/torso.stl'), 'shin': stl(run / 'rollout/leg.stl')}
    assert 20_000 < sum(map(len, meshes.values())) == 27_652
    started = time.monotonic()
    video = render(root, 'sample')
    assert time.monotonic() - started < 120
    frames = [f for f in trace['frames'] if f.get('frame_kind') == 'solver_output']
    def box(points):
        return [[m(p[j] for p in points) for j in range(3)] for m in (min, max)]
    exact = [box([p for name in meshes for tri in placed(meshes[name], f['component_placements'][name]) for p in tri])
             for f in frames]
    def aabb_corners(mesh):
        low, high = box([p for tri in mesh for p in tri])
        return [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
    corners = [box([p for name in meshes for tri in placed([[c] * 3 for c in aabb_corners(meshes[name])],
                                                             f['component_placements'][name]) for p in tri])
               for f in frames]
    lo = [min(b[0][j] for b in exact) for j in range(3)]
    hi = [max(b[1][j] for b in exact) for j in range(3)]
    assert all(abs(a - b) < 1e-3 for a, b in zip(video['bounds']['min'] + video['bounds']['max'], lo + hi))
    assert abs(video['framing']['subject_height_mm'] - (exact[0][1][2] - exact[0][0][2])) < 1e-3
    # The turned tetrahedron's own box is narrower than the box of its turned box.
    assert max(b[1][1] for b in corners) > hi[1] + 4 > 39
    assert video['frames'] == 6 and video['showing'].startswith('tessellated solids')
    decoded = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(run / video['path']), '-f', 'rawvideo',
                              '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    assert len(decoded) == 6 * 512 * 512 * 3


# ---- the studio style (ot10 W1, ADR-431): the design look on the CPU ----

needs_ffmpeg = pytest.mark.skipif(not shutil.which('ffmpeg'), reason='FFmpeg required')


def _decoded(path, size=STUDIO['size']):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True, check=True).stdout
    frame = size*size*3
    return [raw[i:i+frame] for i in range(0, len(raw), frame)]


@needs_ffmpeg
def test_studio_video_pins_its_identity_and_bound_with_no_browser(video_project, monkeypatch):
    # No browser may be found: the studio style never looks for one.
    monkeypatch.setenv('CADEX_BROWSER', '/nonexistent')
    monkeypatch.setattr('cadex_cli.video.find_browser', lambda: pytest.fail('studio looked for a browser'))
    root, run = video_project, video_project / 'runs/sample'
    video = render(root, 'sample', 'studio')
    record = json.loads((run / 'run.json').read_text())
    trace = json.loads((run / record['artifacts']['trace']).read_text())
    assert video['style'] == 'studio' and video['width'] == video['height'] == STUDIO['size']
    assert video['accepted_revision'] == REVISION_A == record['model']['accepted_revision']
    assert video['model_digest'] == record['model']['digest']
    assert video['policy_sha256'] == record['policy']['sha256'] == trace['policy']['policy_sha256']
    assert video['task_sha256'] == record['task']['sha256'] and video['seed'] == 7
    assert video['trace_sha256'] == hashlib.sha256((run / record['artifacts']['trace']).read_bytes()).hexdigest()
    assert video['sha256'] == hashlib.sha256((run / video['path']).read_bytes()).hexdigest()
    assert video['path'] == 'rollout-' + video['sha256'] + '.webm'
    assert video['render_bound_seconds'] == RENDER_SECONDS and 0 < video['render_seconds'] < RENDER_SECONDS
    assert video['frames'] == 6 and video['fps'] == 10 and len(video['style_sha256']) == 64
    frames = _decoded(run / video['path'])
    assert len(frames) == 6 and frames[0] != frames[-1], 'the robot must move'
    assert read_run_record(run, root)['videos'] == [video]
    # Written into the project, and nowhere else.
    assert not list(run.glob('.video-*')) and not list(Path.cwd().glob('rollout-*.webm'))


@needs_ffmpeg
def test_studio_video_draws_the_declared_materials_and_says_where_they_came_from(video_project):
    root, run = video_project, video_project / 'runs/sample'
    undeclared = render(root, 'sample', 'studio')
    assert undeclared['materials']['declared'] is False
    assert {v['role'] for v in undeclared['appearance'].values()} == {'shell'}
    summary = root / 'review/render' / REVISION_A / 'summary.json'
    data = json.loads(summary.read_text())
    data['appearance'] = {'body': {'role': 'accent', 'color': '#F26A1B'},
                          'shin': {'role': 'mechanism', 'color': '#2F3237'}}
    summary.write_text(json.dumps(data))
    declared = render(root, 'sample', 'studio')
    assert declared['materials'] == {'declared': True, 'environment_omitted': [],
                                     'source': f'review/render/{REVISION_A}/summary.json'}
    assert declared['appearance']['body'] == {'role': 'accent', 'color': '#F26A1B'}

    def orange(frame):
        return sum(1 for i in range(0, len(frame), 3)
                   if frame[i] > 150 and frame[i] - frame[i+2] > 90 and frame[i+1] < frame[i] - 40)
    assert orange(_decoded(run / declared['path'])[0]) > 500
    assert orange(_decoded(run / undeclared['path'])[0]) == 0
    # Both recordings are kept, newest first.
    assert [v['sha256'] for v in read_run_record(run, root)['videos']] == [declared['sha256'], undeclared['sha256']]


def test_studio_video_refuses_a_bad_style_and_a_bad_declared_appearance(video_project):
    root, run = video_project, video_project / 'runs/sample'
    with pytest.raises(ValueError, match='unknown style'):
        render(root, 'sample', 'blender')
    summary = root / 'review/render' / REVISION_A / 'summary.json'
    data = json.loads(summary.read_text())
    data['appearance'] = {'body': {'role': 'chrome', 'color': '#FFFFFF'}}
    summary.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='body no valid appearance'):
        render(root, 'sample', 'studio')
    status = read_run_record(run, root)
    assert status['video_render']['state'] == 'failed' and status['videos'] == []
    assert not list(run.glob('*.webm'))


@needs_ffmpeg
def test_dashboard_serves_the_studio_video_it_lists(video_project, monkeypatch):
    root = video_project
    # The claim is the listing and the bytes served, not the pixels (ADR-563).
    monkeypatch.setitem(STUDIO, 'size', 128)
    video = render(root, 'sample', 'studio')
    server, _ = serve(root, '127.0.0.1', 0)
    try:
        listed = json.loads(_get(server.url + 'api/run/sample')[2])
        assert listed['videos'][0]['sha256'] == video['sha256'] and listed['videos'][0]['style'] == 'studio'
        assert listed['resolved']['videos'][0]['exists'] and not listed['resolved']['videos'][0]['error']
        status, headers, body = _get(server.url + 'video/run/sample/0')
        assert status == 200 and headers['content-type'] == 'video/webm'
        assert hashlib.sha256(body).hexdigest() == video['sha256']
    finally:
        server.shutdown()
        server.server_close()


@needs_ffmpeg
def test_studio_video_reads_a_rollout_tessellation_past_the_scene_bounds_and_draws_it_within_budget(
        video_project, monkeypatch):
    """ot10-quadruped-3's w2-1 rollout (ADR-432) retains 2,528,456 triangles in
    611 MB of ASCII STL, deck.stl alone 172 MB: the scene style's 32 MB and
    500k caps refused it before a frame was drawn. Scaled down here: the
    studio style reads a solid past the scene caps in full, clusters it to its
    drawn budget, says so, and every drawn corner is a corner of the source,
    so the bounds move by less than one cell. The scene style still refuses."""
    root, run = video_project, video_project / 'runs/sample'
    (run / 'rollout/torso.stl').write_text(_fine_stl(20.0, 48))   # 27 648 facets, 5.4 MB
    meshes = {'body': stl(run / 'rollout/torso.stl'), 'shin': stl(run / 'rollout/leg.stl')}
    monkeypatch.setattr(video_module, 'MAX_BYTES', 1024 * 1024)
    monkeypatch.setattr(video_module, 'MAX_TRIANGLES', 20_000)
    monkeypatch.setattr(video_module, 'STUDIO_TRIANGLES', 3_000, raising=False)
    with pytest.raises(ValueError, match='artifact size/type refused'):
        render(root, 'sample', 'scene')
    video = render(root, 'sample', 'studio')
    geometry = video['geometry']
    assert geometry['input_triangles'] == sum(map(len, meshes.values())) == 27_648 + len(meshes['shin'])
    assert 0 < geometry['drawn_triangles'] <= geometry['budget_triangles'] == 3_000
    assert geometry['cell_mm'] > 0 and geometry['input_bound_triangles'] == video_module.STUDIO_INPUT_TRIANGLES
    trace = json.loads((run / 'rollout/assembly-simulation-trace.json').read_text())
    frames = [f for f in trace['frames'] if f.get('frame_kind') == 'solver_output']
    points = [p for f in frames for name in meshes for tri in placed(meshes[name], f['component_placements'][name])
              for p in tri]
    exact = [min(p[j] for p in points) for j in range(3)] + [max(p[j] for p in points) for j in range(3)]
    assert all(abs(a - b) < geometry['cell_mm'] for a, b in zip(video['bounds']['min'] + video['bounds']['max'], exact))
    assert video['frames'] == 6 and len(_decoded(run / video['path'])) == 6
    # Refused at the input cap, before anything is drawn.
    monkeypatch.setattr(video_module, 'STUDIO_INPUT_TRIANGLES', 20_000)
    with pytest.raises(ValueError, match='excessive input geometry'):
        render(root, 'sample', 'studio')


@needs_ffmpeg
def test_studio_video_leaves_the_environment_out_and_puts_the_floor_on_top_of_it(video_project, monkeypatch):
    """The render summary's environment (a floor) is not a part: it gets no
    material and is not drawn, and the studio floor is its top face rather
    than the lowest point the solids reach, which a tipping robot drives
    below the floor because the rollout collides on proxies (ADR-281,
    ADR-432): the quadruped's reached -18.5 mm and floated off its shadow."""
    root, run = video_project, video_project / 'runs/sample'
    # The claims are the floor's height and the omitted part, not the pixels (ADR-563).
    monkeypatch.setitem(STUDIO, 'size', 128)
    summary = root / 'review/render' / REVISION_A / 'summary.json'
    data = json.loads(summary.read_text())
    data['appearance'] = {'body': {'role': 'shell', 'color': '#ECE8DF'}}
    data['environment'] = ['shin']
    summary.write_text(json.dumps(data))
    video = render(root, 'sample', 'studio')
    assert video['materials']['environment_omitted'] == ['shin'] and list(video['appearance']) == ['body']
    trace = json.loads((run / 'rollout/assembly-simulation-trace.json').read_text())
    frames = [f for f in trace['frames'] if f.get('frame_kind') == 'solver_output']
    shin = placed(stl(run / 'rollout/leg.stl'), frames[0]['component_placements']['shin'])
    body = [p for f in frames for tri in placed(stl(run / 'rollout/torso.stl'), f['component_placements']['body'])
            for p in tri]
    assert abs(video['floor_z_mm'] - max(p[2] for tri in shin for p in tri)) < 1e-6
    assert abs(video['lowest_reach_z_mm'] - min(p[2] for p in body)) < 1e-6
    assert video['floor_source'] == 'top of the environment geometry: shin'
    # Without an environment the floor is the lowest reach, as before.
    data['appearance']['shin'] = {'role': 'mechanism', 'color': '#2F3237'}
    data['environment'] = []
    summary.write_text(json.dumps(data))
    plain = render(root, 'sample', 'studio')
    assert plain['floor_z_mm'] == plain['lowest_reach_z_mm'] and plain['materials']['environment_omitted'] == []
