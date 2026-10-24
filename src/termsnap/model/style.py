"""
Оформление фрагмента текста.
"""

from dataclasses import dataclass

from termsnap.model.color import Color


@dataclass(frozen=True, slots=True, kw_only=True)
class Style:
    """
    Оформление фрагмента текста. ``fg`` и ``bg`` равны ``None``, если цвет не задан (цвет по умолчанию темы).
    """

    fg: Color | None = None
    bg: Color | None = None
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    inverse: bool = False


#: Стиль по умолчанию: ничего не задано.
PLAIN = Style()
