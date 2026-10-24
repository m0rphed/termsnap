"""
Тема: какими RGB-цветами показываются цвета палитры терминала и цвета по умолчанию.

Своя тема собирается от готовой (``DARK.derive(background="#101010", ansi={"red": "#ff5555"})``) или из словаря
(``Theme.from_mapping``), а ``get_theme`` приводит к ``Theme`` все способы ее задать: саму тему, имя из ``THEMES``
или словарь. Поэтому код, который только передает тему дальше, может принимать любой из них (``ThemeSpec``).

Файлы пакета: ``colors`` (запись цвета) -> ``palette`` (16 базовых имен и палитра xterm) -> ``theme`` (``Theme``) ->
``builtin`` (``DARK``, ``LIGHT``) -> ``registry`` (имена и ``get_theme``).
"""

from termsnap.theme.builtin import DARK, LIGHT
from termsnap.theme.colors import ColorLike, parse_color
from termsnap.theme.palette import ANSI_NAMES
from termsnap.theme.registry import THEMES, ThemeSpec, get_theme, register_theme
from termsnap.theme.theme import Theme

__all__ = [
    "ANSI_NAMES",
    "DARK",
    "LIGHT",
    "THEMES",
    "ColorLike",
    "Theme",
    "ThemeSpec",
    "get_theme",
    "parse_color",
    "register_theme",
]
