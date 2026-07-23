#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
rattler_root="$(cd "${script_dir}/.." && pwd)"
repo_root="$(cd "${rattler_root}/../.." && pwd)"

env_root="${1:-${rattler_root}/.pixi/envs/default}"
if [[ ! -d "${env_root}" ]]; then
    echo "VibeCAD runtime environment not found: ${env_root}" >&2
    exit 1
fi
env_root="$(cd "${env_root}" && pwd)"

python_exe=""
if [[ -x "${env_root}/bin/python" ]]; then
    python_exe="${env_root}/bin/python"
elif [[ -x "${env_root}/python.exe" ]]; then
    python_exe="${env_root}/python.exe"
else
    echo "No Python executable found in VibeCAD runtime environment: ${env_root}" >&2
    exit 1
fi

requirements="${repo_root}/src/Mod/VibeCAD/requirements.txt"
if [[ ! -f "${requirements}" ]]; then
    echo "VibeCAD provider requirements file not found: ${requirements}" >&2
    exit 1
fi

echo "Installing VibeCAD provider SDK dependencies into ${env_root}"
"${python_exe}" -m pip uninstall --yes openai-agents
"${python_exe}" -m pip install \
    --disable-pip-version-check \
    --upgrade \
    --prefer-binary \
    -r "${requirements}"
"${python_exe}" -m pip check
"${python_exe}" - <<'PY'
import importlib
import importlib.util
import sys

for module_name in ("openai", "anthropic", "keyring", "jsonschema"):
    importlib.import_module(module_name)

if sys.platform == "win32":
    importlib.import_module("keyring.backends.Windows")
elif sys.platform == "darwin":
    macos_backend = importlib.import_module("keyring.backends.macOS")
    if macos_backend.Keyring.priority <= 0:
        raise RuntimeError("The macOS Keychain keyring backend is unavailable.")
else:
    importlib.import_module("secretstorage")
    importlib.import_module("keyring.backends.SecretService")

if importlib.util.find_spec("agents") is not None:
    raise RuntimeError("The removed OpenAI Agents SDK is still present in the runtime.")

print("VibeCAD provider SDK, OS keyring backend, and schema validator imports ok")
PY
