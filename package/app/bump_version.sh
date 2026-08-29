#!/usr/bin/env bash
#
# Bump the product version (ADR-166).
#
#   package/app/bump_version.sh          0.0.5 -> 0.0.6   (patch, the default)
#   package/app/bump_version.sh minor    0.0.5 -> 0.1.0
#   package/app/bump_version.sh major    0.0.5 -> 1.0.0
#
# `VERSION` at the repo root is the single source of truth; the build stamps
# it into the bundle (build_app.sh stamp_version), the window title reads it
# from there, and the *build number* -- CFBundleVersion -- is the commit
# count, which increments on its own. So this script is for the deliberate
# bumps only, and committing the changed VERSION is the release act.

set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
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
echo "${current} -> ${next}"
