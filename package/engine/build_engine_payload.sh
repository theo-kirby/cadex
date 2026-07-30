#!/usr/bin/env bash
#
# Build the cadex engine payload: the headless engine, and nothing else.
#
# This repository stops producing a user-facing application in Phase 7
# (cadex ADR-020). What it produces instead is a relocatable directory that
# the Blender shell carries and finds by manifest (ADR-023):
#
#   cadex-engine-<version>-<os>-<arch>/
#     cadex-engine.json          the discovery manifest -- the whole point
#     bin/{freecadcmd,CadexGeometryWorker,python}
#     lib/                       no Qt, no PySide, no Coin
#     Mod/{cadex,Part,PartDesign,Sketcher,Assembly,Mesh,MeshPart,Import,
#          Material,Measure,Show}
#
# Descended from osx/create_bundle.sh minus the .app wrapper, the icon
# pipeline, the DMG, and the two provider-install scripts -- none of which
# exist any more (ADR-021).
#
# Usage:  package/engine/build_engine_payload.sh [<pixi-env>] [<output-dir>]
#
# CADEX_ENGINE_STAGE_ONLY=1 skips the conda-pack relocation and copies the
# environment directly. The result runs *on this machine only* -- the build
# prefix stays baked into Mach-O load commands and Python metadata -- so it
# is for local verification (the CadexEnginePayloadSmoke gate) and must
# never be shipped. Relocation needs a rattler-built conda package, where
# the engine's own files are package-managed.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "${here}/../.." && pwd)"
source_env="${1:-${repo}/.pixi/envs/default}"
out_root="${2:-${repo}/build/engine}"

version="$(sed -n 's/^ *PACKAGE_VERSION *"\([^"]*\)".*/\1/p' "${repo}/CMakeLists.txt" | head -1)"
version="${version:-0.0.0}"
case "$(uname -s)" in
    Darwin) os="macos" ;;
    Linux)  os="linux" ;;
    *)      os="windows" ;;
esac
arch="$(uname -m)"
case "${arch}" in x86_64|amd64) arch="x64" ;; esac

payload_name="cadex-engine-${version}-${os}-${arch}"
payload="${out_root}/${payload_name}"

echo "==> building ${payload_name}"
rm -rf "${payload}"
mkdir -p "${out_root}"

source_env_absolute="$(cd "${source_env}" && pwd)"
payload_absolute="${out_root}/${payload_name}"

# Relocate rather than copy: a raw copy leaves the build prefix baked into
# Mach-O load commands and Python metadata.
if [ "${CADEX_ENGINE_STAGE_ONLY:-0}" = "1" ]; then
    echo "==> STAGE ONLY: copying without relocation (not shippable)"
    mkdir -p "${payload_absolute}"
    for part in bin lib Mod share; do
        [ -d "${source_env_absolute}/${part}" ] && \
            cp -a "${source_env_absolute}/${part}" "${payload_absolute}/"
    done
else
    python "${repo}/package/rattler-build/scripts/relocate_conda_environment.py" \
        "${source_env_absolute}" \
        "${payload_absolute}"
fi

# ---------------------------------------------------------------------------
# Prune to the engine.
# ---------------------------------------------------------------------------

rm -rf "${payload}/include" "${payload}/conda-meta" "${payload}/share/doc"
find "${payload}" -name '*.a' -delete

# Binaries: the engine service host, the geometry worker, and the Python
# that runs them. No GUI binary is produced at all (ADR-022).
mv "${payload}/bin" "${payload}/bin_all"
mkdir -p "${payload}/bin"
for tool in freecadcmd FreeCADCmd CadexGeometryWorker python; do
    if [ -e "${payload}/bin_all/${tool}" ]; then
        cp -a "${payload}/bin_all/${tool}" "${payload}/bin/"
    fi
done
rm -rf "${payload}/bin_all"

# Workbenches the xscript domains actually load. Everything else FreeCAD
# ships is out of scope (docs/VISION.md) and simply is not carried.
keep_mods="cadex Part PartDesign Sketcher Assembly Mesh MeshPart Import Material Measure Show"
if [ -d "${payload}/Mod" ]; then
    for mod in "${payload}/Mod"/*; do
        name="$(basename "${mod}")"
        case " ${keep_mods} " in
            *" ${name} "*) ;;
            *) rm -rf "${mod}" ;;
        esac
    done
fi

# Qt GUI, PySide and Coin are the whole reason the payload is affordable.
#
# Note what is NOT pruned: FreeCAD's App layer links Qt6Core and Qt6Xml
# (XML parsing, string handling) and the engine inherits that, so those
# four non-GUI Qt libraries stay. The plan's "zero Qt" is not achievable
# and was never what mattered -- what mattered is that a headless engine
# carries no widget toolkit, no Python bindings for one, and no 3D
# scene-graph renderer. Verified below rather than asserted.
qt_keep="Core Xml Concurrent Network DBus"

prune_qt_libs() {
    local dir="$1"
    [ -d "${dir}" ] || return 0
    find "${dir}" -maxdepth 1 \( -name 'libQt6*' -o -name 'libQt5*' \) -print0 2>/dev/null |
    while IFS= read -r -d '' lib; do
        local base keep=0
        base="$(basename "${lib}")"
        for component in ${qt_keep}; do
            case "${base}" in libQt[65]${component}.*|libQt[65]${component}) keep=1 ;; esac
        done
        [ "${keep}" = "1" ] || rm -rf "${lib}"
    done
}

prune_qt_libs "${payload}/lib"

# FreeCAD's own GUI libraries. A BUILD_GUI=OFF build does not produce
# these at all (ADR-022); pruning them keeps a stage-only payload honest
# when it is copied from an environment that still has older ones.
# Both the shared library and the Python extension module: the binding is
# named FreeCADGui.so with no "lib" prefix, so the libFreeCADGui* pattern
# alone let a stale one survive a re-stage -- and a surviving FreeCADGui is
# not inert, it silently changes which imports succeed in the payload
# (it is what hid the headless-joint break, ADR-047).
find "${payload}/lib" -maxdepth 1 \( -name 'libFreeCADGui*' \
     -o -name 'FreeCADGui.so' -o -name 'FreeCADGui.dylib' \
     -o -name 'FreeCADGui.pyd' \) -exec rm -rf {} + 2>/dev/null || true
find "${payload}/Mod" -name '*Gui.so' -delete 2>/dev/null || true
find "${payload}/Mod" -name '*Gui.dylib' -delete 2>/dev/null || true

# Coin and Quarter render Inventor scene graphs; nothing headless draws.
find "${payload}/lib" -maxdepth 1 \( -iname 'libCoin*' -o -iname 'libQuarter*' \
    -o -iname 'libSoQt*' \) -exec rm -rf {} + 2>/dev/null || true

# Python bindings for Qt, and Qt's own plugin/QML/translation trees.
rm -rf "${payload}/lib/python"*/site-packages/PySide6 \
       "${payload}/lib/python"*/site-packages/shiboken6 \
       "${payload}/lib/python"*/site-packages/PySide2 \
       "${payload}/lib/qt6" "${payload}/lib/qml" "${payload}/plugins" \
       "${payload}/translations" "${payload}/qml"

# Development leftovers: headers, .pc files and CMake config for libraries
# nothing in the payload ever compiles against.
rm -rf "${payload}/lib/pkgconfig" "${payload}/lib/cmake" "${payload}/mkspecs" \
       "${payload}/share/qt6" "${payload}/libexec" \
       "${payload}/share/PySide6" "${payload}/share/shiboken6" \
       "${payload}/share/doc" "${payload}/share/man" "${payload}/share/Coin"
find "${payload}" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

# ---------------------------------------------------------------------------
# macOS: repair install names and rpaths for the payload's final location.
# ---------------------------------------------------------------------------

if [ "${os}" = "macos" ] && [ "${CADEX_ENGINE_STAGE_ONLY:-0}" != "1" ]; then
    python "${repo}/package/rattler-build/scripts/fix_macos_lib_paths.py" \
        --bundle-prefix "${payload_absolute}" \
        --source-prefix "${source_env_absolute}" \
        "${payload}"
    python "${repo}/package/rattler-build/scripts/relocate_macos_runtime_rpaths.py" \
        --bundle-prefix "${payload_absolute}" \
        "${payload}"
fi

# ---------------------------------------------------------------------------
# The manifest. Finding this file IS discovery (ADR-020): it names the
# binary and the module directory with manifest-relative, forward-slash
# paths, so no shell ever has to guess at a platform layout again.
# ---------------------------------------------------------------------------

freecadcmd_rel="bin/freecadcmd"
[ -e "${payload}/bin/freecadcmd" ] || freecadcmd_rel="bin/FreeCADCmd"

cat > "${payload}/cadex-engine.json" <<MANIFEST
{
  "schema": "cadex-engine-v1",
  "version": "${version}",
  "protocol": "cadex-cadexd-v1",
  "freecadcmd": "${freecadcmd_rel}",
  "module_dir": "Mod/cadex"
}
MANIFEST

# ---------------------------------------------------------------------------
# Prove it.
# ---------------------------------------------------------------------------

test -f "${payload}/${freecadcmd_rel}" || { echo "FAIL: no engine binary"; exit 1; }
test -f "${payload}/Mod/cadex/cadexd.py" || { echo "FAIL: no cadexd module"; exit 1; }

# The gate: no widget toolkit, no Qt Python bindings, no scene-graph
# renderer anywhere in the payload. Qt6Core/Xml/Concurrent/Network are
# expected and allowed -- FreeCAD's App layer links them.
leaked="$(find "${payload}" \( \
        -iname 'libQt[65]Gui*' -o -iname 'libQt[65]Widgets*' \
        -o -iname 'libQt[65]Quick*' -o -iname 'libQt[65]Qml*' \
        -o -iname 'libQt[65]OpenGL*' -o -iname 'libQt[65]Svg*' \
        -o -iname 'libQt[65]PrintSupport*' -o -iname 'libQt[65]UiTools*' \
        -o -iname 'libQt[65]Designer*' \
        -o -iname 'libCoin*' -o -iname 'libQuarter*' -o -iname 'libsoqt*' \
        -o -iname 'PySide[26]' -o -iname 'shiboken[26]' \
    \) -print 2>/dev/null | head -20 || true)"
if [ -n "${leaked}" ]; then
    echo "FAIL: a GUI dependency leaked into the headless engine payload:"
    echo "${leaked}"
    exit 1
fi

echo "==> Qt libraries carried (expected: Core, Xml, Concurrent, Network):"
ls "${payload}/lib" 2>/dev/null | grep -i '^libQt' | sort || true

# The dynamics engine has to be in the payload, not merely in the developer's
# environment (cadex ADR-060). It reaches here by two different routes and
# both have silently dropped it before: the relocated path carries it only
# because CARRIED_PYPI_PACKAGES names it, and the stage-only path only
# because it copies lib/ wholesale. Asserted rather than assumed, and
# asserted by *importing* -- a present directory proves nothing about a
# bundled dylib whose rpath was just rewritten.
mujoco_version="$("${payload}/bin/python" -c 'import mujoco; print(mujoco.__version__)' 2>&1 | tail -1 || true)"
if [ "${mujoco_version}" != "3.10.0" ]; then
    echo "FAIL: the payload cannot import mujoco 3.10.0 (got: ${mujoco_version})"
    echo "      CARRIED_PYPI_PACKAGES in relocate_conda_environment.py is what"
    echo "      carries it; the pin lives in pixi.toml. See ADR-060."
    exit 1
fi
echo "==> mujoco ${mujoco_version} imports from the payload"

if [ "${os}" = "macos" ] && [ -f "${repo}/package/rattler-build/scripts/audit_macos_bundle.py" ]; then
    python "${repo}/package/rattler-build/scripts/audit_macos_bundle.py" "${payload}" || true
fi

echo "==> ${payload}"
du -sh "${payload}"
