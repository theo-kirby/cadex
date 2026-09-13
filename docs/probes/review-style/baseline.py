"""Read-only visual baseline; bulk images go in the selected project's evidence.

PYTHONPATH=cli:cli/tests pixi run python docs/probes/review-style/baseline.py URL PROJECT REFERENCE
"""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from cdp_browser import HeadlessBrowser, find_browser
from cadex_cli.review_record import read_run_record

url, project, reference = sys.argv[1:]
root, ref = Path(project), Path(reference)
out = root / 'evidence' / 'style39'
out.mkdir(parents=True, exist_ok=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def decode(source, target):
    subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', str(source),
                    '-frames:v', '1', str(out / target)], check=True, timeout=30)

sources = ['web/studio/environment.js', 'web/studio/scene.js', 'web/studio/geometry.js',
           'web/capture/capture.js', 'web/capture/index.html', 'render-examples/README.md',
           'render-examples/manifest.json', 'LICENSE']
evidence = {'schema': 'cadex-style-baseline-v1', 'reference_commit': subprocess.check_output(
    ['git', '-C', str(ref), 'rev-parse', 'HEAD'], text=True).strip(),
    'reference_sources': {p: sha(ref / p) for p in sources}, 'reference_frames': {},
    'project': root.name, 'screenshots': {}, 'same_pose_camera_comparison': False}
for maneuver in ('flip', 'swing', 'orbit'):
    rel = f'render-examples/{maneuver}_maneuver_policy.mp4'
    target = f'reference-{maneuver}-frame0.png'
    decode(ref / rel, target)
    evidence['reference_frames'][rel] = {'video_sha256': sha(ref / rel),
        'frame_index': 0, 'image': target, 'image_sha256': sha(out / target)}
record = read_run_record(root / 'runs' / 'copy100', root)
video = root / 'runs' / 'copy100' / record['videos'][0]['path']
decode(video, 'cadex-video-frame0.png')
evidence['video'] = {'run': 'copy100', 'sha256': sha(video), 'frame_index': 0,
                     'image_sha256': sha(out / 'cadex-video-frame0.png')}
with HeadlessBrowser(find_browser()) as browser:
    page = browser.page(url)
    page.evaluate('window.cadexReview.ready', await_promise=True)
    assert page.text('#project-name') == root.name + ' — review'
    assert page.text('#view-kind') == 'RUN copy100'
    assert page.text('#view-revision') == record['model']['accepted_revision']
    page.wait_for("document.getElementById('model-status').dataset.state === 'loaded'")
    page.scroll_into_view('#viewer')
    def capture(label):
        page.evaluate('new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))', await_promise=True)
        rect = page.rect('#viewer')
        clip = dict(rect, scale=1)
        clip['y'] += page.evaluate('window.scrollY')
        data = page.send('Page.captureScreenshot', {'format': 'png', 'clip': clip})['data']
        path = out / (label + '.png')
        path.write_bytes(base64.b64decode(data))
        evidence['screenshots'][label] = {'sha256': sha(path),
            'camera': page.evaluate('cadexReview.viewer().camera()'),
            'stats': page.evaluate('cadexReview.viewer().stats()')}
    capture('cadex-fit')
    r = page.rect('#viewer'); x, y = r['x'] + r['width']/2, r['y'] + r['height']/2
    initial = page.evaluate('cadexReview.viewer().camera()')
    page.wheel(x, y, -300)
    page.wait_for(f'cadexReview.viewer().camera().distance < {initial["distance"]}')
    capture('cadex-close')
    page.drag(x, y, x+100, y+20)
    page.wait_for(f'cadexReview.viewer().camera().yaw !== {initial["yaw"]}')
    capture('cadex-close-orbit')
    page.wheel(x, y, 900)
    page.wait_for(f'cadexReview.viewer().camera().distance > {initial["distance"]}')
    capture('cadex-wide-orbit')
    evidence['current'] = page.evaluate('cadexReview.state()')
evidence['images'] = {p.name: sha(p) for p in sorted(out.glob('*.png'))}
(out / 'baseline.json').write_text(json.dumps(evidence, indent=2) + '\n')
print(json.dumps(evidence, indent=2))
