"""
Цвета на картинке: 16 базовых цветов берутся из темы, 16-255 - из палитры xterm, Rgb - как есть; умолчания, обращение
и тусклость. Одноклеточные картинки заливаются сплошным блоком (его рисует библиотека, без сглаживания), поэтому
ожидаемый цвет - одно число, а не рисунок.
"""

import pytest
from picture import cell_colors
from support import require_module

require_module("PIL")

from termsnap import DARK, LIGHT, Indexed, Line, Rgb, Span, Style
from termsnap.png import FontSet, render_image
from termsnap.theme import Theme

#: Цвета тем, как они поставляются (записаны здесь, чтобы случайная правка темы не прошла незамеченной).
DARK_ANSI = [
    "#000000", "#cd3131", "#0dbc79", "#e5e510", "#2472c8", "#bc3fbc", "#11a8cd", "#e5e5e5",
    "#666666", "#f14c4c", "#23d18b", "#f5f543", "#3b8eea", "#d670d6", "#29b8db", "#e5e5e5",
]  # fmt: skip
LIGHT_ANSI = [
    "#000000", "#cd3131", "#00bc00", "#949800", "#0451a5", "#bc05bc", "#0598bc", "#555555",
    "#666666", "#cd3131", "#14ce14", "#b5ba00", "#0451a5", "#bc05bc", "#0598bc", "#a5a5a5",
]  # fmt: skip


def hexes(colors: list[tuple[int, int, int]]) -> list[str]:
    return [Rgb(*color).hex for color in colors]


def swatches(theme: Theme, fonts: FontSet, indexes: range | list[int]) -> list[tuple[int, int, int]]:
    """
    Цвета, которыми закрашены клетки с фоном ``Indexed(n)`` для каждого n из ``indexes``.
    """
    line = Line(tuple(Span(" ", Style(bg=Indexed(index))) for index in indexes))
    image = render_image([line], fonts=fonts, theme=theme, scale=1, padding=0)
    return cell_colors(image, columns=len(indexes))


def solid(style: Style, fonts: FontSet, theme: Theme = DARK) -> tuple[int, int, int]:
    """
    Цвет сплошного блока со стилем ``style`` (блок занимает всю клетку).
    """
    image = render_image([Line((Span("█", style),))], fonts=fonts, theme=theme, scale=1, padding=0)
    ((_count, color),) = image.convert("RGB").getcolors() or [(0, (-1, -1, -1))]
    return color


def test_the_shipped_themes_have_these_sixteen_colours():
    assert [Rgb(*color.channels).hex for color in DARK.ansi] == DARK_ANSI
    assert [Rgb(*color.channels).hex for color in LIGHT.ansi] == LIGHT_ANSI


GREYS = [f"#{n:02x}{n:02x}{n:02x}" for n in range(0, 160, 10)]  # 16 серых ступеней: 000000, 0a0a0a, ... 969696
TWO_REPLACED = [*DARK_ANSI[:1], "#12ab34", *DARK_ANSI[2:15], "#fefefe"]  # красный (1) и ярко-белый (15) свои


@pytest.mark.parametrize(
    ("theme", "expected"),
    [
        (DARK, DARK_ANSI),
        (LIGHT, LIGHT_ANSI),
        # свою палитру можно поправить в паре цветов (остальные от базовой темы) или задать целиком
        (DARK.derive(ansi={"red": "#12ab34", "bright_white": "#fefefe"}), TWO_REPLACED),
        (LIGHT.derive(ansi=GREYS), GREYS),
    ],
    ids=["dark", "light", "dark-with-two-colours-replaced", "light-with-all-colours-replaced"],
)
def test_basic_colours_are_painted_in_the_colours_of_the_theme(
    theme: Theme, expected: list[str], bundled_fonts: FontSet
):
    assert hexes(swatches(theme, bundled_fonts, range(16))) == expected


@pytest.mark.parametrize("theme", [DARK, LIGHT, DARK.derive(ansi={"red": "#12ab34"})], ids=["dark", "light", "custom"])
def test_colours_from_16_to_255_do_not_depend_on_the_theme(theme: Theme, bundled_fonts: FontSet):
    indexes = [16, 21, 46, 196, 208, 231, 232, 243, 255]
    # куб 6x6x6: 16 - черный, 21 - чистый синий, 46 - зеленый, 196 - красный, 208 - оранжевый, 231 - белый;
    # затем серые ступени: 232 - самая темная, 255 - самая светлая
    expected = [(0, 0, 0), (0, 0, 255), (0, 255, 0), (255, 0, 0), (255, 135, 0)]
    expected += [(255, 255, 255), (8, 8, 8), (118, 118, 118), (238, 238, 238)]
    assert swatches(theme, bundled_fonts, indexes) == expected


def test_truecolor_is_painted_as_it_is_in_any_theme(bundled_fonts: FontSet):
    for theme in (DARK, LIGHT):
        assert solid(Style(fg=Rgb(1, 2, 3)), bundled_fonts, theme) == (1, 2, 3)


@pytest.mark.parametrize(
    ("theme", "expected"), [(DARK, (0xCC, 0xCC, 0xCC)), (LIGHT, (0x33, 0x33, 0x33))], ids=["dark", "light"]
)
def test_text_without_a_colour_uses_the_default_foreground_of_the_theme(theme, expected, bundled_fonts: FontSet):
    assert solid(Style(), bundled_fonts, theme) == expected


def test_bold_does_not_change_the_colour(bundled_fonts: FontSet):
    # жирный не заменяет красный (1) на яркий красный (9): яркие цвета задаются своими кодами
    assert solid(Style(fg=Indexed(1), bold=True), bundled_fonts) == (0xCD, 0x31, 0x31)


@pytest.mark.parametrize(
    ("theme", "expected"),
    [(DARK, (134, 134, 134)), (LIGHT, (133, 133, 133))],
    ids=["dark", "light"],
)
def test_dim_default_text_is_sixty_percent_text_and_forty_percent_background(theme, expected, bundled_fonts: FontSet):
    # тёмная тема: 0.6 * 204 + 0.4 * 30 = 134.4; светлая: 0.6 * 51 + 0.4 * 255 = 132.6
    assert solid(Style(dim=True), bundled_fonts, theme) == expected


def test_inverse_paints_a_cell_in_the_text_colour_whatever_the_kind_of_colour(bundled_fonts: FontSet):
    cells = [
        Style(fg=Indexed(2), bg=Indexed(4), inverse=True),  # базовый цвет из темы
        Style(fg=Indexed(196), inverse=True),  # цвет палитры xterm
        Style(fg=Rgb(9, 8, 7), inverse=True),  # truecolor
    ]
    line = Line(tuple(Span(" ", style) for style in cells))
    image = render_image([line], fonts=bundled_fonts, scale=1, padding=0)
    assert cell_colors(image, columns=3) == [DARK.ansi[2].channels, (255, 0, 0), (9, 8, 7)]
