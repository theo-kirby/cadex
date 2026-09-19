# SPDX-License-Identifier: LGPL-2.1-or-later
"""Selection and live HTTP regressions for the operator deployment."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import urlopen
from http.server import ThreadingHTTPServer
from operator_review import Selection, Handler


class FollowTest(unittest.TestCase):
    def test_dispatch_identity_and_run_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / '.ouroboros').mkdir()
            config = repo / '.ouroboros/config.yml'
            config.write_text('run: ot7\n')
            projects = repo / 'projects'
            projects.mkdir()
            select = Selection(repo, projects)
            def receipt(name, timestamp, identity=None):
                root = projects / name
                (root / 'evidence').mkdir(parents=True, exist_ok=True)
                (root / 'evidence/attempt.json').write_text(json.dumps(dict(
                    project=identity or name, turns=[dict(window=dict(
                        dispatched=True, read_at=timestamp))])))
                select.checked = 0
                return root
            receipt('ot6-old', '2026-09-20T00:00:00+00:00')
            self.assertIsNone(select.snapshot()[1])
            a = receipt('ot7-a', '2026-09-19T00:00:00+00:00')
            self.assertEqual(select.snapshot()[1].root, a)
            receipt('ot7-copy', '2026-09-21T00:00:00+00:00', 'ot7-a')
            self.assertEqual(select.snapshot()[1].root, a)
            b = receipt('ot7-b', '2026-09-19T01:00:00+00:00')
            self.assertEqual(select.snapshot()[1].root, b)
            (b / 'evidence/attempt.json').write_text('{')
            select.checked = 0
            self.assertEqual(select.snapshot()[1].root, b)
            config.write_text('run: ot8\n')
            select.checked = 0
            self.assertIsNone(select.snapshot()[1])
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            server.selection = select
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                url = 'http://127.0.0.1:' + str(server.server_port)
                self.assertIn(b'Waiting for', urlopen(url).read())
                receipt('ot8-new', '2026-09-20T00:00:00+00:00')
                status = json.load(urlopen(url + '/operator-status'))
                self.assertEqual(status['project'], 'ot8-new')
                page = urlopen(url).read()
                self.assertIn(b'location.reload()', page)
                self.assertIn(b'Cadex review', page)
                self.assertEqual(urlopen(url + '/api/project').status, 200)
            finally:
                server.shutdown()
                server.server_close()
                worker.join()


if __name__ == '__main__':
    unittest.main()
