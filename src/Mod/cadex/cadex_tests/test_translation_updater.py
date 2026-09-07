# SPDX-License-Identifier: LGPL-2.1-or-later
"""Offline maintenance-command coverage; never use credentials or Crowdin."""
import ast
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock
import zipfile

import pytest

SOURCE = Path(__file__).resolve().parents[3] / 'Tools' / 'updatecrowdin.py'


@pytest.fixture
def updater(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, 'PySide6', SimpleNamespace(QtCore=Mock()))
    tree = ast.parse(SOURCE.read_text())
    dispatch = tree.body.pop()
    ns = {'__name__': 'offline_updater', '__file__': str(SOURCE)}
    exec(compile(tree, str(SOURCE), 'exec'), ns)
    ns['load_token'] = Mock(return_value='synthetic-token')
    ns['urlopen'] = Mock(side_effect=AssertionError('network forbidden'))
    ns['urlretrieve'] = Mock(side_effect=AssertionError('network forbidden'))
    ns['updateTranslatorCpp'] = Mock(side_effect=AssertionError('GUI writer forbidden'))
    monkeypatch.setenv('CROWDIN_TOKEN', 'synthetic-token')
    monkeypatch.setenv('CROWDIN_PROJECT_ID', 'synthetic-project')
    service = Mock()
    service.status.return_value = [
        {'languageId': lang, 'translationProgress': progress, 'approvalProgress': 0}
        for lang, progress in [('sv-SE', 80), ('de', 25), ('fr', 30)]]
    ns['CrowdinUpdater'] = Mock(return_value=service)

    def run(*args):
        monkeypatch.setattr(sys, 'argv', [str(SOURCE), *args])
        ns['__name__'] = '__main__'
        exec(compile(ast.Module(body=[dispatch], type_ignores=[]), str(SOURCE), 'exec'), ns)
    return ns, service, run


def test_retired_command_does_not_request_progress(updater, capsys):
    ns, service, run = updater
    run('updateTranslator')
    assert 'updateTranslator is retired' in capsys.readouterr().out
    assert service.mock_calls == []
    ns['updateTranslatorCpp'].assert_not_called()
    ns['load_token'].assert_called_once_with()


@pytest.mark.parametrize('command', ['apply', 'install'])
def test_apply_installs_languages_without_gui_writer(updater, command):
    ns, service, run = updater
    ns['applyTranslations'] = Mock()
    run(command)
    ns['applyTranslations'].assert_called_once_with(['sv-SE', 'fr'])
    service.status.assert_called_once_with()
    ns['updateTranslatorCpp'].assert_not_called()


@pytest.mark.parametrize('command', ['status', 'build', 'build-status', 'download', 'update', 'upload', 'gather'])
def test_retained_dispatch(updater, monkeypatch, command):
    ns, service, run = updater
    service.build_status.return_value = [{'id': '42', 'progress': 100, 'status': 'finished'}]
    ns['glob'] = SimpleNamespace(glob=Mock(return_value=['../App.ts', '../App_sv.ts', '../Draft.ts']))
    gather = Mock()
    monkeypatch.setitem(sys.modules, 'updatets', SimpleNamespace(main=gather))
    run(command)
    if command in ('update', 'upload'):
        assert service.update.call_args.args[0] == [ns['TsFile']('App.ts', '../App.ts'), ns['TsFile']('draft.ts', '../Draft.ts')]
    elif command == 'gather':
        gather.assert_called_once_with()
    elif command == 'download':
        service.download.assert_called_once_with('42')
    else:
        getattr(service, command.replace('-', '_')).assert_called_once_with()


def test_archive_app_base_and_swedish_qrc(updater, tmp_path):
    ns, _, _ = updater
    locations = []
    for family in ('App', 'Base', 'Tux'):
        target = tmp_path / family
        target.mkdir()
        qrc = target / (family + '.qrc')
        if family != 'Base':
            qrc.write_text('<RCC>\n<qresource>\n</qresource>\n</RCC>\n')
        locations.append([family, str(target), str(qrc)])
    ns['locations'] = locations
    extracted = tmp_path / 'extracted'
    extracted.mkdir()
    ns['tempfile'] = SimpleNamespace(mkdtemp=lambda: str(extracted))
    def lrelease(args, timeout):
        assert args[0] == 'lrelease' and timeout == 5
        Path(args[1]).with_suffix('.qm').write_bytes(b'synthetic-qm')
    ns['subprocess'] = SimpleNamespace(run=Mock(side_effect=lrelease))
    with zipfile.ZipFile(tmp_path / 'freecad.zip', 'w') as archive:
        for family in ('App', 'Base', 'Tux'):
            archive.writestr('sv-SE/' + family + '.ts', family + ' Swedish fixture')
    ns['applyTranslations'](['sv-SE'])
    assert Path.cwd() == tmp_path
    for family in ('App', 'Base', 'Tux'):
        assert (tmp_path / family / (family + '_sv.ts')).read_text() == family + ' Swedish fixture'
    ns['subprocess'].run.assert_called_once()
    qrc = tmp_path / 'Tux' / 'Tux.qrc'
    ns['updateqrc'](str(qrc), 'sv-SE')
    assert qrc.read_text().count('Tux_sv.qm') == 1
    assert not (tmp_path / 'Base' / 'Base.qrc').exists()
    ns['updateTranslatorCpp'].assert_not_called()
