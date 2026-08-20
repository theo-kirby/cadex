# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Runs ONE Part Design eval case inside Blender, driving a real Claude Code
backend (real API calls — costs money; see README.md). Invoked by runner.py:

    blender --background --factory-startup --python eval_blender.py -- \
        --case single_gear [--model claude-opus-5] [--results-dir results]

Scoring is fully local (no LLM judging), out of 100:
    30  turn completes + rebuild-on-rerun is deterministic
    30  every part manifold, watertight, no self-intersections
    15  part count within the expected range
    15  required parameters declared
    10  bbox/size sanity + STL export smoke test

Writes <results-dir>/<case>.json with the rubric breakdown, the final model
script, the tool-call count and wall time.
"""

import argparse
import json
import os
import sys
import tempfile
import time

import bpy
from mathutils import Vector

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))
sys.path.insert(0, _HERE)

import mesh_agent  # noqa: E402
from mesh_agent import agent as agent_module  # noqa: E402
from mesh_agent import model as model_module  # noqa: E402
from mesh_agent import modes as modes_module  # noqa: E402
from mesh_agent import tools as tools_module  # noqa: E402
from mesh_agent import validation as validation_module  # noqa: E402
from mesh_agent.backend import ClaudeCodeBackend, find_claude  # noqa: E402

import cases  # noqa: E402

TURN_TIMEOUT = 600.0
TOOL_CAP = 40


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--model", default="claude-opus-5")
    parser.add_argument("--results-dir",
                        default=os.path.join(_HERE, "results"))
    return parser.parse_args(argv)


def run_turn(agent, prompt, timeout):
    started = agent.start_turn(prompt)
    deadline = time.monotonic() + timeout
    while agent.busy and time.monotonic() < deadline:
        agent.drain()
        time.sleep(0.01)
    if agent.busy:
        agent.cancel()
        # Give the backend a moment to wind down, then drain the exit event.
        settle = time.monotonic() + 5.0
        while agent.busy and time.monotonic() < settle:
            agent.drain()
            time.sleep(0.05)
    return started and not agent.busy


def model_parts():
    collection = bpy.data.collections.get(model_module.COLLECTION_NAME)
    if collection is None:
        return []
    return [obj for obj in collection.all_objects if obj.type == 'MESH']


def part_snapshot():
    return sorted((obj.name, len(obj.data.vertices)) for obj in model_parts())


def score_case(case, completed, tool_calls):
    """Local rubric. Returns (score, breakdown dict, details dict)."""
    breakdown = {}
    details = {}

    # -- 30: completion + determinism
    breakdown["completed"] = 15 if completed else 0
    snapshot_before = part_snapshot()
    rebuild_ok, rebuild_report = model_module.rebuild()
    deterministic = rebuild_ok and part_snapshot() == snapshot_before
    breakdown["deterministic_rebuild"] = 15 if deterministic else 0
    details["rebuild_report_head"] = (rebuild_report or "").splitlines()[:1]

    # -- 30: geometry quality (fraction of parts that are clean)
    parts = model_parts()
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    part_stats = []
    clean = 0
    for obj in parts:
        stats = validation_module.analyze_object(obj, depsgraph)
        issues = validation_module._issues(stats)
        part_stats.append({
            "name": stats["name"],
            "dimensions": [round(v, 3) for v in stats["dimensions"]],
            "tris": stats["tris"],
            "issues": {key: count for key, count in issues},
        })
        if not issues:
            clean += 1
    breakdown["geometry"] = round(30 * clean / len(parts)) if parts else 0
    details["parts"] = part_stats

    # -- 15: part count
    low, high = case["part_count"]
    breakdown["part_count"] = 15 if low <= len(parts) <= high else 0
    details["part_count"] = len(parts)

    # -- 15: required parameters
    declared = {spec["id"] for spec in
                model_module.load_specs(bpy.context.scene)}
    required = case["required_params"]
    present = [pid for pid in required if pid in declared]
    breakdown["params"] = (round(15 * len(present) / len(required))
                           if required else 15)
    details["declared_params"] = sorted(declared)
    details["missing_params"] = [p for p in required if p not in declared]

    # -- 10: bbox sanity (5) + STL export smoke (5)
    bbox_ok = bool(parts)
    if parts:
        corners = []
        for obj in parts:
            for corner in obj.bound_box:
                corners.append(obj.matrix_world @ Vector(corner))
        spans = [max(c[i] for c in corners) - min(c[i] for c in corners)
                 for i in range(3)]
        details["assembly_bbox"] = [round(s, 2) for s in spans]
        bbox_ok = all(span <= limit + 1e-3
                      for span, limit in zip(spans, case["bbox_max"]))
        for stats in part_stats:
            if max(stats["dimensions"]) < case["min_part_size"]:
                bbox_ok = False
    breakdown["bbox"] = 5 if bbox_ok else 0

    stl_ok = False
    if parts:
        stl_dir = os.path.join(tempfile.gettempdir(),
                               "mesh_eval_stl_" + case["id"])
        content, is_error = tools_module.execute(
            "export_stl", {"directory": stl_dir})
        stl_ok = not is_error
        details["stl_result_head"] = content[0]["text"].splitlines()[:1]
    breakdown["stl_export"] = 5 if stl_ok else 0

    details["tool_calls"] = tool_calls
    return sum(breakdown.values()), breakdown, details


def main():
    args = parse_args()
    case = cases.get_case(args.case)

    claude_path = find_claude()
    if claude_path is None:
        print("eval: claude CLI not found", file=sys.stderr)
        sys.exit(2)

    mesh_agent.register()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.mesh_agent_mode = 'PART_DESIGN'

    agent = agent_module.Agent()
    agent.tool_cap_override = TOOL_CAP

    def factory(bridge):
        return ClaudeCodeBackend(
            claude_path=claude_path,
            model=args.model,
            system_prompt=modes_module.system_prompt_for('PART_DESIGN'),
            tool_names=[tool["name"] for tool in tools_module.list_tools()],
            bridge_port=bridge.port,
            bridge_token=bridge.token,
        )

    agent.backend_factory = factory
    agent._undo_push = lambda message: None

    started = time.monotonic()
    try:
        completed = run_turn(agent, case["prompt"], TURN_TIMEOUT)
        wall_time = time.monotonic() - started
        score, breakdown, details = score_case(case, completed,
                                               agent._tool_calls)
    finally:
        agent.shutdown()

    result = {
        "case": case["id"],
        "model": args.model,
        "score": score,
        "breakdown": breakdown,
        "details": details,
        "completed": completed,
        "backend_error": agent.last_error,
        "wall_time_s": round(wall_time, 1),
        "script": model_module.get_script(),
        "transcript_tail": [
            {"role": message.role, "text": message.text[-500:]}
            for message in agent.history.messages[-8:]
        ],
    }

    os.makedirs(args.results_dir, exist_ok=True)
    path = os.path.join(args.results_dir, case["id"] + ".json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=1)
    print("eval: {:s} scored {:d}/100 -> {:s}".format(
        case["id"], score, path))


if __name__ == "__main__":
    main()
