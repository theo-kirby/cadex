# orun20 S1 lab: leon I's saddle skin (leon_i5.py), its regions as boxes (A) and as rounded boxes (B).
wh = 545.0
keel_z = wh - 275.0 - 20.0
cw = 260.0
GAP = 3.0
R = 7.0
FLANK_Z = 410.0
result = {}

def band(x, ztop, zbot, w, sq=2.4):
    zc = 0.5 * (ztop + zbot)
    return {"at": (x, 0.0, zc), "width": w, "top": ztop - zc, "bottom": zc - zbot, "square": sq}

def ybox(x0, x1, y0, y1, z0, z1):
    return part.box(x1 - x0, abs(y1 - y0), z1 - z0, origin=(x0, min(y0, y1), z0))

def rbox(x0, x1, y0, y1, z0, z1, r=R):
    return part.fillet(ybox(x0, x1, y0, y1, z0, z1), r)

form = lib.form([
    band(5.0, wh - 32.0, keel_z + 68.0, 0.84 * cw),
    band(-42.0, wh - 46.0, keel_z + 86.0, 0.76 * cw),
    band(-95.0, wh - 49.0, keel_z + 91.0, 0.81 * cw),
], label="saddle_form")
A = part.skin([form], [ybox(-80.0, 0.0, -45.0, 45.0, 430.0, 700.0),
                       ybox(-80.0, 0.0, 45.0, 300.0, FLANK_Z, 700.0),
                       ybox(-80.0, 0.0, -300.0, -45.0, FLANK_Z, 700.0)], thickness=2.5, gap=GAP, label="a")
# B: each region rounded R on every edge; the flanks start a gap past the saddle's side,
# so no later piece is trimmed by an earlier one's grown outline (which would leave a corner)
E = GAP + 0.2
B = part.skin([form], [rbox(-80.0, 0.0, -45.0, 45.0, 430.0, 700.0),
                       rbox(-80.0, 0.0, 45.0 + E, 300.0, FLANK_Z, 700.0),
                       rbox(-80.0, 0.0, -300.0, -45.0 - E, FLANK_Z, 700.0)], thickness=2.5, gap=GAP, label="b")
for tag, sk in (("a", A), ("b", B)):
    for i, piece in enumerate(sk.parts):
        result[tag + str(i)] = piece
