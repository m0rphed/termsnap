"""
Палитра терминала и запись цвета: расчет цветов 16-255 по правилам xterm, шестнадцатеричные цвета, имена базовых цветов.
"""

import pytest

from termsnap import ANSI_NAMES, DARK, Indexed, Rgb
from termsnap.theme.palette import ansi_index, extended_color


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (16, (0, 0, 0)),  # начало куба: черный
        (17, (0, 0, 95)),  # синий растет первым: младшая цифра куба
        (21, (0, 0, 255)),
        (22, (0, 95, 0)),
        (46, (0, 255, 0)),
        (52, (95, 0, 0)),
        (196, (255, 0, 0)),
        (208, (255, 135, 0)),  # оранжевый
        (231, (255, 255, 255)),  # конец куба: белый
        (232, (8, 8, 8)),  # начало серых ступеней
        (243, (118, 118, 118)),
        (255, (238, 238, 238)),
    ],
)
def test_extended_palette_follows_xterm(index: int, expected: tuple[int, int, int]):
    assert extended_color(index).channels == expected


def test_theme_takes_basic_colors_from_itself_and_the_rest_from_xterm():
    assert DARK.resolve(Indexed(1)) == DARK.ansi[1]
    assert DARK.resolve(Indexed(15)) == DARK.ansi[15]
    assert DARK.resolve(Indexed(16)) == extended_color(16)
    assert DARK.resolve(Rgb(1, 2, 3)) == Rgb(1, 2, 3)


def test_hex_colors_are_read_with_or_without_the_hash():
    assert Rgb.from_hex("cd3131") == Rgb(0xCD, 0x31, 0x31)
    assert Rgb.from_hex("#CD3131") == Rgb(0xCD, 0x31, 0x31)
    assert Rgb(0xCD, 0x31, 0x31).hex == "#cd3131"
    assert Rgb(1, 2, 3).channels == (1, 2, 3)


@pytest.mark.parametrize("bad", ["", "fff", "12345", "1234567", "gggggg"])
def test_bad_hex_colors_are_rejected(bad: str):
    with pytest.raises(ValueError):
        Rgb.from_hex(bad)


def test_basic_colors_are_found_by_number_and_by_any_spelling_of_the_name():
    assert ansi_index(3) == 3
    assert ansi_index("red") == 1
    assert ansi_index("Bright Red") == ansi_index("bright-red") == ansi_index("bright_red") == 9
    assert [ansi_index(name) for name in ANSI_NAMES] == list(range(16))


@pytest.mark.parametrize("bad", [-1, 16, "reddish", ""])
def test_unknown_basic_colors_are_rejected(bad: int | str):
    with pytest.raises(ValueError):
        ansi_index(bad)
