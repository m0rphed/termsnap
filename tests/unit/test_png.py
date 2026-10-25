"""
Картинка целиком: размеры, масштаб, поля, тема и байты PNG. Как рисуются сами фрагменты - в ``test_painter.py``.

Шрифт - встроенный в Pillow (``bundled_fonts``), поэтому результат не зависит от шрифтов машины.
"""

import io

import pytest
from support import require_module

require_module("PIL")

from PIL import Image

from termsnap import DARK, LIGHT, Line, Span
from termsnap.png import FontSet, render_image, render_png


def lines(*texts: str) -> list[Line]:
    return [Line((Span(text),)) for text in texts]


def test_the_picture_is_as_wide_as_the_longest_line_and_each_line_adds_a_row(bundled_fonts: FontSet):
    options = {"fonts": bundled_fonts, "scale": 1, "padding": 0}
    short, long = render_image(lines("ab"), **options), render_image(lines("abcdef"), **options)
    assert long.width > short.width
    assert render_image(lines("abcdef", "ab"), **options).width == long.width  # короткая вторая строка ширину не меняет
    assert long.height == short.height
    assert render_image(lines("ab", "ab"), **options).height == 2 * short.height


def test_columns_widen_the_picture_beyond_the_text_but_not_its_height(bundled_fonts: FontSet):
    options = {"fonts": bundled_fonts, "scale": 1, "padding": 0}
    narrow = render_image(lines("abcdef"), **options)
    wide = render_image(lines("abcdef"), columns=12, **options)
    assert wide.width > narrow.width
    assert wide.height == narrow.height


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
    assert image.width > 0
    assert image.height > 0


@pytest.mark.parametrize(
    ("theme", "background"), [(DARK, DARK.background), (LIGHT, LIGHT.background)], ids=["dark", "light"]
)
def test_the_picture_is_filled_with_the_background_of_the_theme(theme, background, bundled_fonts: FontSet):
    image = render_image(lines(" "), fonts=bundled_fonts, theme=theme, scale=1)
    assert image.getcolors() == [(image.width * image.height, background.channels)]


def test_png_bytes_are_a_png_with_screen_resolution(bundled_fonts: FontSet):
    text = lines("hello")
    data = render_png(text, fonts=bundled_fonts, scale=2)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    image = Image.open(io.BytesIO(data))
    assert image.size == render_image(text, fonts=bundled_fonts, scale=2).size
    dpi = image.info["dpi"]
    assert round(dpi[0]) == 192  # 96 точек на дюйм "как на экране", умноженные на масштаб
    assert round(dpi[1]) == 192
