import io
import sys

import pytest

pytest.importorskip("PIL")

from PIL import Image

from termsnap import DARK, LIGHT, Line, Rgb, Span, Style, run
from termsnap.errors import FontNotFound
from termsnap.png import FontSet, render_image, render_png, resolve


@pytest.fixture(scope="module")
def fonts() -> FontSet:
    try:
        return resolve(covers="АЯабвёЖ")
    except FontNotFound as error:
        pytest.skip(f"в системе нет подходящего моноширинного шрифта: {error.problems}")


def rgb(color: Rgb) -> tuple[int, int, int]:
    return color.red, color.green, color.blue


def pixels(image: Image.Image) -> set[tuple[int, int, int]]:
    colors = image.convert("RGB").getcolors(maxcolors=image.width * image.height) or []
    return {color for _count, color in colors}


def test_background_and_size_follow_the_text(fonts: FontSet):
    lines = [Line((Span("abcdef"),)), Line((Span("ab"),)), Line()]
    one = render_image(lines, fonts=fonts, scale=1, padding=0)
    assert one.getpixel((0, 0)) == rgb(DARK.background)
    wide = render_image(lines, fonts=fonts, scale=1, padding=0, columns=12)
    assert wide.width > one.width
    assert wide.height == one.height
    taller = render_image([*lines, Line()], fonts=fonts, scale=1, padding=0)
    assert taller.height > one.height
    padded = render_image(lines, fonts=fonts, scale=1, padding=10)
    assert (padded.width, padded.height) == (one.width + 20, one.height + 20)


def test_scale_doubles_the_picture(fonts: FontSet):
    lines = [Line((Span("hello"),))]
    small = render_image(lines, fonts=fonts, scale=1, padding=8)
    big = render_image(lines, fonts=fonts, scale=2, padding=8)
    assert 1.9 < big.width / small.width < 2.1
    assert 1.9 < big.height / small.height < 2.1


def test_empty_output_still_gives_a_valid_picture(fonts: FontSet):
    image = render_image([], fonts=fonts)
    assert image.width > 0
    assert image.height > 0


def test_theme_decides_the_background(fonts: FontSet):
    image = render_image([Line((Span("x"),))], fonts=fonts, theme=LIGHT)
    assert image.getpixel((0, 0)) == (255, 255, 255)


def test_span_background_fills_its_cells(fonts: FontSet):
    colour = Rgb(10, 20, 30)
    lines = [Line((Span("   ", Style(bg=colour)),))]
    image = render_image(lines, fonts=fonts, scale=1, padding=0, theme=LIGHT)
    assert image.getpixel((1, 1)) == (10, 20, 30)
    assert image.getpixel((image.width - 1, image.height - 1)) == (10, 20, 30)


def test_text_is_drawn_in_the_style_colour(fonts: FontSet):
    colour = Rgb(250, 10, 10)
    lines = [Line((Span("MMMM", Style(fg=colour)),))]
    image = render_image(lines, fonts=fonts, scale=1, font_size=28, theme=LIGHT)
    assert (250, 10, 10) in pixels(image)


def test_inverse_swaps_text_and_background_colours(fonts: FontSet):
    lines = [Line((Span("   ", Style(inverse=True)),))]
    image = render_image(lines, fonts=fonts, scale=1, padding=0, theme=DARK)
    assert image.getpixel((1, 1)) == rgb(DARK.foreground)


def test_underline_and_strike_are_horizontal_lines_over_the_whole_span(fonts: FontSet):
    colour = Rgb(1, 200, 3)
    plain = render_image([Line((Span("MMMM", Style(fg=colour)),))], fonts=fonts, scale=1, font_size=28, theme=LIGHT)
    underlined = render_image(
        [Line((Span("MMMM", Style(fg=colour, underline=True)),))], fonts=fonts, scale=1, font_size=28, theme=LIGHT
    )
    struck = render_image(
        [Line((Span("MMMM", Style(fg=colour, strike=True)),))], fonts=fonts, scale=1, font_size=28, theme=LIGHT
    )

    def long_rows(image: Image.Image) -> int:
        width = image.width
        rows = 0
        for y in range(image.height):
            count = sum(1 for x in range(width) if image.getpixel((x, y)) == (1, 200, 3))
            rows += count >= width * 0.5
        return rows

    assert long_rows(plain) == 0
    assert long_rows(underlined) >= 1
    assert long_rows(struck) >= 1


def test_dim_text_is_closer_to_the_background(fonts: FontSet):
    bright = render_image([Line((Span("MMMM", Style(fg=Rgb(255, 255, 255))),))], fonts=fonts, scale=1, font_size=28)
    dim = render_image(
        [Line((Span("MMMM", Style(fg=Rgb(255, 255, 255), dim=True)),))], fonts=fonts, scale=1, font_size=28
    )
    assert max(sum(p) for p in pixels(bright)) > max(sum(p) for p in pixels(dim))


def test_bold_text_is_heavier_even_without_a_bold_face(fonts: FontSet):
    only_regular = FontSet(fonts.family, fonts.regular)
    light = render_image([Line((Span("MMMM"),))], fonts=only_regular, scale=2, font_size=20)
    heavy = render_image([Line((Span("MMMM", Style(bold=True)),))], fonts=only_regular, scale=2, font_size=20)

    def ink(image: Image.Image) -> int:
        background = image.getpixel((0, 0))
        colors = image.convert("RGB").getcolors(maxcolors=image.width * image.height) or []
        return sum(count for count, color in colors if color != background)

    assert ink(heavy) > ink(light)


def test_png_bytes_are_a_png_with_screen_resolution(fonts: FontSet):
    lines = [Line((Span("Привет, мир", Style(fg=Rgb(1, 2, 3))),))]
    data = render_png(lines, fonts=fonts, scale=2)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    image = Image.open(io.BytesIO(data))
    assert image.size == render_image(lines, fonts=fonts, scale=2).size
    dpi = image.info["dpi"]
    assert round(dpi[0]) == 192
    assert round(dpi[1]) == 192


def test_real_command_output_is_rendered_with_its_colours(fonts: FontSet):
    capture = run([sys.executable, "-c", "print('\x1b[38;2;1;250;3mgreen\x1b[0m done')"])
    image = render_image(capture.lines, fonts=fonts, scale=2, font_size=28)
    assert (1, 250, 3) in pixels(image)
