# SPDX-License-Identifier: LGPL-2.1-or-later

"""Generate Windows and Qt branding assets from the canonical VibeCAD mark."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_prefix_font_dir = Path(sys.prefix) / "fonts"
if _prefix_font_dir.is_dir():
    os.environ.setdefault("QT_QPA_FONTDIR", str(_prefix_font_dir))

from PIL import Image
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
)
from PySide6.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
MASTER_MARK = ROOT / "src" / "Mod" / "VibeCAD" / "preferences-vibecad.svg"
GUI_ICONS = ROOT / "src" / "Gui" / "Icons"
MAIN_DIR = ROOT / "src" / "Main"
INSTALLER_DIR = ROOT / "package" / "WindowsInstaller"

INK = QColor("#0e1116")
PANEL = QColor("#151b23")
TEXT = QColor("#e8edf2")
MUTED = QColor("#a9b4c0")
BLUE = QColor("#4dabf7")
LIGHT_BLUE = QColor("#74c0fc")
FONT_FAMILY = "Ubuntu"


def _application() -> QGuiApplication:
    return QGuiApplication.instance() or QGuiApplication([])


def _load_fonts() -> None:
    global FONT_FAMILY
    prefix_fonts = Path(sys.prefix) / "fonts"
    candidates = [
        prefix_fonts / "Ubuntu-R.ttf",
        prefix_fonts / "Ubuntu-B.ttf",
    ]
    windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    if not candidates[0].is_file():
        candidates = [
            windows_fonts / "segoeui.ttf",
            windows_fonts / "segoeuib.ttf",
        ]
    families: list[str] = []
    for candidate in candidates:
        if not candidate.is_file():
            continue
        font_id = QFontDatabase.addApplicationFont(str(candidate))
        if font_id >= 0:
            families.extend(QFontDatabase.applicationFontFamilies(font_id))
    if not families:
        raise RuntimeError("Could not load a deterministic branding font.")
    FONT_FAMILY = families[0]


def _canvas(width: int, height: int) -> QImage:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(INK)
    painter = QPainter(image)
    gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0.0, INK)
    gradient.setColorAt(0.62, PANEL)
    gradient.setColorAt(1.0, QColor("#10283a"))
    painter.fillRect(image.rect(), gradient)
    painter.setPen(QPen(QColor(77, 171, 247, 24), 1))
    spacing = max(16, round(min(width, height) / 12))
    for x in range(0, width, spacing):
        painter.drawLine(x, 0, x, height)
    for y in range(0, height, spacing):
        painter.drawLine(0, y, width, y)
    painter.end()
    return image


def _draw_logo(painter: QPainter, renderer: QSvgRenderer, rect: QRectF) -> None:
    renderer.render(painter, rect)


def _font(pixel_size: int, *, bold: bool = False) -> QFont:
    font = QFont(FONT_FAMILY)
    font.setPixelSize(pixel_size)
    if bold:
        font.setWeight(QFont.Weight.Bold)
    return font


def _save_png(image: QImage, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(path), "PNG"):
        raise RuntimeError(f"Could not write PNG asset: {path}")


def _save_bmp(image: QImage, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rgb = image.convertToFormat(QImage.Format.Format_RGB888)
    if not rgb.save(str(path), "BMP"):
        raise RuntimeError(f"Could not write BMP asset: {path}")


def _render_icon(renderer: QSvgRenderer, size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def _write_icon(renderer: QSvgRenderer) -> None:
    png_path = GUI_ICONS / "vibecad-icon-256.png"
    _save_png(_render_icon(renderer, 256), png_path)
    with Image.open(png_path) as source:
        rgba = source.convert("RGBA")
        ico_path = MAIN_DIR / "vibecad.ico"
        rgba.save(
            ico_path,
            format="ICO",
            sizes=[
                (16, 16),
                (20, 20),
                (24, 24),
                (32, 32),
                (40, 40),
                (48, 48),
                (64, 64),
                (128, 128),
                (256, 256),
            ],
        )
    installer_icon = INSTALLER_DIR / "icons" / "VibeCAD.ico"
    installer_icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ico_path, installer_icon)


def _write_header(renderer: QSvgRenderer) -> None:
    image = _canvas(150, 57)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    _draw_logo(painter, renderer, QRectF(7, 5, 47, 47))
    painter.setFont(_font(19, bold=True))
    painter.setPen(TEXT)
    painter.drawText(QRectF(59, 0, 88, 57), Qt.AlignmentFlag.AlignVCenter, "VibeCAD")
    painter.end()
    _save_bmp(image, INSTALLER_DIR / "graphics" / "vibecad-header.bmp")


def _write_banner(renderer: QSvgRenderer) -> None:
    image = _canvas(164, 314)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    _draw_logo(painter, renderer, QRectF(30, 29, 104, 104))
    painter.setPen(TEXT)
    painter.setFont(_font(29, bold=True))
    painter.drawText(
        QRectF(8, 150, 148, 42),
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        "VibeCAD",
    )
    painter.setPen(LIGHT_BLUE)
    painter.setFont(_font(14, bold=True))
    painter.drawText(
        QRectF(8, 196, 148, 45),
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        "AI-native\nparametric CAD",
    )
    painter.setPen(MUTED)
    painter.setFont(_font(10))
    painter.drawText(
        QRectF(8, 276, 148, 24),
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        "Powered by FreeCAD",
    )
    painter.end()
    _save_bmp(image, INSTALLER_DIR / "graphics" / "vibecad-banner.bmp")


def _splash(renderer: QSvgRenderer, width: int, height: int) -> QImage:
    scale = width / 568.0
    image = _canvas(width, height)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    margin = round(38 * scale)
    logo_size = round(150 * scale)
    _draw_logo(painter, renderer, QRectF(margin, margin, logo_size, logo_size))
    text_x = margin + logo_size + round(35 * scale)
    painter.setPen(TEXT)
    painter.setFont(_font(round(58 * scale), bold=True))
    painter.drawText(
        QRectF(text_x, round(62 * scale), width - text_x - margin, round(78 * scale)),
        Qt.AlignmentFlag.AlignVCenter,
        "VibeCAD",
    )
    painter.setPen(LIGHT_BLUE)
    painter.setFont(_font(round(22 * scale), bold=True))
    painter.drawText(
        QRectF(text_x, round(145 * scale), width - text_x - margin, round(42 * scale)),
        Qt.AlignmentFlag.AlignVCenter,
        "AI-native parametric CAD",
    )
    painter.setPen(MUTED)
    painter.setFont(_font(round(15 * scale)))
    painter.drawText(
        QRectF(margin, height - round(58 * scale), width - 2 * margin, round(28 * scale)),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        "Built on FreeCAD's open parametric modeling engine",
    )
    painter.setPen(QPen(BLUE, max(2, round(3 * scale))))
    painter.drawLine(
        margin,
        height - round(75 * scale),
        width - margin,
        height - round(75 * scale),
    )
    painter.end()
    return image


def _write_splash(renderer: QSvgRenderer) -> None:
    _save_png(_splash(renderer, 568, 368), GUI_ICONS / "vibecadsplash.png")
    _save_png(_splash(renderer, 1136, 736), GUI_ICONS / "vibecadsplash_2x.png")


def _about(renderer: QSvgRenderer, *, development: bool) -> QImage:
    width, height = 552, 189
    image = _canvas(width, height)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    _draw_logo(painter, renderer, QRectF(24, 24, 141, 141))
    painter.setPen(TEXT)
    painter.setFont(_font(48, bold=True))
    painter.drawText(QRectF(190, 26, 335, 62), Qt.AlignmentFlag.AlignVCenter, "VibeCAD")
    painter.setPen(LIGHT_BLUE)
    painter.setFont(_font(18, bold=True))
    painter.drawText(
        QRectF(193, 91, 330, 31),
        Qt.AlignmentFlag.AlignVCenter,
        "AI-native parametric CAD",
    )
    painter.setPen(MUTED)
    painter.setFont(_font(13))
    painter.drawText(
        QRectF(193, 128, 330, 27),
        Qt.AlignmentFlag.AlignVCenter,
        "Powered by FreeCAD",
    )
    if development:
        painter.setPen(INK)
        painter.setBrush(LIGHT_BLUE)
        painter.drawRoundedRect(QRectF(409, 20, 116, 25), 7, 7)
        painter.setFont(_font(11, bold=True))
        painter.drawText(
            QRectF(409, 20, 116, 25),
            Qt.AlignmentFlag.AlignCenter,
            "DEVELOPMENT",
        )
    painter.end()
    return image


def _write_about(renderer: QSvgRenderer) -> None:
    _save_png(_about(renderer, development=False), GUI_ICONS / "vibecadabout.png")
    _save_png(_about(renderer, development=True), GUI_ICONS / "vibecadaboutdev.png")


def main() -> None:
    _application()
    _load_fonts()
    renderer = QSvgRenderer(str(MASTER_MARK))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid VibeCAD master mark: {MASTER_MARK}")
    shutil.copyfile(MASTER_MARK, GUI_ICONS / "vibecad.svg")
    _write_icon(renderer)
    _write_header(renderer)
    _write_banner(renderer)
    _write_splash(renderer)
    _write_about(renderer)
    print("Generated VibeCAD branding assets.")


if __name__ == "__main__":
    main()
