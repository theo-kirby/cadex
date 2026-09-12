# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Render a retained, engine-verified rollout without opening the engine.

Run with ``python -m cadex_cli.video --project DIR --run NAME``. FFmpeg is
an external encoder, never imported. One CPU render per project; no trainer
handles, process groups or training files are touched.
"""
from __future__ import annotations

import argparse
import bisect
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import time

from .render import BASES, PALETTE, png, rasterize
from .review_record import read_run_record, resolve_reference
from .review_server import run_model

FPS = 10
MAX_BYTES = 32 * 1024 * 1024
MAX_TRIANGLES = 20_000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def retained(base, relative):
    item = resolve_reference(base, relative)
    require(item['exists'] and not item['error'], 'missing or refused retained artifact')
    path = base / relative
    require(path.is_file() and path.stat().st_size <= MAX_BYTES, 'artifact size/type refused')
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stl(path):
    data = path.read_bytes()
    if len(data) >= 84 and len(data) == 84 + 50 * struct.unpack_from('<I', data, 80)[0]:
        points = [struct.unpack_from('<3f', data, offset + 12 + j * 12)
                  for offset in range(84, len(data), 50) for j in range(3)]
    else:
        points = [tuple(map(float, row.split()[1:])) for row in data.decode('ascii').splitlines()
                  if row.strip().startswith('vertex ')]
    require(points and len(points) % 3 == 0 and len(points) <= MAX_TRIANGLES * 3,
            'empty or excessive STL')
    require(all(len(p) == 3 and all(math.isfinite(x) and abs(x) < 1e7 for x in p)
                for p in points), 'invalid STL coordinates')
    return [points[i:i+3] for i in range(0, len(points), 3)]


def placed(triangles, pose):
    p, q = pose['position_mm'], pose['rotation_xyzw']
    require(len(p) == 3 and len(q) == 4 and all(math.isfinite(x) and abs(x) < 1e7 for x in p+q),
            'invalid component pose')
    require(abs(sum(x*x for x in q) - 1) < 1e-4, 'non-unit quaternion')
    x, y, z, w = q
    rows = ((1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)),
            (2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)),
            (2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)))
    return [tuple(tuple(sum(row[j]*v[j] for j in range(3))+p[k]
                        for k, row in enumerate(rows)) for v in tri) for tri in triangles]


def atomic_json(path, data):
    temporary = path.with_suffix('.partial')
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True)+'\n')
    temporary.replace(path)


def render(project, name):
    root = Path(project).resolve()
    require(bool(re.fullmatch(r'[A-Za-z0-9_-]+', name)), 'invalid run name')
    directory = root / 'runs' / name
    require(directory.is_dir() and directory.resolve() == directory and
            (root / 'runs').resolve() == root / 'runs', 'missing or symlinked run directory')
    # O_NOFOLLOW also refuses an existing lock symlink. flock is released on
    # crash; it serializes only this renderer, never training or the engine.
    fd = os.open(root / '.video.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _render(root, directory)


def _render(root, directory):
    started = time.monotonic()
    status_path = directory / 'video.json'
    require(not status_path.is_symlink() and not status_path.with_suffix('.partial').is_symlink(),
            'symlinked video status refused')
    old = {}
    if status_path.is_file():
        old = json.loads(status_path.read_text())
    status = {'schema': 'cadex-run-video-v1', 'state': 'rendering',
              'videos': old.get('videos', []), 'error': None}
    atomic_json(status_path, status)
    try:
        record = read_run_record(directory, root)
        identity = record['model']
        revision = identity['accepted_revision']
        require(bool(re.fullmatch('[0-9a-f]{64}', revision or '')), 'no accepted revision')
        require(any(leg.get('leg') == 'rollout' and leg.get('exit') == 0 and
                    leg.get('accepted_revision') == revision and leg.get('digest') == identity['digest']
                    for leg in record['legs']), 'no successful recorded rollout at this identity')
        trace_path = retained(directory, record['artifacts']['trace'])
        trace = json.loads(trace_path.read_text())
        require(trace.get('schema') == 'cadex-assembly-simulation-trace-v1', 'unsupported trace')
        evidence = trace['policy']
        policy = retained(root, record['policy']['asset'])
        require(digest(policy) == evidence['policy_sha256'] == record['policy']['sha256'],
                'policy digest mismatch')
        require(evidence['task_sha256'] == record['task']['sha256'] and
                evidence['seed'] == record['rollout']['seed'], 'task or seed mismatch')
        model = retained(directory, record['artifacts']['model_xml'])
        require(digest(model) == evidence['model_sha256'], 'model digest mismatch')
        frames = [f for f in trace['frames'] if f.get('frame_kind') == 'solver_output']
        require(2 <= len(frames) <= 3601, 'missing or excessive solved frames')
        times = [f['nominal_time_s'] for f in frames]
        require(all(type(t) in (int, float) and math.isfinite(t) for t in times) and
                times[0] == 0 and 0 < times[-1] <= 60 and
                all(b > a for a, b in zip(times, times[1:])), 'invalid or excessive simulation times')
        manifest = run_model(root, record)
        require(manifest['available'], 'no retained rollout model')
        names = trace['component_outputs']
        require(names and len(names) == len(set(names)), 'invalid component list')
        meshes = {}
        for entry in manifest['components']:
            if entry['name'] in names:
                require(entry['mesh_status'] == 'retained', 'missing component mesh')
                meshes[entry['name']] = stl(retained(directory, str(trace_path.parent.relative_to(directory) /
                                                                    (entry['output'] + '.stl'))))
        require(set(meshes) == set(names) and sum(map(len, meshes.values())) <= MAX_TRIANGLES,
                'incomplete or excessive component geometry')
        def geometry(frame):
            poses = frame['component_placements']
            require(set(poses) == set(names), 'incomplete frame')
            return [(PALETTE[i % len(PALETTE)], tri) for i, name in enumerate(names)
                    for tri in placed(meshes[name], poses[name])]
        # Fit once over every visited pose: a moving camera would conceal travel.
        lo, hi = [math.inf]*2, [-math.inf]*2
        for frame in frames:
            require(time.monotonic()-started < 300, 'render exceeded 300 seconds')
            for _, tri in geometry(frame):
                for point in tri:
                    for j, axis in enumerate(BASES['iso'][:2]):
                        v = sum(point[k]*axis[k] for k in range(3))
                        lo[j], hi[j] = min(lo[j], v), max(hi[j], v)
        count = math.ceil(times[-1]*FPS) + 1
        with tempfile.TemporaryDirectory(prefix='.video-', dir=directory) as temporary:
            work = Path(temporary)
            for i in range(count):
                require(time.monotonic()-started < 300, 'render exceeded 300 seconds')
                # Hold the latest solved sample; never invent interpolated dynamics.
                frame = frames[-1] if i == count-1 else frames[max(0, bisect.bisect_right(times, i/FPS)-1)]
                pixels, _ = rasterize(geometry(frame), BASES['iso'], bounds=(lo, hi))
                (work / f'{i:04d}.png').write_bytes(png(pixels))
            result = subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-threads', '1',
                '-framerate', str(FPS), '-i', str(work / '%04d.png'), '-an', '-c:v', 'libvpx-vp9',
                '-threads', '1', '-pix_fmt', 'yuv420p', str(work / 'rollout.webm')],
                capture_output=True, timeout=60)
            require(result.returncode == 0, 'FFmpeg encoding failed')
            # Decode every frame before publishing. Encoder exit 0 alone is not evidence.
            check = subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-i',
                str(work / 'rollout.webm'), '-f', 'framemd5', '-'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            decoded = [line for line in check.stdout.splitlines() if line and not line.startswith(b'#')]
            require(check.returncode == 0 and len(decoded) == count,
                    'video decoding/frame count failed')
            sha = digest(work / 'rollout.webm')
            target = directory / ('rollout-' + sha + '.webm')
            (work / 'rollout.webm').replace(target)
        video = {'path': target.name, 'sha256': sha, 'accepted_revision': revision,
                 'model_digest': identity['digest'], 'policy_sha256': evidence['policy_sha256'],
                 'task_sha256': evidence['task_sha256'], 'seed': evidence['seed'],
                 'sim_seconds': times[-1], 'duration_seconds': count/FPS, 'fps': FPS,
                 'frames': count, 'trace_sha256': digest(trace_path),
                 'render_seconds': round(time.monotonic()-started, 3),
                 'sampling': '10 fps, latest solved pose plus final pose, fixed camera; tessellation preview'}
        status.update(state='ready', videos=[video])
        atomic_json(status_path, status)
        return video
    except Exception as exc:
        status.update(state='failed', error=f'{type(exc).__name__}: {exc}')
        atomic_json(status_path, status)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(render(args.project, args.run), sort_keys=True))
    except Exception as exc:
        parser.exit(1, f'video: {exc}\n')


if __name__ == '__main__':
    main()
