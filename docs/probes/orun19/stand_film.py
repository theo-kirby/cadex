"""Leo standing, one full turn, on the dark floor (orun19 F1: "v06 standing").

usage: CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun19/stand_film.py \
           PROJECT EVAL_DIR OUT_WEBM [--seed 1001] [--size 480] [--seconds 6] [--label TEXT]

The pose drawn is the first frame (t = 0) of one seed's trace in an evaluation
``speed_judge.py`` wrote: the model's standing keyframe as the evaluation spawned
it, before the policy's first action. The camera turns once about the body's
middle, 12 degrees above the floor, at one scale for the whole turn. It is drawn
by the engine's own film stage (``cadex_cli.film``: the accepted attempt's
retained tessellation moved rigidly to the recorded placements, the contact
shadow on the model's collision plane), as ``orun18/side_film.py`` draws. The
trace drawn is the trace measured (its sha256 is the evaluation's). Nothing in
the project is written and the film goes outside the repository; it prints one
JSON line with what was drawn and the decode check.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "cli"))

from cadex_cli import film as F  # noqa: E402
from cadex_cli import video as V  # noqa: E402
from cadex_cli.studio import STUDIO as S  # noqa: E402

FPS = 25


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project", type=Path)
    parser.add_argument("evaluation", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--seed", type=int, default=1001)
    parser.add_argument("--size", type=int, default=480)
    parser.add_argument("--seconds", type=float, default=6.0)
    parser.add_argument("--label", default="leo v06 standing")
    args = parser.parse_args(argv)
    root = args.project.expanduser().resolve()
    directory = args.evaluation.expanduser().resolve()
    F.FRAME = args.size
    report = json.loads((directory / "evaluation.json").read_text())
    row = next((r for r in report["seeds"] if int(r["seed"]) == args.seed), None)
    F._require(row is not None, f"{directory.name}: seed {args.seed} is not in this evaluation")
    flats, sources, world = F.retained_solids(root, str(report["model_output"]))
    meshes, _geometry = V.drawn_meshes({n: f for n, f in flats.items() if n not in world})
    looks, _source = F.materials(sources, list(meshes), str(report["accepted_revision"]), None)
    stage = F._Stage(meshes, looks, {n: flats[n] for n in world})
    frames, times, _target = F.read_trace(directory / row["trace"]["file"], row["trace"]["sha256"],
                                          list(flats))
    pose = frames[0]["component_placements"]
    floor, why = stage.floor(frames, (report.get("rig") or {}).get("floor_mm"))
    count = round(args.seconds * FPS)
    turns = [360.0 * i / count for i in range(count)]
    boxes = [F._projected(stage.box(pose), S.camera(a, F.DETAIL_ELEVATION_DEGREES)) for a in turns]
    half = max(max(b[2] - b[0], b[3] - b[1]) / 2 for b in boxes) * (1 + 2 * F.PAD)
    out = args.out.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="stand-film-") as work:
        for i, (azimuth, b) in enumerate(zip(turns, boxes)):
            basis = S.camera(azimuth, F.DETAIL_ELEVATION_DEGREES)
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            bounds = ([cx - half, cy - half], [cx + half, cy + half])
            face = S.Canvas(args.size, args.size, (0, 0, 0))
            face.pixels = bytearray(stage.draw(pose, basis, bounds, floor, f"t {times[0]:.2f} s"))
            face.text(10, 10, args.label, 2, S.PALETTE["ink_2"])
            (Path(work) / f"{i:05d}.png").write_bytes(S.png(bytes(face.pixels), args.size, args.size))
        encoder = V.ffmpeg()
        result = subprocess.run([encoder, "-v", "error", "-nostdin", "-y", "-framerate", str(FPS),
                                 "-i", str(Path(work) / "%05d.png"), "-an", "-c:v", "libvpx-vp9",
                                 "-b:v", "0", "-crf", "34", "-pix_fmt", "yuv420p", str(out)],
                                capture_output=True, timeout=600)
        if result.returncode != 0:
            raise SystemExit(result.stderr.decode())
    check = subprocess.run([encoder, "-v", "error", "-nostdin", "-i", str(out), "-f", "framemd5", "-"],
                           capture_output=True, timeout=300)
    decoded = sum(1 for line in check.stdout.decode().splitlines() if line and not line.startswith("#"))
    if check.returncode != 0 or decoded != count:
        raise SystemExit(f"decode check failed: {decoded} of {count} frames")
    lowest = min(p[2] for p in stage.box(pose))
    print(json.dumps({"evaluation": directory.name, "seed": args.seed, "time_s": times[0],
                      "policy_sha256": report.get("policy_sha256"), "trace_sha256": row["trace"]["sha256"],
                      "model_sha256": report.get("model_sha256"), "floor_mm": floor, "floor_from": why,
                      "lowest_bound_mm": round(lowest, 1), "half_extent_mm": round(half, 1)}))
    print(out, out.stat().st_size, "bytes,", count, "frames decoded,", f"{count / FPS:.1f} s")


if __name__ == "__main__":
    main(sys.argv[1:])
