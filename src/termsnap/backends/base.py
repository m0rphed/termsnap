"""
Общий интерфейс способов запуска команды.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True, kw_only=True)
class Request:
    """
    Что запустить: команда без оболочки, рабочий каталог, полное окружение процесса, предельное время и размер
    терминала (канал его не использует, но псевдотерминалу он нужен).
    """

    argv: tuple[str, ...]
    env: Mapping[str, str]
    cwd: Path | None = None
    timeout: float | None = None
    columns: int = 100
    rows: int = 30


@dataclass(frozen=True, slots=True)
class RawResult:
    """
    Результат запуска: все, что процесс вывел (стандартный вывод и ошибки вместе, как в терминале), код возврата
    и длительность в секундах.
    """

    output: bytes
    returncode: int
    duration: float


class Backend(Protocol):
    """
    Способ запуска команды. Реализации: ``PipeBackend`` (каналы).
    """

    def run(self, request: Request) -> RawResult:
        """
        Запускает команду и ждет завершения; при превышении времени останавливает процесс и бросает ``RunTimeout``.
        """
        ...
