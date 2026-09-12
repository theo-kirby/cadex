# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A headless Chromium driven over its DevTools pipe, for the review tests.

No Playwright, no Selenium, no websocket library: Chromium started with
``--remote-debugging-pipe`` speaks the DevTools protocol as NUL-separated
JSON on file descriptors 3 (in) and 4 (out), and that is enough to load a
page, evaluate JavaScript in it, send real mouse events and take a
screenshot — which is all a dashboard test needs. The browser is whatever
Chromium the machine has (``CADEX_BROWSER``, then PATH, then the
Playwright cache); tests skip when there is none, the way engine tests
skip without an engine.

Downloads are collected where the browser can actually write them. A snap
Chromium (Ubuntu's default) runs under confinement: its ``/tmp`` is a private
namespace, so a download "completed" into a pytest ``tmp_path`` lands where no
test can read it, and a hidden directory under ``$HOME`` is refused outright —
Chromium reports ``canceled`` after receiving every byte. ``Page.download``
therefore saves into a directory chosen for the browser at hand, waits on the
browser's own download-progress events rather than polling the filesystem, and
fails naming the state it saw instead of timing out on a file that never comes.
"""

from __future__ import annotations

import base64
import glob
import json
import os
from pathlib import Path
import select
import shutil
import signal
import tempfile
import time
from typing import Any, NamedTuple

CANDIDATES = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable",
              "chrome", "chrome-headless-shell")
PLAYWRIGHT_GLOB = "~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"


def find_browser() -> str | None:
    """A Chromium executable, or None."""

    explicit = os.environ.get("CADEX_BROWSER", "")
    if explicit:
        return explicit if os.access(explicit, os.X_OK) else None
    for name in CANDIDATES:
        found = shutil.which(name)
        if found:
            return found
    cached = sorted(glob.glob(os.path.expanduser(PLAYWRIGHT_GLOB)))
    return cached[-1] if cached else None


def snap_confined(executable: str) -> bool:
    """True when ``executable`` is a snap: ``/snap/bin/<name>`` or the snap launcher."""

    path = Path(executable)
    return path.parts[:2] == ("/", "snap") or os.path.basename(os.path.realpath(executable)) == "snap"


class BrowserError(RuntimeError):
    pass


class Download(NamedTuple):
    """One finished download: the file, and what the browser said it wrote."""

    path: Path
    url: str
    received_bytes: int
    total_bytes: int


class HeadlessBrowser:
    """One headless Chromium; ``page(url)`` opens a tab on a URL."""

    def __init__(self, executable: str, *, width: int = 1280, height: int = 900) -> None:
        self.executable = executable
        self.confined = snap_confined(executable)
        self._downloads: str | None = None
        self.profile = tempfile.mkdtemp(prefix="cadex-review-browser-")
        self._log = open(os.path.join(self.profile, "browser.log"), "wb")
        r_in, w_in = os.pipe()
        r_out, w_out = os.pipe()
        null = os.open(os.devnull, os.O_RDWR)
        argv = [executable, "--headless=new", "--remote-debugging-pipe", "--disable-gpu",
                "--enable-unsafe-swiftshader", "--no-sandbox", "--no-first-run",
                "--disable-dev-shm-usage", f"--window-size={width},{height}",
                f"--user-data-dir={self.profile}", "about:blank"]
        # posix_spawn, because subprocess closes descriptors 3 and 4 after
        # the pre-exec hook would have placed the pipe ends there.
        self.pid = os.posix_spawn(executable, argv, os.environ, file_actions=[
            (os.POSIX_SPAWN_DUP2, null, 0), (os.POSIX_SPAWN_DUP2, null, 1),
            (os.POSIX_SPAWN_DUP2, self._log.fileno(), 2),
            (os.POSIX_SPAWN_DUP2, r_in, 3), (os.POSIX_SPAWN_DUP2, w_out, 4),
        ])
        for fd in (r_in, w_out, null):
            os.close(fd)
        self._w_in, self._r_out = w_in, r_out
        self._buffer = b""
        self._next_id = 0
        self._events: list[dict[str, Any]] = []

    # -- protocol ----------------------------------------------------------

    def send(self, method: str, params: dict[str, Any] | None = None,
             session: str | None = None, timeout: float = 30.0) -> dict[str, Any]:
        self._next_id += 1
        message: dict[str, Any] = {"id": self._next_id, "method": method, "params": params or {}}
        if session:
            message["sessionId"] = session
        os.write(self._w_in, json.dumps(message).encode("utf-8") + b"\0")
        deadline = time.monotonic() + timeout
        while True:
            for index, item in enumerate(self._events):
                if item.get("id") == self._next_id:
                    del self._events[index]
                    return self._finish(item, method)
            self._pump(deadline, f"{method}: no reply within {timeout}s")

    def _pump(self, deadline: float, on_timeout: str) -> None:
        """Read whatever the browser has sent into ``_events``, or raise at ``deadline``."""

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BrowserError(on_timeout)
        ready, _, _ = select.select([self._r_out], [], [], remaining)
        if not ready:
            return
        chunk = os.read(self._r_out, 1 << 16)
        if not chunk:
            raise BrowserError(f"browser closed the pipe; log: {self.log_tail()}")
        self._buffer += chunk
        while b"\0" in self._buffer:
            raw, _, self._buffer = self._buffer.partition(b"\0")
            self._events.append(json.loads(raw))

    def wait_event(self, method: str, session: str | None = None,
                   predicate: Any = None, timeout: float = 15.0) -> dict[str, Any]:
        """The params of the next ``method`` event (on ``session``) satisfying ``predicate``."""

        deadline = time.monotonic() + timeout
        while True:
            for index, item in enumerate(self._events):
                if item.get("method") != method or (session and item.get("sessionId") != session):
                    continue
                params = item.get("params") or {}
                if predicate is None or predicate(params):
                    del self._events[index]
                    return params
            self._pump(deadline, f"{method}: no such event within {timeout}s")

    def download_dir(self) -> Path:
        """A directory this browser can write downloads into and a test can read.

        A confined snap browser sees a private ``/tmp`` and may not write hidden
        paths under ``$HOME``, so it gets a visible directory under ``$HOME``;
        anything else gets the system temporary directory. Removed by ``close``.
        """

        if self._downloads is None:
            self._downloads = tempfile.mkdtemp(
                prefix="cadex-review-downloads-", dir=Path.home() if self.confined else None)
        return Path(self._downloads)

    @staticmethod
    def _finish(reply: dict[str, Any], method: str) -> dict[str, Any]:
        if "error" in reply:
            raise BrowserError(f"{method}: {reply['error']}")
        return reply.get("result") or {}

    def log_tail(self, limit: int = 800) -> str:
        try:
            return Path(self.profile, "browser.log").read_text(errors="replace")[-limit:]
        except OSError:
            return ""

    def page(self, url: str) -> "Page":
        target = self.send("Target.createTarget", {"url": "about:blank"})["targetId"]
        session = self.send("Target.attachToTarget", {"targetId": target, "flatten": True})["sessionId"]
        page = Page(self, session)
        page.send("Page.enable")
        page.send("Runtime.enable")
        page.send("Page.navigate", {"url": url})
        page.wait_for("document.readyState === 'complete'")
        return page

    def close(self) -> None:
        try:
            os.kill(self.pid, signal.SIGKILL)
            os.waitpid(self.pid, 0)
        except OSError:
            pass
        for fd in (self._w_in, self._r_out):
            try:
                os.close(fd)
            except OSError:
                pass
        self._log.close()
        shutil.rmtree(self.profile, ignore_errors=True)
        if self._downloads:
            shutil.rmtree(self._downloads, ignore_errors=True)

    def __enter__(self) -> "HeadlessBrowser":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


class Page:
    def __init__(self, browser: HeadlessBrowser, session: str) -> None:
        self.browser = browser
        self.session = session

    def send(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.browser.send(method, params, session=self.session)

    def evaluate(self, expression: str, *, await_promise: bool = False) -> Any:
        """Evaluate JavaScript in the page and return its value (by value)."""

        result = self.send("Runtime.evaluate", {
            "expression": expression, "returnByValue": True, "awaitPromise": await_promise,
        })
        if "exceptionDetails" in result:
            details = result["exceptionDetails"]
            text = (details.get("exception") or {}).get("description") or details.get("text")
            raise BrowserError(f"page script failed: {text}")
        return (result.get("result") or {}).get("value")

    def wait_for(self, expression: str, timeout: float = 15.0, interval: float = 0.1) -> Any:
        """Poll ``expression`` until truthy; return its value."""

        deadline = time.monotonic() + timeout
        while True:
            value = self.evaluate(expression)
            if value:
                return value
            if time.monotonic() > deadline:
                raise BrowserError(f"timed out waiting for {expression!r}")
            time.sleep(interval)

    def text(self, selector: str) -> str:
        return self.evaluate(
            f"(document.querySelector({json.dumps(selector)}) || {{textContent: null}}).textContent")

    def attribute(self, selector: str, name: str) -> Any:
        return self.evaluate(
            f"(function(){{var n=document.querySelector({json.dumps(selector)});"
            f"return n ? n.getAttribute({json.dumps(name)}) : null}})()")

    def click(self, selector: str) -> None:
        self.evaluate(f"document.querySelector({json.dumps(selector)}).click()")

    def download(self, selector: str, timeout: float = 15.0) -> Download:
        """Click ``selector`` and return the download it produced, once the browser has written it.

        Raises ``BrowserError`` when the browser cancels the download, naming the
        directory and the bytes it had received, so a confinement problem reads
        as one rather than as a missing file.
        """

        directory = self.browser.download_dir()
        self.send("Browser.setDownloadBehavior", {
            "behavior": "allow", "downloadPath": str(directory), "eventsEnabled": True})
        self.click(selector)
        begin = self.browser.wait_event("Browser.downloadWillBegin", self.session, timeout=timeout)
        guid = begin["guid"]
        final = self.browser.wait_event(
            "Browser.downloadProgress", self.session, timeout=timeout,
            predicate=lambda params: params.get("guid") == guid
            and params.get("state") in ("completed", "canceled"))
        if final["state"] != "completed":
            raise BrowserError(
                f"download of {begin['url']} into {directory} was {final['state']} after "
                f"{final.get('receivedBytes', 0)} of {final.get('totalBytes', 0)} bytes; "
                f"{'a snap-confined ' if self.browser.confined else 'the '}browser could not write there")
        path = directory / begin["suggestedFilename"]
        deadline = time.monotonic() + timeout
        while not path.exists():
            if time.monotonic() > deadline:
                raise BrowserError(f"download reported completed but {path} never appeared")
            time.sleep(0.05)
        return Download(path, begin["url"], int(final.get("receivedBytes", 0)),
                        int(final.get("totalBytes", 0)))

    def rect(self, selector: str) -> dict[str, float]:
        return self.evaluate(
            f"(function(){{var r=document.querySelector({json.dumps(selector)}).getBoundingClientRect();"
            f"return {{x:r.x,y:r.y,width:r.width,height:r.height}}}})()")

    def scroll_into_view(self, selector: str) -> None:
        self.evaluate(f"document.querySelector({json.dumps(selector)}).scrollIntoView({{block:'center'}})")

    def mouse(self, kind: str, x: float, y: float, **extra: Any) -> None:
        params = {"type": kind, "x": x, "y": y, "button": "left", "buttons": 1 if kind != "mouseReleased" else 0}
        params.update(extra)
        self.send("Input.dispatchMouseEvent", params)

    def drag(self, x0: float, y0: float, x1: float, y1: float, steps: int = 8) -> None:
        """A real left-button drag: press, moves, release, as the OS would send."""

        self.mouse("mousePressed", x0, y0, clickCount=1)
        for step in range(1, steps + 1):
            t = step / steps
            self.mouse("mouseMoved", x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
        self.mouse("mouseReleased", x1, y1, clickCount=1)

    def wheel(self, x: float, y: float, delta_y: float) -> None:
        self.send("Input.dispatchMouseEvent", {"type": "mouseWheel", "x": x, "y": y,
                                               "deltaX": 0, "deltaY": delta_y})

    def screenshot(self, path: str | Path) -> None:
        data = self.send("Page.captureScreenshot", {"format": "png"})["data"]
        Path(path).write_bytes(base64.b64decode(data))
