"""
Мелкие помощники, общие для тестов: запуск Python-кода, текст строк, часто нужные символы.
"""

import sys
from collections.abc import Iterable

from termsnap import Capture, Line

ESC = "\x1b"

#: Селектор эмодзи-начертания: символ перед ним рисуется как цветной эмодзи в две клетки.
VS16 = chr(0xFE0F)

#: Соединитель нулевой ширины: склеивает эмодзи в одну картинку (семья, флаг с цветом).
ZWJ = chr(0x200D)

#: Первые восемь байт любого файла PNG.
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def python(code: str) -> list[str]:
    """
    Команда, которая выполняет ``code`` тем же интерпретатором, что и тесты.
    """
    return [sys.executable, "-c", code]


def texts(source: Capture | Iterable[Line]) -> list[str]:
    """
    Текст каждой строки вывода (``Capture`` или строки из него).
    """
    lines = source.lines if isinstance(source, Capture) else source
    return [line.text for line in lines]
