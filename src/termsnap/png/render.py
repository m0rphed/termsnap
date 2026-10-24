"""
Отрисовка строк со стилями в картинку PNG: сетка клеток моноширинного шрифта, цвета берутся из темы.

Каждая группа символов (см. ``termsnap.width.clusters``) ставится в свою клетку сетки, поэтому выравнивание не
зависит от ширины глифов; широкие символы (эмодзи, иероглифы) занимают две клетки. Если в основном шрифте нет
глифа, берется первый запасной шрифт из ``termsnap.png.fonts.FALLBACK_FAMILIES``, в котором он есть.

Этот файл только собирает части: выбор шрифта (``fonts``, ``text``), размеры (``layout``), рисование (``painter``).
"""

import io
from collections.abc import Sequence
from typing import TypedDict, Unpack

from PIL import Image

from termsnap.model import Line
from termsnap.png import proportions
from termsnap.png.fonts import FontSpec, resolve_spec
from termsnap.png.layout import Layout
from termsnap.png.painter import Painter
from termsnap.png.text import load_font
from termsnap.theme import DARK, ThemeSpec, get_theme


def render_image(
    lines: Sequence[Line],
    *,
    theme: ThemeSpec = DARK,
    fonts: FontSpec | None = None,
    font_size: float = proportions.DEFAULT_FONT_SIZE,
    scale: int = proportions.DEFAULT_SCALE,
    padding: int = proportions.DEFAULT_PADDING,
    line_spacing: float = proportions.DEFAULT_LINE_SPACING,
    columns: int | None = None,
) -> Image.Image:
    """
    Рисует строки на фоне темы. ``theme`` - ``Theme``, имя темы (``"light"``) или словарь для ``Theme.from_mapping``
    (см. ``termsnap.get_theme``). ``font_size`` и ``padding`` задаются в пикселях "как на экране", ``scale`` - во
    сколько раз картинка подробнее (при 2 текст четкий на дисплеях высокой плотности). ``padding`` - поля со всех
    четырех сторон, можно ``0``. ``columns`` - ширина картинки в клетках (по умолчанию по самой длинной строке).

    ``fonts`` - основной шрифт: готовый ``FontSet``, имя семейства или список семейств в порядке предпочтения (см.
    ``termsnap.png.fonts.resolve_spec``); не задан - выбирается из установленных по умолчанию. Основной шрифт
    переопределяется, а символы, которых в нем нет (эмодзи, стрелки, иероглифы), по-прежнему рисуются запасными
    шрифтами автоматически, рамки и блоки рисует сама библиотека.
    """
    if padding < 0:
        raise ValueError(f"поля не могут быть отрицательными: {padding}")
    theme = get_theme(theme)
    fontset = resolve_spec(fonts, covers="".join(line.text for line in lines))  # основной шрифт должен покрыть текст
    size = round(font_size * scale)
    layout = Layout.measure(
        load_font(fontset.regular, size),
        size=size,
        margin=padding * scale,
        line_spacing=line_spacing,
        columns=columns if columns is not None else max((line.width for line in lines), default=1),
        rows=len(lines),
    )
    image = Image.new("RGB", (layout.width, layout.height), theme.background.channels)
    painter = Painter(image, layout, theme, fontset)
    for row, line in enumerate(lines):
        painter.paint_line(row, line)
    return image


class RenderOptions(TypedDict, total=False):
    """
    Параметры ``render_image`` и ``render_png`` (все необязательны), см. ``render_image``.
    """

    theme: ThemeSpec
    fonts: FontSpec
    font_size: float
    scale: int
    padding: int
    line_spacing: float
    columns: int


def render_png(lines: Sequence[Line], **options: Unpack[RenderOptions]) -> bytes:
    """
    То же, что ``render_image``, но возвращает байты PNG. В файл записывается разрешение 96 точек на дюйм,
    умноженное на ``scale``, поэтому в Word и браузере картинка имеет "экранный" размер.
    """
    image = render_image(lines, **options)
    dpi = proportions.SCREEN_DPI * options.get("scale", proportions.DEFAULT_SCALE)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", dpi=(dpi, dpi))
    return buffer.getvalue()
