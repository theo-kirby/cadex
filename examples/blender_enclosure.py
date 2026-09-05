# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

# One project script: exact mounting rails and a Blender-native shell.
# Dimensions and attachment frames cross as values; CAD cutters cross as meshes.
p = params(
    mount_spacing=num(42, unit="mm", min=30, max=70, step=1),
    length=num(80, unit="mm", min=60, max=120, step=1),
    height=num(28, unit="mm", min=20, max=45, step=1),
    wall=num(2, unit="mm", min=1.5, max=4, step=0.5),
)
left = part.box(6, p.length, 4, origin=[-p.mount_spacing / 2 - 3, -p.length / 2, 0])
right = part.box(6, p.length, 4, origin=[p.mount_spacing / 2 - 3, -p.length / 2, 0])
mounts = part.compound([left, right])
# The interior envelope is deliberately explicit; Blender subtracts it after
# evaluating the rounded outer body, preserving the declared mounting space.
clearance = part.box(p.mount_spacing + 8, p.length + 2, 9,
                     origin=[-p.mount_spacing / 2 - 4, -p.length / 2 - 1, -5])
skin = mesh.blender('''
import bmesh
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2)
for vertex in bm.verts:
    vertex.co.x *= values["width"] / 2
    vertex.co.y *= values["length"] / 2
    vertex.co.z *= values["height"] / 2
    vertex.co.z += values["height"] / 2
data = bpy.data.meshes.new("enclosure_cage")
bm.to_mesh(data)
bm.free()
result = bpy.data.objects.new("enclosure", data)
bpy.context.scene.collection.objects.link(result)
rounded = result.modifiers.new("rounded_body", 'BEVEL')
rounded.width = 7
rounded.segments = 5
rounded.affect = 'EDGES'
hollow = result.modifiers.new("wall", 'SOLIDIFY')
hollow.thickness = values["wall"]
hollow.offset = -1
opening = result.modifiers.new("mounting_clearance", 'BOOLEAN')
opening.operation = 'DIFFERENCE'
opening.solver = 'EXACT'
opening.object = inputs["clearance"]
''', version="5.3.0", inputs={"clearance": mesh.from_shape(clearance)},
    values={"width": p.mount_spacing + 20, "length": p.length + 16,
            "height": p.height, "wall": p.wall,
            "mount_frames": {"left": [-p.mount_spacing / 2, 0, 4],
                             "right": [p.mount_spacing / 2, 0, 4]}})
result = {"mounts": mounts, "skin": skin, "skin_check": mesh.check(skin)}
