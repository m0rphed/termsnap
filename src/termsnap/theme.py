"""
Тема: какими RGB-цветами показываются цвета палитры терминала и цвета по умолчанию.
"""

from dataclasses import dataclass

from termsnap.model import Color, Indexed, Rgb, Style

#: Уровни канала в кубе 6x6x6 расширенной палитры xterm (индексы 16-231).
_CUBE_LEVELS = (0, 95, 135, 175, 215, 255)


@dataclass(frozen=True, slots=True)
class Theme:
    """
    Цвет текста и фона по умолчанию и 16 базовых цветов палитры (8 обычных и 8 ярких).
    """

    foreground: Rgb
    background: Rgb
    ansi: tuple[Rgb, ...]

    def __post_init__(self) -> None:
        if len(self.ansi) != 16:
            raise ValueError(f"в теме должно быть 16 базовых цветов, получено {len(self.ansi)}")

    def resolve(self, color: Color) -> Rgb:
        """
        RGB-значение цвета: цвета 0-15 берутся из темы, 16-255 вычисляются по правилам xterm.
        """
        match color:
            case Rgb():
                return color
            case Indexed(index) if index < 16:
                return self.ansi[index]
            case Indexed(index) if index < 232:
                cube = index - 16
                red, green, blue = cube // 36, cube // 6 % 6, cube % 6
                return Rgb(_CUBE_LEVELS[red], _CUBE_LEVELS[green], _CUBE_LEVELS[blue])
            case Indexed(index):
                level = 8 + 10 * (index - 232)
                return Rgb(level, level, level)

    def colors_of(self, style: Style) -> tuple[Rgb, Rgb]:
        """
        Итоговые цвета текста и фона для стиля с учетом цветов по умолчанию и обращенного вывода (``inverse``).
        """
        foreground = self.foreground if style.fg is None else self.resolve(style.fg)
        background = self.background if style.bg is None else self.resolve(style.bg)
        return (background, foreground) if style.inverse else (foreground, background)


def _rgb(*codes: str) -> tuple[Rgb, ...]:
    return tuple(Rgb(int(code[0:2], 16), int(code[2:4], 16), int(code[4:6], 16)) for code in codes)


#: Тёмная тема в духе встроенного терминала VS Code.
DARK = Theme(
    foreground=Rgb(0xCC, 0xCC, 0xCC),
    background=Rgb(0x1E, 0x1E, 0x1E),
    ansi=_rgb(
        "000000", "cd3131", "0dbc79", "e5e510", "2472c8", "bc3fbc", "11a8cd", "e5e5e5",
        "666666", "f14c4c", "23d18b", "f5f543", "3b8eea", "d670d6", "29b8db", "e5e5e5",
    ),
)  # fmt: skip

#: Светлая тема: тёмный текст на белом фоне, цвета подобраны так, чтобы читаться на белом.
LIGHT = Theme(
    foreground=Rgb(0x33, 0x33, 0x33),
    background=Rgb(0xFF, 0xFF, 0xFF),
    ansi=_rgb(
        "000000", "cd3131", "00bc00", "949800", "0451a5", "bc05bc", "0598bc", "555555",
        "666666", "cd3131", "14ce14", "b5ba00", "0451a5", "bc05bc", "0598bc", "a5a5a5",
    ),
)  # fmt: skip
