"""
Чужие интерактивные программы в псевдотерминале: IPython получает ввод, историю по стрелке вверх и автодополнение по
Tab, страница руководства читается в pager (листание, поиск, выход), ``top`` и ``htop`` снимаются в заданный момент.
Состав программ и то, на каких системах они обязательны, - ``tests/registry.py``.

IPython берется из окружения проекта (группа ``external``, версия в ``uv.lock``, см. ``tests/pins.py``): сети нет, и
экран сверяется целиком. Выводы ``top`` и ``htop`` зависят от машины (процессы, нагрузка, часы), поэтому у них
проверяются заголовок, таблица и цвета, а не весь экран.
"""

import re

from helpers import texts
from picture import check_snapshot_picture

from termsnap import Capture, Indexed, Span, Style

# --- top и htop ---


def test_real_top_shows_its_header_and_the_process_table(pty_captures):
    capture = pty_captures("top")
    assert capture.stopped
    assert capture.lines[0].text.startswith(("top - ", "Processes:"))  # procps в Linux, BSD-top в macOS
    assert any(re.match(r"\s*PID\s+(USER|COMMAND)", text) for text in texts(capture))
    assert "\x1b" not in capture.text


def test_real_htop_shows_meters_and_the_process_table(pty_captures):
    capture = pty_captures("htop")
    assert capture.stopped
    assert any("Tasks:" in text for text in texts(capture))
    assert any("PID" in text and "Command" in text for text in texts(capture))
    assert len({s.style for line in capture.lines for s in line.spans}) > 5  # цветные счетчики и заголовок


# --- IPython: ввод, ответы, трассировка, история и автодополнение ---

GREEN, RED = Indexed(2), Indexed(1)

#: Номер в приглашении яркий: Linux и macOS передают его яркой зеленой (10), а ConPTY в Windows переписывает яркие цвета
#: как жирные обычные (2 и жирный). Для красного то же самое.
BRIGHT_OR_BOLD_GREEN = (Indexed(10), GREEN)
BRIGHT_OR_BOLD_RED = (Indexed(9), RED)

IPYTHON_SESSION = [
    "",  # перед первым приглашением (без заставки) IPython печатает пустую строку
    "In [1]: squares = [n ** 2 for n in range(6)]",
    "",
    "In [2]: squares",
    "Out[2]: [0, 1, 4, 9, 16, 25]",
    "",
    "In [3]: import math; math.pi",
    "Out[3]: 3.141592653589793",
    "",
    "In [4]: 1 / 0",
    "-" * 75,
    "ZeroDivisionError                         Traceback (most recent call last)",
    "Cell In[4], line 1",
    "----> 1 1 / 0",
    "",
    "ZeroDivisionError: division by zero",
    "",
    "In [5]: exit",
]


def test_ipython_repl_shows_the_whole_session(pty_captures):
    capture = pty_captures("ipython_session")
    assert capture.returncode == 0
    assert texts(capture) == IPYTHON_SESSION


def test_ipython_input_prompt_is_green_with_a_bold_number(pty_captures):
    prompt, number, colon, *_ = pty_captures("ipython_session").lines[1].spans  # "In [", "1", "]: " и код
    assert (prompt.text, prompt.style) == ("In [", Style(fg=GREEN))
    assert (number.text, colon.text, colon.style) == ("1", "]: ", Style(fg=GREEN))
    assert number.style.bold and number.style.fg in BRIGHT_OR_BOLD_GREEN


def test_ipython_input_is_highlighted_as_code(pty_captures):
    code = pty_captures("ipython_session").lines[1].spans[3:]  # после "In [", номера и "]: "
    assert next(span for span in code if span.text == "for").style.bold  # ключевое слово жирно
    assert len({span.style for span in code}) >= 4  # остальной код - другими цветами


def test_ipython_output_prompt_is_red_with_a_bold_number_and_the_value_is_plain(pty_captures):
    out, number, colon, value = pty_captures("ipython_session").lines[4].spans
    assert (out.text, out.style, colon.text, colon.style) == ("Out[", Style(fg=RED), "]: ", Style(fg=RED))
    assert number.style.bold and number.style.fg in BRIGHT_OR_BOLD_RED
    assert (value.text, value.style) == ("[0, 1, 4, 9, 16, 25]", Style())


def test_ipython_traceback_is_coloured(pty_captures):
    lines = pty_captures("ipython_session").lines
    assert lines[10].spans == (Span("-" * 75, Style(fg=RED)),)
    assert lines[11].spans == (
        Span("ZeroDivisionError", Style(fg=RED)),
        Span(" " * 25 + "Traceback (most recent call last)", Style()),
    )
    assert lines[13].spans == (  # строка, где случилась ошибка, выделена цветом фона
        Span("----> 1", Style(fg=GREEN)),
        Span(" ", Style()),
        Span("1 / 0", Style(fg=Indexed(0), bg=Indexed(3))),
    )
    assert lines[15].spans == (Span("ZeroDivisionError", Style(fg=RED)), Span(": division by zero", Style()))


def test_ipython_up_arrow_brings_back_the_previous_line(pty_captures):
    capture = pty_captures("ipython_history")
    assert capture.returncode == 0
    assert texts(capture) == [
        "",
        "In [1]: 6 * 7",
        "Out[1]: 42",
        "",
        "In [2]: 6 * 7",  # строку достала стрелка вверх, Enter ее повторил
        "Out[2]: 42",
        "",
        "In [3]: exit",
    ]


def test_ipython_tab_opens_the_completion_menu_and_the_snapshot_waits_for_it(pty_captures):
    capture = pty_captures("ipython_complete")
    assert capture.stopped
    lines = texts(capture)
    assert lines[:4] == ["", "In [1]: import math", "", "In [2]: math.s"]
    # меню под строкой ввода: имена из math, начинающиеся с "s", в две строки; скобки после функций ставит jedi (по
    # версии Python), поэтому сравниваются имена
    assert {word.removesuffix("()") for word in " ".join(lines[4:]).split()} == {"sin", "sinh", "sqrt", "sumprod"}
    assert all(line.startswith(" " * 15) for line in lines[4:])
    assert all(span.style.bg is not None for line in capture.lines[4:] for span in line.spans[1:])  # меню на фоне


# --- man: страница руководства в pager ---

SECTIONS = ["NAME", "SYNOPSIS", "DESCRIPTION", "OPTIONS", "EXAMPLES", "SEE ALSO"]


def headings(capture: Capture) -> list[str]:
    """
    Заголовки разделов: строки без отступа, набранные жирным (в человеческом виде pager показывает так заголовки).
    """
    return [
        line.text
        for line in capture.lines
        if line.text.isupper() and not line.text.startswith(" ") and line.spans[0].style.bold
    ]


def test_man_page_is_scrolled_by_page_down_and_headings_are_bold(pty_captures):
    capture = pty_captures("man_scroll")
    assert capture.stopped
    assert headings(capture) == SECTIONS  # OPTIONS и дальше видны только после Page Down: сначала экран кончался раньше
    assert "\x1b" not in capture.text
    assert "\b" not in capture.text  # жирный и подчеркнутый текст дошел стилями, а не символами возврата


def test_man_page_marks_arguments_with_underline_and_commands_with_bold(pty_captures):
    capture = pty_captures("man_scroll")
    # номер строки зависит от шапки страницы (groff и mandoc ее верстают по-разному), поэтому строку ищем по словам
    lines = [line for line in capture.lines if "--width" in line.text and "--color" in line.text]
    assert len(lines) == 1, texts(capture)
    # пробелы и скобки вокруг слов pager оставляет как есть, а groff разных версий подчеркивает и соседний пробел
    styled = [(span.text.strip(), span.style) for span in lines[0].spans if span.style != Style() and span.text.strip()]
    assert styled == [
        ("termsnap-demo", Style(bold=True)),
        ("--width", Style(bold=True)),
        ("N", Style(underline=True)),
        ("--color", Style(bold=True)),
        ("file", Style(underline=True)),
    ], lines[0].spans


def test_man_search_jumps_to_the_word_and_highlights_it(pty_captures):
    capture = pty_captures("man_search")
    assert capture.stopped
    (found,) = [line for line in capture.lines if "The word" in line.text]
    assert [(span.text.strip(), span.style.inverse) for span in found.spans if span.text.strip()] == [
        ("The word", False),
        ("needle", True),  # найденное слово pager показывает инверсией
        ("appears once, here, so that a search lands on", False),
    ]
    assert any(text == "...skipping..." for text in texts(capture))


def test_man_page_quits_with_q_and_a_zero_exit_code(pty_captures):
    capture = pty_captures("man_quit")
    assert not capture.stopped
    assert capture.returncode == 0


def test_man_page_text_is_the_one_in_the_file(pty_captures):
    # слова в строках pager расставляет по ширине (man-db растягивает пробелы), поэтому сверяются слова, а не пробелы
    words = " ".join(" ".join(texts(pty_captures("man_scroll"))).split())
    assert "termsnap-demo - a page that exists only to be read in a pager" in words
    assert "Paragraph four. Sphinx of black quartz, judge my vow" in words
    assert "Wrap lines at N columns." in words
    assert "The word needle appears once, here" in words


# --- PNG ---


def test_ipython_session_renders_to_a_picture_that_follows_its_screen(pty_captures, bundled_fonts):
    check_snapshot_picture(pty_captures("ipython_session").lines, bundled_fonts)
