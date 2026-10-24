"""
Итог запуска для пользователя библиотеки: разобранный вывод вместе с обстоятельствами запуска.
"""

from dataclasses import dataclass

from termsnap.defaults import DEFAULT_COLUMNS, DEFAULT_ROWS
from termsnap.model import Line


@dataclass(frozen=True, slots=True)
class Capture:
    """
    Результат запуска: команда, код возврата, длительность, исходные байты и разобранные строки со стилями.
    ``columns`` и ``rows`` - размер терминала, в котором запускалась команда (у канала он условный): по нему
    рисуется окно целиком, а не только занятая выводом часть. ``stopped`` - программа не завершилась сама, ее
    остановили в момент снимка (``snapshot``), и ``returncode`` в этом случае ничего не значит. Ширина строк везде
    считается в клетках терминала (``termsnap.width``): так же ее считает эмулятор экрана, поэтому столбцы совпадают
    с настоящим терминалом.
    """

    argv: tuple[str, ...]
    returncode: int
    duration: float
    output: bytes
    lines: tuple[Line, ...]
    columns: int = DEFAULT_COLUMNS
    rows: int = DEFAULT_ROWS
    stopped: bool = False

    @property
    def ok(self) -> bool:
        """
        Запуск прошел как задумано: программа завершилась с кодом 0 или ее остановили по ``snapshot``.
        """
        return self.stopped or self.returncode == 0

    @property
    def text(self) -> str:
        """
        Вывод без оформления: строки через ``\\n``.
        """
        return "\n".join(line.text for line in self.lines)
