"""
Набор начертаний одного семейства.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from termsnap.png.fonts.face import Face


@dataclass(frozen=True, slots=True)
class FontSet:
    """
    Начертания одного семейства: обычное обязательно, остальные - если установлены.
    """

    family: str
    regular: Face
    bold: Face | None = None
    italic: Face | None = None
    bold_italic: Face | None = None

    @classmethod
    def from_faces(cls, faces: Iterable[Face]) -> "FontSet | None":
        """
        Раскладывает начертания по ролям (жирное, курсивное); если на одну роль претендуют несколько, берется самое
        "основное" (см. ``Face.rank``). ``None``, если нет обычного начертания.
        """
        best: dict[tuple[bool, bool], Face] = {}  # (жирное, курсивное) -> лучшее начертание этой роли
        for face in faces:
            role = (face.bold, face.italic)
            if role not in best or face.rank < best[role].rank:
                best[role] = face
        regular = best.get((False, False))
        if regular is None:
            return None
        return cls(regular.family, regular, best.get((True, False)), best.get((False, True)), best.get((True, True)))

    def pick(self, *, bold: bool, italic: bool) -> tuple[Face, bool]:
        """
        Начертание для сочетания "жирный/курсив" и признак того, что жирность придется имитировать (нужного
        начертания в семействе нет). Отсутствующий курсив не имитируется: берется прямое начертание.

            жирный курсив -> bold_italic, иначе bold, иначе italic, иначе regular
            жирный        -> bold, иначе regular
            курсив        -> italic, иначе regular
            обычный       -> regular
        """
        if bold and italic:
            candidates = (self.bold_italic, self.bold, self.italic, self.regular)
        elif bold:
            candidates = (self.bold, self.regular)
        elif italic:
            candidates = (self.italic, self.regular)
        else:
            candidates = (self.regular,)
        face = next(candidate for candidate in candidates if candidate is not None)
        return face, bold and not face.bold
