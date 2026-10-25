"""
Запуск в псевдотерминале: программа видит терминал, вывод разбирается эмулятором экрана.
"""

import os
import signal
import sys

import pytest
from helpers import ESC, VS16, python, texts
from picture import check_snapshot_picture
from registry import PTY_REGISTRY, REGISTRY, Program
from styles import styles_by_text
from support import require_pty_extras, skip_on

require_pty_extras()

from termsnap import Capture, Indexed, PtyBackend, Request, Rgb, RunTimeout, Snapshot, Span, Style, run

PTY = PtyBackend()
PIPE_PROGRAMS = [program for program in REGISTRY if not program.external]


def colours(capture: Capture) -> set:
    return {span.style.fg for line in capture.lines for span in line.spans if span.style.fg is not None}


def printing(text: str) -> list[str]:
    """
    Команда, которая печатает ``text`` как есть (с управляющими символами).
    """
    return python(f"print({text!r})")


def test_program_sees_a_terminal_of_the_requested_size():
    code = "import sys, os; print(sys.stdout.isatty(), sys.stdin.isatty(), os.get_terminal_size())"
    capture = run(python(code), backend=PTY, columns=80, rows=24)
    assert capture.text == "True True os.terminal_size(columns=80, lines=24)"


def test_exit_code_and_output_of_a_failing_program_are_both_reported():
    capture = run(python("import sys; print('boom'); sys.exit(3)"), backend=PTY)
    assert capture.returncode == 3
    assert capture.text == "boom"


def test_stdout_and_stderr_share_the_terminal_in_order():
    code = "import sys; print('a', flush=True); print('b', file=sys.stderr, flush=True); print('c', flush=True)"
    assert run(python(code), backend=PTY).text == "a\nb\nc"


def test_raw_terminal_stream_is_kept():
    assert f"{ESC}[1mx".encode() in run(printing(f"{ESC}[1mx"), backend=PTY).output


@pytest.mark.parametrize(
    ("sgr", "expected"),
    [
        ("2", Style(dim=True)),
        ("38;5;202", Style(fg=Indexed(202))),
        ("38;2;1;2;3", Style(fg=Rgb(1, 2, 3))),
    ],
    ids=["dim", "palette", "truecolor"],
)
def test_dim_palette_and_truecolor_survive_the_pty(sgr: str, expected: Style):
    (line,) = run(printing(f"{ESC}[{sgr}mword{ESC}[0m"), backend=PTY).lines
    assert line.spans == (Span("word", expected),)


def test_timeout_stops_the_program_and_keeps_its_output():
    code = "import time; print('started', flush=True); time.sleep(60)"
    with pytest.raises(RunTimeout) as caught:
        run(python(code), backend=PTY, timeout=1.5)
    assert b"started" in caught.value.output


def test_missing_program_is_reported():
    with pytest.raises(FileNotFoundError):
        run(["no-such-program-termsnap"], backend=PTY)


def test_color_can_be_turned_off():
    capture = run(PTY_REGISTRY[0].argv, backend=PTY, color=False)
    assert capture.lines
    assert not colours(capture)
    assert not any(span.style.bg is not None for line in capture.lines for span in line.spans)


# --- rich без настроек в терминале ---

RICH_NATIVE = [
    "терминал: True, цвета: truecolor, ширина: 100",  # termsnap объявляет терминал с 24-битным цветом шириной 100
    "          Результаты           ",
    "┏━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┓",
    "┃ Тест   ┃ Статус  ┃ Время, с ┃",
    "┡━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━┩",
    "│ парсер │  ✅ ok  │     0.12 │",
    "│ рендер │ ❌ fail │     1.40 │",
    f"│ шрифты │ ⚠{VS16} warn │     0.07 │",  # ⚠ с селектором эмодзи занимает две клетки, как ✅ и ❌
    "└────────┴─────────┴──────────┘",
    "╭" + "─" * 98 + "╮",
    "│ ВНИМАНИЕ Проверьте настройки" + " " * 69 + "│",
    "╰" + "─" * 98 + "╯",
]


def test_plain_rich_console_needs_no_workarounds_in_a_pty(pty_captures):
    # rich без настроек сам видит терминал: цвета, ширину и эмодзи определяет по нему
    assert texts(pty_captures("rich_native")) == RICH_NATIVE


def test_rich_table_and_panel_in_a_pty_are_even(pty_captures):
    # эмодзи в таблице занимают две клетки, поэтому все строки таблицы одной ширины, а панель - во всю ширину терминала
    lines = pty_captures("rich_native").lines
    assert {line.width for line in lines[2:9]} == {31}
    assert {line.width for line in lines[9:]} == {100}


def test_plain_rich_console_colours_in_a_pty(pty_captures):
    assert (
        styles_by_text(pty_captures("rich_native")).items()
        >= {
            "Тест": Style(bold=True),
            "✅ ok": Style(fg=Indexed(2)),
            "❌ fail": Style(fg=Indexed(1)),
            "0.12": Style(dim=True),
            "ВНИМАНИЕ": Style(fg=Indexed(1), bold=True),
        }.items()
    )


# --- программа рисует весь экран абсолютными позициями курсора ---

FULL_SCREEN = [
    " top - 12:00:00 up 3 days, 2 users ",
    "",
    "CPU  |||||||| 40%",
    "MEM  |||||||||||| 60%",
    "",
    "         Привет, терминал",
    "",
    "новая строка",  # на этом месте была строка длиннее: ее стерли перед записью новой
    *[""] * 21,  # строки 9-29 не тронуты
    " q: выход ",
]


def test_full_screen_program_leaves_exactly_the_drawn_screen(pty_captures):
    # разбор потока по строкам такой вывод не прочитал бы
    assert texts(pty_captures("full_screen")) == FULL_SCREEN


def test_full_screen_program_keeps_the_styles_of_what_it_drew(pty_captures):
    lines = pty_captures("full_screen").lines
    assert lines[0].spans == (Span(" top - 12:00:00 up 3 days, 2 users ", Style(inverse=True)),)  # строка состояния
    assert lines[2].spans == (Span("CPU  "), Span("||||||||", Style(fg=Indexed(2))), Span(" 40%"))  # зеленая шкала
    assert lines[3].spans == (Span("MEM  "), Span("||||||||||||", Style(fg=Indexed(3))), Span(" 60%"))  # желтая
    assert lines[5].spans == (Span("         "), Span("Привет, терминал", Style(fg=Indexed(6), bold=True)))
    assert lines[29].spans == (Span(" q: выход ", Style(fg=Indexed(15), bg=Indexed(4))),)  # белое на синем


# --- вывод длиннее экрана: 120 строк в экране из 30, верхние уходят за край, но остаются в результате ---


def test_output_longer_than_the_screen_keeps_every_line(pty_captures):
    lines = pty_captures("long_output").lines
    assert len(lines) == 120
    assert (lines[0].text.rstrip(), lines[-1].text) == ("строка 001: x", "строка 120: x")


def test_scrolled_off_lines_keep_their_text(pty_captures):
    lines = pty_captures("long_output").lines
    assert [line.text.rstrip() for line in lines[:8]] == [
        "строка 001: x",
        "строка 002: xx",
        "строка 003: xxx",
        "строка 004: xxxx",
        "строка 005: xxxxx",
        "строка 006: xxxxxx",
        "строка 007:",  # число икс - остаток от деления на 7
        "строка 008: x",
    ]


def test_scrolled_off_lines_keep_their_colours(pty_captures):
    lines = pty_captures("long_output").lines
    # цвет меняется каждые десять строк: 1-9 красный, 10-19 зеленый, затем дальше по кругу из шести цветов
    assert [lines[number - 1].spans[0].style.fg for number in (1, 9, 10, 19, 20, 60, 120)] == [
        Indexed(index) for index in (1, 1, 2, 2, 3, 1, 1)
    ]


# --- программы проекта в канале и в псевдотерминале ---


@pytest.mark.parametrize("item", PIPE_PROGRAMS, ids=lambda item: item.name)
def test_project_programs_run_in_a_pty_and_leave_no_escape_sequences(item: Program, pty_captures):
    capture = pty_captures(item.name)
    assert (capture.returncode != 0) is item.expect_failure, item.name
    assert capture.lines, item.name
    assert "\x1b" not in capture.text, item.name


@pytest.mark.parametrize(
    "name",
    ["rich_table", "rich_panel_tree", "rich_syntax", "rich_traceback", "rich_progress", "rich_live"],
)
def test_pty_and_pipe_agree_on_programs_that_do_not_depend_on_the_terminal(name: str, pty_captures, captures):
    assert [text.rstrip() for text in texts(pty_captures(name))] == [text.rstrip() for text in texts(captures(name))]


def test_pty_and_pipe_use_the_same_colours_for_rich_table(pty_captures, captures):
    assert colours(pty_captures("rich_table")) == colours(captures("rich_table"))


def test_rich_misc_keeps_emoji_with_variation_selector(pty_captures):
    last_line = pty_captures("rich_misc").lines[-1].text
    assert last_line == f"Эмодзи: 🚀 ✅ ❌ ⚠{VS16} 🐍  Иероглифы: 日本語 中文  Рамки: ┌─┬─┐│ │ │└─┴─┘"


@pytest.mark.parametrize("name", [p.name for p in PTY_REGISTRY])
def test_pty_programs_render_to_a_picture_that_follows_their_screen(name: str, pty_captures, bundled_fonts):
    check_snapshot_picture(pty_captures(name).lines, bundled_fonts)


# --- видимая часть экрана и прокрутка ---

SCROLLING = "for n in range(1, 51): print('line', n)"


def test_scrolled_off_lines_are_kept_by_default():
    lines = run(python(SCROLLING), backend=PTY, rows=10).lines
    assert (len(lines), lines[0].text, lines[-1].text) == (50, "line 1", "line 50")


def test_scrolled_off_lines_are_dropped_on_request():
    lines = run(python(SCROLLING), backend=PTY, rows=10, capture_visible_only=True).lines
    assert (len(lines), lines[0].text, lines[-1].text) == (9, "line 42", "line 50")


def test_visible_only_changes_how_the_stream_is_read_and_not_the_stream():
    everything = run(python(SCROLLING), backend=PTY, rows=10)
    visible = run(python(SCROLLING), backend=PTY, rows=10, capture_visible_only=True)
    assert visible.output == everything.output


def test_visible_only_keeps_the_final_screen_of_a_stopped_program():
    code = "import time\n" + SCROLLING + "\ntime.sleep(60)"
    options = {"backend": PTY, "rows": 10, "snapshot": Snapshot(after=1.0), "timeout": 30}
    everything = run(python(code), **options)
    visible = run(python(code), capture_visible_only=True, **options)
    assert everything.stopped and visible.stopped
    assert len(everything.lines) == 50
    assert texts(visible) == [f"line {number}" for number in range(42, 51)]


# --- остановка программы, когда сигнал ей послать нельзя (только Linux и macOS) ---


@skip_on("win32", "сигналы группе процессов есть только в POSIX")
@pytest.mark.parametrize("error", [ProcessLookupError, PermissionError])
def test_stopping_a_group_that_is_gone_or_protected_is_not_an_error(error: type[OSError]):
    # macOS: setuid-программе (top) нельзя послать SIGKILL, killpg отвечает EPERM; группы может уже не быть
    from termsnap.backends.pty import posix

    calls = []

    def refusing(pid: int, signal_number: int) -> None:
        calls.append((pid, signal_number))
        raise error

    posix.stop_group(123, kill=refusing)
    assert calls == [(123, signal.SIGKILL)]


@skip_on("win32", "сигналы группе процессов есть только в POSIX")
def test_other_errors_of_stopping_a_group_are_not_hidden():
    from termsnap.backends.pty import posix

    def broken(pid: int, signal_number: int) -> None:
        raise OSError("что-то другое")

    with pytest.raises(OSError, match="что-то другое"):
        posix.stop_group(123, kill=broken)


@skip_on("win32", "сигналы группе процессов есть только в POSIX")
def test_a_program_waiting_on_the_terminal_ends_when_the_terminal_is_closed_even_if_no_signal_is_sent():
    # так программа заканчивается там, где ей нельзя послать сигнал (setuid-программа на macOS): закрытый конец
    # терминала обрывает ей чтение. Запасной будильник (SIGALRM через 20 с) не дает тесту повиснуть, если не оборвет.
    from termsnap.backends.pty import posix

    code = "import signal, sys; signal.alarm(20); print('ready', flush=True); sys.stdin.read()"
    request = Request(argv=(sys.executable, "-c", code), env=dict(os.environ), snapshot=Snapshot(when="ready"))
    output, returncode, stopped = posix.run(sys.executable, request, stop=lambda pid: None)
    assert stopped
    assert b"ready" in output
    assert returncode != -signal.SIGALRM  # программа кончила сама, а не по будильнику
