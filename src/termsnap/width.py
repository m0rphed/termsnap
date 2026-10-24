"""
Ширина текста в клетках терминала: обычные символы занимают одну клетку, иероглифы и эмодзи две, комбинируемые
знаки ни одной.

Используется только стандартная библиотека (``unicodedata``), поэтому результат приближенный: он совпадает с
современными терминалами для латиницы, кириллицы, псевдографики, иероглифов и эмодзи (в том числе с селектором
``U+FE0F``), но не знает всех особенностей конкретного терминала.

Единица подсчета - не символ, а "клеточная группа" (``clusters``): символ вместе со знаками, которые к нему
присоединяются. Терминал выделяет под группу целое число клеток, и в эти же клетки рисует ее PNG-бэкенд.
"""

import unicodedata
from collections.abc import Iterator

#: Соединитель нулевой ширины: склеивает эмодзи в один знак (семья, флаг с оттенком кожи и т.п.).
ZERO_WIDTH_JOINER = "\N{ZERO WIDTH JOINER}"

#: Селектор начертания 16: просит показать предыдущий знак как цветной эмодзи (обычно в две клетки).
EMOJI_SELECTOR = "\N{VARIATION SELECTOR-16}"

#: Селектор начертания 15: просит показать предыдущий знак как обычный текстовый символ (одна клетка).
TEXT_SELECTOR = "\N{VARIATION SELECTOR-15}"

#: Категории Unicode знаков, которые не занимают клетки сами: Mn - диакритика, Me - охватывающие знаки,
#: Cf - форматирующие (селекторы начертания, соединитель нулевой ширины и т.п.).
_ZERO_WIDTH_CATEGORIES = frozenset({"Mn", "Me", "Cf"})

#: Классы ширины East Asian Width, которые занимают две клетки: W (wide) и F (fullwidth).
_DOUBLE_WIDTH_CLASSES = frozenset({"W", "F"})


def _is_combining(char: str) -> bool:
    """
    Знак, который не занимает клетки сам и присоединяется к предыдущему символу.
    """
    return unicodedata.category(char) in _ZERO_WIDTH_CATEGORIES


def clusters(text: str) -> Iterator[str]:
    """
    Делит текст на клеточные группы: символ вместе с присоединяемыми к нему знаками; после соединителя нулевой
    ширины (составные эмодзи) в группу входит и следующий символ.
    """
    current = ""
    join_next = False  # прошлым был соединитель: следующий символ войдет в группу, даже если он обычный
    for char in text:
        if current and (join_next or _is_combining(char)):
            join_next = char == ZERO_WIDTH_JOINER
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
    Сколько клеток занимает группа из ``clusters``: 0, 1 или 2. Правила по порядку: группа без основы (одни
    комбинируемые знаки) - 0; широкая основа (иероглиф, эмодзи) - 2; текстовый селектор - 1; эмодзи-селектор или
    соединитель делают эмодзи даже из узкого знака (например, предупреждающего) - 2; иначе 1.
    """
    base = cluster[0]
    if _is_combining(base):
        return 0
    if unicodedata.east_asian_width(base) in _DOUBLE_WIDTH_CLASSES:
        return 2
    if TEXT_SELECTOR in cluster:
        return 1
    if EMOJI_SELECTOR in cluster or ZERO_WIDTH_JOINER in cluster:
        return 2
    return 1


def text_width(text: str) -> int:
    """
    Ширина текста в клетках.
    """
    return sum(cluster_width(cluster) for cluster in clusters(text))
