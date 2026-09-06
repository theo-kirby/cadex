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
from copy import deepcopy

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
    "BOARDS",
    "board_spec",
    "BLDC_MOTORS",
    "bldc_spec",
    "linear_actuator_spec",
    "joint_spec",
    "GEARMOTORS",
    "gearmotor_spec",
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



# Board interfaces, independently transcribed from manufacturer drawings.
# Full source/version and approximation ledger: docs/PROVENANCE.md §8a.
# Local frame: PCB lower-left corner, bottom face z=0, component side +Z.
# Terminals describe solder pads, not the free ends of optional pin headers.
def _board_pin(name: str, signal: str, x: float, y: float, drill: float) -> dict:
    return {"name": name.lower().replace("+", "plus"), "signal": signal, "origin": [x, y, 1.6],
            "axis": [0.0, 0.0, -1.0], "hole_dia": drill}


BOARDS = {
    "esp32-devkitc-v4": {
        "manufacturer": "Espressif", "variant": "ESP32-DevKitC V4, WROOM-32E",
        "width_mm": 27.94, "length_mm": 48.26, "thickness_mm": 1.6,
        "mount_holes": [], "mount_hole_dia_mm": 0.0,
        "cosmetic_origin": [4.97, 23.0, 1.6],
        "cosmetic_size": [18.0, 31.30, 3.0],
        "density_kg_m3": 1850.0,
        "approximate": ["thickness_mm", "cosmetic_origin", "cosmetic_size",
                        "density_kg_m3", "terminal_hole_dia_mm"],
        "source": "https://dl.espressif.com/dl/schematics/esp32_devkitc_v4_dimensions.pdf",
        "terminals": [
            _board_pin(f"{header}_{i+1}", signal, x, round(47.01-i*2.54, 4), 1.0)
            for header, x, signals in [
                ("J2", 1.24, "3V3 EN VP VN IO34 IO35 IO32 IO33 IO25 IO26 IO27 IO14 IO12 GND IO13 D2 D3 CMD 5V"),
                ("J3", 26.64, "GND IO23 IO22 TX RX IO21 GND IO19 IO18 IO5 IO17 IO16 IO4 IO0 IO2 IO15 D1 D0 CLK"),
            ] for i, signal in enumerate(signals.split())
        ],
    },
    "pi-zero-2-w": {
        "manufacturer": "Raspberry Pi", "variant": "Zero 2 W, unpopulated GPIO header",
        "width_mm": 65.0, "length_mm": 30.0, "thickness_mm": 1.6,
        "mount_holes": [[x, y] for x in (3.5, 61.5) for y in (3.5, 26.5)],
        "mount_hole_dia_mm": 2.75,
        "cosmetic_origin": [37.0, 8.0, 1.6], "cosmetic_size": [15.0, 15.0, 2.0],
        "density_kg_m3": 1850.0,
        "approximate": ["thickness_mm", "mount_hole_dia_mm", "cosmetic_origin",
                        "cosmetic_size", "density_kg_m3", "terminal_origins",
                        "terminal_hole_dia_mm"],
        "source": "https://datasheets.raspberrypi.com/rpizero2/raspberry-pi-zero-2-w-mechanical-drawing.pdf",
        "terminals": [
            _board_pin(f"J8_{i+1}", signal, round(8.37+(i//2)*2.54, 4),
                       25.23+(i%2)*2.54, 1.0)
            for i, signal in enumerate((
                "3V3 5V GPIO2 5V GPIO3 GND GPIO4 GPIO14 GND GPIO15 "
                "GPIO17 GPIO18 GPIO27 GND GPIO22 GPIO23 3V3 GPIO24 GPIO10 GND "
                "GPIO9 GPIO25 GPIO11 GPIO8 GND GPIO7 ID_SD ID_SC GPIO5 GND "
                "GPIO6 GPIO12 GPIO13 GND GPIO19 GPIO16 GPIO26 GPIO20 GND GPIO21"
            ).split())
        ],
    },
    "pca9685-adafruit-rev-c": {
        "manufacturer": "Adafruit", "variant": "815 PCA9685 revision C",
        "width_mm": 62.23, "length_mm": 25.4, "thickness_mm": 1.6,
        "mount_holes": [[x, y] for x in (3.175, 59.055) for y in (3.175, 22.225)],
        "mount_hole_dia_mm": 2.5,
        "cosmetic_origin": [26.0, 10.0, 1.6], "cosmetic_size": [10.0, 6.0, 1.2],
        "density_kg_m3": 1850.0,
        "approximate": ["thickness_mm", "cosmetic_origin", "cosmetic_size", "density_kg_m3"],
        "source": "https://github.com/adafruit/Adafruit-16-Channel-PWM-Servo-Driver-PCB/blob/32578c83a5ba2946249b80b1aa1fb18ae4e61e7d/Adafruit%20PCA9685%20rev%20C.brd",
        "terminals": [
            _board_pin(f"{header}_{i+1}", signal, x, round(6.477+i*2.54, 4), 1.016)
            for header, x in (("JP3", 1.905), ("JP4", 60.325))
            for i, signal in enumerate("V+ VCC SDA SCL OE GND".split())
        ] + [
            _board_pin(f"PWM{channel}_{signal}", signal if signal != "PWM" else f"PWM{channel}",
                       round(x, 4), y, 1.0)
            for channel, x in enumerate([
                6.985, 9.525, 12.065, 14.605, 19.685, 22.225, 24.765, 27.305,
                34.925, 37.465, 40.005, 42.545, 47.625, 50.165, 52.705, 55.245,
            ]) for signal, y in (("PWM", 6.477), ("V+", 3.937), ("GND", 1.397))
        ] + [_board_pin("J1_1", "V+_IN", 29.315, 21.59, 1.0),
             _board_pin("J1_2", "GND", 32.815, 21.59, 1.0)],
    },
}


def board_spec(sku: Any) -> dict[str, Any]:
    """A named board variant; nested rows are independent of the catalog."""
    if not isinstance(sku, str) or sku.strip().lower() not in BOARDS:
        raise CatalogError(f"Unknown board {sku!r}; catalogued boards: "
                           + ", ".join(sorted(BOARDS)) + ".")
    return deepcopy(BOARDS[sku.strip().lower()])


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


# Pololu drawing 0J949, 2024-04-03, page 4; #2367 specifications.
# Independently authored envelope, not a manufacturer CAD model.
GEARMOTORS = {
    "pololu-2367": {
        "manufacturer": "Pololu", "manufacturer_part_number": "2367",
        "form_factor": "N20", "gear_ratio": (35*37*35*38)/(12*11*13*10),
        "width_mm": 12.0, "height_mm": 10.0,
        "rear_envelope_mm": 25.6, "gearbox_length_mm": 9.0,
        "shaft_dia_mm": 3.0, "shaft_tip_z_mm": 10.0,
        "shaft_flat_start_z_mm": 1.0, "shaft_flat_to_opposite_mm": 2.5,
        "boss_dia_mm": 4.0, "boss_height_mm": 0.7,
        "mount_thread": "M1.6", "mount_holes": [[-4.5, 0.0], [4.5, 0.0]],
        "mount_bore_dia_mm": 1.6, "mount_bore_depth_mm": 1.0,
        "mass_g": 9.5, "rated_voltage_v": 6.0,
        "no_load_speed_rpm": 220.0, "no_load_speed_tolerance_percent": 20.0,
        "no_load_current_a": 0.07, "no_load_current_tolerance_percent": 50.0,
        "stall_current_a": 0.67, "stall_torque_nmm": 0.94 * KG_CM_TO_NMM,
        "rating_notes": "At 6 V; stall current and torque are theoretical extrapolations, not continuous ratings. Stalls can damage the motor/gearbox. No continuous torque or thermal model supplied.",
        "sources": ["https://www.pololu.com/product/2367/specs",
                    "https://www.pololu.com/file/0J949/micro-metal-gearmotors-dimensions.pdf"],
        "approximate": [
            "Filled rectangular rear envelope replaces motor, exposed gears and terminals; not internal geometry or inertia.",
            "M1.6 threads represented by major-diameter blind bores of assumed 1 mm depth; not a screw engagement limit.",
            "Flat starts 1 mm from face (9 mm usable shaft); axial flat transition and shaft chamfer simplified.",
        ],
    },
}


def gearmotor_spec(sku: Any) -> dict[str, Any]:
    """One manufacturer variant; no generic N20 ratings or shared nested rows."""
    if not isinstance(sku, str) or sku.strip().lower() not in GEARMOTORS:
        raise CatalogError(f"Unknown gearmotor {sku!r}; catalogued gearmotors: "
                           + ", ".join(sorted(GEARMOTORS)))
    return deepcopy(GEARMOTORS[sku.strip().lower()])


# HOBBYWING Skywalker 2820 SL 550KV, product 30415200; drawing 2820SL.
# Rear mounting plane at Z=0; local X/Y aligned to 19/25 mm hole pairs.
BLDC_MOTORS = {
    "hobbywing-30415200": {
        "manufacturer": "HOBBYWING", "manufacturer_part_number": "30415200",
        "model": "Skywalker 2820 SL 550KV",
        "case_dia_mm": 35.1, "case_length_mm": 40.0,
        "rear_boss_dia_mm": 11.0, "rear_boss_height_mm": 2.0,
        "shaft_dia_mm": 5.0, "shaft_projection_mm": 18.0,
        "shaft_collar_envelope_dia_mm": 10.5,
        "mount_thread": "M3",
        "mount_holes": [[-9.5, 0.0], [9.5, 0.0], [0.0, -12.5], [0.0, 12.5]],
        "mount_bore_dia_mm": 3.0, "mount_bore_depth_mm": 1.0,
        "kv_rpm_per_v": 550.0, "supply_lipo_cells": 6,
        "no_load_current_a": 1.38, "no_load_test_voltage_v": 22.2,
        "mass_g": 144.5,
        "rating_notes": "No torque, thermal or physical inertia model. Manufacturer lists 40.9 A and 910.2 W for 46 s, without full cooling conditions; these are not continuous robot-joint ratings.",
        "sources": ["https://www.hobbywing.com/en/products/skywalker2814.html",
                    "https://www.hobbywing.com/en/uploads/file/20231121/6ce36297af7f04e8e0c41c3b28a36dbd.pdf"],
        "approximate": [
            "Filled case envelope unites rotating and stationary components; no vents, windings or physical inertia.",
            "Collar axial length is undimensioned: reserve its 10.5 mm diameter over the whole 18 mm shaft projection. Not a shaft coupling fit model; the actual shaft diameter is 5 mm.",
            "M3 threads represented by major-diameter blind bores of assumed 1 mm depth; not a screw engagement limit.",
            "Leads, connectors, propeller adapter and cross mounting plate omitted; no full installation clearance guarantee. Local X/Y sets the hole pattern only, not cable clocking.",
        ],
    },
}


def bldc_spec(sku: Any) -> dict[str, Any]:
    """A specific winding and manufacturer, with conservative shaft reservation."""
    if not isinstance(sku, str) or sku.strip().lower() not in BLDC_MOTORS:
        raise CatalogError(f"Unknown BLDC motor {sku!r}; catalogued BLDC motors: "
                           + ", ".join(sorted(BLDC_MOTORS)))
    return deepcopy(BLDC_MOTORS[sku.strip().lower()])


# Actuonix revision F drawing; older STEP discrepancy and local widths: PROVENANCE 8d.
LINEAR_ACTUATORS = {
    "l12-50-210-12-s": {
        "manufacturer": "Actuonix", "manufacturer_part_number": "L12-50-210-12-S",
        "stroke_mm": 50.0, "retracted_centres_mm": 102.0,
        "mount_bore_dia_mm": 4.25, "rear_lug_width_mm": 8.0,
        "clevis_width_mm": 6.0, "older_step_spacing_excess_mm": 0.5,
        "rated_voltage_v": 12.0, "gear_ratio": 210,
        "maximum_lifted_force_n": 80.0, "unloaded_speed_mm_s": 6.5,
        "peak_power_force_n": 62.0, "peak_power_speed_mm_s": 3.2,
        "maximum_duty_percent": 20.0, "temperature_range_c": [-10.0, 50.0],
        "rating_notes": "At 12 V: maximum lifted force, unloaded speed and peak-power force/speed are distinct operating points. Duty at most 20%; application life requires testing. No physical inertia, load or dynamics guarantee.",
        "switch_notes": "S limit switches stop within 0.5 mm of a stroke end; geometric endpoints are not guaranteed powered-reachable. No position controller or feedback is supplied by this recipe.",
        "sources": ["https://www.actuonix.com/assets/images/datasheets/ActuonixL12Datasheet.pdf",
                    "https://www.actuonix.com/assets/images/datasheets/L12_STP.zip"],
        "approximate": [
            "Datasheet nominal centres take precedence over older STEP spacing, 0.5 mm longer; not a tolerance or blanket surface correction.",
            "Primitive housing, rear lug and sleeve transitions; flat-ended clipped cylindrical supplied clevis omits rounded tip and threaded neck. Axial extents in PROVENANCE 8d are approximations.",
            "Filled fused exterior omits internals, shaft hollowing, threads, clamps, brackets, fasteners, cable and connector. No installation fit, conservative collision envelope, strength or physical inertia claim.",
        ],
    },
}


def linear_actuator_spec(sku: Any) -> dict[str, Any]:
    """One sourced L12 stroke, ratio, voltage and switch variant."""
    if not isinstance(sku, str) or sku.strip().lower() not in LINEAR_ACTUATORS:
        raise CatalogError(f"Unknown linear actuator {sku!r}; catalogued linear actuators: "
                           + ", ".join(sorted(LINEAR_ACTUATORS)))
    return deepcopy(LINEAR_ACTUATORS[sku.strip().lower()])


# SKF BU/P1 06116/1 EN, May 2013, pp. 132–133; PROVENANCE §8f.
JOINTS = {
    "skf-ge-6-c": {
        "manufacturer": "SKF", "manufacturer_part_number": "GE 6 C",
        "bore_dia_mm": 6.0, "outside_dia_mm": 14.0,
        "inner_width_mm": 6.0, "outer_width_mm": 4.0, "sphere_dia_mm": 10.0,
        "maximum_tilt_degrees": 13.0,
        "shaft_shoulder_dia_range_mm": [7.4, 8.0],
        "housing_opening_dia_range_mm": [9.5, 12.7],
        "ring_chamfer_min_mm": 0.3, "abutment_fillet_max_mm": 0.3,
        "basic_dynamic_load_n": 3600.0, "basic_static_load_n": 9000.0,
        "mass_g": 4.0,
        "sliding_contact": "Steel/PTFE sintered bronze; maintenance-free radial spherical plain bearing.",
        "rating_notes": "Basic catalog radial ratings, not allowable robot working loads, axial ratings, life, torque or friction. Application duty, fit and operating conditions require separate selection; no dynamics or physical inertia model.",
        "datum_notes": "Common sphere centre at origin; neutral bore and housing axes +Z; inner faces Z=±3, outer faces Z=±2 mm. Inner tilt about canonical +Y before placement; spec coordinates stay canonical.",
        "tilt_notes": "Nominal ±13 degrees conditional on shaft shoulder diameter at most 8 mm; no assembly solver or installed motion guarantee.",
        "source_revision": "BU/P1 06116/1 EN, May 2013, printed pages 132–133",
        "source_sha256": "df51e55192dc9ce138e371e2f5047cfbceeba7f2ac6246f92e5bd3d7f24930cb",
        "sources": ["https://www.skf.com/binaries/pub12/Images/0901d19680154a05-06116_1-EN_tcm_12-122020.pdf"],
        "approximate": [
            "Two nominal rings with coincident spherical surfaces; no radial running clearance.",
            "Chamfers, liner thickness and manufacturing seams omitted; no mating hardware.",
            "Not a tolerance, press-fit, conservative collision envelope, manufacturing drawing or physical inertia model.",
        ],
    },
}


def joint_spec(sku: Any) -> dict[str, Any]:
    """Only the qualified SKF GE 6 C publication variant."""
    if not isinstance(sku, str) or sku.strip().lower() not in JOINTS:
        raise CatalogError(f"Unknown joint {sku!r}; catalogued joints: "
                           + ", ".join(sorted(JOINTS)))
    return deepcopy(JOINTS[sku.strip().lower()])


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
        "joints": {
            "skus": sorted(JOINTS),
            "notes": "lib.joint(sku, tilt_degrees=0): SKF GE 6 C nominal two-ring geometry; spec carries source, datums, conditional tilt, qualified ratings and approximation limits. No fit or dynamics guarantee.",
        },
        "linear_actuators": {
            "skus": sorted(LINEAR_ACTUATORS),
            "notes": "lib.linear_actuator(sku, extension=0): nominal L12 mounting geometry with supplied clevis; bounded geometric extension, qualified operating points and approximation limits in spec. No installation or dynamics guarantee.",
        },
        "bldc_motors": {
            "skus": sorted(BLDC_MOTORS),
            "notes": "lib.bldc(sku): sourced rear-mount case and conservative shaft/collar envelope; spec carries kV, qualified ratings and fit limitations. No torque or inertia model.",
        },
        "gearmotors": {
            "skus": sorted(GEARMOTORS),
            "notes": "lib.gearmotor(sku): N20 envelope, D shaft and mounting bores; spec carries manufacturer dimensions, 6 V ratings and approximations. No continuous torque or inertia model.",
        },
        "boards": {
            "skus": sorted(BOARDS),
            "notes": "lib.board(sku): PCB and simple component marker; spec carries mounting holes, solder-pad pinout, sources and explicit approximations. No connector clearance envelope or measured assembly mass.",
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
