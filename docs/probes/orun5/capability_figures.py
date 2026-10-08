"""One figure per orun5 capability, drawn from the rigs its tests pin.

Each panel replays a test's own fixture through Cadex's real code
(``CadexDynamics`` build, MJCF export and observation path, or
``CadexEvaluation``) and plots what the test asserts at a few points across
a sweep:

* ``s1-position-tracker.png`` (ADR-588): a ball held still in the world
  while the plate turns through ±160° at a 20° tilt -- the panel's reading
  against the ball's true position in the plate frame -- and the ball
  pushed out along the plate's x until it leaves the declared range, where
  the reading drops to zeros and ``in_range`` to 0;
* ``s2-load-sensor.png`` (ADR-591): the held arm of the load test under
  servos of rising stall torque -- the reading follows the stall line until
  the servo can hold the joint, then the gravity torque;
* ``l1-four-bar.png`` (ADR-593, ADR-595): the four-bar driven by its crank
  at the linkage test's 0.5 ms step -- the rocker against its analytic
  circle-intersection angle over a turn and a quarter, and the error at the
  rocker's tip;
* ``r1-goal-frame.png`` (ADR-592): the drifting-base trace of the goal-frame
  test, top-down, with the reach error ``CadexEvaluation`` reports for a
  target held in the base and for one fixed in the world.

Usage::

    pixi run python docs/probes/orun5/capability_figures.py OUT_DIR
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TESTS = ROOT / "src" / "Mod" / "cadex" / "cadex_tests"
sys.path.insert(0, str(TESTS))
import conftest  # noqa: E402,F401  -- stubs the FreeCAD runtime and puts the engine on sys.path

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mujoco  # noqa: E402

import CadexDynamics as dyn  # noqa: E402
import CadexEvaluation as evaluation  # noqa: E402
import test_dynamics_linkages as linkages  # noqa: E402
import test_dynamics_load_sensor as load  # noqa: E402
import test_dynamics_position_tracker as tracker  # noqa: E402
from test_dynamics_goal_frame import _drifting  # noqa: E402

FLOOR, INK, MUTED, EDGE = "#16181c", "#e6e0d2", "#9aa0a8", "#3a3e45"
ORANGE, BLUE = "#d8602a", "#5b8fd6"


def _style(ax, xlabel: str, ylabel: str, title: str) -> None:
    ax.set_facecolor(FLOOR)
    ax.set_title(title, color=INK, fontsize=9)
    ax.set_xlabel(xlabel, color=MUTED, fontsize=8)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=8)
    ax.tick_params(colors=MUTED, labelsize=7)
    for side in ax.spines.values():
        side.set_color(EDGE)


def _legend(ax) -> None:
    ax.legend(fontsize=7, facecolor=FLOOR, edgecolor=EDGE, labelcolor=INK)


def _save(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=100, facecolor=FLOOR)
    plt.close(fig)
    print(f"{path.name}: {path.stat().st_size // 1024} KB")


def position_tracker(out: Path) -> None:
    model, task = tracker._bundle([tracker._entry()])
    data = mujoco.MjData(model)
    turns = list(range(-160, 161, 10))
    truth, read = [], []
    for turn in turns:
        tracker._set_pose(model, data, turn_deg=turn, tilt_deg=20.0, ball_world_m=[0.03, -0.02, 0.09])
        truth.append(tracker._true_in_plate(model, data))
        read.append(dyn.observation_values(task, data.sensordata))
    worst = max(abs(r[f"ball_{a}"] - t[i]) for r, t in zip(read, truth) for i, a in enumerate("xy"))

    offsets = [x / 1000.0 for x in range(0, 121, 2)]
    out_truth, out_read, flag = [], [], []
    for x in offsets:
        tracker._set_pose(model, data, turn_deg=0.0, tilt_deg=0.0, ball_world_m=[x, 0.0, 0.09])
        out_truth.append(tracker._true_in_plate(model, data)[0])
        values = dyn.observation_values(task, data.sensordata)
        out_read.append(values["ball_x"])
        flag.append(values["ball_in_range"])

    fig, (left, right) = plt.subplots(1, 2, figsize=(9, 3.8), facecolor=FLOOR)
    for i, (axis, colour) in enumerate((("x", ORANGE), ("y", BLUE))):
        left.plot(turns, [t[i] for t in truth], color=colour, lw=1.0, label=f"true {axis} in plate frame")
        left.plot(turns, [r[f"ball_{axis}"] for r in read], "o", color=colour, ms=3, label=f"panel ball_{axis}")
    _style(left, "plate turn, deg (tilt 20 deg, ball still in the world)", "mm",
           f"through a turn and a tilt:\nworst error {worst:.2f} mm (resolution 0.5 mm)")
    _legend(left)
    right.plot(out_truth, out_truth, color=MUTED, lw=0.8, ls="--", label="true x")
    right.plot(out_truth, out_read, color=ORANGE, lw=1.2, label="panel ball_x")
    right.axvline(tracker.TRACKER["range_mm"][0][1], color=EDGE, lw=0.8)
    twin = right.twinx()
    twin.step(out_truth, flag, color=BLUE, lw=1.0, where="post")
    twin.set_ylim(-0.1, 1.3)
    twin.set_ylabel("ball_in_range", color=BLUE, fontsize=8)
    twin.tick_params(colors=MUTED, labelsize=7)
    _style(right, "ball x in the plate frame, mm", "mm",
           "past the 90 mm edge:\nzeros and a flag, never a clamp")
    _legend(right)
    _save(fig, out / "s1-position-tracker.png")


def load_sensor(out: Path) -> None:
    mj, model, task = load._held(20000.0)
    data, dof, qadr = load._settle(mj, model)
    gravity = abs(1000.0 * float(data.qfrc_bias[dof]))
    held_at = float(data.qpos[qadr])
    stalls = [200.0 * k for k in range(1, 16)]
    readings, sag = [], []
    for stall in stalls:
        mj, model, task = load._held(stall)
        data, _dof, qadr = load._settle(mj, model, seconds=1.5)
        readings.append(abs(dyn.observation_values(task, data.sensordata)["effort"]))
        sag.append(abs(math.degrees(float(data.qpos[qadr]) - held_at)))

    fig, ax = plt.subplots(figsize=(6, 3.6), facecolor=FLOOR)
    ax.plot(stalls, stalls, color=MUTED, lw=0.8, ls="--", label="stall line")
    ax.axhline(gravity, color=EDGE, lw=0.8, label=f"gravity torque {gravity:.0f} N·mm")
    ax.plot(stalls, readings, "o-", color=ORANGE, ms=3, lw=1.2, label="load_sensor reading")
    twin = ax.twinx()
    twin.plot(stalls, sag, color=BLUE, lw=1.0)
    twin.set_ylabel("sag off setpoint, deg", color=BLUE, fontsize=8)
    twin.tick_params(colors=MUTED, labelsize=7)
    _style(ax, "servo stall torque, N·mm", "|load|, N·mm",
           "held load: the reading saturates at stall while the arm sags")
    _legend(ax)
    _save(fig, out / "s2-load-sensor.png")


def four_bar(out: Path) -> None:
    components, joints = linkages._four_bar()
    run = dyn.simulate(
        components, joints, start_time_s=0.0, end_time_s=2.0, frames_per_second=60,
        time_step_s=linkages.STEP_S, actuators=[linkages._servo("a", "50 + 225*time")],
    )
    crank, rocker, analytic, tip_error = [], [], [], []
    swept, last, expected = 0.0, None, None
    for frame in run["frames"]:
        poses = frame["component_placements"]
        theta = linkages._angle(poses["crank"])
        actual = linkages._angle(poses["rocker"])
        expected = linkages._rocker_angle(theta, actual if expected is None else expected)
        if last is not None:
            swept += abs(math.remainder(theta - last, math.tau))
        last = theta
        crank.append(math.degrees(swept))
        # Unwrapped onto the analytic branch, so a heading crossing ±180° does not jump.
        previous = math.radians(analytic[-1]) if analytic else expected
        analytic.append(math.degrees(previous + math.remainder(expected - previous, math.tau)))
        rocker.append(analytic[-1] + math.degrees(math.remainder(actual - math.radians(analytic[-1]), math.tau)))
        tip_error.append(linkages.ROCKER * abs(math.remainder(actual - expected, math.tau)))

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(6, 4.4), facecolor=FLOOR, sharex=True,
                                      gridspec_kw={"height_ratios": [2, 1]})
    top.plot(crank, analytic, color=MUTED, lw=2.4, label="analytic rocker (circle intersection)")
    top.plot(crank, rocker, color=ORANGE, lw=1.0, label="simulated rocker, export + equality/connect")
    _style(top, "", "rocker heading, deg", "four-bar 200/80/220/120 mm driven by its crank only")
    _legend(top)
    bottom.plot(crank, tip_error, color=BLUE, lw=1.0)
    bottom.axhline(dyn.MJCF_POSE_TOLERANCE_MM, color=EDGE, lw=0.8, ls="--")
    _style(bottom, "crank swept, deg", "rocker tip error, mm",
           f"worst {max(tip_error):.4f} mm; closure residual {run['worst_closure_residual_mm']:.4f} mm "
           f"(contract {dyn.MJCF_POSE_TOLERANCE_MM} mm)")
    _save(fig, out / "l1-four-bar.png")


def goal_frame(out: Path) -> None:
    rig = {"tip": {"body": "tip", "local_mm": [0.0, 0.0, 0.0]}, "arm_length_mm": 200.0}
    held = [{"start_s": 0.0, "end_s": 2.0, "target_mm": [100.0, 0.0, 0.0], "frame": "base"}]
    world = [{"start_s": 0.0, "end_s": 2.0, "target_mm": [100.0, 0.0, 50.0]}]
    riding, left = _drifting(True), _drifting(False)
    error = {
        (tip, goal): evaluation.reach_metrics(trace, rig, segments)["final_error_mm_max"]
        for tip, trace in (("rides", riding), ("stays", left))
        for goal, segments in (("held", held), ("world", world))
    }
    base = [poses["base"]["position_mm"] for _t, poses in riding]
    goal = [poses["tip"]["position_mm"] for _t, poses in riding]   # the riding tip sits on the held goal

    fig, ax = plt.subplots(figsize=(6, 3.8), facecolor=FLOOR)
    ax.plot([p[0] for p in base], [p[1] for p in base], color=MUTED, lw=1.0, label="base origin (slides 400 mm, turns 90°)")
    ax.plot([p[0] for p in goal], [p[1] for p in goal], color=ORANGE, lw=1.4,
            label="goal held at (100, 0) in the base = a tip riding with it")
    ax.plot([100.0], [0.0], "s", color=BLUE, ms=6, label="goal fixed in the world = a tip left behind")
    for p, q in zip(base[::25], goal[::25]):
        ax.plot([p[0], q[0]], [p[1], q[1]], color=EDGE, lw=0.8)
    ax.set_ylim(-20.0, 190.0)
    _style(ax, "world x, mm", "world y, mm",
           f"final error, held goal: rider {error['rides', 'held']:.1f} mm, left behind {error['stays', 'held']:.1f} mm\n"
           f"world goal: rider {error['rides', 'world']:.1f} mm, left behind {error['stays', 'world']:.1f} mm")
    ax.legend(fontsize=7, facecolor=FLOOR, edgecolor=EDGE, labelcolor=INK, loc="upper left")
    _save(fig, out / "r1-goal-frame.png")


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    position_tracker(out)
    load_sensor(out)
    four_bar(out)
    goal_frame(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
