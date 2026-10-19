"""Render chosen real parts at one frame of an evaluation trace, on the dark floor (orun12 O9/Q2).

usage: PYTHONPATH=cli pixi run python docs/probes/orun12/render_frame.py PROJECT TRACE TIME_S OUT.png
       [--parts c_chest_frame,c_qdd_wrist_l,...] [--hot c_qdd_wrist_l,...] [--az 0] [--el 4]
       [--half 160] [--size 720]

Places each part by the trace frame nearest ``TIME_S`` (the component
placements ``judge.py`` kept) and draws it with the studio renderer that
``cadex render`` uses: ``--hot`` parts in the accent colour, the rest as
shell, framed on the hot parts. ``--az`` is the camera azimuth in degrees
(0 looks from -Y, the right side; 90 from +X, the front), ``--el`` its
elevation in degrees (89 looks down). It is how a pair ``trace_check.py`` flags is looked at.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from cadex_cli import film, video as studio_video
from cadex_cli.studio import STUDIO as R


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("project")
    p.add_argument("trace")
    p.add_argument("time_s", type=float)
    p.add_argument("out")
    p.add_argument("--parts", default="")
    p.add_argument("--hot", default="")
    p.add_argument("--az", type=float, default=0.0)
    p.add_argument("--el", type=float, default=4.0)
    p.add_argument("--half", type=float, default=160.0)
    p.add_argument("--size", type=int, default=720)
    args = p.parse_args(argv)

    trace = json.loads(Path(args.trace).read_text())
    frames = [f for f in trace["frames"] if f["frame_kind"] == "solver_output"]
    frame = min(frames, key=lambda f: abs(float(f["nominal_time_s"]) - args.time_s))
    placed = frame["component_placements"]
    flats, _sources, _world = film.retained_solids(Path(args.project), "cat_model")
    hot = [k for k in args.hot.split(",") if k]
    parts = [k for k in (args.parts.split(",") if args.parts else []) if k] + hot
    parts = [k for i, k in enumerate(parts) if k in flats and k not in parts[:i]]

    def triangles(k):
        f = flats[k]
        return [((f[i], f[i + 1], f[i + 2]), (f[i + 3], f[i + 4], f[i + 5]), (f[i + 6], f[i + 7], f[i + 8]))
                for i in range(0, len(f), 9)]

    def look(k):
        return (R.ROLE_COLORS["accent"], R.FINISH["accent"]) if k in hot else (R.ROLE_COLORS["shell"], R.FINISH["shell"])

    local = {k: R._prepare([(look(k), triangles(k))]) for k in parts}
    posed = [t for k in parts for t in studio_video._posed(local[k], placed[k])]
    basis = R.camera(args.az, args.el)

    def proj(q):
        return (sum(a * b for a, b in zip(q, basis[0])), sum(a * b for a, b in zip(q, basis[1])))

    pts = []
    for k in hot or parts:
        rows, pos = studio_video._rows(placed[k])
        for tri in triangles(k)[::5]:
            for c in tri:
                pts.append(proj([sum(rows[i][j] * c[j] for j in range(3)) + pos[i] for i in range(3)]))
    cx = (min(q[0] for q in pts) + max(q[0] for q in pts)) / 2
    cy = (min(q[1] for q in pts) + max(q[1] for q in pts)) / 2
    bounds = ([cx - args.half, cy - args.half], [cx + args.half, cy + args.half])
    pixels, _ = R.studio(posed, basis, bounds=bounds, size=args.size, shadow=R._contact_shadow(posed, floor=0.0))
    Image.frombytes("RGB", (args.size, args.size), bytes(pixels)).save(args.out, optimize=True)
    print(f"{args.out}: frame {frame['frame_index']} at {float(frame['nominal_time_s']):.2f} s, parts {parts}")


if __name__ == "__main__":
    main(sys.argv[1:])
