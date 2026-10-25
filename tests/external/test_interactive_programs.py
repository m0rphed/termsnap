"""
Чужие интерактивные программы в псевдотерминале: ``top`` и ``htop`` снимаются в заданный момент, IPython получает
ввод, историю по стрелке вверх и автодополнение по Tab. Состав программ - ``tests/registry.py``.
"""

import io
import re
import shutil
import subprocess
import sys

import pytest
from registry import INTERACTIVE, Program

pytest.importorskip("pyte")
if sys.platform == "win32":
    pytest.importorskip("winpty")

from termsnap import Capture, Indexed, PtyBackend, Span, run

PTY = PtyBackend()
CAPTURES: dict[str, Capture] = {}


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


# --- top и htop ---


def test_real_top_shows_its_header_and_the_process_table():
    capture = session("top")
    assert capture.stopped
    assert capture.lines[0].text.startswith(("top - ", "Processes:"))  # procps в Linux, BSD-top в macOS
    assert any(re.match(r"\s*PID\s+(USER|COMMAND)", text) for text in texts(capture))
    assert "\x1b" not in capture.text


def test_real_htop_shows_meters_and_the_process_table():
    capture = session("htop")
    assert capture.stopped
    assert any("Tasks:" in text for text in texts(capture))
    assert any("PID" in text and "Command" in text for text in texts(capture))
    assert len({s.style for line in capture.lines for s in line.spans}) > 5  # цветные счетчики и заголовок


# --- IPython через uvx (ставить его в проект не нужно; при первом запуске нужна сеть) ---


@pytest.fixture(scope="module")
def ipython() -> None:
    if shutil.which("uvx") is None:
        pytest.skip("нет uvx")
    try:
        subprocess.run(["uvx", "--quiet", "ipython", "--version"], check=True, capture_output=True, timeout=300)
    except (subprocess.SubprocessError, OSError) as error:
        pytest.skip(f"IPython не удалось получить через uvx: {error}")


def test_ipython_repl_shows_the_whole_session(ipython: None):
    capture = session("ipython_session")
    assert capture.returncode == 0
    lines = texts(capture)
    assert "In [1]: squares = [n ** 2 for n in range(6)]" in lines
    assert "Out[2]: [0, 1, 4, 9, 16, 25]" in lines
    assert "Out[3]: 3.141592653589793" in lines
    assert "ZeroDivisionError: division by zero" in lines
    assert lines[-1] == "In [5]: exit"


def test_ipython_prompts_and_traceback_are_coloured(ipython: None):
    capture = session("ipython_session")
    assert span(capture, "In [").style.fg == Indexed(2)
    assert span(capture, "Out[").style.fg == Indexed(1)
    assert span(capture, "ZeroDivisionError").style.fg == Indexed(1)


def test_ipython_input_is_syntax_highlighted(ipython: None):
    capture = session("ipython_session")
    (line,) = [line for line in capture.lines if line.text.startswith("In [3]")]
    assert len({s.style for s in line.spans}) >= 3  # приглашение, ключевое слово, имена и т.д.


def test_ipython_up_arrow_brings_back_the_previous_line(ipython: None):
    capture = session("ipython_history")
    assert capture.returncode == 0
    assert [line for line in texts(capture) if line] == [
        "In [1]: 6 * 7",
        "Out[1]: 42",
        "In [2]: 6 * 7",  # строку достала стрелка вверх, Enter ее повторил
        "Out[2]: 42",
        "In [3]: exit",
    ]


def test_ipython_tab_opens_the_completion_menu_and_the_snapshot_waits_for_it(ipython: None):
    capture = session("ipython_complete")
    assert capture.stopped
    lines = texts(capture)
    assert "In [2]: math.s" in lines
    menu = " ".join(lines[lines.index("In [2]: math.s") + 1 :])
    assert {"sqrt", "sin", "sinh"} <= {word.removesuffix("()") for word in menu.split()}


def test_ipython_session_renders_to_png(ipython: None):
    pytest.importorskip("PIL")
    from PIL import Image

    from termsnap.errors import FontNotFound
    from termsnap.png import render_png

    try:
        data = render_png(session("ipython_session").lines, font_size=12, scale=1)
    except FontNotFound as error:
        pytest.skip(f"нет моноширинного шрифта: {error.problems}")
    assert Image.open(io.BytesIO(data)).height > 100
