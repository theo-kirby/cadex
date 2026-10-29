# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""CLI review reads must not replay the accepted script (ADR-875)."""
import json

from cadex_cli.__main__ import main


def test_review_commands_do_not_create_build_attempts(engine, tmp_path):
    root = tmp_path / 'project'
    source = tmp_path / 'source.py'
    source.write_text('''
p = params(width=num(20, min=10, max=30))
box = part.box(p.width, 12, 8)
base = assembly.component(box, grounded=True)
asm = assembly.assembly([base])
solved = assembly.solve(asm)
result = {"box": box, "base": base, "asm": asm, "solved": solved}
''')
    assert main(['script', '--project', str(root), '--set', str(source), '--json']) == 0
    def attempts():
        return set((root / 'script_artifacts').glob('*/attempt-*'))
    before = attempts()
    state = json.loads((root / 'script.json').read_text())
    for command in ['inventory', 'render', 'section', 'asset']:
        extra = ['--plane', 'XY'] if command == 'section' else []
        assert main([command, '--project', str(root), '--json', *extra]) == 0
        assert attempts() == before, command
        current = json.loads((root / 'script.json').read_text())
        assert current['accepted_digest'] == state['accepted_digest']
    assert main(['params', '--project', str(root), '--set', 'width=22', '--json']) == 0
    assert len(attempts() - before) == 1

    # Older accepted attempts may have no retained triangles: one rebuild
    # must still make the review usable, without a preliminary restore.
    current = json.loads((root / 'script.json').read_text())
    result_path = root / current['accepted_attempt']['staging'] / 'result.json'
    result = json.loads(result_path.read_text())
    display = next(o['display'] for o in result['outputs'] if isinstance(o.get('display'), dict))
    mesh = result_path.parent / display['artifact_path']
    saved = mesh.read_bytes()
    mesh.unlink()
    before = attempts()
    assert main(['render', '--project', str(root), '--json']) == 0
    assert len(attempts() - before) == 1
    mesh.write_bytes(saved)
    current = json.loads((root / 'script.json').read_text())
    result_path = root / current['accepted_attempt']['staging'] / 'result.json'
    result = json.loads(result_path.read_text())
    for output in result['outputs']:
        output['display'] = None
    result_path.write_text(json.dumps(result))
    before = attempts()
    assert main(['render', '--project', str(root), '--json']) == 0
    assert len(attempts() - before) == 1
