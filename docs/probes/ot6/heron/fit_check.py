"""Heron's per-solid inventory and measured fit check (charter D8, on D5's rules).

Usage: pixi run python docs/probes/ot6/heron/fit_check.py PROJECT OUT

Reads the accepted attempt's published measurements -- the pairwise clearance
the engine computed on the exact BREP at the solved pose (ADR-237), the mass
of every body from the mjcf export, the catalog identity of every output --
and one `cadex section` cut through the outboard cheeks' mid-plane for the
servo window clearance. Writes the project's docs/INVENTORY.md and docs/FIT.md
and the compact receipt OUT/fit.json. Exit 1 when any fit rule fails. Nothing
here rebuilds or re-accepts anything; it runs against whichever revision the
project has accepted and names it.
"""
import hashlib, json, math, re, sys
from pathlib import Path

project, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
store = json.loads((project / 'script.json').read_text())
accepted = store['accepted_attempt']
rev = accepted['revision']
result = json.loads((project / accepted['staging'] / 'result.json').read_text())
outs = {o['name']: o for o in result['outputs']}
model = outs['heron_model']['assembly_data']
dyn = model['dynamics']
mass = {i['component_output']: i['mass_kg'] for i in dyn['inertials']}
collisions = {c['component_output']: c['shapes'] for c in dyn['collisions']}
clearance = outs['heron_assembly']['clearance']
pairs = {}
for c in clearance:
    pairs[(c['first'], c['second'])] = pairs[(c['second'], c['first'])] = c
script = (project / 'script.py').read_text()
stdout = result.get('stdout') or ''
def pval(name):
    m = re.search(r'^\s*' + name + r'=num\(([-0-9.]+)', script, re.M)
    if not m:
        raise KeyError(name)
    return float(m.group(1))
P = {k: pval(k) for k in ('window_clear', 'horn_clear', 'stub_clear', 'side_gap', 'cheek_t', 'block_w',
                          'upper_len', 'fore_len', 'z_shoulder', 'target_x', 'target_z', 'tip_floor',
                          'episode_steps', 'control_hz', 'reach_tol')}
TAB_SCREW, TAB_T, TAP_R, SHANK_R = 6.0, 2.4, 0.8, 1.0
ENGAGE = 17.0 - P['block_w']                                   # centre screw reach into the spline
CENTRE_VOL = math.pi * SHANK_R ** 2 * ENGAGE                    # M2 shank in the (solid) spline
TAB_VOL = math.pi * (SHANK_R ** 2 - TAP_R ** 2) * (TAB_SCREW - TAB_T)  # shank past its 1.6 mm tap drill

PURPOSE = {
    'base': 'printed base: bench foot with four M3 clearance holes, webs, and the shoulder clevis (outboard cheek with servo window and tap-drilled tab holes, inboard cheek with bearing bore); grounded',
    'upper_arm': 'printed upper arm: shoulder child block (horn pocket, bearing stub, centre-screw counterbore), beam, and the elbow clevis',
    'forearm': 'printed forearm: elbow child block (horn pocket, bearing stub, counterbore), beam and rounded tip; its frame is the tip',
}
RELATION = {
    'base': 'foot, webs, cheek panels around the window as boxes; holes, window and bore not subtracted',
    'upper_arm': 'block, beam, bridge and cheek panels as boxes; pocket, stub and window not modelled',
    'forearm': 'block and beam as boxes, tip as a sphere; pocket and stub not modelled',
    'servo': 'case envelope box only; tabs, spline and horn not in contact',
}
rows, checks = [], []
def check(name, measured, expect, tol=1e-3, unit='mm'):
    ok = abs(measured - expect) <= tol
    checks.append({'check': name, 'measured': round(measured, 5), 'expected': round(expect, 5), 'ok': ok, 'unit': unit})
    return ok
def pair(a, b):
    c = pairs[('comp_' + a, 'comp_' + b)]
    assert not c.get('error'), (a, b, c)
    return c['distance_mm'], c['common_volume_mm3']

for name, o in outs.items():
    if o['type'] != 'solid':
        continue
    link = 'comp_' + name
    cat = o.get('catalog')
    source = f"catalog {cat['family']} `{cat['part_number']}`" if cat else 'modelled: ' + PURPOSE[name]
    shapes = collisions.get(link, [])
    kinds = ', '.join(f"{n} {k}" for k, n in sorted({s['kind']: sum(1 for t in shapes if t['kind'] == s['kind']) for s in shapes}.items())) or 'none (mass only)'
    relation = RELATION.get(name, RELATION.get(name.split('_')[0], '—')) if shapes else '—'
    rows.append({'component': link, 'solid': name, 'source': source, 'catalog': cat, 'mass_g': round(1000 * mass[link], 3),
                 'volume_mm3': round(o['facts']['volume_mm3'], 3), 'proxies': kinds, 'relation': relation,
                 'valid_single_solid': bool(o['facts']['valid'] and o['facts']['solids'] == 1)})
assert not any(r['source'].startswith('modelled') and r['solid'] not in PURPOSE for r in rows)

for j, parent, child in (('shoulder', 'base', 'upper_arm'), ('elbow', 'upper_arm', 'forearm')):
    sv, hn, br, cs = 'servo_' + j, 'horn_' + j, 'bearing_' + j, 'centrescrew_' + j
    d, v = pair(parent, sv); check(j + ' servo tabs seated on the cheek outer face: distance', d, 0.0); check(j + ' servo/cheek common volume', v, 0.0, unit='mm3')
    d, v = pair(child, hn); check(j + ' horn nested in the block pocket: distance', d, 0.0); check(j + ' horn/block common volume', v, 0.0, unit='mm3')
    d, v = pair(sv, hn); check(j + ' horn on the spline top: distance', d, 0.0); check(j + ' horn/servo common volume', v, 0.0, unit='mm3')
    d, v = pair(parent, br); check(j + ' bearing pressed in the cheek: distance', d, 0.0); check(j + ' bearing/cheek common volume', v, 0.0, unit='mm3')
    d, v = pair(child, br); check(j + ' stub in the bearing bore: radial clearance', d, P['stub_clear'], 1e-4); check(j + ' stub/bearing common volume', v, 0.0, unit='mm3')
    d, v = pair(sv, cs); check(j + ' centre screw engagement in the spline', v, CENTRE_VOL, 1e-3, 'mm3')
    d, v = pair(child, cs); check(j + ' centre screw head seated in the block counterbore: distance', d, 0.0); check(j + ' centre screw/block common volume', v, 0.0, unit='mm3')
    d, v = pair(hn, cs); check(j + ' centre screw/horn common volume (hub bore)', v, 0.0, unit='mm3')
    for i in (0, 1):
        d, v = pair(parent, f'tabscrew_{j}_{i}'); check(f'{j} tab screw {i} engagement in the tap-drilled cheek', v, TAB_VOL, 1e-3, 'mm3')
        d, v = pair(sv, f'tabscrew_{j}_{i}'); check(f'{j} tab screw {i}/servo tab common volume', v, 0.0, unit='mm3')
    d, v = pair(parent, child); check(j + ' stub through the inboard cheek lip hole: radial clearance (nearest parent/child approach)', d, 4.5 - (4.0 - P['stub_clear']), 1e-3)
    check(j + ' parent/child common volume', v, 0.0, unit='mm3')

# The window clearance, from the section through the outboard cheeks' mid-plane
# (both cheeks share the module's Y layout, printed by the script itself).
m = re.search(r'cheek outer (-?[0-9.]+), cheek inner (-?[0-9.]+)', stdout)
assert m, 'the script no longer prints its module Y layout'
y_outer, y_inner = float(m.group(1)), float(m.group(2))
offset = (y_outer + y_inner) / 2.0
def seg(p, a, b):
    (ax, ay), (bx, by), (px, py) = a, b, p
    dx, dy = bx - ax, by - ay; l2 = dx * dx + dy * dy
    t = 0 if l2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)
def loops_distance(A, B):
    return min(seg(p, lb[i], lb[(i + 1) % len(lb)]) for la in A for lb in B for p in la for i in range(len(lb)))
summary = json.loads((project / 'review' / 'section' / rev / f'XZ-{offset:.17g}' / 'summary.json').read_text())
assert summary['status'] == 'ok' and summary['revision'] == rev, summary.get('status')
objs = summary['objects']
sections = {'plane': 'XZ', 'offset_mm': offset, 'objects_cut': summary['objects_cut']}
for j, parent in (('shoulder', 'base'), ('elbow', 'upper_arm')):
    gap = loops_distance(objs['comp_servo_' + j]['contours_mm'], objs['comp_' + parent]['contours_mm'])
    check(j + ' window clearance around the case (section)', gap, P['window_clear'], 0.01)
    sections[j + '_gap_mm'] = round(gap, 4)

# The side gap (child block to the inboard cheek), from an XY section 5.3 mm above
# each joint axis (5.3: an exact 6 lands on a tessellation edge and the cut refuses): above the lip hole and stub, below the cheek top, so the
# nearest approach between the two contours is the declared gap itself.
for j, parent, child, z in (('shoulder', 'base', 'upper_arm', P['z_shoulder'] + 5.3),
                            ('elbow', 'upper_arm', 'forearm', P['z_shoulder'] + P['upper_len'] + 5.3)):
    xy = json.loads((project / 'review' / 'section' / rev / f'XY-{z:.17g}' / 'summary.json').read_text())
    assert xy['status'] == 'ok' and xy['revision'] == rev, xy.get('status')
    gap = loops_distance(xy['objects']['comp_' + child]['contours_mm'], xy['objects']['comp_' + parent]['contours_mm'])
    check(j + ' block to inboard cheek gap (XY section 5.3 mm above the axis)', gap, P['side_gap'], 0.01)
    sections[j + '_side_gap'] = {'plane': 'XY', 'offset_mm': z, 'objects_cut': xy['objects_cut'], 'gap_mm': round(gap, 4)}

screws = ('tabscrew', 'centrescrew')
others = [c for c in clearance if c['common_volume_mm3'] > 1e-6
          and not (c['first'].startswith(tuple('comp_' + s for s in screws)) or c['second'].startswith(tuple('comp_' + s for s in screws)))]
checks.append({'check': 'no intersection other than the 6 declared thread engagements', 'measured': len(others), 'expected': 0, 'ok': not others, 'unit': 'pairs'})
checks.append({'check': 'no unmeasured pair', 'measured': sum(1 for c in clearance if c.get('error')), 'expected': 0,
               'ok': not any(c.get('error') for c in clearance), 'unit': 'pairs'})
world = [s for c in dyn['collisions'] for s in c['shapes'] if s['kind'] not in ('box', 'sphere')]
checks.append({'check': 'no plane, floor, bench or world geometry in the design', 'measured': len(world), 'expected': 0, 'ok': not world, 'unit': 'geoms'})
checks.append({'check': 'no initial contact between proxies', 'measured': len(dyn['initial_contacts']), 'expected': 0, 'ok': not dyn['initial_contacts'], 'unit': 'contacts'})
checks.append({'check': 'the base is the only grounded component', 'measured': len(dyn['grounded_components']), 'expected': 1,
               'ok': dyn['grounded_components'] == ['comp_base'], 'unit': 'components'})
revolute = [j for j in dyn['joints'] if j['joint_kind'] == 'revolute']
checks.append({'check': 'exactly two revolute joints, each a limited hinge', 'measured': len(revolute), 'expected': 2,
               'ok': len(revolute) == 2 and all(j['mujoco_type'] == 'hinge' and not j['limits']['one_sided'] for j in revolute), 'unit': 'joints'})
checks.append({'check': 'every output a valid single solid', 'measured': sum(not r['valid_single_solid'] for r in rows), 'expected': 0,
               'ok': all(r['valid_single_solid'] for r in rows), 'unit': 'solids'})
checks.append({'check': 'solver residual: solved', 'measured': outs['heron_solved']['diagnostics']['solver_code'], 'expected': 0,
               'ok': outs['heron_solved']['diagnostics']['status'] == 'solved', 'unit': 'code'})
task = json.loads((project / accepted['staging'] / outs['heron_task']['artifact_path']).read_text())
check('episode length (steps)', task['episode']['max_steps'], P['episode_steps'], 0.5, 'steps')
checks.append({'check': 'termination reads tip_z below tip_floor', 'measured': task['termination'][0]['below'], 'expected': P['tip_floor'],
               'ok': task['termination'][0]['expression'] == 'tip_z' and task['termination'][0]['below'] == P['tip_floor'], 'unit': 'mm'})
checks.append({'check': 'reset variation: none (grounded); disturbances on the forearm', 'measured': len(task['disturbance']), 'expected': 2,
               'ok': not task['reset_variation'] and all(d['body'] == 'comp_forearm' for d in task['disturbance']) and len(task['disturbance']) == 2, 'unit': 'events'})
ok = all(c['ok'] for c in checks)

printed = sum(r['mass_g'] for r in rows if not r['catalog']); purchased = sum(r['mass_g'] for r in rows if r['catalog'])
counts = {}
for r in rows:
    if r['catalog']:
        k = f"{r['catalog']['family']}/{r['catalog']['part_number']}"; counts[k] = counts.get(k, 0) + 1
inv = ['# Heron — per-solid inventory', '', 'Verified against source: 2026-09-14. [Cadex-new]', '',
       f'Accepted revision `{rev}`; generated by `docs/probes/ot6/heron/fit_check.py` from the accepted attempt. '
       'Masses are the mjcf export\'s, computed from the exact solids at the declared densities (PLA 1240, steel 7850, nylon 1150, the MG90S at its datasheet 13.4 g). '
       'Collision proxies are the shapes each body declares for MuJoCo; "relation" says how they stand to the solid. Proxies are never what the viewer shows by default.', '',
       '| component | solid | source | mass (g) | volume (mm³) | proxies | relation to the solid |', '|---|---|---|---|---|---|---|']
inv += [f"| `{r['component']}` | `{r['solid']}` | {r['source']} | {r['mass_g']:.2f} | {r['volume_mm3']:.1f} | {r['proxies']} | {r['relation']} |" for r in rows]
inv += ['', '## Roll-up', '', f'- {len(rows)} solids: {sum(1 for r in rows if not r["catalog"])} modelled printable parts, {sum(1 for r in rows if r["catalog"])} catalog parts.']
inv += [f'- `{k}` × {n}' for k, n in sorted(counts.items())]
inv += [f'- mass: printed {printed:.1f} g, purchased {purchased:.1f} g, total {printed + purchased:.1f} g.',
        f"- reach {P['upper_len'] + P['fore_len']:.0f} mm from the shoulder at z = {P['z_shoulder']:.0f}; target ({P['target_x']:.0f}, 0, {P['target_z']:.0f}) mm.",
        '- no floor, bench, wall or stage: every collision geom is a box or sphere on a part of the design; the base is grounded because an arm is bolted to its bench.', '']
(project / 'docs' / 'INVENTORY.md').write_text('\n'.join(inv))
fit = ['# Heron — fit check', '', 'Verified against source: 2026-09-14. [Cadex-new]', '',
       f'Accepted revision `{rev}`. Every row is a published measurement: pair distance and common volume on the exact BREP at the solved rest pose '
       '(`cadex clearance`, ADR-237), or the gap between contours in a `cadex section` cut through the outboard cheeks\' mid-plane. Expected values are the script\'s declared clearances '
       'and the analytic thread-engagement volumes (M2 shank in the spline, M2 shank past a 1.6 mm tap drill). Not a swept check; not a fabrication check.', '',
       '| check | measured | expected | unit | verdict |', '|---|---|---|---|---|']
fit += [f"| {c['check']} | {c['measured']} | {c['expected']} | {c['unit']} | {'ok' if c['ok'] else '**FAIL**'} |" for c in checks]
fit += ['', f"**Verdict: {'every rule holds' if ok else 'FAILED'}** ({sum(c['ok'] for c in checks)} of {len(checks)} checks).", '']
(project / 'docs' / 'FIT.md').write_text('\n'.join(fit))
receipt = {'schema': 'heron-fit-evidence-v1', 'project': project.name, 'revision': rev,
           'script_sha256': hashlib.sha256(script.encode()).hexdigest(), 'script_bytes': len(script),
           'result_sha256': hashlib.sha256((project / accepted['staging'] / 'result.json').read_bytes()).hexdigest(),
           'params': P, 'mass_g': {'printed': round(printed, 2), 'purchased': round(purchased, 2), 'total': round(printed + purchased, 2)},
           'catalog_counts': counts, 'components': len(rows), 'pair_count': len(clearance), 'geoms': model['mjcf']['geom_count'],
           'inventory': rows, 'checks': checks, 'section': sections, 'ok': ok,
           'scope': 'retained exact BREP at the accepted solved rest pose; no restore or swept-fit certification'}
(out / 'fit.json').write_text(json.dumps(receipt, indent=1) + '\n')
print(json.dumps({'ok': ok, 'checks': len(checks), 'failed': [c['check'] for c in checks if not c['ok']], 'mass_g': receipt['mass_g'], 'section': sections}, indent=1))
sys.exit(0 if ok else 1)
