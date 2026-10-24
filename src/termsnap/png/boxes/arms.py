"""
Из чего состоит символ рамки: какие "рукава" идут от центра клетки и какой они толщины.
"""

import unicodedata
from dataclasses import dataclass
from functools import cache

from termsnap.png.boxes.ranges import BOX_DRAWINGS

#: Толщины рукава в ``Arms``: нет рукава, тонкий, толстый, двойной (две параллельные линии).
NONE, THIN, HEAVY, DOUBLE = 0, 1, 2, 3

#: Слово толщины в названии символа Unicode -> толщина: LIGHT и SINGLE - тонкая, HEAVY - толстая, DOUBLE - двойная.
WEIGHTS = {"LIGHT": THIN, "SINGLE": THIN, "HEAVY": HEAVY, "DOUBLE": DOUBLE}

#: Слова названия, которые задают направления: VERTICAL - это сразу вверх и вниз, HORIZONTAL - влево и вправо.
_DIRECTIONS = {
    "UP": ("up",),
    "DOWN": ("down",),
    "LEFT": ("left",),
    "RIGHT": ("right",),
    "VERTICAL": ("up", "down"),
    "HORIZONTAL": ("left", "right"),
}

#: Слова штриховых линий (``BOX DRAWINGS LIGHT TRIPLE DASH HORIZONTAL``). Штриховые линии рисуются сплошными. Здесь
#: DOUBLE значит "две черточки", а не "двойная линия", поэтому в штриховых названиях его нужно убрать до разбора толщин.
_DASH_WORDS = frozenset({"DOUBLE", "TRIPLE", "QUADRUPLE", "DASH"})

_NAME_PREFIX = "BOX DRAWINGS "
_PARTS_SEPARATOR = " AND "


@dataclass(frozen=True, slots=True)
class Arms:
    """
    Рукава символа рамки от центра клетки: толщина каждого (0 - нет, 1 - тонкая, 2 - толстая, 3 - двойная).
    ``arc`` - угол скругленный.
    """

    up: int = NONE
    down: int = NONE
    left: int = NONE
    right: int = NONE
    arc: bool = False


@cache
def arms_of(char: str) -> Arms | None:
    """
    Рукава символа рамки по его названию Unicode; ``None`` для остальных символов и для диагоналей.

        "BOX DRAWINGS LIGHT DOWN AND HEAVY RIGHT"
            -> части "LIGHT DOWN" и "HEAVY RIGHT"
            -> вниз тонкий (1), вправо толстый (2)
        часть без слова толщины ("UP AND HEAVY RIGHT" -> "UP") берет первую найденную толщину
        "ARC" ставит arc=True и в разборе не участвует; штриховые слова отбрасываются
    """
    if len(char) != 1 or ord(char) not in BOX_DRAWINGS:
        return None
    words = unicodedata.name(char, "").removeprefix(_NAME_PREFIX).split()
    if "DIAGONAL" in words:
        return None
    arc = "ARC" in words
    words = [word for word in words if word != "ARC"]
    if "DASH" in words:
        words = [word for word in words if word not in _DASH_WORDS]
    parts = [part.split() for part in " ".join(words).split(_PARTS_SEPARATOR)]
    weights = [next((WEIGHTS[word] for word in part if word in WEIGHTS), None) for part in parts]
    default = next((weight for weight in weights if weight is not None), THIN)
    result = {"up": NONE, "down": NONE, "left": NONE, "right": NONE}
    for part, weight in zip(parts, weights, strict=True):
        for word in part:
            for direction in _DIRECTIONS.get(word, ()):
                result[direction] = weight or default
    return Arms(**result, arc=arc)
