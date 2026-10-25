"""
Помощники для проверок разобранного вывода: текст строк и стили фрагментов.
"""

from termsnap import Capture, Style


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
