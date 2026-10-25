"""
Как фрагменты строки превращаются в пиксели: фон, цвета, подчеркивание, жирность, стыки рамок.

Шрифт - встроенный в Pillow (``bundled_fonts``). Размер шрифта 8, масштаб 1, поля 0: строка получается 13 пикселей
в высоту, базовая линия лежит в строке 9 (подъем 8, спуск 2). Ширина клетки зависит от движка раскладки текста в сборке
Pillow (8 пикселей без raqm, 7 с ним), поэтому тесты ее не прошивают, а берут из раскладки.
"""

import pytest
from picture import picture

pytest.importorskip("PIL")

from PIL import Image

from termsnap import DARK, Line, Rgb, Span, Style
from termsnap.png import FontSet, render_image
from termsnap.png.layout import Layout
from termsnap.png.text import load_font

GREY = Rgb(200, 200, 200)
BACKGROUND = DARK.background.channels
LEGEND = {".": BACKGROUND, "#": GREY.channels}


def paint(spans: list[Span], fonts: FontSet, *, size: int = 8) -> Image.Image:
    return render_image([Line(tuple(spans))], fonts=fonts, font_size=size, scale=1, padding=0)


def layout_of(fonts: FontSet, *, columns: int, rows: int = 1, size: int = 8) -> Layout:
    return Layout.measure(
        load_font(fonts.regular, size), size=size, margin=0, line_spacing=1.25, columns=columns, rows=rows
    )


def colors(image: Image.Image) -> list[tuple[int, tuple[int, int, int]]]:
    return image.convert("RGB").getcolors(maxcolors=image.width * image.height) or []


def column(image: Image.Image, x: int) -> str:
    """
    Один столбец картинки сверху вниз буквами легенды: как по высоте строки расположены линии.
    """
    return picture(image, LEGEND, box=(x, 0, x + 1, image.height)).replace(chr(10), "")


def test_underline_is_two_pixels_below_the_baseline_and_strike_through_is_above_it(bundled_fonts: FontSet):
    # две клетки: слева с подчеркиванием, справа с зачеркиванием; столбец каждой клетки сверху вниз (13 строк)
    spans = [Span(" ", Style(fg=GREY, underline=True)), Span(" ", Style(fg=GREY, strike=True))]
    image = paint(spans, bundled_fonts)
    second_cell = round(layout_of(bundled_fonts, columns=2).column_x(1))
    assert column(image, 0) == "...........#."  # подчеркивание в строке 11: на два пикселя ниже базовой линии 9
    assert column(image, second_cell) == ".......#....."  # зачеркивание в строке 7: на два выше нее


def test_underline_covers_every_cell_of_the_span_without_gaps(bundled_fonts: FontSet):
    image = paint([Span("   ", Style(fg=GREY, underline=True))], bundled_fonts)
    line = picture(image, LEGEND, box=(0, 11, image.width, 12))
    assert line == "#" * image.width


def test_a_span_background_fills_its_cells_and_stops_at_their_edge(bundled_fonts: FontSet):
    red = Rgb(200, 0, 0)
    image = paint([Span("  ", Style(bg=red)), Span("  ")], bundled_fonts)
    legend = {"R": red.channels, ".": BACKGROUND}
    layout = layout_of(bundled_fonts, columns=4)
    middle = picture(image, legend, box=(0, 6, image.width, 7))
    boundary = round(layout.column_x(2))
    assert middle == "R" * boundary + "." * (image.width - boundary)


def test_inverse_swaps_the_colours_of_the_style(bundled_fonts: FontSet):
    red, blue = Rgb(200, 0, 0), Rgb(0, 0, 200)
    image = paint([Span(" ", Style(fg=red, bg=blue, inverse=True))], bundled_fonts)
    # клетка залита цветом текста, а текст был бы синим
    assert colors(image) == [(image.width * image.height, red.channels)]


def test_inverse_without_colours_uses_the_theme_text_colour_for_the_background(bundled_fonts: FontSet):
    image = paint([Span(" ", Style(inverse=True))], bundled_fonts)
    assert colors(image) == [(image.width * image.height, DARK.foreground.channels)]


def test_dim_text_is_mixed_with_the_background_by_sixty_percent(bundled_fonts: FontSet):
    # сплошной блок рисует сама библиотека, без сглаживания: цвет блока 0.6 * 200 + 0.4 * 0 = 120
    black = Rgb(0, 0, 0)
    image = paint([Span("█", Style(fg=GREY, bg=black, dim=True))], bundled_fonts)
    assert colors(image) == [(image.width * image.height, (120, 120, 120))]


def test_text_is_drawn_in_the_colour_of_its_style_and_only_inside_its_cell(bundled_fonts: FontSet):
    red = Rgb(250, 10, 10)
    image = paint([Span(" "), Span("H", Style(fg=red)), Span(" ")], bundled_fonts, size=14)
    assert red.channels in {color for _count, color in colors(image)}  # сердцевина штрихов закрашена цветом без смеси
    layout = layout_of(bundled_fonts, columns=3, size=14)
    left_edge, right_edge = round(layout.column_x(1)), round(layout.column_x(2))
    outside = [(x, y) for y in range(image.height) for x in range(image.width) if not left_edge <= x < right_edge]
    assert {image.getpixel(point) for point in outside} == {BACKGROUND}


def test_bold_text_is_heavier_even_when_the_family_has_no_bold_face(bundled_fonts: FontSet):
    # в наборе одно обычное начертание: жирность имитируется вторым проходом со сдвигом на пиксель
    def ink(style: Style) -> int:
        image = paint([Span("HHHH", style)], bundled_fonts, size=16)
        return sum(count for count, color in colors(image) if color != BACKGROUND)

    assert ink(Style(fg=GREY, bold=True)) > ink(Style(fg=GREY))


@pytest.mark.parametrize("size", range(9, 31))
def test_a_horizontal_box_line_is_one_unbroken_stroke_across_the_cells_at_any_font_size(
    size: int, bundled_fonts: FontSet
):
    # раньше при некоторых размерах линия пропадала, а на стыках клеток рвалась (банковское округление краев штриха)
    fonts = bundled_fonts
    image = paint([Span("┌──┬──┐", Style(fg=GREY))], fonts, size=size)
    layout = layout_of(fonts, columns=7, size=size)
    stroke_row = max(
        range(image.height), key=lambda y: sum(image.getpixel((x, y)) != BACKGROUND for x in range(image.width))
    )
    lit = [x for x in range(image.width) if image.getpixel((x, stroke_row)) != BACKGROUND]
    assert lit == list(range(lit[0], lit[-1] + 1)), "в линии есть разрыв"
    # линия идет от черточки левого угла до черточки правого: от середины первой клетки минус полтолщины до середины
    # последней плюс полтолщины; края округляются до пикселя, отсюда допуск в один
    half = layout.thickness / 2
    assert abs(lit[0] - (layout.column_x(0) + layout.cell / 2 - half)) <= 1
    assert abs(lit[-1] + 1 - (layout.column_x(6) + layout.cell / 2 + half)) <= 1
