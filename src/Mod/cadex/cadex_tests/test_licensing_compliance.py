# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The licensing compliance suite (ADR-171).

What a release-readiness audit found broken once, held mechanically so it
cannot silently break again: every file of ours declares its license, every
modified inherited file carries (or is ledgered as) its modification
notice, the modification manifest stays equal to git reality, the tree
carries no GPL source now that the Blender shell is gone (ADR-498), the
attribution and component-map documents keep naming what the binaries require, and a staged
payload actually carries its license material.

Headless and stdlib-only, in the house patterns: AST walks like
``test_nothing_under_analysis_imports_a_gpl_package``, doc-vs-code equality
like ``test_the_protocol_document_matches_the_op_table``. The payload test
gates on ``CADEX_ENGINE_ROOT`` like the packaged lifecycle gate.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
MANIFEST = REPO / "docs" / "inherited-modifications.json"

sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "package" / "engine"))


# ---------------------------------------------------------------------------
# SPDX headers on everything of ours.
# ---------------------------------------------------------------------------

# tree -> (license identifier, extensions checked). Scopes are ours-only by
# construction; inherited files are covered by the notice tests instead.
SPDX_SCOPES = {
    "src/Mod/cadex": ("LGPL-2.1-or-later", {".py", ".pyi", ".cpp", ".sh"}),
    "cli": ("LGPL-2.1-or-later", {".py"}),
    "analysis": ("LGPL-2.1-or-later", {".py"}),
    "training": ("LGPL-2.1-or-later", {".py", ".sh"}),
    "package": ("LGPL-2.1-or-later", {".py", ".sh"}),
    # tools/ is deliberately absent: it mixes our helpers with inherited
    # FreeCAD lint scripts (tools/lint/*) that carry no headers upstream.
}

# Exemptions carry their reason; test_the_exemption_list_is_not_stale keeps
# this from accumulating dead entries. Generated project scripts and binary
# assets are excluded by scope/extension, so nothing needs a row today. The
# one row there was, package/app/make_app_icon.py (GPL in an LGPL tree),
# left with the shell's bundle build (ADR-495).
SPDX_EXEMPT: dict[str, str] = {}


def _head(path: Path, lines: int = 12) -> str:
    return "\n".join(path.read_text(errors="replace").splitlines()[:lines])


def test_every_source_file_declares_the_right_license():
    wrong = []
    for tree, (identifier, exts) in SPDX_SCOPES.items():
        for path in sorted((REPO / tree).rglob("*")):
            rel = path.relative_to(REPO).as_posix()
            if not path.is_file() or path.suffix not in exts or rel in SPDX_EXEMPT:
                continue
            head = _head(path)
            if f"SPDX-License-Identifier: {identifier}" not in head:
                wrong.append(f"{rel}: wants {identifier}")
    if "SPDX-License-Identifier: LGPL-2.1-or-later" not in _head(REPO / "cadex"):
        wrong.append("cadex: the CLI shim wants LGPL-2.1-or-later")
    assert not wrong, "files missing or mis-declaring their license:\n" + "\n".join(wrong)


def test_the_exemption_list_is_not_stale():
    for rel, reason in SPDX_EXEMPT.items():
        assert (REPO / rel).exists(), f"exempt path no longer exists ({reason}): {rel}"


# ---------------------------------------------------------------------------
# Modification notices on inherited files.
# ---------------------------------------------------------------------------


def test_every_modified_inherited_file_carries_its_notice():
    from apply_modification_notices import missing_notices

    missing = [str(p.relative_to(REPO)) for p in missing_notices()]
    assert not missing, (
        "run tools/apply_modification_notices.py --write; missing:\n" + "\n".join(missing)
    )

    # ledger-only entries: the ledger doc itself is the notice, so the file
    # must be named there.
    manifest = json.loads(MANIFEST.read_text())
    unlisted = []
    for tree in manifest["trees"].values():
        ledger_text = (REPO / tree["ledger"]).read_text()
        for entry in tree["files"]:
            if entry.get("notice") == "ledger-only":
                if Path(entry["path"]).name not in ledger_text:
                    unlisted.append(f"{entry['path']} not named in {tree['ledger']}")
    assert not unlisted, "\n".join(unlisted)


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=REPO, text=True, stderr=subprocess.DEVNULL
    )


def test_the_manifest_matches_git_reality():
    """docs/inherited-modifications.json == git diff against the import
    commit of each fork the repository still carries (FreeCAD alone since
    ADR-498): a new edit to an inherited file fails here until it is manifested,
    noticed and ledgered."""
    if not (REPO / ".git").exists():
        pytest.skip("not a git checkout (exported tree)")
    try:
        _git("rev-parse", "--git-dir")
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git is not runnable here")

    manifest = json.loads(MANIFEST.read_text())
    for name, tree in manifest["trees"].items():
        commit = tree["import_commit"]
        try:
            _git("cat-file", "-e", f"{commit}^{{commit}}")
        except subprocess.CalledProcessError:
            pytest.skip(
                f"import commit {commit[:12]} not in this clone "
                "(shallow checkout? CI uses fetch-depth: 0)"
            )
        diff = _git(
            "diff", "--name-only", "--diff-filter=M", commit, "HEAD", "--", *tree["scopes"]
        ).splitlines()
        actual = {
            line
            for line in diff
            if not any(line.startswith(ours) for ours in tree["ours"])
        }
        # `premodified` entries were edited before the squashed import and
        # were invisible to this diff until their notice line itself became
        # the modification -- so they are part of the equality like any
        # other entry, and the flag documents history rather than exempting.
        manifested = {entry["path"] for entry in tree["files"]}
        assert actual == manifested, (
            f"{name}: manifest and git disagree.\n"
            f"  modified but not manifested: {sorted(actual - manifested)}\n"
            f"  manifested but not modified: {sorted(manifested - actual)}\n"
            "Regenerate docs/inherited-modifications.json and run "
            "tools/apply_modification_notices.py --write."
        )


def test_the_manifest_names_only_the_fork_still_in_the_tree():
    """The Blender half of the manifest left with shell/ (ADR-498). Every
    tree the manifest still names must exist on disk, and its ledger must be
    a live doc rather than one moved to docs/history/."""
    manifest = json.loads(MANIFEST.read_text())
    assert set(manifest["trees"]) == {"freecad"}, sorted(manifest["trees"])
    for name, tree in manifest["trees"].items():
        assert not tree["ledger"].startswith("docs/history/"), (name, tree["ledger"])
        assert (REPO / tree["ledger"]).is_file(), (name, tree["ledger"])
        for scope in tree["scopes"]:
            assert (REPO / scope).exists(), f"{name}: scope {scope} is not on disk"


# ---------------------------------------------------------------------------
# The attribution documents keep naming what the binaries require.
# ---------------------------------------------------------------------------


def test_the_notice_file_names_the_binary_grants():
    notice = (REPO / "NOTICE").read_text()
    for required in ("MuJoCo", "Open CASCADE", "OpenTheme", "FreeCAD"):
        assert required in notice, f"NOTICE no longer names {required}"


def test_third_party_licenses_covers_every_vendored_tree():
    """Disk is ground truth: every directory under src/3rdParty/ appears in
    THIRD_PARTY_LICENSES.md."""
    doc = (REPO / "THIRD_PARTY_LICENSES.md").read_text()
    missing = [
        d.name
        for d in sorted((REPO / "src" / "3rdParty").iterdir())
        if d.is_dir() and f"`{d.name}`" not in doc
    ]
    assert not missing, f"src/3rdParty dirs absent from THIRD_PARTY_LICENSES.md: {missing}"


def test_the_recipe_declares_the_engine_license():
    """recipe.yaml carries an about: block with the engine license. Parsed
    by line rather than yaml — this suite is stdlib-only."""
    lines = (REPO / "package" / "rattler-build" / "recipe.yaml").read_text().splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.rstrip() == "about:")
    except StopIteration:
        pytest.fail("recipe.yaml has no about: block")
    block = []
    for line in lines[start + 1 :]:
        if line.strip() and not line.startswith((" ", "\t")):
            break
        block.append(line.strip())
    assert "license: LGPL-2.1-or-later" in block, block
    assert any(l.startswith("license_file:") for l in block), block


# ---------------------------------------------------------------------------
# The collector, and the payload it stages.
# ---------------------------------------------------------------------------


def test_collect_licenses_harvests_a_synthetic_environment(tmp_path):
    import collect_licenses

    env = tmp_path / "env"
    (env / "conda-meta").mkdir(parents=True)
    (env / "conda-meta" / "occt-7.8.1-h1.json").write_text(
        json.dumps({"name": "occt", "version": "7.8.1", "license": "LGPL-2.1-only"})
    )
    (env / "conda-meta" / "nolicense-1-h1.json").write_text(
        json.dumps({"name": "nolicense", "version": "1"})
    )
    occt_doc = env / "share" / "doc" / "opencascade"
    occt_doc.mkdir(parents=True)
    (occt_doc / "LICENSE_LGPL_21.txt").write_text("lgpl")
    (occt_doc / "OCCT_LGPL_EXCEPTION.txt").write_text("exception")
    fc_doc = env / "share" / "doc" / "FreeCAD"
    fc_doc.mkdir(parents=True)
    (fc_doc / "LICENSE.html").write_text("<html>lgpl</html>")
    dist = env / "lib" / "python3.11" / "site-packages" / "mujoco-9.9.9.dist-info"
    (dist / "licenses").mkdir(parents=True)
    (dist / "licenses" / "LICENSE").write_text("apache")

    payload = tmp_path / "payload"
    payload.mkdir()
    collect_licenses.collect(env, payload)

    manifest = json.loads((payload / "licenses" / "MANIFEST.json").read_text())
    assert manifest["schema"] == "cadex-licenses-v1"
    by_name = {p["name"]: p for p in manifest["packages"]}
    assert by_name["occt"]["license"] == "LGPL-2.1-only"
    assert by_name["nolicense"]["license"] == "UNKNOWN"
    assert (payload / "licenses" / "occt" / "OCCT_LGPL_EXCEPTION.txt").is_file()
    assert (payload / "licenses" / "mujoco" / "LICENSE").is_file()
    assert (payload / "NOTICE").is_file(), "repo notices are copied in"

    with pytest.raises(RuntimeError, match="missing"):
        collect_licenses.copy_repo_notices(payload, repo=tmp_path / "not-a-repo")


def test_the_staged_payload_carries_its_license_material():
    root = os.environ.get("CADEX_ENGINE_ROOT")
    if not root:
        pytest.skip("CADEX_ENGINE_ROOT not set (packaged-gate test)")
    payload = Path(root)
    manifest = json.loads((payload / "licenses" / "MANIFEST.json").read_text())
    assert manifest["schema"] == "cadex-licenses-v1" and manifest["packages"]
    for rel in (
        "licenses/occt/OCCT_LGPL_EXCEPTION.txt",
        "licenses/occt/LICENSE_LGPL_21.txt",
        "licenses/mujoco/LICENSE",
        "LICENSE",
        "NOTICE",
        "THIRD_PARTY_LICENSES.md",
    ):
        assert (payload / rel).is_file(), f"payload is missing {rel}"
    dead = [
        str(p.relative_to(payload))
        for pattern in ("libpyside6*", "libshiboken6*", "PySide6-*.dist-info",
                        "shiboken6-*.dist-info")
        for p in payload.rglob(pattern)
    ]
    assert not dead, f"dead PySide material back in the payload: {dead}"


# ---------------------------------------------------------------------------
# The license boundary, mechanized.
# ---------------------------------------------------------------------------


def test_the_repository_carries_no_gpl_source():
    """Cadex was LGPL beside a GPL shell; with shell/ deleted it is LGPL and
    the permissive licences it redistributes, and nothing else (ADR-498).
    The seam the old shell-client test guarded is gone, so what is held now
    is the whole tree: nothing is tracked under shell/, no tracked source
    file declares a GPL (as opposed to LGPL) SPDX identifier in its header,
    and the attribution documents no longer point a reader at shell/."""
    if not (REPO / ".git").exists():
        pytest.skip("not a git checkout (exported tree)")
    assert not _git("ls-files", "--", "shell").strip(), "shell/ is tracked again"
    try:
        hits = _git("grep", "-n", "-I", "-E", r"SPDX-License-Identifier: *A?GPL", "--", ".")
    except subprocess.CalledProcessError:  # git grep exits 1 on no match
        hits = ""
    gpl = []
    for line in hits.splitlines():
        path, number, _ = line.split(":", 2)
        # A header, not prose: Markdown that tells the old shell's story
        # quotes the identifier in running text.
        if int(number) <= 12 and not path.endswith(".md"):
            gpl.append(path)
    assert not gpl, f"GPL-declared source is back in the tree: {gpl}"
    for doc in ("NOTICE", "THIRD_PARTY_LICENSES.md"):
        assert "shell/" not in (REPO / doc).read_text(), f"{doc} still points at shell/"


def test_the_render_font_ships_with_its_licence():
    """ADR-568: the renders' one face is Noto Sans (SIL OFL 1.1), installed
    with the module beside its licence and recorded in PROVENANCE.md; no
    other font file is tracked under the engine module."""
    module = REPO / "src" / "Mod" / "cadex"
    cmake = (module / "CMakeLists.txt").read_text(encoding="utf-8")
    for name in ("NotoSans-Regular-subset.ttf", "NotoSans-OFL.txt"):
        assert (module / name).is_file(), name
        assert f"    {name}\n" in cmake, f"{name} is not installed with the module"
    licence = (module / "NotoSans-OFL.txt").read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE Version 1.1" in licence and "Google LLC" in licence
    fonts = sorted(p.name for p in module.rglob("*") if p.suffix.lower() in {".ttf", ".otf", ".woff", ".woff2"})
    assert fonts == ["NotoSans-Regular-subset.ttf"], fonts
    provenance = (REPO / "docs" / "PROVENANCE.md").read_text(encoding="utf-8")
    assert "NotoSans-Regular-subset.ttf" in provenance and "OFL-1.1" in provenance
