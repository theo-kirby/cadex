#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Bump the product version (ADR-166, ADR-673).
#
#   package/bump_version.sh          0.2.0 -> 0.2.1   (patch, the default)
#   package/bump_version.sh minor    0.2.0 -> 0.3.0
#   package/bump_version.sh major    0.2.0 -> 1.0.0
#
# `VERSION` at the repo root is the product version, and the one source every
# other copy follows: the CLI's `__version__` and the MCP server's
# `serverInfo` read it, the engine payload is named from it, and this script
# writes it into `version.json` (CMake's PACKAGE_VERSION and `App.Version()`)
# and, through src/Tools/sync_version.py, into the pixi manifests.
# `test_version.py` fails if any copy drifts. The release procedure is in
# docs/cadex-release-packaging.md.

set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
current="$(tr -d '[:space:]' < "${repo}/VERSION")"
IFS=. read -r major minor patch <<< "${current}"

case "${1:-patch}" in
    patch) patch=$((patch + 1)) ;;
    minor) minor=$((minor + 1)); patch=0 ;;
    major) major=$((major + 1)); minor=0; patch=0 ;;
    *) echo "usage: $(basename "$0") [patch|minor|major]"; exit 2 ;;
esac

next="${major}.${minor}.${patch}"
printf '%s\n' "${next}" > "${repo}/VERSION"
python3 - "${repo}/version.json" "${major}" "${minor}" "${patch}" <<'PY'
import json, sys
path, major, minor, patch = sys.argv[1], *map(int, sys.argv[2:])
with open(path, encoding="utf-8") as f:
    data = json.load(f)
data.update(version_major=major, version_minor=minor, version_patch=patch)
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
(cd "${repo}" && python3 src/Tools/sync_version.py --update >/dev/null)
echo "${current} -> ${next}"
