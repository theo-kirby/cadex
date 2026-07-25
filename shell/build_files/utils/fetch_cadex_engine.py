# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Fetch, verify and stage the pinned cadex engine payload (cadex ADR-023).

Mesh ships the cadex engine inside its own bundle so Cadex mode works with
no configuration at all. This script gets that payload into a staging
directory that ``source/creator/CMakeLists.txt`` installs, under
``WITH_CADEX_ENGINE``.

Verification is not optional. The pin file carries a SHA256 per platform,
an unpinned platform is refused rather than downloaded, and a digest
mismatch is a hard error -- a shipped application bundle is the last place
an unverified binary should be able to reach.

    python build_files/utils/fetch_cadex_engine.py --stage <dir>
    python build_files/utils/fetch_cadex_engine.py --stage <dir> \\
        --from-local /path/to/cadex-engine-0.0.2-macos-arm64

``--from-local`` copies an already-built payload (for engine development)
and still validates its manifest, so the layout contract is checked on
every path into a bundle.
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import tarfile
import tempfile
import urllib.request

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PIN_FILE = os.path.join(REPO, "build_files", "cadex_engine.txt")

MANIFEST_NAME = "cadex-engine.json"
MANIFEST_SCHEMA = "cadex-engine-v1"
PROTOCOL = "cadex-cadexd-v1"


def read_pins(path=PIN_FILE):
    pins = {}
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            key, _, value = line.partition(" ")
            pins[key.strip()] = value.strip()
    return pins


def platform_key():
    system = platform.system()
    machine = platform.machine().lower()
    arch = {"x86_64": "x64", "amd64": "x64"}.get(machine, machine)
    if system == "Darwin":
        return "macos-{:s}".format(arch)
    if system == "Linux":
        return "linux-{:s}".format(arch)
    return "windows-{:s}".format(arch)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest(payload_root):
    """The layout contract, checked on every path into a bundle."""
    manifest_path = os.path.join(payload_root, MANIFEST_NAME)
    if not os.path.isfile(manifest_path):
        raise SystemExit(
            "FAIL: {:s} has no {:s}; a payload without its manifest cannot "
            "be discovered (cadex ADR-020).".format(payload_root, MANIFEST_NAME))
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise SystemExit("FAIL: unknown manifest schema {!r}".format(manifest.get("schema")))
    if manifest.get("protocol") != PROTOCOL:
        raise SystemExit(
            "FAIL: payload speaks protocol {!r}, this Mesh speaks {!r}".format(
                manifest.get("protocol"), PROTOCOL))
    for key in ("freecadcmd", "module_dir"):
        relative = manifest.get(key)
        if not isinstance(relative, str) or not relative:
            raise SystemExit("FAIL: manifest {:s} is missing or not a string".format(key))
        resolved = os.path.join(payload_root, *relative.split("/"))
        if not os.path.exists(resolved):
            raise SystemExit("FAIL: manifest {:s} points at {:s}, which does not "
                             "exist".format(key, resolved))
    print("manifest ok: cadex engine {:s}, protocol {:s}".format(
        manifest.get("version", "?"), manifest["protocol"]))
    return manifest


def stage(source_root, target):
    if os.path.isdir(target):
        shutil.rmtree(target)
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    shutil.copytree(source_root, target, symlinks=True)
    print("staged -> {:s}".format(target))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True,
                        help="Directory to place the payload in.")
    parser.add_argument("--from-local", default="",
                        help="Use an already-built payload directory instead "
                             "of downloading.")
    parser.add_argument("--platform", default="",
                        help="Override the platform key (e.g. macos-arm64).")
    args = parser.parse_args()

    if args.from_local:
        root = os.path.abspath(os.path.expanduser(args.from_local))
        if not os.path.isdir(root):
            raise SystemExit("FAIL: {:s} is not a directory".format(root))
        validate_manifest(root)
        stage(root, args.stage)
        return 0

    pins = read_pins()
    key = args.platform or platform_key()
    version = pins.get("version")
    base_url = pins.get("base_url", "").rstrip("/")
    expected = pins.get(key, "unpinned")
    if not version or not base_url:
        raise SystemExit("FAIL: build_files/cadex_engine.txt lacks version or base_url")
    if expected in ("", "unpinned"):
        raise SystemExit(
            "FAIL: no SHA256 pinned for {:s} in build_files/cadex_engine.txt.\n"
            "An unverified engine payload will not be staged into a bundle. "
            "Pin the digest, or build the engine locally and pass "
            "--from-local.".format(key))

    name = "cadex-engine-{:s}-{:s}".format(version, key)
    url = "{:s}/{:s}/{:s}.tar.gz".format(base_url, version, name)
    workdir = tempfile.mkdtemp(prefix="cadex-engine-")
    archive = os.path.join(workdir, name + ".tar.gz")
    try:
        print("fetching {:s}".format(url))
        urllib.request.urlretrieve(url, archive)
        found = sha256(archive)
        if found != expected:
            raise SystemExit(
                "FAIL: digest mismatch for {:s}\n  expected {:s}\n  found    "
                "{:s}".format(name, expected, found))
        print("sha256 ok: {:s}".format(found))
        with tarfile.open(archive) as tar:
            tar.extractall(workdir)
        root = os.path.join(workdir, name)
        validate_manifest(root)
        stage(root, args.stage)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
