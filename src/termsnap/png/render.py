"""
Отрисовка строк со стилями в картинку PNG: сетка клеток моноширинного шрифта, цвета берутся из темы.

Каждая группа символов (см. ``termsnap.width.clusters``) ставится в свою клетку сетки, поэтому выравнивание не
зависит от ширины глифов; широкие символы (эмодзи, иероглифы) занимают две клетки. Если в основном шрифте нет
глифа, берется первый запасной шрифт из ``termsnap.png.fonts.FALLBACK_FAMILIES``, в котором он есть.
"""

import io
import math
from collections.abc import Sequence
from functools import cache
from typing import TypedDict, Unpack

from PIL import Image, ImageDraw, ImageFont, features

from termsnap.errors import FontNotFound
from termsnap.model import Line, Rgb
from termsnap.png.boxes import draw_cell
from termsnap.png.fonts import Face, FontSet, fallback_fontsets, has_glyph, resolve, resolve_best
from termsnap.theme import DARK, Theme
from termsnap.width import cluster_width, clusters

#: Доля цвета текста в тусклом (``dim``) тексте; остальное - цвет фона.
_DIM_SHARE = 0.6

_ZWJ = "\u200d"
_SELECTORS = {"\ufe0e", "\ufe0f"}

#: Отключение лигатур для шрифтов с лигатурами: работает только при наличии библиотеки raqm в сборке Pillow.
_NO_LIGATURES = ["-liga", "-clig", "-calt"]


@cache
def _font(face: Face, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(face.path), size=size, index=face.index)


@cache
def _covers(face: Face, size: int, char: str) -> bool:
    try:
        return has_glyph(_font(face, size), char)
    except OSError:  # растровые шрифты эмодзи с одним допустимым размером не открываются в произвольном
        return False


def _blend(foreground: Rgb, background: Rgb, share: float) -> Rgb:
    def channel(front: int, back: int) -> int:
        return round(front * share + back * (1 - share))

    return Rgb(
        channel(foreground.red, background.red),
        channel(foreground.green, background.green),
        channel(foreground.blue, background.blue),
    )


def _rgb(color: Rgb) -> tuple[int, int, int]:
    return color.red, color.green, color.blue


def _main_fonts(text: str) -> FontSet:
    """
    Основной шрифт для текста: первое семейство по умолчанию, в котором есть все символы; если такого нет (в тексте
    эмодзи или редкие знаки) - семейство, в котором их больше всего.
    """
    try:
        return resolve(covers=text)
    except FontNotFound:
        return resolve_best(covers=text)


def _drawn_text(cluster: str) -> str:
    """
    Что рисовать для группы символов: без селекторов начертания и без продолжения составного эмодзи (без
    библиотеки raqm Pillow не умеет их шаблонизировать и рисует «пустой» знак).
    """
    return "".join(char for char in cluster.split(_ZWJ)[0] if char not in _SELECTORS)


def _choose(fonts: FontSet, size: int, char: str, *, bold: bool, italic: bool) -> tuple[Face, bool, bool]:
    """
    Начертание для символа: основное, если в нем есть глиф, иначе первое запасное с глифом. Возвращает начертание,
    нужна ли имитация жирности и признак запасного шрифта.
    """
    face, synthetic = fonts.pick(bold=bold, italic=italic)
    if char.isascii() or _covers(face, size, char):
        return face, synthetic, False
    for fallback in fallback_fontsets():
        alternative, alternative_synthetic = fallback.pick(bold=bold, italic=italic)
        if _covers(alternative, size, char):
            return alternative, alternative_synthetic, True
    return face, synthetic, False


def render_image(
    lines: Sequence[Line],
    *,
    theme: Theme = DARK,
    fonts: FontSet | None = None,
    font_size: float = 14,
    scale: int = 2,
    padding: int = 16,
    line_spacing: float = 1.25,
    columns: int | None = None,
) -> Image.Image:
    """
    Рисует строки на фоне темы. ``font_size`` и ``padding`` задаются в пикселях «как на экране», ``scale`` - во
    сколько раз картинка подробнее (при 2 текст четкий на дисплеях высокой плотности). ``columns`` - ширина
    картинки в клетках (по умолчанию по самой длинной строке). Если ``fonts`` не заданы, основной шрифт выбирается
    автоматически из установленных (см. ``termsnap.png.fonts.resolve``), недостающие символы рисуются запасными.
    """
    fonts = fonts or _main_fonts("".join(line.text for line in lines))
    size = round(font_size * scale)
    regular = _font(fonts.regular, size)
    ascent, descent = regular.getmetrics()
    cell = regular.getlength("M")
    row_height = math.ceil((ascent + descent) * line_spacing)
    margin = padding * scale
    width_cells = columns if columns is not None else max((line.width for line in lines), default=1)
    width = round(margin + max(width_cells, 1) * cell) + margin  # правый край совпадает с краем фона последней клетки
    height = margin * 2 + max(len(lines), 1) * row_height

    image = Image.new("RGB", (width, height), _rgb(theme.background))
    draw = ImageDraw.Draw(image)
    thickness = max(1, size // 14)
    draw_features = _NO_LIGATURES if features.check("raqm") else None
    for row, line in enumerate(lines):
        top = margin + row * row_height
        baseline = top + (row_height - ascent - descent) // 2 + ascent
        column = 0
        for span in line.spans:
            left = margin + column * cell
            right = margin + (column + span.width) * cell
            foreground, background = theme.colors_of(span.style)
            if span.style.dim:
                foreground = _blend(foreground, background, _DIM_SHARE)
            if background != theme.background:
                draw.rectangle((round(left), top, round(right) - 1, top + row_height - 1), fill=_rgb(background))
            offset = column
            for cluster in clusters(span.text):
                x = margin + offset * cell
                if cluster.strip() and not draw_cell(
                    draw, cluster, (x, top, x + cell, top + row_height), _rgb(foreground), _rgb(background), thickness
                ):
                    face, synthetic_bold, fallback = _choose(
                        fonts, size, cluster[0], bold=span.style.bold, italic=span.style.italic
                    )
                    font = _font(face, size)
                    for shift in (0, max(1, size // 16)) if synthetic_bold else (0,):
                        draw.text(
                            (x + shift, baseline),
                            _drawn_text(cluster),
                            font=font,
                            fill=_rgb(foreground),
                            anchor="ls",
                            features=draw_features,
                            embedded_color=fallback,
                        )
                offset += cluster_width(cluster)
            column += span.width
            if span.style.underline:
                y = baseline + max(2, descent // 3)
                draw.rectangle((round(left), y, round(right) - 1, y + thickness - 1), fill=_rgb(foreground))
            if span.style.strike:
                y = baseline - round(ascent * 0.3)
                draw.rectangle((round(left), y, round(right) - 1, y + thickness - 1), fill=_rgb(foreground))
    return image


class RenderOptions(TypedDict, total=False):
    """
    Параметры ``render_image`` и ``render_png`` (все необязательны), см. ``render_image``.
    """

    theme: Theme
    fonts: FontSet
    font_size: float
    scale: int
    padding: int
    line_spacing: float
    columns: int


def render_png(lines: Sequence[Line], **options: Unpack[RenderOptions]) -> bytes:
    """
    То же, что ``render_image``, но возвращает байты PNG. В файл записывается разрешение 96 точек на дюйм,
    умноженное на ``scale``, поэтому в Word и браузере картинка имеет «экранный» размер.
    """
    image = render_image(lines, **options)
    dpi = 96 * options.get("scale", 2)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", dpi=(dpi, dpi))
    return buffer.getvalue()
