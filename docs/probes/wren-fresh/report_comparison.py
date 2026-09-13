# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Assemble the Wren comparison from retained project-local receipts.

Usage: pixi run python report_comparison.py PROJECT RETAINED_C1 RETAINED_F1 RETAINED_C2 RETAINED_F2
Writes JSON to stdout. Large artifacts and raw CLI envelopes stay project-local.
"""
import hashlib
import json
from pathlib import Path
import statistics
import sys

p = Path(sys.argv[1]).resolve()
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
old = read(p / 'evidence/revision50/runs-before.json')
assert all(sha(p / path) == digest for path, digest in old.items())
old_task = read(p / 'runs/wren1/train/wren_walk-task.json')
new_task = read(p / 'runs/wren2/train/wren_walk-task.json')
assert {k for k in old_task.keys() | new_task.keys() if old_task.get(k) != new_task.get(k)} == {'model'}
runs = {}
for location in sys.argv[2:]:
    retained = Path(location).resolve()
    assert p in retained.parents, 'Retain evaluations inside the reviewed project first'
    result = read(retained / 'evidence/comparison.json')
    name = result['run']; run = p / 'runs' / name
    record = read(run / 'run.json')
    video = read(run / 'video.json')['videos'][0]
    suffix = '-recheck' if name.startswith('wren1-') else ''
    browser = read(p / 'evidence' / (name + suffix + '-check.json'))
    assert browser['download_sha256'] == video['sha256'] == sha(run / video['path'])
    rows = result['rows']
    assert [row['seed'] for row in rows] == list(range(5))
    assert all(row['policy_sha256'] == video['policy_sha256'] for row in rows)
    assert all(row['model_sha256'] == sha(run / record['artifacts']['model_xml']) for row in rows)
    runs[name] = dict(evaluation=result, evidence_directory=str(retained.relative_to(p)), accepted_revision=record['model']['accepted_revision'],
                      accepted_digest=record['model']['digest'], params=record['params'],
                      video=video, browser=browser, summary=dict(
                          mean_displacement_x_mm=statistics.mean(r['displacement_x_mm'] for r in rows),
                          mean_survival_s=statistics.mean(r['survival_s'] for r in rows),
                          min_survival_s=min(r['survival_s'] for r in rows),
                          falls=sum(r['fell'] for r in rows)))
assert set(runs) == {'wren1-checkpoint20', 'wren1-final', 'wren2-checkpoint20', 'wren2-final'}
result = dict(schema='wren-comparative-lifecycle-v1', project=p.name,
              design_authorship='Original Wren: product agent; 85 to 105 mm foot revision: public CLI params, not product-agent authorship',
              protocol=dict(seeds=list(range(5)), episode_seconds=8, control_hz=50,
                            training_iterations=240, environments=1024, training_seed=0),
              original_run_files_preserved=len(old), task_changed_fields=['model'],
              completion_browser=read(p / 'evidence/wren2-final-completion-browser.json'), runs=runs)

def portable(v):
    if isinstance(v, dict): return {k: portable(x) for k,x in v.items() if k != 'url'}
    if isinstance(v, list): return [portable(x) for x in v]
    if isinstance(v, str): return v.replace(str(p), '<project>')
    return v

print(json.dumps(portable(result), indent=2))
