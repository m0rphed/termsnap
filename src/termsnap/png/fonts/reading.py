"""
Чтение файлов шрифтов: какие начертания в файле лежат.

Имена семейства и начертания всегда берутся из самого файла (FreeType через Pillow), а не из имени файла или
записи реестра: ``Consolas`` - это семейство, а ``consola.ttf`` - файл, и Pillow ищет шрифт по имени файла.
"""

from pathlib import Path

from PIL import ImageFont

from termsnap.png.fonts.face import Face

#: Расширения файлов шрифтов (TrueType, OpenType и их коллекции).
FONT_SUFFIXES = frozenset({".ttf", ".otf", ".ttc", ".otc"})

#: Расширения коллекций: в одном файле несколько шрифтов, они различаются номером.
COLLECTION_SUFFIXES = frozenset({".ttc", ".otc"})

#: Сколько шрифтов в файле-коллекции просматривать: Pillow не говорит, сколько их, номера перебираются до первой ошибки.
MAX_FACES_PER_FILE = 64

#: Размер, в котором шрифт открывается только ради чтения имен: на имена он не влияет.
_PROBE_SIZE = 10


def read_faces(path: Path) -> list[Face]:
    """
    Начертания, найденные в файле шрифта (у коллекций ``.ttc`` их несколько); нечитаемый файл дает пустой список.
    """
    faces = []
    for index in range(MAX_FACES_PER_FILE):
        try:
            font = ImageFont.truetype(str(path), size=_PROBE_SIZE, index=index)
        except OSError:
            break
        family, style = font.getname()
        if family:
            faces.append(Face(family, style or "Regular", path, index))
        if path.suffix.lower() not in COLLECTION_SUFFIXES:
            break
    return faces
