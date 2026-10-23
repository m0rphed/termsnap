"""
Рисование вывода в PNG (нужна необязательная зависимость ``termsnap[png]``, то есть Pillow).

    from termsnap import run
    from termsnap.png import render_png

    capture = run(["node", "app.js"])
    png = render_png(capture.lines)

Шрифт берется из установленных в системе (см. ``termsnap.png.fonts``): шрифты в пакет не вшиваются.
"""

from termsnap.png.fonts import (
    DEFAULT_FAMILIES,
    FALLBACK_FAMILIES,
    Face,
    FontSet,
    find_family,
    from_files,
    resolve,
    resolve_best,
)
from termsnap.png.render import RenderOptions, render_image, render_png

__all__ = [
    "DEFAULT_FAMILIES",
    "FALLBACK_FAMILIES",
    "Face",
    "FontSet",
    "RenderOptions",
    "find_family",
    "from_files",
    "render_image",
    "render_png",
    "resolve",
    "resolve_best",
]
