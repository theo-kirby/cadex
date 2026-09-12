"""Fault-inject a stopped copy's video; restore every original byte in finally.

PYTHONPATH=cli:cli/tests pixi run python docs/probes/reed-copy/video_recovery.py COPY
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from cadex_cli.review_server import serve
from cdp_browser import HeadlessBrowser, find_browser

root = Path(sys.argv[1]).resolve()
run = root / 'runs/copy100'
status = json.loads((run / 'video.json').read_text())
video = run / status['videos'][0]['path']
original = video.read_bytes()
backup = video.with_suffix('.recovery-backup')
assert not backup.exists()
protected = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
             for folder in ('runs', 'assets', 'script_history')
             for p in (root / folder).rglob('*') if p.is_file()}
protected['script.json'] = hashlib.sha256((root / 'script.json').read_bytes()).hexdigest()
server, _ = serve(root, subprocess.check_output(['tailscale', 'ip', '-4'], text=True).strip(), 0)
result = {'same_machine_private_address': True, 'states': []}
try:
    with HeadlessBrowser(find_browser()) as browser:
        page = browser.page(server.url)
        page.evaluate('window.cadexReview.ready', await_promise=True)
        page.click("#views li[data-run='copy100']")
        page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
        video.rename(backup)
        page.wait_for("document.querySelector('#videos [data-video]').textContent.includes('missing')")
        assert page.evaluate("fetch('/video/run/copy100/0').then(r=>r.status)", await_promise=True) == 404
        result['states'].append('missing refused')
        video.write_bytes(original[:64])
        page.wait_for("document.querySelector('#videos [data-video]').textContent.includes('digest mismatch')")
        assert not page.evaluate("!!document.querySelector('#videos video')")
        assert page.evaluate("fetch('/video/run/copy100/0').then(r=>r.status)", await_promise=True) == 404
        assert 'Retry the CLI video command' in page.text('#videos')
        result['states'].append('partial refused')
        # A restored artifact must recover in the same page without navigation.
        backup.replace(video)
        page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
        page.evaluate("document.querySelector('#videos video').muted=true; document.querySelector('#videos video').play()", await_promise=True)
        page.wait_for("document.querySelector('#videos video').currentTime > 0.1")
        download = page.download('#videos a')
        assert hashlib.sha256(download.path.read_bytes()).hexdigest() == status['videos'][0]['sha256']
        result['states'].append('restored plays and downloads')
        page.click("#views li[data-run='foot90']")
        page.wait_for("document.querySelector('#videos video')?.readyState >= 2")
        result['prior_completed_video_available'] = True
finally:
    if backup.exists():
        backup.replace(video)
    server.shutdown()
    server.server_close()
    assert video.read_bytes() == original
    assert all(hashlib.sha256((root / p).read_bytes()).hexdigest() == sha
               for p, sha in protected.items())
result['protected_files_unchanged'] = len(protected)
result['video_sha256'] = hashlib.sha256(original).hexdigest()
(root / 'evidence/video-recovery30.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
