# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""D3: the dark look on the persistent dashboard, its capture and its video, beside the reference.

    PYTHONPATH=cli pixi run python docs/probes/ot6/look/compare.py URL PROJECT REFERENCE RUN OUT [COMMIT]

URL is the operator page (an argument, never committed); PROJECT the project it
serves; REFERENCE the read-only neural-whoop checkout; RUN the run whose newest
video is compared; OUT a directory outside the repo for every image and the full
receipt; COMMIT, if given, a repo directory that receives the compact receipt and
256-colour copies of the decisive images. The persistent server is never started
or stopped and the reference checkout is never written.
"""
import base64, hashlib, json, math, re, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image
from cadex_cli.browser import HeadlessBrowser, find_browser
from cadex_cli.review_record import read_run_record
from cadex_cli.review_server import run_model
from cadex_cli.video import stl

url, project, reference, run, out, *rest = sys.argv[1:]
root, ref, out = Path(project), Path(reference), Path(out)
out.mkdir(parents=True, exist_ok=True)
record = read_run_record(root / 'runs' / run, root)
video = record['videos'][0]
trace = json.loads((root / 'runs' / run / record['artifacts']['trace']).read_text())
frame = next(f for f in trace['frames'] if f.get('frame_kind') == 'solver_output')
manifest = run_model(root, record)
entries = [{'name': e['name'], 'placement': frame['component_placements'][e['name']],
            'positions': [v for t in stl(root / 'runs' / run / 'rollout' / (e['output'] + '.stl')) for p in t for v in p]}
           for e in manifest['components'] if e['name'] in frame['component_placements']]
FRAC = 0.22   # the reference's default `droneFrac`: subject height as a fraction of the frame height
FOV = 55
height_mm = video['bounds']['max'][2] - video['bounds']['min'][2]
framed = {**video['camera'], 'distance': height_mm / (2 * math.tan(math.radians(FOV / 2)) * FRAC)}
evidence = {'project': root.name, 'run': run, 'video': video, 'screenshots': {}, 'stage': {}, 'model_pixels': {},
            'reference_commit': subprocess.check_output(['git', '-C', str(ref), 'rev-parse', 'HEAD'], text=True).strip(),
            'framing': {'fraction': FRAC, 'subject_height_mm': height_mm, 'distance_mm': framed['distance']}}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def luminance(name):
    """Mean sRGB value of the whole frame and of its top-left 48 px (sky) and bottom-right 48 px (floor)."""
    im = Image.open(out / (name + '.png')).convert('RGB'); w, h = im.size
    def mean(box):
        px = list(im.crop(box).getdata()); return round(sum(sum(p) for p in px) / (3 * len(px)), 1)
    return {'all': mean((0, 0, w, h)), 'sky': mean((0, 0, 48, 48)), 'floor': mean((w - 48, h - 48, w, h))}


def canvas(page, expression, name, stage=None):
    path = out / (name + '.png'); path.write_bytes(base64.b64decode(page.evaluate(expression)))
    evidence['screenshots'][name] = sha(path)
    if stage: evidence['stage'][name] = page.evaluate(stage)


def decode(source, seconds, name):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(seconds), '-i', str(source), '-frames:v', '1',
                    str(out / (name + '.png'))], check=True)
    evidence['screenshots'][name] = sha(out / (name + '.png'))


decode(root / 'runs' / run / video['path'], 0, 'video-frame0')
decode(root / 'runs' / run / video['path'], 4, 'video-frame4s')
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
    V = 'cadexReview.viewer()'
    canvas(page, V + '.png()', 'persistent-default', V + '.stats().stage')
    page.evaluate(V + '.frameBounds(' + json.dumps(video['bounds']) + '); ' + V + '.setCamera(' + json.dumps(video['camera']) + ')')
    canvas(page, V + '.png()', 'persistent-same-pose', V + '.stats().stage')
    evidence['persistent_identity'] = page.evaluate('cadexReview.state()')
    evidence['camera'] = page.evaluate(V + '.camera()')
    evidence['stats'] = page.evaluate(V + '.stats()')
    evidence['page_tokens'] = page.evaluate("(function(){var c=getComputedStyle(document.documentElement);return {bg:c.getPropertyValue('--bg').trim(), body:getComputedStyle(document.body).backgroundColor}})()")
    shots = {'close': {**video['camera'], 'distance': video['camera']['distance'] * .7, 'pitch': .25, 'yaw': 1.8},
             'wide': {**video['camera'], 'distance': video['camera']['distance'] * 3, 'pitch': .08, 'yaw': 1.8},
             'under': {**video['camera'], 'pitch': -.5, 'yaw': 1.8},
             'framed': framed}
    for label, c in shots.items():
        page.evaluate(V + '.setCamera(' + json.dumps(c) + ')')
        canvas(page, V + '.png()', 'persistent-' + label, V + '.stats().stage')
        evidence['model_pixels'][label] = page.evaluate(V + '.nonBackgroundPixels()')
    # Orbit and zoom by real pointer input: the environment must restage under the framing a person reaches.
    page.evaluate(V + '.setCamera(' + json.dumps(video['camera']) + ')')
    page.scroll_into_view('#viewer'); rect = page.rect('#viewer')
    cx, cy = rect['x'] + rect['width'] / 2, rect['y'] + rect['height'] / 2
    before = page.evaluate(V + '.camera()')
    page.drag(cx, cy, cx - 180, cy + 30)
    dragged = page.wait_for('(function(){var c=' + V + '.camera();return c.yaw!==' + repr(before['yaw']) + '&&c.pitch!==' + repr(before['pitch']) + '&&c})()')
    assert dragged['distance'] == before['distance']
    canvas(page, V + '.png()', 'persistent-orbit-drag', V + '.stats().stage')
    page.wheel(cx, cy, -360)
    zoomed = page.wait_for('(function(){var c=' + V + '.camera();return c.distance<' + repr(dragged['distance']) + '&&c})()')
    canvas(page, V + '.png()', 'persistent-orbit-zoom', V + '.stats().stage')
    page.wheel(cx, cy, 1200)
    far = page.wait_for('(function(){var c=' + V + '.camera();return c.distance>' + repr(before['distance']) + '*2&&c})()')
    canvas(page, V + '.png()', 'persistent-orbit-far', V + '.stats().stage')
    for label, c in (('drag', dragged), ('zoom_in', zoomed), ('zoom_out', far)):
        evidence['model_pixels'][label] = page.evaluate('(' + V + '.setCamera(' + json.dumps(c) + '), ' + V + '.nonBackgroundPixels())')
    evidence['orbit'] = {'before': before, 'after_drag': dragged, 'after_zoom_in': zoomed, 'after_zoom_out': far}
    assert min(evidence['model_pixels'].values()) > 1000
    # The stage never shows its edge: the floor runs to 4x the fog's far distance at every framing reached.
    for name, stage in evidence['stage'].items():
        assert stage['roomSize'] >= 4 * stage['fog']['far'] - 1e-6, name
    page.evaluate(V + '.setCamera(' + json.dumps(video['camera']) + ')')

    # Identical capture API and explicit same pose/camera, lossless before encoding.
    capture = browser.page(url + 'capture.html'); capture.wait_for('window.cadexCapture?.available')
    capture.evaluate('cadexCapture.install(' + json.dumps(entries) + ');cadexCapture.frameBounds(' + json.dumps(video['bounds']) + ');cadexCapture.setCamera(' + json.dumps(video['camera']) + ')')
    canvas(capture, 'cadexCapture.png()', 'capture-same-pose')
    assert (out / 'persistent-same-pose.png').read_bytes() == (out / 'capture-same-pose.png').read_bytes()
    evidence['lossless_viewport_capture_equal'] = True
    evidence['capture_style'] = capture.evaluate('cadexCapture.stats().style')

    # The reference's own unmodified scene/environment modules, dark theme, drawing the same Lark
    # entries at the same cameras: no file is written into the sibling checkout.
    routes = {'/scene.js': ref / 'web/studio/scene.js', '/environment.js': ref / 'web/studio/environment.js',
              '/geometry.js': ref / 'web/studio/geometry.js',
              '/three.js': ref / '.cache/three/28f7db420fe306d9_three.module.js',
              '/OrbitControls.js': ref / '.cache/three/10917d0867f0b694_OrbitControls.js'}
    html = b'''<style>body{margin:0}#scene{width:512px;height:512px;border:0;padding:0}</style><div id="scene"></div>
    <script type="importmap">{"imports":{"three":"/three.js","three/addons/controls/OrbitControls.js":"/OrbitControls.js"}}</script>'''

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            if self.path != '/' and self.path not in routes: self.send_error(404); return
            body = html if self.path == '/' else routes[self.path].read_bytes()
            self.send_response(200); self.send_header('Content-Type', 'text/html' if self.path == '/' else 'text/javascript'); self.end_headers(); self.wfile.write(body)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        page = browser.page('http://127.0.0.1:%d/' % server.server_port)
        page.evaluate('window.entries=' + json.dumps(entries) + ';window.floorZ=' + repr(video['bounds']['min'][2] / 1000 - 0.003))
        page.evaluate('''(async()=>{
          const THREE=await import('three');
          const {createScene,setToneMapping}=await import('/scene.js');
          const {createEnvironment}=await import('/environment.js');
          const v=createScene(document.getElementById('scene'),{grid:false,preserveDrawingBuffer:true});
          v.renderer.setPixelRatio(1);v.controls.enabled=false;v.ground.visible=false;
          setToneMapping(v.renderer,.95);const env=createEnvironment(v);env.setTheme('dark');
          const palette=[0x5b9dcd,0xde8f47,0x6ab270,0xc468b4,0xdcc85a,0x7878c8,0xc86e6e,0x6ebebe];
          entries.forEach((e,i)=>{const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(e.positions.map(x=>x/1000),3));g.computeVertexNormals();
            const m=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:palette[i%8],roughness:.72,metalness:.05,side:THREE.DoubleSide}));
            m.position.fromArray(e.placement.position_mm).multiplyScalar(.001);m.quaternion.fromArray(e.placement.rotation_xyzw);m.castShadow=true;m.receiveShadow=true;v.world.add(m);});
          window.referenceView=v;window.referenceEnv=env;
          window.shoot=async(c)=>{const {configureKeyLight}=await import('/scene.js');
            const t=c.target.map(x=>x/1000),d=c.distance/1000,cp=Math.cos(c.pitch);
            v.camera.position.set(t[0]+d*cp*Math.cos(c.yaw),t[2]+d*Math.sin(c.pitch),-t[1]-d*cp*Math.sin(c.yaw));
            v.controls.target.set(t[0],t[2],-t[1]);v.camera.lookAt(v.controls.target);
            env.setStage({camDist:d});env.setSize({floorZ:floorZ});
            configureKeyLight(v,{focus:v.controls.target,extent:.35});v.resize();v.render();
            return v.renderer.domElement.toDataURL('image/png').split(',')[1];};
        })()''', await_promise=True)
        for label, c in (('', video['camera']), ('-close', shots['close']), ('-wide', shots['wide']), ('-framed', framed)):
            (out / ('reference-dark-lark' + label + '.png')).write_bytes(base64.b64decode(page.evaluate('shoot(' + json.dumps(c) + ')', await_promise=True)))
            evidence['screenshots']['reference-dark-lark' + label] = sha(out / ('reference-dark-lark' + label + '.png'))
    finally:
        server.shutdown(); server.server_close()


def rgb(path):
    return subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])


a, b = rgb(out / 'persistent-same-pose.png'), rgb(out / 'video-frame0.png')
assert len(a) == len(b) == 512 * 512 * 3
evidence['codec_mean_absolute_rgb_error'] = sum(abs(x - y) for x, y in zip(a, b)) / len(a)
assert evidence['codec_mean_absolute_rgb_error'] < 3
evidence['luminance'] = {name: luminance(name) for name in sorted(evidence['screenshots'])}
rows = [['reference-shipped-orbit-4s', 'reference-dark-lark', 'persistent-same-pose', 'video-frame0'],
        ['reference-shipped-swing-2s', 'reference-dark-lark-framed', 'persistent-framed', 'video-frame4s'],
        ['reference-shipped-flip-2s', 'reference-dark-lark-close', 'persistent-close', 'persistent-orbit-drag'],
        ['persistent-default', 'reference-dark-lark-wide', 'persistent-wide', 'persistent-orbit-far']]
html = '<meta charset="utf-8"><style>body{font:13px sans-serif;margin:8px;background:#fff}main{display:flex}figure{margin:6px}img{width:280px;display:block}</style>'
for columns in rows:
    html += '<main>' + ''.join('<figure><figcaption>%s</figcaption><img src="data:image/png;base64,%s"></figure>' % (
        name, base64.b64encode((out / (name + '.png')).read_bytes()).decode()) for name in columns) + '</main>'
(out / 'side-by-side.html').write_text(html)
with HeadlessBrowser(find_browser(), width=1200, height=1290) as browser:
    page = browser.page((out / 'side-by-side.html').resolve().as_uri())
    page.send('Emulation.setDeviceMetricsOverride', {'width': 1200, 'height': 1290, 'deviceScaleFactor': 1, 'mobile': False})
    page.wait_for("document.readyState === 'complete' && Array.from(document.images).every(function (i) { return i.complete && i.naturalWidth > 0; })")
    page.screenshot(out / 'side-by-side.png')
evidence['images'] = {p.name: sha(p) for p in sorted(out.glob('*.png'))}
(out / 'look.json').write_text(json.dumps(evidence, indent=1, sort_keys=True) + '\n')
if rest:
    commit = Path(rest[0]); commit.mkdir(parents=True, exist_ok=True)
    compact = {k: v for k, v in evidence.items() if k not in ('persistent_identity',)}
    compact['persistent_identity'] = {k: evidence['persistent_identity'].get(k) for k in ('selected', 'relation', 'revision', 'stale', 'error')}
    text = json.dumps(compact, indent=1, sort_keys=True) + '\n'
    assert not re.search(r'\b(?:10|100|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', text)
    (commit / 'look.json').write_text(text)
    for name in ('side-by-side', 'reference-shipped-orbit-4s', 'reference-dark-lark', 'persistent-same-pose', 'video-frame0',
                 'persistent-framed', 'persistent-wide', 'persistent-orbit-far'):
        im = Image.open(out / (name + '.png')).convert('RGB')
        if name == 'side-by-side': im = im.resize((im.width * 2 // 3, im.height * 2 // 3), Image.LANCZOS)
        im.quantize(256).save(commit / (name + '.png'), optimize=True)
print(json.dumps({'run': run, 'style': video['style'], 'codec_error': evidence['codec_mean_absolute_rgb_error'],
                  'framing': evidence['framing'], 'out': str(out)}))
