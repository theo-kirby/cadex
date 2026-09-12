"""Verify a stopped Reed copy after retraining; temporarily hide its source.

Run with PYTHONPATH=cli:cli/tests under pixi from the repository root.
The copy's evidence/copy29-before.json is the full pre-copy SHA-256 inventory.
Both projects must have no active writers. The source is restored on failure.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def inventory(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


parser = argparse.ArgumentParser(__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('copy', type=Path)
args = parser.parse_args()
source, copy = args.source.resolve(), args.copy.resolve()
assert source != copy and source not in copy.parents and copy not in source.parents
before = json.loads((copy / 'evidence/copy29-before.json').read_text())
assert inventory(source) == before, 'Original changed before isolation test'
retained = {p: digest for p, digest in before.items()
            if p.startswith(('runs/', 'assets/'))}
copied = inventory(copy)
assert all(copied[p] == digest for p, digest in retained.items())
hidden = source.with_name(source.name + '.copy-test-unavailable')
assert not hidden.exists()
source.rename(hidden)
try:
    assert not source.exists()
    accepted = json.loads((copy / 'script.json').read_text())
    reopened = subprocess.run(['./cadex', 'export', '--project', str(copy),
                              '--out', str(copy / 'evidence/copy100-reopen'), '--json'],
                             capture_output=True, text=True, timeout=120)
    (copy / 'evidence/copy100-reopen.json').write_text(reopened.stdout)
    (copy / 'evidence/copy100-reopen.stderr').write_text(reopened.stderr)
    assert reopened.returncode == 0, reopened.stderr
    receipt = json.loads(reopened.stdout)
    assert receipt['accepted_revision'] == accepted['accepted_revision']
    assert receipt['digest'] == accepted['accepted_digest']
    subprocess.run([sys.executable, 'docs/probes/reed-foot90/history.py', str(copy),
                    '--view', 'probe3-final:70', '--view', 'foot90:90',
                    '--view', 'copy100:100', '--output', 'copy100-history.json'],
                   check=True, timeout=180)
    subprocess.run([sys.executable, str(copy / 'evidence/check-probe3-video.py'),
                    str(copy), 'copy100'], check=True, timeout=120)
    assert not source.exists()
    assert inventory(hidden) == before, 'Original changed while unavailable'
finally:
    hidden.rename(source)
assert inventory(source) == before
after_copy = inventory(copy)
assert all(after_copy[p] == digest for p, digest in retained.items())
history = json.loads((copy / 'evidence/copy100-history.json').read_text())
result = {'schema': 'reed-copy-lifecycle-v1', 'original_files_unchanged': len(before),
          'inherited_run_asset_files_unchanged': len(retained),
          'original_unavailable_during_browser_review': True,
          'original_restored': True, 'engine_reopened_without_original': True,
          'copy_accepted_revision': receipt['accepted_revision'], 'copy_digest': receipt['digest'], 'private_address_same_machine': True,
          'views': history,
          'video_check': json.loads((copy / 'evidence/copy100-check.json').read_text())}
(copy / 'evidence/copy100-isolation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'ok': True, 'original_files': len(before), 'retained_files': len(retained)}))
