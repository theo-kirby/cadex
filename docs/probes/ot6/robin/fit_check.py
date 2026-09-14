"""Read Robin's retained accepted measurements; write project inventory and fit report.

Usage: python3 docs/probes/ot6/robin/fit_check.py PROJECT OUT
No rebuild or re-acceptance. Checks the solved pose, not swept motion or fabrication.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

project, out = map(Path, sys.argv[1:])
a = json.loads((project / 'script.json').read_text())['accepted_attempt']
stage = project / a['staging']
r = json.loads((stage / 'result.json').read_text())
o = {v['name']: v for v in r['outputs']}
d = o['robin_model']['assembly_data']['dynamics']
t = json.loads((stage / o['balance_task']['artifact_path']).read_text())
masses = {v['component_output']: v['mass_kg'] * 1000 for v in d['inertials']}
proxies = {v['component_output']: v['shapes'] for v in d['collisions']}
pairs = {frozenset((v['first'], v['second'])): v for v in o['robin_asm']['clearance']}
purposes = {'chassis': 'printed motor pockets, insert seats, battery bay and board bosses',
            'wheel_l': 'printed D-bore hub, web and rim', 'wheel_r': 'printed D-bore hub, web and rim',
            'clamp_l': 'printed recessed motor clamp bar', 'clamp_r': 'printed recessed motor clamp bar'}
relations = {'chassis': 'block and tower envelopes fill the pockets/bay; bosses omitted',
             'wheel': 'radius-30 sphere represents tread contact; extends beyond the 8 mm tread width',
             'motor': 'case envelope box; shaft and boss omitted',
             'clamp': 'bar envelope box; screw holes filled',
             'board': 'PCB and component envelope box'}
rows = []
for n, v in o.items():
    if v['type'] != 'solid':
        continue
    cat = v.get('catalog')
    source = f"catalog {cat['family']}/{cat['part_number']}" if cat else 'modelled: ' + purposes[n]
    shapes = proxies.get('comp_' + n, [])
    rows.append({'solid': n, 'source': source, 'mass_g': round(masses['comp_' + n], 5),
                 'volume_mm3': round(v['facts']['volume_mm3'], 5),
                 'proxies': ', '.join(s['kind'] for s in shapes) or 'none (mass only)',
                 'relation': relations.get(n, relations.get(n.split('_')[0], 'mass only')),
                 'valid_single_solid': v['facts']['valid'] and v['facts']['solids'] == 1})
checks = []
def check(name, value, expected, tolerance=1e-5):
    checks.append({'check': name, 'measured': round(value, 6), 'expected': round(expected, 6),
                   'ok': abs(value - expected) <= tolerance})
def pair(a, b, gap):
    v = pairs[frozenset(('comp_' + a, 'comp_' + b))]
    assert not v.get('error'), v
    check(a + '/' + b + ' distance mm', v['distance_mm'], gap)
    check(a + '/' + b + ' overlap mm3', v['common_volume_mm3'], 0)
for side in ('l', 'r'):
    pair('chassis', 'motor_' + side, .3)
    pair('wheel_' + side, 'motor_' + side, .05)
    pair('motor_' + side, 'clamp_' + side, 0)
    pair('chassis', 'clamp_' + side, 0)
pair('chassis', 'board', 0)
engagements = set()
for n in o:
    if not n.startswith('insert_'):
        continue
    screw = n.replace('insert_', 'screw_', 1)
    pair('chassis', n, 0)
    mounting = 'board' if n.startswith('insert_board') else 'clamp_' + n.split('_')[2]
    pair(mounting, screw, 0)
    pair(mounting, n, 0)
    v = pairs[frozenset(('comp_' + n, 'comp_' + screw))]
    # Catalog insert models its tap bore at radius .8; M2 shank radius 1.
    # The socket recess removes some shank volume: compare actual engagement
    # against a conservative 3 mm annular-thread minimum, not the author's
    # incorrect solid-cylinder pi*r^2*4 claim.
    checks.append({'check': n + ' thread engagement >= 3 mm annular equivalent',
                   'measured_mm3': round(v['common_volume_mm3'], 6),
                   'minimum_mm3': round(math.pi * (1 - .8**2) * 3, 6),
                   'ok': v['common_volume_mm3'] >= math.pi * (1 - .8**2) * 3})
    engagement = frozenset(('comp_' + n, 'comp_' + screw))
    engagements.add(engagement)
check('unexpected intersections', sum(v['common_volume_mm3'] > 1e-6 for k, v in pairs.items() if k not in engagements), 0)
check('unmeasured pairs', sum(bool(v.get('error')) for v in pairs.values()), 0)
check('invalid or multi-solid outputs', sum(not v['valid_single_solid'] for v in rows), 0)
check('grounded components', len(d['grounded_components']), 0)
check('solver code', o['robin_solve']['diagnostics']['solver_code'], 0)
check('additional reset penetration mm', -t['reset_variation'][0]['clearance_mm'], 0)
check('minimum reset lift mm', t['reset_variation'][0]['height_low_m'] * 1000, 3)
check('maximum reset lift mm', t['reset_variation'][0]['height_high_m'] * 1000, 5)
check('initial contacts outside the wheel/environment pairs', sum(set(c['component_outputs']) not in
      [{'world', 'comp_wheel_l'}, {'world', 'comp_wheel_r'}] for c in d['initial_contacts']), 0)
check('initial wheel/environment contacts', len(d['initial_contacts']), 2)
assert len(rows) == 24 and len(engagements) == 8
receipt = {'project': project.name, 'revision': a['revision'], 'script_sha256': hashlib.sha256((project/'script.py').read_bytes()).hexdigest(),
           'result_sha256': hashlib.sha256((stage/'result.json').read_bytes()).hexdigest(),
           'inventory': rows, 'mass_g': round(sum(masses.values()), 5), 'checks': checks,
           'ok': all(c['ok'] for c in checks), 'pair_count': len(pairs),
           'scope': 'retained exact BREP at accepted solved pose; no restore or swept-fit certification'}
(project / 'docs').mkdir(exist_ok=True)
inv = ['# Robin — per-solid inventory', '', 'Verified against source: 2026-09-14. [Cadex-new]', '',
       f"Accepted revision `{a['revision']}`. Mass from exact-solid MJCF inertials. PLA 1240 kg/m³; catalog densities for hardware; motor density calibrated to 9.5 g each.", '',
       '| solid | source/purpose | mass g | proxy | relation |', '|---|---|---|---|---|']
inv += [f"| {v['solid']} | {v['source']} | {v['mass_g']:.3f} | {v['proxies']} | {v['relation']} |" for v in rows]
inv += ['', f"Total {receipt['mass_g']:.3f} g. Five printed solids, nineteen catalog solids. No world geometry.",
        'Battery bay nominal usable dimensions: 39×68×21 mm, open at +X, for a 38×66×20 mm pack (~100 g). Pack mass is excluded. Bay dimensions are source-derived, not an independent section measurement.',
        'The motor includes its internal shaft support; no separate bearing or horn is used in this gearmotor design.', '']
(project/'docs/INVENTORY.md').write_text('\n'.join(inv))
fit = ['# Robin — measured fits', '', 'Verified against source: 2026-09-14. [Cadex-new]', '',
       f"Revision `{a['revision']}`. Retained exact BREP, initial solved pose only. {len(pairs)} measured component pairs.", '',
       '| check | result |', '|---|---|']
fit += [f"| {c['check']} | {json.dumps({k:v for k,v in c.items() if k != 'check'})} |" for c in checks]
fit += ['', 'The motor shoulder has the declared 0.3 mm clearance, not face contact. Clamp bars touch the motors. The D-bore has 0.05 mm radial skin clearance; this establishes a clearance fit, not a tested press fit or axial retention. Source-derived hub engagement is 8 mm and boss gap 1 mm.',
        'The author’s stdout claims 12.566 mm³ solid-cylinder screw engagement. Actual screw/insert common volume is 4.852224 mm³; the catalog insert has a bore, so the stdout claim is not a measurement.',
        'A subsequent cadex section command refused restore with a digest mismatch. No acceptance check was bypassed. These retained measurements do not certify that reopen works; repair that before training.', '']
(project/'docs/FIT.md').write_text('\n'.join(fit))
out.mkdir(parents=True, exist_ok=True)
(out/'fit.json').write_text(json.dumps(receipt, indent=1)+'\n')
print(json.dumps({'ok':receipt['ok'],'checks':len(checks),'mass_g':receipt['mass_g'],'failed':[c for c in checks if not c['ok']]}))
sys.exit(0 if receipt['ok'] else 1)
