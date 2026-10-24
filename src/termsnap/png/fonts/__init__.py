"""
Поиск моноширинного шрифта среди установленных в системе: по имени семейства находит файлы начертаний.

Единого кроссплатформенного способа узнать, какие шрифты установлены, нет, поэтому для каждой платформы берется ее
штатный источник, а общий запасной вариант - обход каталогов шрифтов:

- Windows: реестр (``windows``);
- Linux и прочие Unix: fontconfig (``fontconfig``);
- запасной вариант везде: обход стандартных каталогов (``directories``).

Файлы пакета, от простого к сложному: ``families`` (списки имен) -> ``face`` и ``fontset`` (начертание и набор
начертаний) -> ``reading`` (чтение файла) -> источники ``windows``, ``fontconfig``, ``directories`` -> ``search``
(поиск семейства) -> ``glyphs`` (покрытие символов) -> ``resolution`` (выбор основного и запасных шрифтов).
"""

from termsnap.png.fonts.directories import font_directories
from termsnap.png.fonts.face import Face
from termsnap.png.fonts.families import DEFAULT_FAMILIES, FALLBACK_FAMILIES
from termsnap.png.fonts.fontconfig import parse_fc_list
from termsnap.png.fonts.fontset import FontSet
from termsnap.png.fonts.glyphs import has_glyph, missing_glyphs
from termsnap.png.fonts.reading import read_faces
from termsnap.png.fonts.resolution import FontSpec, fallback_fontsets, resolve, resolve_best, resolve_spec
from termsnap.png.fonts.search import find_family, from_files
from termsnap.png.fonts.windows import registry_name_matches

__all__ = [
    "DEFAULT_FAMILIES",
    "FALLBACK_FAMILIES",
    "Face",
    "FontSet",
    "FontSpec",
    "fallback_fontsets",
    "find_family",
    "font_directories",
    "from_files",
    "has_glyph",
    "missing_glyphs",
    "parse_fc_list",
    "read_faces",
    "registry_name_matches",
    "resolve",
    "resolve_best",
    "resolve_spec",
]
