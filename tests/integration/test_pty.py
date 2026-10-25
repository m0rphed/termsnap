import sys

import pytest
from picture import check_snapshot_picture
from registry import PTY_REGISTRY, REGISTRY, Program
from styles import styles_by_text
from support import require_pty_extras, skip_on

require_pty_extras()

from termsnap import Capture, Indexed, PtyBackend, Rgb, RunTimeout, Span, Style, run

PTY = PtyBackend()
VS16 = "️"  # селектор эмодзи
CAPTURES: dict[str, Capture] = {}


def python(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def program(name: str) -> Program:
    return next(p for p in [*REGISTRY, *PTY_REGISTRY] if p.name == name)


def captured(name: str) -> Capture:
    if name not in CAPTURES:
        CAPTURES[name] = run(program(name).argv, backend=PTY, timeout=60)
    return CAPTURES[name]


def colours(capture: Capture) -> set:
    return {span.style.fg for line in capture.lines for span in line.spans if span.style.fg is not None}


def test_program_sees_a_terminal_of_the_requested_size():
    code = "import sys, os; print(sys.stdout.isatty(), sys.stdin.isatty(), os.get_terminal_size())"
    capture = run(python(code), backend=PTY, columns=80, rows=24)
    assert capture.text == "True True os.terminal_size(columns=80, lines=24)"
    assert (capture.columns, capture.rows) == (80, 24)


def test_exit_code_is_reported():
    capture = run(python("import sys; print('boom'); sys.exit(3)"), backend=PTY)
    assert capture.returncode == 3
    assert capture.text == "boom"


def test_stdout_and_stderr_share_the_terminal_in_order():
    code = "import sys; print('a', flush=True); print('b', file=sys.stderr, flush=True); print('c', flush=True)"
    assert run(python(code), backend=PTY).text == "a\nb\nc"


def test_raw_terminal_stream_is_kept():
    assert b"\x1b[1mx" in run(python("print('\\x1b[1mx')"), backend=PTY).output


def test_dim_palette_and_truecolor_survive_the_pty():
    code = "print('\\x1b[2mdim\\x1b[0m \\x1b[38;5;202mtone\\x1b[0m \\x1b[38;2;1;2;3mrgb')"
    (line,) = run(python(code), backend=PTY).lines
    styles = {span.text: span.style for span in line.spans}
    assert styles["dim"].dim
    assert styles["tone"] == Style(fg=Indexed(202))
    assert styles["rgb"] == Style(fg=Rgb(1, 2, 3))


def test_timeout_stops_the_program_and_keeps_its_output():
    code = "import time; print('started', flush=True); time.sleep(60)"
    with pytest.raises(RunTimeout) as caught:
        run(python(code), backend=PTY, timeout=1.5)
    assert b"started" in caught.value.output


def test_missing_program_is_reported():
    with pytest.raises(FileNotFoundError):
        run(["no-such-program-termsnap"], backend=PTY)


def test_color_can_be_turned_off():
    capture = run(program("rich_native").argv, backend=PTY, color=False)
    assert capture.lines
    assert not colours(capture)
    assert not any(span.style.bg is not None for line in capture.lines for span in line.spans)


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


def test_plain_rich_console_needs_no_workarounds_in_a_pty():
    # rich без настроек сам видит терминал: цвета, ширину и эмодзи определяет по нему, таблица и панель ровные
    capture = captured("rich_native")
    assert [line.text for line in capture.lines] == RICH_NATIVE
    assert {line.width for line in capture.lines[2:9]} == {31}
    assert {line.width for line in capture.lines[9:]} == {100}


def test_plain_rich_console_colours_in_a_pty():
    styles = styles_by_text(captured("rich_native"))
    assert styles["Тест"] == Style(bold=True)
    assert styles["✅ ok"] == Style(fg=Indexed(2))
    assert styles["❌ fail"] == Style(fg=Indexed(1))
    assert styles["0.12"] == Style(dim=True)
    assert styles["ВНИМАНИЕ"] == Style(fg=Indexed(1), bold=True)


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


def test_full_screen_program_leaves_exactly_the_drawn_screen():
    # программа рисует экран абсолютными позициями курсора: разбор потока по строкам такой вывод не прочитал бы
    capture = captured("full_screen")
    assert [line.text for line in capture.lines] == FULL_SCREEN


def test_full_screen_program_keeps_the_styles_of_what_it_drew():
    lines = captured("full_screen").lines
    assert lines[0].spans == (Span(" top - 12:00:00 up 3 days, 2 users ", Style(inverse=True)),)  # строка состояния
    assert lines[2].spans == (Span("CPU  "), Span("||||||||", Style(fg=Indexed(2))), Span(" 40%"))  # зеленая шкала
    assert lines[3].spans == (Span("MEM  "), Span("||||||||||||", Style(fg=Indexed(3))), Span(" 60%"))  # желтая
    assert lines[5].spans == (Span("         "), Span("Привет, терминал", Style(fg=Indexed(6), bold=True)))
    assert lines[29].spans == (Span(" q: выход ", Style(fg=Indexed(15), bg=Indexed(4))),)  # белое на синем


def test_output_longer_than_the_screen_is_not_lost():
    # 120 строк в экране из 30: верхние уходят за его край, но остаются в результате
    lines = captured("long_output").lines
    assert len(lines) == 120
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
    assert lines[-1].text == "строка 120: x"
    # цвет меняется каждые десять строк: 1-9 красный, 10-19 зеленый, затем дальше по кругу из шести цветов
    assert [lines[number - 1].spans[0].style.fg for number in (1, 9, 10, 19, 20, 60, 120)] == [
        Indexed(index) for index in (1, 1, 2, 2, 3, 1, 1)
    ]


PROJECT = [program for program in REGISTRY if not program.external]


@pytest.mark.parametrize("item", PROJECT, ids=lambda item: item.name)
def test_project_programs_run_in_a_pty_and_leave_no_escape_sequences(item: Program):
    capture = captured(item.name)
    assert (capture.returncode != 0) is item.expect_failure, item.name
    assert capture.lines, item.name
    assert "\x1b" not in capture.text, item.name


@pytest.mark.parametrize(
    "name",
    ["rich_table", "rich_panel_tree", "rich_syntax", "rich_traceback", "rich_progress", "rich_live"],
)
def test_pty_and_pipe_agree_on_programs_that_do_not_depend_on_the_terminal(name: str):
    piped = run(program(name).argv, timeout=60)
    assert [line.text.rstrip() for line in captured(name).lines] == [line.text.rstrip() for line in piped.lines]


def test_pty_and_pipe_use_the_same_colours_for_rich_table():
    assert colours(captured("rich_table")) == colours(run(program("rich_table").argv))


def test_rich_misc_keeps_emoji_with_variation_selector():
    last_line = captured("rich_misc").lines[-1].text
    assert last_line == f"Эмодзи: 🚀 ✅ ❌ ⚠{VS16} 🐍  Иероглифы: 日本語 中文  Рамки: ┌─┬─┐│ │ │└─┴─┘"


@pytest.mark.parametrize("name", [p.name for p in PTY_REGISTRY])
def test_pty_programs_render_to_a_picture_that_follows_their_screen(name: str, bundled_fonts):
    check_snapshot_picture(captured(name).lines, bundled_fonts)


# --- видимая часть экрана и прокрутка ---

SCROLLING = "for n in range(1, 51): print('line', n)"


def test_scrolled_off_lines_are_kept_by_default_and_dropped_on_request():
    everything = run(python(SCROLLING), backend=PTY, rows=10)
    assert (len(everything.lines), everything.lines[0].text, everything.lines[-1].text) == (50, "line 1", "line 50")
    visible = run(python(SCROLLING), backend=PTY, rows=10, capture_visible_only=True)
    assert (len(visible.lines), visible.lines[0].text, visible.lines[-1].text) == (9, "line 42", "line 50")
    assert visible.output == everything.output  # сырой поток тот же, различается только разбор


def test_visible_only_keeps_the_final_screen_of_a_stopped_program():
    from termsnap import Snapshot

    code = "import time\n" + SCROLLING + "\ntime.sleep(60)"
    options = {"backend": PTY, "rows": 10, "snapshot": Snapshot(after=1.0), "timeout": 30}
    everything = run(python(code), **options)
    visible = run(python(code), capture_visible_only=True, **options)
    assert everything.stopped and visible.stopped
    assert len(everything.lines) == 50
    assert [line.text for line in visible.lines] == [f"line {number}" for number in range(42, 51)]


@skip_on("win32", "сигналы группе процессов есть только в POSIX")
def test_a_program_that_cannot_be_signalled_is_still_stopped_by_hanging_up_the_terminal(monkeypatch):
    # macOS: setuid-программе (top) нельзя послать SIGKILL, killpg отвечает EPERM
    import os

    def forbidden(pid: int, sig: int) -> None:
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(os, "killpg", forbidden)
    from termsnap import Snapshot

    code = "import time; print('ready', flush=True); time.sleep(60)"
    capture = run(python(code), backend=PTY, snapshot=Snapshot(after=0.5), timeout=30)
    assert capture.stopped
    assert capture.text == "ready"
