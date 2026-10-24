import pytest

from termsnap import PLAIN, Indexed, Rgb, Span, Style, apply_sgr, parse

ESC = "\x1b"


def spans(text: str) -> list[list[tuple[str, Style]]]:
    return [[(span.text, span.style) for span in line.spans] for line in parse(text)]


def test_plain_text_is_split_into_lines():
    assert [line.text for line in parse("one\ntwo\n")] == ["one", "two"]


def test_empty_output_has_no_lines_and_a_blank_line_is_kept():
    assert parse("") == ()
    assert [line.text for line in parse("a\n\nb")] == ["a", "", "b"]


def test_output_without_final_newline_keeps_the_last_line():
    assert [line.text for line in parse("a\nb")] == ["a", "b"]


def test_windows_line_endings_are_the_same_as_unix_ones():
    assert parse("a\r\nb\r\n") == parse("a\nb\n")


def test_basic_colors_and_reset():
    red = Style(fg=Indexed(1))
    assert spans(f"{ESC}[31mred{ESC}[0m plain") == [[("red", red), (" plain", PLAIN)]]


def test_empty_sgr_is_reset():
    assert spans(f"{ESC}[1mbold{ESC}[m x") == [[("bold", Style(bold=True)), (" x", PLAIN)]]


def test_bright_colors_use_indexes_8_to_15():
    assert apply_sgr(PLAIN, "91").fg == Indexed(9)
    assert apply_sgr(PLAIN, "107").bg == Indexed(15)


def test_attributes_combine_and_switch_off_separately():
    style = apply_sgr(PLAIN, "1;3;4;9;7;2")
    assert style == Style(bold=True, dim=True, italic=True, underline=True, strike=True, inverse=True)
    assert apply_sgr(style, "22;23;24;27;29") == PLAIN


def test_default_color_codes_clear_only_their_own_color():
    style = apply_sgr(PLAIN, "31;42")
    assert apply_sgr(style, "39") == Style(bg=Indexed(2))
    assert apply_sgr(style, "49") == Style(fg=Indexed(1))


@pytest.mark.parametrize("params", ["38;5;202", "38:5:202"])
def test_256_color_in_both_notations(params):
    assert apply_sgr(PLAIN, params).fg == Indexed(202)


@pytest.mark.parametrize("params", ["38;2;10;20;30", "38:2:10:20:30", "38:2::10:20:30"])
def test_truecolor_in_all_notations(params):
    assert apply_sgr(PLAIN, params).fg == Rgb(10, 20, 30)


def test_extended_color_does_not_swallow_the_following_codes():
    assert apply_sgr(PLAIN, "48;5;17;1") == Style(bg=Indexed(17), bold=True)
    assert apply_sgr(PLAIN, "38;2;1;2;3;44") == Style(fg=Rgb(1, 2, 3), bg=Indexed(4))


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


def test_carriage_return_overwrites_the_line_from_the_start():
    assert [line.text for line in parse("progress 10%\rprogress 99%\n")] == ["progress 99%"]
    assert [line.text for line in parse("abcdef\rxy\n")] == ["xycdef"]


def test_erase_to_end_of_line_after_carriage_return():
    assert [line.text for line in parse(f"loading...\r{ESC}[Kdone\n")] == ["done"]


def test_erase_modes():
    assert [line.text for line in parse(f"abcdef\b\b\b{ESC}[0K")] == ["abc"]
    assert [line.text for line in parse(f"abcdef\b\b\b{ESC}[1K")] == ["    ef"]
    assert [line.text for line in parse(f"abcdef{ESC}[2Kx")] == ["      x"]


def test_cursor_moves_along_the_line():
    assert [line.text for line in parse(f"abc{ESC}[2Dx{ESC}[3Gy")] == ["axy"]
    assert [line.text for line in parse(f"a{ESC}[3Cb")] == ["a   b"]


def test_backspace_and_tab():
    assert [line.text for line in parse("ab\bc")] == ["ac"]
    assert [line.text for line in parse("a\tb")] == ["a       b"]


def test_title_and_hyperlink_sequences_are_dropped():
    assert [line.text for line in parse(f"{ESC}]0;title\x07text")] == ["text"]
    assert [line.text for line in parse(f"{ESC}]8;;http://x{ESC}\\link{ESC}]8;;{ESC}\\")] == ["link"]


def test_private_modes_and_vertical_moves_are_dropped_without_changing_style():
    text = f"{ESC}[?25l{ESC}[>4;2m{ESC}[2Aok{ESC}[?25h"
    assert spans(text) == [[("ok", PLAIN)]]


def test_stray_control_characters_are_dropped():
    assert [line.text for line in parse("a\x07b\x00c")] == ["abc"]
    assert [line.text for line in parse(f"a{ESC}")] == ["a"]
    assert [line.text for line in parse(f"a{ESC}[")] == ["a"]


def test_non_ascii_text_is_kept():
    assert [line.text for line in parse(f"{ESC}[36mПривет, мир{ESC}[0m")] == ["Привет, мир"]


# - перемещение курсора и стирание экрана -
def texts(text: str) -> list[str]:
    return [line.text for line in parse(text)]


def test_cursor_up_overwrites_earlier_lines():
    assert texts("one\ntwo\n" + ESC + "[2A\rONE\nTWO\n") == ["ONE", "TWO"]


def test_redrawing_the_last_lines_leaves_only_the_final_frame():
    frame = ESC + "[2K" + "{}\n"
    first = frame.format("progress 1") + frame.format("other 1")
    second = ESC + "[2A" + frame.format("progress 2") + frame.format("other 2")
    assert texts("start\n" + first + second) == ["start", "progress 2", "other 2"]


def test_cursor_down_extends_the_screen():
    assert texts("a" + ESC + "[2Bb") == ["a", "", " b"]


def test_next_and_previous_line_move_to_the_line_start():
    assert texts("abc\ndef" + ESC + "[1Fx") == ["xbc", "def"]
    assert texts("abc" + ESC + "[1Ex") == ["abc", "x"]


def test_erase_below_and_whole_screen():
    assert texts("a\nb\nc\n" + ESC + "[2A" + ESC + "[J") == ["a"]
    assert texts("a\nb\n" + ESC + "[2J" + "new") == ["new"]


def test_erase_above_blanks_earlier_lines():
    assert texts("a\nb\nc" + ESC + "[1J") == ["", "", " "]


def test_absolute_position_counts_from_the_first_line():
    assert texts("12345\nabcde\n" + ESC + "[1;3Hx" + ESC + "[2;2Hy") == ["12x45", "aycde"]
    assert texts("abc" + ESC + "[Hx") == ["xbc"]
