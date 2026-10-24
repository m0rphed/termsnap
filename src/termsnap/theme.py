"""
Тема: какими RGB-цветами показываются цвета палитры терминала и цвета по умолчанию.

Своя тема собирается от готовой (``DARK.derive(background="#101010", ansi={"red": "#ff5555"})``) или из словаря
(``Theme.from_mapping``), а ``get_theme`` приводит к ``Theme`` все способы ее задать: саму тему, имя из ``THEMES``
или словарь. Поэтому код, который только передает тему дальше, может принимать любой из них (``ThemeSpec``).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from termsnap.model import Color, Indexed, Rgb, Style

#: Уровни канала в кубе 6x6x6 расширенной палитры xterm (индексы 16-231).
_CUBE_LEVELS = (0, 95, 135, 175, 215, 255)

#: Названия 16 базовых цветов по порядку номеров (0-7 обычные, 8-15 яркие).
ANSI_NAMES = (
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "bright_black", "bright_red", "bright_green", "bright_yellow",
    "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
)  # fmt: skip

#: Как можно записать цвет: ``Rgb``, строка ``"#rrggbb"`` или ``"#rgb"`` (``#`` необязателен), тройка чисел 0-255.
type ColorLike = Rgb | str | tuple[int, int, int]


def parse_color(value: ColorLike) -> Rgb:
    """
    Приводит цвет, записанный любым из способов (``ColorLike``), к ``Rgb``.
    """
    match value:
        case Rgb():
            return value
        case str():
            digits = value.strip().removeprefix("#")
            if len(digits) == 3:
                digits = "".join(char * 2 for char in digits)
            try:
                if len(digits) != 6:
                    raise ValueError
                return Rgb(int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))
            except ValueError:
                raise ValueError(f"цвет {value!r}: ожидается запись вида #rrggbb или #rgb") from None
        case (int(red), int(green), int(blue)):
            return Rgb(red, green, blue)
    raise TypeError(f"цвет {value!r}: ожидается Rgb, строка #rrggbb или тройка чисел")


def _ansi_index(key: int | str) -> int:
    """
    Номер базового цвета по номеру или названию (``"red"``, ``"bright-red"``, ``"Bright Red"``).
    """
    if isinstance(key, int):
        if not 0 <= key < len(ANSI_NAMES):
            raise ValueError(f"номер базового цвета от 0 до 15, получено {key}")
        return key
    name = key.strip().casefold().replace("-", "_").replace(" ", "_")
    if name not in ANSI_NAMES:
        raise ValueError(f"неизвестный базовый цвет {key!r}; допустимы номера 0-15 и названия {', '.join(ANSI_NAMES)}")
    return ANSI_NAMES.index(name)


@dataclass(frozen=True, slots=True)
class Theme:
    """
    Цвет текста и фона по умолчанию и 16 базовых цветов палитры (8 обычных и 8 ярких). ``name`` - название для
    ``THEMES`` и сообщений. Цвета 16-255 общие для всех тем (куб и серые ступени xterm).
    """

    foreground: Rgb
    background: Rgb
    ansi: tuple[Rgb, ...]
    name: str = ""

    def __post_init__(self) -> None:
        if len(self.ansi) != 16:
            raise ValueError(f"в теме должно быть 16 базовых цветов, получено {len(self.ansi)}")

    def derive(
        self,
        *,
        foreground: ColorLike | None = None,
        background: ColorLike | None = None,
        ansi: Mapping[int | str, ColorLike] | Sequence[ColorLike] | None = None,
        name: str | None = None,
    ) -> "Theme":
        """
        Копия темы с другими цветами. ``ansi`` - либо словарь, в котором меняются только указанные базовые цвета
        (ключи - номера 0-15 или названия ``"red"``, ``"bright_red"``), либо все 16 цветов подряд. Что не указано,
        остается прежним.
        """
        colors = list(self.ansi)
        if isinstance(ansi, Mapping):
            for key, value in ansi.items():
                colors[_ansi_index(key)] = parse_color(value)
        elif ansi is not None:
            colors = [parse_color(value) for value in ansi]
        return replace(
            self,
            foreground=self.foreground if foreground is None else parse_color(foreground),
            background=self.background if background is None else parse_color(background),
            ansi=tuple(colors),
            name=self.name if name is None else name,
        )

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Theme":
        """
        Тема из словаря (например, из TOML или JSON): ``base`` - от какой темы отталкиваться (имя из ``THEMES``,
        по умолчанию ``"dark"``), далее необязательные ``name``, ``foreground``, ``background`` и ``ansi``
        (словарь или список из 16 цветов, как в ``derive``). Опечатка в ключе - ошибка, а не молчаливое игнорирование.
        """
        unknown = set(data) - {"base", "name", "foreground", "background", "ansi"}
        if unknown:
            raise ValueError(f"неизвестные ключи темы: {', '.join(sorted(unknown))}")
        base = get_theme(data.get("base", "dark"))
        return base.derive(
            foreground=data.get("foreground"),
            background=data.get("background"),
            ansi=data.get("ansi"),
            name=data.get("name"),
        )

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
    name="dark",
    foreground=Rgb(0xCC, 0xCC, 0xCC),
    background=Rgb(0x1E, 0x1E, 0x1E),
    ansi=_rgb(
        "000000", "cd3131", "0dbc79", "e5e510", "2472c8", "bc3fbc", "11a8cd", "e5e5e5",
        "666666", "f14c4c", "23d18b", "f5f543", "3b8eea", "d670d6", "29b8db", "e5e5e5",
    ),
)  # fmt: skip

#: Светлая тема: тёмный текст на белом фоне, цвета подобраны так, чтобы читаться на белом.
LIGHT = Theme(
    name="light",
    foreground=Rgb(0x33, 0x33, 0x33),
    background=Rgb(0xFF, 0xFF, 0xFF),
    ansi=_rgb(
        "000000", "cd3131", "00bc00", "949800", "0451a5", "bc05bc", "0598bc", "555555",
        "666666", "cd3131", "14ce14", "b5ba00", "0451a5", "bc05bc", "0598bc", "a5a5a5",
    ),
)  # fmt: skip


#: Известные темы по именам (в нижнем регистре): ``get_theme("dark")``. Свои добавляются через ``register_theme``.
THEMES: dict[str, Theme] = {"dark": DARK, "light": LIGHT}

#: Все способы задать тему: сама тема, имя из ``THEMES`` или словарь для ``Theme.from_mapping``.
type ThemeSpec = Theme | str | Mapping[str, Any]


def register_theme(name: str, theme: Theme) -> None:
    """
    Делает тему доступной по имени (регистр не важен); прежняя тема с таким именем заменяется.
    """
    THEMES[name.strip().casefold()] = theme


def get_theme(spec: ThemeSpec | None = None) -> Theme:
    """
    Приводит любой способ задать тему к ``Theme``: ``None`` - тема по умолчанию (``DARK``), ``str`` - имя из
    ``THEMES``, словарь - ``Theme.from_mapping``.
    """
    match spec:
        case None:
            return DARK
        case Theme():
            return spec
        case str():
            try:
                return THEMES[spec.strip().casefold()]
            except KeyError:
                raise ValueError(f"нет темы {spec!r}; известны: {', '.join(sorted(THEMES))}") from None
        case Mapping():
            return Theme.from_mapping(spec)
    raise TypeError(f"тема {spec!r}: ожидается Theme, имя темы или словарь")
