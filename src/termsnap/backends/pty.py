"""
Запуск в псевдотерминале: программа видит настоящий терминал нужного размера.
"""

import shutil
import sys
import time
from dataclasses import replace

from termsnap.backends.base import RawResult, Request
from termsnap.model import Line


class PtyBackend:
    """
    Программа считает, что работает в терминале (``isatty()`` истинно, размер известен), поэтому сама включает цвет,
    рисует индикаторы выполнения и перерисовывает экран. Вывод читается как поток терминала и превращается в
    картину экрана эмулятором ``pyte`` (``termsnap.screen``): работают абсолютные позиции курсора, прокрутка и
    стирание, а длинный вывод не теряется.

    Нужен дополнительный пакет: ``pip install termsnap[pty]`` (``pyte``, а в Windows еще ``pywinpty``). В Windows
    используется ConPTY, в Linux и macOS - ``pty`` из стандартной библиотеки. Ввода нет: программы, ждущие ответа
    пользователя, не запустить. Стандартный вывод и вывод ошибок в терминале общие, порядок сохраняется.
    """

    def run(self, request: Request) -> RawResult:
        executable = shutil.which(request.argv[0], path=request.env.get("PATH"))
        if executable is None:
            raise FileNotFoundError(f"программа {request.argv[0]!r} не найдена в PATH")
        request = _with_truecolor(request)
        started = time.perf_counter()
        if sys.platform == "win32":
            from termsnap.backends import _conpty

            output, code, stopped = _conpty.run(executable, request)
        else:
            from termsnap.backends import _posix_pty

            output, code, stopped = _posix_pty.run(executable, request)
        return RawResult(output, code, time.perf_counter() - started, stopped)

    def interpret(self, output: bytes, request: Request, encoding: str) -> tuple[Line, ...]:
        from termsnap import screen

        return screen.render(output.decode(encoding, errors="replace"), columns=request.columns, rows=request.rows)


def _with_truecolor(request: Request) -> Request:
    """
    Настоящий терминал сообщает о 24-битном цвете переменной ``COLORTERM``: ее и добавляем, если не задана.
    """
    if "COLORTERM" in request.env:
        return request
    return replace(request, env={**request.env, "COLORTERM": "truecolor"})
