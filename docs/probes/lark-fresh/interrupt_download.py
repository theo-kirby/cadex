"""Abort retained-video downloads against the PERSISTENT dashboard, then resume.

usage: interrupt_download.py PROJECT RUN URL SERVER_LOG [--attempts N]
Never starts or stops a server. Opens the run's first retained video as a
download over URL, reads only the response head, then resets the connection
the way a cancelled browser download does -- N times, concurrently with the
server's ordinary polling clients. Then asks for the file's second half with a
byte range, as a resumed download would, and for the whole file. Reports what
each attempt received, that the server's log gained no traceback, and that
the resumed and whole responses are byte-identical to the retained file.
Prints one JSON object; the caller composes the evidence receipt (ADR-324).
"""
from pathlib import Path
import hashlib, json, socket, struct, sys, time, urllib.request
from urllib.parse import urlsplit
project = Path(sys.argv[1]).resolve(); run = sys.argv[2]; url = sys.argv[3].rstrip('/'); log = Path(sys.argv[4])
attempts = int(sys.argv[sys.argv.index('--attempts') + 1]) if '--attempts' in sys.argv else 3
video = json.loads((project / 'runs' / run / 'video.json').read_text())['videos'][0]
movie = project / 'runs' / run / video['path']
size = movie.stat().st_size
assert hashlib.sha256(movie.read_bytes()).hexdigest() == video['sha256']
before = log.read_text()
parts = urlsplit(url)
path = f'/video/run/{run}/0?download=1'
received = []
for _ in range(attempts):
    with socket.create_connection((parts.hostname, parts.port), timeout=10) as sock:
        sock.sendall(f'GET {path} HTTP/1.1\r\nHost: review\r\n\r\n'.encode('ascii'))
        head = sock.recv(512)
        assert head.startswith(b'HTTP/1.0 200') or head.startswith(b'HTTP/1.1 200'), head[:40]
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
    received.append(len(head))
    time.sleep(0.2)
time.sleep(1.0)
resume_from = size // 2
request = urllib.request.Request(url + f'/video/run/{run}/0', headers={'Range': f'bytes={resume_from}-'})
with urllib.request.urlopen(request, timeout=30) as response:
    assert response.status == 206, response.status
    content_range = response.headers['Content-Range']
    tail = response.read()
assert content_range == f'bytes {resume_from}-{size - 1}/{size}', content_range
assert tail == movie.read_bytes()[resume_from:]
with urllib.request.urlopen(url + path, timeout=30) as response:
    disposition = response.headers['Content-Disposition']
    whole = response.read()
assert hashlib.sha256(whole).hexdigest() == video['sha256']
assert disposition == f'attachment; filename="{movie.name}"', disposition
after = log.read_text()
added = after[len(before):]
assert 'Traceback' not in after and 'Exception occurred' not in after, after[-2000:]
print(json.dumps({
    'run': run, 'video': movie.name, 'bytes': size, 'sha256': video['sha256'],
    'aborted_attempts': attempts, 'head_bytes_received': received,
    'server_log': log.name, 'server_log_lines_before': before.count('\n'), 'server_log_lines_added': added.count('\n'),
    'server_log_has_traceback': False,
    'resumed_from_byte': resume_from, 'resumed_content_range': content_range, 'resumed_tail_matches': True,
    'whole_download_sha256_matches': True, 'mid_transfer_interrupted': size > (1 << 20),
}))
