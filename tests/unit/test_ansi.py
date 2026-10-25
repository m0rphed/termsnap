"""
Построчный разбор потока: SGR (цвета и атрибуты), возврат каретки, стирание, перемещения курсора по строкам.
"""

import pytest
from helpers import ESC

from termsnap import PLAIN, Indexed, Rgb, Span, Style, apply_sgr, parse


def spans(text: str) -> list[list[tuple[str, Style]]]:
    return [[(span.text, span.style) for span in line.spans] for line in parse(text)]


def parsed_texts(text: str) -> list[str]:
    return [line.text for line in parse(text)]


# --- строки ---


def test_plain_text_is_split_into_lines():
    assert parsed_texts("one\ntwo\n") == ["one", "two"]


def test_empty_output_has_no_lines():
    assert parse("") == ()


def test_a_blank_line_in_the_middle_is_kept():
    assert parsed_texts("a\n\nb") == ["a", "", "b"]


def test_output_without_final_newline_keeps_the_last_line():
    assert parsed_texts("a\nb") == ["a", "b"]


def test_windows_line_endings_are_the_same_as_unix_ones():
    assert parse("a\r\nb\r\n") == parse("a\nb\n")


# --- SGR: цвета и атрибуты ---


def test_basic_colors_and_reset():
    red = Style(fg=Indexed(1))
    assert spans(f"{ESC}[31mred{ESC}[0m plain") == [[("red", red), (" plain", PLAIN)]]


def test_empty_sgr_is_reset():
    assert spans(f"{ESC}[1mbold{ESC}[m x") == [[("bold", Style(bold=True)), (" x", PLAIN)]]


def test_bright_colors_use_indexes_8_to_15():
    assert (apply_sgr(PLAIN, "91").fg, apply_sgr(PLAIN, "107").bg) == (Indexed(9), Indexed(15))


def test_attributes_combine():
    style = apply_sgr(PLAIN, "1;3;4;9;7;2")
    assert style == Style(bold=True, dim=True, italic=True, underline=True, strike=True, inverse=True)


def test_attributes_switch_off_separately():
    style = apply_sgr(PLAIN, "1;3;4;9;7;2")
    assert apply_sgr(style, "22;23;24;27;29") == PLAIN


@pytest.mark.parametrize(
    ("clear", "left"),
    [("39", Style(bg=Indexed(2))), ("49", Style(fg=Indexed(1)))],
    ids=["default foreground", "default background"],
)
def test_default_color_codes_clear_only_their_own_color(clear: str, left: Style):
    assert apply_sgr(apply_sgr(PLAIN, "31;42"), clear) == left


@pytest.mark.parametrize("params", ["38;5;202", "38:5:202"])
def test_256_color_in_both_notations(params):
    assert apply_sgr(PLAIN, params).fg == Indexed(202)


@pytest.mark.parametrize("params", ["38;2;10;20;30", "38:2:10:20:30", "38:2::10:20:30"])
def test_truecolor_in_all_notations(params):
    assert apply_sgr(PLAIN, params).fg == Rgb(10, 20, 30)


@pytest.mark.parametrize(
    ("params", "expected"),
    [("48;5;17;1", Style(bg=Indexed(17), bold=True)), ("38;2;1;2;3;44", Style(fg=Rgb(1, 2, 3), bg=Indexed(4)))],
    ids=["palette then bold", "truecolor then background"],
)
def test_extended_color_does_not_swallow_the_following_codes(params: str, expected: Style):
    assert apply_sgr(PLAIN, params) == expected


@pytest.mark.parametrize("params", ["38;5", "38;2;1;2", "38;5;999", "38;2;1;2;300", "38;9;1", "38"])
def test_broken_extended_color_is_ignored(params):
    assert apply_sgr(Style(bold=True), params) == Style(bold=True)


def test_unknown_sgr_codes_are_ignored():
    assert apply_sgr(Style(bold=True), "5;8;53;150") == Style(bold=True)


def test_adjacent_cells_with_the_same_style_merge_into_one_span():
    line = parse(f"{ESC}[31ma{ESC}[31mb{ESC}[32mc")[0]
    assert line.spans == (Span("ab", Style(fg=Indexed(1))), Span("c", Style(fg=Indexed(2))))


def test_style_carries_over_the_end_of_a_line():
    assert spans(f"{ESC}[32ma\nb") == [[("a", Style(fg=Indexed(2)))], [("b", Style(fg=Indexed(2)))]]


def test_non_ascii_text_is_kept():
    assert parsed_texts(f"{ESC}[36mПривет, мир{ESC}[0m") == ["Привет, мир"]


# --- возврат каретки, стирание, перемещения вдоль строки ---


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("progress 10%\rprogress 99%\n", "progress 99%"),
        ("abcdef\rxy\n", "xycdef"),
        (f"loading...\r{ESC}[Kdone\n", "done"),
    ],
    ids=["longer replaces shorter", "shorter overwrites the start", "erase to end of line"],
)
def test_carriage_return_overwrites_the_line_from_the_start(text: str, expected: str):
    assert parsed_texts(text) == [expected]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (f"abcdef\b\b\b{ESC}[0K", "abc"),
        (f"abcdef\b\b\b{ESC}[1K", "    ef"),
        (f"abcdef{ESC}[2Kx", "      x"),
    ],
    ids=["to the end", "to the start", "whole line"],
)
def test_erase_in_line_modes(text: str, expected: str):
    assert parsed_texts(text) == [expected]


@pytest.mark.parametrize(
    ("text", "expected"),
    [(f"abc{ESC}[2Dx{ESC}[3Gy", "axy"), (f"a{ESC}[3Cb", "a   b")],
    ids=["left and absolute column", "right"],
)
def test_cursor_moves_along_the_line(text: str, expected: str):
    assert parsed_texts(text) == [expected]


@pytest.mark.parametrize(
    ("text", "expected"), [("ab\bc", "ac"), ("a\tb", "a       b")], ids=["backspace", "tab to the next stop"]
)
def test_backspace_and_tab(text: str, expected: str):
    assert parsed_texts(text) == [expected]


@pytest.mark.parametrize(
    ("text", "expected"),
    [(f"{ESC}]0;title\x07text", "text"), (f"{ESC}]8;;http://x{ESC}\\link{ESC}]8;;{ESC}\\", "link")],
    ids=["window title", "hyperlink"],
)
def test_title_and_hyperlink_sequences_are_dropped(text: str, expected: str):
    assert parsed_texts(text) == [expected]


def test_private_modes_and_vertical_moves_are_dropped_without_changing_style():
    text = f"{ESC}[?25l{ESC}[>4;2m{ESC}[2Aok{ESC}[?25h"
    assert spans(text) == [[("ok", PLAIN)]]


@pytest.mark.parametrize(
    ("text", "expected"),
    [("a\x07b\x00c", "abc"), (f"a{ESC}", "a"), (f"a{ESC}[", "a")],
    ids=["bell and nul", "lone escape", "unfinished sequence"],
)
def test_stray_control_characters_are_dropped(text: str, expected: str):
    assert parsed_texts(text) == [expected]


# --- перемещение курсора по экрану и стирание экрана ---


def test_cursor_up_overwrites_earlier_lines():
    assert parsed_texts("one\ntwo\n" + ESC + "[2A\rONE\nTWO\n") == ["ONE", "TWO"]


def test_redrawing_the_last_lines_leaves_only_the_final_frame():
    frame = ESC + "[2K" + "{}\n"
    first = frame.format("progress 1") + frame.format("other 1")
    second = ESC + "[2A" + frame.format("progress 2") + frame.format("other 2")
    assert parsed_texts("start\n" + first + second) == ["start", "progress 2", "other 2"]


def test_cursor_down_extends_the_screen():
    assert parsed_texts("a" + ESC + "[2Bb") == ["a", "", " b"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [("abc\ndef" + ESC + "[1Fx", ["xbc", "def"]), ("abc" + ESC + "[1Ex", ["abc", "x"])],
    ids=["previous line", "next line"],
)
def test_next_and_previous_line_move_to_the_line_start(text: str, expected: list[str]):
    assert parsed_texts(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [("a\nb\nc\n" + ESC + "[2A" + ESC + "[J", ["a"]), ("a\nb\n" + ESC + "[2J" + "new", ["new"])],
    ids=["below the cursor", "whole screen"],
)
def test_erase_below_and_whole_screen(text: str, expected: list[str]):
    assert parsed_texts(text) == expected


def test_erase_above_blanks_earlier_lines():
    assert parsed_texts("a\nb\nc" + ESC + "[1J") == ["", "", " "]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12345\nabcde\n" + ESC + "[1;3Hx" + ESC + "[2;2Hy", ["12x45", "aycde"]),
        ("abc" + ESC + "[Hx", ["xbc"]),
    ],
    ids=["row and column", "home"],
)
def test_absolute_position_counts_from_the_first_line(text: str, expected: list[str]):
    assert parsed_texts(text) == expected
