# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The re-export probe's own two pieces, on answers stated before they run.

`reexport_smoke.py` is mostly the shipped `cadex smoke` with one substitution:
the digest-checked bundle comes from a named attempt directory instead of the
accepted pin. That substitution is the part that can be wrong on its own — a
reader that skipped the digest check, or followed an artifact path out of the
attempt, would smoke something other than what it claims to — so it is what
these fixtures hold. The other piece, `compare_attempts`, is what turns "the
project digest moved" into "these outputs moved it", and it has to find
exactly the changed one among unchanged siblings.

Nothing here runs an engine or MuJoCo: the attempts are hand-written.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[2] / 'docs/probes/ot7/runner/reexport_smoke.py'
spec = importlib.util.spec_from_file_location('ot7_reexport_smoke', PATH)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

from cadex_cli.smoke import SmokeError  # noqa: E402  (after the probe's sys.path insert)


def attempt(root: Path, name: str, *, model=b'<mujoco/>', brep=b'BREP-ONE',
            definition=None, wrong_digest=False, artifact_path=None, ok=True):
    """One attempt directory: a BREP output, an MJCF output, a result.json."""

    staging = root / name
    (staging / 'outputs').mkdir(parents=True)
    (staging / 'outputs/part-shape.brep').write_bytes(brep)
    (staging / 'outputs/model-model.xml').write_bytes(model)
    outputs = [
        {'name': 'part', 'artifact_kind': 'brep',
         'artifact_path': 'outputs/part-shape.brep',
         'artifact_sha256': hashlib.sha256(brep).hexdigest(),
         'definition': definition or {'op': 'box'}},
        {'name': 'model', 'artifact_kind': 'assembly_mjcf_xml',
         'artifact_path': artifact_path or 'outputs/model-model.xml',
         'artifact_sha256': ('0' * 64 if wrong_digest
                             else hashlib.sha256(model).hexdigest()),
         'definition': {'op': 'mjcf'}},
    ]
    (staging / 'result.json').write_text(json.dumps(
        {'ok': ok, 'digest': hashlib.sha256(model + brep).hexdigest(), 'outputs': outputs}))
    return staging


def project(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / 'script.json').write_text(json.dumps(
        {'schema': 'cadex-project-script-v1', 'accepted_revision': 'rev',
         'accepted_digest': 'accepted-digest-that-no-rebuild-matches'}))
    return root


def test_bundle_reads_the_named_attempt_not_the_accepted_pin(tmp_path):
    """The point of the probe: a digest the project rejects is still read."""

    root = project(tmp_path / 'design')
    staging = attempt(tmp_path / 'design/script_artifacts/rev', 'attempt-new')
    state, items, display = probe.bundle_from(staging)(root, tmp_path / 'out')
    assert state['accepted_digest'] == 'accepted-digest-that-no-rebuild-matches'
    assert sorted(items) == ['model', 'part']
    assert sorted(display) == ['model', 'part']
    copied = Path(display['model']['artifact_path'])
    assert copied.parent == tmp_path / 'out'
    assert copied.read_bytes() == b'<mujoco/>'
    assert (tmp_path / 'out/part-shape.brep').read_bytes() == b'BREP-ONE'


def test_bundle_refuses_an_artifact_that_does_not_hash_to_its_entry(tmp_path):
    root = project(tmp_path / 'design')
    staging = attempt(tmp_path / 'design/script_artifacts/rev', 'attempt-new',
                      wrong_digest=True)
    with pytest.raises(SmokeError, match='digest mismatch: model'):
        probe.bundle_from(staging)(root, tmp_path / 'out')


def test_bundle_refuses_an_artifact_path_leaving_the_attempt(tmp_path):
    root = project(tmp_path / 'design')
    (tmp_path / 'design/script_artifacts/rev').mkdir(parents=True)
    (tmp_path / 'design/script_artifacts/rev/elsewhere.xml').write_bytes(b'<mujoco/>')
    staging = attempt(tmp_path / 'design/script_artifacts/rev', 'attempt-new',
                      artifact_path='../elsewhere.xml')
    with pytest.raises(SmokeError, match='escaping retained artifact: model'):
        probe.bundle_from(staging)(root, tmp_path / 'out')


def test_bundle_refuses_an_attempt_that_did_not_build_and_an_unsafe_out(tmp_path):
    root = project(tmp_path / 'design')
    failed = attempt(tmp_path / 'design/script_artifacts/rev', 'attempt-failed', ok=False)
    with pytest.raises(SmokeError, match='did not build'):
        probe.bundle_from(failed)(root, tmp_path / 'out')
    staging = attempt(tmp_path / 'design/script_artifacts/rev', 'attempt-new')
    for unsafe in (root, staging / 'outputs'):
        with pytest.raises(SmokeError, match='must not overwrite'):
            probe.bundle_from(staging)(root, unsafe)


def test_compare_names_the_one_output_whose_bytes_moved(tmp_path):
    """Two attempts of the same revision: same BREP, a re-exported model."""

    first = attempt(tmp_path, 'attempt-old', model=b'<mujoco version="old"/>')
    second = attempt(tmp_path, 'attempt-new', model=b'<mujoco version="new"/>')
    row = probe.compare_attempts(first, second)
    assert row['outputs'] == 2
    assert row['digests'][0] != row['digests'][1]
    assert [item['output'] for item in row['changed']] == ['model']
    assert row['changed'][0]['artifact']['kind'] == 'assembly_mjcf_xml'
    assert row['changed'][0]['artifact']['first_sha256'] == hashlib.sha256(
        b'<mujoco version="old"/>').hexdigest()


def test_compare_sees_a_changed_recipe_and_an_identical_pair(tmp_path):
    first = attempt(tmp_path, 'attempt-old')
    same = attempt(tmp_path, 'attempt-same')
    edited = attempt(tmp_path, 'attempt-edited', definition={'op': 'cylinder'})
    assert probe.compare_attempts(first, same)['changed'] == []
    assert probe.compare_attempts(first, edited)['changed'] == [
        {'output': 'part', 'definition': True}]
