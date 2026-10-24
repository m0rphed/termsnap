"""
Общий для всех платформ способ найти шрифты: обойти стандартные каталоги шрифтов и прочитать каждый файл.

Это запасной вариант: он находит и шрифты macOS, где штатный интерфейс (CoreText) недоступен без сторонних
библиотек, и все, что не нашел штатный источник платформы.
"""

import os
import sys
from functools import cache
from pathlib import Path

from termsnap.png.fonts.face import Face
from termsnap.png.fonts.reading import FONT_SUFFIXES, read_faces


def font_directories() -> list[Path]:
    """
    Стандартные каталоги шрифтов текущей платформы (существующие и нет - проверяется при обходе).
    """
    home = Path.home()
    if sys.platform == "win32":
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        return [windir / "Fonts", local / "Microsoft" / "Windows" / "Fonts"]
    if sys.platform == "darwin":
        return [
            Path("/System/Library/Fonts"),
            Path("/System/Library/Fonts/Supplemental"),
            Path("/Library/Fonts"),
            home / "Library" / "Fonts",
        ]
    # Linux и прочие Unix: XDG Base Directory (https://specifications.freedesktop.org), плюс старый ~/.fonts
    data_home = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    data_dirs = [Path(p) for p in (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":") if p]
    return [home / ".fonts", *(base / "fonts" for base in (data_home, *data_dirs))]


@cache
def _scanned_faces() -> tuple[Face, ...]:
    """
    Все начертания из стандартных каталогов шрифтов (обход занимает время, поэтому результат запоминается).
    """
    faces: list[Face] = []
    for directory in font_directories():
        if directory.is_dir():
            for path in sorted(directory.rglob("*")):
                if path.suffix.lower() in FONT_SUFFIXES and path.is_file():
                    faces += read_faces(path)
    return tuple(faces)


def directory_faces(family: str) -> list[Face]:
    """
    Начертания семейства среди шрифтов из каталогов (регистр имени не важен).
    """
    wanted = family.casefold()
    return [face for face in _scanned_faces() if face.family.casefold() == wanted]
