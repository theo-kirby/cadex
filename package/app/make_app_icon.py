#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Generate the macOS app icon from the repository's Cadex logo.

    pixi run python package/app/make_app_icon.py [--light] [--out <path>]

The icon that ships is `shell/release/darwin/Blender.app/Contents/Resources/
cadex_icon.icns`, and it used to be the VibeCAD-era mark that the Stage C
rebrand missed (so does `docs/images/cadex-mark.svg` -- that file is the old
design too, do not reach for it). The source of truth is the logo the README
shows: `cadex-logo-white.png` on dark, `cadex-logo-black.png` on light.

A README logo is a bare mark on transparency; a Dock icon is not. macOS
composites it against wallpaper, so it needs its own body -- hence the rounded
square underneath, sized to Apple's grid (824/1024 with a 185 corner radius),
which is also what keeps the Dock silhouette the same shape it was.

This script exists so the icns is *derived* rather than dropped in: rerun it
whenever the logo changes, and the binary in the tree stays explainable.
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

REPO = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO / "shell/release/darwin/Blender.app/Contents/Resources/cadex_icon.icns"

CANVAS = 1024
BODY = 824  # Apple's icon grid: the rounded square inside a 1024 canvas.
RADIUS = 185
MARK_FRACTION = 0.60  # the mark's longest side, as a fraction of the body

DARK_BG = (14, 17, 22, 255)  # #0e1116, the shell's own dark
LIGHT_BG = (255, 255, 255, 255)

# Every size `iconutil` wants: (pixel size, iconset filename).
ICONSET = [
    (16, "icon_16x16.png"),
    (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"),
    (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"),
    (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"),
    (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"),
    (1024, "icon_512x512@2x.png"),
]


def compose(logo_path: pathlib.Path, background: tuple[int, int, int, int]) -> Image.Image:
    icon = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))

    body = Image.new("RGBA", (BODY, BODY), (0, 0, 0, 0))
    ImageDraw.Draw(body).rounded_rectangle(
        [(0, 0), (BODY - 1, BODY - 1)], radius=RADIUS, fill=background
    )
    offset = (CANVAS - BODY) // 2
    icon.alpha_composite(body, (offset, offset))

    # Trim the logo's own transparent padding before scaling, or the mark ends
    # up smaller than asked for and off-centre by whatever the padding was.
    logo = Image.open(logo_path).convert("RGBA")
    bbox = logo.getbbox()
    if bbox is None:
        sys.exit(f"FAIL: {logo_path} is fully transparent")
    logo = logo.crop(bbox)

    target = int(BODY * MARK_FRACTION)
    scale = target / max(logo.size)
    logo = logo.resize(
        (max(1, round(logo.width * scale)), max(1, round(logo.height * scale))),
        Image.LANCZOS,
    )
    icon.alpha_composite(
        logo, ((CANVAS - logo.width) // 2, (CANVAS - logo.height) // 2)
    )
    return icon


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--light",
        action="store_true",
        help="black mark on white instead of white mark on the shell's dark",
    )
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--png",
        type=pathlib.Path,
        help="also write the composed 1024px source next to the icns",
    )
    args = ap.parse_args()

    logo = REPO / ("cadex-logo-black.png" if args.light else "cadex-logo-white.png")
    if not logo.is_file():
        sys.exit(f"FAIL: {logo} not found")
    if shutil.which("iconutil") is None:
        sys.exit("FAIL: iconutil not found; this script is macOS-only")

    icon = compose(logo, LIGHT_BG if args.light else DARK_BG)
    if args.png:
        icon.save(args.png)

    with tempfile.TemporaryDirectory() as tmp:
        iconset = pathlib.Path(tmp) / "cadex.iconset"
        iconset.mkdir()
        for size, name in ICONSET:
            icon.resize((size, size), Image.LANCZOS).save(iconset / name)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(args.out)], check=True
        )
    print(f"==> wrote {args.out}  (from {logo.name})")


if __name__ == "__main__":
    main()
