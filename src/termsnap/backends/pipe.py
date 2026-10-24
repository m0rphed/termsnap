"""
Запуск через каналы: стандартные вывод и ошибки читаются из одного канала, ввода нет.
"""

import subprocess
import time

from termsnap.ansi import parse
from termsnap.backends.executable import find_executable
from termsnap.errors import RunTimeout
from termsnap.model import Line
from termsnap.request import RawResult, Request


class PipeBackend:
    """
    Самый переносимый способ: только стандартная библиотека, одинаково работает в Windows, Linux и macOS.

    Процесс не видит терминала (``isatty()`` ложно), поэтому цветной вывод включается переменными окружения
    (``FORCE_COLOR`` и подобными), см. ``termsnap.run``. Интерактивные программы и программы, управляющие экраном,
    так не запустить: им нужен псевдотерминал.
    """

    def run(self, request: Request) -> RawResult:
        if request.input or request.snapshot is not None or request.capture_visible_only:
            raise ValueError(
                "PipeBackend не умеет вводить текст, снимать экран и выбирать видимую часть: нужен PtyBackend"
            )
        executable = find_executable(request)
        started = time.perf_counter()
        with subprocess.Popen(
            [executable, *request.argv[1:]],
            cwd=request.cwd,
            env=dict(request.env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # ошибки в тот же канал: порядок строк как в терминале
        ) as process:
            try:
                output, _ = process.communicate(timeout=request.timeout)
            except subprocess.TimeoutExpired as expired:
                process.kill()
                output, _ = process.communicate()  # то, что успело появиться, отдаем вместе с ошибкой
                assert request.timeout is not None
                raise RunTimeout(request.argv, request.timeout, output) from expired
        return RawResult(output, process.returncode, time.perf_counter() - started)

    def interpret(self, output: bytes, request: Request, encoding: str) -> tuple[Line, ...]:
        return parse(output.decode(encoding, errors="replace"))
