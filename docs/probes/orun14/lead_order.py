"""orun14 P2 (O3): why LH-first strides read transverse. Crosses each stride's hind order with its fore order.

usage: python3 docs/probes/orun14/lead_order.py GALLOP_TASK_JSON EVALUATION_DIR [EVALUATION_DIR ...]

``legs.footfall_kind`` reads a stride as rotary when the fore paw that
lands right after the hind pair is on the same side as the second hind
(LH RH RF LF), and transverse when it is on the other side (LH RH LF RF).
So with the fore pair's order fixed, the hind pair's order alone decides
the kind: whichever hind lands first, one of the two hind orders is
always transverse.

**The clip.** From the bundle's ``reference`` block: each foot's
touch-down phase, and the order the clip asks for, with which pair leads.

**Each evaluation.** Over every stride of every seed (``flight_metrics``,
after ``legs.SETTLE_S``) whose four first landings are distinct: the
first hind (LH or RH) against the first fore after the hind pair (LF or
RF), with ``legs.stride_kind`` in each cell; then the share of strides on
which the fore pair keeps the clip's lead and the hind pair keeps the
clip's lead. Strides whose hinds do not land consecutively (a fore
between them) are counted as ``split``. Standard library only.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "orun12"))

from legs import SETTLE_S, stride_kind  # noqa: E402

NAME = {"c_paw_fl": "LF", "c_paw_fr": "RF", "c_paw_hl": "LH", "c_paw_hr": "RH"}


def clip_order(task: Path):
    ref = json.loads(task.read_text())["reference"]
    off = ref["parameters"]["phase_offsets"]
    # each pair's first paw is the one its partner follows within half a cycle
    hind0 = "LH" if (off["RH"] - off["LH"]) % 1.0 < 0.5 else "RH"
    fore0 = "LF" if (off["RF"] - off["LF"]) % 1.0 < 0.5 else "RF"
    order = sorted(("LH", "RH", "LF", "RF"), key=lambda k: (off[k] - off[hind0]) % 1.0)
    print(f"## The clip ({ref['label']})\n")
    print("phase offsets " + ", ".join(f"{k} {off[k]:.3f}" for k in ("LH", "RH", "LF", "RF")))
    print(f"order from the first hind: {' '.join(order)}; {hind0} first of the hinds, "
          f"{fore0} first of the fores\n")
    return hind0, fore0


def hind_then_fore(order):
    """(first hind, first fore after the hind pair) for a cyclic order, or None if the hinds are split."""

    names = [NAME[p] for p in order]
    for i, n in enumerate(names):
        nxt = names[(i + 1) % 4]
        if n in ("LH", "RH") and nxt in ("LH", "RH") and nxt != n:
            return n, names[(i + 2) % 4]
    return None


def eval_report(path: Path, clip):
    report = json.loads((path / "evaluation.json").read_text())
    cells = collections.Counter()
    split = 0
    for s in report["seeds"]:
        d = s["detail"]
        for st in d["flight"]["strides"]:
            if st["start_s"] < SETTLE_S or len(st["order"]) != 4:
                continue
            kind = stride_kind(st, d["feet"])
            if kind == "tied":
                cells["tied"] += 1
                continue
            pair = hind_then_fore(st["order"])
            if pair is None:
                split += 1
                continue
            cells[(pair, kind)] += 1
    ordered = sum(v for k, v in cells.items() if k != "tied")
    print(f"## {path.name}\n")
    print("| first hind \\ first fore | LF | RF |")
    print("|---|---|---|")
    for h in ("LH", "RH"):
        row = []
        for f in ("LF", "RF"):
            parts = [f"{v} {k[1]}" for k, v in cells.items() if k != "tied" and k[0] == (h, f)]
            row.append(", ".join(parts) or "0")
        print(f"| {h} | {' | '.join(row)} |")
    fore_keep = sum(v for k, v in cells.items() if k != "tied" and k[0][1] == clip[1])
    hind_keep = sum(v for k, v in cells.items() if k != "tied" and k[0][0] == clip[0])
    if ordered:
        print(f"\n{ordered} ordered strides, {cells['tied']} tied, {split} split; fore keeps the clip's "
              f"{clip[1]}-first on {fore_keep / ordered:.2f}, hind keeps {clip[0]}-first on "
              f"{hind_keep / ordered:.2f}\n")
    else:
        print(f"\nno ordered strides, {cells['tied']} tied, {split} split\n")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    clip = clip_order(Path(argv[0]))
    for path in argv[1:]:
        eval_report(Path(path), clip)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
