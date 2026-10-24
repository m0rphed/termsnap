"""
Раскладка картинки: из метрик шрифта и числа клеток получаются размеры и положение строк. Шрифт здесь - заглушка с
тремя числами, поэтому все ожидаемые размеры можно сосчитать в уме.
"""

import pytest

pytest.importorskip("PIL")

from termsnap.png.layout import Layout


class StubFont:
    """
    Шрифт с подъемом 10, спуском 4 и буквой "M" шириной 7 пикселей: все, что нужно ``Layout.measure``.
    """

    def __init__(self, cell: float = 7.0) -> None:
        self._cell = cell

    def getmetrics(self) -> tuple[int, int]:
        return 10, 4

    def getlength(self, text: str) -> float:
        assert text == "M"  # клетка меряется по одной букве
        return self._cell


def measure(*, columns: int, rows: int, margin: int = 4, line_spacing: float = 1.25, cell: float = 7.0, size: int = 14):
    return Layout.measure(
        StubFont(cell),  # type: ignore[arg-type]
        size=size,
        margin=margin,
        line_spacing=line_spacing,
        columns=columns,
        rows=rows,
    )


def test_a_row_is_the_font_height_with_air_around_it():
    # подъем 10 + спуск 4 = 14, с коэффициентом 1.25 это 17.5, а строка занимает целое число пикселей вверх: 18
    assert measure(columns=1, rows=1).row_height == 18
    assert measure(columns=1, rows=1, line_spacing=1.0).row_height == 14


def test_the_picture_is_margin_cells_margin_wide_and_margin_rows_margin_high():
    #   ширина = 4 + 3 * 7 + 4 = 29        высота = 4 + 2 * 18 + 4 = 44
    layout = measure(columns=3, rows=2)
    assert (layout.width, layout.height) == (29, 44)


def test_rows_and_columns_start_after_the_margin_one_cell_or_row_apart():
    layout = measure(columns=3, rows=2)
    assert [layout.row_top(row) for row in range(2)] == [4, 22]
    assert [layout.column_x(column) for column in range(3)] == [4, 11, 18]


def test_the_free_space_of_a_row_is_split_in_halves_above_and_below_the_text():
    # в строке высотой 18 текст занимает 14: два пикселя сверху, два снизу; базовая линия на 10 ниже верха текста
    layout = measure(columns=1, rows=2)
    assert layout.baseline(0) == 4 + 2 + 10
    assert layout.baseline(1) == 22 + 2 + 10


def test_the_right_margin_is_exactly_a_margin_even_when_the_cell_is_fractional():
    # сетка 3 * 6.4 = 19.2 пикселя: край сетки округляется до пикселя (4 + 19.2 = 23.2 -> 23), и только потом справа
    # добавляется поле
    layout = measure(columns=3, rows=1, cell=6.4)
    assert layout.width == 23 + 4
    assert layout.column_x(3) == pytest.approx(23.2)


def test_an_empty_output_still_has_one_cell_and_one_row():
    layout = measure(columns=0, rows=0)
    assert (layout.width, layout.height) == (4 + 7 + 4, 4 + 18 + 4)


def test_line_thickness_follows_the_font_size():
    assert measure(columns=1, rows=1, size=14).thickness == 1
    assert measure(columns=1, rows=1, size=28).thickness == 2
