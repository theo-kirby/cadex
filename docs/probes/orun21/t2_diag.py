# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""orun21 T2: where the Go1 scan policy fails on held-out terrain seeds (fall or stall), and what ground is under it."""
import json, math, sys
from pathlib import Path

def ground(t, x, y):
    """Top of the terrain at (x, y) mm: boxes are blocks, domes are sphere caps."""
    z = t["plane_z_mm"]
    for b in t["boxes"]:
        cx, cy, cz = b["centre_mm"]; hx, hy, hz = b["half_mm"]
        qx, qy, qz, qw = b["rotation_xyzw"]
        yaw = math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))
        dx, dy = x - cx, y - cy
        lx = dx * math.cos(-yaw) - dy * math.sin(-yaw); ly = dx * math.sin(-yaw) + dy * math.cos(-yaw)
        if abs(lx) <= hx and abs(ly) <= hy:
            z = max(z, cz + hz)
    for d in t["domes"]:
        cx, cy, cz = d["centre_mm"]; r = d["radius_mm"]
        q = r * r - (x - cx) ** 2 - (y - cy) ** 2
        if q > 0:
            z = max(z, cz + math.sqrt(q))
    return z

def up_z(q):
    x, y, z, w = q
    return 1 - 2 * (x * x + y * y)

def yaw_of(q):
    x, y, z, w = q
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))

def edge(t, x, y, yaw, reach=600, step=20):
    """Largest rise and drop between successive 20 mm samples within reach ahead, and the slope over it."""
    prof = [ground(t, x + s * math.cos(yaw), y + s * math.sin(yaw)) for s in range(-200, reach + 1, step)]
    jumps = [b - a for a, b in zip(prof, prof[1:])]
    return max(jumps), min(jumps), (prof[-1] - prof[10]) / reach

rows = []
for seed_dir in sorted(Path(sys.argv[1]).glob("s[0-9]*")):
    g = json.load(open(seed_dir / "goto.json"))
    if g["pass"]["all"]:
        continue
    tr = json.load(open(seed_dir / "view" / "trace.json"))
    t = tr["terrain"]; frames = tr["frames"]
    pos = [f["component_placements"]["trunk"]["position_mm"] for f in frames]
    rot = [f["component_placements"]["trunk"]["rotation_xyzw"] for f in frames]
    why = []
    if g["fell"]:
        i = next((k for k, q in enumerate(rot) if up_z(q) < 0.5), len(rot) - 1)
        j = max(0, i - 25)  # one second before the tilt
        x, y, _ = pos[j]
        # heading of travel over the second before
        k = max(0, j - 12); yaw = math.atan2(pos[j][1] - pos[k][1], pos[j][0] - pos[k][0])
        rise, drop, slope = edge(t, x, y, yaw)
        why.append(("fall", round(i / 25, 1), round(rise), round(drop), round(math.degrees(math.atan(slope)), 1),
                    round(ground(t, x, y) - t["plane_z_mm"])))
    bad = [p for p in g["points"] if not p["reached"] and p["closest_m"] is not None]
    for p in bad[:1]:
        # stall: mean trunk position over the last 5 s of the trace
        tail = pos[-125:]; x = sum(a[0] for a in tail) / len(tail); y = sum(a[1] for a in tail) / len(tail)
        tx, ty = (v * 1000 for v in g["sequence"]["points"][p["point"]]["xy_m"])
        yaw = math.atan2(ty - y, tx - x)
        rise, drop, slope = edge(t, x, y, yaw)
        why.append(("stall" if not g["fell"] else "stall*", p["point"], p["band"], p["closest_m"], round(rise), round(drop),
                    round(math.degrees(math.atan(slope)), 1)))
    slow = [round(p["speed_ratio"], 2) for p in g["points"] if p.get("speed_ratio") is not None and p["speed_ratio"] < 0.85 and p["reached"]]
    rows.append((seed_dir.name, g["pass"], why, slow))
for name, ps, why, slow in rows:
    fails = [k for k, v in ps.items() if not v and k != "all"]
    print(name, fails, why, "slow-reached:", slow)
