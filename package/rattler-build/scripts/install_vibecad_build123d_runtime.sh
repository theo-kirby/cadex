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
requirements="${repository_root}/src/Mod/VibeCAD/build123d-requirements.txt"
runtime_root="${module_directory}/build123d_runtime"
site_packages="${runtime_root}/site-packages"
stamp="${runtime_root}/runtime-spec.sha256"

if [[ ! -x "${python_executable}" ]]; then
    echo "build123d runtime Python is not executable: ${python_executable}" >&2
    exit 1
fi
if [[ ! -f "${requirements}" ]]; then
    echo "build123d requirements file is missing: ${requirements}" >&2
    exit 1
fi
if [[ ! -f "${module_directory}/build123d_worker.py" ]]; then
    echo "VibeCAD build123d worker is missing from: ${module_directory}" >&2
    exit 1
fi

smoke_runtime() {
    "${python_executable}" -I -S -c \
        "import sys; sys.path.insert(0, sys.argv[1]); import build123d; assert build123d.__version__ == '0.11.1'; namespace = {}; exec('from build123d import *', namespace, namespace); box = namespace['Box'](2, 3, 5); assert abs(float(box.volume) - 30.0) < 1.0e-9" \
        "${site_packages}"
}

runtime_spec_hash="$(sha256sum "${requirements}" "$0" | sha256sum | awk '{print $1}')"
if [[ -f "${stamp}" ]] \
  && [[ "$(tr -d '\r\n' < "${stamp}")" == "${runtime_spec_hash}" ]] \
  && [[ -d "${site_packages}/build123d-0.11.1.dist-info" ]]; then
    smoke_runtime
    echo "VibeCAD isolated build123d runtime is current"
    exit 0
fi

rm -rf "${runtime_root}"
mkdir -p "${site_packages}"
"${python_executable}" -m pip install \
    --disable-pip-version-check \
    --no-compile \
    --only-binary=:all: \
    --target "${site_packages}" \
    -r "${requirements}"

smoke_runtime
echo "VibeCAD isolated build123d runtime ok"
printf '%s\n' "${runtime_spec_hash}" > "${stamp}"
