#!/usr/bin/env bash

set -euo pipefail

if [[ "$#" -ne 2 ]]; then
    echo "usage: $0 PYTHON_EXECUTABLE VIBECAD_MODULE_DIRECTORY" >&2
    exit 2
fi

python_executable="$1"
module_directory="$2"
script_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd "${script_directory}/../../.." && pwd)"
download_cache="${VIBECAD_DOWNLOAD_CACHE:-${repository_root}/package/rattler-build/.download-cache}"
runtime_root="${module_directory}/openscad_runtime"
stamp="${runtime_root}/runtime-spec.sha256"

stable_openscad_version="2021.01"
linux_archive="OpenSCAD-2021.01-x86_64.AppImage"
linux_url="https://files.openscad.org/${linux_archive}"
linux_sha256="f758528f2cd213f773c7a105fb63bf3b45bf754b0f586fbb7c9cd653ffcd0882"
windows_archive="OpenSCAD-2021.01-x86-64.zip"
windows_url="https://files.openscad.org/${windows_archive}"
windows_sha256="fb0caabf5bbc89f8f2f80c10b79ae64d697aaff6efd58b2756f5d6270edb7ba7"
macos_openscad_version="2026.06.12"
macos_archive="OpenSCAD-${macos_openscad_version}.dmg"
macos_url="https://files.openscad.org/snapshots/${macos_archive}"
macos_sha256="555be2ed313e67657b3d8ba3e1de0acd6141b982fd458776c52d3eda748f57c4"

bosl2_version="v2.0.747"
bosl2_commit="fbcdfdd511b6abfde93c43c8f85c2bd24ee7a02d"
bosl2_archive="BOSL2-${bosl2_commit}.tar.gz"
bosl2_url="https://codeload.github.com/BelfrySCAD/BOSL2/tar.gz/${bosl2_commit}"
bosl2_sha256="632167bc2b5485d92813a8cdec2de3a9b0151048020af6744dd8bed81bbb8666"

mcad_commit="bd0a7ba3f042bfbced5ca1894b236cea08904e26"
mcad_archive="MCAD-${mcad_commit}.tar.gz"
mcad_url="https://codeload.github.com/openscad/MCAD/tar.gz/${mcad_commit}"
mcad_sha256="1f7003bf1bdfe9c7e5898eb5e82c54834b156569e79da97d906f3bbcf7c5549c"

if [[ ! -x "${python_executable}" ]]; then
    echo "OpenSCAD runtime Python is not executable: ${python_executable}" >&2
    exit 1
fi

platform="$(${python_executable} -c 'import sys; print(sys.platform)')"
machine="$(${python_executable} -c 'import platform; print(platform.machine().lower())')"
case "${platform}:${machine}" in
    linux:x86_64|linux:amd64)
        openscad_version="${stable_openscad_version}"
        openscad_archive="${linux_archive}"
        openscad_url="${linux_url}"
        openscad_sha256="${linux_sha256}"
        openscad_executable="${runtime_root}/bin/openscad"
        ;;
    win32:amd64|win32:x86_64)
        openscad_version="${stable_openscad_version}"
        openscad_archive="${windows_archive}"
        openscad_url="${windows_url}"
        openscad_sha256="${windows_sha256}"
        openscad_executable="${runtime_root}/openscad.exe"
        ;;
    darwin:arm64|darwin:x86_64|darwin:amd64)
        openscad_version="${macos_openscad_version}"
        openscad_archive="${macos_archive}"
        openscad_url="${macos_url}"
        openscad_sha256="${macos_sha256}"
        openscad_executable="${runtime_root}/OpenSCAD.app/Contents/MacOS/OpenSCAD"
        ;;
    *)
        echo "No pinned OpenSCAD runtime is available for ${platform}/${machine}." >&2
        exit 1
        ;;
esac

runtime_spec="$({
    printf '%s\n' \
        "openscad=${openscad_version}:${openscad_sha256}" \
        "bosl2=${bosl2_version}:${bosl2_commit}:${bosl2_sha256}" \
        "mcad=${mcad_commit}:${mcad_sha256}"
    sha256sum "$0"
} | sha256sum | awk '{print $1}')"

if [[ -f "${stamp}" ]] \
  && [[ "$(tr -d '\r\n' < "${stamp}")" == "${runtime_spec}" ]] \
  && [[ -x "${openscad_executable}" ]] \
  && [[ -f "${runtime_root}/libraries/BOSL2/std.scad" ]] \
  && [[ -f "${runtime_root}/libraries/MCAD/gears.scad" ]]; then
    echo "VibeCAD isolated OpenSCAD runtime is current"
    exit 0
fi

mkdir -p "${download_cache}"

download_verified() {
    local url="$1"
    local expected="$2"
    local destination="$3"
    if [[ -f "${destination}" ]] \
      && echo "${expected}  ${destination}" | sha256sum --check --status; then
        return
    fi
    local temporary="${destination}.tmp"
    rm -f "${temporary}"
    curl --fail --location --retry 4 --retry-all-errors --output "${temporary}" "${url}"
    echo "${expected}  ${temporary}" | sha256sum --check
    mv "${temporary}" "${destination}"
}

openscad_download="${download_cache}/${openscad_archive}"
bosl2_download="${download_cache}/${bosl2_archive}"
mcad_download="${download_cache}/${mcad_archive}"
download_verified "${openscad_url}" "${openscad_sha256}" "${openscad_download}"
download_verified "${bosl2_url}" "${bosl2_sha256}" "${bosl2_download}"
download_verified "${mcad_url}" "${mcad_sha256}" "${mcad_download}"

temporary_root="$(mktemp -d)"
mounted_image=""
cleanup() {
    if [[ -n "${mounted_image}" ]]; then
        hdiutil detach "${mounted_image}" >/dev/null 2>&1 || true
    fi
    rm -rf "${temporary_root}"
}
trap cleanup EXIT
rm -rf "${runtime_root}"
mkdir -p "${runtime_root}"

if [[ "${platform}" == "linux" ]]; then
    chmod +x "${openscad_download}"
    (
        cd "${temporary_root}"
        "${openscad_download}" --appimage-extract >/dev/null
    )
    cp -a "${temporary_root}/squashfs-root/usr/." "${runtime_root}/"
elif [[ "${platform}" == "win32" ]]; then
    "${python_executable}" - "${openscad_download}" "${temporary_root}/openscad" <<'PY'
import pathlib
import sys
import zipfile

archive = pathlib.Path(sys.argv[1])
target = pathlib.Path(sys.argv[2])
with zipfile.ZipFile(archive) as package:
    target_root = target.resolve()
    for member in package.infolist():
        destination = (target / member.filename).resolve()
        if target_root != destination and target_root not in destination.parents:
            raise SystemExit(f"Unsafe path in OpenSCAD archive: {member.filename}")
        unix_mode = member.external_attr >> 16
        if (unix_mode & 0o170000) == 0o120000:
            raise SystemExit(f"Links are not allowed in OpenSCAD archive: {member.filename}")
    package.extractall(target)
roots = [path for path in target.iterdir() if path.is_dir()]
if len(roots) != 1:
    raise SystemExit("OpenSCAD Windows archive has an unexpected root layout")
print(roots[0])
PY
    windows_source="$(find "${temporary_root}/openscad" -mindepth 1 -maxdepth 1 -type d -print -quit)"
    cp -a "${windows_source}/." "${runtime_root}/"
else
    mounted_image="${temporary_root}/openscad-volume"
    mkdir -p "${mounted_image}"
    hdiutil attach \
        -readonly \
        -nobrowse \
        -mountpoint "${mounted_image}" \
        "${openscad_download}" >/dev/null
    macos_source="$(find "${mounted_image}" -maxdepth 2 -type d -name 'OpenSCAD.app' -print -quit)"
    if [[ -z "${macos_source}" ]]; then
        echo "OpenSCAD macOS image does not contain OpenSCAD.app." >&2
        exit 1
    fi
    cp -a "${macos_source}" "${runtime_root}/OpenSCAD.app"
    hdiutil detach "${mounted_image}" >/dev/null
    mounted_image=""
fi

install_library() {
    local archive="$1"
    local destination="$2"
    local extraction="$3"
    mkdir -p "${extraction}"
    "${python_executable}" - "${archive}" "${extraction}" <<'PY'
import pathlib
import sys
import tarfile

archive = pathlib.Path(sys.argv[1])
target = pathlib.Path(sys.argv[2])
with tarfile.open(archive, "r:gz") as package:
    target_root = target.resolve()
    for member in package.getmembers():
        destination = (target / member.name).resolve()
        if target_root != destination and target_root not in destination.parents:
            raise SystemExit(f"Unsafe path in library archive: {member.name}")
        if member.issym() or member.islnk():
            raise SystemExit(f"Links are not allowed in library archive: {member.name}")
    package.extractall(target)
PY
    local source
    source="$(find "${extraction}" -mindepth 1 -maxdepth 1 -type d -print -quit)"
    if [[ -z "${source}" ]]; then
        echo "Library archive has no root directory: ${archive}" >&2
        exit 1
    fi
    rm -rf "${destination}"
    mkdir -p "$(dirname "${destination}")"
    cp -a "${source}" "${destination}"
}

install_library "${bosl2_download}" "${runtime_root}/libraries/BOSL2" "${temporary_root}/bosl2"
install_library "${mcad_download}" "${runtime_root}/libraries/MCAD" "${temporary_root}/mcad"

cat > "${runtime_root}/runtime.json" <<EOF
{
  "openscad": "${openscad_version}",
  "bosl2": "${bosl2_version}",
  "bosl2_commit": "${bosl2_commit}",
  "mcad_commit": "${mcad_commit}"
}
EOF
printf '%s\n' "${runtime_spec}" > "${stamp}"
chmod +x "${openscad_executable}"

if [[ "${platform}" == "darwin" ]]; then
    available_architectures="$(lipo -archs "${openscad_executable}")"
    if [[ " ${available_architectures} " != *" ${machine} "* ]]; then
        echo "OpenSCAD runtime does not contain the required ${machine} architecture: ${available_architectures}" >&2
        exit 1
    fi
fi

if [[ "${platform}" == "linux" ]]; then
    LD_LIBRARY_PATH="${runtime_root}/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" \
    QT_PLUGIN_PATH="${runtime_root}/plugins" \
        "${openscad_executable}" --version
else
    "${openscad_executable}" --version
fi

echo "VibeCAD isolated OpenSCAD runtime and libraries installed"
