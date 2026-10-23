"""
Запуск команды и разбор ее вывода: главная функция библиотеки - ``run``.
"""

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from termsnap.backends import Backend, PipeBackend, Request
from termsnap.model import Line

#: Переменные, по которым программы включают цвет без терминала (Node.js, Python, git, ls и многие другие).
_COLOR_ON = {"FORCE_COLOR": "1", "CLICOLOR_FORCE": "1"}


@dataclass(frozen=True, slots=True)
class Capture:
    """
    Результат запуска: команда, код возврата, длительность, исходные байты и разобранные строки со стилями.
    ``columns`` и ``rows`` - размер терминала, в котором запускалась команда (у канала он условный): по нему
    рисуется окно целиком, а не только занятая выводом часть. Ширина строк везде считается в клетках терминала
    (``termsnap.width``): так же ее считает эмулятор экрана, поэтому столбцы совпадают с настоящим терминалом.
    """

    argv: tuple[str, ...]
    returncode: int
    duration: float
    output: bytes
    lines: tuple[Line, ...]
    columns: int = 100
    rows: int = 30

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def text(self) -> str:
        """
        Вывод без оформления: строки через ``\\n``.
        """
        return "\n".join(line.text for line in self.lines)


def terminal_environment(
    base: Mapping[str, str], *, color: bool, columns: int, rows: int, term: str = "xterm-256color"
) -> dict[str, str]:
    """
    Окружение «как у терминала»: тип и размер терминала, UTF-8 для Python, цвет включен или выключен принудительно.
    Из ``base`` убираются ``NO_COLOR`` и прежние ``FORCE_COLOR``/``CLICOLOR_FORCE``, чтобы цвет зависел только от
    аргумента ``color``.
    """
    env = {key: value for key, value in base.items() if key not in {"NO_COLOR", *_COLOR_ON}}
    env |= {"TERM": term, "COLUMNS": str(columns), "LINES": str(rows), "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    if color:
        env |= _COLOR_ON
    else:
        env["NO_COLOR"] = "1"
    return env


def run(
    argv: Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float | None = 30.0,
    color: bool = True,
    columns: int = 100,
    rows: int = 30,
    encoding: str = "utf-8",
    backend: Backend | None = None,
) -> Capture:
    """
    Запускает команду (без оболочки: ``["node", "app.js"]``) и возвращает ее вывод со стилями.

    ``env`` - окружение процесса целиком (по умолчанию окружение текущего процесса); цвет включается или выключается
    через ``color`` (см. ``terminal_environment``). ``encoding`` - кодировка вывода программы; нераспознанные байты
    заменяются символом подстановки. По умолчанию команда запускается через каналы (``PipeBackend``); для программ,
    которым нужен терминал, есть ``PtyBackend``.
    """
    command = tuple(argv)
    if not command:
        raise ValueError("команда пуста")
    request = Request(
        argv=command,
        env=terminal_environment(os.environ if env is None else env, color=color, columns=columns, rows=rows),
        cwd=None if cwd is None else Path(cwd),
        timeout=timeout,
        columns=columns,
        rows=rows,
    )
    backend = backend or PipeBackend()
    result = backend.run(request)
    lines = backend.interpret(result.output, request, encoding)
    return Capture(command, result.returncode, result.duration, result.output, lines, columns, rows)
