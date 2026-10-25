"""
Палитра терминала и запись цвета: расчет цветов 16-255 по правилам xterm, имена базовых цветов, цвет в любой записи.
"""

import pytest

from termsnap import ANSI_NAMES, Rgb, parse_color
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
        (202, (255, 95, 0)),
        (208, (255, 135, 0)),  # оранжевый
        (231, (255, 255, 255)),  # конец куба: белый
        (232, (8, 8, 8)),  # начало серых ступеней
        (243, (118, 118, 118)),
        (255, (238, 238, 238)),
    ],
)
def test_extended_palette_follows_xterm(index: int, expected: tuple[int, int, int]):
    assert extended_color(index).channels == expected


# --- имена базовых цветов ---


def test_names_are_the_sixteen_basic_colors_in_palette_order():
    assert (
        *("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"),
        *("bright_black", "bright_red", "bright_green", "bright_yellow"),
        *("bright_blue", "bright_magenta", "bright_cyan", "bright_white"),
    ) == ANSI_NAMES


def test_basic_color_is_found_by_its_number():
    assert ansi_index(3) == 3


def test_basic_color_is_found_by_name():
    assert ansi_index("red") == 1


@pytest.mark.parametrize("spelling", ["Bright Red", "bright-red", "bright_red", " BRIGHT_RED "])
def test_any_spelling_of_a_name_finds_the_same_color(spelling: str):
    assert ansi_index(spelling) == 9


def test_every_name_finds_its_own_number():
    assert [ansi_index(name) for name in ANSI_NAMES] == list(range(16))


@pytest.mark.parametrize("bad", [-1, 16, "reddish", ""])
def test_unknown_basic_colors_are_rejected(bad: int | str):
    with pytest.raises(ValueError):
        ansi_index(bad)


# --- цвет в любой записи ---


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("#ff2e97", Rgb(255, 46, 151)),
        ("FF2E97", Rgb(255, 46, 151)),
        ("  #f00 ", Rgb(255, 0, 0)),
        ("abc", Rgb(0xAA, 0xBB, 0xCC)),
        ((1, 2, 3), Rgb(1, 2, 3)),
        (Rgb(9, 8, 7), Rgb(9, 8, 7)),
    ],
    ids=["hash", "no hash, capitals", "short, spaces", "short, no hash", "tuple", "Rgb"],
)
def test_colors_can_be_written_in_several_ways(value, expected: Rgb):
    assert parse_color(value) == expected


@pytest.mark.parametrize("bad", ["", "#12", "#12345", "#gggggg", "red"])
def test_bad_color_strings_are_rejected(bad: str):
    with pytest.raises(ValueError, match="#rrggbb"):
        parse_color(bad)


def test_color_of_a_wrong_kind_is_rejected():
    with pytest.raises(TypeError):
        parse_color(15)  # pyright: ignore[reportArgumentType]


def test_color_channel_out_of_range_is_rejected():
    with pytest.raises(ValueError, match="от 0 до 255"):
        parse_color((0, 0, 300))
