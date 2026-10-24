"""
Раскладка картинки: размеры клетки, строки и полей, положение строк и столбцов.
"""

from dataclasses import dataclass

from PIL import ImageFont

from termsnap.png import proportions


@dataclass(frozen=True, slots=True)
class Layout:
    """
    Размеры в пикселях готовой картинки (с учетом ``scale``).

        ширина  = поле + столбцы * клетка + поле
        высота  = поле + строки * высота_строки + поле
        строка r начинается на  поле + r * высота_строки
        базовая линия лежит так, чтобы поля над и под текстом в строке были поровну
    """

    size: int  # размер шрифта
    ascent: int  # подъем: от базовой линии вверх
    descent: int  # спуск: от базовой линии вниз
    cell: float  # ширина клетки (дробная: ширина "M" в этом размере)
    row_height: int
    margin: int
    width: int
    height: int
    thickness: int  # толщина тонкой линии

    @classmethod
    def measure(
        cls, font: ImageFont.FreeTypeFont, *, size: int, margin: int, line_spacing: float, columns: int, rows: int
    ) -> "Layout":
        """
        Раскладка для ``columns`` x ``rows`` клеток основного шрифта ``font`` размера ``size``.
        """
        ascent, descent = font.getmetrics()
        cell = font.getlength(proportions.CELL_MEASURE_CHAR)
        row_height = proportions.row_height(ascent, descent, line_spacing)
        # правый край картинки совпадает с краем фона последней клетки: ширина округляется до пикселя до добавления поля
        width = round(margin + max(columns, 1) * cell) + margin
        height = margin * 2 + max(rows, 1) * row_height
        return cls(size, ascent, descent, cell, row_height, margin, width, height, proportions.line_thickness(size))

    def row_top(self, row: int) -> int:
        """
        Верхний край строки ``row``.
        """
        return self.margin + row * self.row_height

    def baseline(self, row: int) -> int:
        """
        Базовая линия строки ``row``: свободное место внутри строки делится пополам над и под текстом.
        """
        return self.row_top(row) + (self.row_height - self.ascent - self.descent) // 2 + self.ascent

    def column_x(self, column: int) -> float:
        """
        Левый край столбца ``column``.
        """
        return self.margin + column * self.cell
