"""
Настоящие запуски интерактивных программ: REPL с вводом и долгие программы со снимком экрана в заданный момент.
"""

import io
import re
import sys

import pytest
from registry import INTERACTIVE, PROGRAMS, Program

pytest.importorskip("pyte")
if sys.platform == "win32":
    pytest.importorskip("winpty")

from termsnap import (
    Capture,
    Indexed,
    Key,
    Keys,
    Pause,
    PipeBackend,
    PtyBackend,
    RunTimeout,
    Snapshot,
    Span,
    Style,
    run,
)

PTY = PtyBackend()
CAPTURES: dict[str, Capture] = {}
MONITOR = [sys.executable, str(PROGRAMS / "live_monitor.py")]


def program(name: str) -> Program:
    return next(p for p in INTERACTIVE if p.name == name)


def session(name: str) -> Capture:
    item = program(name)
    if name not in CAPTURES:
        CAPTURES[name] = run(item.argv, backend=PTY, timeout=120, **item.options)
    return CAPTURES[name]


def texts(capture: Capture) -> list[str]:
    return [line.text for line in capture.lines]


def tick(capture: Capture) -> int:
    match = re.search(r"tick\s+(\d+)", capture.lines[0].text)
    assert match, capture.lines[0].text
    return int(match.group(1))


# --- REPL с вводом ---


def test_scripted_session_of_a_tiny_repl_keeps_the_order_of_output():
    capture = session("mini_repl")
    assert capture.returncode == 0
    assert not capture.stopped
    assert texts(capture) == [
        "mini-repl: add a b | slow | fail | exit",
        ">> add 2 3",
        "5",
        ">> slow",
        "медленно, но готово",  # команда молчит дольше, чем settle (0.5 с): `bogus` не печатается раньше времени
        ">> bogus",
        "неизвестная команда: bogus",
        ">> fail",
        "ошибка: команда не удалась",  # вывод ошибок в том же порядке
        ">> exit",
        "пока",
    ]


def test_scripted_session_has_styles_of_the_prompt_and_replies():
    # приглашение - жирный зеленый, ответ add - бирюзовый, ошибки - красные, заголовок - тусклый; ввод без оформления
    prompt = Span(">>", Style(fg=Indexed(2), bold=True))
    error = Style(fg=Indexed(1))
    assert [line.spans for line in session("mini_repl").lines] == [
        (Span("mini-repl: add a b | slow | fail | exit", Style(dim=True)),),
        (prompt, Span(" add 2 3")),
        (Span("5", Style(fg=Indexed(6))),),
        (prompt, Span(" slow")),
        (Span("медленно, но готово"),),
        (prompt, Span(" bogus")),
        (Span("неизвестная команда: bogus", error),),
        (prompt, Span(" fail")),
        (Span("ошибка: команда не удалась", error),),
        (prompt, Span(" exit")),
        (Span("пока"),),
    ]


def test_input_without_a_prompt_pattern_goes_by_silence():
    code = "while (line := input()) != 'exit': print(line.upper())"
    capture = run([sys.executable, "-c", code], backend=PTY, input=("раз", "два", "exit"), settle=0.3)
    assert texts(capture) == ["раз", "РАЗ", "два", "ДВА", "exit"]


def test_program_that_never_stops_ends_with_a_timeout_and_keeps_what_was_typed():
    code = "while True: print(input().upper())"
    with pytest.raises(RunTimeout) as caught:
        run([sys.executable, "-c", code], backend=PTY, input=("abc",), timeout=3, settle=0.3)
    assert b"ABC" in caught.value.output


def test_pipe_backend_refuses_input_and_snapshot():
    with pytest.raises(ValueError, match="PtyBackend"):
        run([sys.executable, "-c", "pass"], backend=PipeBackend(), input=("x",))
    with pytest.raises(ValueError, match="PtyBackend"):
        run([sys.executable, "-c", "pass"], backend=PipeBackend(), snapshot=Snapshot())
    with pytest.raises(ValueError, match="PtyBackend"):
        run([sys.executable, "-c", "pass"], backend=PipeBackend(), capture_visible_only=True)


@pytest.mark.skipif(sys.platform == "win32", reason="ConPTY отвечает на запросы терминала сам")
def test_terminal_answers_the_cursor_position_request_of_a_program():
    code = (
        "import os, sys, tty; tty.setraw(0); sys.stdout.write('ab' + chr(27) + '[6n'); sys.stdout.flush(); "
        "reply = os.read(0, 32); sys.stdout.write(chr(13) + chr(10) + repr(reply)); sys.stdout.flush()"
    )
    capture = run([sys.executable, "-c", code], backend=PTY, timeout=30)
    # программа печатает то, что прочитала в ответ: позицию курсора "строка 1, столбец 3" (после двух букв)
    assert texts(capture) == ["ab", repr(b"\x1b[1;3R")]


# --- долгая программа: когда снимать экран ---
#
# ``live_monitor.py`` рисует таблицу процессов (данные выдуманы) и пять раз в секунду обновляет счетчик ``tick`` в
# первой строке; ``s`` меняет сортировку, стрелки двигают выбор. Все, кроме первой строки, на экране известно точно.


def monitor_screen(*rows: str) -> list[str]:
    """
    Экран монитора без первой строки (в ней меняющийся счетчик): пустая строка, заголовок таблицы, шесть процессов,
    пустая строка и подсказка по клавишам.
    """
    return ["", "  NAME        CPU%   MEM%", *rows, "", "q quit   s sort   up/down select"]


BY_CPU_FIRST_SELECTED = monitor_screen(
    "> ffmpeg      77.9    2.2",
    "  python      48.2    3.4",
    "  node        31.0    6.7",
    "  postgres    12.5    8.1",
    "  nginx        1.2    0.9",
    "  redis        0.8    1.5",
)
BY_NAME_THIRD_SELECTED = monitor_screen(
    "  ffmpeg      77.9    2.2",
    "  nginx        1.2    0.9",
    "> node        31.0    6.7",
    "  postgres    12.5    8.1",
    "  python      48.2    3.4",
    "  redis        0.8    1.5",
)
BY_CPU_LAST_SELECTED = monitor_screen(
    "  ffmpeg      77.9    2.2",
    "  python      48.2    3.4",
    "  node        31.0    6.7",
    "  postgres    12.5    8.1",
    "  nginx        1.2    0.9",
    "> redis        0.8    1.5",
)


def test_without_a_snapshot_a_program_that_never_ends_is_a_timeout():
    with pytest.raises(RunTimeout) as caught:
        run(MONITOR, backend=PTY, timeout=2)
    assert b"monitor" in caught.value.output


def test_snapshot_after_takes_the_screen_and_stops_the_program():
    capture = run(MONITOR, backend=PTY, rows=12, snapshot=Snapshot(after=1.0), timeout=30)
    assert capture.stopped
    assert capture.ok  # остановили мы сами, код возврата ничего не значит
    assert capture.duration < 10
    assert 2 <= tick(capture) <= 8  # кадр каждые 0.2 с, около секунды после запуска
    assert texts(capture)[1:] == BY_CPU_FIRST_SELECTED


def test_snapshot_shows_the_screen_with_its_styles():
    capture = run(MONITOR, backend=PTY, snapshot=Snapshot(after=0.5), timeout=30)
    header = capture.lines[0].spans
    assert [span.style for span in header] == [Style(bold=True, inverse=True)]  # вся первая строка одним фрагментом
    assert [span.style for span in capture.lines[2].spans] == [Style(bold=True)]  # заголовок таблицы жирный
    # процент CPU красный выше 40, желтый выше 10, иначе зеленый; выбранная строка целиком обращена
    cpu_colours = {line.text[2:].split()[0]: line.spans[1].style for line in capture.lines[3:9]}
    assert cpu_colours == {
        "ffmpeg": Style(fg=Indexed(1), inverse=True),
        "python": Style(fg=Indexed(1)),
        "node": Style(fg=Indexed(3)),
        "postgres": Style(fg=Indexed(3)),
        "nginx": Style(fg=Indexed(2)),
        "redis": Style(fg=Indexed(2)),
    }
    assert capture.lines[10].spans == (Span("q quit   s sort   up/down select", Style(dim=True)),)


def test_snapshot_when_waits_for_the_text_on_the_screen():
    capture = run(MONITOR, backend=PTY, snapshot=Snapshot(when=r"tick\s+6\b"), timeout=30)
    assert capture.stopped
    assert 6 <= tick(capture) <= 7  # кадр мог смениться, пока шли проверки


def test_snapshot_when_that_never_happens_is_a_timeout_with_what_was_seen():
    with pytest.raises(RunTimeout) as caught:
        run(MONITOR, backend=PTY, snapshot=Snapshot(when="такого-на-экране-нет"), timeout=2)
    assert b"monitor" in caught.value.output


def test_keys_change_what_the_program_shows():
    # s - сортировка по имени; затем два раза вниз от первой строки: выбрана третья (node)
    steps = (Keys("s"), Pause(0.4), Key.DOWN, Pause(0.4), Key.DOWN, Pause(0.4))
    capture = run(MONITOR, backend=PTY, input=steps, settle=0, snapshot=Snapshot(after=0.5), timeout=30)
    assert "sort: name" in capture.lines[0].text
    assert texts(capture)[1:] == BY_NAME_THIRD_SELECTED


def test_keys_stop_at_the_ends_of_the_list():
    # вверх от первой строки не уходим, вниз - только до последней (redis)
    steps = (Key.UP, Pause(0.3), *([Key.DOWN, Pause(0.3)] * 8))
    capture = run(MONITOR, backend=PTY, input=steps, settle=0, snapshot=Snapshot(after=0.4), timeout=30)
    assert texts(capture)[1:] == BY_CPU_LAST_SELECTED


def test_program_that_quits_on_its_own_is_not_stopped():
    capture = run(MONITOR, backend=PTY, input=(Pause(0.6), Keys("q")), settle=0, timeout=30)
    assert not capture.stopped
    assert capture.returncode == 0
    assert tick(capture) >= 1  # последний кадр остался на экране


def test_snapshot_is_not_needed_if_the_program_ends_first():
    code = "print('готово')"
    capture = run([sys.executable, "-c", code], backend=PTY, snapshot=Snapshot(after=30), timeout=60)
    assert not capture.stopped  # программа успела завершиться сама, снимок по таймеру не понадобился
    assert capture.text == "готово"


def test_stopped_capture_renders_to_png():
    pytest.importorskip("PIL")
    from PIL import Image

    from termsnap.errors import FontNotFound
    from termsnap.png import render_png

    capture = run(MONITOR, backend=PTY, rows=12, snapshot=Snapshot(after=0.5), timeout=30)
    try:
        data = render_png(capture.lines, font_size=12, scale=1)
    except FontNotFound as error:
        pytest.skip(f"нет моноширинного шрифта: {error.problems}")
    assert Image.open(io.BytesIO(data)).height > 100
