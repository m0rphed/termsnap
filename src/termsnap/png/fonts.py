"""
Поиск моноширинного шрифта среди установленных в системе: по имени семейства находит файлы начертаний.

Единого кроссплатформенного способа узнать, какие шрифты установлены, нет, поэтому для каждой платформы берется ее
штатный источник, а общий запасной вариант - обход каталогов шрифтов:

- Windows: реестр (``HKLM`` и ``HKCU``, ключ ``...\\CurrentVersion\\Fonts``) - именно из него системные библиотеки
  узнают об установленных шрифтах, в том числе поставленных только для пользователя;
- Linux и прочие Unix: fontconfig (``fc-list``), он же определяет шрифты в большинстве окружений рабочего стола;
- запасной вариант везде: обход стандартных каталогов шрифтов с чтением имен прямо из файлов (так находятся и
  шрифты macOS, где штатный интерфейс - CoreText, не доступный без сторонних библиотек).

Имена семейства и начертания всегда берутся из самого файла (FreeType через Pillow), а не из имени файла или
записи реестра: ``Consolas`` - это семейство, а ``consola.ttf`` - файл, и Pillow ищет шрифт по имени файла.
"""

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from termsnap.errors import FontNotFound

#: Семейства по умолчанию: сначала самые подходящие для кода (без лигатур и с кириллицей), потом штатные шрифты
#: платформ (Windows, macOS, Linux) и запасной вариант.
DEFAULT_FAMILIES = (
    "JetBrains Mono NL",
    "JetBrains Mono",
    "Cascadia Mono",
    "Consolas",
    "Menlo",
    "DejaVu Sans Mono",
    "Liberation Mono",
    "Noto Sans Mono",
    "Courier New",
)

#: Запасные семейства для символов, которых нет в основном шрифте (эмодзи, стрелки, математические и прочие знаки);
#: они не обязаны быть моноширинными: каждый символ ставится в свою клетку.
FALLBACK_FAMILIES = (
    "Segoe UI Emoji",
    "Segoe UI Symbol",
    "Noto Color Emoji",
    "Apple Color Emoji",
    "Noto Sans Symbols 2",
    "Noto Sans Symbols",
    "Symbola",
    "DejaVu Sans",
    "Arial Unicode MS",
    "Segoe UI",
    # иероглифы
    "MS Gothic",
    "Microsoft YaHei",
    "Yu Gothic",
    "Malgun Gothic",
    "Noto Sans Mono CJK SC",
    "Noto Sans CJK SC",
    "PingFang SC",
    "Hiragino Sans GB",
    "WenQuanYi Micro Hei",
)

FONT_SUFFIXES = frozenset({".ttf", ".otf", ".ttc", ".otc"})
COLLECTION_SUFFIXES = frozenset({".ttc", ".otc"})

#: Сколько шрифтов в файле-коллекции просматривать.
_MAX_COLLECTION = 64

#: Слова стиля, которые определяют роль начертания (жирное, курсивное), а не его «основность».
_EMPHASIS = frozenset({"bold", "italic", "oblique"})

#: Остаток стиля после отбрасывания слов из ``_EMPHASIS``: чем меньше число, тем «основнее» начертание.
_REGULAR_RANK = {"regular": 0, "book": 1, "normal": 1, "roman": 1, "medium": 2}
_UNKNOWN_RANK = 9


def _tokens(style: str) -> set[str]:
    return set(re.split(r"[\s_-]+", style.casefold()))


@dataclass(frozen=True, slots=True)
class Face:
    """
    Одно начертание: семейство, стиль («Regular», «Bold Italic»), файл и номер шрифта в файле-коллекции.
    """

    family: str
    style: str
    path: Path
    index: int = 0

    @property
    def bold(self) -> bool:
        return "bold" in _tokens(self.style)

    @property
    def italic(self) -> bool:
        return bool({"italic", "oblique"} & _tokens(self.style))

    @property
    def rank(self) -> int:
        """
        Насколько стиль похож на «основной» своей роли (0 - точно Regular, Bold, Italic или Bold Italic): слова
        про жирность и наклон отбрасываются, по остатку («Book», «Medium») сравниваются начертания одной роли,
        а «Light» или «ExtraBold» уступают всем остальным.
        """
        core = " ".join(sorted(_tokens(self.style) - _EMPHASIS - {""}))
        return 0 if not core else _REGULAR_RANK.get(core, _UNKNOWN_RANK)


@dataclass(frozen=True, slots=True)
class FontSet:
    """
    Начертания одного семейства: обычное обязательно, остальные - если установлены.
    """

    family: str
    regular: Face
    bold: Face | None = None
    italic: Face | None = None
    bold_italic: Face | None = None

    @classmethod
    def from_faces(cls, faces: Iterable[Face]) -> "FontSet | None":
        """
        Раскладывает начертания по ролям; ``None``, если нет обычного начертания.
        """
        best: dict[tuple[bool, bool], Face] = {}
        for face in faces:
            key = (face.bold, face.italic)
            if key not in best or face.rank < best[key].rank:
                best[key] = face
        regular = best.get((False, False))
        if regular is None:
            return None
        return cls(regular.family, regular, best.get((True, False)), best.get((False, True)), best.get((True, True)))

    def pick(self, *, bold: bool, italic: bool) -> tuple[Face, bool]:
        """
        Начертание для сочетания «жирный/курсив» и признак того, что жирность придется имитировать (нужного
        начертания в семействе нет). Отсутствующий курсив не имитируется: берется прямое начертание.
        """
        if bold and italic:
            candidates = (self.bold_italic, self.bold, self.italic, self.regular)
        elif bold:
            candidates = (self.bold, self.regular)
        elif italic:
            candidates = (self.italic, self.regular)
        else:
            candidates = (self.regular,)
        face = next(candidate for candidate in candidates if candidate is not None)
        return face, bold and not face.bold


# --------------------------------------------------------------------------------------------- чтение файлов
def read_faces(path: Path) -> list[Face]:
    """
    Начертания, найденные в файле шрифта (у коллекций ``.ttc`` их несколько); нечитаемый файл дает пустой список.
    """
    faces = []
    for index in range(_MAX_COLLECTION):
        try:
            font = ImageFont.truetype(str(path), size=10, index=index)
        except OSError:
            break
        family, style = font.getname()
        if family:
            faces.append(Face(family, style or "Regular", path, index))
        if path.suffix.lower() not in COLLECTION_SUFFIXES:
            break
    return faces


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
    data_home = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    data_dirs = [Path(p) for p in (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":") if p]
    return [home / ".fonts", *(base / "fonts" for base in (data_home, *data_dirs))]


# ------------------------------------------------------------------------------------------------- Windows
_REGISTRY_FONTS = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
_REGISTRY_SUFFIX = re.compile(r"\s*\((?:TrueType|OpenType)\)\s*$")


def _squash(name: str) -> str:
    """
    Имя без пробелов, дефисов и подчеркиваний и без учета регистра: установщики пишут в реестр и
    «JetBrains Mono NL Regular», и «JetBrainsMonoNL-Regular».
    """
    return re.sub(r"[\s_\-]+", "", name.casefold())


def registry_name_matches(name: str, family: str) -> bool:
    """
    Подходит ли запись реестра («Consolas Bold Italic (TrueType)», «Cambria & Cambria Math (TrueType)») под
    семейство: название записи должно начинаться с названия семейства. Точное имя семейства потом проверяется
    по самому файлу.
    """
    wanted = _squash(family)
    return any(_squash(part).startswith(wanted) for part in _REGISTRY_SUFFIX.sub("", name).split(" & "))


def _registry_fonts() -> Iterator[tuple[str, str]]:
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


def _windows_faces(family: str) -> list[Face]:
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


# ------------------------------------------------------------------------------------------------ fontconfig
_FC_FORMAT = "%{file}\t%{index}\t%{family}\t%{style}\n"


def _fc_escape(value: str) -> str:
    return re.sub(r"([\\\-:,=])", r"\\\1", value)


def parse_fc_list(output: str, family: str) -> list[Face]:
    """
    Начертания семейства из вывода ``fc-list --format "%{file}\\t%{index}\\t%{family}\\t%{style}\\n"``. В ответе
    fontconfig у семейства и стиля может быть несколько названий через запятую (на разных языках); берется первый
    стиль. Именованные экземпляры вариативных шрифтов (в индексе заняты старшие 16 бит) пропускаются: Pillow
    загружает такой файл с настройками по умолчанию, а не нужным экземпляром.
    """
    wanted = family.casefold()
    faces = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        file, index, families, styles = parts
        if wanted not in {name.strip().casefold() for name in families.split(",")}:
            continue
        number = int(index) if index.isdigit() else 0
        if number >> 16:
            continue
        faces.append(Face(family, styles.split(",")[0].strip() or "Regular", Path(file), number))
    return faces


def _fontconfig_faces(family: str) -> list[Face]:
    executable = shutil.which("fc-list")
    if executable is None:
        return []
    try:
        done = subprocess.run(
            [executable, "--format", _FC_FORMAT, f":family={_fc_escape(family)}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return parse_fc_list(done.stdout, family)


# ---------------------------------------------------------------------------------------------- каталоги
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


def _directory_faces(family: str) -> list[Face]:
    wanted = family.casefold()
    return [face for face in _scanned_faces() if face.family.casefold() == wanted]


# ------------------------------------------------------------------------------------------------- поиск
def _providers() -> tuple[Callable[[str], list[Face]], ...]:
    native = _windows_faces if sys.platform == "win32" else _fontconfig_faces
    return native, _directory_faces


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


# ------------------------------------------------------------------------------------------------ символы
def _picture(font: ImageFont.FreeTypeFont, char: str) -> bytes:
    """
    Как символ выглядит в шрифте: яркости точек на небольшом листе.
    """
    side = round(font.size * 2)
    sheet = Image.new("L", (side, side))
    ImageDraw.Draw(sheet).text((0, 0), char, font=font, fill=255)
    return sheet.tobytes()


def has_glyph(font: ImageFont.FreeTypeFont, char: str) -> bool:
    """
    Есть ли в шрифте символ: у отсутствующего символа рисуется тот же знак «нет глифа», что и у заведомо
    незанятого кода.
    """
    return _picture(font, char) != _picture(font, "\U0010ffff")


def missing_glyphs(face: Face, chars: str) -> str:
    """
    Символы из ``chars`` (без пробельных и управляющих), которых нет в шрифте, в порядке кодов.
    """
    font = ImageFont.truetype(str(face.path), size=24, index=face.index)
    wanted = {char for char in chars if char.isprintable() and not char.isspace()}
    return "".join(sorted(char for char in wanted if not has_glyph(font, char)))


def resolve(families: Sequence[str] = DEFAULT_FAMILIES, *, covers: str = "") -> FontSet:
    """
    Первое из семейств, которое установлено и содержит все символы ``covers``; иначе ``FontNotFound`` с причиной
    отказа по каждому семейству.
    """
    problems = []
    for family in families:
        fontset = find_family(family)
        if fontset is None:
            problems.append(f"{family}: не установлен")
            continue
        missing = missing_glyphs(fontset.regular, covers)
        if missing:
            problems.append(f"{family}: нет символов {missing!r}")
            continue
        return fontset
    raise FontNotFound(problems)


def resolve_best(families: Sequence[str] = DEFAULT_FAMILIES, *, covers: str = "") -> FontSet:
    """
    Установленное семейство, в котором есть больше всего символов ``covers`` (при равенстве - более раннее в списке).
    Нужно, когда ни одно семейство не содержит все символы, а недостающие рисуются запасными шрифтами.
    """
    best: tuple[int, FontSet] | None = None
    problems = []
    for family in families:
        fontset = find_family(family)
        if fontset is None:
            problems.append(f"{family}: не установлен")
            continue
        missing = len(missing_glyphs(fontset.regular, covers))
        if best is None or missing < best[0]:
            best = (missing, fontset)
    if best is None:
        raise FontNotFound(problems)
    return best[1]


@cache
def fallback_fontsets() -> tuple[FontSet, ...]:
    """
    Установленные запасные семейства из ``FALLBACK_FAMILIES`` в порядке предпочтения.
    """
    return tuple(fontset for family in FALLBACK_FAMILIES if (fontset := find_family(family)) is not None)
