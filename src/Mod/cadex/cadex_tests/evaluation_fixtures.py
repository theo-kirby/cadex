# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Rollouts whose answers are stated, for the evaluation metrics (ADR-455).

A reader that fails everything proves nothing about a shuffle, so each metric
is pinned on a motion built to pass it and one built to fail it for a stated
reason. The generators here write trace samples -- ``(time_s, placements)``,
the shape ``CadexEvaluation.read_trace`` returns -- directly, with no physics:
a trot whose feet stay where they landed, a shuffle that chatters, a balancer
that is knocked and settles, an arm whose tip moves to a target.

One fixture is not synthetic. :func:`w2_2` is ot10's ``w2-2`` policy, the
quadruped that passed the old gait check and shuffled: the base and four feet
of its stored rollout, which is the failure the metrics exist to see.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

IDENTITY = [0.0, 0.0, 0.0, 1.0]
DT = 0.02
DONE = {"duration_s": 10.0, "termination": "", "truncated": True, "seed": 1101}

# -- a quadruped ------------------------------------------------------------

HIP = 100.0
FEET = {"fl": (60.0, 40.0), "fr": (60.0, -40.0), "rl": (-60.0, 40.0), "rr": (-60.0, -40.0)}
RADIUS = 7.5


def walk_rig():
    sphere = {"kind": "sphere", "size_mm": [RADIUS, 0.0, 0.0], "pos_mm": [0.0, 0.0, 0.0], "quat_xyzw": IDENTITY}
    return {"base": "base", "reference_xyzw": IDENTITY, "base_com_local_mm": [0.0, 0.0, 0.0],
            "floor_mm": 0.0, "hip_height_mm": HIP, "com_height_mm": 80.0,
            "feet": {name: [sphere] for name in FEET}}


def yaw(degrees: float) -> list[float]:
    half = math.radians(degrees) / 2.0
    return [0.0, 0.0, math.sin(half), math.cos(half)]


def pitch(degrees: float) -> list[float]:
    half = math.radians(degrees) / 2.0
    return [0.0, math.sin(half), 0.0, math.cos(half)]


def trot(*, speed=80.0, lift=15.0, period_frames=24, seconds=10.0, swing_frames=None,
         heading=0.0, sideways=0.0, sink=0.0):
    """A trot: diagonal pairs swing in turn, stance feet stay where they landed."""

    swing_frames = period_frames // 2 if swing_frames is None else swing_frames
    samples = []
    for k in range(int(round(seconds / DT)) + 1):
        t = k * DT
        placements = {"base": {"position_mm": [speed * t, sideways * t, 90.0], "rotation_xyzw": yaw(heading * t)}}
        for name, (x, y) in FEET.items():
            shift = 0 if name in ("fl", "rr") else period_frames // 2
            cycle, phase = divmod(k + shift, period_frames)
            stride = speed * period_frames * DT
            if phase < swing_frames:
                fraction = (phase + 0.5) / swing_frames
                along = (cycle - 1) * stride + stride * fraction
                height = lift * math.sin(math.pi * fraction)
            else:
                along, height = cycle * stride, -sink
            placements[name] = {"position_mm": [x + along, y, RADIUS + height], "rotation_xyzw": IDENTITY}
        samples.append((t, placements))
    return samples


def shuffle(*, speed=140.0, hop=2.5, seconds=10.0):
    """The w2-2 shape: feet chatter forward in 40 ms hops a few millimetres high."""

    samples = []
    for k in range(int(round(seconds / DT)) + 1):
        t = k * DT
        placements = {"base": {"position_mm": [speed * t, 0.0, 90.0], "rotation_xyzw": IDENTITY}}
        for name, (x, y) in FEET.items():
            airborne = (k + (0 if name in ("fl", "rr") else 2)) % 4 < 2
            placements[name] = {"position_mm": [x + speed * t, y, RADIUS + (hop if airborne else 0.0)],
                                "rotation_xyzw": IDENTITY}
        samples.append((t, placements))
    return samples


# -- a balancer -------------------------------------------------------------

SHOVES = [(2.5, 0.1), (6.0, 0.1)]


def balance_rig():
    return {"base": "base", "reference_xyzw": IDENTITY, "base_com_local_mm": [0.0, 0.0, 0.0],
            "floor_mm": 0.0, "com_height_mm": 50.0, "hip_height_mm": None, "feet": {}}


def standing(*, drift=0.0, turn=0.0, shoves=((2.5, 0.1), (6.0, 0.1)), bump=20.0, lean=8.0, settle=0.6,
             seconds=10.0):
    """A balancer that is knocked ``bump`` mm and ``lean`` degrees by each
    shove and settles back with time constant ``settle``; plus a steady
    ``drift`` (mm/s) and ``turn`` (deg/s)."""

    samples = []
    for k in range(int(round(seconds / DT)) + 1):
        t = k * DT
        x, tilt = drift * t, 0.0
        for onset, duration in shoves:
            since = t - onset
            if since >= 0.0:
                pulse = (since / settle) * math.exp(1.0 - since / settle)
                x += bump * pulse
                tilt += lean * pulse
        half_yaw, half_tilt = math.radians(turn * t) / 2.0, math.radians(tilt) / 2.0
        # yaw about world Z after a pitch: q = q_yaw * q_pitch
        rotation = [-math.sin(half_yaw) * math.sin(half_tilt), math.cos(half_yaw) * math.sin(half_tilt),
                    math.sin(half_yaw) * math.cos(half_tilt), math.cos(half_yaw) * math.cos(half_tilt)]
        samples.append((t, {"base": {"position_mm": [x, 0.0, 50.0], "rotation_xyzw": rotation}}))
    return samples


# -- an arm -----------------------------------------------------------------

ARM = 200.0
REST = (150.0, 0.0, 100.0)
TARGET_A = (50.0, 120.0, 160.0)
TARGET_B = (-40.0, 60.0, 220.0)
TIP_LOCAL = [0.0, 0.0, 40.0]
REACH_DONE = {"duration_s": 8.0, "termination": "", "truncated": True, "seed": 1101}


def reach_rig():
    return {"base": None, "tip": {"body": "hand", "local_mm": list(TIP_LOCAL)}, "arm_length_mm": ARM}


def segments(*, switch=4.0, seconds=8.0):
    return [{"start_s": 0.0, "end_s": switch, "target_mm": list(TARGET_A)},
            {"start_s": switch, "end_s": seconds, "target_mm": list(TARGET_B)}]


def reaching(*, move_s=1.0, over=0.0, miss_mm=0.0, leaves_at=None, switch=4.0, seconds=8.0, hand_yaw=90.0):
    """An arm whose tip goes to target A, then at ``switch`` to target B.

    Each move is a straight line taking ``move_s``. ``over`` carries the tip
    past the target by that share of the move and back, over the next 0.4 s.
    ``miss_mm`` leaves it that far short, held. ``leaves_at`` makes it walk
    away from the last target at 50 mm/s from that time on. The hand is
    turned ``hand_yaw`` about Z, so the tip is not the hand's origin.
    """

    turn = math.radians(hand_yaw)
    offset = (TIP_LOCAL[0] * math.cos(turn) - TIP_LOCAL[1] * math.sin(turn),
              TIP_LOCAL[0] * math.sin(turn) + TIP_LOCAL[1] * math.cos(turn), TIP_LOCAL[2])
    samples = []
    for k in range(int(round(seconds / DT)) + 1):
        t = k * DT
        origin, target, since = (REST, TARGET_A, t) if t < switch - 1e-9 else (TARGET_A, TARGET_B, t - switch)
        line = [b - a for a, b in zip(origin, target)]
        length = math.sqrt(sum(v * v for v in line))
        if since < move_s:
            share = since / move_s
        else:
            pulse = max(0.0, 1.0 - abs(since - move_s - 0.2) / 0.2)
            share = 1.0 + over * pulse
        share = min(share, 1.0 - miss_mm / length) if miss_mm else share
        tip = [a + share * v for a, v in zip(origin, line)]
        if leaves_at is not None and t > leaves_at:
            tip[0] += 50.0 * (t - leaves_at)
        samples.append((t, {"hand": {"position_mm": [p - o for p, o in zip(tip, offset)],
                                     "rotation_xyzw": yaw(hand_yaw)}}))
    return samples


# -- the known negative -----------------------------------------------------

W2_2 = Path(__file__).resolve().parent / "fixtures" / "ot10_w2_2_feet.json"


def w2_2():
    """ot10's ``w2-2`` shuffle: ``(samples, rig, command_mm_s, episode)``."""

    fixture = json.loads(W2_2.read_text(encoding="utf-8"))
    bodies = fixture["bodies"]
    samples = [
        (index * fixture["frame_interval_s"],
         {body: {"position_mm": row[7 * k:7 * k + 3], "rotation_xyzw": row[7 * k + 3:7 * k + 7]}
          for k, body in enumerate(bodies)})
        for index, row in enumerate(fixture["frames"])
    ]
    return samples, fixture["rig"], fixture["command_mm_s"], fixture["episode"]


# -- models -----------------------------------------------------------------

#: One leg under a floating base. The hip is below a welded servo and above a
#: knee, so the hip height is neither the first body's nor the nearest joint's.
LEGGED_MODEL = """<mujoco>
  <worldbody>
    <geom name="floor" type="plane" size="0 0 0.05"/>
    <body name="base" pos="0 0 0.1">
      <freejoint/>
      <geom type="box" size="0.05 0.03 0.01" mass="0.4" contype="0" conaffinity="0"/>
      <body name="servo" pos="0.04 0 0.02">
        <body name="leg" pos="0 0 -0.02">
          <joint name="hip" type="hinge" axis="0 1 0"/>
          <geom type="capsule" fromto="0 0 0 0 0 -0.08" size="0.004" mass="0.05" contype="0" conaffinity="0"/>
          <body name="shin" pos="0 0 -0.04">
            <joint name="knee" type="hinge" axis="0 1 0"/>
            <body name="foot" pos="0 0 -0.04">
              <geom name="pad" type="sphere" size="0.01" pos="0 0 -0.01" mass="0.05"/>
            </body>
          </body>
        </body>
      </body>
    </body>
  </worldbody>
  <keyframe><key name="solved"/></keyframe>
</mujoco>
"""

#: A grounded arm: a free-spinning turntable nobody drives, then a shoulder
#: and an elbow that are driven, then a hand. The arm starts at the shoulder.
ARM_MODEL = """<mujoco>
  <worldbody>
    <geom name="floor" type="plane" size="0 0 0.05"/>
    <body name="turntable" pos="0 0 0.05">
      <joint name="spin" type="hinge" axis="0 0 1"/>
      <geom type="cylinder" size="0.03 0.01" mass="0.2"/>
      <body name="upper" pos="0 0 0.05">
        <joint name="shoulder" type="hinge" axis="0 1 0"/>
        <geom type="capsule" fromto="0 0 0 0.12 0 0" size="0.008" mass="0.1"/>
        <body name="fore" pos="0.12 0 0">
          <joint name="elbow" type="hinge" axis="0 1 0"/>
          <geom type="capsule" fromto="0 0 0 0 0 0.09" size="0.008" mass="0.1"/>
          <body name="hand" pos="0 0 0.09">
            <geom type="sphere" size="0.01" mass="0.05"/>
          </body>
        </body>
      </body>
    </body>
  </worldbody>
  <actuator>
    <position name="shoulder_servo" joint="shoulder" kp="5"/>
    <position name="elbow_servo" joint="elbow" kp="5"/>
  </actuator>
  <keyframe><key name="solved"/></keyframe>
</mujoco>
"""
