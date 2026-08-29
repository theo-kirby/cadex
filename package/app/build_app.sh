#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Build the Cadex application: one repository, one build, one bundle.
#
#   package/app/build_app.sh setup    check out the shell libraries for this platform
#   package/app/build_app.sh shell    configure + build + install the shell
#   package/app/build_app.sh launch   run the built bundle
#   package/app/build_app.sh gate     the product gate against the built bundle
#   package/app/build_app.sh path     print the built executable's path
#   package/app/build_app.sh install  copy the bundle into /Applications
#   package/app/build_app.sh uninstall  remove it again
#
# The engine half (`build-engine`, `stage-engine`) stays in pixi.toml, where
# it already lived. This script exists for one reason: **the shell must not
# see the engine's toolchain.**
#
# The engine builds inside the pixi/conda-forge environment (OCCT 7.8.1, Qt6,
# conda compilers, a conda sysroot). The shell builds against
# `shell/lib/<platform>` -- Blender's own prebuilt library set -- with Xcode
# and a homebrew cmake/ninja. Those two are not compatible and they overlap
# on names: put `.pixi/envs/default/bin` on PATH during a shell configure and
# CMake finds conda's zlib, png, OpenSSL and Python instead of the ones in
# `shell/lib`, which either fails late in the link or, worse, produces a
# binary that misbehaves at runtime.
#
# So every command this script runs against the shell tree runs through
# `scrubbed`, which strips the conda/pixi environment out. That is why
# `pixi run build-shell` is a thin wrapper around this file rather than a
# `cmd = ["cmake", ...]` task: pixi would hand cmake the very environment we
# are removing.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "${here}/../.." && pwd)"
shell_src="${repo}/shell"

case "$(uname -s)" in
    Darwin) os_ncase="darwin"; lib_platform="macos" ;;
    Linux)  os_ncase="linux";  lib_platform="linux" ;;
    *)      os_ncase="windows"; lib_platform="windows" ;;
esac
case "$(uname -m)" in
    arm64|aarch64) lib_arch="arm64" ;;
    *)             lib_arch="x64" ;;
esac
lib_dir="lib/${lib_platform}_${lib_arch}"

build_dir="${CADEX_SHELL_BUILD_DIR:-${shell_src}/build_${os_ncase}}"
install_dir="${build_dir}/bin"

if [ "${os_ncase}" = "darwin" ]; then
    app_name="${CADEX_APP_NAME:-Cadex}"
    app_exe="${install_dir}/${app_name}.app/Contents/MacOS/${app_name}"
else
    app_exe="${install_dir}/cadex"
fi

# ---------------------------------------------------------------------------
# The scrub.
# ---------------------------------------------------------------------------
#
# Two halves. PATH is filtered by prefix -- anything under the pixi
# environment or a conda install goes. The variable list is the set conda's
# activation scripts and pixi's task runner export; each one of them, left
# in place, redirects a CMake `find_package` or an implicit compiler flag at
# the wrong tree.

scrubbed() {
    local clean_path="" entry
    local IFS=:
    for entry in ${PATH}; do
        case "${entry}" in
            "${repo}/.pixi/"*|*/.pixi/envs/*|*/conda/*|*/miniconda*|*/anaconda*|*/mambaforge*|*/micromamba*)
                continue ;;
        esac
        [ -n "${entry}" ] || continue
        clean_path="${clean_path:+${clean_path}:}${entry}"
    done
    unset IFS

    env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u CONDA_PYTHON_EXE \
        -u CONDA_SHLVL -u CONDA_BUILD_SYSROOT -u CONDA_TOOLCHAIN_BUILD \
        -u CONDA_TOOLCHAIN_HOST -u _CONDA_PYTHON_SYSCONFIGDATA_NAME \
        -u CMAKE_PREFIX_PATH -u CMAKE_ARGS -u CMAKE_GENERATOR \
        -u CMAKE_INSTALL_PREFIX -u CMAKE_BUILD_PARALLEL_LEVEL \
        -u CFLAGS -u CXXFLAGS -u CPPFLAGS -u LDFLAGS \
        -u DEBUG_CFLAGS -u DEBUG_CXXFLAGS -u DEBUG_CPPFLAGS \
        -u CC -u CXX -u AR -u AS -u LD -u NM -u RANLIB -u STRIP \
        -u OBJCOPY -u OBJDUMP -u READELF -u SIZE -u STRINGS -u ADDR2LINE \
        -u HOST -u BUILD -u GCC -u GXX -u CPP \
        -u PKG_CONFIG_PATH -u PKG_CONFIG_LIBDIR \
        -u PYTHONPATH -u PYTHONHOME -u PYTHONNOUSERSITE \
        -u SDKROOT -u MACOSX_DEPLOYMENT_TARGET -u OSX_SDK_DIR \
        -u LD_LIBRARY_PATH -u DYLD_LIBRARY_PATH -u DYLD_FALLBACK_LIBRARY_PATH \
        -u QT_PLUGIN_PATH -u QML2_IMPORT_PATH -u GSETTINGS_SCHEMA_DIR \
        -u PIXI_PROJECT_ROOT -u PIXI_PROJECT_NAME -u PIXI_ENVIRONMENT_NAME \
        -u PIXI_ENVIRONMENT_PLATFORMS -u PIXI_PROMPT -u PIXI_IN_SHELL \
        -u PIXI_EXE -u PIXI_PROJECT_MANIFEST -u PIXI_PROJECT_VERSION \
        PATH="${clean_path}" \
        "$@"
}

# The engine payload the shell will carry. `stage-engine` builds it; the
# name embeds the version, so resolve it rather than hardcode it.
resolve_engine_dir() {
    if [ -n "${CADEX_ENGINE_DIR:-}" ]; then
        printf '%s\n' "${CADEX_ENGINE_DIR}"
        return
    fi
    local candidate
    candidate="$(find "${repo}/build/engine" -maxdepth 2 -name cadex-engine.json \
        -print 2>/dev/null | head -1)"
    [ -n "${candidate}" ] && printf '%s\n' "$(dirname "${candidate}")"
}

# ---------------------------------------------------------------------------

cmd_setup() {
    if [ ! -e "${shell_src}/${lib_dir}/.git" ]; then
        echo "==> checking out shell/${lib_dir} (~1.3 GB, git-lfs)"
        # The lib repositories are git-lfs. `--skip-repo` installs the
        # filters without touching this repository's hooks.
        git lfs install --skip-repo >/dev/null 2>&1 || {
            echo "FAIL: git-lfs is not installed; the shell libraries need it."
            echo "      brew install git-lfs   (or your platform's package)"
            exit 1
        }
        # `update = none` in .gitmodules keeps a recursive init from pulling
        # all four platforms; --checkout overrides it for the one we want.
        git -C "${repo}" submodule update --init --checkout "shell/${lib_dir}"
    else
        echo "==> shell/${lib_dir} already present"
    fi
    # The engine's own submodules (OndselSolver, GSL).
    git -C "${repo}" submodule update --init --recursive \
        src/3rdParty/OndselSolver src/3rdParty/GSL
    echo "==> setup complete"
}

cmd_shell() {
    local engine_dir
    engine_dir="$(resolve_engine_dir)"
    if [ -z "${engine_dir}" ] || [ ! -f "${engine_dir}/cadex-engine.json" ]; then
        echo "FAIL: no engine payload found under build/engine/."
        echo "      Run:  pixi run stage-engine"
        exit 1
    fi
    if [ ! -d "${shell_src}/${lib_dir}" ] || \
       [ -z "$(ls -A "${shell_src}/${lib_dir}" 2>/dev/null)" ]; then
        echo "FAIL: shell/${lib_dir} is empty."
        echo "      Run:  pixi run setup"
        exit 1
    fi

    echo "==> engine payload: ${engine_dir}"
    echo "==> shell build:    ${build_dir}"

    scrubbed cmake -S "${shell_src}" -B "${build_dir}" -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX="${install_dir}" \
        -DWITH_CADEX_ENGINE=ON \
        -DCADEX_ENGINE_DIR="${engine_dir}" \
        "$@"

    scrubbed cmake --build "${build_dir}" --target install
    stamp_version
    echo "==> ${app_exe}"
}

# The product version (ADR-166). `VERSION` at the repo root is the single
# source of truth -- bump it with package/app/bump_version.sh -- and the
# build number is the commit count, so every commit's build is distinguishable
# with no state kept anywhere. The stamp lands in three places: the window
# title reads Resources/cadex_version.txt (wm_window.cc), and the two
# Info.plist keys are what Finder and the About panel show.
stamp_version() {
    [ "${os_ncase}" = "darwin" ] || return 0
    local version build_number bundle resources
    version="$(tr -d '[:space:]' < "${repo}/VERSION")"
    build_number="$(git -C "${repo}" rev-list --count HEAD 2>/dev/null || echo 0)"
    bundle="${install_dir}/${app_name}.app"
    resources="${bundle}/Contents/Resources"
    [ -d "${resources}" ] || { echo "FAIL: no bundle to stamp at ${bundle}"; exit 1; }
    printf '%s\n' "${version}" > "${resources}/cadex_version.txt"
    plutil -replace CFBundleShortVersionString -string "${version}" \
        "${bundle}/Contents/Info.plist"
    plutil -replace CFBundleVersion -string "${build_number}" \
        "${bundle}/Contents/Info.plist"
    # Editing Info.plist breaks any existing ad-hoc seal; put one back so the
    # bundle stays launchable. Best-effort: an unsigned dev bundle is fine.
    codesign --force --deep --sign - "${bundle}" >/dev/null 2>&1 || true
    echo "==> stamped Cadex ${version} (build ${build_number})"
}

cmd_launch() {
    [ -x "${app_exe}" ] || { echo "FAIL: ${app_exe} does not exist. Run: pixi run app"; exit 1; }
    # Deliberately without any MESH_* engine override: the bundle must find
    # its own engine by manifest, which is the whole point of one repo.
    scrubbed env -u MESH_FREECADCMD -u MESH_CADEXD_MODULE -u MESH_CADEX_ENGINE \
        "${app_exe}" "$@"
}

cmd_path() { printf '%s\n' "${app_exe}"; }

# Install the built bundle where the desktop expects an application, so Cadex
# opens from Spotlight, Launchpad and the Dock like anything else.
#
# This is a **local** install, and the distinction is the one from
# docs/cadex-release-packaging.md: `pixi run app` bundles a *staged* engine
# payload, whose Mach-O load commands still carry the build prefix. Every
# binary under Contents/Resources/cadex resolves @rpath through
# `<repo>/.pixi/envs/default/lib` and `<repo>/build/release/lib`, so the
# installed bundle reads its libraries out of this repository rather than out
# of itself. Move or delete the repo and the installed app stops modelling.
# Making it standalone is the relocated-payload + notarization work, not this.
cmd_install() {
    if [ "${os_ncase}" != "darwin" ]; then
        echo "FAIL: install is macOS-only for now (no shell bundle is built elsewhere)."
        exit 1
    fi
    local src="${install_dir}/${app_name}.app"
    local dest_dir="${CADEX_INSTALL_DIR:-/Applications}"
    local dest="${dest_dir}/${app_name}.app"

    [ -x "${app_exe}" ] || { echo "FAIL: ${src} does not exist. Run: pixi run app"; exit 1; }
    [ -d "${dest_dir}" ] || { echo "FAIL: ${dest_dir} does not exist."; exit 1; }
    # Refuse to --delete into anything that is not a bundle we put there.
    if [ -e "${dest}" ] && [ ! -f "${dest}/Contents/Info.plist" ]; then
        echo "FAIL: ${dest} exists and is not an application bundle."
        exit 1
    fi

    echo "==> installing ${src}"
    echo "==>        to  ${dest}   (~3 GB; incremental after the first time)"
    rsync -a --delete "${src}/" "${dest}/"

    # Make Launch Services notice it now rather than whenever it next rescans.
    local lsregister="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
    [ -x "${lsregister}" ] && "${lsregister}" -f "${dest}" || true

    echo "==> installed. Open it from Spotlight, Launchpad or:  open -a ${app_name}"
    echo "    NOTE: the bundled engine still resolves its libraries out of"
    echo "          ${repo}"
    echo "          Keep this repository where it is, or the installed app will"
    echo "          launch but fail to model."
}

cmd_uninstall() {
    local dest="${CADEX_INSTALL_DIR:-/Applications}/${app_name}.app"
    if [ ! -d "${dest}" ]; then
        echo "==> ${dest} is not installed"
        return
    fi
    [ -f "${dest}/Contents/Info.plist" ] || {
        echo "FAIL: ${dest} is not an application bundle; refusing to remove it."
        exit 1
    }
    rm -rf "${dest}"
    echo "==> removed ${dest}"
}

# The product gate. Run from `shell/` because the suite resolves its own
# fixtures relative to the shell tree, and with every MESH_* engine override
# unset -- the bundle must find its engine by manifest or fail.
cmd_gate() {
    local suite="${1:-tests/python/bl_mesh_agent_cadex.py}"
    [ -x "${app_exe}" ] || { echo "FAIL: ${app_exe} does not exist. Run: pixi run app"; exit 1; }
    scrubbed env -u MESH_FREECADCMD -u MESH_CADEXD_MODULE -u MESH_CADEX_ENGINE \
        sh -c 'cd "$1" && exec "$2" --background --factory-startup --python "$3"' \
        _ "${shell_src}" "${app_exe}" "${suite}"
}

# `scrubbed <anything>` is exposed so the gate suites can run the built
# bundle without the engine environment on PATH either.
case "${1:-}" in
    setup)     shift; cmd_setup "$@" ;;
    shell)     shift; cmd_shell "$@" ;;
    launch)    shift; cmd_launch "$@" ;;
    path)      shift; cmd_path "$@" ;;
    gate)      shift; cmd_gate "$@" ;;
    install)   shift; cmd_install "$@" ;;
    uninstall) shift; cmd_uninstall "$@" ;;
    exec)      shift; scrubbed "$@" ;;
    *)
        echo "usage: $(basename "$0") {setup|shell|launch|gate|path|install|uninstall|exec} [args...]"
        exit 2 ;;
esac
