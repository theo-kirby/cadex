# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: GPL-2.0-or-later
# Evidence only: invokes the existing GPL renderer in its own process.
import bpy, json, os, sys
from mesh_agent import cadex_backend, capture
root = os.path.abspath(sys.argv[sys.argv.index('--') + 1])
bpy.context.scene[cadex_backend.ROOT_PROP] = root
ok, report = cadex_backend.ensure_open(bpy.context.scene)
assert ok, report
accepted = cadex_backend.last_accepted(root)
print('ACCEPTED', json.dumps({'revision': accepted.get('revision'), 'display': sorted(accepted.get('display', {})), 'bbox': capture.model_bbox()}))
for view in ('front', 'top', 'right', 'iso'):
    spec = {'view': view} if view != 'iso' else {'view': 'custom', 'azimuth': -45, 'elevation': 35.264389682754654, 'projection': 'ortho', 'title': 'iso'}
    result, error = capture.render_blueprint(views=[spec])
    print('PROBE', json.dumps({'view': view, 'result': result, 'error': error}))
print('MULTIVIEW', capture.render_views())
