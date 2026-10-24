"""
Одно начертание шрифта: что о нем известно из файла.
"""

import re
from dataclasses import dataclass
from pathlib import Path

#: Слова стиля, которые определяют роль начертания (жирное, курсивное), а не его "основность".
_EMPHASIS_WORDS = frozenset({"bold", "italic", "oblique"})

#: Что остается в стиле после отбрасывания слов из ``_EMPHASIS_WORDS``, и насколько это "основное" начертание своей
#: роли: чем меньше число, тем основнее. Пустой остаток ("Regular", "Bold") - 0.
_CORE_RANK = {"regular": 0, "book": 1, "normal": 1, "roman": 1, "medium": 2}

#: Ранг начертания, чей остаток стиля не в таблице ("Light", "ExtraBold", "Condensed"): уступает всем известным.
_UNKNOWN_RANK = 9


def _style_words(style: str) -> set[str]:
    """
    Слова стиля в нижнем регистре: "Bold Italic" и "Bold-Italic" -> {"bold", "italic"}.
    """
    return set(re.split(r"[\s_-]+", style.casefold()))


@dataclass(frozen=True, slots=True)
class Face:
    """
    Одно начертание: семейство, стиль ("Regular", "Bold Italic"), файл и номер шрифта в файле-коллекции.
    """

    family: str
    style: str
    path: Path
    index: int = 0

    @property
    def bold(self) -> bool:
        return "bold" in _style_words(self.style)

    @property
    def italic(self) -> bool:
        return bool({"italic", "oblique"} & _style_words(self.style))

    @property
    def rank(self) -> int:
        """
        Насколько стиль похож на "основной" своей роли (0 - точно Regular, Bold, Italic или Bold Italic).

            core = слова стиля без bold/italic/oblique;  "Bold Italic" -> пусто, "Medium Italic" -> "medium"
            пусто -> 0;  "regular" -> 0;  "book", "normal", "roman" -> 1;  "medium" -> 2;  остальное -> 9

        Так среди нескольких начертаний одной роли побеждает самое обычное, а "Light" или "ExtraBold" уступают всем.
        """
        core = " ".join(sorted(_style_words(self.style) - _EMPHASIS_WORDS - {""}))
        return 0 if not core else _CORE_RANK.get(core, _UNKNOWN_RANK)
