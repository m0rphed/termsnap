"""
Помощники для проверок разобранного вывода: текст строк и стили фрагментов.
"""

from termsnap import Capture, Line, Style


def rstripped(capture: Capture) -> list[str]:
    """
    Строки вывода без пробелов справа (rich дополняет пробелами фон блоков до всей ширины).
    """
    return [line.text.rstrip() for line in capture.lines]


def styles_by_text(capture: Capture) -> dict[str, Style]:
    """
    Стиль каждого фрагмента вывода по его тексту (без пробелов по краям; пустые фрагменты не берутся).
    """
    return {span.text.strip(): span.style for line in capture.lines for span in line.spans if span.text.strip()}


def control_characters(text: str) -> list[str]:
    """
    Управляющие символы, которые не должны попадать в текст разобранного вывода: ESC, возврат каретки, звонок, NUL.
    """
    return sorted({char for char in text if char in "\x1b\r\x07\x00"})


def styled(lines: tuple[Line, ...]) -> bool:
    """
    Есть ли в строках хоть какое-то оформление (цвет, фон, жирность, курсив).
    """
    return any(
        span.style.fg is not None or span.style.bg is not None or span.style.bold or span.style.italic
        for line in lines
        for span in line.spans
    )
