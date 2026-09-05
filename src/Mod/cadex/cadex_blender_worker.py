# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Native Blender recipe evaluator. Executed by Blender, never by cadexd.

New, independently authored geometry adapter; no shell code is imported.
Security is the launcher's OS sandbox, not a Python import allowlist.
"""

import json
from pathlib import Path
import random
import resource
import sys


def main():
    import bpy
    import numpy

    request_path, output_path = sys.argv[sys.argv.index("--") + 1:]
    request = json.loads(Path(request_path).read_text())
    version = ".".join(str(n) for n in bpy.app.version)
    if request.get("schema") != "cadex-blender-recipe-v1":
        raise ValueError("Unknown Blender recipe schema")
    if request["version"] != version:
        raise ValueError(f"Recipe requires Blender {request['version']}; runtime is {version}.")
    resource.setrlimit(resource.RLIMIT_CPU, (80, 80))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    random.seed(request["seed"])
    numpy.random.seed(request["seed"])
    # Even factory startup has a cube, camera and light. Inputs and recipe
    # must be the entire model, independent of user startup/preferences.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 0.001
    scene.frame_set(1)
    inputs = {}
    for name, geometry in request["inputs"].items():
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(geometry["vertices"], [], geometry["triangles"])
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        scene.collection.objects.link(obj)
        inputs[name] = obj
    namespace = {"__name__": "__cadex_blender_recipe__", "bpy": bpy,
                 "inputs": inputs, "values": request["values"]}
    exec(compile(request["source"], "<cadex-blender-recipe>", "exec"), namespace, namespace)
    obj = namespace.get("result")
    if not isinstance(obj, bpy.types.Object) or obj.type != 'MESH':
        raise ValueError("Assign one Blender mesh Object to result.")
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        if len(mesh.loop_triangles) > 250_000 or len(mesh.vertices) > 750_000:
            raise ValueError("Blender output exceeds 250000 triangles / 750000 vertices.")
        matrix = evaluated.matrix_world
        vertices = [list(matrix @ vertex.co) for vertex in mesh.vertices]
        # A negative object scale reverses orientation in world coordinates.
        flip = matrix.to_3x3().determinant() < 0
        triangles = [list(reversed(t.vertices)) if flip else list(t.vertices)
                     for t in mesh.loop_triangles]
        Path(output_path).write_text(json.dumps({"vertices": vertices, "triangles": triangles},
                                                allow_nan=False, separators=(",", ":")))
    finally:
        evaluated.to_mesh_clear()


if __name__ == "__main__":
    main()
