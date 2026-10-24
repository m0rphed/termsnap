"""
Шрифты Windows: реестр (``HKLM`` и ``HKCU``, ключ ``...\\CurrentVersion\\Fonts``).

Именно из реестра системные библиотеки узнают об установленных шрифтах, в том числе поставленных только для
пользователя.
"""

import os
import re
import sys
from collections.abc import Iterator
from pathlib import Path

from termsnap.png.fonts.face import Face
from termsnap.png.fonts.reading import read_faces

_REGISTRY_FONTS = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"

#: Хвост имени записи, который не относится к названию шрифта: "Consolas (TrueType)".
_REGISTRY_SUFFIX = re.compile(r"\s*\((?:TrueType|OpenType)\)\s*$")

#: Разделитель семейств в одной записи: "Cambria & Cambria Math (TrueType)" - два шрифта в одном файле.
_REGISTRY_SEPARATOR = " & "


def _squash(name: str) -> str:
    """
    Имя без пробелов, дефисов и подчеркиваний и без учета регистра: установщики пишут в реестр и
    "JetBrains Mono NL Regular", и "JetBrainsMonoNL-Regular".
    """
    return re.sub(r"[\s_\-]+", "", name.casefold())


def registry_name_matches(name: str, family: str) -> bool:
    """
    Подходит ли запись реестра ("Consolas Bold Italic (TrueType)", "Cambria & Cambria Math (TrueType)") под
    семейство: название записи должно начинаться с названия семейства. Точное имя семейства потом проверяется
    по самому файлу.
    """
    wanted = _squash(family)
    return any(_squash(part).startswith(wanted) for part in _REGISTRY_SUFFIX.sub("", name).split(_REGISTRY_SEPARATOR))


def _registry_fonts() -> Iterator[tuple[str, str]]:
    """
    Записи реестра шрифтов: (название, значение), где значение - имя файла или полный путь.
    """
    import winreg

    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            key = winreg.OpenKey(hive, _REGISTRY_FONTS)
        except OSError:
            continue
        with key:
            for position in range(winreg.QueryInfoKey(key)[1]):
                name, value, _kind = winreg.EnumValue(key, position)
                if isinstance(value, str):
                    yield name, value


def windows_faces(family: str) -> list[Face]:
    """
    Начертания семейства, найденные через реестр; вне Windows пусто.

        для каждой записи реестра, чье название начинается с названия семейства:
            путь = значение (если там только имя файла - в каталоге Fonts системы)
            взять из файла начертания с точно таким семейством
    """
    if sys.platform != "win32":
        return []
    fonts_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    wanted = family.casefold()
    faces = []
    for name, value in _registry_fonts():
        if registry_name_matches(name, family):
            path = Path(value) if Path(value).is_absolute() else fonts_dir / value
            faces += [face for face in read_faces(path) if face.family.casefold() == wanted]
    return faces
