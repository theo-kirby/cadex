"""Finch's per-solid inventory and measured fit check (ADR-334, charter D5).

Usage: pixi run python docs/probes/ot6/finch/fit_check.py PROJECT OUT

Reads the accepted attempt's published measurements -- the pairwise clearance
the engine computed on the exact BREP at the solved pose (ADR-237), the mass
of every body from the mjcf export, the catalog identity of every output --
and the four cheek-plane sections cut by `cadex section`. Writes the
project's docs/INVENTORY.md and docs/FIT.md and the compact receipt OUT/fit.json.
Exit 1 when any fit rule fails. Nothing here rebuilds or re-accepts anything.
"""
import hashlib, json, math, sys
from pathlib import Path

project, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
accepted = json.loads((project / 'script.json').read_text())['accepted_attempt']
rev = accepted['revision']
result = json.loads((project / accepted['staging'] / 'result.json').read_text())
outs = {o['name']: o for o in result['outputs']}
params = {k: v for k, v in json.loads((project / 'script.json').read_text()).get('params', {}).items()}
model = outs['finch_model']['assembly_data']
dyn = model['dynamics']
mass = {i['component_output']: i['mass_kg'] for i in dyn['inertials']}
collisions = {c['component_output']: c['shapes'] for c in dyn['collisions']}
pairs = {}
for c in outs['finch']['clearance']:
    pairs[(c['first'], c['second'])] = pairs[(c['second'], c['first'])] = c
script = (project / 'script.py').read_text()
def pval(name):
    for line in script.splitlines():
        if line.strip().startswith(name + '=num('):
            return float(line.split('num(')[1].split(',')[0])
    raise KeyError(name)
P = {k: pval(k) for k in ('window_clear', 'horn_clear', 'stub_clear', 'side_gap', 'cheek_t', 'hip_y')}
ENGAGE, TAB_SCREW, TAB_T = 2.5, 6.0, 2.4
CENTRE_VOL = math.pi * 1.0 ** 2 * ENGAGE                      # M2 shank in the (solid) spline
TAB_VOL = math.pi * (1.0 ** 2 - 0.8 ** 2) * (TAB_SCREW - TAB_T)  # M2 shank past its 1.6 mm tap drill

PURPOSE = {
    'pelvis': 'printed pelvis: top plate, open electronics bay, two hip clevises (outboard cheek with servo window, inboard wall with bearing bore)',
    'thigh_l': 'printed thigh: hip block (horn slot, bearing stub) and two knee cheeks', 'thigh_r': 'printed thigh, mirrored',
    'shin_l': 'printed shin: knee block, beam and integral 70x34 sole', 'shin_r': 'printed shin, mirrored',
}
RELATION = {
    'pelvis': 'central box (walls and bay as one), top plate, two outboard cheeks; bay and windows not subtracted',
    'thigh': 'hip block, two knee cheeks; slot, stub and windows not modelled', 'shin': 'knee block, beam, sole (friction 1.0)',
    'servo': 'case envelope only; tabs, spline and horn not in contact',
}
rows, checks = [], []
def check(name, measured, expect, tol=1e-3, unit='mm'):
    ok = abs(measured - expect) <= tol
    checks.append({'check': name, 'measured': round(measured, 5), 'expected': expect, 'ok': ok, 'unit': unit})
    return ok
def pair(a, b):
    c = pairs[(a + '_link', b + '_link')]
    assert not c.get('error'), (a, b, c)
    return c['distance_mm'], c['common_volume_mm3']

for name, o in outs.items():
    if o['type'] != 'solid':
        continue
    link = name + '_link'
    cat = o.get('catalog')
    source = f"catalog {cat['family']} `{cat['part_number']}`" if cat else 'modelled: ' + PURPOSE[name]
    shapes = collisions.get(link, [])
    kinds = ', '.join(f"{len(shapes)} {shapes[0]['kind']}" for _ in [0]) if shapes else 'none (mass only)'
    relation = RELATION[name.split('_')[0]] if shapes else '—'
    rows.append({'component': link, 'solid': name, 'source': source, 'catalog': cat, 'mass_g': round(1000 * mass[link], 3),
                 'volume_mm3': round(o['facts']['volume_mm3'], 3), 'proxies': kinds, 'relation': relation})
assert not any(r['source'].startswith('modelled') and r['solid'] not in PURPOSE for r in rows)

for j in ('hip_l', 'hip_r', 'knee_l', 'knee_r'):
    parent = 'pelvis' if j.startswith('hip') else 'thigh_' + j[-1]
    child = ('thigh_' if j.startswith('hip') else 'shin_') + j[-1]
    sv, hn, br, cs = 'servo_' + j, 'horn_' + j, 'bearing_' + j, 'centrescrew_' + j
    d, v = pair(parent, sv); check(j + ' servo seated in the cheek window: distance', d, 0.0); check(j + ' servo/cheek common volume', v, 0.0, unit='mm3')
    d, v = pair(child, hn); check(j + ' horn nested in the block slot: distance', d, 0.0); check(j + ' horn/block common volume', v, 0.0, unit='mm3')
    d, v = pair(sv, hn); check(j + ' horn on the spline top: distance', d, 0.0); check(j + ' horn/servo common volume', v, 0.0, unit='mm3')
    d, v = pair(parent, br); check(j + ' bearing pressed in the cheek: distance', d, 0.0); check(j + ' bearing/cheek common volume', v, 0.0, unit='mm3')
    d, v = pair(child, br); check(j + ' stub in the bearing bore: radial clearance', d, P['stub_clear'], 1e-4); check(j + ' stub/bearing common volume', v, 0.0, unit='mm3')
    d, v = pair(sv, cs); check(j + ' centre screw engagement in the spline', v, CENTRE_VOL, 1e-3, 'mm3')
    d, v = pair(child, cs); check(j + ' centre screw/block common volume (clearance hole)', v, 0.0, unit='mm3')
    d, v = pair(hn, cs); check(j + ' centre screw clear of the horn hub bore', d, 2.45 - 1.0, 1e-3)
    for i in (0, 1):
        d, v = pair(parent, f'tabscrew_{j}_{i}'); check(f'{j} tab screw {i} engagement in the cheek', v, TAB_VOL, 1e-3, 'mm3')
        d, v = pair(sv, f'tabscrew_{j}_{i}'); check(f'{j} tab screw {i}/servo tab common volume', v, 0.0, unit='mm3')
    d, v = pair(parent, child); check(j + ' block to inboard cheek gap', d, P['side_gap'], 1e-3)
    d, v = pair(sv, child); check(j + ' spline to block hub recess (radial)', d, 3.45 + P['horn_clear'] - 2.45, 1e-3)

# The window clearance, from the section through each outboard cheek's mid-plane (tessellation, planar faces).
def seg(p, a, b):
    (ax, ay), (bx, by), (px, py) = a, b, p
    dx, dy = bx - ax, by - ay; l2 = dx * dx + dy * dy
    t = 0 if l2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)
def loops_distance(A, B):
    return min(seg(p, lb[i], lb[(i + 1) % len(lb)]) for la in A for lb in B for p in la for i in range(len(lb)))
sections = {}
for j in ('hip_l', 'hip_r', 'knee_l', 'knee_r'):
    s = 1.0 if j.endswith('l') else -1.0
    parent = 'pelvis' if j.startswith('hip') else 'thigh_' + j[-1]
    cheek_mid = (P['hip_y'] + 26.75 if j.startswith('hip') else P['hip_y'] + 15.25) - P['cheek_t'] / 2.0 + 0.137
    offset = s * cheek_mid
    summary = json.loads((project / 'review' / 'section' / rev / f'XZ-{offset:.17g}' / 'summary.json').read_text())
    assert summary['status'] == 'ok' and summary['revision'] == rev
    objs = summary['objects']
    gap = loops_distance(objs['servo_%s_link' % j]['contours_mm'], objs[parent + '_link']['contours_mm'])
    check(j + ' window clearance around the case (section)', gap, P['window_clear'], 0.01)
    sections[j] = {'plane': 'XZ', 'offset_mm': offset, 'objects_cut': summary['objects_cut'], 'gap_mm': round(gap, 4)}

others = [c for c in outs['finch']['clearance'] if c['common_volume_mm3'] > 1e-6
          and not (c['first'].startswith(('tabscrew', 'centrescrew')) or c['second'].startswith(('tabscrew', 'centrescrew')))]
checks.append({'check': 'no intersection other than the 12 declared thread engagements', 'measured': len(others), 'expected': 0, 'ok': not others, 'unit': 'pairs'})
checks.append({'check': 'no unmeasured pair', 'measured': sum(1 for c in outs['finch']['clearance'] if c.get('error')), 'expected': 0,
               'ok': not any(c.get('error') for c in outs['finch']['clearance']), 'unit': 'pairs'})
world = [c for c in dyn['collisions'] for s in c['shapes'] if s['kind'] not in ('box',)]
checks.append({'check': 'no plane, floor or world geometry in the design', 'measured': len(world), 'expected': 0, 'ok': not world, 'unit': 'geoms'})
checks.append({'check': 'no initial contact between proxies', 'measured': dyn['initial_contact_count'], 'expected': 0, 'ok': dyn['initial_contact_count'] == 0, 'unit': 'contacts'})
checks.append({'check': 'solver residual: solved', 'measured': outs['diagnostics']['diagnostics']['solver_code'], 'expected': 0,
               'ok': outs['diagnostics']['diagnostics']['status'] == 'solved', 'unit': 'code'})
ok = all(c['ok'] for c in checks)

printed = sum(r['mass_g'] for r in rows if not r['catalog']); purchased = sum(r['mass_g'] for r in rows if r['catalog'])
counts = {}
for r in rows:
    if r['catalog']:
        k = f"{r['catalog']['family']}/{r['catalog']['part_number']}"; counts[k] = counts.get(k, 0) + 1
inv = ['# Finch — per-solid inventory', '', f'Accepted revision `{rev}`; generated by `docs/probes/ot6/finch/fit_check.py` from the accepted attempt (ADR-334). '
       'Masses are the mjcf export\'s, computed from the exact solids at the declared densities (PLA 1240, steel 7850, nylon 1150, the MG90S at its datasheet 13.4 g). '
       'Collision proxies are the boxes each body declares for MuJoCo; "relation" says how they stand to the solid.', '',
       '| component | solid | source | mass (g) | volume (mm³) | proxies | relation to the solid |', '|---|---|---|---|---|---|---|']
inv += [f"| `{r['component']}` | `{r['solid']}` | {r['source']} | {r['mass_g']:.2f} | {r['volume_mm3']:.1f} | {r['proxies']} | {r['relation']} |" for r in rows]
inv += ['', '## Roll-up', '', f'- {len(rows)} solids: {sum(1 for r in rows if not r["catalog"])} modelled printable parts, {sum(1 for r in rows if r["catalog"])} catalog parts.']
inv += [f'- `{k}` × {n}' for k, n in sorted(counts.items())]
inv += [f'- mass: printed {printed:.1f} g, purchased {purchased:.1f} g, total {printed + purchased:.1f} g.',
        '- no floor, wall or stage: every collision geom is a box on a part of the design; the pelvis is grounded for the solver only (see DECISIONS.md).', '']
(project / 'docs' / 'INVENTORY.md').write_text('\n'.join(inv))
fit = ['# Finch — fit check', '', f'Accepted revision `{rev}`. Every row is a published measurement: pair distance and common volume on the exact BREP at the solved pose '
       '(`cadex clearance`, ADR-237), or the gap between contours in a `cadex section` cut through the cheek mid-plane. Expected values are the script\'s declared clearances '
       'and the analytic thread-engagement volumes (M2 shank in the spline, M2 shank past a 1.6 mm tap drill). Not a swept check.', '',
       '| check | measured | expected | unit | verdict |', '|---|---|---|---|---|']
fit += [f"| {c['check']} | {c['measured']} | {c['expected']} | {c['unit']} | {'ok' if c['ok'] else '**FAIL**'} |" for c in checks]
fit += ['', f"**Verdict: {'every rule holds' if ok else 'FAILED'}** ({sum(c['ok'] for c in checks)} of {len(checks)} checks).", '']
(project / 'docs' / 'FIT.md').write_text('\n'.join(fit))
receipt = {'project': project.name, 'revision': rev, 'script_sha256': hashlib.sha256(script.encode()).hexdigest(), 'script_bytes': len(script),
           'params': P, 'mass_g': {'printed': round(printed, 2), 'purchased': round(purchased, 2), 'total': round(printed + purchased, 2)},
           'catalog_counts': counts, 'components': len(rows), 'geoms': model['mjcf']['geom_count'], 'checks': checks, 'sections': sections, 'ok': ok}
(out / 'fit.json').write_text(json.dumps(receipt, indent=1) + '\n')
print(json.dumps({'ok': ok, 'checks': len(checks), 'failed': [c['check'] for c in checks if not c['ok']], 'mass_g': receipt['mass_g'], 'sections': sections}, indent=1))
sys.exit(0 if ok else 1)
