"""
Набор настоящих программ с нетривиальным цветным выводом: на нем проверяются разбор ANSI и рисование в PNG.

Каждая запись - команда и каталог запуска. Программы лежат в ``programs`` (скрипты rich и Node.js, образцы для pytest и
ruff); если нужного инструмента нет в системе, запись пропускается (``available``).
"""

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

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

    @property
    def available(self) -> bool:
        return self.tool is None or shutil.which(self.tool) is not None


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
    Program("node_inspect", ("node", _script("node_inspect.js")), tool="node"),
    Program("node_ansi", ("node", _script("node_ansi.js")), tool="node"),
    Program(
        "pytest_failure",
        (PY, "-m", "pytest", _script("sample_failing_test.py"), "--color=yes", "-p", "no:cacheprovider", "-q"),
        expect_failure=True,
    ),
    Program(
        "ruff_diagnostics",
        (PY, "-m", "ruff", "check", _script("bad_style.py"), "--color=always", "--no-cache", "--select", "E,F,I"),
        expect_failure=True,
    ),
    Program(
        "git_log",
        ("git", "-C", str(HERE.parent), "log", "--oneline", "--graph", "--color=always", "-n", "5"),
        tool="git",
    ),
]
