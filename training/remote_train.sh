#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Drive `training/cadex_train.py` on a remote GPU box (ADR-089).
#
#   training/remote_train.sh check                       pre-flight the box
#   training/remote_train.sh train <bundle.json> <out.cxpolicy> [-- trainer args]
#   training/remote_train.sh train ... --detach          start it and come back
#   training/remote_train.sh watch <run-id> [dest]       follow a detached run
#   training/remote_train.sh pull  <run-id> [dest]       bring its files home
#   training/remote_train.sh stop  <run-id>              end it early
#   training/remote_train.sh shell                       interactive ssh, configured
#   training/remote_train.sh config                      print the resolved settings
#
# Configuration is read from `training/.remote.env` (override with
# `CADEX_TRAIN_ENV=<path>`); `training/remote.env.example` documents every
# variable. Set them in the environment instead and that file is optional.
# `training/SETUP.md` is the end-to-end version, including the three ways to
# train that do not involve this file at all.
#
# This is dispatch machinery and nothing more. It builds no bundle, installs
# no package, and creates no virtualenv -- it copies two files out, runs the
# trainer that is already on the box, and copies one file back, which is the
# same three steps `training/README.md` documents by hand. ADR-084 stands:
# nothing here enters `pixi.toml`, no CMake rule references it, and the
# engine still cannot train.
#
# **It fails loudly rather than repairing.** A missing venv is an error
# naming the path, not a venv this script built; a run that fell back to CPU
# is an error, not a slow success. Both are failure modes that otherwise
# surface only as a number nobody compares -- the trainer already records
# `device` into the policy for exactly that reason, and this is what makes it
# loud at the moment it happens rather than a month later.
#
# Written for bash 3.2, which is what macOS ships: no `${x@Q}`, no
# `${arr[@]}` on a possibly-empty array, no associative arrays.
#
# Remote paths must not contain spaces. They are interpolated into a command
# line the remote shell parses, and pretending otherwise would take
# `rsync --protect-args`, which the rsync macOS ships does not have.
#
# EDITING THE `REMOTE` HEREDOC: no apostrophes, not even in a comment. It
# sits inside a `$( )`, where bash scans the body honouring quotes, so one
# unpaired single quote is an unterminated string -- and the error it
# reports points at the last line of this file rather than at the quote.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
env_file="${CADEX_TRAIN_ENV:-${here}/.remote.env}"
requirements="${here}/requirements.txt"

# ---------------------------------------------------------------------------
# Configuration.
# ---------------------------------------------------------------------------
#
# The file is read as literal `KEY=value` lines, and deliberately NOT
# sourced. Two reasons, one of which cost a debugging session to notice:
#
#   * `CADEX_TRAIN_REPO=~/cadex` sourced by bash expands the tilde against
#     the *laptop's* $HOME, silently, and the value means a path on the box.
#     Read literally it stays `~/cadex` and `resolve_remote_paths` expands it
#     against the box's own $HOME, which is what was meant.
#   * A configuration file that can also run commands is a configuration
#     file that eventually does.
#
# Anything already set in the environment wins, which is what lets a one-off
# run override a single setting inline:
#
#     CADEX_TRAIN_VENV=/opt/other-venv training/remote_train.sh check

read_env_file() {
    local line name value
    while IFS= read -r line || [ -n "${line}" ]; do
        line="${line#"${line%%[![:space:]]*}"}"          # strip leading space
        case "${line}" in ""|"#"*) continue ;; esac
        case "${line}" in *"="*) : ;; *) continue ;; esac
        name="${line%%=*}"
        value="${line#*=}"
        case "${name}" in
            CADEX_TRAIN_[A-Z_]*) : ;;
            *) continue ;;
        esac
        value="${value%%[[:space:]]#*}"                  # strip a trailing comment
        value="${value%"${value##*[![:space:]]}"}"       # strip trailing space
        case "${value}" in                               # strip paired quotes
            \"*\") value="${value#\"}"; value="${value%\"}" ;;
            \'*\') value="${value#\'}"; value="${value%\'}" ;;
        esac
        # The environment wins. `+set` distinguishes unset from set-empty, so
        # `CADEX_TRAIN_SSH_USER=` in the environment really does mean "none".
        local present
        eval "present=\${${name}+set}"
        if [ -z "${present}" ]; then
            eval "${name}=\$value"
        fi
    done < "${env_file}"
}

load_config() {
    if [ -f "${env_file}" ]; then
        read_env_file
    fi

    host="${CADEX_TRAIN_SSH_HOST:-}"
    user="${CADEX_TRAIN_SSH_USER:-}"
    key="${CADEX_TRAIN_SSH_KEY:-}"
    port="${CADEX_TRAIN_SSH_PORT:-22}"
    remote_repo="${CADEX_TRAIN_REPO:-}"
    remote_venv="${CADEX_TRAIN_VENV:-}"
    remote_work="${CADEX_TRAIN_WORK:-}"

    if [ -z "${host}" ]; then
        echo "FAIL: CADEX_TRAIN_SSH_HOST is not set."
        echo "      Copy training/remote.env.example to ${env_file} and fill it in."
        exit 2
    fi

    target="${host}"
    if [ -n "${user}" ]; then target="${user}@${host}"; fi

    # One option list, shared by ssh and rsync, so the two cannot disagree
    # about which key or port reaches the box. Empty entries are dropped --
    # ssh has to fall through to ~/.ssh/config when we say nothing.
    #
    # `if` rather than `[ x ] && y` throughout: under `set -e` a bare
    # short-circuit whose test fails is the *last* command of its list, and
    # takes the script with it.
    ssh_opts=(-o BatchMode=yes)
    if [ -n "${port}" ]; then ssh_opts+=(-p "${port}"); fi
    if [ -n "${key}" ]; then
        case "${key}" in "~"/*) key="${HOME}/${key#\~/}" ;; esac
        if [ ! -f "${key}" ]; then
            echo "FAIL: CADEX_TRAIN_SSH_KEY names ${key}, which does not exist."
            exit 2
        fi
        ssh_opts+=(-i "${key}")
    fi

    # rsync wants the transport as one string, and its port flag is not -p.
    rsync_ssh="ssh -o BatchMode=yes"
    if [ -n "${port}" ]; then rsync_ssh="${rsync_ssh} -p ${port}"; fi
    if [ -n "${key}" ]; then rsync_ssh="${rsync_ssh} -i ${key}"; fi
}

on_box() { ssh "${ssh_opts[@]}" "${target}" "$@"; }

require() {
    [ -n "$2" ] || {
        echo "FAIL: $1 is not set. See training/remote.env.example."
        exit 2
    }
}

# Single-quote a string for a remote shell. The only quoting primitive this
# file needs, and bash 3.2 has no `${x@Q}` to borrow one from.
#
# The `sed` is not decoration. This was written as a `${1//.../...}`
# substitution and that form is **wrong** in bash 3.2: measured, it turns
# `a'b` into `'a\'\\'\'b'` rather than `'a'\''b'`. Nothing had ever
# passed it a string containing a quote, so it worked for a year and then
# broke the first command that did. Identical output for anything without
# one, which is every existing caller.
shquote() {
    local body
    body=$(printf %s "$1" | sed s/\'/\'\\\\\'\'/g)
    printf \'%s\' "${body}"
}

# sha256 of a local file. macOS ships `shasum`, Linux ships `sha256sum`, and
# a dispatch script that only runs on the machine it was written on is not
# dispatch machinery.
sha256_of() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | cut -d' ' -f1
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d' ' -f1
    else
        echo "FAIL: neither shasum nor sha256sum is on PATH; cannot verify the policy." >&2
        exit 1
    fi
}

# THE TRAINER THAT RUNS IS THE BOX-S, NOT THIS REPO-S.
#
# This script copies a bundle and a model and then runs
# `${remote_repo}/training/cadex_train.py` -- the checkout on the box. Every
# test that pins the trainer against the engine runs here, against the file
# in this repo, and nothing connected the two. So a box whose checkout
# predates a change to `EPISODE_VARIATION_ALGORITHM` reads the new fields as
# absent, trains against a task nobody declared, and records the NEW
# algorithm string in the policy header because it copies that string out of
# the bundle it was handed. Nothing fails, and the run looks exactly like a
# good one.
#
# Measured, on the run this check was written for: the box sat on a retired
# branch three commits back and would have trained with no stumble, over the
# whole circle instead of the declared arc, and with no exploration width in
# the header -- so `compare.py --sample` would have refused the result and
# `watch` would have had no sigma to print. It was caught by reading
# `remote_train.sh` before dispatching, which is not a control.
#
# One hash, one round trip. `check` reports it and `train` refuses on it,
# because a warning at dispatch time is a thing people click past.
remote_trainer_sha() {
    on_box "sha256sum $(shquote "${remote_repo}/training/cadex_train.py") \
            2>/dev/null | cut -c1-64"
}

assert_trainer_matches() {
    local mine theirs
    mine="$(sha256_of "${here}/cadex_train.py")"
    theirs="$(remote_trainer_sha)"
    [ "${mine}" = "${theirs}" ] && return 0
    echo "FAIL: the trainer on the box is not the one in this repo."
    echo "      here  ${mine}"
    echo "      box   ${theirs:--unreadable-}"
    echo
    echo "      ${target} runs its OWN checkout, so dispatching now would"
    echo "      train against whatever that file says while recording this"
    echo "      bundle-s algorithm string in the policy header. Nothing would"
    echo "      fail and the run would look fine. On the box:"
    echo "        cd ${remote_repo} && git fetch origin && git checkout <branch>"
    echo "      then re-run: $(basename "$0") check"
    exit 1
}

# The reachability check, and the reason every later path can be quoted: a
# `~` in the config is expanded here, once, against the box's own $HOME.
# After this the three remote paths are absolute.
resolve_remote_paths() {
    local home
    home="$(on_box 'printf %s "$HOME"')" || {
        echo "FAIL: cannot reach ${target} over ssh."
        echo "      Try:  ssh ${ssh_opts[*]} ${target}"
        echo "      BatchMode is on, so a password prompt or an unknown host key"
        echo "      reads as a connection failure. Accept the host key once with"
        echo "        training/remote_train.sh shell"
        exit 1
    }
    case "${remote_repo}" in "~"/*) remote_repo="${home}/${remote_repo#\~/}" ;; esac
    case "${remote_venv}" in "~"/*) remote_venv="${home}/${remote_venv#\~/}" ;; esac
    case "${remote_work}" in "~"/*) remote_work="${home}/${remote_work#\~/}" ;; esac
}

# ---------------------------------------------------------------------------
# check -- everything that is wrong with the box, in one round trip.
# ---------------------------------------------------------------------------
#
# The remote half reports facts and always exits 0; this half judges them.
# That split is deliberate. Stopping at the first failure means learning
# about the missing venv, then the wrong mujoco, then the CPU-only jax over
# three separate trips to a machine that is probably not in the room.

cmd_check() {
    load_config
    require CADEX_TRAIN_REPO "${remote_repo}"
    require CADEX_TRAIN_VENV "${remote_venv}"
    require CADEX_TRAIN_WORK "${remote_work}"
    resolve_remote_paths

    echo "==> ${target}"

    local report
    report="$(on_box "REPO=$(shquote "${remote_repo}")" \
                     "VENV=$(shquote "${remote_venv}")" \
                     "WORK=$(shquote "${remote_work}")" \
                     bash -s <<'REMOTE'
set -u
echo "host $(hostname)"

if [ -f "${REPO}/training/cadex_train.py" ]; then
    echo "repo ok"
    # The file that will actually run, identified rather than assumed.
    if command -v sha256sum >/dev/null 2>&1; then
        echo "trainer $(sha256sum "${REPO}/training/cadex_train.py" | cut -c1-64)"
    else
        echo "trainer -no sha256sum on the box-"
    fi
    if command -v git >/dev/null 2>&1 && [ -d "${REPO}/.git" ]; then
        echo "at $(cd "${REPO}" && git log --oneline -1 2>/dev/null | cut -c1-72)"
    fi
else
    echo "repo missing"
fi
if [ -d "${WORK}" ]; then echo "work ok"; else echo "work missing"; fi

if [ ! -d "${VENV}" ]; then
    echo "venv missing"
elif [ ! -x "${VENV}/bin/python" ]; then
    echo "venv notvenv"
else
    echo "venv ok"
    "${VENV}/bin/python" - <<'PROBE' 2>&1 || echo "probe failed"
import importlib.metadata as meta
for name in ("jax", "jaxlib", "mujoco", "mujoco-mjx", "numpy"):
    try:
        print("pkg", name, meta.version(name))
    except Exception:
        print("pkg", name, "-")
try:
    import jax
    print("backend", jax.default_backend())
    print("devices", ", ".join(str(d) for d in jax.devices()) or "-")
except Exception as error:
    print("backend unimportable")
    print("error", type(error).__name__, error)
PROBE
fi

if command -v nvidia-smi >/dev/null 2>&1; then
    if smi="$(nvidia-smi --query-gpu=name,memory.total,driver_version \
                         --format=csv,noheader 2>&1)"; then
        echo "${smi}" | while IFS= read -r line; do echo "gpu ${line}"; done
    else
        # nvidia-smi itself failed. The usual cause is a driver package
        # upgraded without a reboot, leaving the loaded kernel module a
        # different version from the userspace library -- so report both
        # numbers, which is the difference between "it is broken" and a
        # thing somebody can fix.
        echo "gpubroken yes"
        echo "${smi}" | head -2 |
            while IFS= read -r line; do echo "gpu ${line}"; done
        if [ -r /proc/driver/nvidia/version ]; then
            echo "gpukernel $(sed -n \
                's/.*Kernel Module *\([0-9][0-9.]*\).*/\1/p' \
                /proc/driver/nvidia/version | head -1)"
        fi
        # The pattern needs the dot: `libnvidia-ml.so.1` is the SONAME
        # symlink and sorts first, so a looser glob reports the library
        # version as "1" and the comparison below silently stops meaning
        # anything. Only `libnvidia-ml.so.<major>.<minor>` is the real file.
        for candidate in \
            /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.[0-9]*.[0-9]* \
            /usr/lib/libnvidia-ml.so.[0-9]*.[0-9]*; do
            [ -f "${candidate}" ] && [ ! -L "${candidate}" ] || continue
            echo "gpulib ${candidate##*libnvidia-ml.so.}"
            break
        done
        # Failing that, the error line from nvidia-smi carries it.
        # (No apostrophes anywhere in this heredoc, deliberately. It sits
        # inside a $( ) and bash scans the body honouring quotes, so one
        # unpaired single quote -- in a comment, even -- is an unterminated
        # string, and the whole file stops parsing with an error that points
        # at the LAST line of the script rather than at the quote.)
        echo "${smi}" | sed -n \
            's/.*NVML library version: *\([0-9][0-9.]*\).*/gpulibsmi \1/p' | head -1
        [ -f /var/run/reboot-required ] && echo "gpureboot yes"
    fi
else
    echo "gpu -none on PATH-"
fi
REMOTE
    )" || { echo "FAIL: the probe did not run on ${target}."; exit 1; }

    local failures=0 line
    while IFS= read -r line; do
        case "${line}" in
            "host "*)    printf '    %-14s %s\n' box        "${line#host }" ;;
            "gpu "*)     printf '    %-14s %s\n' gpu        "${line#gpu }" ;;
            "devices "*) printf '    %-14s %s\n' "jax devices" "${line#devices }" ;;
        esac
    done <<<"${report}"
    printf '    %-14s %s\n' repo "${remote_repo}"
    printf '    %-14s %s\n' venv "${remote_venv}"
    printf '    %-14s %s\n' work "${remote_work}"

    local mine theirs at
    mine="$(sha256_of "${here}/cadex_train.py")"
    theirs="$(grep '^trainer ' <<<"${report}" | head -1)"; theirs="${theirs#trainer }"
    at="$(grep '^at ' <<<"${report}" | head -1)"; at="${at#at }"
    [ -n "${at}" ] && printf '    %-14s %s\n' "box at" "${at}"
    if [ "${theirs}" = "${mine}" ]; then
        printf '    %-14s %s\n' trainer "${mine:0:12} -- matches this repo"
    else
        printf '    %-14s %s\n' trainer "${theirs:0:12} on the box"
        printf '    %-14s %s\n' "" "${mine:0:12} here"
        echo "FAIL: the box runs its OWN checkout of training/cadex_train.py, and"
        echo "      it is not this one. A trainer that predates a surface addition"
        echo "      reads the new bundle fields as absent, trains against a task"
        echo "      nobody declared, and records the new algorithm string in the"
        echo "      policy header anyway -- so nothing fails and the run looks"
        echo "      fine. On the box:"
        echo "        cd ${remote_repo} && git fetch origin && git checkout <branch>"
        failures=$((failures + 1))
    fi

    grep -q '^repo ok$' <<<"${report}" || {
        echo "FAIL: ${remote_repo}/training/cadex_train.py is not on the box."
        echo "      CADEX_TRAIN_REPO must be a checkout of this repository."
        failures=$((failures + 1))
    }

    if grep -q '^venv missing$' <<<"${report}"; then
        echo "FAIL: ${remote_venv} does not exist."
        echo "      This script never creates it. A venv nobody built is a venv"
        echo "      nobody knows the contents of, and the exact pins exist so the"
        echo "      contents are known. On the box:"
        echo "        python3 -m venv ${remote_venv}"
        echo "        ${remote_venv}/bin/pip install -r ${remote_repo}/training/requirements.txt"
        echo "        ${remote_venv}/bin/pip install 'jax[cuda12]==0.7.2'"
        echo "      training/SETUP.md path (c) is the long form."
        failures=$((failures + 1))
    elif grep -q '^venv notvenv$' <<<"${report}"; then
        echo "FAIL: ${remote_venv} exists but has no bin/python, so it is not a venv."
        failures=$((failures + 1))
    else
        # The pinned four must match exactly. MuJoCo's own VERSIONING.md
        # disclaims cross-version numerical reproducibility, so a box one
        # patch release off produces numbers that cannot be compared against
        # the engine's -- a wrong answer, not a slow one. jaxlib is reported
        # and not compared: `jax[cuda12]` is what chooses it.
        local pinned name want got
        while IFS= read -r pinned; do
            case "${pinned}" in ""|"#"*) continue ;; esac
            case "${pinned}" in *"=="*) : ;; *) continue ;; esac
            name="${pinned%%==*}"; want="${pinned##*==}"
            got="$(grep "^pkg ${name} " <<<"${report}" | head -1 | awk '{print $3}')"
            if [ "${got}" = "${want}" ]; then
                printf '    %-14s %s\n' "${name}" "${got}"
            else
                echo "FAIL: ${name} is ${got:--absent-} on the box; requirements.txt pins ${want}."
                failures=$((failures + 1))
            fi
        done < <(sed 's/[[:space:]]*#.*//' "${requirements}")

        got="$(grep '^pkg jaxlib ' <<<"${report}" | head -1 | awk '{print $3}')"
        printf '    %-14s %s\n' jaxlib "${got:--} (unpinned; jax[cuda12] chooses it)"
    fi

    local backend
    backend="$(grep '^backend ' <<<"${report}" | head -1 | cut -d' ' -f2-)"

    # A broken `nvidia-smi` is judged AGAINST the backend, because on its own
    # it does not say whether the box can train. NVML and the CUDA driver API
    # are separate libraries, and a box was measured doing 23 TFLOP/s through
    # jax while `nvidia-smi` refused to start. So:
    #
    #   * jax has the GPU  -> a warning. You lose nvidia-smi, which means no
    #     utilisation or temperature reading during a run. The run is fine.
    #   * jax does NOT     -> a failure, and the LIKELY CAUSE of it, which is
    #     why this is worth reporting at all: "install the GPU wheel" is
    #     misleading advice when the driver is the thing that is broken.
    local driver_broken=0
    if grep -q '^gpubroken yes$' <<<"${report}"; then
        driver_broken=1
        local kernel library label
        kernel="$(grep '^gpukernel ' <<<"${report}" | head -1 | cut -d' ' -f2-)"
        library="$(grep '^gpulib ' <<<"${report}" | head -1 | cut -d' ' -f2-)"
        if [ -z "${library}" ]; then
            library="$(grep '^gpulibsmi ' <<<"${report}" | head -1 \
                       | cut -d' ' -f2-)"
        fi
        if [ "${backend}" = "gpu" ]; then label="WARN"; else label="FAIL"; fi
        echo "${label}: nvidia-smi does not run on the box."
        if [ -n "${kernel}" ] && [ -n "${library}" ] \
           && [ "${kernel}" != "${library}" ]; then
            echo "      The loaded kernel module is ${kernel} and the userspace"
            echo "      library is ${library} -- a driver package upgraded without"
            echo "      a reboot. Reboot the box, or reload the nvidia modules."
        else
            echo "      Reboot the box, or reinstall the driver."
        fi
        if grep -q '^gpureboot yes$' <<<"${report}"; then
            echo "      /var/run/reboot-required exists, which agrees."
        fi
        if [ "${backend}" = "gpu" ]; then
            echo "      NOT counted as a problem: jax has the GPU and computes on"
            echo "      it. What you lose is monitoring -- no utilisation or"
            echo "      temperature reading while a run is going."
        else
            failures=$((failures + 1))
        fi
    fi

    if [ "${backend}" = "gpu" ]; then
        printf '    %-14s %s\n' "jax backend" gpu
    elif [ "${backend}" = "unimportable" ]; then
        echo "FAIL: jax does not import in ${remote_venv}:"
        echo "        $(grep '^error ' <<<"${report}" | head -1 | cut -d' ' -f2-)"
        failures=$((failures + 1))
    elif [ -n "${backend}" ]; then
        echo "FAIL: jax.default_backend() is '${backend}', not 'gpu'."
        echo "      The box would train on CPU: valid numbers, hours it does not"
        echo "      need to take. Install the GPU wheel:"
        echo "        ${remote_venv}/bin/pip install 'jax[cuda12]==0.7.2'"
        if [ "${driver_broken}" -eq 1 ]; then
            echo "      ...but fix the driver FIRST. With nvidia-smi failing, the"
            echo "      GPU wheel installs cleanly and still finds no GPU, so"
            echo "      doing this one first looks like it did not work."
        fi
        failures=$((failures + 1))
    fi

    grep -q '^work ok$' <<<"${report}" ||
        echo "NOTE: ${remote_work} does not exist yet; \`train\` will create it."

    if [ "${failures}" -ne 0 ]; then
        echo "==> ${failures} problem(s). The box is not ready."
        exit 1
    fi
    echo "==> ready."
}

# ---------------------------------------------------------------------------
# train
# ---------------------------------------------------------------------------
#
# The bundle references its model by a path relative to the *project root*,
# with a sha256 -- which is what makes the pair movable at all. The trainer
# resolves `<bundle>/../../<relative>` first and falls back to
# `<bundle>/<basename>` (cadex_train.py:198-203), and that documented flat
# fallback is what this copies into: two files, side by side, in one scratch
# directory. Anything else would need the project tree on the box.

cmd_train() {
    load_config

    local allow_cpu=0 detach=0 bundle="" out="" extra="" seen_dashdash=0
    while [ "$#" -gt 0 ]; do
        if [ "${seen_dashdash}" -eq 1 ]; then
            extra="${extra} $(shquote "$1")"; shift; continue
        fi
        case "$1" in
            --)          seen_dashdash=1; shift ;;
            --allow-cpu) allow_cpu=1; shift ;;
            --detach)    detach=1; shift ;;
            -*)          echo "FAIL: unknown option $1 (trainer flags go after \`--\`)."; exit 2 ;;
            *)
                if   [ -z "${bundle}" ]; then bundle="$1"
                elif [ -z "${out}" ];    then out="$1"
                else echo "FAIL: unexpected argument $1."; exit 2
                fi
                shift ;;
        esac
    done
    if [ -z "${bundle}" ] || [ -z "${out}" ]; then
        echo "usage: $(basename "$0") train <bundle.json> <out.cxpolicy> [--allow-cpu] [--detach] [-- trainer args]"
        exit 2
    fi

    require CADEX_TRAIN_REPO "${remote_repo}"
    require CADEX_TRAIN_VENV "${remote_venv}"
    require CADEX_TRAIN_WORK "${remote_work}"
    [ -f "${bundle}" ] || { echo "FAIL: ${bundle} does not exist."; exit 1; }
    command -v python3 >/dev/null 2>&1 || {
        echo "FAIL: python3 is not on PATH; it reads the bundle's model reference."
        exit 1
    }

    # The model this bundle names, resolved the way the trainer resolves it.
    local model
    model="$(python3 - "${bundle}" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1]).resolve()
task = json.loads(path.read_text(encoding="utf-8"))
relative = pathlib.Path(str(task["model"]["path"]))
for candidate in (path.parent.parent / relative, path.parent / relative.name):
    if candidate.exists():
        print(candidate)
        break
else:
    raise SystemExit(
        f"FAIL: the model {task['model']['path']!r} this bundle references is "
        f"beside neither {path.parent.parent} nor {path.parent}."
    )
PY
    )" || exit 1

    resolve_remote_paths
    # Before anything is copied: the box has to be running the trainer these
    # tests pinned, or the run is about a task nobody declared.
    assert_trainer_matches

    local run_id bundle_name out_name remote_dir
    run_id="$(basename "${bundle}" .json)-$(date +%Y%m%d-%H%M%S)"
    bundle_name="$(basename "${bundle}")"
    out_name="$(basename "${out}")"
    remote_dir="${remote_work%/}/${run_id}"

    echo "==> bundle ${bundle}"
    echo "==> model  ${model}"
    echo "==> box    ${target}:${remote_dir}"

    on_box "mkdir -p $(shquote "${remote_dir}")"
    rsync -e "${rsync_ssh}" -a "${bundle}" "${model}" "${target}:${remote_dir}/"

    if [ "${detach}" -eq 1 ]; then
        detached_train "${run_id}" "${remote_dir}" "${bundle_name}" \
                       "${out_name}" "${extra}"
        return 0
    fi

    # stdout is the trainer's single JSON line; stderr is its per-iteration
    # reward curve, which streams to this terminal while it trains.
    local result status
    set +e
    result="$(on_box "$(shquote "${remote_venv}/bin/python")" \
                     "$(shquote "${remote_repo}/training/cadex_train.py")" \
                     "$(shquote "${remote_dir}/${bundle_name}")" \
                     "--out $(shquote "${remote_dir}/${out_name}")" \
                     "${extra}")"
    status=$?
    set -e
    [ "${status}" -eq 0 ] || { echo "FAIL: the trainer exited ${status}."; exit "${status}"; }

    echo "${result}"

    # THE RECEIPT IS THE LAST LINE, and it has to be taken as the last line
    # rather than as the whole of stdout. This said "last stdout line" and
    # passed `${result}` -- everything the trainer printed -- to `json.load`,
    # which is the same thing only while nothing else prints to stdout.
    # MuJoCo 3.10 does: an installation without the optional `warp` backend
    # emits two `Failed to import warp: No module named 'warp'` lines there,
    # so `json.load` saw those first and refused. Measured the expensive way
    # -- a 3 h 49 m run trained, wrote its policy and reported it correctly,
    # and the dispatch failed on the receipt and never ran the rsync below.
    # The policy was recoverable from the box, which is the only reason this
    # cost an hour rather than the run.
    local receipt device claimed
    receipt="$(printf '%s\n' "${result}" | tail -n 1)"
    device="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["device"])' <<<"${receipt}" 2>/dev/null)" || {
        echo "FAIL: the trainer's last stdout line is not the JSON receipt it"
        echo "      documents. It was: ${receipt}"
        exit 1
    }
    claimed="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["sha256"])' <<<"${receipt}")"

    mkdir -p "$(dirname "${out}")"
    rsync -e "${rsync_ssh}" -a "${target}:${remote_dir}/${out_name}" "${out}"

    local actual
    actual="$(sha256_of "${out}")"
    if [ "${actual}" != "${claimed}" ]; then
        echo "FAIL: ${out} hashes ${actual}; the trainer wrote ${claimed}."
        echo "      The transfer is wrong. Do not paste either digest into a script."
        exit 1
    fi

    if [ "${device}" != "gpu" ] && [ "${allow_cpu}" -eq 0 ]; then
        echo "FAIL: the run reports device '${device}', not 'gpu'."
        echo "      A silent CPU fallback is the failure this exists to make loud."
        echo "      The policy is valid and its numbers are real -- it just took"
        echo "      hours it did not need to. Re-run with --allow-cpu if that was"
        echo "      the intent, or fix the box:  training/remote_train.sh check"
        echo "      The policy is at ${out}; its digest is ${actual}."
        exit 1
    fi

    echo "==> ${out}"
    echo "==> sha256 ${actual}   (device ${device})"
    echo "==> paste that digest into the script:"
    echo "        assembly.policy(task, weights=\"${out_name}\", sha256=\"${actual}\", label=...)"
}

# ---------------------------------------------------------------------------
# detach / watch / pull / stop -- a run you can leave, and see.
# ---------------------------------------------------------------------------
#
# `train` without `--detach` is one ssh that lives as long as the run does.
# A dropped connection, a closed laptop or a sleeping wifi chip is then a
# lost run, and the mg-legs run that motivated M9 took 76 minutes -- long
# enough for all three. So the process is started under `setsid nohup`,
# owned by nothing, and everything after that is polling files.
#
# `progress.json` is the contract. Nothing here parses the trainer stderr:
# ADR-093 measured what happens when a receipt is taken from a stream that
# something else can write into, and the answer was a 3 h 49 m run whose
# dispatch failed on two warp warnings. The trainer writes that file
# atomically every iteration and this reads it, and neither of them cares
# what else is on the terminal.

# The local directory a run mirrors into. Defaults to ./<run-id> so two runs
# cannot land on each other, and takes a project directory when you want the
# shell to see it -- the panel polls <dir>/training-progress.json.
run_destination() {
    if [ -n "${2:-}" ]; then printf %s "$2"; else printf %s "./$1"; fi
}

detached_train() {
    local run_id="$1" remote_dir="$2" bundle_name="$3" out_name="$4" extra="$5"

    # Two things here are subtler than they look, and both were measured
    # rather than reasoned about, because both fail *silently*:
    #
    #   * **The pid file has to be python own.** Writing `$!` after
    #     backgrounding records the pid of the wrapping subshell, and
    #     `setsid` forks again on top of that. Measured: `stop` reported
    #     "stopped", killed the subshell, and left a 4000-iteration run on a
    #     5090 training happily with nothing pointing at it. So the inner
    #     shell writes its **own** pid and then `exec`s, which makes the
    #     recorded number the trainer process itself by construction.
    #   * **ssh has to be able to let go.** `cd X && cmd &` backgrounds the
    #     whole AND-list, so the subshell keeps the ssh channel stdout and
    #     stderr open and the ssh does not return -- which is exactly the
    #     blocking `--detach` exists to remove. The `cd` is therefore its own
    #     statement, and the backgrounded command has all three descriptors
    #     redirected.
    local inner
    inner="echo \$\$ > $(shquote "${remote_dir}/train.pid"); exec"
    inner="${inner} $(shquote "${remote_venv}/bin/python")"
    inner="${inner} $(shquote "${remote_repo}/training/cadex_train.py")"
    inner="${inner} $(shquote "${remote_dir}/${bundle_name}")"
    inner="${inner} --out $(shquote "${remote_dir}/${out_name}")"
    inner="${inner} ${extra}"

    on_box "cd $(shquote "${remote_dir}") || exit 1
            setsid sh -c $(shquote "${inner}") < /dev/null > train.log 2>&1 &"

    # The pid lands as soon as the inner shell runs, which is a fork away
    # rather than an interpreter start away -- but it is still a race, and a
    # `stop` that found no pid file would be a run nobody can end.
    local pid="" attempt=0
    while [ "${attempt}" -lt 20 ]; do
        pid="$(on_box "cat $(shquote "${remote_dir}/train.pid") 2>/dev/null" || true)"
        if [ -n "${pid}" ]; then break; fi
        attempt=$((attempt + 1))
        sleep 1
    done
    if [ -z "${pid}" ]; then
        echo "FAIL: the run started but never wrote ${remote_dir}/train.pid."
        echo "      It may be running and unstoppable. On the box:"
        echo "        tail ${remote_dir}/train.log"
        exit 1
    fi

    echo "==> detached, run ${run_id} (pid ${pid})"
    echo "==> watch it:   $(basename "$0") watch ${run_id}"
    echo "==> stop it:    $(basename "$0") stop ${run_id}"
    echo "==> bring home: $(basename "$0") pull ${run_id}"
}

# One poll: mirror progress.json and any new .cxpolicy back, print a line.
# Split out because `watch` and `pull` differ only in whether they loop.
sync_run() {
    local remote_dir="$1" dest="$2"
    mkdir -p "${dest}"
    # `--ignore-missing-args` is not portable, so a run whose first
    # progress.json has not landed yet is a non-fatal rsync rather than an
    # error: the loop tries again in a moment.
    rsync -e "${rsync_ssh}" -a \
        "${target}:${remote_dir}/progress.json" \
        "${dest}/training-progress.json" 2>/dev/null || return 1
    # Every checkpoint the run has written, including the one it is named
    # for. `-a` skips what has not changed, so this is one stat per file
    # after the first pass.
    rsync -e "${rsync_ssh}" -a --include="*.cxpolicy" --exclude="*" \
        "${target}:${remote_dir}/" "${dest}/" 2>/dev/null || true
    return 0
}

# Read one field out of the mirrored progress file. Absent is empty, never
# an error: the file is written by another machine and a half-second of
# "not there yet" is normal.
progress_field() {
    python3 -c 'import json,sys
try:
    print(json.load(open(sys.argv[1])).get(sys.argv[2], "") or "")
except Exception:
    print("")' "$1" "$2" 2>/dev/null || echo ""
}

cmd_watch() {
    load_config
    require CADEX_TRAIN_WORK "${remote_work}"
    local run_id="${1:-}" dest
    if [ -z "${run_id}" ]; then
        echo "usage: $(basename "$0") watch <run-id> [destination]"
        echo "       destination defaults to ./<run-id>; point it at a .cadex"
        echo "       project directory and the shell Training panel picks it up."
        exit 2
    fi
    dest="$(run_destination "${run_id}" "${2:-}")"
    resolve_remote_paths
    local remote_dir="${remote_work%/}/${run_id}"
    local progress="${dest}/training-progress.json"

    echo "==> ${target}:${remote_dir}"
    echo "==> ${progress}"

    local state="" last=""
    while :; do
        if sync_run "${remote_dir}" "${dest}"; then
            state="$(progress_field "${progress}" state)"
            local line
            line="$(python3 -c 'import json,sys
d = json.load(open(sys.argv[1]))
eta = d.get("eta_s") or 0.0
best = d.get("best_reward_per_step")
steps = d.get("episode_steps")
sigma = d.get("action_std")
print("%-8s %5d/%-5d  reward/step %s  episode %s  sigma %s  best %s @%s  %4.0fs elapsed  %4.0fs left  %d checkpoints" % (
    d.get("state",""), d.get("iteration",-1) + 1, d.get("total",0),
    ("%+.6g" % d["reward_per_step"]) if d.get("reward_per_step") is not None else "-",
    ("%.1f" % steps) if steps is not None else "-",
    ("%.3f" % sigma) if sigma is not None else "-",
    ("%+.6g" % best) if best is not None else "-",
    d.get("best_iteration",-1), d.get("wall_time_s") or 0.0, eta,
    len(d.get("checkpoints") or [])))' "${progress}" 2>/dev/null || echo "")"
            if [ -n "${line}" ] && [ "${line}" != "${last}" ]; then
                echo "    ${line}"
                last="${line}"
            fi
        fi
        case "${state}" in
            done)
                echo "==> finished. Files are in ${dest}"
                ls -1 "${dest}" | sed "s/^/        /"
                return 0 ;;
            failed)
                echo "FAIL: the run reports state 'failed'."
                echo "      $(progress_field "${progress}" error)"
                echo "      The box still has train.log:  $(basename "$0") pull ${run_id}"
                return 1 ;;
        esac
        sleep "${CADEX_TRAIN_POLL_S:-10}"
    done
}

cmd_pull() {
    load_config
    require CADEX_TRAIN_WORK "${remote_work}"
    local run_id="${1:-}" dest
    if [ -z "${run_id}" ]; then
        echo "usage: $(basename "$0") pull <run-id> [destination]"
        exit 2
    fi
    dest="$(run_destination "${run_id}" "${2:-}")"
    resolve_remote_paths
    local remote_dir="${remote_work%/}/${run_id}"
    mkdir -p "${dest}"
    sync_run "${remote_dir}" "${dest}" || echo "NOTE: no progress.json yet."
    # The log too, which is the only place a traceback lives.
    rsync -e "${rsync_ssh}" -a "${target}:${remote_dir}/train.log" \
        "${dest}/train.log" 2>/dev/null || true

    echo "==> ${dest}"
    local file digest
    for file in "${dest}"/*.cxpolicy; do
        [ -f "${file}" ] || continue
        digest="$(sha256_of "${file}")"
        echo "        $(basename "${file}")  ${digest}"
    done
    echo "==> paste a digest into the script:"
    echo "        assembly.policy(task, weights=\"<name>.cxpolicy\", sha256=\"<digest>\", label=...)"
}

cmd_stop() {
    load_config
    require CADEX_TRAIN_WORK "${remote_work}"
    local run_id="${1:-}"
    if [ -z "${run_id}" ]; then
        echo "usage: $(basename "$0") stop <run-id>"
        exit 2
    fi
    resolve_remote_paths
    local remote_dir="${remote_work%/}/${run_id}"

    # TERM rather than KILL: the trainer writes progress.json atomically
    # every iteration and its checkpoints are already on disk, so there is
    # nothing to flush -- but a run killed with -9 leaves a `.partial` beside
    # a file somebody is about to read.
    local report
    report="$(on_box "if [ -f $(shquote "${remote_dir}/train.pid") ]; then \
                          kill -TERM \$(cat $(shquote "${remote_dir}/train.pid")) \
                              2>/dev/null && echo stopped || echo gone; \
                      else echo nopid; fi")"
    case "${report}" in
        stopped)
            # Verified rather than assumed. `kill` succeeding means a signal
            # was delivered to *a* process, and the whole reason the pid file
            # is written the way it is above is that this once reported
            # success while the trainer carried on.
            sleep 2
            local alive
            alive="$(on_box "kill -0 \$(cat $(shquote "${remote_dir}/train.pid")) \
                                 2>/dev/null && echo yes || echo no")"
            if [ "${alive}" = "yes" ]; then
                echo "FAIL: signalled ${run_id}, and it is still running."
                echo "      On the box:  kill -KILL \$(cat ${remote_dir}/train.pid)"
                exit 1
            fi
            echo "==> stopped ${run_id}." ;;
        gone)    echo "==> ${run_id} was not running (already finished, or stopped)." ;;
        *)       echo "FAIL: ${remote_dir}/train.pid does not exist on the box."
                 echo "      That run was not started with --detach."
                 exit 1 ;;
    esac
    echo "==> whatever it wrote is still there:  $(basename "$0") pull ${run_id}"
}

cmd_shell() {
    load_config
    # No BatchMode: this is the command you run *to* accept a host key or
    # type a passphrase, so it has to be allowed to prompt.
    local opts=()
    if [ -n "${port}" ]; then opts+=(-p "${port}"); fi
    if [ -n "${key}" ]; then opts+=(-i "${key}"); fi
    exec ssh ${opts[@]+"${opts[@]}"} "${target}" "$@"
}

cmd_config() {
    load_config
    local note=""
    [ -f "${env_file}" ] || note="   (absent)"
    printf '%-14s %s\n' "env file" "${env_file}${note}"
    printf '%-14s %s\n' target "${target}"
    printf '%-14s %s\n' port "${port}"
    printf '%-14s %s\n' key "${key:--none; ssh config or agent-}"
    printf '%-14s %s\n' repo "${remote_repo:--unset-}"
    printf '%-14s %s\n' venv "${remote_venv:--unset-}"
    printf '%-14s %s\n' work "${remote_work:--unset-}"
}

case "${1:-}" in
    check)  shift; cmd_check "$@" ;;
    train)  shift; cmd_train "$@" ;;
    watch)  shift; cmd_watch "$@" ;;
    pull)   shift; cmd_pull "$@" ;;
    stop)   shift; cmd_stop "$@" ;;
    shell)  shift; cmd_shell "$@" ;;
    config) shift; cmd_config "$@" ;;
    *)
        echo "usage: $(basename "$0") {check|train|watch|pull|stop|shell|config} [args...]"
        echo "       train <bundle.json> <out.cxpolicy> [--allow-cpu] [--detach] [-- trainer args]"
        echo "       watch <run-id> [destination]     poll progress, pull checkpoints"
        echo "       pull  <run-id> [destination]     bring everything home once"
        echo "       stop  <run-id>                   TERM a detached run"
        exit 2 ;;
esac
