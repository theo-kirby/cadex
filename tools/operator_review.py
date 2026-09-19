#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Serve the latest dispatched project in the configured Ouroboros run.

Operator deployment only; ordinary `cadex review --project` stays single-project.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Lock
import time

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cli"))
from cadex_cli.review_server import ReviewHandler, ReviewProject, STATIC_FILES


def read_json(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


class Selection:
    def __init__(self, repo, projects):
        self.repo, self.projects = Path(repo), Path(projects).resolve()
        self.lock = Lock()
        self.checked = 0
        self.value = {}
        self.project = None

    def snapshot(self):
        with self.lock:
            if time.monotonic() - self.checked < 2:
                return self.value.copy(), self.project
            try:
                config = yaml.safe_load((self.repo / '.ouroboros/config.yml').read_text())
                run = str(config['run'])
                if Path(run).name != run or run in ('.', '..'):
                    raise ValueError('invalid run name')
            except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
                # A partially written config must not switch to an unrelated project.
                return dict(self.value, selection_error='Cannot read run configuration'), self.project
            candidates = []
            for root in self.projects.iterdir():
                if not root.name.startswith(run + '-') or root.is_symlink() or not root.is_dir():
                    continue
                receipt = read_json(root / 'evidence/attempt.json')
                # Copies retain the original receipt identity; they are not live work.
                if receipt.get('project') != root.name:
                    continue
                for turn in receipt.get('turns', []):
                    window = turn.get('window', {})
                    if not window.get('dispatched'):
                        continue
                    try:
                        stamp = datetime.fromisoformat(window['read_at'])
                        if stamp.tzinfo is None:
                            continue
                        candidates.append((stamp.timestamp(), root.name, root))
                    except (KeyError, ValueError, TypeError):
                        continue
            root = max(candidates)[2] if candidates else None
            # A transient receipt write must not move backwards within the same run.
            stamp = max(candidates)[0] if candidates else 0
            if run == self.value.get('run') and stamp < self.value.get('dispatch_epoch', 0):
                root, stamp = self.project.root, self.value['dispatch_epoch']
            status = read_json(self.repo / '.ouroboros/runs' / run / 'status.json')
            if root is None:
                self.project = None
            elif self.project is None or self.project.root != root:
                self.project = ReviewProject(root)
                print(f'Following {run}: {root.name}', flush=True)
            self.value = dict(run=run, project=root.name if root else None,
                              dispatch_epoch=stamp, state=status.get('state', 'unknown'),
                              iteration=status.get('iteration'), updated=status.get('ts'))
            self.checked = time.monotonic()
            return self.value.copy(), self.project


class Handler(ReviewHandler):
    @property
    def project(self):
        return self.selected_project

    def _route(self, segments, download):
        status, self.selected_project = self.server.selection.snapshot()
        if segments == ['operator-status']:
            self._send_json(status)
            return
        if not segments or segments == ['index.html']:
            if self.selected_project is None:
                page = '<!doctype html><title>Cadex live review</title><p>Waiting for this run’s first project dispatch.</p>'
            else:
                page = STATIC_FILES['index.html'][1].read_text()
            identity = json.dumps([status.get('run'), status.get('project')]).replace('<', '\\u003c')
            page += '''<script>
(function () {
  const initial = IDENTITY;
  const label = document.createElement('div');
  label.style.cssText = 'position:fixed;bottom:0;right:0;z-index:10000;background:#17191c;color:#ddd;padding:4px 10px;font:12px sans-serif';
  label.setAttribute('role', 'status'); document.body.appendChild(label);
  async function update() {
    try {
      const response = await fetch('/operator-status', {cache:'no-store'});
      if (!response.ok) throw Error('offline');
      const s = await response.json();
      if (JSON.stringify([s.run,s.project]) !== JSON.stringify(initial)) {location.reload(); return;}
      label.textContent = s.selection_error || [s.run, 'iteration ' + (s.iteration ?? '?'), s.state, s.project || 'waiting for project'].join(' · ');
      label.title = 'Status updated: ' + (s.updated || 'unknown');
    } catch (_) { label.textContent = 'Live run status unavailable — reconnecting'; }
  }
  update(); setInterval(update, 3000);
})();
</script>'''.replace('IDENTITY', identity)
            self._send_bytes(page.encode(), 'text/html; charset=utf-8')
            return
        if self.selected_project is None:
            self._not_found('waiting for a project in the current run')
            return
        super()._route(segments, download)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--projects', type=Path, required=True)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.selection = Selection(args.repo, args.projects)
    server.serve_forever()


if __name__ == '__main__':
    main()
