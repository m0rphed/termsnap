"""
Готовые темы.
"""

from termsnap.model import Rgb
from termsnap.theme.theme import Theme


def _palette(*codes: str) -> tuple[Rgb, ...]:
    return tuple(Rgb.from_hex(code) for code in codes)


#: Темная тема в духе встроенного терминала VS Code.
DARK = Theme(
    name="dark",
    foreground=Rgb(0xCC, 0xCC, 0xCC),
    background=Rgb(0x1E, 0x1E, 0x1E),
    ansi=_palette(
        "000000", "cd3131", "0dbc79", "e5e510", "2472c8", "bc3fbc", "11a8cd", "e5e5e5",
        "666666", "f14c4c", "23d18b", "f5f543", "3b8eea", "d670d6", "29b8db", "e5e5e5",
    ),
)  # fmt: skip

#: Светлая тема: темный текст на белом фоне, цвета подобраны так, чтобы читаться на белом.
LIGHT = Theme(
    name="light",
    foreground=Rgb(0x33, 0x33, 0x33),
    background=Rgb(0xFF, 0xFF, 0xFF),
    ansi=_palette(
        "000000", "cd3131", "00bc00", "949800", "0451a5", "bc05bc", "0598bc", "555555",
        "666666", "cd3131", "14ce14", "b5ba00", "0451a5", "bc05bc", "0598bc", "a5a5a5",
    ),
)  # fmt: skip
