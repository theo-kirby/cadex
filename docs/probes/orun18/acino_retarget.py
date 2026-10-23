"""Retarget one AcinoSet cheetah stride to leo v05 as a gait clip (orun18 C4).

usage: pixi run python docs/probes/orun18/acino_retarget.py MODEL_XML FTE_PICKLE FIRST END LABEL OUT_DIR [SAMPLES]

``FTE_PICKLE`` is one take's ``fte_pw/fte.pickle`` under ``~/mocap/acinoset/``
(D5a: AcinoSet, Joska et al. ICRA 2021, cited in SOURCES.md; never committed),
read by ``acino_strides.load`` (numpy arrays only) and low-passed at 12 Hz as
``acino_strides.py`` measured (c4-cheetah.md). ``FIRST``/``END`` are the stride's
frames from that probe (left hind touchdown to the next). Writes
``OUT_DIR/LABEL.clip.json`` and ``OUT_DIR/LABEL.measure.json`` exactly as
``retarget.py`` does for the dog, by the same function: this file only reads the
cheetah into the stride ``retarget.retarget`` takes.

**The mapping.** The FTE model has 20 points and no paws: each leg ends at its
"ankle", the wrist (fore) or hock (hind). The probe tried to place the paw below
it as a planted pivot (a fixed-length distal segment turning about a point on
the floor, fitted to every stance's arc). That fit is ill-posed: the floor height
and the segment's length trade against each other on arcs of five to eight
frames, and two of three takes diverged. So the paw is not modelled:

- **leo's paw follows the cheetah's wrist and hock**, each over its own stance
  level (its 5th percentile height over the stride);
- **each girdle's height is its pivots over its own distal floor** (shoulders
  over the wrists', hips over the hocks'), so ``s`` is leo's pivot height over
  the cheetah's pivot-over-wrist or -hock height. The cheetah's true pivot
  height is greater by the planted wrist's or hock's height, so ``s`` is too
  large and leo's speed (``sqrt(s)`` times the stride's at equal Froude number)
  is an upper bound, as in c4-cheetah.md;
- **stance is the wrist or hock stopped**, read with ``acino_strides.py``'s rule
  (within 40 mm of its stance level, under 0.35 of the trunk's speed, lifts of up
  to 25 ms closed). The paw is planted for longer than that, so duty reads
  short and flight long; the touchdown order is what the clip claims;
- the wrist or hock rolls over the planted paw (about 43 mm over a stance,
  c4-cheetah.md), so ``retarget.py``'s **raw slip** here is that roll, not paw
  slip; the target is held still through stance as for the dog, and the
  **solved slip** and **foot miss** are leo's own;
- **the spine** is the thorax (spine point to neck base) against the pelvis
  (tail base to spine point) in pitch, and the shoulder line against the hip
  line in heading, to ``j_spine`` / ``j_spine_yaw`` by leo's gains, as for the dog.

The stride is read on ``SAMPLES`` even steps of its phase (default, its frames),
each between its two frames linearly, in a heading frame: x along the spine
point's travel over the stride, y left, z up.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acino_strides as A  # noqa: E402
import retarget as R  # noqa: E402

CUTOFF_HZ = 12.0
PIVOT = {"LF": "l_shoulder", "RF": "r_shoulder", "LH": "l_hip", "RH": "r_hip"}
GIRDLE_FEET = {"fore": ("LF", "RF"), "hind": ("LH", "RH")}


def cheetah_stride(path: Path, first: int, end: int, samples: int | None = None) -> dict:
    """The stride as ``retarget.dog_stride`` gives the dog's, with its source and contact rule."""

    take = A.load(path)
    fps = take["fps"]
    pos = A.lowpass(take["pos"], fps, CUTOFF_HZ)
    ix = {name: k for k, name in enumerate(A.POINTS)}
    spine = pos[first:end + 1, ix["spine"], :2]
    fwd = spine[-1] - spine[0]
    fwd = fwd / np.linalg.norm(fwd)
    basis = np.array([[fwd[0], fwd[1], 0.0], [-fwd[1], fwd[0], 0.0], [0.0, 0.0, 1.0]])
    frames = slice(first, end + 1)
    # each girdle stands over its own distal points' floor (their 5th percentile
    # over the stride): the wrist's for the fore, the hock's for the hind
    floor = {g: float(np.percentile(pos[frames][:, [ix[A.FEET[f]] for f in feet], 2], 5))
             for g, feet in GIRDLE_FEET.items()}
    origin = np.array([spine[0, 0], spine[0, 1], 0.0])

    def track(name: str, girdle: str | None = None) -> np.ndarray:
        p = (pos[frames, ix[name]] - origin) @ basis.T
        if girdle:
            p[:, 2] -= floor[girdle]
        return p

    girdle_of = {f: g for g, feet in GIRDLE_FEET.items() for f in feet}
    paw = {f: track(A.FEET[f], girdle_of[f]) for f in A.FEET}
    pivot = {f: track(PIVOT[f], girdle_of[f]) for f in A.FEET}
    names = A.POINTS
    count = end - first
    steps = int(samples) if samples else count
    at_t = np.arange(steps) * (count / steps)
    low = np.floor(at_t).astype(int)
    w = at_t - low

    def read(a: np.ndarray) -> np.ndarray:
        shape = (-1,) + (1,) * (a.ndim - 1)
        return a[low] + w.reshape(shape) * (a[low + 1] - a[low])

    neck, mid, tail = track("neck_base"), track("spine"), track("tail_base")
    # for drawing: the fore leg's points over the fore floor, every other point over the hind
    points = np.stack([track(n, "fore" if "front" in n or n.endswith("shoulder") else "hind")
                       for n in names], axis=1)
    return {
        "dt": (1.0 / fps) * count / steps, "frames": [first, end], "frame_count": len(pos),
        "paw": {f: read(v) for f, v in paw.items()},
        "pivot": {f: read(v) for f, v in pivot.items()},
        "next_pivot_mid": 0.25 * sum(v[-1] for v in pivot.values()),
        "thorax": read(neck - mid), "pelvis": read(mid - tail),
        "thorax_lateral": read(pivot["LF"] - pivot["RF"]),
        "pelvis_lateral": read(pivot["LH"] - pivot["RH"]),
        "skeleton": {"parents": [-1] * len(names), "names": names, "points": read(points)},
        "contact": (A.CONTACT_M, A.CONTACT_SPEED, A.CONTACT_GAP_S),
        "source": {"name": str(Path(*path.parts[-5:-2])), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "label": f"AcinoSet cheetah {Path(*path.parts[-5:-2])} frames {first}-{end} "
                            f"({fps:g} fps, {CUTOFF_HZ:g} Hz low-pass; paw = wrist/hock)",
                   "sources": [A.CITATION, R.SOURCES[1]]},
        "floor_m": floor, "fps": fps,
    }


def main(argv: list[str]) -> None:
    model_path, pickle_path, first, end, label, out_dir = argv[:6]
    samples = int(argv[6]) if len(argv) > 6 else None
    stride = cheetah_stride(Path(pickle_path), int(first), int(end), samples)
    clip, measure, _ = R.retarget(Path(model_path), Path(pickle_path), int(first), int(end), label,
                                  samples, stride=stride)
    measure["cheetah"] = {"fps": stride["fps"], "cutoff_hz": CUTOFF_HZ,
                          "pivot_over_distal_floor_m": {g: float(np.mean([stride["pivot"][f][:, 2] for f in feet]))
                                                        for g, feet in GIRDLE_FEET.items()},
                          "paw": "wrist/hock (FTE has no paw): duty short, flight long, raw slip is the roll"}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(clip)
    (out / f"{label}.clip.json").write_text(text)
    measure["clip_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    (out / f"{label}.measure.json").write_text(json.dumps(measure, indent=1))
    print(json.dumps(measure, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
