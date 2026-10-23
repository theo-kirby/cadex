"""Policies side by side, side-on, on the dark floor, from their evaluations' traces (orun18 F1).

usage: CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/side_film.py \
           PROJECT OUT_WEBM [--seed 1001] [--start 6] [--span 2] [--slow 2] [--size 320] \
           'TITLE@EVAL_DIR=LABEL,EVAL_DIR=LABEL,...' ['TITLE@...' ...]

Each argument after OUT_WEBM is one clip: a row of panels, one per evaluation
directory ``speed_judge.py`` wrote. Every panel shows the same seed over the
same window of simulation time, SPAN seconds from START, first at real time
and then at 1/SLOW speed; the clips follow one another. A panel is drawn by
the engine's own film renderer (``cadex_cli.film``'s stage: the accepted
attempt's retained tessellation moved rigidly to each recorded pose, the
contact shadow on the model's collision plane), side-on to the way the
chest travelled, 12 degrees above the floor, the window following the chest
(its middle held at the body's mean offset from the chest) and never moving
up or down. All panels of a clip share one scale, so a
longer stride reads as longer. Frames are 25 a second and each shows the
latest solved pose at or before its time: the traces are solved at 50 Hz, so
at 1/2 speed every solved pose is shown once and nothing is interpolated.

The trace drawn is the trace measured: its sha256 is the one the evaluation
recorded. No engine is opened (every part is drawn as shell: no inventory is
read), nothing in the project is written, and the film goes outside the
repository. It prints one JSON line per clip with what was drawn.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "cli"))

from cadex_cli import film as F  # noqa: E402
from cadex_cli import video as V  # noqa: E402
from cadex_cli.studio import STUDIO as S  # noqa: E402

FPS = 25
GUTTER = 4
ELEVATION = F.DETAIL_ELEVATION_DEGREES


def panel(root: Path, directory: Path, seed: int, start: float, span: float) -> dict:
    """One evaluation's seed: its stage, frames, floor, camera and per-frame chest position."""

    report = json.loads((directory / "evaluation.json").read_text())
    row = next((r for r in report["seeds"] if int(r["seed"]) == seed), None)
    F._require(row is not None, f"{directory.name}: seed {seed} is not in this evaluation")
    flats, sources, world = F.retained_solids(root, str(report["model_output"]))
    meshes, _geometry = V.drawn_meshes({n: f for n, f in flats.items() if n not in world})
    looks, _source = F.materials(sources, list(meshes), str(report["accepted_revision"]), None)
    stage = F._Stage(meshes, looks, {n: flats[n] for n in world})
    frames, times, _target = F.read_trace(directory / row["trace"]["file"], row["trace"]["sha256"],
                                          list(flats))
    F._require(times[-1] >= start + span - 1e-9,
               f"{directory.name} seed {seed} ended at {times[-1]:.2f} s, before {start + span:.2f} s")
    rig = report.get("rig") or {}
    floor, _why = stage.floor(frames, rig.get("floor_mm"))
    base = rig.get("base")
    window = [k for k, t in enumerate(times) if start - 1e-9 <= t <= start + span + 1e-9]
    azimuth, _travel = F.travel_azimuth(stage, [frames[k] for k in window], base)
    basis = S.camera(azimuth, ELEVATION)
    right = basis[0]
    centre = {k: sum(c * r for c, r in zip(stage.centre(frames[k]["component_placements"], base), right))
              for k in window}
    boxes = {k: F._projected(stage.box(frames[k]["component_placements"]), basis) for k in window}
    # Follow the chest, but frame the whole body: the window's middle sits the
    # body's mean offset ahead of or behind the chest (the tail is long).
    offset = sum((b[0] + b[2]) / 2 - centre[k] for k, b in boxes.items()) / len(boxes)
    centre = {k: c + offset for k, c in centre.items()}
    across = max(max(centre[k] - b[0], b[2] - centre[k]) for k, b in boxes.items())
    low, high = min(b[1] for b in boxes.values()), max(b[3] for b in boxes.values())
    speed = (stage.centre(frames[window[-1]]["component_placements"], base)[0]
             - stage.centre(frames[window[0]]["component_placements"], base)[0]) / 1000 / (
                 times[window[-1]] - times[window[0]])
    return {"name": directory.name, "stage": stage, "frames": frames, "times": times, "floor": floor,
            "basis": basis, "centre": centre, "across": across, "low": low, "high": high,
            "azimuth": azimuth, "speed": speed, "trace": row["trace"]["sha256"],
            "policy": report.get("policy_sha256"), "command": report.get("judged_command_mm_s")}


def schedule(start: float, span: float, slow: int) -> list[tuple[float, str]]:
    """(simulation time, clock tag) per film frame: real time, then 1/SLOW."""

    real = [(start + i / FPS, "") for i in range(round(span * FPS))]
    slowed = [(start + i / (FPS * slow), f"  1/{slow}") for i in range(round(span * FPS * slow))]
    return real + slowed


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("clips", nargs="+")
    parser.add_argument("--seed", type=int, default=1001)
    parser.add_argument("--start", type=float, default=6.0)
    parser.add_argument("--span", type=float, default=2.0)
    parser.add_argument("--slow", type=int, default=2)
    parser.add_argument("--size", type=int, default=320)
    args = parser.parse_args(argv)
    root = args.project.expanduser().resolve()
    F.FRAME = args.size  # the stage draws its frames at this edge
    evaluations = root / "evaluations"
    clips = []
    for spec in args.clips:
        title, _, rest = spec.partition("@")
        panels = []
        for item in rest.split(","):
            name, _, label = item.partition("=")
            p = panel(root, evaluations / name, args.seed, args.start, args.span)
            p["label"] = label or name
            panels.append(p)
        clips.append((title, panels))
    columns = max(len(p) for _t, p in clips)
    width = columns * args.size + (columns - 1) * GUTTER
    out = args.out.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with tempfile.TemporaryDirectory(prefix="side-film-") as work:
        for title, panels in clips:
            # One scale for the clip: the widest reach of any panel, about its chest.
            half = max(max(p["across"], (p["high"] - p["low"]) / 2) for p in panels) * (1 + 2 * F.PAD)
            for p in panels:
                p["cy"] = (p["low"] + p["high"]) / 2
            for moment, tag in schedule(args.start, args.span, args.slow):
                canvas = S.Canvas(width, args.size, S.PALETTE["bg"])
                for column, p in enumerate(panels):
                    at = F._index(p["times"], moment)
                    cx = p["centre"].get(at)
                    if cx is None:  # the frame at START's edge: the nearest one the window measured
                        cx = p["centre"][min(p["centre"], key=lambda k: abs(k - at))]
                    bounds = ([cx - half, p["cy"] - half], [cx + half, p["cy"] + half])
                    pixels = bytearray(p["stage"].draw(p["frames"][at]["component_placements"], p["basis"],
                                                       bounds, p["floor"], f"{p['times'][at]:.2f} s{tag}"))
                    face = S.Canvas(args.size, args.size, (0, 0, 0))
                    face.pixels = pixels
                    face.text(10, 10, p["label"], 2, S.PALETTE["ink_2"])
                    if column == 0 and title:
                        face.text(10, 34, title, 2, S.MUTED)
                    canvas.paste(column * (args.size + GUTTER), 0, bytes(face.pixels), args.size, args.size)
                (Path(work) / f"{count:05d}.png").write_bytes(S.png(bytes(canvas.pixels), width, args.size))
                count += 1
            print(json.dumps({"clip": title, "seed": args.seed, "start_s": args.start, "span_s": args.span,
                              "half_extent_mm": round(half, 1),
                              "panels": [{"evaluation": p["name"], "label": p["label"],
                                          "command_mm_s": p["command"], "policy_sha256": p["policy"],
                                          "trace_sha256": p["trace"],
                                          "chest_m_s_in_window": round(p["speed"], 3),
                                          "azimuth_deg": round(p["azimuth"], 2)} for p in panels]}))
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
    print(out, out.stat().st_size, "bytes,", count, "frames decoded,", f"{count / FPS:.1f} s")


if __name__ == "__main__":
    main(sys.argv[1:])
