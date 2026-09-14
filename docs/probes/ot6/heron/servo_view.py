"""Orbit the persistent dashboard's viewport to Heron's servo side and keep the frame.

Usage: PYTHONPATH=cli pixi run python docs/probes/ot6/heron/servo_view.py URL OUT [RUN]
The default view (yaw 0.8, from +X +Y) looks at the bearing cheeks; the servo
cases, tab plates and horns are on the -Y side (the outboard cheeks' mid-plane
is y = -16.5). One pointer drag of +200 px rotates the yaw by -2.0 rad (the
viewport's 0.01 rad/px), to -1.2, looking from -Y with a little +X so the
forearm's reach is in front. With RUN, that run's view is selected first (a
fresh visit must already select it when it is the default). Writes
OUT/servo-view.json and OUT/servo-view-1400.png (quantised, under 200 KB).
The URL comes from argv, never from this file.
"""
import hashlib, json, sys
from pathlib import Path
from PIL import Image
from cadex_cli.browser import HeadlessBrowser, find_browser

url, out = sys.argv[1], Path(sys.argv[2]); run = sys.argv[3] if len(sys.argv) > 3 else None
out.mkdir(parents=True, exist_ok=True)
width, height = 1400, 900
with HeadlessBrowser(find_browser(), width=width, height=height) as browser:
    page = browser.page(url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    fresh = page.text('#view-kind')
    if run and fresh != 'RUN ' + run:
        page.click("#views li[data-run='%s']" % run)
        page.wait_for("document.getElementById('view-kind').textContent === 'RUN %s'" % run)
        page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    page.wait_for("document.getElementById('model-status').dataset.showing === 'solids'")
    page.scroll_into_view('#model')
    rect = page.rect('#model'); cx, cy = rect['x'] + rect['width'] / 2, rect['y'] + rect['height'] / 2
    before = page.evaluate('window.cadexReview.viewer().camera()')
    page.drag(cx - 100, cy, cx + 100, cy - 15, steps=20)
    after = page.wait_for("(function(){var c=window.cadexReview.viewer().camera(); return c.yaw < -1.0 && c})()")
    page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))', await_promise=True)
    png = out / 'servo-view-1400.png'
    page.screenshot(png, clip=page.rect('#model'))
    Image.open(png).convert('RGB').quantize(256).save(png, optimize=True)
    receipt = {'url_source': 'argv (private address, not committed)', 'width': width, 'height': height,
               'fresh_selection': fresh, 'selected': page.text('#view-kind'), 'status': page.text('#model-status'),
               'showing': page.attribute('#model-status', 'data-showing'),
               'camera_before': before, 'camera_after': after, 'drag_px': [200, -15], 'rad_per_px': 0.01,
               'looking_from': 'the -Y side (servo cases, tab plates and horns outboard of the cheeks), slightly +X',
               'png': png.name, 'png_sha256': hashlib.sha256(png.read_bytes()).hexdigest(), 'png_bytes': png.stat().st_size}
assert receipt['png_bytes'] <= 200 * 1024, receipt['png_bytes']
(out / 'servo-view.json').write_text(json.dumps(receipt, indent=1) + '\n')
print(json.dumps({k: receipt[k] for k in ('selected', 'showing', 'camera_after', 'png_bytes')}))
