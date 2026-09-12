# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Independent synthetic rollout fixtures; real verification is in test_walk."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest

from cadex_cli.video import render, placed, stl
from cadex_cli.review_record import read_run_record
from cadex_cli.review_server import serve
from test_review_server import (browser, needs_browser, _open, _mesh_run,
                                _rewrite_record, _project, REVISION_A)


@pytest.fixture
def video_project(tmp_path):
    root = _project(tmp_path)
    run = _mesh_run(root, 'sample', revision=REVISION_A)
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
    return root


@pytest.fixture
def rendered(video_project):
    if not shutil.which('ffmpeg'):
        pytest.skip('FFmpeg not available')
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
        assert 'Video render: failed' in page.text('#videos') and 'Retry the CLI' in page.text('#videos')
        assert page.evaluate("!!document.querySelector('#videos video')")
        page.click("#views li[data-view='accepted']")
        assert page.evaluate("!document.querySelector('#videos video')")
    finally:
        server.shutdown()
        server.server_close()
