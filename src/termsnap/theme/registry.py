"""
Реестр тем по именам и приведение любого способа задать тему к ``Theme``.
"""

from collections.abc import Mapping
from typing import Any

from termsnap.theme.builtin import DARK, LIGHT
from termsnap.theme.theme import Theme

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
