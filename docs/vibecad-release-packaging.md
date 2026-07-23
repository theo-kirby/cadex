# VibeCAD Release Packaging

VibeCAD releases are produced by the `VibeCAD Release` GitHub Actions workflow.
The workflow can run from a pushed tag or from `workflow_dispatch`.

## Release Assets

The workflow produces:

- Linux AppImage from the existing Rattler package bundle flow.
- Linux Debian package named `vibecad_<version>_<arch>.deb`.
- Windows portable `.7z` bundle.
- Windows NSIS installer when `make_windows_installer` is enabled.
- SHA256 files for each package.

The Debian package is intentionally self-contained. It installs the bundled
runtime tree under `/opt/vibecad/freecad`, creates `/usr/bin/vibecad`,
and adds a desktop launcher and icon. Users can install it with:

```bash
sudo apt install ./vibecad_*.deb
```

## Manual Release

Run the workflow manually and provide a release tag such as:

```text
vibecad-2026.07.02
```

If the tag is omitted, the workflow creates a prerelease tag using the current
UTC date and short commit SHA.

## Tag Release

Push a tag matching `v*` or `vibecad-*`:

```bash
git tag vibecad-2026.07.02
git push origin vibecad-2026.07.02
```

The release job uploads all Linux and Windows artifacts to the GitHub release
for that tag.

## Local Debian Package Smoke

After running the Linux Rattler bundle locally, build the Debian package with:

```bash
package/linux/build_deb_from_appdir.sh \
  --appdir package/rattler-build/linux/AppDir \
  --output-dir package/rattler-build/linux \
  --version vibecad-local \
  --arch "$(uname -m)"
```
