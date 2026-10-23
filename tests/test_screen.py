import pytest

pytest.importorskip("pyte")

from termsnap import PLAIN, Indexed, Rgb, Style
from termsnap.screen import render

ESC = "\x1b"
VS16 = chr(0xFE0F)
ZWJ = chr(0x200D)


def screen(text: str, *, columns: int = 40, rows: int = 10):
    return render(text, columns=columns, rows=rows)


def texts(text: str, **size: int) -> list[str]:
    return [line.text for line in screen(text, **size)]


def test_plain_text_lines_without_trailing_blank_cells():
    assert texts("one\r\ntwo\r\n") == ["one", "two"]
    assert screen("") == ()


def test_basic_styles_and_palette_index_are_kept():
    (line,) = screen(f"{ESC}[1;31mred{ESC}[0m {ESC}[38;5;202mtone{ESC}[0m {ESC}[48;5;17mbg{ESC}[0m")
    styles = {span.text: span.style for span in line.spans}
    assert styles["red"] == Style(fg=Indexed(1), bold=True)
    assert styles["tone"] == Style(fg=Indexed(202))
    assert styles["bg"] == Style(bg=Indexed(17))
    assert styles[" "] == PLAIN


def test_bright_colors_map_to_indexes_8_to_15():
    (line,) = screen(f"{ESC}[91ma{ESC}[0m{ESC}[102mb")
    assert [span.style for span in line.spans] == [Style(fg=Indexed(9)), Style(bg=Indexed(10))]


def test_truecolor():
    (line,) = screen(f"{ESC}[38;2;10;20;30mx")
    assert line.spans[0].style.fg == Rgb(10, 20, 30)


def test_dim_is_kept_and_switched_off_by_22_and_0():
    (line,) = screen(f"{ESC}[2ma{ESC}[22mb{ESC}[2mc{ESC}[0md")
    assert [(span.text, span.style.dim) for span in line.spans] == [
        ("a", True),
        ("b", False),
        ("c", True),
        ("d", False),
    ]


def test_dim_inside_extended_color_arguments_is_not_mistaken_for_the_attribute():
    (line,) = screen(f"{ESC}[38;5;2mx")  # 2 здесь - номер цвета палитры
    assert line.spans[0].style == Style(fg=Indexed(2))
    (line,) = screen(f"{ESC}[38;2;2;2;2mx")
    assert not line.spans[0].style.dim


def test_inverse_underline_italic_strike():
    (line,) = screen(f"{ESC}[3;4;7;9mx")
    assert line.spans[0].style == Style(italic=True, underline=True, inverse=True, strike=True)


def test_background_of_trailing_blank_cells_is_kept():
    (line,) = screen(f"{ESC}[44m   ")
    assert line.text == "   "
    assert line.spans[0].style.bg == Indexed(4)


def test_absolute_positions_and_overwriting():
    text = f"{ESC}[2J{ESC}[1;1Hfirst{ESC}[3;5Hthird{ESC}[1;1H{ESC}[2Kfresh"
    assert texts(text) == ["fresh", "", "    third"]


def test_long_output_keeps_the_lines_that_scrolled_off_the_screen():
    result = texts("".join(f"line {number}\r\n" for number in range(1, 31)), rows=5)
    assert result == [f"line {number}" for number in range(1, 31)]


def test_long_lines_wrap_at_the_terminal_width():
    assert texts("a" * 25, columns=10) == ["a" * 10, "a" * 10, "a" * 5]


def test_cursor_up_redraws_the_last_lines():
    text = "one\r\ntwo\r\n" + f"{ESC}[2A{ESC}[2K" + "ONE\r\n" + f"{ESC}[2K" + "TWO\r\n"
    assert texts(text) == ["ONE", "TWO"]


def test_wide_characters_keep_columns_and_text():
    (line,) = screen("日本x")
    assert line.text == "日本x"
    assert line.width == 5


def test_zero_width_characters_do_not_drop_the_rest_of_the_line():
    warning = chr(0x26A0) + VS16
    family = chr(0x1F468) + ZWJ + chr(0x1F469)
    assert texts(f"a {warning} b {family} end") == [f"a {warning} b {family} end"]
    assert screen(f"a {warning} b")[0].width == 6  # эмодзи с селектором занимает две клетки


def test_combining_marks_join_the_previous_character():
    assert texts("e" + chr(0x301) + "x") == ["e" + chr(0x301) + "x"]


def test_window_and_mode_sequences_leave_no_trace():
    assert texts(f"{ESC}[1t{ESC}[c{ESC}[?1004h{ESC}[?25l{ESC}]0;title\x07text") == ["text"]
