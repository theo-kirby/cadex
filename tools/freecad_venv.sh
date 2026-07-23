#!/usr/bin/env bash
# SPDX-License-Identifier: LGPL-2.1-or-later
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
freecad_cmd="$repo_root/build/release/bin/FreeCADCmd"
freecad_gui="$repo_root/build/release/bin/FreeCAD"
extra_python_path=()

if [[ -x "$repo_root/.venv/bin/python" ]]; then
    venv_site="$("$repo_root/.venv/bin/python" - <<'PY'
import sysconfig
print(sysconfig.get_path("purelib"))
PY
)"
    export FREECAD_VENV="$repo_root/.venv"
    extra_python_path=(-P "$venv_site")
else
    unset FREECAD_VENV
fi

export PYTHONNOUSERSITE=1

"$freecad_cmd" "${extra_python_path[@]}" -c \
  "import FreeCAD as App; p=App.ParamGet('User parameter:BaseApp/Preferences/Dialog'); p.SetBool('DontUseNativeDialog', True); p.SetBool('DontUseNativeColorDialog', True)" \
  >/dev/null

exec "$freecad_gui" "${extra_python_path[@]}" "$@"
