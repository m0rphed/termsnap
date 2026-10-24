"""
Набор настоящих программ с нетривиальным цветным выводом: на нем проверяются разбор ANSI и рисование в PNG.

Каждая запись - команда и каталог запуска. Программы лежат в ``programs`` (скрипты rich и Node.js, образцы для pytest и
ruff); если нужного инструмента нет в системе, запись пропускается (``available``).
"""

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from termsnap import Key, Keys, Pause, Snapshot, Step

HERE = Path(__file__).resolve().parent
PROGRAMS = HERE / "programs"
PY = sys.executable


@dataclass(frozen=True, slots=True)
class Program:
    name: str
    argv: tuple[str, ...]
    tool: str | None = None  # внешняя программа, без которой запись пропускается
    expect_failure: bool = False  # программа должна завершаться с ненулевым кодом (проверка pytest и ruff)
    colored: bool = True  # в выводе должны быть цвета
    input: tuple[Step, ...] = ()  # шаги сценария: строки, клавиши, паузы (только псевдотерминал)
    prompt: str | None = None  # как выглядит приглашение, когда программа ждет ввода
    settle: float = 0.5  # сколько вывод должен молчать перед следующим шагом (0 - для постоянно перерисовываемых)
    snapshot: Snapshot | None = None  # когда снять экран у программы, которая сама не завершается
    isolated: bool = False  # без VIRTUAL_ENV: uvx-программы не должны думать, что работают в нашем окружении
    posix_only: bool = False  # программа есть только в Linux и macOS
    external: bool = False  # чужая команда, а не скрипт проекта: тесты на ней лежат в tests/external

    @property
    def available(self) -> bool:
        if self.posix_only and sys.platform == "win32":
            return False
        return self.tool is None or shutil.which(self.tool) is not None

    @property
    def options(self) -> dict[str, Any]:
        """
        Аргументы ``termsnap.run`` для этой программы (кроме ``argv`` и ``backend``).
        """
        env = {key: value for key, value in os.environ.items() if not self.isolated or key != "VIRTUAL_ENV"}
        return {
            "env": env,
            "input": self.input,
            "prompt": self.prompt,
            "settle": self.settle,
            "snapshot": self.snapshot,
        }


def _script(name: str) -> str:
    return str(PROGRAMS / name)


REGISTRY = [
    Program("rich_table", (PY, _script("rich_table.py"))),
    Program("rich_panel_tree", (PY, _script("rich_panel_tree.py"))),
    Program("rich_syntax", (PY, _script("rich_syntax.py"))),
    Program("rich_markdown", (PY, _script("rich_markdown.py"))),
    Program("rich_traceback", (PY, _script("rich_traceback.py"))),
    Program("rich_progress", (PY, _script("rich_progress.py"))),
    Program("rich_live", (PY, _script("rich_live.py"))),
    Program("rich_misc", (PY, _script("rich_misc.py"))),
    Program("node_inspect", ("node", _script("node_inspect.js")), tool="node", external=True),
    Program("node_ansi", ("node", _script("node_ansi.js")), tool="node", external=True),
    Program(
        "pytest_failure",
        (PY, "-m", "pytest", _script("sample_failing_test.py"), "--color=yes", "-p", "no:cacheprovider", "-q"),
        expect_failure=True,
        external=True,
    ),
    Program(
        "ruff_diagnostics",
        (PY, "-m", "ruff", "check", _script("bad_style.py"), "--color=always", "--no-cache", "--select", "E,F,I"),
        expect_failure=True,
        external=True,
    ),
    Program(
        "git_log",
        ("git", "-C", str(HERE.parent), "log", "--oneline", "--graph", "--color=always", "-n", "5"),
        tool="git",
        external=True,
    ),
]

#: Программы, которым нужен терминал: в канале они дают бедный или бессмысленный вывод (rich без настроек, вывод
#: абсолютными позициями курсора, вывод длиннее экрана). Запускаются только через ``PtyBackend``.
PTY_REGISTRY = [
    Program("rich_native", (PY, _script("rich_native.py"))),
    Program("full_screen", (PY, _script("full_screen.py"))),
    Program("long_output", (PY, _script("long_output.py"))),
]

#: Интерактивные программы (REPL): им печатается ввод, поэтому запускаются только через ``PtyBackend``. IPython берется
#: через ``uvx`` (при первом запуске нужна сеть), ставить его в проект не нужно.
INTERACTIVE = [
    Program(
        "mini_repl",
        (PY, _script("mini_repl.py")),
        input=("add 2 3", "slow", "bogus", "fail", "exit"),
        prompt=r">>$",
    ),
    Program(
        "ipython_session",
        ("uvx", "--quiet", "ipython"),
        tool="uvx",
        input=(
            "squares = [n ** 2 for n in range(6)]",
            "squares",
            "import math; math.pi",
            "1 / 0",
            "exit",
        ),
        prompt=r"In \[\d+\]:$",
        isolated=True,
        external=True,
    ),
    # стрелка вверх достает прошлую строку из истории, Enter ее повторяет
    Program(
        "ipython_history",
        ("uvx", "--quiet", "ipython", "--no-banner"),
        tool="uvx",
        input=("6 * 7", Key.UP, Key.ENTER, Pause(1), "exit"),
        prompt=r"In \[\d+\]:$",
        isolated=True,
        external=True,
    ),
    # Tab открывает меню автодополнения (первый раз оно появляется не сразу): снимок ждет его появления
    Program(
        "ipython_complete",
        ("uvx", "--quiet", "ipython", "--no-banner"),
        tool="uvx",
        input=("import math", Keys("math.s"), Key.TAB),
        prompt=r"In \[\d+\]:$",
        snapshot=Snapshot(when=r"sqrt", after=0.3),
        isolated=True,
        external=True,
    ),
    # программы, которые сами не завершаются: экран снимается в заданный момент, и программа останавливается
    Program(
        "live_monitor",
        (PY, _script("live_monitor.py")),
        input=(Keys("s"), Pause(0.4), Key.DOWN, Pause(0.4), Key.DOWN, Pause(0.4)),
        settle=0,
        snapshot=Snapshot(after=0.5),
    ),
    Program("htop", ("htop",), tool="htop", snapshot=Snapshot(when=r"Tasks:", after=2), external=True),
    Program(
        "top",
        ("top",),
        tool="top",
        posix_only=True,
        snapshot=Snapshot(when=r"PID\s+(USER|COMMAND)", after=1),
        external=True,
    ),
]

ALL_PROGRAMS = [*REGISTRY, *PTY_REGISTRY, *INTERACTIVE]

#: Скрипты проекта: тесты на них лежат в ``tests/integration``. Чужие команды (``external=True``) проверяются в
#: ``tests/external``.
PROJECT_PROGRAMS = [program for program in ALL_PROGRAMS if not program.external]
EXTERNAL_PROGRAMS = [program for program in ALL_PROGRAMS if program.external]
