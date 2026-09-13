# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Assemble a Wren revision comparison from retained project-local receipts.

Usage: pixi run python report_revision.py PROJECT BEFORE_INVENTORY RETAINED...
BEFORE_INVENTORY is the pre-revision SHA-256 inventory of runs/ and assets/;
every file in it must still match. Each RETAINED directory holds a
``compare.py`` evaluation (``evidence/comparison.json``) copied into the
project. Writes JSON to stdout; large artifacts stay project-local.
"""
import hashlib
import json
from pathlib import Path
import statistics
import sys

p = Path(sys.argv[1]).resolve()
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = read(Path(sys.argv[2]).resolve())
changed = [path for path, digest in before.items() if sha(p / path) != digest]
assert not changed, changed
runs = {}
for location in sys.argv[3:]:
    retained = Path(location).resolve()
    assert p in retained.parents, 'Retain evaluations inside the reviewed project first'
    result = read(retained / 'evidence/comparison.json')
    name = result['run']; run = p / 'runs' / name
    record = read(run / 'run.json')
    video = read(run / 'video.json')['videos'][0]
    browser = read(p / 'evidence' / (name + '-check.json'))
    assert browser['download_sha256'] == video['sha256'] == sha(run / video['path'])
    rows = result['rows']
    assert [row['seed'] for row in rows] == list(range(5))
    assert all(row['policy_sha256'] == video['policy_sha256'] for row in rows)
    assert all(row['model_sha256'] == sha(run / record['artifacts']['model_xml']) for row in rows)
    assert len({row['task_sha256'] for row in rows}) == 1
    runs[name] = dict(evaluation=result, evidence_directory=str(retained.relative_to(p)),
                      accepted_revision=record['model']['accepted_revision'],
                      accepted_digest=record['model']['digest'], params=record['params'],
                      authored_by=((record.get('training') or {}).get('requested') or {}).get('design_authored_by'),
                      video={k: video[k] for k in ('path', 'sha256', 'policy_sha256', 'model_digest', 'task_sha256', 'frames', 'fps', 'duration_seconds', 'sim_seconds', 'style', 'style_sha256', 'seed')},
                      browser={k: browser.get(k) for k in ('browser_playback', 'download_sha256', 'fresh_selection', 'historical_selection', 'returned_to_current', 'foot_len_mm', 'decoded_frames', 'simulation_seconds')},
                      summary=dict(
                          mean_displacement_x_mm=statistics.mean(r['displacement_x_mm'] for r in rows),
                          min_displacement_x_mm=min(r['displacement_x_mm'] for r in rows),
                          mean_survival_s=statistics.mean(r['survival_s'] for r in rows),
                          min_survival_s=min(r['survival_s'] for r in rows),
                          falls=sum(r['fell'] for r in rows),
                          mean_total_reward=statistics.mean(r['total_reward'] for r in rows)))
print(json.dumps(dict(schema='wren-revision-comparison-v1', project=p.name,
                      protocol=dict(seeds=list(range(5)), episode_seconds=8, control_hz=50,
                                    training_iterations=240, environments=1024, training_seed=0),
                      before_inventory_files=len(before), before_inventory_preserved=True,
                      runs=runs), indent=2))
