"""
Поиск установленного семейства: по очереди штатный источник платформы и обход каталогов.
"""

import sys
from collections.abc import Callable
from pathlib import Path

from termsnap.errors import FontNotFound
from termsnap.png.fonts.directories import directory_faces
from termsnap.png.fonts.face import Face
from termsnap.png.fonts.fontconfig import fontconfig_faces
from termsnap.png.fonts.fontset import FontSet
from termsnap.png.fonts.reading import read_faces
from termsnap.png.fonts.windows import windows_faces

type FaceProvider = Callable[[str], list[Face]]


def _providers() -> tuple[FaceProvider, ...]:
    """
    Источники начертаний в порядке обращения: штатный для платформы, затем общий запасной (обход каталогов).
    """
    native = windows_faces if sys.platform == "win32" else fontconfig_faces
    return native, directory_faces


def find_family(family: str) -> FontSet | None:
    """
    Находит установленное семейство по имени (регистр не важен) или возвращает ``None``.
    """
    for provider in _providers():
        fontset = FontSet.from_faces(provider(family))
        if fontset is not None:
            return fontset
    return None


def from_files(
    regular: str | Path,
    *,
    bold: str | Path | None = None,
    italic: str | Path | None = None,
    bold_italic: str | Path | None = None,
) -> FontSet:
    """
    Набор шрифтов из явно указанных файлов (если нужен шрифт, который не установлен в системе).
    """

    def load(path: str | Path | None) -> Face | None:
        faces = read_faces(Path(path)) if path is not None else []
        return faces[0] if faces else None

    first = load(regular)
    if first is None:
        raise FontNotFound([f"{regular}: не удалось прочитать файл шрифта"])
    return FontSet(first.family, first, load(bold), load(italic), load(bold_italic))
