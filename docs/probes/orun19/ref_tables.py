"""How a motion policy follows its reference's footfall, from the engine's evaluations.

usage: python3 docs/probes/orun19/ref_tables.py EVAL_DIR [EVAL_DIR ...]

Reads only each ``evaluation.json``'s per-seed ``detail.reference`` (the
engine's ``CadexEvaluation`` reading against the task's reference, anchored on
the left hind): per foot, the median phase error (share of a stride) and the
missed strides summed over seeds against the strides counted; the policy's
stride Hz against the reference's; and each foot's duty factor against the
reference's. Seeds without a reference block are counted and skipped.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ORDER = ("LF", "RF", "LH", "RH")


def med(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def fmt(value, spec=".2f"):
    return "–" if value is None else format(value, spec)


def read(out: Path) -> dict:
    report = json.loads((out / "evaluation.json").read_text())
    refs = [s["detail"].get("reference") for s in report["seeds"]]
    refs = [r for r in refs if r and r.get("feet")]
    row = {"cmd": report.get("judged_command_mm_s"), "seeds": len(report["seeds"]), "read": len(refs),
           "strides": sum(r.get("strides") or 0 for r in refs),
           "hz": med(r.get("stride_hz") for r in refs), "ref_hz": med(r.get("reference_stride_hz") for r in refs)}
    for foot in ORDER:
        feet = [r["feet"].get(foot) for r in refs if r["feet"].get(foot)]
        row[foot] = {"phase": med(f.get("phase_error") for f in feet),
                     "missed": sum(f.get("missed_strides") or 0 for f in feet),
                     "duty": med(f.get("duty_factor") for f in feet),
                     "ref_duty": med(f.get("reference_duty_factor") for f in feet)}
    return row


def main(argv: list[str]) -> int:
    rows = [read(Path(a).expanduser()) for a in argv]
    print("| command mm/s | " + " | ".join(str(r["cmd"]) for r in rows) + " |")
    print("|---|" + "---|" * len(rows))
    print("| seeds read | " + " | ".join(f"{r['read']}/{r['seeds']}" for r in rows) + " |")
    print("| stride Hz, policy / reference (seed median) | "
          + " | ".join(f"{fmt(r['hz'])} / {fmt(r['ref_hz'])}" for r in rows) + " |")
    print("| phase error LF / RF / LH / RH (stride share, median) | "
          + " | ".join(" / ".join(fmt(r[f]["phase"]) for f in ORDER) for r in rows) + " |")
    print("| missed strides LF / RF / LH / RH, of strides counted | "
          + " | ".join(" / ".join(str(r[f]["missed"]) for f in ORDER) + f" of {r['strides']}" for r in rows) + " |")
    print("| duty factor LF / RF / LH / RH (reference) | "
          + " | ".join(" / ".join(fmt(r[f]["duty"]) for f in ORDER)
                       + f" ({fmt(r['LF']['ref_duty'])})" for r in rows) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
