"""
Рисование вывода в PNG (нужна необязательная зависимость ``termsnap[png]``, то есть Pillow).

    from termsnap import run
    from termsnap.png import render_png

    capture = run(["node", "app.js"])
    png = render_png(capture.lines)

Шрифт берется из установленных в системе (см. ``termsnap.png.fonts``): шрифты в пакет не вшиваются.

Как устроено рисование: ``render`` собирает картинку, ``layout`` считает размеры, ``painter`` рисует фрагменты по
клеткам, ``text`` выбирает начертание для символа, ``boxes`` сама рисует рамки и блоки, ``proportions`` хранит числа,
от которых зависит вид картинки, ``pixels`` - общая пиксельная арифметика.
"""

from termsnap.extras import need

need("PIL", "png", "Рисование в PNG")

from termsnap.png.fonts import (
    DEFAULT_FAMILIES,
    FALLBACK_FAMILIES,
    Face,
    FontSet,
    FontSpec,
    find_family,
    from_files,
    resolve,
    resolve_best,
    resolve_spec,
)
from termsnap.png.render import RenderOptions, render_image, render_png

__all__ = [
    "DEFAULT_FAMILIES",
    "FALLBACK_FAMILIES",
    "Face",
    "FontSet",
    "FontSpec",
    "RenderOptions",
    "find_family",
    "from_files",
    "render_image",
    "render_png",
    "resolve",
    "resolve_best",
    "resolve_spec",
]
