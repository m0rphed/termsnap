"""
Клавиши доходят до программы теми байтами, которые в терминале посылает настоящее нажатие: стрелки, Tab, Esc, Ctrl+C,
функциональные клавиши. Программа ``tests/programs/key_reporter.py`` переводит терминал в сырой режим и пишет, что
получила за одно чтение; так проверяется весь путь от ``Key`` через ``PtyBackend`` и операционную систему, без IPython.
"""

import sys

import pytest
from registry import PROGRAMS
from support import require_pty_extras

require_pty_extras()

from termsnap import Capture, Key, Keys, PtyBackend, run

#: Что послать и как программа назовет полученное. Последние три - не клавиши с именем, а Ctrl+L, Ctrl+Z и строка:
#: программа показывает их байты.
KEYS = [
    (Key.UP, "up"),
    (Key.DOWN, "down"),
    (Key.LEFT, "left"),
    (Key.RIGHT, "right"),
    (Key.TAB, "tab"),
    (Key.ESC, "esc"),
    (Key.ENTER, "enter"),
    (Key.BACKSPACE, "backspace"),
    (Key.CTRL_C, "ctrl+c"),
    (Key.CTRL_D, "ctrl+d"),
    (Key.HOME, "home"),
    (Key.END, "end"),
    (Key.DELETE, "delete"),
    (Key.PAGE_UP, "page up"),
    (Key.PAGE_DOWN, "page down"),
    (Key.F[1], "f1"),
    (Key.F[5], "f5"),
    (Keys("a"), "letter a"),
    (Keys("7"), "letter 7"),
    (Key.ctrl("l"), r"bytes b'\x0c'"),
    (Key.ctrl("z"), r"bytes b'\x1a'"),
    (Keys("ab"), "bytes b'ab'"),
]


@pytest.fixture(scope="module")
def session() -> Capture:
    return run(
        (sys.executable, str(PROGRAMS / "key_reporter.py")),
        backend=PtyBackend(),
        timeout=60,
        input=(*(key for key, _ in KEYS), Keys("q")),
        prompt=r">$",
        settle=0.3,
    )


def test_every_key_arrives_as_one_event_with_the_name_the_terminal_gives_it(session: Capture):
    assert [line.text for line in session.lines] == [
        "keys: press anything, q quits",
        *(f"> {name}" for _, name in KEYS),
        "> bye",
    ]


def test_ctrl_c_is_a_key_here_and_not_a_signal_that_ends_the_program(session: Capture):
    # терминал в сыром режиме: Ctrl+C - байт 3, программа продолжила работу и корректно завершилась по "q"
    assert "> ctrl+c" in session.text
    assert session.returncode == 0
    assert not session.stopped
