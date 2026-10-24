"""
Общий интерфейс способов запуска команды.
"""

from typing import Protocol

from termsnap.model import Line
from termsnap.request import RawResult, Request


class Backend(Protocol):
    """
    Способ запуска команды. Реализации: ``PipeBackend`` (каналы) и ``PtyBackend`` (псевдотерминал).
    """

    def run(self, request: Request) -> RawResult:
        """
        Запускает команду и ждет завершения; при превышении времени останавливает процесс и бросает ``RunTimeout``.
        """
        ...

    def interpret(self, output: bytes, request: Request, encoding: str) -> tuple[Line, ...]:
        """
        Строки со стилями из того, что вывела программа: каждый способ запуска знает, как читать свой вывод (из
        канала приходит поток для построчного разбора, из псевдотерминала - картина экрана).
        """
        ...
