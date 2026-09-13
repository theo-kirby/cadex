# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Independent synthetic rollout fixtures; real verification is in test_walk."""
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import sys
import time

import pytest

from cadex_cli.video import render, placed, stl
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


@pytest.mark.parametrize('fault', ['policy', 'time', 'pose', 'escape', 'encoder'])
def test_render_refuses_invalid_inputs_without_touching_training(video_project, monkeypatch, fault):
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
    if fault == 'encoder': monkeypatch.setenv('PATH', '')
    # A real independent process stands in for the trainer: rendering must
    # neither terminate it nor change its telemetry file. No GPU claim.
    heartbeat = run / 'train/heartbeat'
    process = subprocess.Popen([sys.executable, '-c',
        'import time,pathlib,sys\np=pathlib.Path(sys.argv[1])\n'
        'for i in range(1000):\n p.write_text(str(i)); time.sleep(.02)', str(heartbeat)])
    try:
        with pytest.raises((ValueError, FileNotFoundError)):
            render(root, 'sample')
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
def test_browser_revisits_history_beyond_video_cache_across_process_restart(rendered, browser):
    """257 independent retained paths, real process restart, synthetic rollouts.

    These are repeated runs of one model, not 257 trained policies. The early
    and late run names must survive selection even though their model is shared.
    """
    root, video = rendered
    _manifest(root, REVISION_B)
    sample = root / 'runs/sample'
    for index in range(257):
        run = root / 'runs' / f'history-{index:03d}'
        shutil.copytree(sample, run)
        record_path = run / 'run.json'
        record = json.loads(record_path.read_text())
        record['run'] = run.name
        record['training']['requested']['iterations'] = index + 10
        record_path.write_text(json.dumps(record))
        (run / 'train/progress.json').write_text(json.dumps({
            'schema': 'cadex-training-progress-v1', 'state': 'done',
            'updated_at': time.time(), 'task_sha256': record['task']['sha256'],
            'iteration': index + 10, 'total': index + 10,
            'reward_per_step': index, 'loss': 1, 'episode_steps': 20,
            'curve': [[i, i] for i in range(index + 1)],
            'loss_curve': [[i, 1] for i in range(index + 1)],
            'episode_steps_curve': [[i, 20] for i in range(index + 1)],
            'checkpoints': [],
        }))
    shutil.rmtree(sample)

    def snapshot():
        return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in root.rglob('*') if path.is_file()}

    before = snapshot()
    processes = []

    def start(port=0):
        process = subprocess.Popen(
            [sys.executable, '-m', 'cadex_cli', 'review', '--project', str(root),
             '--port', str(port), '--json'], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
            env={**os.environ, 'PYTHONPATH': str(CLI_DIR)})
        processes.append(process)
        assert select.select([process.stderr], [], [], 20)[0], 'server did not start'
        line = process.stderr.readline()
        assert ' at http://' in line, line
        return process, line.split(' at ')[1].split(' ')[0]

    def stop(process):
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=20)
        assert process.returncode == 0, stdout + stderr

    def visit(page, name, *, damaged=False):
        page.click(f"#views li[data-run='{name}']")
        page.wait_for("document.getElementById('view-kind').textContent === "
                      + json.dumps('RUN ' + name))
        assert page.text('#view-revision') == REVISION_A
        assert page.text('#view-digest') == 'd' * 64
        assert page.text('#view-relation').startswith('HISTORICAL')
        assert page.text("#params tr[data-param='leg_len'] td:nth-child(2)") == '90'
        assert page.text("#params tr[data-param='leg_len'] td:nth-child(3)") == '80'
        assert _model_state(page) == 'loaded'
        state = page.evaluate('window.cadexReview.state()')
        assert state['selected'] == name and state['model']['revision'] == REVISION_A
        assert name in page.text('#model-status')
        assert video['policy_sha256'] in page.text("#training tr[data-key='policy']")
        index = int(name.rsplit('-', 1)[1])
        assert page.attribute('#telemetry', 'data-state') == 'done'
        assert page.text("#training tr[data-key='requested iterations'] td") == str(index + 10)
        assert page.text('[data-metric=iteration]') == f'iteration: {index + 10}'
        for curve in ('curve', 'loss_curve', 'episode_steps_curve'):
            assert page.attribute(f'[data-history={curve}]', 'data-points') == str(index + 1)
        assert 'seed 7' in page.text('#videos')
        if damaged:
            page.wait_for("document.getElementById('videos').textContent.includes('digest mismatch')")
            assert not page.evaluate("!!document.querySelector('#videos video, #videos a')")
            assert 'Retry the CLI video command' in page.text('#videos')
            for headers in ({}, {'Range': 'bytes=0-15'}):
                assert _get(url + f'video/run/{name}/0', headers)[0] == 404
        else:
            page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
            page.evaluate("window.historyVideo=document.querySelector('#videos video'); "
                          "historyVideo.muted=true; historyVideo.loop=true; historyVideo.play()",
                          await_promise=True)
            page.wait_for('historyVideo.currentTime > 0.1')
            download = page.download('#videos a')
            assert f'/video/run/{name}/0?download=1' in download.url
            assert hashlib.sha256(download.path.read_bytes()).hexdigest() == video['sha256']

    early = root / 'runs/history-000' / video['path']
    original = early.read_bytes()
    try:
        first, url = start()
        page = _open(browser, url)
        assert page.evaluate("document.querySelectorAll('#views li[data-run]').length") == 257
        for name in ('history-000', 'history-256', 'history-000'):
            visit(page, name)
        assert snapshot() == before

        # Same-size corruption, with mtime restored, after cache churn. The
        # other retained runs must still play; corruption must survive restart.
        stamp = early.stat()
        early.write_bytes(bytes([original[0] ^ 1]) + original[1:])
        os.utime(early, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
        visit(page, 'history-000', damaged=True)
        visit(page, 'history-256')
        page.evaluate("window.historyRestartMarker='same page'")
        stop(first)
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
        assert page.attribute('#freshness', 'data-state') == 'stale'
        second, restarted_url = start(int(url.rstrip('/').rsplit(':', 1)[1]))
        assert second.pid != first.pid and restarted_url == url
        page.wait_for("document.getElementById('freshness').dataset.state === 'live'")
        assert page.evaluate('window.historyRestartMarker') == 'same page'
        for name in ('history-256', 'history-000'):
            visit(page, name, damaged=name == 'history-000')

        replacement = early.with_suffix('.partial')
        replacement.write_bytes(original)
        replacement.replace(early)
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
        for name in ('history-000', 'history-256', 'history-000'):
            visit(page, name)
        assert page.evaluate("performance.getEntriesByType('navigation').length") == 1
        stop(second)
        assert snapshot() == before, 'inspection changed retained project content'
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=20)


@needs_browser
def test_browser_plays_downloads_and_keeps_playback_across_polls(rendered, browser):
    root, video = rendered
    server, _ = serve(root, '127.0.0.1', 0)
    try:
        page = _open(browser, server.url)
        page.click("#views li[data-run='sample']")
        page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
        assert REVISION_A[:12] in page.text('#videos')
        assert video['policy_sha256'][:12] in page.text('#videos')
        assert 'seed 7' in page.text('#videos') and '0.50000 s' in page.text('#videos')
        page.evaluate("window.testVideo=document.querySelector('#videos video'); testVideo.muted=true; testVideo.loop=true; testVideo.play()", await_promise=True)
        page.wait_for('testVideo.currentTime > 0.1')
        for _ in range(3):
            page.evaluate('window.cadexReview.refresh()', await_promise=True)
            assert page.evaluate("testVideo === document.querySelector('#videos video') && !testVideo.paused")
        assert abs(page.evaluate('testVideo.duration') - .6) < .11
        # The download the browser itself wrote: the retained file, byte for byte.
        download = page.download('#videos a')
        assert download.url.endswith('/video/run/sample/0?download=1')
        assert download.path.name == video['path']
        assert download.received_bytes == download.total_bytes == download.path.stat().st_size
        assert hashlib.sha256(download.path.read_bytes()).hexdigest() == video['sha256']
        # A failed rerender preserves the prior playable result and names its failure.
        (root / 'assets/gait.cxpolicy').write_bytes(b'changed')
        with pytest.raises(ValueError, match='policy digest'):
            render(root, 'sample')
        page.evaluate('window.cadexReview.refresh()', await_promise=True)
        assert 'Recorded video render: failed' in page.text('#videos') and 'Retry the CLI' in page.text('#videos')
        assert page.evaluate("!!document.querySelector('#videos video')")
        page.click("#views li[data-view='accepted']")
        assert page.evaluate("!document.querySelector('#videos video')")
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_shared_scene_matches_decoded_video_and_keeps_older_recording(rendered, browser):
    """Same solved pose/camera pixels, plus a real retained older encoding."""
    root, video = rendered
    run = root / 'runs/sample'
    legacy_path = run / 'legacy.webm'
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(run/video['path']),
                    '-c', 'copy', '-metadata', 'comment=prior recording', str(legacy_path)], check=True)
    legacy = {**video, 'path': legacy_path.name,
              'sha256': hashlib.sha256(legacy_path.read_bytes()).hexdigest()}
    legacy.pop('style')
    # The original recording may predate video.json and live in run.json.
    (run/'video.json').unlink()
    original = json.loads((run/'run.json').read_text())
    original['videos'] = [legacy]
    (run/'run.json').write_text(json.dumps(original))
    newest = render(root, 'sample')
    record = read_run_record(run, root)
    assert record['videos'] == [newest, legacy]
    assert all(v['exists'] and not v['error'] for v in record['resolved']['videos'])
    assert newest['style'] == 'cadex-prototype-dark-v1'
    assert len(newest['style_sha256']) == 64
    server, _ = serve(root, '127.0.0.1', 0)
    try:
        page = _open(browser, server.url)
        page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
        assert 'historical legacy style' in page.text('#videos')
        trace = json.loads((run/'rollout/assembly-simulation-trace.json').read_text())
        frame = next(f for f in trace['frames'] if f.get('frame_kind') == 'solver_output')
        page.evaluate("document.getElementById('viewer').style.cssText='width:512px;height:512px;border:0;padding:0'")
        # The video's first frame: its follow camera, the first solved pose and the timer at 0 s,
        # each through the viewport's own shared scene (ADR-332).
        page.evaluate('cadexReview.viewer().frameBounds('+json.dumps(newest['bounds'])+');'
                      'cadexReview.viewer().setCamera('+json.dumps(newest['camera'])+');'
                      'cadexReview.viewer().setClock(0);'
                      'cadexReview.viewer().setPoses('+json.dumps(frame['component_placements'])+')')
        import base64
        image = run/'viewport.png'
        image.write_bytes(base64.b64decode(page.evaluate('cadexReview.viewer().png()')))
        def rgb(path):
            return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-frames:v','1',
                                            '-f','rawvideo','-pix_fmt','rgb24','-'])
        a,b = rgb(image),rgb(run/newest['path'])
        assert len(a) == len(b) == 512*512*3
        assert sum(abs(x-y) for x,y in zip(a,b))/len(a) < 3
        for index in (0, 1):
            selector = f'#videos li[data-video="{index}"]'
            page.wait_for(f'document.querySelector(\'{selector} video\').readyState >= 2')
            page.evaluate(f"window.retainedVideo=document.querySelector('{selector} video');retainedVideo.muted=true;retainedVideo.play()", await_promise=True)
            page.wait_for('retainedVideo.currentTime > .1')
            download = page.download(selector+' a')
            assert hashlib.sha256(download.path.read_bytes()).hexdigest() == record['videos'][index]['sha256']
    finally:
        server.shutdown();server.server_close()


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


@needs_browser
def test_video_shows_the_solids_never_the_proxies_and_says_so(rendered, browser):
    """D4 (ADR-333): a recording is the tessellated solids; the run's proxies
    differ from them, and the decoded first frame matches the shared scene
    with the proxies hidden and not with them shown; the page's identity
    strip names what the video shows, and an older video says it did not."""
    root, video = rendered
    assert video['showing'] == 'tessellated solids of the accepted revision; collision proxies not drawn'
    assert video['proxies'] == {'drawn': False, 'retained': 2}
    run = root / 'runs/sample'
    record = read_run_record(run, root)
    manifest = run_model(root, record)
    assert manifest['collision']['available'] and len(manifest['collision']['geoms']) == 2
    trace = json.loads((run / 'rollout/assembly-simulation-trace.json').read_text())
    frame = next(f for f in trace['frames'] if f.get('frame_kind') == 'solver_output')
    entries = [{'name': e['name'], 'placement': frame['component_placements'][e['name']],
                'positions': [v for t in stl(run / 'rollout' / (e['output'] + '.stl')) for pt in t for v in pt]}
               for e in manifest['components'] if e['name'] in frame['component_placements']]
    def rgb(path):
        return subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-frames:v', '1',
                                        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
    decoded = rgb(run / video['path'])
    server, _ = serve(root, '127.0.0.1', 0)
    try:
        page = browser.page(server.url + 'capture.html')
        page.wait_for('window.cadexCapture?.available')
        page.evaluate('cadexCapture.install(' + json.dumps(entries) + '); cadexCapture.frameBounds(' + json.dumps(video['bounds']) + ');'
                      'cadexCapture.setCamera(' + json.dumps(video['camera']) + '); cadexCapture.setClock(0);'
                      'cadexCapture.setProxies(' + json.dumps(manifest['collision']['geoms']) + ')')
        import base64
        def shot(shown):
            path = run / f'proxies-{shown}.png'
            page.evaluate(f'cadexCapture.showProxies({json.dumps(shown)})')
            path.write_bytes(base64.b64decode(page.evaluate('cadexCapture.png()')))
            return rgb(path)
        hidden, shown = shot(False), shot(True)
        assert len(hidden) == len(shown) == len(decoded) == 512 * 512 * 3
        outline = sum(1 for i in range(0, len(hidden), 3)
                      if sum(abs(a - b) for a, b in zip(hidden[i:i+3], shown[i:i+3])) > 40)
        assert outline > 1000, 'the proxies draw as outlines the solids do not cover'
        error_hidden = sum(abs(x - y) for x, y in zip(hidden, decoded)) / len(decoded)
        error_shown = sum(abs(x - y) for x, y in zip(shown, decoded)) / len(decoded)
        assert error_hidden < 3, 'the decoded frame is the solids, inside the codec tolerance'
        assert error_shown > 1.5 * error_hidden, 'the decoded frame is not the proxies'
        assert page.evaluate('cadexCapture.stats().showing') == 'tessellated solids with collision proxies'
        assert page.evaluate('cadexCapture.modelPixels().count') > page.evaluate('cadexCapture.showProxies(false); cadexCapture.modelPixels().count')
        # An older recording that never said what it showed is labelled as such on the page.
        legacy = {**video, 'path': 'older.webm', 'sha256': '1' * 64}
        legacy.pop('showing'); legacy.pop('proxies')
        status = json.loads((run / 'video.json').read_text())
        status['videos'] = [video, legacy]
        (run / 'video.json').write_text(json.dumps(status))
        page = _open(browser, server.url)
        page.wait_for("document.querySelectorAll('#videos li[data-video]').length === 2")
        assert page.attribute('#videos li[data-video="0"]', 'data-showing') == 'solids'
        assert '· showing tessellated solids of the accepted revision; collision proxies not drawn' in page.text('#videos li[data-video="0"]')
        assert page.attribute('#videos li[data-video="1"]', 'data-showing') == 'unrecorded'
        assert 'showing not recorded' in page.text('#videos li[data-video="1"]')
    finally:
        server.shutdown(); server.server_close()


@needs_browser
def test_video_availability_tracks_missing_partial_restored_and_history(rendered, browser):
    root, video = rendered
    current = root / 'runs/sample'
    shutil.copytree(current, root / 'runs/history')
    history_record = root / 'runs/history/run.json'
    history_record.write_text(json.dumps({**json.loads(history_record.read_text()), 'run': 'history'}))
    path = current / video['path']
    original = path.read_bytes()
    server, _ = serve(root, '127.0.0.1', 0)
    try:
        page = _open(browser, server.url)
        page.click("#views li[data-run='sample']")

        def availability(expected):
            page.wait_for("document.querySelector('#videos > li')?.textContent === " + json.dumps(expected))
            assert 'Recorded video render: ready' in page.text('#videos')

        availability('Video files: available (1/1 retained)')
        for fault in ('missing', 'partial'):
            if fault == 'missing':
                path.unlink()
            else:
                path.write_bytes(original[:64])
            # Automatic polling in the same page must override the saved ready receipt.
            availability('Video files: unavailable (0/1 retained)')
            assert ('missing' if fault == 'missing' else 'digest mismatch') in page.text('#videos')
            assert not page.evaluate("!!document.querySelector('#videos video, #videos a')")
            assert 'Retry the CLI video command' in page.text('#videos')
            page.click("#views li[data-run='history']")
            availability('Video files: available (1/1 retained)')
            page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
            page.evaluate("window.keptVideo=document.querySelector('#videos video'); keptVideo.muted=true; keptVideo.loop=true; keptVideo.play()", await_promise=True)
            page.wait_for('keptVideo.currentTime > 0.1')
            page.evaluate('cadexReview.refresh()', await_promise=True)
            assert page.text('#view-kind') == 'RUN history'
            assert page.evaluate("keptVideo === document.querySelector('#videos video') && !keptVideo.paused")
            download = page.download('#videos a')
            assert hashlib.sha256(download.path.read_bytes()).hexdigest() == video['sha256']
            page.click("#views li[data-run='sample']")
            availability('Video files: unavailable (0/1 retained)')
            path.write_bytes(original)
            availability('Video files: available (1/1 retained)')
            page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
            download = page.download('#videos a')
            assert hashlib.sha256(download.path.read_bytes()).hexdigest() == video['sha256']
        # A run can retain one usable recording while a second is missing.
        receipt_path = current / 'video.json'
        receipt = json.loads(receipt_path.read_text())
        receipt['videos'].append({**video, 'path': 'missing.webm'})
        receipt_path.write_text(json.dumps(receipt))
        availability('Video files: partly available (1/2 retained)')
        assert page.evaluate("document.querySelectorAll('#videos video').length") == 1
        assert page.evaluate("performance.getEntriesByType('navigation').length") == 1
    finally:
        server.shutdown()
        server.server_close()
