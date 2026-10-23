"""
Эмуляция экрана терминала на ``pyte``: вывод программы, запущенной в псевдотерминале, превращается в те же строки
со стилями (``Line``), что и у разбора ``termsnap.ansi``, но экран ведется целиком: абсолютные позиции курсора,
прокрутка, перерисовка кадров, стирание областей.

Нужен дополнительный пакет ``pyte`` (``pip install termsnap[pty]``).

Отличия от «голого» ``pyte``: сохраняется индекс цвета палитры (``Indexed``, а не готовый RGB), поэтому тема
остается в силе, и поддерживается «тусклый» атрибут (SGR 2), который ``pyte`` отбрасывает.
"""

from itertools import groupby

import pyte
from pyte import modes
from pyte.screens import Char

from termsnap.model import PLAIN, Color, Indexed, Line, Rgb, Span, Style
from termsnap.width import cluster_width, clusters

#: Сколько строк, ушедших вверх за пределы экрана, помнит эмулятор.
HISTORY_LINES = 100_000

#: Названия цветов pyte для кодов 30-37; яркие получают приставку ``bright``.
_NAMES = ("black", "red", "green", "brown", "blue", "magenta", "cyan", "white")
_BASIC = {name: index for index, name in enumerate(_NAMES)} | {
    f"bright{name}": index + 8 for index, name in enumerate(_NAMES)
}

#: Приставка, которой помечается индекс палитры в поле цвета ячейки (у pyte там оказался бы готовый RGB).
_PALETTE_MARK = "#"

#: Ячейка без оформления (текст не важен).
_UNSTYLED = Char("")

_PLAIN_FG = (*range(30, 38), 39, *range(90, 98))
_PLAIN_BG = (*range(40, 48), 49, *range(100, 108))


class _Screen(pyte.HistoryScreen):
    """
    Экран pyte с историей прокрутки. Атрибут «тусклый» хранится в поле ``blink`` ячейки (настоящее мигание на показ
    в документе не влияет, а у ``Char`` для тусклого поля нет).

    Вывод текста переопределен: ``pyte`` на первом же символе нулевой ширины (селектор эмодзи, соединитель ZWJ)
    бросает остаток строки, а здесь текст делится на те же кластеры, что и в ``termsnap.width``.
    """

    def draw(self, data: str) -> None:
        data = data.translate(self.g1_charset if self.charset else self.g0_charset)
        for cluster in clusters(data):
            width = cluster_width(cluster)
            if width == 0:
                continue
            if self.cursor.x == self.columns:  # конец строки: перенос или замена последнего символа
                if modes.DECAWM in self.mode:
                    self.dirty.add(self.cursor.y)
                    self.carriage_return()
                    self.linefeed()
                else:
                    self.cursor.x -= width
            if modes.IRM in self.mode:
                self.insert_characters(width)
            line = self.buffer[self.cursor.y]
            line[self.cursor.x] = self.cursor.attrs._replace(data=cluster)
            if width == 2 and self.cursor.x + 1 < self.columns:  # у широкого символа вторая клетка пуста
                line[self.cursor.x + 1] = self.cursor.attrs._replace(data="")
            self.cursor.x = min(self.cursor.x + width, self.columns)
        self.dirty.add(self.cursor.y)

    def select_graphic_rendition(self, *attrs: int) -> None:
        dim = self.cursor.attrs.blink
        palette: dict[str, str] = {}
        codes = attrs or (0,)
        index = 0
        while index < len(codes):
            code = codes[index]
            index += 1
            if code == 0:
                dim = False
                palette.clear()
            elif code == 2:
                dim = True
            elif code == 22:
                dim = False
            elif code in _PLAIN_FG:
                palette.pop("fg", None)
            elif code in _PLAIN_BG:
                palette.pop("bg", None)
            elif code in (38, 48):
                key = "fg" if code == 38 else "bg"
                kind = codes[index] if index < len(codes) else None
                if kind == 5 and index + 1 < len(codes):
                    if codes[index + 1] <= 255:
                        palette[key] = f"{_PALETTE_MARK}{codes[index + 1]}"
                    index += 2
                elif kind == 2:
                    palette.pop(key, None)
                    index += 4
        super().select_graphic_rendition(*attrs)
        self.cursor.attrs = self.cursor.attrs._replace(blink=dim, **palette)


def _color(value: str) -> Color | None:
    if value == "default":
        return None
    if value.startswith(_PALETTE_MARK):
        return Indexed(int(value[1:]))
    if value in _BASIC:
        return Indexed(_BASIC[value])
    return Rgb(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def _style(cell: Char) -> Style:
    if cell._replace(data="") == _UNSTYLED:
        return PLAIN
    return Style(
        fg=_color(cell.fg),
        bg=_color(cell.bg),
        bold=cell.bold,
        dim=cell.blink,
        italic=cell.italics,
        underline=cell.underscore,
        strike=cell.strikethrough,
        inverse=cell.reverse,
    )


def _line(cells: list[Char]) -> Line:
    """
    Строка из ячеек экрана без хвоста из пустых ячеек (пробелы без оформления); вторая половина широкого символа
    в тексте пуста, как в ``termsnap.ansi``.
    """
    blank = Char(" ")
    while cells and cells[-1] == blank:
        cells.pop()
    groups = groupby(cells, _style)
    return Line(tuple(Span("".join(cell.data for cell in group), style) for style, group in groups))


def render(text: str, *, columns: int, rows: int) -> tuple[Line, ...]:
    """
    Строки со стилями, которые остались на экране ``columns`` x ``rows`` после вывода ``text`` (вместе со строками,
    ушедшими вверх при прокрутке). Пустые строки в конце отбрасываются.
    """
    screen = _Screen(columns, rows, history=HISTORY_LINES)
    pyte.Stream(screen).feed(text)
    stored = [[row[column] for column in range(columns)] for row in screen.history.top]
    visible = [[screen.buffer[y][column] for column in range(columns)] for y in range(rows)]
    lines = [_line(cells) for cells in stored + visible]
    while lines and not lines[-1].spans:
        lines.pop()
    return tuple(lines)
