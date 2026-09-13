# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""D3: the follow camera and the timer overlay, on the persistent dashboard and its video, beside the reference.

    PYTHONPATH=cli pixi run python docs/probes/ot6/look/follow.py URL PROJECT REFERENCE RUN OUT [COMMIT]

Same arguments as compare.py: URL is the operator page (an argument, never
committed); PROJECT the project it serves; REFERENCE the read-only neural-whoop
checkout; RUN the run whose newest video was recorded with the follow rig; OUT a
directory outside the repo for every image and the full receipt; COMMIT, if
given, a repo directory that receives the compact receipt and 256-colour copies
of the decisive images. The persistent server is never started or stopped and
the reference checkout is never written.
"""
import base64, bisect, hashlib, json, math, re, subprocess, sys
from pathlib import Path

from PIL import Image
from cadex_cli.browser import HeadlessBrowser, find_browser
from cadex_cli.review_record import read_run_record
from cadex_cli.review_server import run_model
from cadex_cli.video import FPS, FRAMING, placed, stl

url, project, reference, run, out, *rest = sys.argv[1:]
root, ref, out = Path(project), Path(reference), Path(out)
out.mkdir(parents=True, exist_ok=True)
directory = root / 'runs' / run
record = read_run_record(directory, root)
video = record['videos'][0]
assert 'framing' in video and video['overlay'].startswith('timer'), 'the newest video predates the follow rig'
trace = json.loads((directory / record['artifacts']['trace']).read_text())
frames = [f for f in trace['frames'] if f.get('frame_kind') == 'solver_output']
times = [f['nominal_time_s'] for f in frames]
manifest = run_model(root, record)
meshes = {e['name']: stl(directory / 'rollout' / (e['output'] + '.stl'))
          for e in manifest['components'] if e['name'] in frames[0]['component_placements']}
entries = [{'name': e['name'], 'placement': frames[0]['component_placements'][e['name']],
            'positions': [v for t in meshes[e['name']] for p in t for v in p]}
           for e in manifest['components'] if e['name'] in meshes]
# The rig's track, exactly as video.py builds it: the subject's centre at each sampled solved pose.
count = math.ceil(times[-1] * FPS) + 1
sample = lambda i: len(frames) - 1 if i == count - 1 else max(0, bisect.bisect_right(times, i / FPS) - 1)
centres, height = [], None
for frame in frames:
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for name, tris in meshes.items():
        for tri in placed(tris, frame['component_placements'][name]):
            for pt in tri:
                for j, v in enumerate(pt):
                    lo[j], hi[j] = min(lo[j], v), max(hi[j], v)
    centres.append([(a + b) / 2 for a, b in zip(lo, hi)])
    height = height if height is not None else hi[2] - lo[2]
track = [centres[sample(i)] for i in range(count)]
TAN_V = math.tan(math.radians(55 / 2))
SECONDS = [0, 4, 8]
evidence = {'project': root.name, 'run': run, 'video': {k: video[k] for k in ('path', 'sha256', 'accepted_revision', 'style', 'frames',
                                                                                'sim_seconds', 'camera', 'framing', 'overlay', 'sampling')},
            'screenshots': {}, 'stage': {}, 'model_pixels': {}, 'apparent_fraction': {}, 'codec_mean_absolute_rgb_error': {},
            'reference_commit': subprocess.check_output(['git', '-C', str(ref), 'rev-parse', 'HEAD'], text=True).strip()}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(path):
    return subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])


def luminance(name):
    im = Image.open(out / (name + '.png')).convert('RGB'); w, h = im.size
    def mean(box):
        px = list(im.crop(box).getdata()); return round(sum(sum(p) for p in px) / (3 * len(px)), 1)
    return {'all': mean((0, 0, w, h)), 'sky': mean((0, 0, 48, 48)), 'floor': mean((w - 48, h - 48, w, h))}


def decode(source, seconds, name):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(seconds), '-i', str(source), '-frames:v', '1',
                    str(out / (name + '.png'))], check=True)
    evidence['screenshots'][name] = sha(out / (name + '.png'))


def canvas(page, expression, name, stage=None):
    path = out / (name + '.png'); path.write_bytes(base64.b64decode(page.evaluate(expression)))
    evidence['screenshots'][name] = sha(path)
    if stage: evidence['stage'][name] = page.evaluate(stage)


def changed_region(a, b):
    """Bounding box (x0, y0, x1, y1) and count of the pixels that differ between two 512² frames."""
    n, x0, y0, x1, y1 = 0, 512, 512, -1, -1
    for i in range(0, len(a), 3):
        if a[i:i + 3] != b[i:i + 3]:
            p = i // 3; x, y = p % 512, p // 512
            n += 1; x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
    return {'count': n, 'box': [x0, y0, x1, y1] if n else None}


for s in SECONDS:
    decode(directory / video['path'], s, f'video-follow-{s}s')
evidence['reference_shipped'] = {}
for clip, seconds in (('orbit', 4), ('swing', 2), ('flip', 2)):
    source = ref / 'render-examples' / f'{clip}_maneuver_policy.mp4'
    decode(source, seconds, f'reference-shipped-{clip}-{seconds}s')
    evidence['reference_shipped'][clip] = {'video': f'render-examples/{clip}_maneuver_policy.mp4',
                                           'video_sha256': sha(source), 'seconds': seconds}

with HeadlessBrowser(find_browser()) as browser:
    page = browser.page(url)
    page.evaluate('cadexReview.ready', await_promise=True)
    assert page.text('#project-name') == root.name + ' — review'
    page.evaluate("cadexReview.select(%s)" % json.dumps(run), await_promise=True)
    assert page.text('#view-kind') == 'RUN ' + run
    assert page.text('#view-revision') == record['model']['accepted_revision']
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    page.evaluate("document.getElementById('viewer').style.cssText='width:512px;height:512px;border:0;padding:0'; cadexReview.viewer().draw()")
    evidence['persistent_identity'] = page.evaluate('cadexReview.state()')
    V = 'cadexReview.viewer()'
    page.evaluate(V + '.frameBounds(' + json.dumps(video['bounds']) + ')')
    # The viewport's own copy of the rig, from the same module over the same track, agrees with the
    # capture's to the number: same standoff, same first camera.
    rig = page.evaluate(V + '.follow(' + json.dumps(track) + ', ' + json.dumps({**FRAMING, 'subject_height_mm': height}) + ')')
    cameras = rig.pop('cameras')
    evidence['viewport_rig'] = rig
    evidence['rig_agrees'] = (abs(rig['standoff_mm'] - video['framing']['standoff_mm']) < 1e-6 and
                              all(abs(a - b) < 1e-6 for a, b in zip(cameras[0]['target'], video['camera']['target'])) and
                              len(cameras) == video['frames'])
    assert evidence['rig_agrees']
    evidence['cameras'] = {str(s): cameras[s * FPS] for s in SECONDS}
    for s in SECONDS:
        i = s * FPS; frame = frames[sample(i)]; clock = times[-1] if i == count - 1 else i / FPS
        page.evaluate(V + '.setCamera(' + json.dumps(cameras[i]) + '); ' + V + '.setPoses(' + json.dumps(frame['component_placements']) +
                      '); ' + V + '.setClock(' + json.dumps(clock) + ')')
        name = f'viewport-follow-{s}s'
        canvas(page, V + '.png()', name, V + '.stats().stage')
        pixels = page.evaluate(V + '.modelPixels()')
        evidence['model_pixels'][name] = pixels['count']
        box = pixels['box']
        eye = [t + d for t, d in zip(cameras[i]['target'], [cameras[i]['distance'] * math.cos(.5) * math.cos(.8),
                                                             cameras[i]['distance'] * math.cos(.5) * math.sin(.8),
                                                             cameras[i]['distance'] * math.sin(.5)])]
        evidence['apparent_fraction'][name] = {
            'declared': video['framing']['fraction'],
            'analytic': height / (2 * TAN_V * math.dist(track[i], eye)),
            'measured_pixel_box': (box[3] - box[1] + 1) / 512 if box else 0,
            'subject_height_now_mm': None}
        a, b = rgb(out / (name + '.png')), rgb(out / f'video-follow-{s}s.png')
        assert len(a) == len(b) == 512 * 512 * 3
        evidence['codec_mean_absolute_rgb_error'][str(s)] = sum(abs(x - y) for x, y in zip(a, b)) / len(a)
        assert evidence['codec_mean_absolute_rgb_error'][str(s)] < 3
    # The subject's height at each sampled pose (a fallen biped is shorter than it stood): the
    # rig frames the STANDING height, so a fall reads as a fall rather than being re-fitted away.
    for s in SECONDS:
        f = frames[sample(s * FPS)]; lo, hi = math.inf, -math.inf
        for name, tris in meshes.items():
            for tri in placed(tris, f['component_placements'][name]):
                for pt in tri:
                    lo, hi = min(lo, pt[2]), max(hi, pt[2])
        evidence['apparent_fraction'][f'viewport-follow-{s}s']['subject_height_now_mm'] = hi - lo
    # Close and wide framings of the same rig at 4 s: the stage must still outrun its fog, the model
    # must still be drawn, and the timer must still sit in its corner.
    mid = frames[sample(4 * FPS)]
    page.evaluate(V + '.setPoses(' + json.dumps(mid['component_placements']) + '); ' + V + '.setClock(4)')
    for label, fraction in (('close', .5), ('wide', .08)):
        r = page.evaluate(V + '.follow(' + json.dumps(track) + ', ' + json.dumps({**FRAMING, 'fraction': fraction, 'subject_height_mm': height}) + ')')
        page.evaluate(V + '.setCamera(' + json.dumps(r['cameras'][4 * FPS]) + ')')
        name = f'viewport-follow-{label}'
        canvas(page, V + '.png()', name, V + '.stats().stage')
        pixels = page.evaluate(V + '.modelPixels()')
        evidence['model_pixels'][name] = pixels['count']
        evidence['apparent_fraction'][name] = {'declared': fraction, 'analytic': r['size_max'],
                                               'measured_pixel_box': (pixels['box'][3] - pixels['box'][1] + 1) / 512 if pixels['box'] else 0}
        evidence['cameras'][label] = r['cameras'][4 * FPS]
    # Orbit by real pointer input from the follow camera: the environment restages, the model stays
    # drawn, and the clock is the only thing the overlay changes.
    page.evaluate(V + '.setCamera(' + json.dumps(cameras[4 * FPS]) + ')')
    page.scroll_into_view('#viewer'); rect = page.rect('#viewer')
    cx, cy = rect['x'] + rect['width'] / 2, rect['y'] + rect['height'] / 2
    before = page.evaluate(V + '.camera()')
    page.drag(cx, cy, cx - 180, cy + 30)
    dragged = page.wait_for('(function(){var c=' + V + '.camera();return c.yaw!==' + repr(before['yaw']) + '&&c.pitch!==' + repr(before['pitch']) + '&&c})()')
    assert dragged['distance'] == before['distance']
    canvas(page, V + '.png()', 'viewport-follow-orbit', V + '.stats().stage')
    evidence['model_pixels']['viewport-follow-orbit'] = page.evaluate(V + '.nonBackgroundPixels()')
    evidence['orbit'] = {'before': before, 'after_drag': dragged}
    with_clock = rgb(out / 'viewport-follow-orbit.png')
    canvas(page, V + '.setClock(null); ' + V + '.png()', 'viewport-follow-orbit-noclock')
    region = changed_region(rgb(out / 'viewport-follow-orbit-noclock.png'), with_clock)
    evidence['timer_region'] = region
    assert region['count'] > 400 and region['box'][1] > 512 * .8 and region['box'][2] < 512 * .3
    assert min(evidence['model_pixels'].values()) > 1000
    for name, stage in evidence['stage'].items():
        assert stage['roomSize'] >= 4 * stage['fog']['far'] - 1e-6, name
    page.evaluate(V + '.setCamera(' + json.dumps(cameras[4 * FPS]) + '); ' + V + '.setClock(4)')

    # The capture page at the 4 s frame: the same bytes as the viewport, clock and all.
    capture = browser.page(url + 'capture.html'); capture.wait_for('window.cadexCapture?.available')
    capture.evaluate('cadexCapture.install(' + json.dumps(entries) + ');cadexCapture.frameBounds(' + json.dumps(video['bounds']) +
                     ');cadexCapture.setCamera(' + json.dumps(cameras[4 * FPS]) + ');cadexCapture.setPoses(' +
                     json.dumps(mid['component_placements']) + ');cadexCapture.setClock(4)')
    canvas(capture, 'cadexCapture.png()', 'capture-follow-4s')
    evidence['lossless_viewport_capture_equal'] = (out / 'viewport-follow-4s.png').read_bytes() == (out / 'capture-follow-4s.png').read_bytes()
    assert evidence['lossless_viewport_capture_equal']

evidence['luminance'] = {name: luminance(name) for name in sorted(evidence['screenshots'])}
rows = [['reference-shipped-orbit-4s', 'reference-shipped-swing-2s', 'reference-shipped-flip-2s'],
        ['video-follow-0s', 'video-follow-4s', 'video-follow-8s'],
        ['viewport-follow-4s', 'viewport-follow-close', 'viewport-follow-wide'],
        ['viewport-follow-orbit', 'capture-follow-4s', 'viewport-follow-8s']]
html = '<meta charset="utf-8"><style>body{font:13px sans-serif;margin:8px;background:#fff}main{display:flex}figure{margin:6px}img{width:280px;display:block}</style>'
for columns in rows:
    html += '<main>' + ''.join('<figure><figcaption>%s</figcaption><img src="data:image/png;base64,%s"></figure>' % (
        name, base64.b64encode((out / (name + '.png')).read_bytes()).decode()) for name in columns) + '</main>'
(out / 'follow-side-by-side.html').write_text(html)
with HeadlessBrowser(find_browser(), width=910, height=1290) as browser:
    page = browser.page((out / 'follow-side-by-side.html').resolve().as_uri())
    page.send('Emulation.setDeviceMetricsOverride', {'width': 910, 'height': 1290, 'deviceScaleFactor': 1, 'mobile': False})
    page.wait_for("document.readyState === 'complete' && Array.from(document.images).every(function (i) { return i.complete && i.naturalWidth > 0; })")
    page.screenshot(out / 'follow-side-by-side.png')
evidence['images'] = {p.name: sha(p) for p in sorted(out.glob('*.png'))}
(out / 'follow.json').write_text(json.dumps(evidence, indent=1, sort_keys=True) + '\n')
if rest:
    commit = Path(rest[0]); commit.mkdir(parents=True, exist_ok=True)
    compact = {k: v for k, v in evidence.items() if k not in ('persistent_identity',)}
    compact['persistent_identity'] = {k: evidence['persistent_identity'].get(k) for k in ('selected', 'relation', 'revision', 'stale', 'error')}
    text = json.dumps(compact, indent=1, sort_keys=True) + '\n'
    assert not re.search(r'\b(?:10|100|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', text)
    (commit / 'follow.json').write_text(text)
    for name in ('follow-side-by-side', 'video-follow-0s', 'video-follow-4s', 'video-follow-8s', 'viewport-follow-4s',
                 'viewport-follow-close', 'viewport-follow-wide', 'viewport-follow-orbit'):
        im = Image.open(out / (name + '.png')).convert('RGB')
        if name == 'follow-side-by-side': im = im.resize((im.width * 2 // 3, im.height * 2 // 3), Image.LANCZOS)
        im.quantize(256).save(commit / (name + '.png'), optimize=True)
print(json.dumps({'run': run, 'framing': video['framing'], 'rig_agrees': evidence['rig_agrees'],
                  'apparent': evidence['apparent_fraction'], 'codec': evidence['codec_mean_absolute_rgb_error'],
                  'timer_region': evidence['timer_region'], 'out': str(out)}))
