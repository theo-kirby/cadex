#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The same grid, solved by somebody else's code (S0's second method).

``analysis/cadex_stress.py`` is a few hundred lines of linear elasticity
written here, and the failure mode of a few hundred lines written here is
not that they crash -- it is that they produce a plausible number nobody
can check. ADR-129 is the standing lesson in this repository: a
plausible-looking result survived being written down and was wrong, and
what caught it was comparing against a second method.

This is that second method. It writes the *identical* grid -- the same
nodes, the same elements, the same corners in the same order, the same
supports and the same nodal forces -- as a CalculiX ``.inp`` deck, runs
``ccx`` as a subprocess, and reads the numbers back out of the ``.dat``
file. If the two disagree by more than a fraction of a percent, one of them
is wrong, and the point of the exercise is that you find out which.

**CalculiX is GPL-2, and that is why this is a subprocess.** ``ccx`` is
never linked and never imported; a text deck goes in and a text result
comes out, which is arm's length in the sense the licence means and is how
FreeCAD's FEM workbench drove it too. ``docs/PROVENANCE.md`` §1 puts the
engine side at LGPL and ``AGENTS.md`` calls the GPL boundary one-way and
hard. Nothing here imports ``ccx``, and nothing here may.

**It is not in the payload and does not need to be.** ``calculix`` is in
``pixi.toml`` and ``.pixi/envs/default/bin/ccx`` exists, but
``package/engine/build_engine_payload.sh`` keeps exactly four binaries and
``ccx`` is not one of them. That is correct and should stay that way: the
cross-check is a thing you run while developing a load case, not a thing a
user's laptop performs.

Reads ``.dat`` rather than ``.frd`` deliberately. ``*NODE PRINT`` and
``*EL PRINT`` write whitespace-separated text; ``.frd`` is a fixed-column
format whose parser is the kind of code that is wrong for a year.

Usage::

    python analysis/calculix.py bracket.stl --load-case loads.json \\
        --element-mm 2.0
    python analysis/calculix.py --self-check
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cadex_stress as stress  # noqa: E402

COMPARISON_SCHEMA = "cadex-analysis-crosscheck-v1"

#: ``_NODE_SIGNS`` order -> Abaqus/CalculiX C3D8 order. Nodes 1-4 are one
#: face taken so that the right-hand rule points at nodes 5-8; ours are
#: ordered ``i + 2j + 4k``, so the two middle nodes of each face swap.
#: ``ccx`` rejects a deck whose Jacobian comes out negative, so this
#: permutation is checked by the tool it is written for.
_ABAQUS_ORDER = (0, 1, 3, 2, 4, 5, 7, 6)

#: CalculiX prints ``sxx, syy, szz, sxy, sxz, syz``; this file's own order is
#: ``sxx, syy, szz, sxy, syz, szx``. The last two are swapped, and swapping
#: them silently is exactly the kind of thing that makes two solvers agree
#: on von Mises and disagree on everything else.
_CCX_TO_LOCAL = (0, 1, 2, 3, 5, 4)

#: What "the two agree" means. Two implementations of the same element on
#: the same grid should differ only by the linear solve's own tolerance, so
#: this is loose by three orders of magnitude and still catches a sign.
DISPLACEMENT_TOLERANCE = 1.0e-3
STRESS_TOLERANCE = 5.0e-3


class CalculiXError(RuntimeError):
    """A refusal, with a sentence a person can act on."""


def find_ccx(explicit: str | None = None) -> str:
    """Where ``ccx`` is, or a refusal that says how to get one."""

    if explicit:
        if not Path(explicit).is_file():
            raise CalculiXError(f"{explicit} is not a file.")
        return explicit
    found = shutil.which("ccx") or shutil.which("ccx_2.23")
    if found:
        return found
    local = Path(__file__).resolve().parents[1] / ".pixi/envs/default/bin/ccx"
    if local.is_file():
        return str(local)
    raise CalculiXError(
        "No `ccx` on PATH. It is in this repository's pixi environment "
        "(`pixi.toml` carries `calculix`), so `pixi run python "
        "analysis/calculix.py ...` finds it; or install CalculiX and pass "
        "`--ccx`."
    )


# ---------------------------------------------------------------------------
# Writing the deck.
# ---------------------------------------------------------------------------


def write_deck(result: stress.Result, load_case: dict[str, Any], path: Path, *,
               element_type: str = "C3D8I") -> dict[str, Any]:
    """The grid ``cadex_stress`` just solved, as a CalculiX input deck.

    Everything is taken off the :class:`~cadex_stress.Result` rather than
    recomputed from the load case: the same solid cells after pruning, the
    same node ids, the same fixed degrees of freedom and -- this is the part
    that matters -- **the same assembled nodal force vector**. A cross-check
    that re-derived the loads from the declaration would be checking two
    load interpretations as well as two solvers, and a disagreement would
    not say which.
    """

    material = result.material
    grid = result.grid
    positions = grid.node_positions()

    used = np.unique(result.element_dofs[:, ::3] // 3)
    renumber = np.zeros(len(positions), dtype=np.int64)
    renumber[used] = np.arange(1, len(used) + 1)

    lines: list[str] = [
        "*HEADING",
        "cadex analysis S0 cross-check -- see analysis/calculix.py",
        "*NODE, NSET=Nall",
    ]
    for node in used:
        x, y, z = positions[node]
        lines.append(f"{renumber[node]}, {x:.10g}, {y:.10g}, {z:.10g}")

    lines.append(f"*ELEMENT, TYPE={element_type}, ELSET=Eall")
    corners = result.element_dofs[:, ::3] // 3
    for index, row in enumerate(corners, start=1):
        ordered = ", ".join(str(int(renumber[row[corner]])) for corner in _ABAQUS_ORDER)
        lines.append(f"{index}, {ordered}")

    lines += [
        "*MATERIAL, NAME=DECLARED",
        "*ELASTIC",
        f"{material.youngs_modulus_mpa:.10g}, {material.poissons_ratio:.10g}",
        "*SOLID SECTION, ELSET=Eall, MATERIAL=DECLARED",
        "*STEP",
        "*STATIC",
        "*BOUNDARY",
    ]

    # The fixed set, carried off the solve rather than re-derived. `Result`
    # records exactly which degrees of freedom were withheld, so the deck
    # holds the structure the same way rather than the same way *again*.
    held = 0
    for node in used:
        for axis in range(3):
            if result.fixed_dofs[3 * int(node) + axis]:
                lines.append(f"{renumber[node]}, {axis + 1}, {axis + 1}")
                held += 1
    if not held:
        raise CalculiXError("The deck would hold nothing; refusing to write it.")

    forces = _nodal_forces(result, load_case)
    lines.append("*CLOAD")
    applied = 0
    for node in used:
        for axis in range(3):
            value = forces[3 * int(node) + axis]
            if value:
                lines.append(f"{renumber[node]}, {axis + 1}, {value:.10g}")
                applied += 1

    lines += [
        "*NODE PRINT, NSET=Nall",
        "U",
        "*EL PRINT, ELSET=Eall",
        "S",
        "*END STEP",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "nodes": int(len(used)),
        "elements": int(len(corners)),
        "held_dofs": held,
        "loaded_dofs": applied,
        "element_type": element_type,
        "renumber": renumber,
        "used": used,
    }


def _nodal_forces(result: stress.Result, load_case: dict[str, Any]) -> np.ndarray:
    """The same force vector ``solve`` assembled, rebuilt from its inputs.

    Rebuilt rather than carried because it is cheap and because doing it
    here keeps ``Result`` about the answer rather than about the question.
    The call goes through ``cadex_stress`` itself, so there is one
    implementation of what a declared load means.
    """

    return stress.assemble_forces(result.grid, result.material, load_case,
                                  result.element_dofs)


# ---------------------------------------------------------------------------
# Running it, and reading it back.
# ---------------------------------------------------------------------------


def _run(ccx: str, deck: Path) -> str:
    started = time.monotonic()
    process = subprocess.run(
        [ccx, deck.stem],
        cwd=str(deck.parent),
        capture_output=True,
        text=True,
        timeout=3600,
        env={**os.environ, "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "4")},
    )
    wall = time.monotonic() - started
    dat = deck.with_suffix(".dat")
    if not dat.is_file():
        raise CalculiXError(
            f"ccx wrote no .dat file (exit {process.returncode}).\n"
            f"{process.stdout[-2000:]}\n{process.stderr[-2000:]}"
        )
    text = dat.read_text(encoding="utf-8", errors="replace")
    if "displacements" not in text:
        raise CalculiXError(
            f"ccx wrote a .dat with no displacements (exit {process.returncode}). "
            f"{process.stdout[-2000:]}"
        )
    _run.wall = wall  # type: ignore[attr-defined]
    return text


def parse_dat(text: str) -> dict[str, np.ndarray]:
    """Displacements by node and stresses by element, out of a ``.dat``.

    The format is a blank line, a title line naming the quantity, a blank
    line, then rows. Rows for ``U`` are ``node ux uy uz``; rows for ``S``
    are ``element point sxx syy szz sxy sxz syz``. Parsed by looking at the
    row width rather than by counting lines, so a CalculiX that adds a
    header line does not silently shift the answer.
    """

    displacements: list[list[float]] = []
    stresses: list[list[float]] = []
    mode = ""
    for line in text.splitlines():
        lowered = line.lower()
        if "displacements" in lowered:
            mode = "u"
            continue
        if "stresses" in lowered:
            mode = "s"
            continue
        parts = line.split()
        if not parts:
            continue
        try:
            values = [float(token) for token in parts]
        except ValueError:
            mode = ""
            continue
        if mode == "u" and len(values) == 4:
            displacements.append(values)
        elif mode == "s" and len(values) == 8:
            stresses.append(values)
    if not displacements:
        raise CalculiXError("No displacement rows in the .dat file.")
    if not stresses:
        raise CalculiXError("No stress rows in the .dat file.")
    return {
        "displacement": np.asarray(displacements, dtype=float),
        "stress": np.asarray(stresses, dtype=float),
    }


def cross_check(solid: Path, load_case: dict[str, Any], *, element_mm: float,
                ccx: str | None = None, element_type: str = "C3D8I",
                keep: Path | None = None) -> dict[str, Any]:
    """Solve once here, once in CalculiX, and report how far apart they are."""

    binary = find_ccx(ccx)
    material = stress.Material.from_mapping(load_case.get("material"))
    triangles, _ = stress.read_solid(solid)
    grid = stress.voxelise(triangles, element_mm)
    mine = stress.solve(grid, material, load_case,
                        incompatible=element_type.upper() == "C3D8I")

    directory = Path(tempfile.mkdtemp(prefix="cadex-ccx-"))
    try:
        deck = directory / "crosscheck.inp"
        written = write_deck(mine, load_case, deck, element_type=element_type)
        text = _run(binary, deck)
        parsed = parse_dat(text)

        # Displacements: renumbered back onto this file's node ids.
        theirs = np.zeros_like(mine.displacement)
        inverse = {int(written["renumber"][node]): int(node)
                   for node in written["used"]}
        for row in parsed["displacement"]:
            theirs[inverse[int(row[0])]] = row[1:4]

        mine_norm = np.linalg.norm(mine.displacement, axis=1)
        their_norm = np.linalg.norm(theirs, axis=1)
        scale = float(mine_norm.max()) or 1.0
        displacement_error = float(np.abs(mine_norm - their_norm).max() / scale)

        # Stresses: CalculiX prints per integration point, so take each
        # element's mean and compare against this file's centroid value --
        # which for a trilinear element is the same quantity by a different
        # route, and is therefore a real comparison rather than a rounding.
        rows = parsed["stress"]
        element_ids = rows[:, 0].astype(int) - 1
        components = rows[:, 2:8][:, list(_CCX_TO_LOCAL)]
        their_centroid = np.zeros((len(mine.element_dofs), 6), dtype=float)
        counts = np.zeros(len(mine.element_dofs), dtype=float)
        np.add.at(their_centroid, element_ids, components)
        np.add.at(counts, element_ids, 1.0)
        their_centroid /= np.maximum(counts, 1.0)[:, None]

        their_vm = stress.von_mises(their_centroid)
        mine_vm = stress.von_mises(mine.centroid_stress_mpa)
        stress_scale = float(np.abs(mine_vm).max()) or 1.0
        stress_error = float(np.abs(mine_vm - their_vm).max() / stress_scale)
        component_error = float(
            np.abs(mine.centroid_stress_mpa - their_centroid).max() / stress_scale)

        if keep:
            keep.mkdir(parents=True, exist_ok=True)
            for name in ("crosscheck.inp", "crosscheck.dat"):
                candidate = directory / name
                if candidate.is_file():
                    shutil.copy2(candidate, keep / name)

        return {
            "schema": COMPARISON_SCHEMA,
            "solid": str(solid),
            "element_mm": float(grid.spacing.mean()),
            "deck": {key: value for key, value in written.items()
                     if key not in {"renumber", "used"}},
            "ccx": {
                "binary": binary,
                "version": _ccx_version(binary),
                "wall_time_s": getattr(_run, "wall", None),
                "kept": str(keep) if keep else None,
            },
            "cadex_stress": {
                "max_displacement_mm": mine.max_displacement_mm,
                "peak_centroid_von_mises_mpa": float(mine_vm.max()),
                "solver": dict(mine.solver),
            },
            "calculix": {
                "max_displacement_mm": float(their_norm.max()),
                "peak_centroid_von_mises_mpa": float(their_vm.max()),
                "integration_points": int(len(rows)),
            },
            "difference": {
                "displacement_fraction": displacement_error,
                "von_mises_fraction": stress_error,
                "worst_component_fraction": component_error,
                "displacement_tolerance": DISPLACEMENT_TOLERANCE,
                "stress_tolerance": STRESS_TOLERANCE,
            },
            "agrees": (displacement_error <= DISPLACEMENT_TOLERANCE
                       and stress_error <= STRESS_TOLERANCE),
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
            },
            "cadex_importable": stress._cadex_importable(),
        }
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def _ccx_version(binary: str) -> str:
    try:
        out = subprocess.run([binary, "-v"], capture_output=True, text=True,
                             timeout=30)
        return (out.stdout or out.stderr).strip().splitlines()[-1]
    except Exception:  # pragma: no cover - a version string is not the point
        return "unknown"


def run_self_check(element_mm: float = 2.5, ccx: str | None = None) -> dict[str, Any]:
    """The cantilever, both ways, plus what beam theory says about it."""

    case = stress.cantilever_case()
    with tempfile.TemporaryDirectory() as directory:
        path = stress.write_binary_stl(
            stress.box_triangles(case["size_mm"]), Path(directory) / "cantilever.stl")
        report = cross_check(path, case["load_case"], element_mm=element_mm, ccx=ccx)
    report["closed_form"] = {
        "tip_deflection_mm": case["tip_deflection_mm"],
        "midspan_bending_stress_mpa": case["midspan_bending_stress_mpa"],
    }
    return report


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="calculix.py",
        description="Solve the same grid in CalculiX and report the difference.")
    parser.add_argument("solid", nargs="?", type=Path)
    parser.add_argument("--load-case", type=Path)
    parser.add_argument("--element-mm", type=float, default=2.0)
    parser.add_argument("--ccx", default=None, help="path to the ccx binary")
    parser.add_argument("--element", choices=("C3D8I", "C3D8"), default="C3D8I")
    parser.add_argument("--keep", type=Path, default=None,
                        help="keep the .inp and .dat here")
    parser.add_argument("--self-check", action="store_true")
    options = parser.parse_args(list(argv[1:]))

    try:
        if options.self_check:
            report = run_self_check(element_mm=options.element_mm, ccx=options.ccx)
        else:
            if options.solid is None or options.load_case is None:
                parser.error("a solid and --load-case are required")
            raw = json.loads(options.load_case.read_text(encoding="utf-8"))
            report = cross_check(options.solid, raw, element_mm=options.element_mm,
                                 ccx=options.ccx, element_type=options.element,
                                 keep=options.keep)
    except (CalculiXError, stress.StressError) as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2

    if not report.get("agrees"):
        print("warning: the two solvers disagree beyond tolerance; read the "
              "`difference` block before trusting either.", file=sys.stderr)
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("agrees") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
