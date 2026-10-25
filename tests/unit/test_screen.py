"""
Эмулятор экрана: поток терминала превращается в строки со стилями так, как его показал бы настоящий терминал.
"""

import pytest
from helpers import ESC, VS16, ZWJ
from support import require_module

require_module("pyte")

from termsnap import PLAIN, Indexed, Rgb, Style
from termsnap.screen import render


def screen(text: str, *, columns: int = 40, rows: int = 10, visible_only: bool = False):
    return render(text, columns=columns, rows=rows, visible_only=visible_only)


def screen_texts(text: str, **options: int | bool) -> list[str]:
    return [line.text for line in screen(text, **options)]


def only_line(text: str):
    (line,) = screen(text)
    return line


def test_plain_text_lines_have_no_trailing_blank_cells():
    assert screen_texts("one\r\ntwo\r\n") == ["one", "two"]


def test_empty_output_has_no_lines():
    assert screen("") == ()


@pytest.mark.parametrize(
    ("sgr", "expected"),
    [
        ("1;31", Style(fg=Indexed(1), bold=True)),
        ("38;5;202", Style(fg=Indexed(202))),
        ("48;5;17", Style(bg=Indexed(17))),
        ("38;2;10;20;30", Style(fg=Rgb(10, 20, 30))),
        ("3;4;7;9", Style(italic=True, underline=True, inverse=True, strike=True)),
    ],
    ids=["bold red", "palette foreground", "palette background", "truecolor", "italic underline inverse strike"],
)
def test_styles_and_colours_are_kept_as_the_program_wrote_them(sgr: str, expected: Style):
    assert only_line(f"{ESC}[{sgr}mx").spans[0].style == expected


def test_unstyled_text_between_styled_words_is_plain():
    line = only_line(f"{ESC}[31mred{ESC}[0m plain")
    assert [(span.text, span.style) for span in line.spans] == [("red", Style(fg=Indexed(1))), (" plain", PLAIN)]


def test_bright_colors_map_to_indexes_8_to_15():
    line = only_line(f"{ESC}[91ma{ESC}[0m{ESC}[102mb")
    assert [span.style for span in line.spans] == [Style(fg=Indexed(9)), Style(bg=Indexed(10))]


def test_dim_is_kept_and_switched_off_by_22_and_0():
    line = only_line(f"{ESC}[2ma{ESC}[22mb{ESC}[2mc{ESC}[0md")
    assert [(span.text, span.style.dim) for span in line.spans] == [
        ("a", True),
        ("b", False),
        ("c", True),
        ("d", False),
    ]


@pytest.mark.parametrize(
    ("sgr", "expected"),
    [("38;5;2", Style(fg=Indexed(2))), ("38;2;2;2;2", Style(fg=Rgb(2, 2, 2)))],
    ids=["palette number", "truecolor channels"],
)
def test_the_digit_2_inside_extended_colour_arguments_is_not_mistaken_for_dim(sgr: str, expected: Style):
    assert only_line(f"{ESC}[{sgr}mx").spans[0].style == expected


def test_background_of_trailing_blank_cells_is_kept():
    line = only_line(f"{ESC}[44m   ")
    assert (line.text, line.spans[0].style.bg) == ("   ", Indexed(4))


def test_absolute_positions_and_overwriting():
    text = f"{ESC}[2J{ESC}[1;1Hfirst{ESC}[3;5Hthird{ESC}[1;1H{ESC}[2Kfresh"
    assert screen_texts(text) == ["fresh", "", "    third"]


def test_long_output_keeps_the_lines_that_scrolled_off_the_screen():
    result = screen_texts("".join(f"line {number}\r\n" for number in range(1, 31)), rows=5)
    assert result == [f"line {number}" for number in range(1, 31)]


def test_long_lines_wrap_at_the_terminal_width():
    assert screen_texts("a" * 25, columns=10) == ["a" * 10, "a" * 10, "a" * 5]


def test_cursor_up_redraws_the_last_lines():
    text = "one\r\ntwo\r\n" + f"{ESC}[2A{ESC}[2K" + "ONE\r\n" + f"{ESC}[2K" + "TWO\r\n"
    assert screen_texts(text) == ["ONE", "TWO"]


def test_wide_characters_keep_their_text():
    assert only_line("日本x").text == "日本x"


def test_wide_characters_take_two_columns_each():
    assert only_line("日本x").width == 5


def test_zero_width_characters_do_not_drop_the_rest_of_the_line():
    warning = chr(0x26A0) + VS16
    family = chr(0x1F468) + ZWJ + chr(0x1F469)
    assert screen_texts(f"a {warning} b {family} end") == [f"a {warning} b {family} end"]


def test_emoji_with_a_selector_takes_two_cells():
    assert only_line(f"a {chr(0x26A0) + VS16} b").width == 6


def test_combining_marks_join_the_previous_character():
    assert screen_texts("e" + chr(0x301) + "x") == ["e" + chr(0x301) + "x"]


def test_window_and_mode_sequences_leave_no_trace():
    assert screen_texts(f"{ESC}[1t{ESC}[c{ESC}[?1004h{ESC}[?25l{ESC}]0;title\x07text") == ["text"]


# --- только видимая часть экрана ---


def numbered(count: int) -> str:
    return "".join(f"line {number}\r\n" for number in range(1, count + 1))


def test_visible_only_drops_the_lines_that_scrolled_off_the_screen():
    assert screen_texts(numbered(30), rows=5, visible_only=True) == [f"line {number}" for number in range(27, 31)]


def test_by_default_nothing_scrolled_off_the_screen_is_lost():
    assert len(screen_texts(numbered(30), rows=5)) == 30


def test_visible_only_changes_nothing_when_everything_fits_on_the_screen():
    assert screen_texts(numbered(3), rows=10, visible_only=True) == screen_texts(numbered(3), rows=10)


def test_visible_only_keeps_styles_and_absolute_positions():
    text = numbered(20) + f"{ESC}[1;1H{ESC}[2K{ESC}[1;31mtop{ESC}[0m"
    lines = screen(text, rows=5, visible_only=True)
    assert (lines[0].text, lines[0].spans[0].style) == ("top", Style(fg=Indexed(1), bold=True))
