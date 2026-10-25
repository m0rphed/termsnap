"""
Ширина текста в клетках терминала: иероглифы и эмодзи занимают две, комбинируемые знаки ни одной.
"""

import pytest
from helpers import VS16, ZWJ

from termsnap import parse
from termsnap.width import cluster_width, clusters, text_width

VS15 = chr(0xFE0E)  # селектор текстового начертания
ACUTE = chr(0x0301)  # комбинируемое ударение


def test_ordinary_text_is_split_into_single_characters():
    assert list(clusters("abc")) == ["a", "b", "c"]


@pytest.mark.parametrize(
    ("text", "width"),
    [("Привет, мир", 11), ("┌─┬─┐│█▒", 8), ("", 0)],
    ids=["cyrillic", "box drawing", "empty"],
)
def test_ordinary_text_is_one_cell_per_character(text: str, width: int):
    assert text_width(text) == width


@pytest.mark.parametrize("text", ["日本語", "中文", "Ｆｕｌｌ"])
def test_east_asian_wide_characters_take_two_cells(text):
    assert text_width(text) == 2 * len(text)


@pytest.mark.parametrize(("text", "width"), [("🚀", 2), ("✅", 2), ("🐍 ok", 5)])
def test_emoji_take_two_cells(text: str, width: int):
    assert text_width(text) == width


@pytest.mark.parametrize(
    ("suffix", "width"), [("", 1), (VS16, 2), (VS15, 1)], ids=["alone", "emoji selector", "text selector"]
)
def test_a_narrow_symbol_becomes_wide_only_with_the_emoji_selector(suffix: str, width: int):
    assert text_width(chr(0x26A0) + suffix) == width


def test_combining_marks_join_the_previous_character():
    assert list(clusters("e" + ACUTE + "x")) == ["e" + ACUTE, "x"]


def test_combining_marks_take_no_cell_of_their_own():
    assert (text_width("e" + ACUTE), cluster_width(ACUTE)) == (1, 0)


def test_zero_width_joiner_sequence_is_one_cluster():
    family = chr(0x1F468) + ZWJ + chr(0x1F469) + ZWJ + chr(0x1F467)
    assert list(clusters("a" + family + "b")) == ["a", family, "b"]


def test_zero_width_joiner_sequence_takes_two_cells():
    assert text_width(chr(0x1F468) + ZWJ + chr(0x1F469) + ZWJ + chr(0x1F467)) == 2


def test_parsed_wide_characters_keep_text_and_columns():
    (line,) = parse("日a")
    assert (line.text, line.width) == ("日a", 3)


@pytest.mark.parametrize(
    ("text", "expected"), [("日本\rab\n", "ab本"), ("ab\r日\n", "日")], ids=["narrow over wide", "wide over narrow"]
)
def test_carriage_return_overwrites_by_cells_not_characters(text: str, expected: str):
    assert [line.text for line in parse(text)] == [expected]
