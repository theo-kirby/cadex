# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Eval cases for Part Design mode.

Each case is one user prompt plus locally checkable expectations — no LLM
judging. Expectations are deliberately loose (ranges, envelopes) so they score
design intent, not one specific construction:

- ``part_count``: (min, max) mesh objects expected in the Model collection.
- ``required_params``: parameter ids that must be declared (substring match
  is NOT used — ids must match exactly, they are part of the contract the
  prompt states).
- ``bbox_max``: (x, y, z) envelope in mm the whole assembly must fit in.
- ``min_part_size``: every part's largest dimension must reach this (mm),
  which catches accidental meter-scale or degenerate output.
"""

CASES = [
    {
        "id": "single_gear",
        "prompt": (
            "Make a single involute spur gear: module 2, 20 teeth, 8 mm "
            "thick, 5 mm bore. Declare parameters `module` and `thickness`."
        ),
        "part_count": (1, 1),
        "required_params": ["module", "thickness"],
        "bbox_max": (60.0, 60.0, 20.0),
        "min_part_size": 20.0,
    },
    {
        "id": "gear_pair_plate",
        "prompt": (
            "Make a meshing spur gear pair (module 1.5, 12 and 28 teeth, "
            "6 mm thick, 3 mm shafts) posed correctly on a mounting plate "
            "with a shaft hole under each gear. Declare a `clearance` "
            "parameter and derive the fits from it."
        ),
        "part_count": (3, 3),
        "required_params": ["clearance"],
        "bbox_max": (110.0, 80.0, 30.0),
        "min_part_size": 15.0,
    },
    {
        # Flagship: the motivating scenario for the mode.
        "id": "two_stage_reduction",
        "prompt": (
            "Design a 2-stage gear reduction: input pinion 10 teeth driving "
            "a 30-tooth gear, second pinion 10 teeth (coaxial with the first "
            "30-tooth gear) driving another 30-tooth gear, module 1.5, gears "
            "6 mm thick, 4 mm shafts. Mount everything on a backplate with a "
            "counterbored M3 hole (3.4 mm, counterbore 6 mm diameter x 3 mm) "
            "at each shaft position. Pose the gears assembled and meshing. "
            "Declare `module`, `gear_thickness` and `clearance` parameters."
        ),
        "part_count": (4, 6),
        "required_params": ["module", "gear_thickness", "clearance"],
        "bbox_max": (160.0, 120.0, 40.0),
        "min_part_size": 15.0,
    },
    {
        "id": "l_bracket",
        "prompt": (
            "Make a printable L-bracket: two 4 mm thick legs, 40 x 30 mm "
            "footprint each, joined at a right angle as ONE part, with two "
            "4.5 mm mounting holes in each leg. Chamfer the bed-contact "
            "edges. Declare `thickness` and `hole_d` parameters."
        ),
        "part_count": (1, 1),
        "required_params": ["thickness", "hole_d"],
        "bbox_max": (60.0, 50.0, 50.0),
        "min_part_size": 30.0,
    },
    {
        "id": "enclosure_lid",
        "prompt": (
            "Make a small electronics enclosure: an open-top box, outside "
            "60 x 40 x 25 mm with 2 mm walls and floor, plus a separate "
            "sliding lid that fits the opening with printing clearance. Pose "
            "the lid above the box, not intersecting it. Declare `wall` and "
            "`clearance` parameters."
        ),
        "part_count": (2, 2),
        "required_params": ["wall", "clearance"],
        "bbox_max": (80.0, 60.0, 70.0),
        "min_part_size": 35.0,
    },
    {
        "id": "bearing_bushing",
        "prompt": (
            "Make a press-fit bushing for a 608 skate bearing (22 mm OD, "
            "7 mm wide): a cylindrical housing 30 mm OD with a 22 mm pocket "
            "7 mm deep and an 8.5 mm through hole. One part. Declare a "
            "`press_fit` parameter for the pocket fit."
        ),
        "part_count": (1, 1),
        "required_params": ["press_fit"],
        "bbox_max": (40.0, 40.0, 20.0),
        "min_part_size": 25.0,
    },
    {
        "id": "hex_knob",
        "prompt": (
            "Make a knurl-free control knob, 30 mm diameter, 15 mm tall, "
            "with a pocket in the underside that press-fits an M5 hex nut "
            "(8 mm across flats, 4 mm thick) and a 5.3 mm through hole for "
            "the screw. One part. Declare `knob_d` and `clearance` "
            "parameters."
        ),
        "part_count": (1, 1),
        "required_params": ["knob_d", "clearance"],
        "bbox_max": (40.0, 40.0, 20.0),
        "min_part_size": 25.0,
    },
    {
        "id": "cable_clip",
        "prompt": (
            "Make a screw-down cable clip for a 6 mm cable: a base with one "
            "3.4 mm countersunk screw hole and a C-shaped saddle that holds "
            "the cable, printable flat without supports, as ONE part. "
            "Declare `cable_d` and `clearance` parameters."
        ),
        "part_count": (1, 1),
        "required_params": ["cable_d", "clearance"],
        "bbox_max": (40.0, 30.0, 20.0),
        "min_part_size": 12.0,
    },
]


def get_case(case_id):
    for case in CASES:
        if case["id"] == case_id:
            return case
    raise KeyError("unknown eval case: {:s}".format(case_id))
