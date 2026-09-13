"""Operator-URL evidence for Finch (charter D4 and D5): the accepted model on the
persistent dashboard, solids by default, proxies under the labelled toggle, and
close-ups in which the servos and horns can be recognised.

Usage: PYTHONPATH=cli pixi run python docs/probes/ot6/finch/operator_probe.py URL OUT
(URL is the private operator address and is never committed.)
"""
import base64, hashlib, json, sys, urllib.request
from pathlib import Path
from PIL import Image
from cadex_cli.browser import HeadlessBrowser, find_browser

url, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
manifest = json.load(urllib.request.urlopen(url + 'api/model/accepted', timeout=10))
collision = manifest['collision']
receipt = {'revision': manifest['revision'], 'view': manifest['view'], 'components': len(manifest['components']),
           'collision': {k: collision[k] for k in ('available', 'source', 'sha256', 'reason', 'skipped')},
           'geoms': {'total': len(collision['geoms']), 'drawn': sum(1 for g in collision['geoms'] if g['drawn']),
                     'kinds': sorted({g['type'] for g in collision['geoms']})}, 'screenshots': {}}
V = 'window.cadexReview.viewer()'


def shot(page, name, clip=None, canvas=False):
    path = out / (name + '.png')
    if canvas:
        path.write_bytes(base64.b64decode(page.evaluate(V + '.png()')))
    else:
        page.screenshot(path, clip=clip)
    im = Image.open(path).convert('RGB')
    im.quantize(256).save(path, optimize=True)      # under the 200 KB evidence cap, like the look probe
    receipt['screenshots'][name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size,
                                    'size': im.size, 'model_pixels': page.evaluate(V + '.modelPixels()')}


with HeadlessBrowser(find_browser(), width=1400, height=900) as browser:
    page = browser.page(url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    page.wait_for("document.getElementById('model-status').dataset.showing === 'solids'")
    receipt['selected'] = page.evaluate('window.cadexReview.state()')['selected']
    receipt['accepted_line'] = page.text('#accepted-line')
    receipt['status_off'] = page.text('#model-status')
    receipt['stats_off'] = {k: v for k, v in page.evaluate(V + '.stats()').items() if k in ('components', 'triangles', 'showing', 'proxies', 'style')}
    page.scroll_into_view('#model')
    shot(page, 'operator-solids', clip=page.rect('#model'))
    page.click('#show-collision')
    page.wait_for("document.getElementById('model-status').dataset.showing === 'solids+proxies'")
    receipt['status_on'] = page.text('#model-status')
    receipt['stats_on'] = {k: v for k, v in page.evaluate(V + '.stats()').items() if k in ('components', 'triangles', 'showing', 'proxies')}
    shot(page, 'operator-proxies', clip=page.rect('#model'))
    page.click('#show-collision')
    page.wait_for("document.getElementById('model-status').dataset.showing === 'solids'")
    receipt['components_listed'] = page.evaluate("Array.from(document.querySelectorAll('#model-components li')).map(n=>n.textContent)")
    # Close-ups at the left knee and the left hip, solids only: the MG90S case outboard of the cheek, the horn arm out of its slot.
    page.evaluate("document.getElementById('viewer').style.cssText='width:640px;height:480px;border:0;padding:0'; " + V + '.draw()')
    receipt['default_camera'] = page.evaluate(V + '.camera()')
    cams = {'knee-close': {'yaw': 0.9, 'pitch': 0.35, 'distance': 150.0, 'target': [0.0, 40.0, 60.0]},
            'hip-close': {'yaw': 0.9, 'pitch': 0.35, 'distance': 170.0, 'target': [0.0, 55.0, 120.0]},
            'front': {'yaw': 0.0, 'pitch': 0.15, 'distance': 420.0, 'target': [0.0, 0.0, 75.0]},
            'iso': {'yaw': 0.8, 'pitch': 0.45, 'distance': 480.0, 'target': [0.0, 0.0, 75.0]}}
    for name, cam in cams.items():
        page.evaluate(V + '.setCamera(' + json.dumps(cam) + ')')
        receipt['screenshots'].setdefault('_cameras', {})[name] = cam
        shot(page, 'operator-' + name, canvas=True)
        receipt['screenshots']['operator-' + name]['stage'] = page.evaluate(V + '.stats().stage')
(out / 'operator.json').write_text(json.dumps(receipt, indent=1) + '\n')
print(json.dumps({k: receipt[k] for k in ('selected', 'status_off', 'status_on', 'geoms')}, indent=1))
print({k: v.get('bytes') for k, v in receipt['screenshots'].items() if isinstance(v, dict) and 'bytes' in v})
