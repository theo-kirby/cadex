# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The parts-library catalog: real component specs as data (ADR-181).

One spec row per part number, one table per family. The generators in
``cadex_library_api`` build geometry *from* these rows, so the row is the
single place a dimension lives and the tests pin each row against the
standard or datasheet it came from. The fidelity contract is
**interface-exact, cosmetically simple**: hole positions, envelopes, bores
and shaft positions are the standard's numbers; thread helixes, knurls and
logos are deliberately not modelled.

Like ``CadexBoards`` and ``CadexMounts``, this module imports nothing from
FreeCAD and touches no kernel object, so the stubbed pytest suite exercises
it exactly as it runs in the sandboxed worker.

Units: millimetres throughout, the engine's own unit. Torque data, where a
family carries it, is N*mm — converted here, once, from whatever unit the
datasheet states, so no script and no agent ever repeats the conversion.

A spec correction is an engine change: it moves geometry under an unchanged
script revision, exactly as a kernel upgrade would, and the accepted
digest is what detects the drift (ADR-181).
"""

from __future__ import annotations

from typing import Any, Mapping

__all__ = [
    "CatalogError",
    "METRIC_THREADS",
    "SOCKET_HEAD_SCREWS",
    "COUNTERSUNK_SCREWS",
    "HEX_NUTS",
    "NYLOC_NUTS",
    "FLAT_WASHERS",
    "HEAT_SET_INSERTS",
    "BALL_BEARINGS",
    "SERVOS",
    "MICRO_HORNS",
    "MICRO_HORN_HUB",
    "KG_CM_TO_NMM",
    "STEEL_DENSITY_KG_M3",
    "BRASS_DENSITY_KG_M3",
    "catalog_families",
    "thread_spec",
    "bearing_spec",
    "servo_spec",
    "normalise_thread_size",
    "normalise_bearing_code",
    "normalise_servo_sku",
]


class CatalogError(ValueError):
    """A catalog lookup names a part number the catalog does not carry."""


#: Steel fasteners and bearings; brass heat-set inserts. Used by the
#: generators as the default ``density_kg_m3`` an ``assembly.body`` wants.
STEEL_DENSITY_KG_M3 = 7850.0
BRASS_DENSITY_KG_M3 = 8500.0


# --------------------------------------------------------------------------
# ISO metric coarse threads.
#
# pitch_mm / minor_dia_mm: ISO 261 / ISO 724 basic profile.
# tap_drill_mm: standard tapping drill for ~75% thread engagement.
# clearance holes: ISO 273 close (H12) and medium fit.
# --------------------------------------------------------------------------
METRIC_THREADS: Mapping[str, Mapping[str, float]] = {
    "m2": {
        "nominal_dia_mm": 2.0,
        "pitch_mm": 0.4,
        "minor_dia_mm": 1.567,
        "tap_drill_mm": 1.6,
        "clearance_close_mm": 2.2,
        "clearance_normal_mm": 2.4,
    },
    "m2.5": {
        "nominal_dia_mm": 2.5,
        "pitch_mm": 0.45,
        "minor_dia_mm": 2.013,
        "tap_drill_mm": 2.05,
        "clearance_close_mm": 2.7,
        "clearance_normal_mm": 2.9,
    },
    "m3": {
        "nominal_dia_mm": 3.0,
        "pitch_mm": 0.5,
        "minor_dia_mm": 2.459,
        "tap_drill_mm": 2.5,
        "clearance_close_mm": 3.2,
        "clearance_normal_mm": 3.4,
    },
    "m4": {
        "nominal_dia_mm": 4.0,
        "pitch_mm": 0.7,
        "minor_dia_mm": 3.242,
        "tap_drill_mm": 3.3,
        "clearance_close_mm": 4.3,
        "clearance_normal_mm": 4.5,
    },
    "m5": {
        "nominal_dia_mm": 5.0,
        "pitch_mm": 0.8,
        "minor_dia_mm": 4.134,
        "tap_drill_mm": 4.2,
        "clearance_close_mm": 5.3,
        "clearance_normal_mm": 5.5,
    },
    "m6": {
        "nominal_dia_mm": 6.0,
        "pitch_mm": 1.0,
        "minor_dia_mm": 4.917,
        "tap_drill_mm": 5.0,
        "clearance_close_mm": 6.4,
        "clearance_normal_mm": 6.6,
    },
    "m8": {
        "nominal_dia_mm": 8.0,
        "pitch_mm": 1.25,
        "minor_dia_mm": 6.647,
        "tap_drill_mm": 6.8,
        "clearance_close_mm": 8.4,
        "clearance_normal_mm": 9.0,
    },
}


# --------------------------------------------------------------------------
# ISO 4762 hexagon socket head cap screws.
# head_dia_mm = dk (max), head_height_mm = k, socket_mm = s (hex across
# flats — data only; the recess is not modelled).
# --------------------------------------------------------------------------
SOCKET_HEAD_SCREWS: Mapping[str, Mapping[str, float]] = {
    "m2": {"head_dia_mm": 3.8, "head_height_mm": 2.0, "socket_mm": 1.5},
    "m2.5": {"head_dia_mm": 4.5, "head_height_mm": 2.5, "socket_mm": 2.0},
    "m3": {"head_dia_mm": 5.5, "head_height_mm": 3.0, "socket_mm": 2.5},
    "m4": {"head_dia_mm": 7.0, "head_height_mm": 4.0, "socket_mm": 3.0},
    "m5": {"head_dia_mm": 8.5, "head_height_mm": 5.0, "socket_mm": 4.0},
    "m6": {"head_dia_mm": 10.0, "head_height_mm": 6.0, "socket_mm": 5.0},
    "m8": {"head_dia_mm": 13.0, "head_height_mm": 8.0, "socket_mm": 6.0},
}


# --------------------------------------------------------------------------
# DIN 7991 / ISO 10642 countersunk socket screws, 90 degree head.
# head_dia_mm = dk (actual head diameter), head_height_mm = k.
# --------------------------------------------------------------------------
COUNTERSUNK_SCREWS: Mapping[str, Mapping[str, float]] = {
    "m2": {"head_dia_mm": 3.8, "head_height_mm": 1.2},
    "m2.5": {"head_dia_mm": 4.7, "head_height_mm": 1.5},
    "m3": {"head_dia_mm": 6.0, "head_height_mm": 1.7},
    "m4": {"head_dia_mm": 8.0, "head_height_mm": 2.3},
    "m5": {"head_dia_mm": 10.0, "head_height_mm": 2.8},
    "m6": {"head_dia_mm": 12.0, "head_height_mm": 3.3},
    "m8": {"head_dia_mm": 16.0, "head_height_mm": 4.4},
}


# --------------------------------------------------------------------------
# ISO 4032 style 1 hex nuts. across_flats_mm = s, height_mm = m.
# --------------------------------------------------------------------------
HEX_NUTS: Mapping[str, Mapping[str, float]] = {
    "m2": {"across_flats_mm": 4.0, "height_mm": 1.6},
    "m2.5": {"across_flats_mm": 5.0, "height_mm": 2.0},
    "m3": {"across_flats_mm": 5.5, "height_mm": 2.4},
    "m4": {"across_flats_mm": 7.0, "height_mm": 3.2},
    "m5": {"across_flats_mm": 8.0, "height_mm": 4.7},
    "m6": {"across_flats_mm": 10.0, "height_mm": 5.2},
    "m8": {"across_flats_mm": 13.0, "height_mm": 6.8},
}


# --------------------------------------------------------------------------
# DIN 985 nylon-insert lock nuts. Same across-flats as the plain hex nut;
# taller for the insert collar. The collar is modelled as part of the hex
# body (interface-exact: the envelope is right, the nylon ring is not
# distinguished).
# --------------------------------------------------------------------------
NYLOC_NUTS: Mapping[str, Mapping[str, float]] = {
    "m3": {"across_flats_mm": 5.5, "height_mm": 4.0},
    "m4": {"across_flats_mm": 7.0, "height_mm": 5.0},
    "m5": {"across_flats_mm": 8.0, "height_mm": 5.0},
    "m6": {"across_flats_mm": 10.0, "height_mm": 6.0},
    "m8": {"across_flats_mm": 13.0, "height_mm": 8.0},
}


# --------------------------------------------------------------------------
# ISO 7089 flat washers, normal series.
# --------------------------------------------------------------------------
FLAT_WASHERS: Mapping[str, Mapping[str, float]] = {
    "m2": {"bore_mm": 2.2, "od_mm": 5.0, "thickness_mm": 0.3},
    "m2.5": {"bore_mm": 2.7, "od_mm": 6.0, "thickness_mm": 0.5},
    "m3": {"bore_mm": 3.2, "od_mm": 7.0, "thickness_mm": 0.5},
    "m4": {"bore_mm": 4.3, "od_mm": 9.0, "thickness_mm": 0.8},
    "m5": {"bore_mm": 5.3, "od_mm": 10.0, "thickness_mm": 1.0},
    "m6": {"bore_mm": 6.4, "od_mm": 12.0, "thickness_mm": 1.6},
    "m8": {"bore_mm": 8.4, "od_mm": 16.0, "thickness_mm": 1.6},
}


# --------------------------------------------------------------------------
# Brass heat-set inserts for plastic, the tapered/knurled kind 3D printing
# standardised on (Ruthex/CNC Kitchen size codes; lengths and pilot holes
# from the vendors' own tables — cnckitchen.store product pages and the
# ruthex drill-set listing, 2026-08). ``hole_dia_mm`` is the vendor's pilot
# hole for the printed boss; ``length_mm`` the standard length,
# ``short_length_mm`` the short variant sold beside it. ``od_mm`` is the
# *nominal* knurl diameter: no vendor publishes the true knurl OD (it bites
# past the pilot hole), so it is stated slightly above the pilot hole and
# is a modelling envelope, not a datasheet figure.
# --------------------------------------------------------------------------
HEAT_SET_INSERTS: Mapping[str, Mapping[str, float]] = {
    "m2": {"od_mm": 3.6, "length_mm": 4.0, "short_length_mm": 3.0, "hole_dia_mm": 3.2},
    "m2.5": {"od_mm": 4.5, "length_mm": 5.7, "short_length_mm": 4.0, "hole_dia_mm": 4.0},
    "m3": {"od_mm": 4.6, "length_mm": 5.7, "short_length_mm": 4.0, "hole_dia_mm": 4.0},
    "m4": {"od_mm": 6.3, "length_mm": 8.1, "short_length_mm": 4.0, "hole_dia_mm": 5.6},
    "m5": {"od_mm": 7.1, "length_mm": 9.5, "short_length_mm": 5.8, "hole_dia_mm": 6.4},
}


# --------------------------------------------------------------------------
# Deep-groove ball bearings, the common metric and MR miniature series.
# bore x od x width per the manufacturer tables (SKF/SMB/Nodes, 2026-08).
# A ZZ/2RS suffix is stripped by ``normalise_bearing_code`` — dimensionally
# free on the 600/6000/6800 series, but NOT on the miniature ribbon series:
# open 688/MR63/MR85/MR105/MR128 are narrower than their shielded twins.
# These rows carry the SHIELDED (ZZ) widths, because shielded is what a
# robot build actually buys; the open widths are 4 / 2 / 2 / 3 / 2.5.
# --------------------------------------------------------------------------
BALL_BEARINGS: Mapping[str, Mapping[str, float]] = {
    "623": {"bore_mm": 3.0, "od_mm": 10.0, "width_mm": 4.0},
    "624": {"bore_mm": 4.0, "od_mm": 13.0, "width_mm": 5.0},
    "625": {"bore_mm": 5.0, "od_mm": 16.0, "width_mm": 5.0},
    "626": {"bore_mm": 6.0, "od_mm": 19.0, "width_mm": 6.0},
    "608": {"bore_mm": 8.0, "od_mm": 22.0, "width_mm": 7.0},
    "688": {"bore_mm": 8.0, "od_mm": 16.0, "width_mm": 5.0},
    "mr63": {"bore_mm": 3.0, "od_mm": 6.0, "width_mm": 2.5},
    "mr85": {"bore_mm": 5.0, "od_mm": 8.0, "width_mm": 2.5},
    "mr105": {"bore_mm": 5.0, "od_mm": 10.0, "width_mm": 4.0},
    "mr115": {"bore_mm": 5.0, "od_mm": 11.0, "width_mm": 4.0},
    "mr128": {"bore_mm": 8.0, "od_mm": 12.0, "width_mm": 3.5},
    "6000": {"bore_mm": 10.0, "od_mm": 26.0, "width_mm": 8.0},
    "6001": {"bore_mm": 12.0, "od_mm": 28.0, "width_mm": 8.0},
    "6800": {"bore_mm": 10.0, "od_mm": 19.0, "width_mm": 5.0},
    "6801": {"bore_mm": 12.0, "od_mm": 21.0, "width_mm": 5.0},
}


# --------------------------------------------------------------------------
# Hobby servos, the four classes a robot build reaches for (ADR-181).
#
# Sources (researched 2026-08, cited per row below): the TowerPro official
# product pages, the classic SG90 datasheet, the AUS Electronics TA0132
# measured drawing (the only source that dimensions the micro mounting
# holes), the Electronicos Caldas MG90S datasheet, the Handsontec MG996R
# drawing, and the official Dongguan Dsservo DS3218 datasheet.
#
# Field conventions:
# - case_height_mm is bottom -> case top, spline excluded.
# - flange_height_mm is bottom -> the mounting flange's UNDERSIDE.
# - hole_spacing_mm is lengthwise hole-centre spacing; a
#   hole_cross_spacing_mm of 0 means one hole per tab on the centreline
#   (micro pattern), non-zero means two per tab (standard pattern).
# - shaft_offset_from_front_mm is the output axis from the front face.
# - stall_torque rows are the manufacturer's kg*cm at the voltages the
#   manufacturer actually rates; nothing is interpolated.
# - approximate=True marks a value no datasheet dimensions (flagged in the
#   research): MG90S holes/tab/shaft carry the measured SG90 footprint the
#   bracket vendors treat as shared; MG996R/DS3218 tab thickness, hole
#   diameter, shaft offset and the DS3218 case/spline split are stated
#   nominally from the 40x20 standard pattern. Interface-critical numbers
#   that ARE dimensioned (hole spacings, flange heights, envelopes) are the
#   drawings' own.
# --------------------------------------------------------------------------
KG_CM_TO_NMM = 98.0665

SERVOS: Mapping[str, Mapping[str, Any]] = {
    # TowerPro SG90, analog micro. towerpro.com.tw/product/sg90-analog/;
    # AUS TA0132 measured drawing (holes 2.2 at 29.0, tab 2.4, flange 15.9,
    # shaft 8.75 from front, spline +3.6). Torque/speed are TowerPro's
    # 4.8 V figures; no manufacturer 6 V rating exists. Spline tooth count
    # is disputed (20 vs 21) across sources; 21 is the horn-market figure.
    "sg90": {
        "family": "micro",
        "body_length_mm": 22.7,
        "body_width_mm": 12.1,
        "case_height_mm": 27.1,
        "overall_tab_length_mm": 32.4,
        "tab_thickness_mm": 2.4,
        "flange_height_mm": 15.9,
        "hole_dia_mm": 2.2,
        "hole_spacing_mm": 29.0,
        "hole_cross_spacing_mm": 0.0,
        "shaft_offset_from_front_mm": 8.75,
        "spline_dia_mm": 4.8,
        "spline_height_mm": 3.6,
        "spline_teeth": 21,
        "mass_g": 9.0,
        "travel_degrees": 180.0,
        "voltage_min_v": 4.8,
        "voltage_max_v": 6.0,
        "stall_torque": [{"volts": 4.8, "kg_cm": 1.8}],
        "speed": [{"volts": 4.8, "s_per_60_deg": 0.12}],
        "approximate": [],
    },
    # TowerPro MG90S, metal-gear micro. towerpro.com.tw/product/mg90s-3/
    # (13.4 g; 1.8 kg*cm @4.8 V, 2.2 @6.6 V; 0.10/0.08 s per 60 deg);
    # Electronicos Caldas datasheet (32.5 over tabs). Holes, tab thickness
    # and shaft offset are the measured SG90 footprint — no MG90S datasheet
    # dimensions them, and bracket vendors sell one bracket for both.
    "mg90s": {
        "family": "micro",
        "body_length_mm": 22.8,
        "body_width_mm": 12.2,
        "case_height_mm": 28.4,
        "overall_tab_length_mm": 32.5,
        "tab_thickness_mm": 2.4,
        "flange_height_mm": 18.5,
        "hole_dia_mm": 2.2,
        "hole_spacing_mm": 29.0,
        "hole_cross_spacing_mm": 0.0,
        "shaft_offset_from_front_mm": 8.75,
        "spline_dia_mm": 4.9,
        "spline_height_mm": 4.0,
        "spline_teeth": 21,
        "mass_g": 13.4,
        "travel_degrees": 180.0,
        "voltage_min_v": 4.8,
        "voltage_max_v": 6.6,
        "stall_torque": [
            {"volts": 4.8, "kg_cm": 1.8},
            {"volts": 6.6, "kg_cm": 2.2},
        ],
        "speed": [
            {"volts": 4.8, "s_per_60_deg": 0.10},
            {"volts": 6.0, "s_per_60_deg": 0.08},
        ],
        "approximate": [
            "tab_thickness_mm",
            "hole_dia_mm",
            "hole_spacing_mm",
            "shaft_offset_from_front_mm",
            "spline_height_mm",
        ],
    },
    # TowerPro MG996R, standard metal-gear. towerpro.com.tw/product/mg996r/
    # (55 g; 9.4 kg*cm @4.8 V, 11 @6.0 V; 0.19/0.15); Handsontec drawing
    # (53.6 over tabs, 36.6 case top, 26.6 flange underside, 42.9 with
    # spline). Hole pattern is the 40x20 standard-class 49.5 x 10 the
    # DS3218 datasheet dimensions; hole diameter, tab thickness and shaft
    # offset are the class's nominal figures, not manufacturer data.
    # Travel is disputed across sources (120/160/180); 180 is the retail
    # figure and the one catalogued.
    "mg996r": {
        "family": "standard",
        "body_length_mm": 40.7,
        "body_width_mm": 19.7,
        "case_height_mm": 36.6,
        "overall_tab_length_mm": 53.6,
        "tab_thickness_mm": 2.5,
        "flange_height_mm": 26.6,
        "hole_dia_mm": 4.5,
        "hole_spacing_mm": 49.5,
        "hole_cross_spacing_mm": 10.0,
        "shaft_offset_from_front_mm": 9.85,
        "spline_dia_mm": 5.9,
        "spline_height_mm": 6.3,
        "spline_teeth": 25,
        "mass_g": 55.0,
        "travel_degrees": 180.0,
        "voltage_min_v": 4.8,
        "voltage_max_v": 6.6,
        "stall_torque": [
            {"volts": 4.8, "kg_cm": 9.4},
            {"volts": 6.0, "kg_cm": 11.0},
        ],
        "speed": [
            {"volts": 4.8, "s_per_60_deg": 0.19},
            {"volts": 6.0, "s_per_60_deg": 0.15},
        ],
        "approximate": [
            "tab_thickness_mm",
            "hole_dia_mm",
            "hole_spacing_mm",
            "hole_cross_spacing_mm",
            "shaft_offset_from_front_mm",
        ],
    },
    # DSSERVO DS3218 (standard variant, not PRO). Official Dsservo
    # datasheet (40 x 20 x 40.5; 54.5 over tabs; holes 49.5 x 10; flange
    # 27.7; lead 300 mm; 4.8-6.8 V); SpeedyFPV listing (19 kg*cm @5 V,
    # 21.5 @6.8 V; 0.16/0.14; 25T spline dia 5.9; 58-60 g). The datasheet's
    # 40.5 height is taken as the case top and the case/spline split is
    # nominal — close the gap from dsservo.com's own STEP file when finer
    # fidelity matters.
    "ds3218": {
        "family": "large",
        "body_length_mm": 40.0,
        "body_width_mm": 20.0,
        "case_height_mm": 40.5,
        "overall_tab_length_mm": 54.5,
        "tab_thickness_mm": 2.5,
        "flange_height_mm": 27.7,
        "hole_dia_mm": 4.5,
        "hole_spacing_mm": 49.5,
        "hole_cross_spacing_mm": 10.0,
        "shaft_offset_from_front_mm": 10.0,
        "spline_dia_mm": 5.9,
        "spline_height_mm": 4.0,
        "spline_teeth": 25,
        "mass_g": 60.0,
        "travel_degrees": 180.0,
        "voltage_min_v": 4.8,
        "voltage_max_v": 6.8,
        "stall_torque": [
            {"volts": 5.0, "kg_cm": 19.0},
            {"volts": 6.8, "kg_cm": 21.5},
        ],
        "speed": [
            {"volts": 5.0, "s_per_60_deg": 0.16},
            {"volts": 6.8, "s_per_60_deg": 0.14},
        ],
        "approximate": [
            "tab_thickness_mm",
            "hole_dia_mm",
            "shaft_offset_from_front_mm",
            "spline_height_mm",
            "case_height_mm",
        ],
    },
}


# --------------------------------------------------------------------------
# Micro-servo horns, measured on the SG90's shipped set (AUS TA0132 — the
# only dimensioned horn source found; the MG90S ships the same family).
# hub 6.9 dia x 2.5 high, arms 1.5 thick, link holes 1.0 dia at 2 mm pitch.
# The standard 25T servos ship undimensioned horn sets; until a measured
# source exists lib refuses rather than inventing one.
# --------------------------------------------------------------------------
MICRO_HORNS: Mapping[str, Mapping[str, Any]] = {
    "single_arm": {"arm_reach_mm": 16.0, "arms": 1, "hole_radii_mm": [4.0, 6.0, 8.0, 10.0, 12.0, 14.0]},
    "double_arm": {"arm_reach_mm": 16.0, "arms": 2, "hole_radii_mm": [4.0, 6.0, 8.0, 10.0, 12.0, 14.0]},
    "cross": {"arm_reach_mm": 10.2, "arms": 4, "hole_radii_mm": [4.0, 6.0, 8.0]},
}

MICRO_HORN_HUB = {
    "hub_dia_mm": 6.9,
    "hub_height_mm": 2.5,
    "arm_thickness_mm": 1.5,
    "arm_width_mm": 4.0,
    "hole_dia_mm": 1.0,
}


def servo_spec(sku: Any) -> dict[str, Any]:
    """The servo row for one part number, as a deep-enough copy."""

    if not isinstance(sku, str) or sku.strip().lower() not in SERVOS:
        raise CatalogError(
            f"Unknown servo {sku!r}; catalogued servos: "
            + ", ".join(sorted(SERVOS)) + "."
        )
    row = SERVOS[sku.strip().lower()]
    copied = dict(row)
    copied["stall_torque"] = [dict(entry) for entry in row["stall_torque"]]
    copied["speed"] = [dict(entry) for entry in row["speed"]]
    copied["approximate"] = list(row["approximate"])
    return copied


def normalise_servo_sku(sku: Any) -> str:
    servo_spec(sku)
    return sku.strip().lower()


_BEARING_SUFFIXES = ("zz", "2rs", "rs", "z")


def normalise_thread_size(size: Any) -> str:
    """``"M3"``/``"m3"``/``" M3 "`` -> ``"m3"``; unknown sizes refuse loudly."""

    if not isinstance(size, str) or not size.strip():
        raise CatalogError(
            "A thread size must be a string such as 'm3'; known sizes: "
            + ", ".join(sorted(METRIC_THREADS)) + "."
        )
    cleaned = size.strip().lower()
    if cleaned not in METRIC_THREADS:
        raise CatalogError(
            f"Unknown thread size {size!r}; known sizes: "
            + ", ".join(sorted(METRIC_THREADS)) + "."
        )
    return cleaned


def normalise_bearing_code(code: Any) -> str:
    """``"608ZZ"``/``"608-2RS"`` -> ``"608"``; unknown codes refuse loudly."""

    if not isinstance(code, str) or not code.strip():
        raise CatalogError(
            "A bearing code must be a string such as '608' or '608zz'; "
            "known codes: " + ", ".join(sorted(BALL_BEARINGS)) + "."
        )
    cleaned = code.strip().lower().replace("-", "")
    for suffix in _BEARING_SUFFIXES:
        if cleaned.endswith(suffix) and cleaned[: -len(suffix)] in BALL_BEARINGS:
            cleaned = cleaned[: -len(suffix)]
            break
    if cleaned not in BALL_BEARINGS:
        raise CatalogError(
            f"Unknown bearing code {code!r}; known codes: "
            + ", ".join(sorted(BALL_BEARINGS)) + "."
        )
    return cleaned


def thread_spec(size: Any) -> dict[str, float]:
    """The metric-thread row for one size, as a plain dict copy."""

    return dict(METRIC_THREADS[normalise_thread_size(size)])


def bearing_spec(code: Any) -> dict[str, float]:
    """The bearing row for one code (shield suffixes accepted), as a copy."""

    return dict(BALL_BEARINGS[normalise_bearing_code(code)])


def _family_lookup(
    family: str, table: Mapping[str, Mapping[str, float]], size: Any
) -> dict[str, float]:
    key = normalise_thread_size(size)
    row = table.get(key)
    if row is None:
        raise CatalogError(
            f"No {family} is catalogued for {size!r}; catalogued sizes: "
            + ", ".join(sorted(table)) + "."
        )
    return dict(row)


def socket_head_spec(size: Any) -> dict[str, float]:
    return _family_lookup("socket head screw", SOCKET_HEAD_SCREWS, size)


def countersunk_spec(size: Any) -> dict[str, float]:
    return _family_lookup("countersunk screw", COUNTERSUNK_SCREWS, size)


def hex_nut_spec(size: Any) -> dict[str, float]:
    return _family_lookup("hex nut", HEX_NUTS, size)


def nyloc_nut_spec(size: Any) -> dict[str, float]:
    return _family_lookup("nyloc nut", NYLOC_NUTS, size)


def washer_spec(size: Any) -> dict[str, float]:
    return _family_lookup("flat washer", FLAT_WASHERS, size)


def heat_set_insert_spec(size: Any) -> dict[str, float]:
    return _family_lookup("heat-set insert", HEAT_SET_INSERTS, size)


def catalog_families() -> dict[str, Any]:
    """The browsable catalog: every family, its part numbers, key specs.

    This is what ``describe_api`` serves so the agent can shop the library
    without a second tool: one line per part number, the numbers that decide
    a design choice, nothing that only matters once a part is placed.
    """

    def _rows(table: Mapping[str, Mapping[str, float]], key_name: str) -> list:
        # Homogeneous row lists, not SKU-keyed dicts: the response-shape
        # golden collapses a list to one representative element, so the
        # catalog can grow part numbers without moving the pinned contract.
        return [
            {key_name: name, **table[name]} for name in sorted(table)
        ]

    return {
        "fasteners": {
            "sizes": sorted(METRIC_THREADS),
            "bolt_heads": ["socket", "countersunk"],
            "nut_styles": ["hex", "nyloc"],
            "notes": (
                "ISO metric coarse. Bolt lengths are free; every other "
                "dimension is the standard's. lib.clearance_hole/tap_drill/"
                "insert_hole return the matching hole diameters."
            ),
        },
        "heat_set_inserts": {
            "sizes": sorted(HEAT_SET_INSERTS),
            "rows": _rows(HEAT_SET_INSERTS, "size"),
        },
        "bearings": {
            "codes": sorted(BALL_BEARINGS),
            "rows": _rows(BALL_BEARINGS, "code"),
            "notes": (
                "Deep-groove ball bearings, bore x od x width; shield "
                "suffixes (zz/2rs) are accepted, and the miniature rows "
                "(688, mr*) carry the shielded widths. lib.bushing(...) is "
                "the parametric plain bearing for everything the codes do "
                "not cover."
            ),
        },
        "servos": {
            "skus": sorted(SERVOS),
            "rows": [
                {
                    "sku": sku,
                    "family": SERVOS[sku]["family"],
                    "mass_g": SERVOS[sku]["mass_g"],
                    "travel_degrees": SERVOS[sku]["travel_degrees"],
                    "stall_torque": [dict(e) for e in SERVOS[sku]["stall_torque"]],
                    "speed": [dict(e) for e in SERVOS[sku]["speed"]],
                }
                for sku in sorted(SERVOS)
            ],
            "notes": (
                "Hobby servos with datasheet interfaces: exact mounting-hole "
                "pattern, flange height and shaft position, a simple exact "
                "envelope, and the manufacturer's stall torque already "
                "converted for assembly.actuator. lib.servo(sku) returns the "
                "part; .horn(style) the matching horn (micro family only so "
                "far); .actuator(joint, control_deg=...) a position actuator "
                "bounded by the real stall torque; .spec the numbers, with "
                "spec['approximate'] naming any field no datasheet "
                "dimensions. Full dimension rows live in lib.servo(sku).spec "
                "rather than here."
            ),
        },
    }
