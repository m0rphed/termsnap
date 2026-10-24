"""
Бэкенд псевдотерминала: общая часть для всех платформ.
"""

import sys
import time
from dataclasses import replace

from termsnap.backends.executable import find_executable
from termsnap.model import Line
from termsnap.request import RawResult, Request


class PtyBackend:
    """
    Программа считает, что работает в терминале (``isatty()`` истинно, размер известен), поэтому сама включает цвет,
    рисует индикаторы выполнения и перерисовывает экран. Вывод читается как поток терминала и превращается в
    картину экрана эмулятором ``pyte`` (``termsnap.screen``): работают абсолютные позиции курсора, прокрутка и
    стирание, а длинный вывод не теряется.

    Нужен дополнительный пакет: ``pip install termsnap[pty]`` (``pyte``, а в Windows еще ``pywinpty``). В Windows
    используется ConPTY, в Linux и macOS - ``pty`` из стандартной библиотеки. Программам, ждущих ответа
    пользователя, ввод подается по сценарию (``Request.input``). Стандартный вывод и вывод ошибок в терминале
    общие, порядок сохраняется.
    """

    def run(self, request: Request) -> RawResult:
        executable = find_executable(request)
        request = _with_truecolor(request)
        started = time.perf_counter()
        if sys.platform == "win32":
            from termsnap.backends.pty import conpty

            output, code, stopped = conpty.run(executable, request)
        else:
            from termsnap.backends.pty import posix

            output, code, stopped = posix.run(executable, request)
        return RawResult(output, code, time.perf_counter() - started, stopped)

    def interpret(self, output: bytes, request: Request, encoding: str) -> tuple[Line, ...]:
        from termsnap.screen import render

        return render(
            output.decode(encoding, errors="replace"),
            columns=request.columns,
            rows=request.rows,
            visible_only=request.capture_visible_only,
        )


def _with_truecolor(request: Request) -> Request:
    """
    Настоящий терминал сообщает о 24-битном цвете переменной ``COLORTERM``: ее и добавляем, если не задана.
    """
    if "COLORTERM" in request.env:
        return request
    return replace(request, env={**request.env, "COLORTERM": "truecolor"})
