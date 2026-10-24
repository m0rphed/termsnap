"""
Описание запуска (что и как запустить) и сырой результат (что получилось).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from termsnap.defaults import DEFAULT_COLUMNS, DEFAULT_ROWS, DEFAULT_SETTLE
from termsnap.scenario import Snapshot, Step


@dataclass(frozen=True, slots=True, kw_only=True)
class Request:
    """
    Что запустить: команда без оболочки, рабочий каталог, полное окружение процесса, предельное время и размер
    терминала (канал его не использует, но псевдотерминалу он нужен).

    Сценарий (только псевдотерминал): ``input`` - шаги (строки с Enter, клавиши, паузы, см. ``termsnap.scenario``),
    ``settle`` - сколько секунд вывод должен молчать перед следующим шагом, ``prompt`` - регулярное выражение для
    последней непустой строки экрана (без хвостовых пробелов), которое должно совпасть, пока программа ждет
    очередную строку, ``snapshot`` - когда снять экран у программы, которая сама не завершается.

    ``capture_visible_only`` (только псевдотерминал): взять только то, что видно на экране в конце, без строк,
    ушедших вверх при прокрутке (по умолчанию они сохраняются, чтобы не терять длинный вывод).
    """

    argv: tuple[str, ...]
    env: Mapping[str, str]
    cwd: Path | None = None
    timeout: float | None = None
    columns: int = DEFAULT_COLUMNS
    rows: int = DEFAULT_ROWS
    input: tuple[Step, ...] = ()
    prompt: str | None = None
    settle: float = DEFAULT_SETTLE
    snapshot: Snapshot | None = None
    capture_visible_only: bool = False


@dataclass(frozen=True, slots=True)
class RawResult:
    """
    Результат запуска: все, что процесс вывел (стандартный вывод и ошибки вместе, как в терминале), код возврата
    и длительность в секундах. ``stopped`` - программу остановили по ``Request.snapshot``, она сама не завершилась.
    """

    output: bytes
    returncode: int
    duration: float
    stopped: bool = False
