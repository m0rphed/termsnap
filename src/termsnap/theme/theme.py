"""
Тема: цвета по умолчанию и 16 базовых цветов палитры.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from termsnap.model import Color, Indexed, Rgb, Style
from termsnap.theme.colors import ColorLike, parse_color
from termsnap.theme.palette import ANSI_NAMES, ansi_index, extended_color

#: Ключи словаря, из которого собирается тема (``Theme.from_mapping``).
_MAPPING_KEYS = frozenset({"base", "name", "foreground", "background", "ansi"})


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
        if len(self.ansi) != len(ANSI_NAMES):
            raise ValueError(f"в теме должно быть {len(ANSI_NAMES)} базовых цветов, получено {len(self.ansi)}")

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
                colors[ansi_index(key)] = parse_color(value)
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
        unknown = set(data) - _MAPPING_KEYS
        if unknown:
            raise ValueError(f"неизвестные ключи темы: {', '.join(sorted(unknown))}")
        # имя базовой темы ищется в реестре, а реестр хранит ``Theme``: импорт здесь разрывает цикл
        from termsnap.theme.registry import get_theme

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
            case Indexed(index) if index < len(self.ansi):
                return self.ansi[index]
            case Indexed(index):
                return extended_color(index)

    def colors_of(self, style: Style) -> tuple[Rgb, Rgb]:
        """
        Итоговые цвета текста и фона для стиля с учетом цветов по умолчанию и обращенного вывода (``inverse``).
        """
        foreground = self.foreground if style.fg is None else self.resolve(style.fg)
        background = self.background if style.bg is None else self.resolve(style.bg)
        return (background, foreground) if style.inverse else (foreground, background)
