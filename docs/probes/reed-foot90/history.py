"""Compare actual Reed baseline and revised models/specs/videos in Chromium."""
import hashlib
import base64
import json
import re
from pathlib import Path
import subprocess
import struct
import sys
from cadex_cli.review_server import serve
from cdp_browser import HeadlessBrowser, find_browser

root = Path(sys.argv[1]).resolve()
server, _ = serve(root, subprocess.check_output(['tailscale', 'ip', '-4'], text=True).strip(), 0)
rows = {}
try:
    with HeadlessBrowser(find_browser()) as browser:
        page = browser.page(server.url)
        page.evaluate('window.cadexReview.ready', await_promise=True)
        for name, length in [('probe3-final', 70), ('foot90', 90)]:
            record = json.loads((root / 'runs' / name / 'run.json').read_text())
            video = json.loads((root / 'runs' / name / 'video.json').read_text())['videos'][0]
            page.click("#views li[data-run='%s']" % name)
            page.wait_for("document.getElementById('view-revision').textContent === " + json.dumps(record['model']['accepted_revision']))
            page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
            assert page.text('#view-digest') == record['model']['digest']
            manifest = page.evaluate("fetch('/api/model/run/" + name + "').then(r=>r.json())", await_promise=True)
            foot = next(c for c in manifest['components'] if c.get('output') == 'foot_l')
            encoded = page.evaluate("fetch(" + json.dumps(foot['mesh']) + ").then(r=>r.arrayBuffer()).then(b=>btoa(String.fromCharCode(...new Uint8Array(b))))", await_promise=True)
            mesh = base64.b64decode(encoded)
            retained_mesh = root / 'runs' / name / 'rollout/foot_l.stl'
            assert mesh == retained_mesh.read_bytes()
            count = struct.unpack_from('<I', mesh, 80)[0]
            if len(mesh) == 84 + count * 50:
                xs = [struct.unpack_from('<f', mesh, 84 + i*50 + 12 + v*12)[0]
                      for i in range(count) for v in range(3)]
            else:
                xs = [float(x) for x in re.findall(rb'\bvertex\s+([^\s]+)', mesh)]
            assert abs(max(xs) - min(xs) - length) < .001
            assert record['params']['values']['foot_len'] == length
            params = page.text('#params')
            assert 'Foot length (X)' in params and str(length) in params
            page.click("#docs li[data-doc='docs/design-specs.md'] a")
            expected_doc = (root / 'runs' / name / 'project-docs/docs/design-specs.md').read_text()
            page.wait_for("document.getElementById('doc-view').textContent.endsWith(" + json.dumps(expected_doc) + ")")
            docs = page.text('#doc-view')
            assert ('Review experiment: foot90' in docs) == (name == 'foot90')
            page.wait_for("document.getElementById('telemetry').dataset.state === 'done'")
            curves = {key: page.attribute('[data-history=' + key + ']', 'data-points')
                      for key in ('curve', 'loss_curve', 'episode_steps_curve')}
            assert set(curves.values()) == {'240'}
            if name == 'probe3-final':
                assert page.text('#view-relation').startswith('HISTORICAL')
            assert page.evaluate('window.cadexReview.viewer().nonBackgroundPixels()') > 1000
            page.scroll_into_view('#viewer')
            rect = page.rect('#viewer')
            x, y = rect['x'] + rect['width']/2, rect['y'] + rect['height']/2
            before = page.evaluate('window.cadexReview.viewer().camera()')
            page.drag(x, y, x + 90, y + 35)
            page.wait_for('window.cadexReview.viewer().camera().yaw !== ' + str(before['yaw']))
            page.wheel(x, y, -240)
            page.wait_for('window.cadexReview.viewer().camera().distance < ' + str(before['distance']))
            page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
            page.evaluate("document.querySelector('#videos video').muted=true; document.querySelector('#videos video').play()", await_promise=True)
            page.wait_for("document.querySelector('#videos video').currentTime > 0.1")
            download = page.download('#videos a')
            assert hashlib.sha256(download.path.read_bytes()).hexdigest() == video['sha256']
            rows[name] = {'revision': page.text('#view-revision'), 'digest': page.text('#view-digest'),
                          'params': params, 'docs': docs, 'relation': page.text('#view-relation'),
                          'model': page.evaluate('window.cadexReview.viewer().stats()'),
                          'curve_points': curves,
                          'foot_length_mm': max(xs) - min(xs),
                          'foot_mesh_sha256': hashlib.sha256(mesh).hexdigest(),
                          'orbit_zoom': True, 'video_played': True, 'download_sha256': video['sha256']}
        assert rows['probe3-final']['digest'] != rows['foot90']['digest']
finally:
    server.shutdown()
    server.server_close()
    (root / 'evidence/foot90-history.json').write_text(json.dumps(rows, indent=2) + '\n')
print(json.dumps({'ok': True, 'views': list(rows)}))
