# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Render a retained, engine-verified rollout without opening the engine.

Run with ``python -m cadex_cli.video --project DIR --run NAME``. FFmpeg is
an external encoder, never imported. One render per project at a time; no trainer
handles, process groups or training files are touched.

Two styles draw the same validated frames. ``studio`` (the command's default,
ot10 W1, ADR-431) draws each one with the engine's ``CadexStudio`` studio
renderer on the CPU, in the design's own materials, with no browser and no
display. ``scene`` is the review viewport's Three.js scene in headless
Chromium (ADR-332).
"""
from __future__ import annotations

import argparse
from array import array
import base64
import bisect
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time

from .studio import STUDIO as studio_render
from .browser import HeadlessBrowser, find_browser
from .review_server import serve, STATIC_DIR
from .review_record import read_run_record, resolve_reference
from .review_server import run_model

FPS = 10
MAX_BYTES = 32 * 1024 * 1024
MAX_TRIANGLES = 500_000
# The follow rig's declared framing (DASHBOARD.md §10, ADR-332): the subject's standing
# height — its vertical extent at the first solved pose — fills this fraction of the frame
# height, and the camera anchor is a Hann-smoothed subject track with this half-window at FPS
# (0.4 s, the reference's 20 frames at 50 Hz). The rest of the rig's numbers are the scene
# module's FOLLOW defaults; every one is recorded into the video it framed.
FRAMING = {'fraction': 0.22, 'smooth_frames': 4}
STYLES = ('studio', 'scene')
#: The studio style (ADR-431): the hero view, followed. The window is the
#: largest pose's projected extent plus this pad on each side, and it is
#: widened until every frame's pose is inside it, so it never loses the robot.
STUDIO = {'size': 512, 'pad': 0.12, 'smooth_frames': 4}
#: Declared bound on a whole render, drawing and encoding included. The
#: studio style is pure-Python CPU work proportional to triangles x frames:
#: ot6 Finch (95,212 triangles, 81 frames) is the measured case.
RENDER_SECONDS = 300
#: What the studio style reads and draws (ADR-432). A rollout leg writes each
#: solid at its own tessellation, far finer than a render's: ot10-quadruped-3's
#: w2-1 rollout is 2,528,456 triangles in 611 MB of ASCII STL, deck.stl alone
#: 172 MB, where its render drew 78,419. So the studio style reads each solid as
#: a stream, bounded at the INPUT caps, and clusters its vertices into a grid
#: cell a quarter of a pixel wide, doubled until the drawn total fits, as
#: render's snapshot does. The scene style keeps MAX_BYTES and MAX_TRIANGLES:
#: its page loads every retained solid whole.
STUDIO_SOURCE_BYTES = 256 * 1024 * 1024
STUDIO_INPUT_TRIANGLES = 4_000_000
STUDIO_TRIANGLES = 120_000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def retained(base, relative, limit=None):
    item = resolve_reference(base, relative)
    require(item['exists'] and not item['error'], 'missing or refused retained artifact')
    path = base / relative
    require(path.is_file() and path.stat().st_size <= (limit or MAX_BYTES), 'artifact size/type refused')
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


def stl_stream(path, budget):
    """A flat ``array('d')`` of corner coordinates, nine per triangle, read as a stream.

    The same two encodings as :func:`stl`, without holding the text or a tuple
    per corner: ot10-quadruped-3's 172 MB deck.stl becomes 49 MB of doubles.
    Refuses more than ``budget`` triangles as soon as it has read them.
    """
    flat = array('d')
    with open(path, 'rb') as handle:
        head = handle.read(84)
        size = path.stat().st_size
        if len(head) == 84 and size == 84 + 50 * struct.unpack_from('<I', head, 80)[0]:
            require((size - 84) // 50 <= budget, 'excessive input geometry')
            for record in struct.iter_unpack('<12fH', handle.read()):
                flat.extend(record[3:12])
        else:
            handle.seek(0)
            for line in handle:
                line = line.lstrip()
                if line.startswith(b'vertex'):
                    fields = line.split()
                    require(len(fields) == 4, 'invalid STL coordinates')
                    flat.extend((float(fields[1]), float(fields[2]), float(fields[3])))
                    require(len(flat) <= budget * 9, 'excessive input geometry')
    require(flat and len(flat) % 9 == 0, 'empty or excessive STL')
    require(all(math.isfinite(x) and abs(x) < 1e7 for x in flat), 'invalid STL coordinates')
    return flat


def _clustered(flat, cell):
    """Triangles of ``flat`` with each corner moved to the first corner seen in
    its grid cell; collapsed triangles dropped and duplicates kept once, as
    ``render._cluster`` does. Every drawn corner is a corner of the source."""
    floor, first, kept, seen = math.floor, {}, [], set()
    for t in range(0, len(flat), 9):
        corners = []
        for o in (t, t+3, t+6):
            x, y, z = flat[o], flat[o+1], flat[o+2]
            corners.append(first.setdefault((floor(x/cell), floor(y/cell), floor(z/cell)), (x, y, z)))
        a, b, c = corners
        if a == b or b == c or a == c:
            continue
        key = tuple(sorted(corners))
        if key not in seen:
            seen.add(key)
            kept.append((a, b, c))
    return kept


def studio_meshes(sources):
    """``(meshes, geometry)``: every named solid read in full, then drawn within STUDIO_TRIANGLES."""
    flats, total = {}, 0
    for name, path in sources.items():
        flats[name] = stl_stream(path, STUDIO_INPUT_TRIANGLES - total)
        total += len(flats[name]) // 9
    return drawn_meshes(flats)


def drawn_meshes(flats):
    """``(meshes, geometry)`` for solids already read as flat corner arrays, nine per triangle."""
    total = sum(len(flat) // 9 for flat in flats.values())
    geometry = {'input_triangles': total, 'drawn_triangles': total, 'cell_mm': None,
                'budget_triangles': STUDIO_TRIANGLES, 'input_bound_triangles': STUDIO_INPUT_TRIANGLES}
    if total <= STUDIO_TRIANGLES:
        return ({name: [((f[i], f[i+1], f[i+2]), (f[i+3], f[i+4], f[i+5]), (f[i+6], f[i+7], f[i+8]))
                        for i in range(0, len(f), 9)] for name, f in flats.items()}, geometry)
    extent = max(max(f[j::3]) - min(f[j::3]) for f in flats.values() for j in range(3))
    require(extent > 0, 'zero model extent')
    cell = extent / (4 * STUDIO['size'])
    while True:
        meshes = {name: _clustered(f, cell) for name, f in flats.items()}
        drawn = sum(map(len, meshes.values()))
        if drawn <= STUDIO_TRIANGLES:
            break
        require(cell < extent, 'excessive input geometry')
        cell *= 2.0
    require(all(meshes.values()), 'a solid vanished at the drawn resolution')
    geometry.update(drawn_triangles=drawn, cell_mm=cell, cell_fraction_of_extent=cell/extent)
    return meshes, geometry


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


def render(project, name, style='scene'):
    root = Path(project).resolve()
    require(style in STYLES, 'unknown style; choose ' + ' or '.join(STYLES))
    require(bool(re.fullmatch(r'[A-Za-z0-9_-]+', name)), 'invalid run name')
    directory = root / 'runs' / name
    require(directory.is_dir() and directory.resolve() == directory and
            (root / 'runs').resolve() == root / 'runs', 'missing or symlinked run directory')
    # O_NOFOLLOW also refuses an existing lock symlink. flock is released on
    # crash; it serializes only this renderer, never training or the engine.
    fd = os.open(root / '.video.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _render(root, directory, style)


def _render(root, directory, style='scene'):
    started = time.monotonic()
    status_path = directory / 'video.json'
    require(not status_path.is_symlink() and not status_path.with_suffix('.partial').is_symlink(),
            'symlinked video status refused')
    old = {"videos": read_run_record(directory, root).get("videos", [])}
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
        # Every solid is read and validated here, once, and its triangle count is what the
        # page must report back after fetching the same retained file over the local server.
        meshes, sources, entries = {}, {}, []
        for entry in manifest['components']:
            if entry['name'] in names:
                require(entry['mesh_status'] == 'retained' and entry.get('mesh'), 'missing component mesh')
                relative = str(trace_path.parent.relative_to(directory) / (entry['output'] + '.stl'))
                if style == 'studio':
                    sources[entry['name']] = retained(directory, relative, STUDIO_SOURCE_BYTES)
                else:
                    meshes[entry['name']] = stl(retained(directory, relative))
                # Manifest order is the component colour identity in both clients.
                entries.append({'name': entry['name'], 'mesh': entry['mesh'],
                                'placement': frames[0]['component_placements'][entry['name']]})
        geometry = None
        if style == 'studio':
            require(set(sources) == set(names), 'incomplete or excessive component geometry')
            meshes, geometry = studio_meshes(sources)
        require(set(meshes) == set(names) and sum(map(len, meshes.values())) <= MAX_TRIANGLES,
                'incomplete or excessive component geometry')
        for frame in frames:
            poses = frame['component_placements']
            require(set(poses) == set(names), 'incomplete frame')
            for name in names:
                placed((), poses[name])   # the pose checks, without transforming anything
        count = math.ceil(times[-1]*FPS) + 1
        def sample(i):
            return len(frames)-1 if i == count-1 else max(0, bisect.bisect_right(times, i/FPS)-1)
        with tempfile.TemporaryDirectory(prefix='.video-', dir=directory) as temporary:
            work = Path(temporary)
            if style == 'studio':
                looks, materials = studio_materials(root, record, names)
                drawn = _studio_frames(looks, materials, names, meshes, frames, times, count, sample, work, started)
                drawn['geometry'] = geometry
            else:
                drawn = _scene_frames(root, entries, meshes, frames, count, sample, times, work, started)
            sha = encode(work, count)
            target = directory / ('rollout-' + sha + '.webm')
            (work / 'rollout.webm').replace(target)
        video = {'path': target.name, 'sha256': sha, 'accepted_revision': revision,
                 'model_digest': identity['digest'], 'policy_sha256': evidence['policy_sha256'],
                 'task_sha256': evidence['task_sha256'], 'seed': evidence['seed'],
                 'sim_seconds': times[-1], 'duration_seconds': count/FPS, 'fps': FPS,
                 'frames': count, 'trace_sha256': digest(trace_path),
                 'render_seconds': round(time.monotonic()-started, 3),
                 'render_bound_seconds': RENDER_SECONDS,
                 'overlay': 'timer: simulation seconds, bottom left',
                 'showing': 'tessellated solids of the accepted revision; collision proxies not drawn',
                 'proxies': {'drawn': False,
                             'retained': len(manifest['collision']['geoms']) if manifest['collision']['available'] else None},
                 **drawn}
        status.update(state='ready', videos=[video] + [v for v in old.get('videos', []) if v.get('sha256') != sha])
        atomic_json(status_path, status)
        return video
    except Exception as exc:
        status.update(state='failed', error=f'{type(exc).__name__}: {exc}')
        atomic_json(status_path, status)
        raise


def ffmpeg():
    """The encoder: the one on ``PATH``, else the one beside this interpreter.

    ``./cadex`` runs the pixi environment's Python without putting that
    environment on ``PATH``, and the environment is where FFmpeg is.
    """
    found = shutil.which('ffmpeg')
    beside = Path(sys.executable).parent / 'ffmpeg'
    if not found and beside.is_file() and os.access(beside, os.X_OK):
        found = str(beside)
    require(found, 'FFmpeg is required and is neither on PATH nor beside the interpreter')
    return found


def encode(work, count):
    """``work/%04d.png`` encoded as ``work/rollout.webm``; its sha256 once all ``count`` frames decode."""
    encoder = ffmpeg()
    result = subprocess.run([encoder, '-v', 'error', '-nostdin', '-threads', '1',
        '-framerate', str(FPS), '-i', str(work / '%04d.png'), '-an', '-c:v', 'libvpx-vp9',
        '-threads', '1', '-pix_fmt', 'yuv420p', str(work / 'rollout.webm')],
        capture_output=True, timeout=60)
    require(result.returncode == 0, 'FFmpeg encoding failed')
    # Decode every frame before publishing. Encoder exit 0 alone is not evidence.
    check = subprocess.run([encoder, '-v', 'error', '-nostdin', '-i',
        str(work / 'rollout.webm'), '-f', 'framemd5', '-'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    decoded = [line for line in check.stdout.splitlines() if line and not line.startswith(b'#')]
    require(check.returncode == 0 and len(decoded) == count,
            'video decoding/frame count failed')
    return digest(work / 'rollout.webm')


def _scene_frames(root, entries, meshes, frames, count, sample, times, work, started):
    """The review scene in headless Chromium, one PNG per sampled frame into ``work``."""
    executable = find_browser()
    require(executable is not None, 'headless Chromium required (CADEX_BROWSER or PATH)')
    server, _ = serve(root, '127.0.0.1', 0)
    try:
        with HeadlessBrowser(executable, width=512, height=512) as browser:
            page = browser.page(server.url + 'capture.html')
            page.wait_for('window.cadexCapture?.available')
            # The page fetches each retained solid from the server over the run
            # directory Python just validated, and reports what it built; a count
            # that differs from the validated file's is a different file.
            loaded = page.evaluate('cadexCapture.load(' + json.dumps({'components': entries}) + ')',
                                   await_promise=True)
            require([(e['name'], e['triangles']) for e in loaded] ==
                    [(e['name'], len(meshes[e['name']])) for e in entries], 'page drew different geometry')
            # Bounds over every visited pose (the shadow camera and the stage cover the
            # whole travel) and the subject's centre at each solved pose (the follow
            # rig's track), exact over every vertex, computed where the vertices are.
            boxes = page.evaluate('cadexCapture.boundsOver(' +
                                  json.dumps([f['component_placements'] for f in frames]) + ')')
            require(len(boxes) == len(frames) and all(
                all(math.isfinite(v) for v in b['min'] + b['max']) for b in boxes), 'bounds failed')
            lo = [min(b['min'][j] for b in boxes) for j in range(3)]
            hi = [max(b['max'][j] for b in boxes) for j in range(3)]
            centres = [[(a+b)/2 for a, b in zip(b['min'], b['max'])] for b in boxes]
            height = boxes[0]['max'][2] - boxes[0]['min'][2]
            require(height > 0, 'subject has no height')
            track = [centres[sample(i)] for i in range(count)]
            bounds = {'min': lo, 'max': hi, 'center': [(a+b)/2 for a,b in zip(lo,hi)],
                      'radius': math.dist(lo,hi)/2 or 1}
            page.evaluate('cadexCapture.frameBounds(' + json.dumps(bounds) + '); cadexCapture.fit()')
            # The follow rig: one standoff at the declared framing, a Hann-smoothed
            # anchor, fixed orientation; the scene module computes and reports it.
            rig = page.evaluate('cadexCapture.follow(' + json.dumps(track) + ', ' +
                                json.dumps({**FRAMING, 'subject_height_mm': height}) + ')')
            cameras = rig.pop('cameras')
            require(len(cameras) == count and rig['worst_drift_ndc'] < rig['max_drift'],
                    'follow rig lost its subject')
            for i in range(count):
                require(time.monotonic()-started < RENDER_SECONDS, f'render exceeded {RENDER_SECONDS} seconds')
                frame = frames[sample(i)]
                clock = times[-1] if i == count-1 else i/FPS
                data = page.evaluate('cadexCapture.setCamera(' + json.dumps(cameras[i]) + '); cadexCapture.setPoses(' +
                                     json.dumps(frame['component_placements']) + '); cadexCapture.setClock(' +
                                     json.dumps(clock) + '); cadexCapture.png()')
                (work / f'{i:04d}.png').write_bytes(base64.b64decode(data))
            stats = page.evaluate('cadexCapture.stats()')
            style = stats['style']
            # A recording shows the tessellated solids and nothing else: the capture
            # was never handed the proxies, and it says so itself.
            require(stats['showing'] == 'tessellated solids' and not stats['proxies']['shown']
                    and stats['proxies']['listed'] == 0, 'capture drew something other than the solids')
            browser_version = browser.send('Browser.getVersion')['product']
    finally:
        server.shutdown()
        server.server_close()
    return {'style': style, 'style_sha256': style_digest(),
            'renderer': 'Three.js r160 / ' + browser_version, 'width': 512, 'height': 512,
            'projection': 'perspective 55 degrees', 'camera': cameras[0], 'bounds': bounds,
            'framing': rig,
            'sampling': '10 fps, latest solved pose plus final pose, follow camera at the declared framing; tessellation preview'}


def studio_materials(root, record, names):
    """``(looks, source)``: each component's appearance role and colour.

    Read from the render summary written at the run's own accepted revision
    (the run's recorded render, then ``review/render/<revision>/``, then
    ``review/render/``), which carries what xscript declared and what the
    inventory said was purchased (docs/XSCRIPT.md, ot10 A3). A design with
    no such summary is drawn all in the shell material, and the video says
    so rather than guessing which parts were bought. Components the summary
    names as environment get no look and are not drawn (ADR-432). Each look
    carries the finish and catalog row the summary names (ADR-603), so a
    bolt is metal and a board a PCB here as in the render.
    """
    revision = record['model']['accepted_revision']
    candidates = [(record.get('project_artifacts') or {}).get('render'),
                  f'review/render/{revision}', 'review/render']
    for relative in candidates:
        if not isinstance(relative, str):
            continue
        item = resolve_reference(root, relative + '/summary.json')
        if not item['exists'] or item['error']:
            continue
        try:
            summary = json.loads((root / item['path']).read_text())
        except (OSError, ValueError):
            continue
        appearance = summary.get('appearance')
        if summary.get('revision') != revision or not isinstance(appearance, dict):
            continue
        # World geometry the render left out (a floor) is left out here too:
        # the studio floor is the backdrop, and the shadow lands where the feet are.
        environment = sorted(set(summary.get('environment') or ()) & set(names))
        looks = {}
        for name in names:
            if name in environment:
                continue
            entry = appearance.get(name) or {}
            role, colour = entry.get('role'), str(entry.get('color', ''))
            finish, catalog = entry.get('finish', 'printed'), entry.get('catalog')
            require(role in studio_render.FINISH and re.fullmatch('#[0-9A-Fa-f]{6}', colour)
                    and finish in studio_render.FINISH_CLASSES
                    and (finish not in ('hardware', 'board') or isinstance(catalog, dict)),
                    f'render summary gives {name} no valid appearance')
            looks[name] = studio_render.Look(role, tuple(int(colour[k:k+2], 16) for k in (1, 3, 5)),
                                             finish, catalog)
        return looks, {'source': item['path'], 'declared': True, 'environment_omitted': environment}
    shell = studio_render.ROLE_COLORS['shell']
    return ({name: ('shell', shell) for name in names},
            {'source': 'no render summary with appearance at this revision: every part drawn as shell',
             'declared': False, 'environment_omitted': []})


def _rows(pose):
    x, y, z, w = pose['rotation_xyzw']
    return ((1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)),
            (2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)),
            (2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y))), pose['position_mm']


def _posed(prepared, pose):
    """Prepared triangles (corners and corner normals) moved rigidly to ``pose``."""
    ((a, b, c), (d, e, f), (g, h, i)), (px, py, pz) = _rows(pose)
    out = []
    for material, tri, normals in prepared:
        out.append((material,
                    tuple((a*x+b*y+c*z+px, d*x+e*y+f*z+py, g*x+h*y+i*z+pz) for x, y, z in tri),
                    tuple((a*x+b*y+c*z, d*x+e*y+f*z, g*x+h*y+i*z) for x, y, z in normals)))
    return out


def _hann(track, half):
    """``track`` (a list of 2-vectors) smoothed by a Hann window of ``half`` samples a side."""
    weights = [0.5 + 0.5*math.cos(math.pi*k/(half+1)) for k in range(-half, half+1)]
    out = []
    for i in range(len(track)):
        total = sx = sy = 0.0
        for k, weight in zip(range(-half, half+1), weights):
            x, y = track[min(len(track)-1, max(0, i+k))]
            sx += weight*x; sy += weight*y; total += weight
        out.append((sx/total, sy/total))
    return out


def _studio_frames(looks, materials, names, meshes, frames, times, count, sample, work, started,
                   floor=None, held=None, overlay=None):
    """The design's studio look (CadexStudio.studio) drawn on the CPU at every sampled pose.

    The hero view, followed: each component is prepared once in its own frame
    (normals smoothed below the crease angle) and moved rigidly per pose. The
    floor is the top of the design's environment geometry (a floor the render
    summary names), or without one the lowest point the robot reaches over the
    whole rollout, so a foot that lifts leaves its shadow behind; the window is fixed in size and
    its centre is a Hann-smoothed track of the robot's projected centre.
    ``looks`` is what each drawn component is made of (:func:`studio_materials`);
    a name it leaves out is environment geometry. ``floor`` names the floor's
    height outright, for a caller that measured against one. ``held`` is one
    world point per entry of ``frames`` that the window keeps inside it beside
    the solids, and ``overlay(index, pixels, size, bounds)`` draws over the
    frame rendered from ``frames[index]`` before its clock: how an
    evaluation's film marks where the episode was asked to go.
    """
    given = floor
    environment = [name for name in names if name not in looks]
    names = [name for name in names if name in looks]
    require(bool(names), 'nothing to draw once environment geometry is left out')
    size, pad, half = STUDIO['size'], STUDIO['pad'], STUDIO['smooth_frames']
    right, up, _ = studio_render.HERO
    local = {name: studio_render._prepare(
        [(studio_render.material(looks[name], meshes[name]), meshes[name])]) for name in names}
    vertices = {name: list({p for tri in meshes[name] for p in tri}) for name in names}
    # One exact pass over every sampled pose: the floor, the travel and the track.
    used = [sample(i) for i in range(count)]
    boxes, floor, lo3, hi3 = {}, math.inf, [math.inf]*3, [-math.inf]*3
    for index in sorted(set(used)):
        box = [math.inf, math.inf, -math.inf, -math.inf]
        for name in names:
            ((a, b, c), (d, e, f), (g, h, i)), (px, py, pz) = _rows(frames[index]['component_placements'][name])
            for x, y, z in vertices[name]:
                w = (a*x+b*y+c*z+px, d*x+e*y+f*z+py, g*x+h*y+i*z+pz)
                for j in range(3):
                    lo3[j], hi3[j] = min(lo3[j], w[j]), max(hi3[j], w[j])
                sx = w[0]*right[0] + w[1]*right[1] + w[2]*right[2]
                sy = w[0]*up[0] + w[1]*up[1] + w[2]*up[2]
                box = [min(box[0], sx), min(box[1], sy), max(box[2], sx), max(box[3], sy)]
        if held is not None:
            w = held[index]
            sx = w[0]*right[0] + w[1]*right[1] + w[2]*right[2]
            sy = w[0]*up[0] + w[1]*up[1] + w[2]*up[2]
            box = [min(box[0], sx), min(box[1], sy), max(box[2], sx), max(box[3], sy)]
        boxes[index] = box
    # The floor is the environment's top face where the design declares one: the
    # rollout collides on proxies (ADR-281), so a tipping solid can pass below it,
    # and a floor at the lowest reach would lift the whole walk off its shadow.
    reach_z = lo3[2]
    if given is not None:
        floor = given
    elif environment:
        floor = -math.inf
        for name in environment:
            ((a, b, c), (d, e, f), (g, h, i)), (px, py, pz) = _rows(frames[0]['component_placements'][name])
            floor = max(floor, max(g*x+h*y+i*z+pz for tri in meshes[name] for x, y, z in tri))
    else:
        floor = reach_z
    track = _hann([((boxes[k][0]+boxes[k][2])/2, (boxes[k][1]+boxes[k][3])/2) for k in used], half)
    reach = max(max(b[2]-b[0], b[3]-b[1]) for b in boxes.values()) / 2 * (1 + 2*pad)
    # Widen until every pose is inside its own window: the rig never loses the robot.
    for (cx, cy), k in zip(track, used):
        b = boxes[k]
        reach = max(reach, 1.02*max(cx-b[0], b[2]-cx, cy-b[1], b[3]-cy))
    clock_colour = studio_render.MUTED
    for i, k in enumerate(used):
        require(time.monotonic()-started < RENDER_SECONDS, f'render exceeded {RENDER_SECONDS} seconds')
        posed = [t for name in names for t in _posed(local[name], frames[k]['component_placements'][name])]
        shadow = studio_render._contact_shadow(posed, floor=floor)
        cx, cy = track[i]
        pixels, _ = studio_render.studio(posed, studio_render.HERO, bounds=([cx-reach, cy-reach], [cx+reach, cy+reach]),
                                         size=size, shadow=shadow)
        canvas = studio_render.Canvas(size, size, (0, 0, 0))
        canvas.pixels = pixels
        if overlay is not None:
            overlay(k, canvas.pixels, size, ([cx-reach, cy-reach], [cx+reach, cy+reach]))
        clock = times[-1] if i == count-1 else i/FPS
        canvas.text(14, size-28, f'{clock:4.1f} s', 2, clock_colour)
        (work / f'{i:04d}.png').write_bytes(studio_render.png(bytes(canvas.pixels), size))
    return {'style': 'studio', 'style_sha256': studio_digest(),
            'renderer': 'CadexStudio studio (engine), CPU, no browser or display',
            'width': size, 'height': size, 'materials': materials,
            'appearance': {name: {'role': looks[name][0], 'color': '#%02X%02X%02X' % tuple(looks[name][1]),
                                  'finish': getattr(looks[name], 'finish', 'printed')}
                           for name in names},
            'projection': 'orthographic hero view (35 degrees round from the front, 20 above the floor)',
            'camera': {'basis': [list(v) for v in studio_render.HERO]},
            'bounds': {'min': lo3, 'max': hi3, 'center': [(a+b)/2 for a, b in zip(lo3, hi3)],
                       'radius': math.dist(lo3, hi3)/2 or 1},
            'floor_z_mm': floor, 'lowest_reach_z_mm': reach_z,
            'floor_source': ('given by the caller' if given is not None else
                             'top of the environment geometry: ' + ', '.join(environment)
                             if environment else 'lowest point the drawn solids reach'),
            'framing': {'kind': 'follow', 'half_extent_mm': reach, **STUDIO},
            'sampling': '10 fps, latest solved pose plus final pose, follow window at the declared framing; tessellation preview'}


def studio_digest():
    """Identity of the code that determines a studio video's pixels."""
    h = hashlib.sha256()
    for path in (Path(studio_render.__file__), Path(studio_render.FONT_FILE), Path(__file__)):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def style_digest():
    """Identity of all shipped code that determines pixels, including the library."""
    h = hashlib.sha256()
    for name in ('review_scene.js', 'environment.js', 'floor.js', 'three.module.js', 'stl.js'):
        h.update(name.encode())
        h.update((STATIC_DIR / name).read_bytes())
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--style', choices=STYLES, default='studio',
                        help='studio: the design look on the CPU (default); scene: the review viewport in headless Chromium')
    args = parser.parse_args()
    try:
        print(json.dumps(render(args.project, args.run, args.style), sort_keys=True))
    except Exception as exc:
        parser.exit(1, f'video: {exc}\n')


if __name__ == '__main__':
    main()
