"""
Ширина текста в клетках терминала: обычные символы занимают одну клетку, иероглифы и эмодзи две, комбинируемые
знаки ни одной.

Используется только стандартная библиотека (``unicodedata``), поэтому результат приближенный: он совпадает с
современными терминалами для латиницы, кириллицы, псевдографики, иероглифов и эмодзи (в том числе с селектором
``U+FE0F``), но не знает всех особенностей конкретного терминала.
"""

import unicodedata
from collections.abc import Iterator

_ZWJ = "\u200d"
_EMOJI_SELECTOR = "\ufe0f"
_TEXT_SELECTOR = "\ufe0e"


def _combining(char: str) -> bool:
    """
    Знак, который не занимает клетки сам и присоединяется к предыдущему символу (диакритика, селекторы
    начертания, соединитель нулевой ширины и другие форматирующие символы).
    """
    return unicodedata.category(char) in {"Mn", "Me", "Cf"}


def clusters(text: str) -> Iterator[str]:
    """
    Делит текст на «клеточные» группы: символ вместе с присоединяемыми к нему знаками; после соединителя нулевой
    ширины (составные эмодзи) в группу входит и следующий символ.
    """
    current = ""
    join_next = False
    for char in text:
        if current and (join_next or _combining(char)):
            join_next = char == _ZWJ
            current += char
            continue
        if current:
            yield current
        current = char
        join_next = False
    if current:
        yield current


def cluster_width(cluster: str) -> int:
    """
    Сколько клеток занимает группа из ``clusters``: 0, 1 или 2.
    """
    base = cluster[0]
    if _combining(base):
        return 0
    if unicodedata.east_asian_width(base) in {"W", "F"}:
        return 2
    if _TEXT_SELECTOR in cluster:
        return 1
    if _EMOJI_SELECTOR in cluster or _ZWJ in cluster:
        return 2  # эмодзи-начертание знака, который сам по себе узкий (например, предупреждающий знак)
    return 1


def text_width(text: str) -> int:
    """
    Ширина текста в клетках.
    """
    return sum(cluster_width(cluster) for cluster in clusters(text))
