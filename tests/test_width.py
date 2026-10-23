import pytest

from termsnap import Line, Span, parse
from termsnap.width import cluster_width, clusters, text_width

VS16 = chr(0xFE0F)  # селектор эмодзи-начертания
VS15 = chr(0xFE0E)  # селектор текстового начертания
ZWJ = chr(0x200D)  # соединитель нулевой ширины
ACUTE = chr(0x0301)  # комбинируемое ударение


def test_ordinary_text_is_one_cell_per_character():
    assert list(clusters("abc")) == ["a", "b", "c"]
    assert text_width("Привет, мир") == 11
    assert text_width("┌─┬─┐│█▒") == 8
    assert text_width("") == 0


@pytest.mark.parametrize("text", ["日本語", "中文", "Ｆｕｌｌ"])
def test_east_asian_wide_characters_take_two_cells(text):
    assert text_width(text) == 2 * len(text)


def test_emoji_take_two_cells():
    assert text_width("🚀") == 2
    assert text_width("✅") == 2
    assert text_width("🐍 ok") == 5


def test_narrow_symbol_becomes_wide_with_emoji_selector_and_stays_narrow_with_text_selector():
    warning = chr(0x26A0)
    assert text_width(warning) == 1
    assert text_width(warning + VS16) == 2
    assert text_width(warning + VS15) == 1


def test_combining_marks_join_the_previous_character():
    assert list(clusters("e" + ACUTE + "x")) == ["e" + ACUTE, "x"]
    assert text_width("e" + ACUTE) == 1
    assert cluster_width(ACUTE) == 0


def test_zero_width_joiner_sequence_is_one_wide_cluster():
    family = chr(0x1F468) + ZWJ + chr(0x1F469) + ZWJ + chr(0x1F467)
    assert list(clusters("a" + family + "b")) == ["a", family, "b"]
    assert text_width(family) == 2


def test_span_and_line_report_width_in_cells():
    line = Line((Span("日本"), Span("ab"), Span("🚀")))
    assert line.width == 4 + 2 + 2
    assert line.text == "日本ab🚀"


def test_parsed_wide_characters_keep_text_and_columns():
    (line,) = parse("日a")
    assert line.text == "日a"
    assert line.width == 3


def test_carriage_return_overwrites_by_cells_not_characters():
    assert [line.text for line in parse("日本\rab\n")] == ["ab本"]
    assert [line.text for line in parse("ab\r日\n")] == ["日"]
