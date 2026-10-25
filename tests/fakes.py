"""
Подставные источники сведений, чтобы тесты не зависели от того, что установлено на машине.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path

from termsnap.png.fonts import Face, FontSet


class InstalledFonts:
    """
    "Установленные" семейства шрифтов без файлов: передается в ``resolve*`` параметрами ``lookup`` и ``missing_of``.

        fake = InstalledFonts(["Rich", "Poor"], lacking={"Poor": "Ж"})
        resolve(["Poor", "Rich"], covers="Ж", lookup=fake.lookup, missing_of=fake.missing_of)   # Rich

    ``lacking`` - каких символов не хватает в семействе; ``asked`` - какие семейства спрашивали и в каком порядке.
    """

    def __init__(self, installed: Sequence[str], lacking: Mapping[str, str] | None = None) -> None:
        self.fontsets: dict[str, FontSet] = {}
        for family in installed:
            fontset = FontSet.from_faces([Face(family, "Regular", Path(f"{family}.ttf"))])
            assert fontset is not None
            self.fontsets[family] = fontset
        self.lacking = dict(lacking or {})
        self.asked: list[str] = []

    def lookup(self, family: str) -> FontSet | None:
        self.asked.append(family)
        return self.fontsets.get(family)

    def missing_of(self, face: Face, chars: str) -> str:
        return "".join(char for char in chars if char in self.lacking.get(face.family, ""))
