"""
Модель вывода: цвета, стиль, фрагменты, строки.
"""

import dataclasses

import pytest

from termsnap import Indexed, Line, Rgb, Span, Style


@pytest.mark.parametrize(
    "make", [lambda: Indexed(256), lambda: Indexed(-1), lambda: Rgb(0, 256, 0), lambda: Rgb(-1, 0, 0)]
)
def test_color_numbers_outside_zero_to_255_are_rejected(make):
    with pytest.raises(ValueError, match="от 0 до 255"):
        make()


@pytest.mark.parametrize("number", [0, 15, 16, 255])
def test_palette_numbers_inside_the_range_are_accepted(number: int):
    assert Indexed(number).index == number


@pytest.mark.parametrize(
    ("color", "text"),
    [(Rgb(255, 46, 151), "#ff2e97"), (Rgb(0, 0, 0), "#000000"), (Rgb(0xCD, 0x31, 0x31), "#cd3131")],
)
def test_rgb_is_written_as_lowercase_hex_with_a_hash(color: Rgb, text: str):
    assert color.hex == text


@pytest.mark.parametrize("text", ["cd3131", "#CD3131", "#cd3131"])
def test_hex_colors_are_read_with_or_without_the_hash_in_any_case(text: str):
    assert Rgb.from_hex(text) == Rgb(0xCD, 0x31, 0x31)


@pytest.mark.parametrize("bad", ["", "fff", "12345", "1234567", "gggggg"])
def test_bad_hex_colors_are_rejected(bad: str):
    with pytest.raises(ValueError):
        Rgb.from_hex(bad)


def test_rgb_channels_come_in_the_order_red_green_blue():
    assert Rgb(1, 2, 3).channels == (1, 2, 3)


def test_line_text_joins_the_text_of_its_spans():
    assert Line((Span("ab"), Span("cd", Style(bold=True)))).text == "abcd"


def test_line_width_counts_terminal_cells_and_not_characters():
    # одна клетка на обычный символ, две на иероглиф (подробности - в test_width)
    assert Line((Span("ab"), Span("日", Style(bold=True)))).width == 4


def test_empty_line_has_no_text_and_no_width():
    assert (Line(()).text, Line(()).width) == ("", 0)


@pytest.mark.parametrize("value", [Indexed(1), Rgb(1, 2, 3), Style(bold=True), Span("x"), Line((Span("x"),))])
def test_model_values_are_immutable(value):
    # неизменяемость позволяет безопасно делить значения между кэшем шрифтов, словарями стилей и строками разбора
    field = dataclasses.fields(value)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(value, field, None)
