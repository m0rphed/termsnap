import io
import sys

import pytest
from registry import PTY_REGISTRY, REGISTRY, Program

pytest.importorskip("pyte")
if sys.platform == "win32":
    pytest.importorskip("winpty")

from termsnap import Capture, Indexed, PtyBackend, Rgb, RunTimeout, Style, run

PTY = PtyBackend()
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


def test_plain_rich_console_needs_no_workarounds_in_a_pty():
    capture = captured("rich_native")
    assert capture.lines[0].text.startswith("терминал: True, цвета: ")
    assert len(colours(capture)) >= 3
    assert "✅ ok" in capture.text
    assert "⚠️ warn" in capture.text


def test_plain_rich_table_and_panel_are_rectangles():
    blocks: list[list[int]] = []
    for line in captured("rich_native").lines:
        if line.text[:1] in "┏┃┡│└╭╰":
            if not blocks or line.text[:1] in "┏╭":
                blocks.append([])
            blocks[-1].append(line.width)
    assert len(blocks) == 2  # таблица и панель
    assert all(len(set(widths)) == 1 for widths in blocks), blocks


def test_full_screen_program_leaves_exactly_the_drawn_screen():
    lines = captured("full_screen").lines
    assert len(lines) == 30  # последняя строка экрана занята нижней полосой
    assert lines[0].text.strip() == "top - 12:00:00 up 3 days, 2 users"
    assert lines[0].spans[0].style.inverse
    assert lines[2].text.startswith("CPU  ||||||||")
    assert lines[5].text == " " * 9 + "Привет, терминал"
    assert lines[7].text == "новая строка"
    assert lines[29].text.strip() == "q: выход"
    assert lines[29].spans[0].style.bg == Indexed(4)
    assert all(line.text == "" for line in lines[8:29])


def test_output_longer_than_the_screen_is_not_lost():
    lines = captured("long_output").lines
    assert len(lines) == 120
    assert lines[0].text == "строка 001: x"
    assert lines[119].text.startswith("строка 120")


def test_all_registry_programs_run_in_a_pty_and_leave_no_escape_sequences():
    for item in REGISTRY:
        if not item.available:
            continue
        capture = captured(item.name)
        assert (capture.returncode != 0) is item.expect_failure, item.name
        assert capture.lines, item.name
        assert "\x1b" not in capture.text, item.name


@pytest.mark.parametrize(
    "name",
    ["rich_table", "rich_panel_tree", "rich_syntax", "rich_traceback", "rich_progress", "rich_live", "node_ansi"],
)
def test_pty_and_pipe_agree_on_programs_that_do_not_depend_on_the_terminal(name: str):
    if not program(name).available:
        pytest.skip("нет программы")
    piped = run(program(name).argv, timeout=60)
    assert [line.text.rstrip() for line in captured(name).lines] == [line.text.rstrip() for line in piped.lines]


def test_pty_and_pipe_use_the_same_colours_for_rich_table():
    assert colours(captured("rich_table")) == colours(run(program("rich_table").argv))


def test_rich_misc_keeps_emoji_with_variation_selector():
    text = captured("rich_misc").text
    assert "⚠️" in text
    assert "Иероглифы" in text


@pytest.mark.parametrize("name", [p.name for p in PTY_REGISTRY])
def test_pty_programs_render_to_png(name: str):
    pytest.importorskip("PIL")
    from PIL import Image

    from termsnap.errors import FontNotFound
    from termsnap.png import render_png

    try:
        data = render_png(captured(name).lines, font_size=12, scale=1)
    except FontNotFound as error:
        pytest.skip(f"нет моноширинного шрифта: {error.problems}")
    assert Image.open(io.BytesIO(data)).width > 100


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


@pytest.mark.skipif(sys.platform == "win32", reason="сигналы группе процессов есть только в POSIX")
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
