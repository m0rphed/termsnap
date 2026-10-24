"""
Полотно для построчного разбора: строки из ячеек, курсор и действия над ними.
"""

from itertools import groupby
from operator import itemgetter

from termsnap.ansi.sgr import apply_sgr
from termsnap.ansi.tokens import number
from termsnap.model import PLAIN, Line, Span, Style
from termsnap.width import cluster_width, clusters

type Cell = tuple[str, Style]

#: Ширина позиции табуляции: курсор переходит к ближайшей кратной восьми колонке.
TAB_WIDTH = 8

#: Частные режимы терминала начинаются с одного из этих знаков в параметрах (``ESC [ ? 25 l``): текст они не меняют.
_PRIVATE_PARAMETER_MARKS = ("<", "=", ">", "?")


class Canvas:
    """
    Полотно: строки из ячеек "символ + стиль" и положение курсора (строка и столбец).

    Строки не ограничены по высоте и не прокручиваются, а "экран" начинается с первой строки вывода: так перемещения
    курсора вверх и абсолютные позиции (``ESC [ r ; c H``) работают для коротких программ, которые перерисовывают
    несколько последних строк (индикаторы выполнения, ``rich.live``).
    """

    def __init__(self) -> None:
        self.rows: list[list[Cell]] = [[]]
        self.cursor_row = 0
        self.column = 0
        self.style = PLAIN

    @property
    def row(self) -> list[Cell]:
        return self.rows[self.cursor_row]

    def move_to_row(self, index: int) -> None:
        self.cursor_row = max(0, index)
        while self.cursor_row >= len(self.rows):
            self.rows.append([])

    def write(self, text: str) -> None:
        """
        Печатает текст с положения курсора. Широкий символ (эмодзи, иероглиф) занимает две ячейки: во второй
        стоит пустая строка, поэтому текст строки не меняется, а столбцы совпадают с терминалом.
        """
        row = self.row
        for cluster in clusters(text):
            width = cluster_width(cluster)
            if width == 0:
                continue
            row.extend((" ", PLAIN) for _ in range(self.column + width - len(row)))  # дотянуть строку до курсора
            row[self.column] = (cluster, self.style)
            if width == 2:
                row[self.column + 1] = ("", self.style)
            self.column += width

    def control(self, char: str) -> None:
        match char:
            case "\r":
                self.column = 0
            case "\n":  # терминал переводит строку вместе с возвратом каретки
                self.move_to_row(self.cursor_row + 1)
                self.column = 0
            case "\b":
                self.column = max(0, self.column - 1)
            case "\t":
                self.column = (self.column // TAB_WIDTH + 1) * TAB_WIDTH

    def erase_line(self, mode: int) -> None:
        """
        ``ESC [ K``: 0 - от курсора до конца строки, 1 - от начала строки до курсора, 2 - вся строка.
        """
        row = self.row
        match mode:
            case 0:
                del row[self.column :]
            case 1:
                for index in range(min(self.column + 1, len(row))):
                    row[index] = (" ", PLAIN)
            case 2:
                row.clear()

    def erase_display(self, mode: int) -> None:
        """
        ``ESC [ J``: 0 - от курсора до конца экрана, 1 - от начала экрана до курсора, 2 и 3 - весь экран.
        """
        match mode:
            case 0:
                self.erase_line(0)
                del self.rows[self.cursor_row + 1 :]
            case 1:
                for row in self.rows[: self.cursor_row]:
                    row.clear()
                self.erase_line(1)
            case 2 | 3:
                self.rows = [[]]
                self.cursor_row = 0

    def csi(self, params: str, final: str) -> None:
        """
        Выполняет последовательность ``ESC [ <params> <final>``. Буква ``final`` выбирает действие:
        ``m`` - стиль, ``K``/``J`` - стирание, ``A``/``B``/``C``/``D`` - курсор на строку вверх/вниз, на столбец
        вправо/влево, ``E``/``F`` - в начало следующей/прошлой строки, ``G`` - в столбец, ``H``/``f`` - в позицию.
        """
        if params.startswith(_PRIVATE_PARAMETER_MARKS):
            return
        numbers = [number(part) for part in params.split(";")] if params else []
        count = numbers[0] if numbers and numbers[0] else 1  # отсутствующее число и 0 означают "один раз"
        match final:
            case "m":
                self.style = apply_sgr(self.style, params)
            case "K":
                self.erase_line(numbers[0] if numbers else 0)
            case "J":
                self.erase_display(numbers[0] if numbers else 0)
            case "C":
                self.column += count
            case "D":
                self.column = max(0, self.column - count)
            case "G":
                self.column = count - 1
            case "A":
                self.move_to_row(self.cursor_row - count)
            case "B":
                self.move_to_row(self.cursor_row + count)
            case "E":
                self.move_to_row(self.cursor_row + count)
                self.column = 0
            case "F":
                self.move_to_row(self.cursor_row - count)
                self.column = 0
            case "H" | "f":  # позиция задается с единицы: "1;1" - левый верхний угол
                self.move_to_row((numbers[0] or 1) - 1 if numbers else 0)
                self.column = (numbers[1] or 1) - 1 if len(numbers) > 1 else 0

    def lines(self) -> tuple[Line, ...]:
        """
        Строки полотна; соседние ячейки с одним стилем склеиваются во фрагмент.
        """
        rows = self.rows[:-1] if not self.rows[-1] else self.rows  # вывод закончился переводом строки (или пуст)
        return tuple(
            Line(tuple(Span("".join(char for char, _ in cells), style) for style, cells in groupby(row, itemgetter(1))))
            for row in rows
        )
