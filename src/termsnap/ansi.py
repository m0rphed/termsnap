"""
Разбор текста с ANSI-последовательностями в строки со стилями.

Это не полный эмулятор терминала, а «построчный» разбор для обычного вывода программ. Поддерживается:

- SGR (``ESC [ ... m``): цвета 16, 256 и 24 бита (в том числе запись через двоеточия), жирный, тусклый, курсив,
  подчеркивание, зачеркивание, обращенный вывод и их отключение;
- ``\\r`` (возврат каретки: следующий текст затирает строку с начала, так рисуются индикаторы выполнения),
  ``\\n``, ``\\b`` и ``\\t``;
- стирание строки (``ESC [ K``) и сдвиг курсора по строке (``ESC [ n C``, ``ESC [ n D``, ``ESC [ n G``).

Все остальные последовательности (заголовок окна, режимы, перемещение курсора по вертикали) отбрасываются, не
попадая в текст. Вывод, который переписывает экран целиком (редакторы, ``top``), требует настоящего эмулятора.
"""

import re
from dataclasses import replace
from itertools import groupby
from operator import itemgetter

from termsnap.model import PLAIN, Color, Indexed, Line, Rgb, Span, Style

type Cell = tuple[str, Style]

#: Ширина позиции табуляции.
TAB_WIDTH = 8

_TOKEN = re.compile(
    r"""
    (?P<osc>\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)?)        # OSC: заголовок окна, гиперссылки - в текст не попадают
    | \x1b\[(?P<params>[0-?]*)[ -/]*(?P<final>[@-~])   # CSI
    | (?P<control>[\r\n\b\t])
    | (?P<text>[^\x00-\x1f\x7f]+)
    | \x1b[ -/]*[0-~]?                                 # прочие последовательности с ESC
    | [\x00-\x1f\x7f]                                  # остальные управляющие символы
    """,
    re.VERBOSE,
)


def _number(part: str) -> int:
    return int(part) if part.isdigit() else 0


#: Сколько значений занимает цвет после кода 38 или 48 (включая вид цвета): ``5, n`` и ``2, r, g, b``.
_EXTENDED_LENGTH = {5: 2, 2: 4}


def _color(values: list[int]) -> Color | None:
    """
    Цвет из значений после кода 38 или 48: ``5, n`` (палитра) или ``2, r, g, b`` (24 бита); в записи через
    двоеточия перед ``r`` может стоять идентификатор цветового пространства, поэтому берутся последние три числа.
    """
    try:
        match values:
            case [5, index, *_]:
                return Indexed(index)
            case [2, _, _, _, *_]:
                return Rgb(*values[-3:])
    except ValueError:
        pass
    return None


def apply_sgr(style: Style, params: str) -> Style:
    """
    Новый стиль после последовательности SGR с параметрами ``params`` (текст между ``[`` и ``m``).
    """
    groups = [[_number(part) for part in group.split(":")] for group in params.split(";")] if params else [[0]]
    index = 0
    while index < len(groups):
        group = groups[index]
        index += 1
        match group[0]:
            case 0:
                style = PLAIN
            case 1:
                style = replace(style, bold=True)
            case 2:
                style = replace(style, dim=True)
            case 3:
                style = replace(style, italic=True)
            case 4 | 21:
                style = replace(style, underline=True)
            case 7:
                style = replace(style, inverse=True)
            case 9:
                style = replace(style, strike=True)
            case 22:
                style = replace(style, bold=False, dim=False)
            case 23:
                style = replace(style, italic=False)
            case 24:
                style = replace(style, underline=False)
            case 27:
                style = replace(style, inverse=False)
            case 29:
                style = replace(style, strike=False)
            case code if 30 <= code <= 37:
                style = replace(style, fg=Indexed(code - 30))
            case code if 90 <= code <= 97:
                style = replace(style, fg=Indexed(code - 90 + 8))
            case code if 40 <= code <= 47:
                style = replace(style, bg=Indexed(code - 40))
            case code if 100 <= code <= 107:
                style = replace(style, bg=Indexed(code - 100 + 8))
            case 39:
                style = replace(style, fg=None)
            case 49:
                style = replace(style, bg=None)
            case 38 | 48 as code:
                if len(group) > 1:  # запись через двоеточия: все значения в одной группе
                    color = _color(group[1:])
                else:  # запись через точки с запятой: значения идут следующими группами
                    rest = [following[0] for following in groups[index:]]
                    length = _EXTENDED_LENGTH.get(rest[0], len(rest)) if rest else 0
                    color = _color(rest[:length])
                    index += length
                style = replace(style, fg=color) if code == 38 else replace(style, bg=color)
            case _:
                pass  # мигание, скрытый текст, шрифты и прочее: на показ в документе не влияет
    return style


class _Canvas:
    """
    Полотно: строки из ячеек «символ + стиль» и положение курсора в последней строке.
    """

    def __init__(self) -> None:
        self.rows: list[list[Cell]] = [[]]
        self.column = 0
        self.style = PLAIN

    @property
    def row(self) -> list[Cell]:
        return self.rows[-1]

    def write(self, text: str) -> None:
        row = self.row
        for char in text:
            if self.column < len(row):
                row[self.column] = (char, self.style)
            else:
                row.extend((" ", PLAIN) for _ in range(self.column - len(row)))
                row.append((char, self.style))
            self.column += 1

    def control(self, char: str) -> None:
        match char:
            case "\r":
                self.column = 0
            case "\n":  # терминал переводит строку вместе с возвратом каретки
                self.rows.append([])
                self.column = 0
            case "\b":
                self.column = max(0, self.column - 1)
            case "\t":
                self.column = (self.column // TAB_WIDTH + 1) * TAB_WIDTH

    def erase_line(self, mode: int) -> None:
        row = self.row
        match mode:
            case 0:
                del row[self.column :]
            case 1:
                for index in range(min(self.column + 1, len(row))):
                    row[index] = (" ", PLAIN)
            case 2:
                row.clear()

    def csi(self, params: str, final: str) -> None:
        if params.startswith(("<", "=", ">", "?")):  # частные режимы терминала не меняют текст
            return
        numbers = [_number(part) for part in params.split(";")] if params else []
        count = numbers[0] if numbers and numbers[0] else 1
        match final:
            case "m":
                self.style = apply_sgr(self.style, params)
            case "K":
                self.erase_line(numbers[0] if numbers else 0)
            case "C":
                self.column += count
            case "D":
                self.column = max(0, self.column - count)
            case "G":
                self.column = count - 1

    def lines(self) -> tuple[Line, ...]:
        rows = self.rows[:-1] if not self.row else self.rows  # вывод закончился переводом строки (или пуст)
        return tuple(
            Line(tuple(Span("".join(char for char, _ in cells), style) for style, cells in groupby(row, itemgetter(1))))
            for row in rows
        )


def parse(text: str) -> tuple[Line, ...]:
    """
    Строки со стилями из текста с ANSI-последовательностями.
    """
    canvas = _Canvas()
    for token in _TOKEN.finditer(text):
        match token.lastgroup:
            case "text":
                canvas.write(token.group())
            case "control":
                canvas.control(token.group())
            case "final":
                canvas.csi(token.group("params"), token.group("final"))
    return canvas.lines()
