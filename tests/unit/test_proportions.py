"""
Пропорции рисования: из размера шрифта и метрик строки выводятся толщина линий, сдвиги и высота строки.
"""

import pytest
from support import require_module

require_module("PIL")

from termsnap.png import proportions
from termsnap.png.boxes.lines import double_offset, heavy_width
from termsnap.png.pixels import blend, pixel


@pytest.mark.parametrize(("size", "thickness"), [(10, 1), (13, 1), (14, 1), (28, 2), (42, 3), (56, 4)])
def test_line_thickness_grows_with_the_font_but_never_vanishes(size: int, thickness: int):
    assert proportions.line_thickness(size) == thickness


def test_synthetic_bold_shift_is_at_least_a_pixel():
    assert proportions.bold_shift(8) == 1
    assert proportions.bold_shift(32) == 2


def test_underline_and_strike_positions_are_measured_from_the_baseline():
    assert proportions.underline_offset(3) == 2  # близко к базовой линии не ставится
    assert proportions.underline_offset(12) == 4  # треть спуска
    assert proportions.strike_offset(20) == 6  # 0.3 подъема


def test_row_height_rounds_up():
    assert proportions.row_height(10, 5, 1.0) == 15
    assert proportions.row_height(10, 5, 1.25) == 19  # 18.75


def test_double_lines_keep_a_gap_and_heavy_lines_stay_centered():
    assert double_offset(1) == 2.0
    assert double_offset(5) == 8.0
    assert [heavy_width(light) for light in (1, 2, 3)] == [3, 5, 7]  # нечетные: центр линии на оси


def test_pixel_rounds_half_up_so_that_strokes_keep_their_thickness():
    assert [pixel(value) for value in (9.4, 9.5, 10.5, 11.5, -0.5)] == [9, 10, 11, 12, 0]
    assert pixel(10.5) - pixel(9.5) == 1  # штрих в один пиксель не исчезает ни при какой координате


def test_blend_is_a_weighted_mix_of_channels():
    assert blend((200, 100, 0), (0, 0, 100), 1.0) == (200, 100, 0)
    assert blend((200, 100, 0), (0, 0, 100), 0.0) == (0, 0, 100)
    assert blend((200, 100, 0), (0, 0, 100), 0.5) == (100, 50, 50)
