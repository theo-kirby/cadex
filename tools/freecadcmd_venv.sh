#!/usr/bin/env bash
# SPDX-License-Identifier: LGPL-2.1-or-later
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv_site="$("$repo_root/.venv/bin/python" - <<'PY'
import sysconfig
print(sysconfig.get_path("purelib"))
PY
)"

export FREECAD_VENV="$repo_root/.venv"
export PYTHONNOUSERSITE=1

exec "$repo_root/build/release/bin/FreeCADCmd" -P "$venv_site" "$@"
