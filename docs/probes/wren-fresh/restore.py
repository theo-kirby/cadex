# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Restore an accepted project twice in place and verify retained artifact bytes.

PYTHONPATH=cli pixi run python docs/probes/wren-fresh/restore.py PROJECT EVIDENCE_NAME
"""
import hashlib, json, sys
from pathlib import Path
from cadex_cli.client import CadexdClient, open_project
from cadex_cli.engine import resolve_engine
root = Path(sys.argv[1]).resolve()
state = json.loads((root / 'script.json').read_text())
staging = root / state['accepted_attempt']['staging']
def inventory():
    return {str(p.relative_to(staging)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(staging.rglob('*')) if p.is_file()}
before = inventory()
receipt = {'project': root.name, 'accepted_revision': state['accepted_revision'],
           'accepted_digest': state['accepted_digest'], 'accepted_attempt': state['accepted_attempt'],
           'retained_attempt_files': len(before), 'opens': []}
for _ in range(2):
    with CadexdClient(resolve_engine()) as client:
        pid = client._process.pid
        reply = open_project(client, root, restore=True)
    assert reply['restore']['matches_accepted'], reply
    after = json.loads((root / 'script.json').read_text())
    for key in ('accepted_revision', 'accepted_digest', 'accepted_attempt', 'accepted_contract'):
        assert state[key] == after[key], key
    assert inventory() == before
    receipt['opens'].append({'pid': pid, 'restore': reply['restore'], 'retained_bytes_unchanged': True})
out = root / 'evidence' / sys.argv[2]
out.mkdir(parents=True, exist_ok=True)
(out / 'restore.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
