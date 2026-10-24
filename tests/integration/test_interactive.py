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
    run,
)

PTY = PtyBackend()
CAPTURES: dict[str, Capture] = {}
MONITOR = [sys.executable, str(PROGRAMS / "live_monitor.py")]


def program(name: str) -> Program:
    return next(p for p in INTERACTIVE if p.name == name)


def session(name: str) -> Capture:
    item = program(name)
    if not item.available:
        pytest.skip(f"нет программы {item.tool}")
    if name not in CAPTURES:
        CAPTURES[name] = run(item.argv, backend=PTY, timeout=120, **item.options)
    return CAPTURES[name]


def span(capture: Capture, prefix: str) -> Span:
    return next(s for line in capture.lines for s in line.spans if s.text.lstrip().startswith(prefix))


def texts(capture: Capture) -> list[str]:
    return [line.text for line in capture.lines]


def tick(capture: Capture) -> int:
    match = re.search(r"tick\s+(\d+)", capture.lines[0].text)
    assert match, capture.lines[0].text
    return int(match.group(1))


def names(capture: Capture) -> list[str]:
    """
    Названия процессов на экране монитора сверху вниз.
    """
    return [line.text[2:].split()[0] for line in capture.lines[3:9]]


def selected(capture: Capture) -> str:
    return next(line.text[2:].split()[0] for line in capture.lines if line.text.startswith(">"))


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
    capture = session("mini_repl")
    assert span(capture, ">>").style.fg == Indexed(2)
    assert span(capture, ">>").style.bold
    assert span(capture, "5").style.fg == Indexed(6)
    assert span(capture, "неизвестная").style.fg == Indexed(1)
    assert span(capture, "mini-repl").style.dim


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
    assert texts(capture) == ["ab", "b'" + chr(92) + "x1b[1;3R'"]  # столбец 3: после двух напечатанных букв


# --- долгая программа: когда снимать экран ---


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
    assert names(capture) == ["ffmpeg", "python", "node", "postgres", "nginx", "redis"]
    assert selected(capture) == "ffmpeg"


def test_snapshot_shows_the_screen_with_its_styles():
    capture = run(MONITOR, backend=PTY, snapshot=Snapshot(after=0.5), timeout=30)
    header = capture.lines[0].spans[0]
    assert header.style.inverse
    assert header.style.bold
    assert span(capture, "77.9").style.fg == Indexed(1)  # больше 40% - красный
    assert span(capture, "12.5").style.fg == Indexed(3)
    assert span(capture, "0.8").style.fg == Indexed(2)
    assert any(s.style.inverse for s in capture.lines[3].spans)  # выбранная строка


def test_snapshot_when_waits_for_the_text_on_the_screen():
    capture = run(MONITOR, backend=PTY, snapshot=Snapshot(when=r"tick\s+6\b"), timeout=30)
    assert capture.stopped
    assert 6 <= tick(capture) <= 7  # кадр мог смениться, пока шли проверки


def test_snapshot_when_that_never_happens_is_a_timeout_with_what_was_seen():
    with pytest.raises(RunTimeout) as caught:
        run(MONITOR, backend=PTY, snapshot=Snapshot(when="такого-на-экране-нет"), timeout=2)
    assert b"monitor" in caught.value.output


def test_keys_change_what_the_program_shows():
    steps = (Keys("s"), Pause(0.4), Key.DOWN, Pause(0.4), Key.DOWN, Pause(0.4))
    capture = run(MONITOR, backend=PTY, input=steps, settle=0, snapshot=Snapshot(after=0.5), timeout=30)
    assert "sort: name" in capture.lines[0].text  # s переключила сортировку
    assert names(capture) == ["ffmpeg", "nginx", "node", "postgres", "python", "redis"]
    assert selected(capture) == "node"  # дважды вниз от первой строки


def test_keys_stop_at_the_ends_of_the_list():
    steps = (Key.UP, Pause(0.3), *([Key.DOWN, Pause(0.3)] * 8))
    capture = run(MONITOR, backend=PTY, input=steps, settle=0, snapshot=Snapshot(after=0.4), timeout=30)
    assert selected(capture) == names(capture)[-1] == "redis"  # вверх от первой строки не ушли, вниз - до последней


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
