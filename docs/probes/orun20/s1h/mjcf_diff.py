import sys, xml.etree.ElementTree as ET
def rows(p):
    t = ET.parse(p).getroot()
    j = sorted((e.get('name'), e.get('type'), e.get('axis'), e.get('range'), e.get('pos'), e.get('limited'), e.get('damping'), e.get('armature'), e.get('stiffness'), e.get('frictionloss'), e.get('ref'), e.get('springref')) for e in t.iter('joint'))
    a = sorted((e.tag, tuple(sorted(e.attrib.items()))) for e in t.find('actuator')) if t.find('actuator') is not None else []
    eq = sorted((e.tag, tuple(sorted(e.attrib.items()))) for e in t.find('equality')) if t.find('equality') is not None else []
    k = sorted((e.tag, tuple(sorted(e.attrib.items()))) for e in t.iter('key'))
    cols = sorted((e.get('name'), e.get('type'), e.get('size'), e.get('pos'), e.get('quat'), e.get('fromto')) for e in t.iter('geom') if e.get('contype') != '0' or e.get('conaffinity') != '0')
    return {'joints': j, 'actuators': a, 'equality': eq, 'keyframes': k, 'colliding geoms': cols}
A, B = rows(sys.argv[1]), rows(sys.argv[2])
for key in A:
    same = A[key] == B[key]
    print(f"{key}: {len(A[key])} vs {len(B[key])}, identical={same}")
    if not same:
        sa, sb = set(A[key]), set(B[key])
        for x in list(sa - sb)[:4]: print("   only A", x)
        for x in list(sb - sa)[:4]: print("   only B", x)
