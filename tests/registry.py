"""
Программы, на которых проверяются запуск, разбор ANSI и рисование в PNG.

Каждая запись - команда запуска и то, что нужно знать, чтобы ее проверить. Скрипты лежат в ``tests/programs``;
ожидаемый вывод каждой программы записан рядом с ее тестами, а не здесь.

Чужие программы делятся на две части. Python-пакеты (IPython, pytest, ruff, rich) берутся из окружения проекта, их
версии держит ``uv.lock``. Системные программы (``top``, ``htop``, ``man``, ``git``, ``node``) ищутся в ``PATH``. На
каждой системе программа либо обязательна (нет ее - тест падает), либо явно исключена (``Program.absent`` с причиной -
тест пропускается). Третьего нет: тихого пропуска из-за того, что чего-то не оказалось, не бывает (``require``).
"""

import os
import shutil
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import nodejs_wheel.executable
import pytest
from support import EXPECTED_SKIP

from termsnap import Key, Keys, Pause, Snapshot, Step


def _node() -> str:
    """
    Node.js из окружения проекта (пакет ``nodejs-wheel-binaries``, версия в ``uv.lock``): системный у всех свой.
    """
    root = Path(nodejs_wheel.executable.ROOT_DIR)
    return str(root / "node.exe") if sys.platform == "win32" else str(root / "bin" / "node")


HERE = Path(__file__).resolve().parent
PROGRAMS = HERE / "programs"
PY = sys.executable
NODE = _node()


@dataclass(frozen=True, slots=True)
class Program:
    name: str
    argv: tuple[str, ...]
    tool: str | None = None  # системная программа, которая должна быть в PATH (Python-пакеты идут через PY)
    expect_failure: bool = False  # программа должна завершаться с ненулевым кодом (проверка pytest и ruff)
    colored: bool = True  # в выводе должны быть цвета
    input: tuple[Step, ...] = ()  # шаги сценария: строки, клавиши, паузы (только псевдотерминал)
    prompt: str | None = None  # как выглядит приглашение, когда программа ждет ввода
    settle: float = 0.5  # сколько вывод должен молчать перед следующим шагом (0 - для постоянно перерисовываемых)
    snapshot: Snapshot | None = None  # когда снять экран у программы, которая сама не завершается
    external: bool = False  # чужая команда, а не скрипт проекта: тесты на ней лежат в tests/external
    env: Mapping[str, str] = field(default_factory=dict)  # добавки к окружению запуска
    cwd: Path | None = None  # рабочий каталог: пути в выводе (pytest, ruff) не зависят от места проекта на диске
    absent: Mapping[str, str] = field(default_factory=dict)  # sys.platform -> почему программы там не ждем

    @property
    def options(self) -> dict[str, Any]:
        """
        Аргументы ``termsnap.run`` для этой программы (кроме ``argv`` и ``backend``).
        """
        return {
            "cwd": self.cwd,
            "env": {**_without_runner(os.environ), **self.env},
            "input": self.input,
            "prompt": self.prompt,
            "settle": self.settle,
            "snapshot": self.snapshot,
        }


#: Переменные, по которым программы узнают, что работают на CI. С ними pytest показывает полный diff вместо
#: подсказки "Use -v", а другие программы тоже меняют вывод, поэтому снимок на раннере отличался бы от локального.
_RUNNER_VARIABLES = frozenset({"CI", "BUILD_NUMBER", "GITHUB_ACTIONS"})


def _without_runner(env: Mapping[str, str]) -> dict[str, str]:
    return {key: value for key, value in env.items() if key not in _RUNNER_VARIABLES}


def _script(name: str) -> str:
    return str(PROGRAMS / name)


#: Python не пишет кэш байт-кода рядом со скриптами: в нем остаются пути той машины и системы, где его создали.
_QUIET = {"PYTHONDONTWRITEBYTECODE": "1"}

#: Страница читается в less без настроек пользователя: ширина задана, истории и цветов из окружения нет.
_MAN_ENV = {"MANWIDTH": "70", "MANPAGER": "less -R", "LESSHISTFILE": "-", "LESS": "", "MAN_KEEP_FORMATTING": ""}


REGISTRY = [
    Program("rich_table", (PY, _script("rich_table.py"))),
    Program("rich_panel_tree", (PY, _script("rich_panel_tree.py"))),
    Program("rich_syntax", (PY, _script("rich_syntax.py"))),
    Program("rich_markdown", (PY, _script("rich_markdown.py"))),
    Program("rich_traceback", (PY, _script("rich_traceback.py"))),
    Program("rich_progress", (PY, _script("rich_progress.py"))),
    Program("rich_live", (PY, _script("rich_live.py"))),
    Program("rich_misc", (PY, _script("rich_misc.py"))),
    Program("node_inspect", (NODE, _script("node_inspect.js")), external=True),
    Program("node_ansi", (NODE, _script("node_ansi.js")), external=True),
    Program("git_log", (PY, _script("git_history.py")), tool="git", external=True),
    Program(
        "pytest_failure",
        # pytest.ini в каталоге программ: вложенный pytest не читает настройки и conftest.py самих тестов проекта
        (PY, "-m", "pytest", "failing_cases.py", "--color=yes", "-p", "no:cacheprovider", "-q"),
        expect_failure=True,
        external=True,
        cwd=PROGRAMS,
        env=_QUIET,
    ),
    Program(
        "ruff_diagnostics",
        # --isolated: настройки ruff самого проекта (длина строки, правила) не влияют на вывод
        (PY, "-m", "ruff", "check", "--isolated", "--no-cache", "--color=always", "--select", "E,F,I", "bad_style.py"),
        expect_failure=True,
        external=True,
        cwd=PROGRAMS,
    ),
]

#: Программы, которым нужен терминал: в канале они дают бедный или бессмысленный вывод (rich без настроек, вывод
#: абсолютными позициями курсора, вывод длиннее экрана). Запускаются только через ``PtyBackend``.
PTY_REGISTRY = [
    Program("rich_native", (PY, _script("rich_native.py"))),
    Program("full_screen", (PY, _script("full_screen.py"))),
    Program("long_output", (PY, _script("long_output.py"))),
]

#: IPython запускается из окружения проекта (группа ``external`` в pyproject.toml, версия - в uv.lock), без uvx и сети.
#: История держится в памяти, подсказки дня выключены, а каталог настроек отдельный: сессия не зависит от домашнего
#: каталога и не оставляет в нем следов.
_IPYTHON = (
    *(PY, "-m", "IPython", "--no-banner"),
    *("--HistoryManager.hist_file=:memory:", "--TerminalInteractiveShell.enable_tip=False"),
)
_IPYTHON_ENV = {"IPYTHONDIR": str(Path(tempfile.gettempdir()) / "termsnap-ipython")}
_IPYTHON_PROMPT = r"In \[\d+\]:$"

#: Интерактивные программы (REPL): им печатается ввод, поэтому запускаются только через ``PtyBackend``.
INTERACTIVE = [
    Program(
        "mini_repl",
        (PY, _script("mini_repl.py")),
        input=("add 2 3", "slow", "bogus", "fail", "exit"),
        prompt=r">>$",
    ),
    Program(
        "ipython_session",
        _IPYTHON,
        input=(
            "squares = [n ** 2 for n in range(6)]",
            "squares",
            "import math; math.pi",
            "1 / 0",
            "exit",
        ),
        prompt=_IPYTHON_PROMPT,
        external=True,
        env=_IPYTHON_ENV,
    ),
    # стрелка вверх достает прошлую строку из истории, Enter ее повторяет
    Program(
        "ipython_history",
        _IPYTHON,
        input=("6 * 7", Key.UP, Key.ENTER, Pause(1), "exit"),
        prompt=_IPYTHON_PROMPT,
        external=True,
        env=_IPYTHON_ENV,
    ),
    # Tab открывает меню автодополнения (первый раз оно появляется не сразу): снимок ждет его появления
    Program(
        "ipython_complete",
        _IPYTHON,
        input=("import math", Keys("math.s"), Key.TAB),
        prompt=_IPYTHON_PROMPT,
        snapshot=Snapshot(when=r"sqrt", after=0.3),
        external=True,
        env=_IPYTHON_ENV,
    ),
    # программы, которые сами не завершаются: экран снимается в заданный момент, и программа останавливается
    Program(
        "live_monitor",
        (PY, _script("live_monitor.py")),
        input=(Keys("s"), Pause(0.4), Key.DOWN, Pause(0.4), Key.DOWN, Pause(0.4)),
        settle=0,
        snapshot=Snapshot(after=0.5),
    ),
    Program(
        "htop",
        ("htop",),
        tool="htop",
        snapshot=Snapshot(when=r"Tasks:", after=2),
        external=True,
        absent={
            "darwin": "htop не ставится на macOS по умолчанию",
            "win32": "htop есть только в Linux (на Windows под этим именем встречаются другие программы)",
        },
    ),
    Program(
        "top",
        ("top",),
        tool="top",
        snapshot=Snapshot(when=r"PID\s+(USER|COMMAND)", after=1),
        external=True,
        absent={"win32": "в Windows нет top"},
    ),
    # страница руководства читается в less: Page Down листает вперед, поиск находит слово, q выходит
    Program(
        "man_scroll",
        ("man", _script("termsnap-demo.1")),
        tool="man",
        input=(Key.PAGE_DOWN,),
        snapshot=Snapshot(when=r"OPTIONS", after=0.5),
        external=True,
        env=_MAN_ENV,
        absent={"win32": "в Windows нет man"},
    ),
    Program(
        "man_search",
        ("man", _script("termsnap-demo.1")),
        tool="man",
        input=("/needle",),
        snapshot=Snapshot(when=r"The word needle", after=0.5),
        external=True,
        env=_MAN_ENV,
        absent={"win32": "в Windows нет man"},
    ),
    Program(
        "man_quit",
        ("man", _script("termsnap-demo.1")),
        tool="man",
        input=(Keys("q"),),
        external=True,
        env=_MAN_ENV,
        absent={"win32": "в Windows нет man"},
    ),
]

ALL_PROGRAMS = [*REGISTRY, *PTY_REGISTRY, *INTERACTIVE]

#: Скрипты проекта: тесты на них лежат в ``tests/integration``. Чужие команды (``external=True``) проверяются в
#: ``tests/external``.
PROJECT_PROGRAMS = [program for program in ALL_PROGRAMS if not program.external]
EXTERNAL_PROGRAMS = [program for program in ALL_PROGRAMS if program.external]


def require(program: Program) -> None:
    """
    Единственное место, где решается, запускать ли чужую программу на этой системе.

    Программа либо исключена на этой системе (``Program.absent``, причина в таблице ``support_table``): тогда тест
    пропускается и пропуск ожидаем, либо она обязательна: тогда ее отсутствие - ошибка тестов, а не пропуск.
    """
    reason = program.absent.get(sys.platform)
    if reason is not None:
        pytest.skip(f"{EXPECTED_SKIP}: {program.name}: {reason}")
    if program.tool is not None and shutil.which(program.tool) is None:
        pytest.fail(
            f"{program.name}: нужна программа {program.tool!r}, а ее нет в PATH "
            "(Linux: python ci/run.py system-deps; другие системы: установите ее)",
            pytrace=False,
        )


SYSTEMS = {"linux": "Linux", "darwin": "macOS", "win32": "Windows"}


def expected_skips() -> dict[str, str]:
    """
    Программы, которые на этой системе не запускаются, с причинами: ``{"htop": "причина"}``.
    """
    return {p.name: p.absent[sys.platform] for p in ALL_PROGRAMS if sys.platform in p.absent}


def support_table() -> str:
    """
    Что на какой системе запускается: таблица Markdown и под ней причины исключений. Она же записана в README, а тест
    сверяет их, поэтому правится только ``Program.absent``. Программы одной чужой команды (``node_ansi`` и
    ``node_inspect``, три сессии ``ipython_*``) - одна строка по первому слову имени.
    """
    families: dict[str, list[Program]] = {}
    for program in EXTERNAL_PROGRAMS:
        families.setdefault(program.name.split("_")[0], []).append(program)
    rows = [["Программа", *SYSTEMS.values()], ["---"] * (len(SYSTEMS) + 1)]
    reasons: list[str] = []
    for family, programs in families.items():
        absent = {system for system in SYSTEMS if all(system in p.absent for p in programs)}
        rows.append([f"`{family}`", *("нет" if system in absent else "да" for system in SYSTEMS)])
        reasons += [
            f"- `{family}`, {SYSTEMS[system]}: {programs[0].absent[system]}" for system in SYSTEMS if system in absent
        ]
    table = [f"| {' | '.join(row)} |" for row in rows]
    return "\n".join([*table, "", *reasons])
