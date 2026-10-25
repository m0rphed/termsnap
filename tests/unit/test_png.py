"""
Картинка целиком: размеры, масштаб, поля, тема и байты PNG. Как рисуются сами фрагменты - в ``test_painter.py``.

Шрифт - встроенный в Pillow (``bundled_fonts``), поэтому результат не зависит от шрифтов машины.
"""

import io

import pytest
from helpers import PNG_SIGNATURE
from support import require_module

require_module("PIL")

from PIL import Image

from termsnap import DARK, LIGHT, Line, Span
from termsnap.png import FontSet, render_image, render_png


def lines(*texts: str) -> list[Line]:
    return [Line((Span(text),)) for text in texts]


def test_a_longer_line_makes_the_picture_wider(bundled_fonts: FontSet):
    options = {"fonts": bundled_fonts, "scale": 1, "padding": 0}
    assert render_image(lines("abcdef"), **options).width > render_image(lines("ab"), **options).width


def test_a_shorter_line_below_does_not_change_the_width(bundled_fonts: FontSet):
    options = {"fonts": bundled_fonts, "scale": 1, "padding": 0}
    assert render_image(lines("abcdef", "ab"), **options).width == render_image(lines("abcdef"), **options).width


def test_each_line_adds_one_row_of_the_same_height(bundled_fonts: FontSet):
    options = {"fonts": bundled_fonts, "scale": 1, "padding": 0}
    one, two = render_image(lines("ab"), **options), render_image(lines("ab", "ab"), **options)
    assert two.height == 2 * one.height


def test_columns_widen_the_picture_beyond_the_text(bundled_fonts: FontSet):
    options = {"fonts": bundled_fonts, "scale": 1, "padding": 0}
    narrow = render_image(lines("abcdef"), **options)
    assert render_image(lines("abcdef"), columns=12, **options).width > narrow.width


def test_columns_do_not_change_the_height(bundled_fonts: FontSet):
    options = {"fonts": bundled_fonts, "scale": 1, "padding": 0}
    narrow = render_image(lines("abcdef"), **options)
    assert render_image(lines("abcdef"), columns=12, **options).height == narrow.height


def test_padding_is_added_on_every_side(bundled_fonts: FontSet):
    options = {"fonts": bundled_fonts, "scale": 1}
    bare = render_image(lines("abcdef", "ab"), padding=0, **options)
    padded = render_image(lines("abcdef", "ab"), padding=10, **options)
    assert (padded.width, padded.height) == (bare.width + 2 * 10, bare.height + 2 * 10)


def test_scale_two_is_the_same_picture_as_doubled_font_size_and_padding_at_scale_one(bundled_fonts: FontSet):
    # scale означает только "подробнее в N раз": шрифт и поля становятся вдвое крупнее, а больше ничего не меняется
    text = lines("hello", "world")
    detailed = render_image(text, fonts=bundled_fonts, font_size=14, padding=8, scale=2)
    doubled = render_image(text, fonts=bundled_fonts, font_size=28, padding=16, scale=1)
    assert detailed.tobytes() == doubled.tobytes()


def test_empty_output_still_gives_a_valid_picture(bundled_fonts: FontSet):
    image = render_image([], fonts=bundled_fonts)
    assert min(image.size) > 0


@pytest.mark.parametrize(
    ("theme", "background"), [(DARK, DARK.background), (LIGHT, LIGHT.background)], ids=["dark", "light"]
)
def test_the_picture_is_filled_with_the_background_of_the_theme(theme, background, bundled_fonts: FontSet):
    image = render_image(lines(" "), fonts=bundled_fonts, theme=theme, scale=1)
    assert image.getcolors() == [(image.width * image.height, background.channels)]


def test_png_bytes_start_with_the_png_signature(bundled_fonts: FontSet):
    assert render_png(lines("hello"), fonts=bundled_fonts).startswith(PNG_SIGNATURE)


def test_png_bytes_hold_the_same_picture_as_the_image(bundled_fonts: FontSet):
    data = render_png(lines("hello"), fonts=bundled_fonts, scale=2)
    assert Image.open(io.BytesIO(data)).size == render_image(lines("hello"), fonts=bundled_fonts, scale=2).size


def test_png_resolution_is_the_screen_one_times_the_scale(bundled_fonts: FontSet):
    # 96 точек на дюйм "как на экране", умноженные на масштаб
    data = render_png(lines("hello"), fonts=bundled_fonts, scale=2)
    dpi_x, dpi_y = Image.open(io.BytesIO(data)).info["dpi"]
    assert (round(dpi_x), round(dpi_y)) == (192, 192)
